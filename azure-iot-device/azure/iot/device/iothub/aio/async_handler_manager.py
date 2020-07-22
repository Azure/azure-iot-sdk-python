# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
""" This module contains the manager for handler methods used by the aio clients"""

import asyncio
import logging
import inspect
import concurrent.futures
from azure.iot.device.common import asyncio_compat, handle_exceptions
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
        # Define a callback that can handle errors in the ThreadPoolExecutor
        def _handler_callback(future):
            try:
                e = future.exception()
            except concurrent.futures.CancelledError as raised_e:
                new_err = HandlerManagerException(
                    message="Handler for {} unexpectedly ended with cancellation".format(
                        handler_name
                    ),
                    cause=raised_e,
                )
                handle_exceptions.handle_background_exception(new_err)
            else:
                new_err = HandlerManagerException(
                    message="Error in handler for {}".format(handler_name), cause=e
                )
                handle_exceptions.handle_background_exception(new_err)

        # Run the handler in a threadpool, so that it cannot block other handlers (from a different task),
        # or the main client thread. The number of worker threads forms an upper bound on how many instances
        # of the same handler can be running simultaneously.
        tpe = concurrent.futures.ThreadPoolExecutor(max_workers=4)
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

                fut = tpe.submit(coro_wrapper, handler, handler_arg)
                fut.add_done_callback(_handler_callback)
            else:
                # Run function directly in ThreadPool
                fut = tpe.submit(handler, handler_arg)
                fut.add_done_callback(_handler_callback)

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

        # Schedule a task with the correct type of handler runner
        inbox = self._get_inbox_for_handler(handler_name)
        if inbox:
            coro = self._inbox_handler_runner(inbox, handler_name)
        else:
            coro = self._event_handler_runner(handler_name)
        task = asyncio_compat.create_task(coro)

        # Define a callback for the task (in order to handle any errors)
        def _handler_runner_callback(completed_task):
            try:
                e = completed_task.exception()
            except asyncio.CancelledError:
                # This is the only "valid" path, since the runner is an infinite loop
                logger.debug("Handler runner for {} ended with cancellation")
            else:
                if e:
                    new_err = HandlerManagerException(
                        message="Error in handler runner for {}".format(handler_name), cause=e
                    )
                    handle_exceptions.handle_background_exception(new_err)
                else:
                    new_err = HandlerManagerException(
                        message="Handler runner for {} completed with no exception (exception was expected)".format(
                            handler_name
                        )
                    )
                    handle_exceptions.handle_background_exception(new_err)

        task.add_done_callback(_handler_runner_callback)

        # Store the task
        self._handler_runners[handler_name] = task

    def _stop_handler_runner(self, handler_name):
        """Cancel and remove a handler runner task"""
        task = self._handler_runners[handler_name]
        task.cancel()
        self._handler_runners[handler_name] = None
