# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module contains a manager for inboxes."""

import logging

logger = logging.getLogger(__name__)


class InboxManager(object):
    """Manages the various Inboxes for a client.

    :ivar c2d_message_inbox: The C2D message Inbox.
    :ivar input_message_inboxes: A dictionary mapping input names to input message Inboxes.
    :ivar generic_method_request_inbox: The generic method request Inbox.
    :ivar named_method_request_inboxes: A dictionary mapping method names to method request Inboxes.
    """

    def __init__(self, inbox_type):
        """Initializer for the InboxManager.

        :param inbox_type: An Inbox class that the manager will use to create Inboxes.
        """
        self._create_inbox = inbox_type
        self.unified_message_inbox = self._create_inbox()
        self.generic_method_request_inbox = self._create_inbox()
        self.twin_patch_inbox = self._create_inbox()
        self.client_event_inbox = self._create_inbox()

        # These inboxes are used only for non-unified receives, using APIs which are now
        # deprecated on the client. However we need to keep them functional for backwards
        # compatibility
        self.c2d_message_inbox = self._create_inbox()
        self.input_message_inboxes = {}
        self.named_method_request_inboxes = {}

        # Set this value to True if want to only use unified message mode
        self.use_unified_msg_mode = False

    def get_unified_message_inbox(self):
        """Retrieve the Inbox for all messages (C2D and Input)"""
        return self.unified_message_inbox

    def get_input_message_inbox(self, input_name):
        """Retrieve the input message Inbox for a given input.

        If the Inbox does not already exist, it will be created.

        :param str input_name: The name of the input for which the associated Inbox is desired.
        :returns: An Inbox for input messages on the selected input.
        """
        try:
            inbox = self.input_message_inboxes[input_name]
        except KeyError:
            # Create new Inbox for input if it does not yet exist
            inbox = self._create_inbox()
            self.input_message_inboxes[input_name] = inbox

        return inbox

    def get_c2d_message_inbox(self):
        """Retrieve the Inbox for C2D messages.

        :returns: An Inbox for C2D messages.
        """
        return self.c2d_message_inbox

    def get_method_request_inbox(self, method_name=None):
        """Retrieve the method request Inbox for a given method name if provided,
        or for generic method requests if not.

        If the Inbox does not already exist, it will be created.

        :param str method_name: Optional. The name of the method for which the
        associated Inbox is desired.
        :returns: An Inbox for method requests.
        """
        if method_name:
            try:
                inbox = self.named_method_request_inboxes[method_name]
            except KeyError:
                # Create a new Inbox for the method name
                inbox = self._create_inbox()
                self.named_method_request_inboxes[method_name] = inbox
        else:
            inbox = self.generic_method_request_inbox

        return inbox

    def get_twin_patch_inbox(self):
        """Retrieve the Inbox for twin patches that arrive from the service

        :returns: An Inbox for twin patches
        """
        return self.twin_patch_inbox

    def get_client_event_inbox(self):
        """Retrieve the Inbox for events that occur within the client

        :returns: An Inbox for client events
        """
        return self.client_event_inbox

    def clear_all_method_requests(self):
        """Delete all method requests currently in inboxes."""
        self.generic_method_request_inbox.clear()
        for inbox in self.named_method_request_inboxes.values():
            inbox.clear()

    def route_input_message(self, incoming_message):
        """Route an incoming input message

        In unified message mode, route to the unified message inbox

        In standard mode, route to the corresponding input message Inbox. If the input
        is unknown, the message will be dropped.

        :param incoming_message: The message to be routed.

        :returns: Boolean indicating if message was successfully routed or not.
        """
        input_name = incoming_message.input_name
        if self.use_unified_msg_mode:
            # Put in the unified message inbox if in simplified mode
            self.unified_message_inbox.put(incoming_message)
            return True
        else:
            # If not in simplified mode, get a specific inbox for the input
            try:
                inbox = self.input_message_inboxes[input_name]
            except KeyError:
                logger.warning(
                    "No input message inbox for {} - dropping message".format(input_name)
                )
                return False
            else:
                inbox.put(incoming_message)
                logger.debug("Input message sent to {} inbox".format(input_name))
                return True

    def route_c2d_message(self, incoming_message):
        """Route an incoming C2D message

        In unified message mode, route to the unified message inbox.

        In standard mode, route to to the C2D message Inbox.

        :param incoming_message: The message to be routed.

        :returns: Boolean indicating if message was successfully routed or not.
        """
        if self.use_unified_msg_mode:
            # Put in the unified message inbox if in simplified mode
            self.unified_message_inbox.put(incoming_message)
            return True
        else:
            self.c2d_message_inbox.put(incoming_message)
            logger.debug("C2D message sent to inbox")
            return True

    def route_method_request(self, incoming_method_request):
        """Route an incoming method request to the correct method request Inbox.

        If the method name is recognized, it will be routed to a method-specific Inbox.
        Otherwise, it will be routed to the generic method request Inbox.

        :param incoming_method_request: The method request to be routed.

        :returns: Boolean indicating if the method request was successfully routed or not.
        """
        try:
            inbox = self.named_method_request_inboxes[incoming_method_request.name]
        except KeyError:
            inbox = self.generic_method_request_inbox
        inbox.put(incoming_method_request)
        return True

    def route_twin_patch(self, incoming_patch):
        """Route an incoming twin patch to the twin patch Inbox.

        :param incoming_patch: The patch to be routed.

        :returns: Boolean indicating if patch was successfully routed or not.
        """
        self.twin_patch_inbox.put(incoming_patch)
        logger.debug("twin patch message sent to inbox")
        return True
