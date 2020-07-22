# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module contains the manager for handler methods used by the callback client"""

import logging
import threading
import abc
import six
from azure.iot.device.common import handle_exceptions
from azure.iot.device.common.chainable_exception import ChainableException
from azure.iot.device.iothub.sync_inbox import InboxEmpty
import concurrent.futures

logger = logging.getLogger(__name__)

MESSAGE = "_on_message_received"
METHOD = "_on_method_request_received"
TWIN_DP_PATCH = "_on_twin_desired_properties_patch_received"
# TODO: add more for "event"


class HandlerManagerException(ChainableException):
    pass


@six.add_metaclass(abc.ABCMeta)
class AbstractHandlerManager(object):
    """Partial class that defines handler manager functionality shared between sync/async"""

    def __init__(self, inbox_manager):
        self._inbox_manager = inbox_manager

        self._handler_runners = {
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

        # Other handlers
        # TODO: add

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

    @abc.abstractmethod
    def _inbox_handler_runner(self, inbox, handler_name):
        """Run infinite loop that waits for an inbox to receive an object from it, then calls
        the handler with that object
        """
        pass

    @abc.abstractmethod
    def _event_handler_runner(self, handler_name):
        pass

    @abc.abstractmethod
    def _start_handler_runner(self, handler_name):
        """Create, and store a handler runner
        """
        pass

    @abc.abstractmethod
    def _stop_handler_runner(self, handler_name):
        """Cancel and remove a handler runner"""
        pass

    def _generic_handler_setter(self, handler_name, new_handler):
        """Set a handler"""
        curr_handler = getattr(self, handler_name)
        if new_handler is not None and curr_handler is None:
            # Create runner, set handler
            logger.debug("Creating new handler task for handler: {}".format(handler_name))
            setattr(self, handler_name, new_handler)
            self._start_handler_runner(handler_name)
        elif new_handler is None and curr_handler is not None:
            # Cancel runner, remove handler
            logger.debug("Removing handler task for handler: {}".format(handler_name))
            self._stop_handler_runner(handler_name)
            setattr(self, handler_name, new_handler)
        else:
            # Update handler, no need to change runner
            logger.debug("Updating handler for handler: {}".format(handler_name))
            setattr(self, handler_name, new_handler)

    @property
    def on_message_received(self):
        return self._on_message_received

    @on_message_received.setter
    def on_message_received(self, value):
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


class SyncHandlerManager(AbstractHandlerManager):
    """Handler manager for use with synchronous clients"""

    def _inbox_handler_runner(self, inbox, handler_name):
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
        curr_thread = threading.current_thread()
        while curr_thread.keep_running:
            # Because inbox.get() is a blocking call, we have to provide a timeout, otherwise
            # it will block forever on an empty inbox, and prevent the while condition from being
            # checked, thus preventing the loop exit, thus meaning the thread this function runs in
            # will be kept alive forever, and never completed.
            try:
                handler_arg = inbox.get(timeout=10)
            except InboxEmpty:
                continue
            handler = getattr(self, handler_name)
            fut = tpe.submit(handler, handler_arg)
            fut.add_done_callback(_handler_callback)

    def _event_handler_runner(self, handler_name):
        # TODO: implement
        logger.error(".event_handler_runner() not yet implemented")

    def _start_handler_runner(self, handler_name):
        """Start and store a handler runner thread
        """
        if self._handler_runners[handler_name] is not None:
            raise HandlerManagerException(
                "Cannot create thread for handler runner: {}. Runner thread already exists".format(
                    handler_name
                )
            )
        inbox = self._get_inbox_for_handler(handler_name)

        if inbox:
            thread = threading.Thread(target=self._inbox_handler_runner, args=[inbox, handler_name])
        else:
            thread = threading.Thread(target=self._event_handler_runner, args=[handler_name])

        thread.keep_running = True
        self._handler_runners[handler_name] = thread
        thread.start()

    def _stop_handler_runner(self, handler_name):
        """Cancel and remove a handler runner thread"""
        thread = self._handler_runners[handler_name]
        thread.keep_running = False
        thread.join()
        self._handler_runners[handler_name] = None
