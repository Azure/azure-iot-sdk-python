# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module contains a class representing messages that are sent or received.
"""


class Message(object):
    """Represents a message to or from IoTHub

    :ivar data: The data that constitutes the payload
    :ivar custom_properties: Dictionary of custom message properties
    :ivar lock_token: Used by receiver to abandon, reject or complete the message
    :ivar message id: A user-settlable identifier for the message used for request-reply patterns. Format: A case-sensitive string (up to 128 characters long) of ASCII 7-bit alphanumeric characters + {'-', ':', '.', '+', '%', '_', '#', '*', '?', '!', '(', ')', ',', '=', '@', ';', '$', '''}
    :ivar sequence_number: A number (unique per device-queue) assigned by IoT Hub to each message
    :ivar to: A destination specified for Cloud-to-Device (C2D) messages
    :ivar expiry_time_utc: Date and time of message expiration in UTC format
    :ivar enqueued_time: Date and time a C2D message was received by IoT Hub
    :ivar correlation_id: A property in a response message that typically contains the message_id of the request, in request-reply patterns
    :ivar user_id: An ID to specify the origin of messages
    :ivar ack: A feedback message generator. This property is used in C2D messages to request IoT Hub to generate feedback messages as a result of the consumption of the message by the device
    :ivar content_encoding: Content encoding of the message data. Can be 'utf-8', 'utf-16' or 'utf-32'
    :ivar content_type: Content type property used to route messages with the message-body. Can be 'application/json'
    :ivar output_name: Name of the output that the is being sent to.
    """

    def __init__(
        self, data, message_id=None, content_encoding=None, content_type=None, output_name=None
    ):
        """
        Initializer for Message

        :param data: The  data that constitutes the payload
        :param str message_id: A user-settable identifier for the message used for request-reply patterns. Format: A case-sensitive string (up to 128 characters long) of ASCII 7-bit alphanumeric characters + {'-', ':', '.', '+', '%', '_', '#', '*', '?', '!', '(', ')', ',', '=', '@', ';', '$', '''}
        :param str content_encoding: Content encoding of the message data. Can be 'utf-8', 'utf-16' or 'utf-32'
        :param str content_type: Content type property used to routes with the message body. Can be 'application/json'
        :param str output_name: Name of the output that the is being sent to.
        """
        self.data = data
        self.custom_properties = {}
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
        self.output_name = output_name
