# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module contains the manager for handler methods used by the aio clients"""

import asyncio
import logging
import inspect
import concurrent.futures
import threading
from azure.iot.device.common import handle_exceptions
from azure.iot.device.iothub.sync_handler_manager import (
    AbstractHandlerManager,
    HandlerManagerException,
    HandlerRunnerKillerSentinel,
    CLIENT_EVENT,
    client_events,
)
from . import loop_management

logger = logging.getLogger(__name__)

HANDLER_RUNNER_RESTART_BASE_DELAY = 0.1
HANDLER_RUNNER_RESTART_MAX_DELAY = 30.0


def _get_handler_runner_restart_delay(attempt):
    if attempt < 1:
        raise ValueError("Restart attempt must be at least 1")

    delay = min(HANDLER_RUNNER_RESTART_BASE_DELAY, HANDLER_RUNNER_RESTART_MAX_DELAY)
    for _ in range(1, attempt):
        delay = min(delay * 2, HANDLER_RUNNER_RESTART_MAX_DELAY)
        if delay == HANDLER_RUNNER_RESTART_MAX_DELAY:
            break
    return delay


class AsyncHandlerManager(AbstractHandlerManager):
    """Handler manager for use with asynchronous clients"""

    def __init__(self, inbox_manager):
        super().__init__(inbox_manager)
        runner_names = list(self._receiver_handler_runners) + [CLIENT_EVENT]
        self._handler_runner_lock = threading.RLock()
        self._handler_runner_restart_attempts = {name: 0 for name in runner_names}
        self._handler_runner_restart_tasks = {name: None for name in runner_names}
        self._handler_runner_restart_tokens = {name: None for name in runner_names}
        self._handler_runners_stopping = set()

    def _get_handler_runner(self, handler_name):
        if handler_name == CLIENT_EVENT:
            return self._client_event_runner
        return self._receiver_handler_runners[handler_name]

    def _set_handler_runner(self, handler_name, future):
        if handler_name == CLIENT_EVENT:
            self._client_event_runner = future
        else:
            self._receiver_handler_runners[handler_name] = future

    def _handler_runner_is_required(self, handler_name):
        if handler_name == CLIENT_EVENT:
            return any(
                self._get_handler_for_client_event(event_name) is not None
                for event_name in client_events
            )
        return getattr(self, handler_name) is not None

    def _cancel_pending_handler_runner_restart(self, handler_name):
        restart_task = self._handler_runner_restart_tasks[handler_name]
        self._handler_runner_restart_tasks[handler_name] = None
        self._handler_runner_restart_tokens[handler_name] = None
        if restart_task is not None:
            restart_task.cancel()

    def _reset_handler_runner_restart_attempts(self, handler_name):
        if self._handler_runner_restart_attempts[handler_name]:
            with self._handler_runner_lock:
                self._handler_runner_restart_attempts[handler_name] = 0

    async def _receiver_handler_runner(self, inbox, handler_name):
        """Run infinite loop that waits for an inbox to receive an object from it, then calls
        the handler with that object
        """
        logger.debug("HANDLER RUNNER ({}): Starting runner".format(handler_name))

        # Define a callback that can handle errors in the ThreadPoolExecutor
        _handler_callback = self._generate_callback_for_handler(handler_name)

        # ThreadPool used for running handler functions. By invoking handlers in a separate thread
        # we can be safe knowing that customer code that has performance issues does not block
        # client code. Note that the ThreadPool is only used for handler FUNCTIONS (coroutines are
        # invoked on a dedicated event loop + thread)
        tpe = concurrent.futures.ThreadPoolExecutor(max_workers=4)
        graceful_shutdown = False
        try:
            while True:
                handler_arg = await inbox.get()
                self._reset_handler_runner_restart_attempts(handler_name)
                if isinstance(handler_arg, HandlerRunnerKillerSentinel):
                    # Exit the runner when a HandlerRunnerKillerSentinel is found
                    logger.debug(
                        "HANDLER RUNNER ({}): HandlerRunnerKillerSentinel found in inbox. Exiting.".format(
                            handler_name
                        )
                    )
                    graceful_shutdown = True
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
        finally:
            tpe.shutdown(wait=graceful_shutdown)

    async def _client_event_handler_runner(self):
        tpe = concurrent.futures.ThreadPoolExecutor(max_workers=4)
        graceful_shutdown = False
        try:
            graceful_shutdown = await self._run_client_event_handler_runner(tpe)
        finally:
            tpe.shutdown(wait=graceful_shutdown)

    async def _run_client_event_handler_runner(self, tpe):
        """Run infinite loop that waits for the client event inbox to receive an event from it,
        then calls the handler that corresponds to that event
        """
        logger.debug("HANDLER RUNNER (CLIENT EVENT): Starting runner")
        _handler_callback = self._generate_callback_for_handler(CLIENT_EVENT)

        # ThreadPool used for running handler functions. By invoking handlers in a separate thread
        # we can be safe knowing that customer code that has performance issues does not block
        # client code. Note that the ThreadPool is only used for handler FUNCTIONS (coroutines are
        # invoked on a dedicated event loop + thread)
        event_inbox = self._inbox_manager.get_client_event_inbox()
        while True:
            event = await event_inbox.get()
            self._reset_handler_runner_restart_attempts(CLIENT_EVENT)
            if isinstance(event, HandlerRunnerKillerSentinel):
                # Exit the runner when a HandlerRunnerKillerSentinel is found
                logger.debug(
                    "HANDLER RUNNER (CLIENT EVENT): HandlerRunnerKillerSentinel found in event queue. Exiting."
                )
                return True
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

    def _start_handler_runner(self, handler_name, is_restart=False):
        """Create and store a task for running a handler."""
        with self._handler_runner_lock:
            if not is_restart:
                self._cancel_pending_handler_runner_restart(handler_name)
                self._handler_runner_restart_attempts[handler_name] = 0
                if not self._handler_runner_is_required(handler_name):
                    return

            runner_loop = loop_management.get_client_handler_runner_loop()
            if self._get_handler_runner(handler_name) is not None:
                raise HandlerManagerException(
                    "Cannot create task for handler runner: {}. Task already exists".format(
                        handler_name
                    )
                )

            if handler_name == CLIENT_EVENT:
                coro = self._client_event_handler_runner()
            else:
                inbox = self._get_inbox_for_receive_handler(handler_name)
                coro = self._receiver_handler_runner(inbox, handler_name)

            try:
                future = asyncio.run_coroutine_threadsafe(coro, runner_loop)
            except RuntimeError:
                coro.close()
                raise

            self._set_handler_runner(handler_name, future)
            callback = self._generate_callback_for_handler_runner(handler_name)
            future.add_done_callback(callback)

    async def _restart_handler_runner_after_delay(self, handler_name, delay, restart_token):
        try:
            await asyncio.sleep(delay)
        except asyncio.CancelledError:
            return

        with self._handler_runner_lock:
            if self._handler_runner_restart_tokens[handler_name] is not restart_token:
                return

            self._handler_runner_restart_tasks[handler_name] = None
            self._handler_runner_restart_tokens[handler_name] = None
            if (
                self._get_handler_runner(handler_name) is not None
                or handler_name in self._handler_runners_stopping
                or not self._handler_runner_is_required(handler_name)
            ):
                return

            try:
                self._start_handler_runner(handler_name, is_restart=True)
            except (HandlerManagerException, RuntimeError) as e:
                new_err = HandlerManagerException(
                    "HANDLER RUNNER ({}): Unable to restart handler runner".format(handler_name)
                )
                new_err.__cause__ = e
                handle_exceptions.handle_background_exception(new_err)

    def _schedule_handler_runner_restart(self, handler_name, completed_future):
        with self._handler_runner_lock:
            if self._get_handler_runner(handler_name) is not completed_future:
                return None

            self._set_handler_runner(handler_name, None)
            if (
                handler_name in self._handler_runners_stopping
                or not self._handler_runner_is_required(handler_name)
            ):
                self._handler_runner_restart_attempts[handler_name] = 0
                return False, 0, 0

            self._handler_runner_restart_attempts[handler_name] += 1
            attempt = self._handler_runner_restart_attempts[handler_name]
            delay = _get_handler_runner_restart_delay(attempt)
            restart_token = object()
            restart_coro = self._restart_handler_runner_after_delay(
                handler_name, delay, restart_token
            )
            runner_loop = loop_management.get_client_handler_runner_loop()
            self._handler_runner_restart_tokens[handler_name] = restart_token
            try:
                restart_task = asyncio.run_coroutine_threadsafe(restart_coro, runner_loop)
            except RuntimeError:
                self._handler_runner_restart_tokens[handler_name] = None
                restart_coro.close()
                raise
            self._handler_runner_restart_tasks[handler_name] = restart_task
            return True, attempt, delay

    def _stop_receiver_handler_runner(self, handler_name):
        """Stop and remove a receiver handler runner."""
        inbox = self._get_inbox_for_receive_handler(handler_name)
        self._stop_handler_runner(handler_name, inbox)

    def _stop_client_event_handler_runner(self):
        """Stop and remove the client event handler runner."""
        event_inbox = self._inbox_manager.get_client_event_inbox()
        self._stop_handler_runner(CLIENT_EVENT, event_inbox)

    def _stop_handler_runner(self, handler_name, inbox):
        with self._handler_runner_lock:
            self._handler_runners_stopping.add(handler_name)
            self._cancel_pending_handler_runner_restart(handler_name)
            self._handler_runner_restart_attempts[handler_name] = 0
            future = self._get_handler_runner(handler_name)
            if future is None:
                self._handler_runners_stopping.discard(handler_name)
                return

            if not future.done():
                logger.debug(
                    "Adding HandlerRunnerKillerSentinel to inbox corresponding to {} handler runner".format(
                        handler_name
                    )
                )
                inbox.put(HandlerRunnerKillerSentinel())

        logger.debug("Waiting for {} handler runner to exit...".format(handler_name))
        try:
            runner_error = future.exception()
        except concurrent.futures.CancelledError:
            runner_error = None
        if runner_error is not None:
            logger.debug(
                "Handler runner for {} exited with a previously reported error".format(handler_name)
            )

        with self._handler_runner_lock:
            if self._get_handler_runner(handler_name) is future:
                self._set_handler_runner(handler_name, None)
            self._handler_runners_stopping.discard(handler_name)
        logger.debug("Handler runner for {} has been stopped".format(handler_name))

    def stop(self, receiver_handlers_only=False):
        """Stop the process of invoking handlers in response to events.
        All pending items will be handled prior to stoppage.
        """
        for handler_name in self._receiver_handler_runners:
            self._stop_receiver_handler_runner(handler_name)

        if not receiver_handlers_only:
            self._stop_client_event_handler_runner()

    def ensure_running(self):
        """Ensure the process of invoking handlers in response to events is running."""
        with self._handler_runner_lock:
            for handler_name in self._receiver_handler_runners:
                if (
                    self._receiver_handler_runners[handler_name] is None
                    and getattr(self, handler_name) is not None
                ):
                    self._start_handler_runner(handler_name)

            if self._client_event_runner is None and self._handler_runner_is_required(CLIENT_EVENT):
                self._start_handler_runner(CLIENT_EVENT)

    @property
    def handling_client_events(self):
        """Indicate whether client events can be handled now or after a pending restart."""
        with self._handler_runner_lock:
            return (
                self._client_event_runner is not None
                or self._handler_runner_restart_tasks[CLIENT_EVENT] is not None
            )

    def _generate_callback_for_handler_runner(self, handler_name):
        """Define a callback that handles errors during handler runner execution."""

        def handler_runner_callback(completed_future):
            try:
                e = completed_future.exception(timeout=0)
            except (concurrent.futures.CancelledError, concurrent.futures.TimeoutError) as raised_e:
                e = raised_e

            if e:
                try:
                    restart_info = self._schedule_handler_runner_restart(
                        handler_name, completed_future
                    )
                except RuntimeError as scheduling_error:
                    new_err = HandlerManagerException(
                        "HANDLER RUNNER ({}): Unable to schedule handler runner restart".format(
                            handler_name
                        )
                    )
                    new_err.__cause__ = scheduling_error
                    handle_exceptions.handle_background_exception(new_err)
                    return

                if restart_info is None:
                    return

                restart_scheduled, attempt, delay = restart_info
                error_detail = str(e) or type(e).__name__
                if restart_scheduled:
                    message = (
                        "HANDLER RUNNER ({}): Unexpected error during task: {}. "
                        "Restarting in {} seconds (attempt {})"
                    ).format(handler_name, error_detail, delay, attempt)
                else:
                    message = (
                        "HANDLER RUNNER ({}): Unexpected error during task: {}. "
                        "Runner is no longer active"
                    ).format(handler_name, error_detail)

                new_err = HandlerManagerException(message)
                new_err.__cause__ = e
                handle_exceptions.handle_background_exception(new_err)
            else:
                self._reset_handler_runner_restart_attempts(handler_name)
                logger.debug(
                    "HANDLER RUNNER ({}): Task successfully completed without exception".format(
                        handler_name
                    )
                )

        return handler_runner_callback
