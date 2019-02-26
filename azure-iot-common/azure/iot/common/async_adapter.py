# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module contains tools for adapting sync code for use in async coroutines."""

import functools
import azure.iot.common.asyncio_compat as asyncio_compat


def emulate_async(fn):
    """Apply as a decorator to emulate async behavior with a sync function/method
    via usage of multithreading.

    :param fn: The sync function to be run in async.
    :returns: A coroutine function that will call the given sync function.
    """

    @functools.wraps(fn)
    async def async_fn_wrapper(*args, **kwargs):
        loop = asyncio_compat.get_running_loop()

        # Run fn in default ThreadPoolExecutor (CPU * 5 threads)
        return await loop.run_in_executor(None, fn, *args, **kwargs)

    return async_fn_wrapper


class AwaitableCallback(object):
    """A sync callback whose completion can be waited upon.
    """

    def __init__(self, callback):
        """Creates an instance of an AwaitableCallback from a callback function.

        :param callback: Callback function to be made awaitable.
        """
        loop = asyncio_compat.get_running_loop()
        self.future = asyncio_compat.create_future(loop)

        def wrapping_callback(*args, **kwargs):
            result = callback(*args, **kwargs)
            # Use event loop from outer scope, since the threads it will be used in will not have
            # an event loop. future.set_result() has to be called in an event loop or it does not work.
            loop.call_soon_threadsafe(self.future.set_result, result)
            return result

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
