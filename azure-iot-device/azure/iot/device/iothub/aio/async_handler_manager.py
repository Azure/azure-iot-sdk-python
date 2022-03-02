# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
""" This module contains the manager for handler methods used by the aio clients"""

import asyncio
from asyncio.tasks import run_coroutine_threadsafe
import logging
import inspect
import concurrent.futures
from azure.iot.device.common import handle_exceptions
from azure.iot.device.iothub.sync_handler_manager import (
    AbstractHandlerManager,
    HandlerManagerException,
    HandlerRunnerKillerSentinel,
    CLIENT_EVENT,
)
from . import loop_management

logger = logging.getLogger(__name__)


class AsyncHandlerManager(AbstractHandlerManager):
    """Handler manager for use with asynchronous clients"""

    async def _receiver_handler_runner(self, inbox, handler_name):
        """Run infinite loop that waits for an inbox to receive an object from it, then calls
        the handler with that object
        """
        logger.debug("HANDLER RUNNER ({}): Starting runner".format(handler_name))

        # Define a callback that can handle errors in the ThreadPoolExecutor
        _handler_callback = self._generate_callback_for_handler("CLIENT_EVENT")

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
                # Free up this object so the garbage collector can free it if necessary. If we don't
                # do this, we end up keeping this object alive until the next event arrives, which
                # might be a long time. Tests would flag this as a memory leak if that happened.
                del handler_arg
                fut.add_done_callback(_handler_callback)
            else:
                # Run function directly in ThreadPool
                fut = tpe.submit(handler, handler_arg)
                # Free up this object so the garbage collector can free it if necessary. If we don't
                # do this, we end up keeping this object alive until the next event arrives, which
                # might be a long time. Tests would flag this as a memory leak if that happened.
                del handler_arg
                fut.add_done_callback(_handler_callback)

    async def _client_event_handler_runner(self):
        """Run infinite loop that waits for the client event inbox to receive an event from it,
        then calls the handler that corresponds to that event
        """
        logger.debug("HANDLER RUNNER (CLIENT EVENT): Starting runner")
        _handler_callback = self._generate_callback_for_handler("CLIENT_EVENT")

        # ThreadPool used for running handler functions. By invoking handlers in a separate thread
        # we can be safe knowing that customer code that has performance issues does not block
        # client code. Note that the ThreadPool is only used for handler FUNCTIONS (coroutines are
        # invoked on a dedicated event loop + thread)
        tpe = concurrent.futures.ThreadPoolExecutor(max_workers=4)
        event_inbox = self._inbox_manager.get_client_event_inbox()
        while True:
            event = await event_inbox.get()
            if isinstance(event, HandlerRunnerKillerSentinel):
                # Exit the runner when a HandlerRunnerKillerSentinel is found
                logger.debug(
                    "HANDLER RUNNER (CLIENT EVENT): HandlerRunnerKillerSentinel found in event queue. Exiting."
                )
                tpe.shutdown()
                break
            handler = self._get_handler_for_client_event(event.name)
            if handler is not None:
                logger.debug(
                    "HANDLER RUNNER (CLIENT EVENT): {} event received. Invoking {} handler".format(
                        event, handler
                    )
                )
                if inspect.iscoroutinefunction(handler):
                    # Run a coroutine on a dedicated event loop for handler invocations
                    # TODO: Can we call this on the user loop instead?
                    handler_loop = loop_management.get_client_handler_loop()
                    fut = asyncio.run_coroutine_threadsafe(
                        handler(*event.args_for_user), handler_loop
                    )
                    # Free up this object so the garbage collector can free it if necessary. If we don't
                    # do this, we end up keeping this object alive until the next event arrives, which
                    # might be a long time. Tests would flag this as a memory leak if that happened.
                    del event
                    fut.add_done_callback(_handler_callback)
                else:
                    # Run a function directly in ThreadPool
                    fut = tpe.submit(handler, *event.args_for_user)
                    # Free up this object so the garbage collector can free it if necessary. If we don't
                    # do this, we end up keeping this object alive until the next event arrives, which
                    # might be a long time. Tests would flag this as a memory leak if that happened.
                    del event
                    fut.add_done_callback(_handler_callback)
            else:
                logger.debug(
                    "No handler for event {} set. Skipping handler invocation".format(event)
                )

    def _start_handler_runner(self, handler_name):
        """Create, and store a task for running a handler"""
        # Run the handler runner on a dedicated event loop for handler runners so as to be
        # isolated from all other client activities
        runner_loop = loop_management.get_client_handler_runner_loop()

        # Client Event handler flow
        if handler_name == CLIENT_EVENT:
            if self._client_event_runner is not None:
                # This branch of code should NOT be reachable due to checks prior to the invocation
                # of this method. The branch exists for safety.
                raise HandlerManagerException(
                    "Cannot create thread for handler runner: {}. Runner thread already exists".format(
                        handler_name
                    )
                )
            # Client events share a handler
            coro = self._client_event_handler_runner()
            future = asyncio.run_coroutine_threadsafe(coro, runner_loop)
            # Store the future
            self._client_event_runner = future

        # Receiver handler flow
        else:
            if self._receiver_handler_runners[handler_name] is not None:
                # This branch of code should NOT be reachable due to checks prior to the invocation
                # of this method. The branch exists for safety.
                raise HandlerManagerException(
                    "Cannot create task for handler runner: {}. Task already exists".format(
                        handler_name
                    )
                )
            # Each receiver handler gets its own runner
            inbox = self._get_inbox_for_receive_handler(handler_name)
            coro = self._receiver_handler_runner(inbox, handler_name)
            future = asyncio.run_coroutine_threadsafe(coro, runner_loop)
            # Store the future
            self._receiver_handler_runners[handler_name] = future

        _handler_runner_callback = self._generate_callback_for_handler_runner(handler_name)
        future.add_done_callback(_handler_runner_callback)

    def _stop_receiver_handler_runner(self, handler_name):
        """Stop and remove a handler runner task.
        All pending items in the corresponding inbox will be handled by the handler before stoppage.
        """
        logger.debug(
            "Adding HandlerRunnerKillerSentinel to inbox corresponding to {} handler runner".format(
                handler_name
            )
        )
        inbox = self._get_inbox_for_receive_handler(handler_name)
        inbox.put(HandlerRunnerKillerSentinel())

        # Wait for Handler Runner to end due to the sentinel
        logger.debug("Waiting for {} handler runner to exit...".format(handler_name))
        future = self._receiver_handler_runners[handler_name]
        future.result()
        # Stop tracking the task since it is now complete
        self._receiver_handler_runners[handler_name] = None
        logger.debug("Handler runner for {} has been stopped".format(handler_name))

    def _stop_client_event_handler_runner(self):
        """Stop and remove a handler task.
        All pending items in the client event queue will be handled by handlers (if they exist)
        before stoppage.
        """
        logger.debug("Adding HandlerRunnerKillerSentinel to client event queue")
        event_inbox = self._inbox_manager.get_client_event_inbox()
        event_inbox.put(HandlerRunnerKillerSentinel())

        # Wait for Handler Runner to end due to the stop command
        logger.debug("Waiting for client event handler runner to exit...")
        future = self._client_event_runner
        future.result()
        # Stop tracking the task since it is now complete
        self._client_event_runner = None
        logger.debug("Handler runner for client events has been stopped")

    def _generate_callback_for_handler_runner(self, handler_name):
        """Define a callback that can handle errors during handler runner execution"""

        def handler_runner_callback(completed_future):
            try:
                e = completed_future.exception(timeout=0)
            except Exception as raised_e:
                # This shouldn't happen because cancellation or timeout shouldn't occur...
                # But just in case...
                new_err = HandlerManagerException(
                    "HANDLER RUNNER ({}): Unable to retrieve exception data from incomplete task".format(
                        handler_name
                    )
                )
                new_err.__cause__ = raised_e
                handle_exceptions.handle_background_exception(new_err)
            else:
                if e:
                    # If this branch is reached something has gone SERIOUSLY wrong.
                    # We must log the error, and then restart the runner so that the program
                    # does not enter an invalid state
                    new_err = HandlerManagerException(
                        "HANDLER RUNNER ({}): Unexpected error during task".format(handler_name),
                    )
                    new_err.__cause__ = e
                    handle_exceptions.handle_background_exception(new_err)
                    # Clear the tracked runner, and start a new one
                    logger.debug("HANDLER RUNNER ({}): Restarting handler runner")
                    self._receiver_handler_runners[handler_name] = None
                    self._start_handler_runner(handler_name)
                else:
                    logger.debug(
                        "HANDLER RUNNER ({}): Task successfully completed without exception".format(
                            handler_name
                        )
                    )

        return handler_runner_callback
