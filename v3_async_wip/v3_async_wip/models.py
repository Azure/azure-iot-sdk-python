# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
from typing import Optional, Dict, Union
from .custom_typing import JSONSerializable
from . import constant

# TODO: Should Message property dictionaries be TypeDicts?


class Message:
    """Represents a message to or from IoTHub

    :ivar payload: The data that constitutes the payload
    :ivar content_encoding: Content encoding of the message data. Can be 'utf-8', 'utf-16' or 'utf-32'
    :ivar content_type: Content type property used to route messages with the message-body. Can be 'application/json'
    :ivar message id: A user-settable identifier for the message used for request-reply patterns. Format: A case-sensitive string (up to 128 characters long) of ASCII 7-bit alphanumeric characters + {'-', ':', '.', '+', '%', '_', '#', '*', '?', '!', '(', ')', ',', '=', '@', ';', '$', '''}
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
        payload: Union[str, JSONSerializable],
        content_encoding: str = "utf-8",
        content_type: str = "text/plain",
        output_name: Optional[str] = None,
    ) -> None:
        """
        Initializer for Message

        :param payload: The JSON serializable data that constitutes the payload.
        :param str content_encoding: Content encoding of the message payload.
            Acceptable values are 'utf-8', 'utf-16' and 'utf-32'
        :param str content_type: Content type of the message payload.
            Acceptable values are 'text/plain' and 'application/json'
        :param str output_name: Name of the output that the message is being sent to.
        """
        # Sanitize
        if content_encoding not in ["utf-8", "utf-16", "utf-32"]:
            raise ValueError(
                "Invalid content encoding. Supported codecs are 'utf-8', 'utf-16' and 'utf-32'"
            )
        if content_type not in ["text/plain", "application/json"]:
            raise ValueError(
                "Invalid content type. Supported types are 'text/plain' and 'application/json'"
            )

        # All Messages
        self.payload = payload
        self.content_encoding = content_encoding
        self.content_type = content_type
        self.message_id: Optional[str] = None
        self.custom_properties: Dict[str, str] = {}

        # Outgoing Messages (D2C/Output)
        self.output_name = output_name
        self._iothub_interface_id: Optional[str] = None

        # Incoming Messages (C2D/Input)
        # NOTE: These are not settable via the __init__ since the end user does not create
        # C2D Messages, they are only created internally
        self.input_name: Optional[str] = None
        self.ack: Optional[str] = None
        self.expiry_time_utc: Optional[str] = None
        self.user_id: Optional[str] = None
        self.correlation_id: Optional[str] = None

    def __str__(self) -> str:
        return str(self.payload)

    @property
    def iothub_interface_id(self):
        return self._iothub_interface_id

    def set_as_security_message(self) -> None:
        """
        Set the message as a security message.
        """
        self._iothub_interface_id = constant.SECURITY_MESSAGE_INTERFACE_ID

    def get_system_properties_dict(self) -> Dict[str, str]:
        """Return a dictionary of system properties"""
        d = {}
        # All messages
        if self.message_id:
            d["$.mid"] = self.message_id
        if self.content_encoding:
            d["$.ce"] = self.content_encoding
        if self.content_type:
            d["$.ct"] = self.content_type
        # Outgoing Messages (D2C/Output)
        if self.output_name:
            d["$.on"] = self.output_name
        if self._iothub_interface_id:
            d["$.ifid"] = self._iothub_interface_id
        # Incoming Messages (C2D/Input)
        if self.input_name:
            d["$.to"] = self.input_name
        if self.ack:
            d["iothub-ack"] = self.ack
        if self.expiry_time_utc:
            d["$.exp"] = self.expiry_time_utc
        if self.user_id:
            d["$.uid"] = self.user_id
        if self.correlation_id:
            d["$.cid"] = self.correlation_id
        return d

    @classmethod
    # TODO: should this just replace the __init__?
    def create_from_properties_dict(
        cls, payload: JSONSerializable, properties: Dict[str, str]
    ) -> "Message":
        message = cls(payload)

        for key in properties:
            # All messages
            if key == "$.mid":
                message.message_id = properties[key]
            elif key == "$.ce":
                message.content_encoding = properties[key]
            elif key == "$.ct":
                message.content_type = properties[key]
            # Outgoing Messages (D2C/Output)
            elif key == "$.on":
                message.output_name = properties[key]
            elif key == "$.ifid":
                message._iothub_interface_id = properties[key]
            # Incoming Messages (C2D/Input)
            elif key == "$.to":
                message.input_name = properties[key]
            elif key == "iothub-ack":
                message.ack = properties[key]
            elif key == "$.exp":
                message.expiry_time_utc = properties[key]
            elif key == "$.uid":
                message.user_id = properties[key]
            elif key == "$.cid":
                message.correlation_id = properties[key]
            else:
                message.custom_properties[key] = properties[key]

        return message


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
