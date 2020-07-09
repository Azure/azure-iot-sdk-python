# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
from .auth import ConnectionStringAuthentication
from .protocol.iot_hub_gateway_service_ap_is import IotHubGatewayServiceAPIs as protocol_client


class IoTHubDigitalTwinManager(object):
    """A class to provide convenience APIs for IoTHub DigitalTwin Manager operations,
    based on top of the auto generated IotHub REST APIs
    """

    def __init__(self, connection_string):
        """Initializer for a DigitalTwin Manager Service client.

        After a successful creation the class has been authenticated with IoTHub and
        it is ready to call the member APIs to communicate with IoTHub.

        :param str connection_string: The IoTHub connection string used to authenticate connection
            with IoTHub.

        :returns: Instance of the IoTHubDigitalTwinManager object.
        :rtype: :class:`azure.iot.hub.IoTHubDigitalTwinManager`
        """
        self.auth = ConnectionStringAuthentication(connection_string)
        self.protocol = protocol_client(self.auth, "https://" + self.auth["HostName"])

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

    def invoke_component_command(self, digital_twin_id, component_path, command_name, payload):

        """Invoke a command on an component of a particular device and get the result of it.
        :param str digital_twin__id: The digital twin Id of the given device.
        :param str component_path: The component's name.
        :param str command_name: The command's name.
        :param str payload: The argument of a command.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The result of the invoked command.
        """
        return self.protocol.digital_twin.invoke_component_command1(
            digital_twin_id, component_path, command_name, payload
        )

    def invoke_command(self, digital_twin_id, command_name, payload):

        """Invoke a command on a particular device and get the result of it.
        :param str digital_twin__id: The digital twin Id of the given device.
        :param str command_name: The command's name.
        :param str payload: The argument of a command.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The result of the invoked command.
        """
        return self.protocol.digital_twin.invoke_root_level_command(
            digital_twin_id, command_name, payload
        )
