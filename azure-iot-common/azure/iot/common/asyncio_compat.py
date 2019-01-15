import asyncio
import functools


def get_running_loop():
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


def create_task(coro):
    """
    Helper function to create a task. "Best effort" function.
    If avaialable (Python 3.7+), use asyncio.create_task, which is preferred as it is
    more specific for the goal of immediately scheduling a task from a coroutine. If
    not available, use the more general puprose asyncio.ensure_future
    """
    try:
        task = asyncio.create_task(coro)
    except AttributeError:
        task = asyncio.ensure_future(coro)
    return task


def run(coro, debug=False):
    """
    Helper function to abstract event loop setup/cleanup. Uses asyncio.run() if it is
    available. Otherwise, manually gets, runs and closes the event loop
    """
    try:
        asyncio.run(coro, debug=debug)
    except AttributeError:
        loop = asyncio.get_event_loop()  # NOT running loop
        loop.set_debug(debug)
        loop.run_until_complete(coro)
        loop.close()


def create_future(loop):
    """
    Helper function to create a Future object.  Uses loop.create_future() if it is
    available.  Otherwise, create the object directly.  loop.create_future is preferred
    because it allows third parties to provide their own Future object, but it is only
    available in 3.5.2+
    """
    try:
        future = loop.create_future()
    except AttributeError:
        future = asyncio.Future(loop=loop)
    return future


def emulate_async(fn):
    """
    Apply as a decorator to emulate async behavior with a sync function/method
    via usage of multithreading
    """

    @functools.wraps(fn)
    async def async_fn_wrapper(*args, **kwargs):
        loop = get_running_loop()

        # Run fn in default ThreadPoolExecutor (CPU * 5 threads)
        await loop.run_in_executor(None, fn, *args, **kwargs)

    return async_fn_wrapper


class AwaitableCallback(object):
    """
    A callback whose completion can be waited upon.
    """

    def __init__(self, callback):
        """
        Creates an instance of an AwaitableCallback from a callback function.

        :param callback: Callback function to be made awaitable.
        """
        loop = get_running_loop()
        self.future = create_future(loop)

        def wrapping_callback(*args, **kwargs):
            result = callback(*args, **kwargs)
            # Use event loop from outer scope, since the threads it will be used in will not have
            # an event loop. future.set_result() has to be called in an event loop or it does not work.
            loop.call_soon_threadsafe(self.future.set_result, result)
            return result

        self.callback = wrapping_callback

    def __call__(self, *args, **kwargs):
        """
        Calls the callback. Returns the result.
        """
        return self.callback(*args, **kwargs)

    async def completion(self):
        """
        Awaitable method that will return once the AwaitableCallback has been completed.

        :returns: Result of the callback when it was called.
        """
        return await self.future
