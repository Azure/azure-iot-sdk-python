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

logger = logging.getLogger(__name__)

# This logic could potentially be encapsulated in another module...
# Say... some kind of... loop_manager.py?
RUNNER_LOOP = asyncio.new_event_loop()
RUNNER_THREAD = threading.Thread(target=RUNNER_LOOP.run_forever)
RUNNER_THREAD.daemon = True
RUNNER_THREAD.start()


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
                e = future.exception()
            except concurrent.futures.CancelledError as raised_e:
                new_err = HandlerManagerException(
                    message="HANDLER ({}): Invocation unexpectedly ended with cancellation".format(
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

        # Run the handler in a threadpool, so that it cannot block other handlers (from a different task),
        # or the main client thread. The number of worker threads forms an upper bound on how many instances
        # of the same handler can be running simultaneously.
        # NOTE: eventually we might want to do this in the customer's event loop (for coroutine handlers).
        # However this will require more infrastructure that is not yet prepared.
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
        # First check if the handler runner already exists
        if self._handler_runners[handler_name] is not None:
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
        future = asyncio.run_coroutine_threadsafe(coro, RUNNER_LOOP)

        # Define a callback for the future (in order to handle any errors)
        def _handler_runner_callback(completed_future):
            try:
                e = completed_future.exception()
            except asyncio.CancelledError:
                # TODO: is this the right error?
                new_err = HandlerManagerException(
                    message="HANDLER RUNNER ({}): Task unexpectedly ended in cancellation".format(
                        handler_name
                    )
                )
                handle_exceptions.handle_background_exception(new_err)
            else:
                if e:
                    new_err = HandlerManagerException(
                        message="HANDLER RUNNER ({}): Unexpected error during task".format(
                            handler_name
                        ),
                        cause=e,
                    )
                    handle_exceptions.handle_background_exception(new_err)
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
        future = self._handler_runners[handler_name]
        future.result()
        # Stop tracking the task since it is now complete
        self._handler_runners[handler_name] = None
