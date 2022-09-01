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

    :ivar message_inbox: The inbox for messages.
    :ivar method_request_inbox: The inbox for method requests.
    :ivar twin_patch_inbox: The inbox for twin patches.
    :ivar client_event_inbox: The inbox for client events.
    """

    def __init__(self, inbox_type):
        """Initializer for the InboxManager.

        :param inbox_type: An Inbox class that the manager will use to create Inboxes.
        """
        self._create_inbox = inbox_type
        self.message_inbox = self._create_inbox()
        self.method_request_inbox = self._create_inbox()
        self.twin_patch_inbox = self._create_inbox()
        self.client_event_inbox = self._create_inbox()

    def get_message_inbox(self):
        """Retrieve the Inbox for all messages (C2D and Input)"""
        return self.message_inbox

    def get_method_request_inbox(self):
        """Retrieve the method request Inbox for a given method name if provided,
        or for generic method requests if not.

        If the Inbox does not already exist, it will be created.

        :param str method_name: Optional. The name of the method for which the
        associated Inbox is desired.
        :returns: An Inbox for method requests.
        """
        return self.method_request_inbox

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
        self.method_request_inbox.clear()

    def route_input_message(self, incoming_message):
        """Route an incoming input message

        Route to the message inbox

        In standard mode, route to the corresponding input message Inbox. If the input
        is unknown, the message will be dropped.

        :param incoming_message: The message to be routed.

        :returns: Boolean indicating if message was successfully routed or not.
        """
        self.message_inbox.put(incoming_message)
        return True

    def route_c2d_message(self, incoming_message):
        """Route an incoming C2D message

        Route to the message inbox.

        :param incoming_message: The message to be routed.

        :returns: Boolean indicating if message was successfully routed or not.
        """
        self.message_inbox.put(incoming_message)
        return True

    def route_method_request(self, incoming_method_request):
        """Route an incoming method request to the correct method request Inbox.

        If the method name is recognized, it will be routed to a method-specific Inbox.
        Otherwise, it will be routed to the generic method request Inbox.

        :param incoming_method_request: The method request to be routed.

        :returns: Boolean indicating if the method request was successfully routed or not.
        """
        self.method_request_inbox.put(incoming_method_request)
        return True

    def route_twin_patch(self, incoming_patch):
        """Route an incoming twin patch to the twin patch Inbox.

        :param incoming_patch: The patch to be routed.

        :returns: Boolean indicating if patch was successfully routed or not.
        """
        self.twin_patch_inbox.put(incoming_patch)
        return True
