# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module contains classes related to Commands.
"""


class CommandRequest(object):
    """Represents a request to invoke a Digital Twin command.

    :ivar str request_id: The request id.
    :ivar str component_name: The name of the component with the command to be invoked.
        Set to None if the command is on the root component.
    :ivar str command_name: The name of the command to be invoked.
    :ivar dict payload: The JSON payload being sent with the request.
    """

    def __init__(self, request_id, component_name, command_name, payload):
        """Initializer for a MethodRequest.

        :param str request_id: The request id.
        :param str component_name: The name of the component with the command to be invoked.
            Set to None if the command is on the root component.
        :param str command_name: The name of the command to be invoked.
        :param dict payload: The JSON payload being sent with the request.
        """
        self._request_id = request_id
        self._component_name = component_name
        self._command_name = command_name
        self._payload = payload

    @property
    def request_id(self):
        return self._request_id

    @property
    def component_name(self):
        return self._component_name

    @property
    def command_name(self):
        return self._command_name

    @property
    def payload(self):
        return self._payload


class CommandResponse(object):
    """Represents a response to a Digital Twin command.

    :ivar str request_id: The request id of the CommandRequest being responded to.
    :ivar int status: The status of the execution of the CommandRequest.
    :ivar payload: The JSON payload to be sent with the response.
    :type payload: dict, str, int, float, bool, or None (JSON compatible values)
    """

    def __init__(self, request_id, status, payload=None):
        """Initializer for CommandResponse.

        :param str request_id: The request id of the CommandRequest being responded to.
        :param int status: The status of the execution of the CommandRequest.
        :param payload: The JSON payload to be sent with the response. (OPTIONAL)
        :type payload: dict, str, int, float, bool, or None (JSON compatible values)
        """
        self.request_id = request_id
        self.status = status
        self.payload = payload

    @classmethod
    def create_from_command_request(cls, command_request, status, payload=None):
        """Factory method for creating a CommandResopnse from a CommandRequest.

        :param command_request: The CommandRequest object to respond to.
        :type command_request: CommandRequest.
        :param int status: The status of the execution of the CommandRequest.
        :type payload: dict, str, int, float, bool, or None (JSON compatible values)
        """
        return cls(request_id=command_request.request_id, status=status, payload=payload)
