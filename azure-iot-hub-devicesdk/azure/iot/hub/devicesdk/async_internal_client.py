# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------
import logging
import asyncio
import functools
from .internal_client import InternalClient

logger = logging.getLogger(__name__)


# all of our async wrappers can follow this same pattern.  We might be able to make this into a
# helper function, but that will involve some tricky parameter handling because the signature of
# callback changes depending on the function.

# these are currently just functions in the module namespace.  We add them to the InternalClient
# prototype below inside the monkeypatch() function.


def _get_event_loop():
    """
    Helper function to use the best method to get an event loop to run async code
    in.  This is a "best effort" function.  get_running_loop is preferred because it
    works in more cases (especially if customers are using custom event loop policies),
    but get_event_loop works well in simple cases (e.g. there is only one loop).
    """
    try:
        loop = asyncio.get_running_loop()
    except AttributeError:
        loop = asyncio.get_event_loop()
    return loop


def _create_future(loop):
    """
    Helper function to create a Future object.  Uses loop.create_future() if it is
    available.  Otherwise, create the object directly.  loop.create_future is preferred
    because it allows third parties to provide their own Future object, but it is only
    available in 3.5.2+
    """
    try:
        future = loop.create_future()
    except AttributeError:
        future = asyncio.Future()
    return future


async def _connect_async(self):
    """
    This is just a test docstring to make sure we can see documentation for these functions
    when we call help(InternalClient), and we can, so life is good and everyone is happy.
    """
    logger.info("async connecting to transport")

    # we need the event loop so we can run our code in side it.
    loop = _get_event_loop()

    # the future is how we communicate the result from the callback task back into the "main" task
    future = _create_future(loop)

    # This is a sync callback that is called by the transport.  We don't know what thread it's
    # going to be called in.
    def callback():
        logger.info("async connect finished")

        # We use the asyncio event loop from our outer scope because that's the event loop for the
        # thread that started this operation.  This is important because this callback is called
        # in the context of some transport thread, and we can almost guarantee that this thread
        # does not have an asyncio event loop.  This line basically says "call future.set_result(None),
        # as soon as you can, in the context of the (outer scope) asyncio event loop."
        #
        # Interestingly enough, even though future.set_result() is not an awaitable function, you
        # still need to call it from inside the context of an asyncio event loop.  Otherwise it
        # won't propertly signal any awaiters.  Don't get tricked by this and waste as much time
        # as I did :)

        loop.call_soon_threadsafe(future.set_result, None)

    # call self._transport.connect(callback) in a threadpool thread managed by asyncio.
    # This thread pool is called a ThreadPoolExecutor, which is a subclass of Executor. This way,
    # the calling thread doesn't get blocked by our calls down into the transport.  In asyncio
    # parlance, an Executor is something that lets you await blocking code.  ThreadPoolExecutor
    # farms out the code to (CPUs * 5) background threads (by default).  There is also
    # ProcessPoolExecutor which can farm the code out to background processes.  The first
    # None parameter means "use the default executor."

    await loop.run_in_executor(None, self._transport.connect, callback)

    # finally, await the callback's call to future.set_result
    await future


async def _disconnect_async(self):
    logger.info("async disconnecting from transport")
    loop = _get_event_loop()
    future = _create_future(loop)

    def callback():
        logger.info("async disconnect finished")
        loop.call_soon_threadsafe(future.set_result, None)

    await loop.run_in_executor(None, self._transport.disconnect, callback)
    await future


async def _send_event_async(self, event):
    logger.info("async sending event")
    loop = _get_event_loop()
    future = _create_future(loop)

    def callback():
        logger.info("async sending finished")
        loop.call_soon_threadsafe(future.set_result, None)

    await loop.run_in_executor(None, self._transport.send_event, event, callback)
    await future


def monkeypatch():
    InternalClient.connect_async = _connect_async
    InternalClient.disconnect_async = _disconnect_async
    InternalClient.send_event_async = _send_event_async
