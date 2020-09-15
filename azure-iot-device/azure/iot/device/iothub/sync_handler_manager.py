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
    """An exception raised by a HandlerManager
    """

    pass


class HandlerRunnerKillerSentinel(object):
    """An object that functions according to the sentinel design pattern.
    Insert into an Inbox in order to indicate that the Handler Runner associated with that
    Inbox should be stopped.
    """

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
            logger.debug("Creating new handler runner for handler: {}".format(handler_name))
            setattr(self, handler_name, new_handler)
            self._start_handler_runner(handler_name)
        elif new_handler is None and curr_handler is not None:
            # Cancel runner, remove handler
            logger.debug("Removing handler runner for handler: {}".format(handler_name))
            self._stop_handler_runner(handler_name)
            setattr(self, handler_name, new_handler)
        else:
            # Update handler, no need to change runner
            logger.debug("Updating set handler: {}".format(handler_name))
            setattr(self, handler_name, new_handler)

    def stop(self):
        """Stop the process of invoking handlers in response to events.
        All pending items will be handled prior to stoppage.
        """
        for handler_name in self._handler_runners:
            if self._handler_runners[handler_name] is not None:
                self._stop_handler_runner(handler_name)

    def ensure_running(self):
        """Ensure the process of invoking handlers in response to events is running"""
        for handler_name in self._handler_runners:
            if (
                self._handler_runners[handler_name] is None
                and getattr(self, handler_name) is not None
            ):
                self._start_handler_runner(handler_name)

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

        # Run the handler in a threadpool, so that it cannot block other handlers (from a different task),
        # or the main client thread. The number of worker threads forms an upper bound on how many instances
        # of the same handler can be running simultaneously.
        tpe = concurrent.futures.ThreadPoolExecutor(max_workers=4)
        while True:
            handler_arg = inbox.get()
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
            fut = tpe.submit(handler, handler_arg)
            fut.add_done_callback(_handler_callback)

    def _event_handler_runner(self, handler_name):
        # TODO: implement
        logger.error(".event_handler_runner() not yet implemented")

    def _start_handler_runner(self, handler_name):
        """Start and store a handler runner thread
        """
        if self._handler_runners[handler_name] is not None:
            # This branch of code should NOT be reachable due to checks prior to the invocation
            # of this method. The branch exists for safety.
            raise HandlerManagerException(
                "Cannot create thread for handler runner: {}. Runner thread already exists".format(
                    handler_name
                )
            )
        inbox = self._get_inbox_for_handler(handler_name)

        # NOTE: It would be nice to have some kind of mechanism for making sure this thread
        # doesn't crash or raise errors, but it would require significant extra infrastructure
        # and an exception in here isn't supposed to happen anyway. Perhaps it could be added
        # later if truly necessary
        if inbox:
            thread = threading.Thread(target=self._inbox_handler_runner, args=[inbox, handler_name])
        else:
            thread = threading.Thread(target=self._event_handler_runner, args=[handler_name])
        thread.daemon = True  # Don't block program exit

        # Store the thread
        self._handler_runners[handler_name] = thread
        thread.start()

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
        thread = self._handler_runners[handler_name]
        thread.join()
        self._handler_runners[handler_name] = None
        logger.debug("Handler runner for {} has been stopped".format(handler_name))
