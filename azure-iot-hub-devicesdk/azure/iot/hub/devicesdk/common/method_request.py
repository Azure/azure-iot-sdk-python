# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module contains a class representing a request to invoke a direct method.
"""


class MethodRequest(object):
    """Represents a request to invoke a direct method.

    :ivar str name: The name of the method to be invoked
    :ivar payload: The payload being sent with the request.
    """

    def __init__(self, request_id, name, payload):
        """Initializer for a MethodRequest.

        :param str request_id: The request id of the request.
        :param str name: The name of the method to be invoked
        :param payload: The payload being sent with the request.
        """
        self._request_id = request_id
        self._name = name
        self._payload = payload

    @property
    def name(self):
        return self._name

    @property
    def payload(self):
        return self._payload
