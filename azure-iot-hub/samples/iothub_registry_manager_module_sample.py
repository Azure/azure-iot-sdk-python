# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import sys
import os
from azure.iot.hub import IoTHubRegistryManager

connection_str = os.getenv("IOTHUB_CONNECTION_STRING")
device_id = os.getenv("IOTHUB_DEVICE_ID")
module_id = os.getenv("IOTHUB_MODULE_ID")


def print_module_info(title, iothub_module):
    print(title + ":")
    print("iothubModule.device_id                      = {0}".format(iothub_module.device_id))
    print("iothubModule.module_id                      = {0}".format(iothub_module.module_id))
    print("iothubModule.managed_by                     = {0}".format(iothub_module.managed_by))
    print("iothubModule.generation_id                  = {0}".format(iothub_module.generation_id))
    print("iothubModule.etag                           = {0}".format(iothub_module.etag))
    print(
        "iothubModule.connection_state               = {0}".format(iothub_module.connection_state)
    )
    print(
        "iothubModule.connection_state_updated_time  = {0}".format(
            iothub_module.connection_state_updated_time
        )
    )
    print(
        "iothubModule.last_activity_time             = {0}".format(iothub_module.last_activity_time)
    )
    print(
        "iothubModule.cloud_to_device_message_count  = {0}".format(
            iothub_module.cloud_to_device_message_count
        )
    )
    print("iothubModule.authentication                 = {0}".format(iothub_module.authentication))
    print("")


try:
    # RegistryManager
    iothub_registry_manager = IoTHubRegistryManager(connection_str)

    # Create Module
    primary_key = "aaabbbcccdddeeefffggghhhiiijjjkkklllmmmnnnoo"
    secondary_key = "111222333444555666777888999000aaabbbcccdddee"
    managed_by = ""
    new_module = iothub_registry_manager.create_module_with_sas(
        device_id, module_id, managed_by, primary_key, secondary_key, "enabled"
    )
    print_module_info("Create Module", new_module)

    # Get Module
    iothub_module = iothub_registry_manager.get_module(device_id, module_id)
    print_module_info("Get Module", iothub_module)

    # Get Module Twin
    module_twin = iothub_registry_manager.get_module_twin(device_id, module_id)
    print(module_twin)

    # Get all modules on the device
    all_modules = iothub_registry_manager.get_modules(device_id)
    for module in all_modules:
        print_module_info("", module)

    # Update Module
    primary_key = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    secondary_key = "yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy"
    managed_by = "testManagedBy"
    updated_module = iothub_registry_manager.update_module_with_sas(
        device_id, module_id, managed_by, iothub_module.etag, primary_key, secondary_key, None
    )
    print_module_info("Update Module", updated_module)

    # Delete Module
    iothub_registry_manager.delete_module(device_id, module_id)
    print("Deleted Module {0}".format(module_id))

except Exception as ex:
    print("Unexpected error {0}".format(ex))
except KeyboardInterrupt:
    print("IoTHubRegistryManager sample stopped")
