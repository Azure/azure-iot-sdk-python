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
    def __init__(self, connection_string):
        self.auth = ConnectionStringAuthentication(connection_string)
        self.protocol = protocol_client(self.auth, "https://" + self.auth["HostName"])

    def get_digital_twin(self, digital_twin_id):
        return self.protocol.digital_twin.get_interfaces(digital_twin_id)

    def get_digital_twin_interface_instance(self, digital_twin_id, interface_instance_name):
        return self.protocol.digital_twin.get_interface(digital_twin_id, interface_instance_name)

    def get_model(self, model_id):
        return self.protocol.digital_twin.get_digital_twin_model(model_id)

    def update_digital_twin(self, digital_twin_id, patch, etag):
        return self.protocol.digital_twin.update_interfaces(digital_twin_id, patch, etag)

    def update_digital_twin_property(
        self, digital_twin_id, interface_instance_name, property_name, property_value, etag
    ):
        pass

    def invoke_command(self, digital_twin_id, interface_instance_name, command_name, argument):
        return self.protocol.digital_twin.invoke_interface_command(
            digital_twin_id, interface_instance_name, command_name, argument
        )
