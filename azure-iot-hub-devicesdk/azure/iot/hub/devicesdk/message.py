# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

import logging

logger = logging.getLogger(__name__)


class Message(object):
    def __init__(self, data, message_id=None, content_encoding=None, content_type=None):
        """
        :param data: The  data that constitutes the payload
        :param message_id: A user-settable identifier for the message used for request-reply patterns.Format: A case-sensitive string (up to 128 characters long) of ASCII 7-bit alphanumeric characters + {'-', ':', '.', '+', '%', '_', '#', '*', '?', '!', '(', ')', ',', '=', '@', ';', '$', '''}.
        :param content_encoding: Content encoding of the message data. Can be 'utf-8', 'utf-16' or 'utf-32'.
        :param content_type: Content type property used to routes with the message body. Can be 'application/json'.
        """
        self.data = data
        self.custom_properties = dict()
        self.lock_token = None
        self.message_id = message_id
        self.sequence_number = None
        self.to = None
        self.expiry_time_utc = None
        self.enqueued_time = None
        self.correlation_id = None
        self.user_id = None
        self.ack = None
        self.content_encoding = content_encoding
        self.content_type = content_type
        self.output_name = None
