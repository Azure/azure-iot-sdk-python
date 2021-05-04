# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
from .auth import ConnectionStringAuthentication, AzureIdentityCredentialAdapter
from .protocol.iot_hub_gateway_service_ap_is import IotHubGatewayServiceAPIs as protocol_client


class DigitalTwinClient(object):
    """A class to provide convenience APIs for DigitalTwin operations,
    based on top of the auto generated IotHub REST APIs
    """

    def __init__(self, connection_string=None, host=None, auth=None):
        """Initializer for a DigitalTwinClient.

        After a successful creation the class has been authenticated with IoTHub and
        it is ready to call the member APIs to communicate with IoTHub.

        :param str connection_string: The IoTHub connection string used to authenticate connection
            with IoTHub if we are using connection_str authentication. Default value: None
        :param str host: The Azure service url if we are using token credential authentication.
            Default value: None
        :param str auth: The Azure authentication object if we are using token credential authentication.
            Default value: None

        :returns: Instance of the DigitalTwinClient object.
        :rtype: :class:`azure.iot.hub.DigitalTwinClient`
        """
        if connection_string is not None:
            self.auth = ConnectionStringAuthentication(connection_string)
            self.protocol = protocol_client(self.auth, "https://" + self.auth["HostName"])
        else:
            self.auth = auth
            self.protocol = protocol_client(self.auth, "https://" + host)

    @classmethod
    def from_connection_string(cls, connection_string):
        """Classmethod initializer for a DigitalTwinClient Service client.
        Creates DigitalTwinClient class from connection string.

        After a successful creation the class has been authenticated with IoTHub and
        it is ready to call the member APIs to communicate with IoTHub.

        :param str connection_string: The IoTHub connection string used to authenticate connection
            with IoTHub.

        :rtype: :class:`azure.iot.hub.DigitalTwinClient`
        """
        return cls(connection_string=connection_string)

    @classmethod
    def from_token_credential(cls, url, token_credential):
        """Classmethod initializer for a DigitalTwinClient Service client.
        Creates DigitalTwinClient class from host name url and Azure token credential.

        After a successful creation the class has been authenticated with IoTHub and
        it is ready to call the member APIs to communicate with IoTHub.

        :param str url: The Azure service url (host name).
        :param str token_credential: The Azure token credential object.

        :rtype: :class:`azure.iot.hub.DigitalTwinClient`
        """
        host = url
        auth = AzureIdentityCredentialAdapter(token_credential)
        return cls(host=host, auth=auth)

    def get_digital_twin(self, digital_twin_id):
        """Retrieve the Digital Twin of a given device.
        :param str digital_twin__id: The digital twin Id of the given device.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The return object containing the Digital Twin.
        """

        return self.protocol.digital_twin.get_digital_twin(digital_twin_id)

    def update_digital_twin(self, digital_twin_id, digital_twin_patch, etag=None):
        """Update the Digital Twin Component of a given device using a patch object.
        :param str digital_twin__id: The digital twin Id of the given device.
        :param list[object]: The json-patch object to update the Digital Twin.
        :param str etag: The etag (if_match) value to use for the update operation.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The return object containing the updated Digital Twin.
        """

        return self.protocol.digital_twin.update_digital_twin(
            digital_twin_id, digital_twin_patch, etag
        )

    def invoke_component_command(
        self,
        digital_twin_id,
        component_path,
        command_name,
        payload,
        connect_timeout_in_seconds=None,
        response_timeout_in_seconds=None,
    ):

        """Invoke a command on an component of a particular device and get the result of it.
        :param str digital_twin__id: The digital twin Id of the given device.
        :param str component_path: The component's name.
        :param str command_name: The command's name.
        :param str payload: The argument of a command.
        :param int connect_timeout_in_seconds: Maximum interval of time, in seconds, that the digital twin command will wait for the answer.
        :param int response_timeout_in_seconds: Maximum interval of time, in seconds, that the digital twin command will wait for the response. The value must be within 5-300.
        :type response_timeout_in_seconds: int

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The result of the invoked command.
        """
        return self.protocol.digital_twin.invoke_component_command(
            digital_twin_id,
            component_path,
            command_name,
            payload,
            connect_timeout_in_seconds,
            response_timeout_in_seconds,
        )

    def invoke_command(
        self,
        digital_twin_id,
        command_name,
        payload,
        connect_timeout_in_seconds=None,
        response_timeout_in_seconds=None,
    ):

        """Invoke a command on a particular device and get the result of it.
        :param str digital_twin__id: The digital twin Id of the given device.
        :param str command_name: The command's name.
        :param str payload: The argument of a command.
        :param int connect_timeout_in_seconds: Maximum interval of time, in seconds, that the digital twin command will wait for the answer.
        :param int response_timeout_in_seconds: Maximum interval of time, in seconds, that the digital twin command will wait for the response. The value must be within 5-300.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The result of the invoked command.
        """
        return self.protocol.digital_twin.invoke_root_level_command(
            digital_twin_id,
            command_name,
            payload,
            connect_timeout_in_seconds,
            response_timeout_in_seconds,
        )
