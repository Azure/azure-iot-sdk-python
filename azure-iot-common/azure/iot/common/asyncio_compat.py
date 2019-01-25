import asyncio


def get_running_loop():
    """
    Helper function to use the best method to get an event loop to run async code
    in.  Uses asyncio.get_running_loop() if available (Python 3.7+) or a backported
    version of the same function in 3.5/3.6.
    """
    try:
        loop = asyncio.get_running_loop()
    except AttributeError:
        loop = asyncio._get_running_loop()
        if loop is None:
            raise RuntimeError("no running event loop")
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
