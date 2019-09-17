# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import os
from azure.iot.hub import DigitalTwinServiceClient

connection_str = os.getenv("IOTHUB_CONNECTION_STRING")
device_id = "<DEVICE_ID_GOES_HERE>"  # Existing device's id
interface_instance_name = (
    "<INTERFACE_INSTANCE_NAME_GOES_HERE>"
)  # for the environmental sensor, try "environmentalSensor"
model_id = "<MODEL_ID_GOES_HERE>"  # Existing model's id

try:
    # Create DigitalTwinServiceClient
    digital_twin_service_client = DigitalTwinServiceClient(connection_str)
    # Read the whole DigitalTwin
    digital_twin = digital_twin_service_client.get_digital_twin(device_id)
    print("DigitalTwin: ")
    print(digital_twin)

    # Read a particular DigitalTwinInterfaceInstance
    digital_twin_interface_instance = digital_twin_service_client.get_digital_twin_interface_instance(
        device_id, interface_instance_name
    )
    print("DigitalTwinInterfaceInstance: ")
    print(digital_twin_interface_instance)

    # Update the DigitalTwin using patch
    patch = {
        "interfaces": {
            "environmentalSensor": {"properties": {"brightness": {"desired": {"value": 42}}}}
        }
    }
    etag = "*"
    digital_twin_updated = digital_twin_service_client.update_digital_twin(device_id, patch, etag)
    print(digital_twin_updated)

    # Update DigitalTwin property by name
    property_name = "brightness"
    property_value = 84
    digital_twin_service_client.update_digital_twin_property(
        device_id, interface_instance_name, property_name, property_value
    )

    # Read a particular Model
    digital_twin_model = digital_twin_service_client.get_model(model_id)
    print("Model: ")
    print(digital_twin_model)
except Exception as ex:
    print("Unexpected error {0}".format(ex))
except KeyboardInterrupt:
    print("digital_twin_service_client_sample stopped")
