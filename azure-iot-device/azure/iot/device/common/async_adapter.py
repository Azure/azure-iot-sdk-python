# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module contains tools for adapting sync code for use in async coroutines."""

import functools
import logging
import azure.iot.device.common.asyncio_compat as asyncio_compat

logger = logging.getLogger(__name__)


def emulate_async(fn):
    """Returns a coroutine function that calls a given function with emulated asynchronous
    behavior via use of mulithreading.

    Can be applied as a decorator.

    :param fn: The sync function to be run in async.
    :returns: A coroutine function that will call the given sync function.
    """

    @functools.wraps(fn)
    async def async_fn_wrapper(*args, **kwargs):
        loop = asyncio_compat.get_running_loop()

        # Run fn in default ThreadPoolExecutor (CPU * 5 threads)
        return await loop.run_in_executor(None, functools.partial(fn, *args, **kwargs))

    return async_fn_wrapper


class AwaitableCallback(object):
    """A sync callback whose completion can be waited upon.
    """

    def __init__(self, return_arg_name=None):
        """Creates an instance of an AwaitableCallback
        """

        # LBYL because this mistake doesn't cause an exception until the callback
        # which is much later and very difficult to trace back to here.
        if return_arg_name and not isinstance(return_arg_name, str):
            raise TypeError("internal error: return_arg_name must be a string")

        loop = asyncio_compat.get_running_loop()
        self.future = asyncio_compat.create_future(loop)

        def wrapping_callback(*args, **kwargs):
            # Use event loop from outer scope, since the threads it will be used in will not have
            # an event loop. future.set_result() and future.set_exception have to be called in an
            # event loop or they do not work.
            if "error" in kwargs and kwargs["error"]:
                exception = kwargs["error"]
            elif return_arg_name:
                if return_arg_name in kwargs:
                    exception = None
                    result = kwargs[return_arg_name]
                else:
                    raise TypeError(
                        "internal error: excepected argument with name '{}', did not get".format(
                            return_arg_name
                        )
                    )
            else:
                exception = None
                result = None

            if exception:
                logger.error(
                    "Callback completed with error {}".format(exception), exc_info=exception
                )
                loop.call_soon_threadsafe(self.future.set_exception, exception)
            else:
                logger.debug("Callback completed with result {}".format(result))
                loop.call_soon_threadsafe(self.future.set_result, result)

        self.callback = wrapping_callback

    def __call__(self, *args, **kwargs):
        """Calls the callback. Returns the result.
        """
        return self.callback(*args, **kwargs)

    async def completion(self):
        """Awaitable coroutine method that will return once the AwaitableCallback
        has been completed.

        :returns: Result of the callback when it was called.
        """
        return await self.future
