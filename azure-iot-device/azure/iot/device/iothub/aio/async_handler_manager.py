# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
""" This module contains the manager for handler methods used by the aio clients"""

from azure.iot.device.common import asyncio_compat
from azure.iot.device.common.chainable_exception import ChainableException
from concurrent.futures import ThreadPoolExecutor
import asyncio
import logging
import inspect

logger = logging.getLogger(__name__)

MESSAGE = "_on_message_received"
METHOD = "_on_method_request_received"
TWIN_DP_PATCH = "_on_twin_desired_properties_patch_received"
# TODO: add more for "event"


class AsyncHandlerManagerException(ChainableException):
    pass


class AsyncHandlerManager(object):
    def __init__(self, inbox_manager):
        self._inbox_manager = inbox_manager

        self._handler_tasks = {
            # Inbox handler tasks
            MESSAGE: None,
            METHOD: None,
            TWIN_DP_PATCH: None,
            # Other handler tasks
            # TODO: add
        }

        # Inbox handlers
        self._on_message_received = None
        self._on_method_request_received = None
        self._on_twin_desired_properties_patch_received = None
        # TODO: message. Should it be unique for input/C2D?
        # TODO: how are we going to handle different inputs anyway?

        # Other handlers
        # TODO: add

    async def _run_inbox_handler(self, inbox, handler_name):
        """Run infinite loop that waits for an inbox to receive an object from it, then calls
        the handler with that object
        """
        # Run the handler in a threadpool, so that it cannot block other handlers (from a different task),
        # or the main client thread. The number of worker threads forms an upper bound on how many instances
        # of the same handler can be running simultaneously.
        tp = ThreadPoolExecutor(max_workers=4)
        while True:
            retval = await inbox.get()
            # NOTE: we MUST use getattr here using the handler name, as opposed to directly passing
            # the handler in order for the handler to be able to be updated without cancelling
            # the running task created for this coroutine
            handler = getattr(self, handler_name)
            if inspect.iscoroutinefunction(handler):
                # Wrap the coroutine in a function so it can be run in ThreadPool
                def coro_wrapper(coro, arg):
                    asyncio.run(coro(arg))

                tp.submit(coro_wrapper, handler, retval)
            else:
                # Run function directly in ThreadPool
                tp.submit(handler, retval)

    async def _run_event_handler(self, handler_name):
        # TODO: implement
        logger.error("._run_event_handler() not yet implemented")

    def _get_inbox_for_handler(self, handler_name):
        """Retrieve the inbox relevant to the handler"""
        if handler_name == METHOD:
            return self._inbox_manager.get_method_request_inbox()
        elif handler_name == TWIN_DP_PATCH:
            return self._inbox_manager.get_twin_patch_inbox()
        elif handler_name == MESSAGE:
            return self._inbox_manager.get_unified_message_inbox()
        else:
            return None

    def _add_handler_task(self, handler_name):
        """Create, and store a task for running a handler
        """
        # First check if the handler task already exists
        if self._handler_tasks[handler_name] is not None:
            raise AsyncHandlerManagerException(
                "Cannot create task for handler: {}. Task already exists".format(handler_name)
            )

        inbox = self._get_inbox_for_handler(handler_name)

        if inbox:
            coro = self._run_inbox_handler(inbox, handler_name)
        else:
            coro = self._run_event_handler(handler_name)
        task = asyncio_compat.create_task(coro)
        self._handler_tasks[handler_name] = task

    def _remove_handler_task(self, handler_name):
        """Cancel and remove a task for running a handler"""
        task = self._handler_tasks[handler_name]
        task.cancel()
        self._handler_tasks[handler_name] = None

    def _generic_handler_setter(self, handler_name, new_handler):
        """Set a handler"""
        curr_handler = getattr(self, handler_name)
        if new_handler is not None and curr_handler is None:
            # Create task, set handler
            logger.debug("Creating new handler task for handler: {}".format(handler_name))
            setattr(self, handler_name, new_handler)
            self._add_handler_task(handler_name)
        elif new_handler is None and curr_handler is not None:
            # Cancel task, remove handler
            logger.debug("Removing handler task for handler: {}".format(handler_name))
            self._remove_handler_task(handler_name)
            setattr(self, handler_name, new_handler)
        else:
            # Update handler, no need to change tasks
            logger.debug("Updating handler for handler: {}".format(handler_name))
            setattr(self, handler_name, new_handler)

    @property
    def on_message_received(self):
        return self._on_message_received

    @on_message_received.setter
    def on_c2d_message_received(self, value):
        self._generic_handler_setter(MESSAGE, value)

    @property
    def on_method_request_received(self):
        return self._on_method_request_received

    @on_method_request_received.setter
    def on_method_request_received(self, value):
        self._generic_handler_setter(METHOD, value)

    @property
    def on_twin_desired_properties_patch_received(self):
        return self._on_twin_desired_properties_patch_received

    @on_twin_desired_properties_patch_received.setter
    def on_twin_desired_properties_patch_received(self, value):
        self._generic_handler_setter(TWIN_DP_PATCH, value)
