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
    """

    def __init__(self, inbox_type):
        """Initializer for the InboxManager.

        :param inbox_type: An Inbox class that the manager will use to create Inboxes.
        """
        self._create_inbox = inbox_type
        self.c2d_message_inbox = self._create_inbox()
        self.input_message_inboxes = {}

    def get_input_message_inbox(self, input_name):
        """Retrieve the input message Inbox for a given input.

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

    def route_input_message(self, input_name, incoming_message):
        """Route an incoming input message to the correct input message Inbox.

        If the input is unknown, the message will be dropped.

        :param str input_name: The name of the input to route the message to.
        :param incoming_message: The message to be routed.

        :returns: Boolean indicating if message was successfuly routed or not.
        """
        try:
            inbox = self.input_message_inboxes[input_name]
        except KeyError:
            logger.warning("No input message inbox for {} - dropping message".format(input_name))
            return False
        else:
            inbox._put(incoming_message)
            logger.info("Input message sent to {} inbox".format(input_name))
            return True

    def route_c2d_message(self, incoming_message):
        """Route an incoming C2D message to the C2D message Inbox.

        :param incoming_message: The message to be routed.

        :returns: Boolean indicating if message was successfully routed or not.
        """
        self.c2d_message_inbox._put(incoming_message)
        logger.info("C2D message sent to inbox")
        return True
