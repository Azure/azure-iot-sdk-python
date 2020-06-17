# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
""" This module contains the manager for handler methods used by the aio clients"""

from azure.iot.device.common import asyncio_compat
from azure.iot.device.common.chainable_exception import ChainableException
import logging
import inspect

logger = logging.getLogger(__name__)

METHOD = "method"
BACKGROUND_EXCEPTION = "background_exception"


class AsyncHandlerManagerException(ChainableException):
    pass


class AsyncHandlerManager(object):
    def __init__(self, inbox_manager):
        self._inbox_manager = inbox_manager

        # loop = asyncio_compat.get_running_loop()

        self._handler_tasks = {METHOD: None, BACKGROUND_EXCEPTION: None}

        # Inbox handlers
        self._on_method_request_received = None
        self._on_twin_desired_properties_patch_received = None
        # TODO: message. Should it be unique for input/C2D?
        # TODO: how are we going to handle different inputs anyway?

        # Other handlers
        # TODO: connection state change or unique connect/disconnect handlers?
        self._on_background_exception = None
        # self._on_sastoken_needs_renew = None

    async def _run_inbox_handler(self, inbox, handler_name):
        while True:
            retval = await inbox.get()
            handler = getattr(self, handler_name)
            if inspect.iscoroutinefunction(handler):
                # TODO: should this await or just schedule?
                await handler(retval)
            else:
                handler(retval)

    async def _run_event_handler(self, handler_name):
        # TODO: how does this work?
        pass

    def _get_inbox_for_handler(self, handler_type):
        if handler_type == METHOD:
            return self._inbox_manager.get_method_request_inbox()
        else:
            return None

    def _get_handler_name(self, handler_type):
        # TODO: this is weird
        if handler_type == METHOD:
            return "on_method_request_received"
        else:
            # This code block should never be reached
            raise AsyncHandlerManagerException(
                "Cannot retrieve handler for type: {}. Handler type does not exist".format(
                    handler_type
                )
            )

    def _add_handler_task(self, handler_type):
        # First check if the handler task already exists
        if self._handler_tasks[handler_type] is not None:
            raise AsyncHandlerManagerException(
                "Cannot create task for handler type: {}. Task already exists".format(handler_type)
            )

        handler_name = self._get_handler_name(handler_type)
        inbox = self._get_inbox_for_handler(handler_type)

        if inbox:
            coro = self._run_inbox_handler(inbox, handler_name)
        else:
            coro = self._run_event_handler(handler_name)
        task = asyncio_compat.create_task(coro)
        self._handler_tasks[handler_type] = task

    def _remove_handler_task(self, handler_type):
        task = self._handler_tasks[handler_type]
        task.cancel()
        self._handler_tasks[handler_type] = None

    # def _handler_setter(self, handler_type):
    #     if value is not None and self._on_method_request_received is None:
    #         # Create task, set handler
    #         logger.debug("Creating new handler task for handler type: {}".format(handler_type))
    #         self._on_method_request_received = value
    #         self._add_handler_task(handler_type)
    #     elif value is None and self._on_method_request_received is not None:
    #         # Cancel task, remove handler
    #         logger.debug("Removing handler task for handler type: {}".format(handler_type))
    #         self._remove_handler_task(handler_type)
    #         self._on_method_request_received = value
    #     else:
    #         # Update handler, no need to change tasks
    #         logger.debug("Updating handler for handler type: {}".format(handler_type))
    #         self._on_method_request_received = value

    @property
    def on_method_request_received(self):
        return self._on_method_request_received

    # TODO: make this more generic
    @on_method_request_received.setter
    def on_method_request_received(self, value):
        if value is not None and self._on_method_request_received is None:
            # Create task, set handler
            logger.debug("Creating new handler task for handler type: {}".format(METHOD))
            self._on_method_request_received = value
            self._add_handler_task(METHOD)
        elif value is None and self._on_method_request_received is not None:
            # Cancel task, remove handler
            logger.debug("Removing handler task for handler type: {}".format(METHOD))
            self._remove_handler_task(METHOD)
            self._on_method_request_received = value
        else:
            # Update handler, no need to change tasks
            logger.debug("Updating handler for handler type: {}".format(METHOD))
            self._on_method_request_received = value

    @property
    def on_twin_desired_properties_patch_received(self):
        return self._on_twin_desired_properties_patch_received

    @on_twin_desired_properties_patch_received.setter
    def on_twin_desired_properties_patch_received(self, value):
        pass

    @property
    def on_background_exception(self):
        return self._on_background_exception

    @on_background_exception.setter
    def on_background_exception(self, value):
        pass
