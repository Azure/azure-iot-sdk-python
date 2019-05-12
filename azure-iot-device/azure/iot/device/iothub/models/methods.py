# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module contains classes related to direct method invocations.
"""


class MethodRequest(object):
    """Represents a request to invoke a direct method.

    :ivar str request_id: The request id.
    :ivar str name: The name of the method to be invoked.
    :ivar dict payload: The JSON payload being sent with the request.
    """

    def __init__(self, request_id, name, payload):
        """Initializer for a MethodRequest.

        :param str request_id: The request id.
        :param str name: The name of the method to be invoked
        :param dict payload: The JSON payload being sent with the request.
        """
        self._request_id = request_id
        self._name = name
        self._payload = payload

    @property
    def request_id(self):
        return self._request_id

    @property
    def name(self):
        return self._name

    @property
    def payload(self):
        return self._payload


class MethodResponse(object):
    """Represents a response to a direct method.

    :ivar str request_id: The request id of the MethodRequest being responded to.
    :ivar int status: The status of the execution of the MethodRequest.
    :ivar payload: The JSON payload to be sent with the response.
    :type payload: dict, str, int, float, bool, or None (JSON compatible values)
    """

    def __init__(self, request_id, status, payload=None):
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
    def create_from_method_request(cls, method_request, status, payload=None):
        """Factory method for creating a MethodResponse from a MethodRequest.

        :param method_request: The MethodRequest object to respond to.
        :type method_request: MethodRequest.
        :param int status: The status of the execution of the MethodRequest.
        :type payload: dict, str, int, float, bool, or None (JSON compatible values)
        """
        return cls(request_id=method_request.request_id, status=status, payload=payload)
