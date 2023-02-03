# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import sys
from typing import Optional, Dict
from .custom_typing import JSONSerializable
from . import constant

# TODO: json docs


class Message:
    """Represents a message to or from IoTHub

    :ivar payload: The data that constitutes the payload
    :ivar message id: A user-settable identifier for the message used for request-reply patterns. Format: A case-sensitive string (up to 128 characters long) of ASCII 7-bit alphanumeric characters + {'-', ':', '.', '+', '%', '_', '#', '*', '?', '!', '(', ')', ',', '=', '@', ';', '$', '''}
    :ivar content_encoding: Content encoding of the message data. Can be 'utf-8', 'utf-16' or 'utf-32'
    :ivar content_type: Content type property used to route messages with the message-body. Can be 'application/json'
    :ivar custom_properties: Dictionary of custom message properties. The keys and values of these properties will always be string.
    :ivar output_name: Name of the output that the message is being sent to.
    :ivar input_name: Name of the input that the message was received on.
    :ivar ack: Indicates the type of feedback generation used by IoTHub
    :ivar expiry_time_utc: Date and time of message expiration in UTC format
    :ivar user_id: An ID to specify the origin of messages
    :ivar correlation_id: A property in a response message that typically contains the message_id of the request, in request-reply patterns
    """

    def __init__(
        self,
        payload: JSONSerializable,
        message_id: Optional[str] = None,
        content_encoding: Optional[str] = None,
        content_type: Optional[str] = None,
        output_name: Optional[str] = None,
    ) -> None:
        """
        Initializer for Message

        :param data: The JSON serializable data that constitutes the payload
        :param str message_id: A user-settable identifier for the message used for request-reply patterns. Format: A case-sensitive string (up to 128 characters long) of ASCII 7-bit alphanumeric characters + {'-', ':', '.', '+', '%', '_', '#', '*', '?', '!', '(', ')', ',', '=', '@', ';', '$', '''}
        :param str content_encoding: Content encoding of the message data. Other values can be utf-16' or 'utf-32'
        :param str content_type: Content type property used to routes with the message body.
        :param str output_name: Name of the output that the is being sent to.
        """
        # All Messages
        self.payload = payload
        self.message_id = message_id
        self.content_encoding = content_encoding
        self.content_type = content_type  # TODO: is this supposed to have a default?
        self.custom_properties: Dict[str, str] = {}

        # D2C Messages
        self.output_name = output_name

        # C2D Messages
        # NOTE: These are not settable via the __init__ since the end user does not create
        # C2D Messages, they are only created internally
        self.input_name: Optional[str] = None
        self.ack: Optional[str] = None
        self.expiry_time_utc: Optional[str] = None
        self.user_id: Optional[str] = None
        self.correlation_id: Optional[str] = None

        # Internal
        self._iothub_interface_id: Optional[str] = None

    @property
    def iothub_interface_id(self):
        return self._iothub_interface_id

    def set_as_security_message(self) -> None:
        """
        Set the message as a security message.
        """
        self._iothub_interface_id = constant.SECURITY_MESSAGE_INTERFACE_ID

    def __str__(self) -> str:
        return str(self.payload)

    def get_size(self) -> int:
        # TODO: this isn't actually accurate for what we use it for.
        # Should we just remove it?
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


class MethodRequest:
    """Represents a request to invoke a direct method.

    :ivar str request_id: The request id.
    :ivar str name: The name of the method to be invoked.
    :ivar dict payload: The JSON payload being sent with the request.
    :type payload: dict, str, int, float, bool, or None (JSON compatible values)
    """

    def __init__(self, request_id: str, name: str, payload: JSONSerializable) -> None:
        """Initializer for a MethodRequest.

        :param str request_id: The request id.
        :param str name: The name of the method to be invoked
        :param payload: The JSON payload being sent with the request.
        :type payload: dict, str, int, float, bool, or None (JSON compatible values)
        """
        self.request_id = request_id
        self.name = name
        self.payload = payload


class MethodResponse:
    """Represents a response to a direct method.

    :ivar str request_id: The request id of the MethodRequest being responded to.
    :ivar int status: The status of the execution of the MethodRequest.
    :ivar payload: The JSON payload to be sent with the response.
    :type payload: dict, str, int, float, bool, or None (JSON compatible values)
    """

    def __init__(self, request_id: str, status: int, payload: JSONSerializable = None) -> None:
        """Initializer for MethodResponse.

        :param str request_id: The request id of the MethodRequest being responded to.
        :param int status: The status of the execution of the MethodRequest.
        :param payload: The JSON payload to be sent with the response. (OPTIONAL)
        :type payload: dict, str, int, float, bool, or None (JSON compatible values)
        """
        self.request_id = request_id
        self.status = status
        self.payload = payload

    @classmethod
    def create_from_method_request(
        cls, method_request: MethodRequest, status: int, payload: JSONSerializable = None
    ):
        """Factory method for creating a MethodResponse from a MethodRequest.

        :param method_request: The MethodRequest object to respond to.
        :type method_request: MethodRequest.
        :param int status: The status of the execution of the MethodRequest.
        :type payload: dict, str, int, float, bool, or None (JSON compatible values)
        """
        return cls(request_id=method_request.request_id, status=status, payload=payload)
