# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module contains compatibility tools for bridging different versions of asyncio"""

import asyncio


def get_running_loop():
    """Gets the currently running event loop

    Uses asyncio.get_running_loop() if available (Python 3.7+) or a backported
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
    """Creates a Task object.

    If avaialable (Python 3.7+), use asyncio.create_task, which is preferred as it is
    more specific for the goal of immediately scheduling a task from a coroutine. If
    not available, use the more general puprose asyncio.ensure_future.

    :returns: A new Task object.
    """
    try:
        task = asyncio.create_task(coro)
    except AttributeError:
        task = asyncio.ensure_future(coro)
    return task


def create_future(loop):
    """Creates a Future object.

    Uses loop.create_future if it is available. Otherwise, create the object directly.

    Use of loop.create_future is preferred because it allows third parties to provide their own
    Future object, but it is only available in 3.5.2+

    :returns: A new Future object.
    """
    try:
        future = loop.create_future()
    except AttributeError:
        future = asyncio.Future(loop=loop)
    return future
