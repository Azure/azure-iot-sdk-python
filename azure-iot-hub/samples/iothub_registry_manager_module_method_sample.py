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
module_id = os.getenv("IOTHUB_MODULE_ID")
method_name = "lockDoor"
method_payload = "now"

try:
    # RegistryManager
    iothub_registry_manager = IoTHubRegistryManager(iothub_connection_str)

    # Create Module
    primary_key = "aaabbbcccdddeeefffggghhhiiijjjkkklllmmmnnnoo"
    secondary_key = "111222333444555666777888999000aaabbbcccdddee"
    managed_by = ""
    new_module = iothub_registry_manager.create_module_with_sas(
        device_id, module_id, managed_by, primary_key, secondary_key
    )

    deviceMethod = CloudToDeviceMethod(method_name=method_name, payload=method_payload)
    iothub_registry_manager.invoke_device_module_method(device_id, module_id, deviceMethod)

    # Delete Module
    iothub_registry_manager.delete_module(device_id, module_id)
    print("Deleted Module {0}".format(module_id))

except Exception as ex:
    print("Unexpected error {0}".format(ex))
except KeyboardInterrupt:
    print("IoTHubRegistryManager sample stopped")
