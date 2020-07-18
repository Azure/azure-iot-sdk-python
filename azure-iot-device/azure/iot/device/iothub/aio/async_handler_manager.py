# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
""" This module contains the manager for handler methods used by the aio clients"""

import asyncio
import logging
import inspect
from concurrent.futures import ThreadPoolExecutor
from azure.iot.device.common import asyncio_compat
from azure.iot.device.iothub.sync_handler_manager import (
    AbstractHandlerManager,
    HandlerManagerException,
)

logger = logging.getLogger(__name__)


class AsyncHandlerManager(AbstractHandlerManager):
    """Handler manager for use with asynchronous clients"""

    async def _inbox_handler_runner(self, inbox, handler_name):
        """Run infinite loop that waits for an inbox to receive an object from it, then calls
        the handler with that object
        """
        # Run the handler in a threadpool, so that it cannot block other handlers (from a different task),
        # or the main client thread. The number of worker threads forms an upper bound on how many instances
        # of the same handler can be running simultaneously.
        tp = ThreadPoolExecutor(max_workers=4)
        while True:
            handler_arg = await inbox.get()
            # NOTE: we MUST use getattr here using the handler name, as opposed to directly passing
            # the handler in order for the handler to be able to be updated without cancelling
            # the running task created for this coroutine
            handler = getattr(self, handler_name)
            if inspect.iscoroutinefunction(handler):
                # Wrap the coroutine in a function so it can be run in ThreadPool
                def coro_wrapper(coro, arg):
                    asyncio_compat.run(coro(arg))

                # TODO: get exceptions to propogate
                tp.submit(coro_wrapper, handler, handler_arg)
            else:
                # Run function directly in ThreadPool
                # TODO: get exceptions to propogate
                tp.submit(handler, handler_arg)

    async def _event_handler_runner(self, handler_name):
        # TODO: implement
        logger.error("._event_handler_runner() not yet implemented")

    def _start_handler_runner(self, handler_name):
        """Create, and store a task for running a handler
        """
        # First check if the handler task already exists
        if self._handler_runners[handler_name] is not None:
            raise HandlerManagerException(
                "Cannot create task for handler runner: {}. Task already exists".format(
                    handler_name
                )
            )

        inbox = self._get_inbox_for_handler(handler_name)

        if inbox:
            coro = self._inbox_handler_runner(inbox, handler_name)
        else:
            coro = self._event_handler_runner(handler_name)
        task = asyncio_compat.create_task(coro)
        # TODO: what happens if an exception is raised?
        self._handler_runners[handler_name] = task

    def _stop_handler_runner(self, handler_name):
        """Cancel and remove a handler runner task"""
        task = self._handler_runners[handler_name]
        task.cancel()
        self._handler_runners[handler_name] = None
