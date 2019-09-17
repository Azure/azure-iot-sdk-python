# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

from .auth import ConnectionStringAuthentication

from .protocol.iot_hub_gateway_service_ap_is20190701_preview import (
    IotHubGatewayServiceAPIs20190701Preview as protocol_client,
)
from .protocol.models import DigitalTwinInterfaces as DigitalTwin
from .protocol.models import DigitalTwinInterfacesPatch as DigitalTwinPatch


class DigitalTwinServiceClient(object):
    """A class to provide convenience APIs for IoTHub Digital Twin operations,
    based on top of the auto generated IotHub REST APIs
    """

    def __init__(self, connection_string):
        """Initializer for a Digital Twin Service client.

        After a successful creation the class has been authenticated with IoTHub and
        it is ready to call the member APIs to communicate with IoTHub.

        :param: str connection_string: The authentication information
        (IoTHub connection string) to connect to IoTHub.

        :returns: DigitalTwinServiceClient object.
        """
        self.auth = ConnectionStringAuthentication(connection_string)
        self.protocol = protocol_client(self.auth, "https://" + self.auth["HostName"])

    def get_digital_twin(self, digital_twin_id):
        """Retrieves the full Digital Twin object.

        It reads the whole Digital Twin object of a given device.

        :param str digital_twin_id: The name (deviceId) of the device.

        :raises: HttpOperationError if the HTTP response status is not in [200].

        :returns: DigitalTwin object representing the given device.
        """
        return self.protocol.digital_twin.get_interfaces(digital_twin_id)

    def get_digital_twin_interface_instance(self, digital_twin_id, interface_instance_name):
        """Retrieves one of the interface instance implemented by the given device

        :param str digital_twin_id: The name (deviceId) of the device.
        :param str interface_instance_name: THe name of the interface instance to get.

        :raises: HttpOperationError if the HTTP response status is not in [200].

        :returns: DigitalTwin object containing the requested interface instance.
        """
        return self.protocol.digital_twin.get_interface(digital_twin_id, interface_instance_name)

    def get_model(self, model_id):
        """Retrieves a model by model ID.

        :param str model_id: THe ID of the requested Model.

        :raises: HttpOperationError if the HTTP response status is not in [200].

        :returns: Object containing the requested Model.
        """
        return self.protocol.digital_twin.get_digital_twin_model(model_id)

    def update_digital_twin(self, digital_twin_id, patch, etag):
        """Updates the Digital Twin of a given device using a differential patch.

        :param str digital_twin_id: The name (deviceId) of the device.
        :param str patch: JSON formatted string containing the patch.
        :param str etag: The etag (if_match) value to use for the update operation.

        :raises: HttpOperationError if the HTTP response status is not in [200].

        :returns: The updated Digital Twin object.
        """
        return self.protocol.digital_twin.update_interfaces(digital_twin_id, patch, etag)

    def update_digital_twin_property(
        self, digital_twin_id, interface_instance_name, property_name, property_value, etag
    ):
        """Updates a given property's value in a particular interface instance.

        :param str digital_twin_id: The name (deviceId) of the device.
        :param str interface_instance_name: THe name of the interface instance to update.
        :param str property_name: The name of the property to update.
        :param str property_value: The property's value to update.
        :param str etag: The etag (if_match) value to use for the update operation.

        :raises: HttpOperationError if the HTTP response status is not in [200].

        :returns: The updated Digital Twin object.
        """

        pass

    def invoke_command(self, digital_twin_id, interface_instance_name, command_name, argument):
        """Invokes a command on a particular interface instance.

        :param str digital_twin_id: The name (deviceId) of the device.
        :param str interface_instance_name: THe name of the interface instance to update.
        :param str command_name: The name of the command to invoke.
        :param str argument: The argument to invoke the command with.

        :raises: HttpOperationError if the HTTP response status is not in [200].

        :returns: The response object.
        """
        return self.protocol.digital_twin.invoke_interface_command(
            digital_twin_id, interface_instance_name, command_name, argument
        )
