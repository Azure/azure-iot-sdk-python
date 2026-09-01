# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module contains a class representing messages that are sent or received.
"""
from datetime import date

from azure.iot.device import constant


def _encode_message_data(data):
    if isinstance(data, str):
        return data.encode("utf-8")
    if isinstance(data, (int, float)):
        return str(data).encode("ascii")
    if data is None:
        return b""
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError("Message data must be a string, bytes, bytearray, int, float, or None.")
    return data


def _get_system_properties(message):
    properties = []
    if message.output_name:
        properties.append(("$.on", str(message.output_name)))
    if message.message_id:
        properties.append(("$.mid", str(message.message_id)))
    if message.correlation_id:
        properties.append(("$.cid", str(message.correlation_id)))
    if message.user_id:
        properties.append(("$.uid", str(message.user_id)))
    if message.content_type:
        properties.append(("$.ct", str(message.content_type)))
    if message.content_encoding:
        properties.append(("$.ce", str(message.content_encoding)))
    if message.iothub_interface_id:
        properties.append(("$.ifid", str(message.iothub_interface_id)))
    if message.expiry_time_utc:
        expiry_time = (
            message.expiry_time_utc.isoformat()
            if isinstance(message.expiry_time_utc, date)
            else message.expiry_time_utc
        )
        properties.append(("$.exp", str(expiry_time)))
    return properties


def _get_custom_properties(message):
    if not message.custom_properties:
        return []

    properties = [(str(key), str(value)) for key, value in message.custom_properties.items()]
    properties.sort()

    keys = [key for key, _ in properties]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate keys in custom properties!")
    return properties


def _get_string_size(value):
    return len(value.encode("utf-8"))


class Message(object):
    """Represents a message to or from IoTHub

    :ivar data: The data that constitutes the payload
    :ivar custom_properties: Dictionary of custom message properties. The keys and values of these properties will always be string.
    :ivar message id: A user-settable identifier for the message used for request-reply patterns. Format: A case-sensitive string (up to 128 characters long) of ASCII 7-bit alphanumeric characters + {'-', ':', '.', '+', '%', '_', '#', '*', '?', '!', '(', ')', ',', '=', '@', ';', '$', '''}
    :ivar expiry_time_utc: Date and time of message expiration in UTC format
    :ivar correlation_id: A property in a response message that typically contains the message_id of the request, in request-reply patterns
    :ivar user_id: An ID to specify the origin of messages
    :ivar content_encoding: Content encoding of the message data. Can be 'utf-8', 'utf-16' or 'utf-32'
    :ivar content_type: Content type property used to route messages with the message-body. Can be 'application/json'
    :ivar output_name: Name of the output that the message is being sent to.
    :ivar input_name: Name of the input that the message was received on.
    """

    def __init__(
        self, data, message_id=None, content_encoding=None, content_type=None, output_name=None
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
        self.input_name = None
        self.ack = None
        self._iothub_interface_id = None

    @property
    def iothub_interface_id(self) -> str:
        return self._iothub_interface_id

    def set_as_security_message(self):
        """
        Set the message as a security message.

        This is a provisional API. Functionality not yet guaranteed.
        """
        self._iothub_interface_id = constant.SECURITY_MESSAGE_INTERFACE_ID

    def __str__(self):
        return str(self.data)

    def get_size(self) -> int:
        """Return the message size in bytes as measured by IoT Hub.

        The size is the encoded body plus system property values and application property names
        and values. Strings are measured as UTF-8, matching the MQTT transport; bytes and
        bytearrays are measured as-is. MQTT topic and packet overhead are not included.

        :raises TypeError: If the message data is not a payload type supported by the MQTT
            transport.
        :raises ValueError: If custom property keys are duplicated after string conversion.
        """
        payload_size = len(_encode_message_data(self.data))
        system_property_size = sum(
            _get_string_size(value) for _, value in _get_system_properties(self)
        )
        application_property_size = sum(
            _get_string_size(key) + _get_string_size(value)
            for key, value in _get_custom_properties(self)
        )
        return payload_size + system_property_size + application_property_size
