# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module contains compatibility tools for bridging different versions of asyncio"""

import asyncio
import sys


def get_running_loop():
    """Gets the currently running event loop

    Uses asyncio.get_running_loop() if available (Python 3.7+) or a backported
    version of the same function in 3.6.
    """
    try:
        loop = asyncio.get_running_loop()
    except AttributeError:
        loop = asyncio._get_running_loop()
        if loop is None:
            raise RuntimeError("no running event loop")
    return loop


def create_task(coro):
    """Creates a Task object.

    If available (Python 3.7+), use asyncio.create_task, which is preferred as it is
    more specific for the goal of immediately scheduling a task from a coroutine. If
    not available, use the more general puprose asyncio.ensure_future.

    :returns: A new Task object.
    """
    try:
        task = asyncio.create_task(coro)
    except AttributeError:
        task = asyncio.ensure_future(coro)
    return task


def run(coro):
    """Execute the coroutine coro and return the result.

    It creates a new event loop and closes it at the end.
    Cannot be called when another asyncio event loop is running in the same thread.

    If available (Python 3.7+) use asyncio.run. If not available, use a custom implementation
    that achieves the same thing
    """
    if sys.version_info >= (3, 7):
        return asyncio.run(coro)
    else:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
            asyncio.set_event_loop(None)
