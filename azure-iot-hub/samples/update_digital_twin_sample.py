# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import sys
import os
import msrest
from azure.iot.hub import IoTHubDigitalTwinManager, IoTHubRegistryManager


iothub_connection_str = os.getenv("IOTHUB_CONNECTION_STRING")
device_id = os.getenv("IOTHUB_DEVICE_ID")

try:
    # Create IoTHubDigitalTwinManager
    iothub_digital_twin_manager = IoTHubDigitalTwinManager(iothub_connection_str)

    # If you already have a component thermostat1:
    # patch = [{"op": "replace", "path": "/thermostat1/targetTemperature", "value": 42}]
    patch = [{"op": "add", "path": "/targetTemperature", "value": 42}]
    iothub_digital_twin_manager.update_digital_twin(device_id, patch)
    print("Patch has been succesfully applied")

    iothub_registry_manager = IoTHubRegistryManager(iothub_connection_str)
    twin = iothub_registry_manager.get_twin(device_id)
    print("Full Twin is:")
    print(twin)

    additional_props = twin.additional_properties
    if "modelId" in additional_props:
        print("Model id for digital twin is")
        print("ModelId:" + additional_props["modelId"])

except msrest.exceptions.HttpOperationError as ex:
    print("HttpOperationError error {0}".format(ex.response.text))
except Exception as exc:
    print("Unexpected error {0}".format(exc))
except KeyboardInterrupt:
    print("Sample stopped")
