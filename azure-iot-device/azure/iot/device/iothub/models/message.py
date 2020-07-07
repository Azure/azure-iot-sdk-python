# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module contains a class representing messages that are sent or received.
"""
from azure.iot.device import constant
import sys


class Message(object):
    """Represents a message to or from IoTHub

    :ivar data: The data that constitutes the payload
    :ivar custom_properties: Dictionary of custom message properties
    :ivar message id: A user-settable identifier for the message used for request-reply patterns. Format: A case-sensitive string (up to 128 characters long) of ASCII 7-bit alphanumeric characters + {'-', ':', '.', '+', '%', '_', '#', '*', '?', '!', '(', ')', ',', '=', '@', ';', '$', '''}
    :ivar expiry_time_utc: Date and time of message expiration in UTC format
    :ivar correlation_id: A property in a response message that typically contains the message_id of the request, in request-reply patterns
    :ivar user_id: An ID to specify the origin of messages
    :ivar content_encoding: Content encoding of the message data. Can be 'utf-8', 'utf-16' or 'utf-32'
    :ivar content_type: Content type property used to route messages with the message-body. Can be 'application/json'
    :ivar output_name: Name of the output that the is being sent to.
    """

    def __init__(
        self,
        data,
        message_id=None,
        content_encoding=None,
        content_type=None,
        output_name=None,
        input_name=None,
    ):
        """
        Initializer for Message

        :param data: The  data that constitutes the payload
        :param str message_id: A user-settable identifier for the message used for request-reply patterns. Format: A case-sensitive string (up to 128 characters long) of ASCII 7-bit alphanumeric characters + {'-', ':', '.', '+', '%', '_', '#', '*', '?', '!', '(', ')', ',', '=', '@', ';', '$', '''}
        :param str content_encoding: Content encoding of the message data. Other values can be utf-16' or 'utf-32'
        :param str content_type: Content type property used to routes with the message body.
        :param str output_name: Name of the output that the is being sent to.
        """
        self.data = data
        self.custom_properties = {}
        self.message_id = message_id
        self.expiry_time_utc = None
        self.correlation_id = None
        self.user_id = None
        self.content_encoding = content_encoding
        self.content_type = content_type
        self.output_name = output_name
        self.input_name = input_name  # TODO: could these two fields be combined?
        self._iothub_interface_id = None

    @property
    def iothub_interface_id(self):
        return self._iothub_interface_id

    def set_as_security_message(self):
        """
        Set the message as a security message.

        This is a provisional API. Functionality not yet guaranteed.
        """
        self._iothub_interface_id = constant.SECURITY_MESSAGE_INTERFACE_ID

    def __str__(self):
        return str(self.data)

    def get_size(self):
        total = 0
        total = total + sum(
            sys.getsizeof(v)
            for v in self.__dict__.values()
            if v is not None and v is not self.custom_properties
        )
        if self.custom_properties:
            total = total + sum(
                sys.getsizeof(v) for v in self.custom_properties.values() if v is not None
            )
        return total
