# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
""" This module contains the manager for handler methods used by the aio clients"""

import asyncio
import logging
import inspect
import threading
import concurrent.futures
from azure.iot.device.common import asyncio_compat, handle_exceptions
from azure.iot.device.iothub.sync_handler_manager import (
    AbstractHandlerManager,
    HandlerManagerException,
    HandlerRunnerKillerSentinel,
)
from . import loop_management

logger = logging.getLogger(__name__)


class AsyncHandlerManager(AbstractHandlerManager):
    """Handler manager for use with asynchronous clients"""

    async def _inbox_handler_runner(self, inbox, handler_name):
        """Run infinite loop that waits for an inbox to receive an object from it, then calls
        the handler with that object
        """
        logger.debug("HANDLER RUNNER ({}): Starting runner".format(handler_name))

        # Define a callback that can handle errors in the ThreadPoolExecutor
        def _handler_callback(future):
            try:
                e = future.exception(timeout=0)
            except Exception as raised_e:
                # This shouldn't happen because cancellation or timeout shouldn't occur...
                # But just in case...
                new_err = HandlerManagerException(
                    message="HANDLER ({}): Unable to retrieve exception data from incomplete invocation".format(
                        handler_name
                    ),
                    cause=raised_e,
                )
                handle_exceptions.handle_background_exception(new_err)
            else:
                if e:
                    new_err = HandlerManagerException(
                        message="HANDLER ({}): Error during invocation".format(handler_name),
                        cause=e,
                    )
                    handle_exceptions.handle_background_exception(new_err)
                else:
                    logger.debug(
                        "HANDLER ({}): Successfully completed invocation".format(handler_name)
                    )

        # ThreadPool used for running handler functions. By invoking handlers in a separate thread
        # we can be safe knowing that customer code that has performance issues does not block
        # client code. Note that the ThreadPool is only used for handler FUNCTIONS (coroutines are
        # invoked on a dedicated event loop + thread)
        tpe = concurrent.futures.ThreadPoolExecutor(max_workers=4)
        while True:
            handler_arg = await inbox.get()
            if isinstance(handler_arg, HandlerRunnerKillerSentinel):
                # Exit the runner when a HandlerRunnerKillerSentinel is found
                logger.debug(
                    "HANDLER RUNNER ({}): HandlerRunnerKillerSentinel found in inbox. Exiting.".format(
                        handler_name
                    )
                )
                tpe.shutdown()
                break
            # NOTE: we MUST use getattr here using the handler name, as opposed to directly passing
            # the handler in order for the handler to be able to be updated without cancelling
            # the running task created for this coroutine
            handler = getattr(self, handler_name)
            logger.debug("HANDLER RUNNER ({}): Invoking handler".format(handler_name))
            if inspect.iscoroutinefunction(handler):
                # Run coroutine on a dedicated event loop for handler invocations
                # TODO: Can we call this on the user loop instead?
                handler_loop = loop_management.get_client_handler_loop()
                fut = asyncio.run_coroutine_threadsafe(handler(handler_arg), handler_loop)
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
        # First check if the handler runner already exists
        if self._handler_runners[handler_name] is not None:
            # This branch of code should NOT be reachable due to checks prior to the invocation
            # of this method. The branch exists for safety.
            raise HandlerManagerException(
                "Cannot create task for handler runner: {}. Task already exists".format(
                    handler_name
                )
            )

        # Schedule a coroutine with the correct type of handler runner
        inbox = self._get_inbox_for_handler(handler_name)
        if inbox:
            coro = self._inbox_handler_runner(inbox, handler_name)
        else:
            coro = self._event_handler_runner(handler_name)
        # Run the handler runner on a dedicated event loop for handler runners so as to be
        # isolated from all other client activities
        runner_loop = loop_management.get_client_handler_runner_loop()
        future = asyncio.run_coroutine_threadsafe(coro, runner_loop)

        # Define a callback for the future (in order to handle any errors)
        def _handler_runner_callback(completed_future):
            try:
                e = completed_future.exception(timeout=0)
            except Exception as raised_e:
                # This shouldn't happen because cancellation or timeout shouldn't occur...
                # But just in case...
                new_err = HandlerManagerException(
                    message="HANDLER RUNNER ({}): Unable to retrieve exception data from incomplete task".format(
                        handler_name
                    ),
                    cause=raised_e,
                )
                handle_exceptions.handle_background_exception(new_err)
            else:
                if e:
                    # If this branch is reached something has gone SERIOUSLY wrong.
                    # We must log the error, and then restart the runner so that the program
                    # does not enter an invalid state
                    new_err = HandlerManagerException(
                        message="HANDLER RUNNER ({}): Unexpected error during task".format(
                            handler_name
                        ),
                        cause=e,
                    )
                    handle_exceptions.handle_background_exception(new_err)
                    # Clear the tracked runner, and start a new one
                    self._handler_runners[handler_name] = None
                    self._start_handler_runner(handler_name)
                else:
                    logger.debug(
                        "HANDLER RUNNER ({}): Task successfully completed without exception".format(
                            handler_name
                        )
                    )

        future.add_done_callback(_handler_runner_callback)

        # Store the future
        self._handler_runners[handler_name] = future
        logger.debug("Future for Handler Runner ({}) was stored".format(handler_name))

    def _stop_handler_runner(self, handler_name):
        """Stop and remove a handler runner task.
        All pending items in the corresponding inbox will be handled by the handler before stoppage.
        """
        # Add a Handler Runner Killer Sentinel to the relevant inbox
        logger.debug(
            "Adding HandlerRunnerKillerSentinel to inbox corresponding to {} handler runner".format(
                handler_name
            )
        )
        inbox = self._get_inbox_for_handler(handler_name)
        inbox._put(HandlerRunnerKillerSentinel())
        # Wait for Handler Runner to end due to the sentinel
        logger.debug("Waiting for {} handler runner to exit...".format(handler_name))
        future = self._handler_runners[handler_name]
        future.result()
        # Stop tracking the task since it is now complete
        self._handler_runners[handler_name] = None
        logger.debug("Handler runner for {} has been stopped".format(handler_name))
