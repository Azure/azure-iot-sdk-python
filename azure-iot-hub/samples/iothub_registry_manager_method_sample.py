# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import sys
import os
from azure.iot.hub import IoTHubRegistryManager
from azure.iot.hub.models import CloudToDeviceMethod


iothub_connection_str = os.getenv("IOTHUB_CONNECTION_STRING")
device_id = os.getenv("IOTHUB_DEVICE_ID")
method_name = "lockDoor"
method_payload = "now"


try:
    # Create IoTHubRegistryManager
    registry_manager = IoTHubRegistryManager(iothub_connection_str)

    deviceMethod = CloudToDeviceMethod(method_name=method_name, payload=method_payload)
    registry_manager.invoke_device_method(device_id, deviceMethod)

except Exception as ex:
    print("Unexpected error {0}".format(ex))
except KeyboardInterrupt:
    print("iothub_registry_manager_sample stopped")
