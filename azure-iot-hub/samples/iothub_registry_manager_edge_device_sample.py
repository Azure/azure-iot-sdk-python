# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import sys
import os
from azure.iot.hub import IoTHubRegistryManager
from azure.iot.hub.models import Twin, TwinProperties, DeviceCapabilities

iothub_connection_str = os.getenv("IOTHUB_CONNECTION_STRING")
device_id = os.getenv("IOTHUB_NEW_DEVICE_ID")


def print_device_info(title, iothub_device):
    print(title + ":")
    print("device_id                      = {0}".format(iothub_device.device_id))
    print("authentication.type            = {0}".format(iothub_device.authentication.type))
    print("authentication.symmetric_key   = {0}".format(iothub_device.authentication.symmetric_key))
    print(
        "authentication.x509_thumbprint = {0}".format(iothub_device.authentication.x509_thumbprint)
    )
    print("connection_state               = {0}".format(iothub_device.connection_state))
    print(
        "connection_state_updated_tTime = {0}".format(iothub_device.connection_state_updated_time)
    )
    print(
        "cloud_to_device_message_count  = {0}".format(iothub_device.cloud_to_device_message_count)
    )
    print("device_scope                   = {0}".format(iothub_device.device_scope))
    print("etag                           = {0}".format(iothub_device.etag))
    print("generation_id                  = {0}".format(iothub_device.generation_id))
    print("last_activity_time             = {0}".format(iothub_device.last_activity_time))
    print("status                         = {0}".format(iothub_device.status))
    print("status_reason                  = {0}".format(iothub_device.status_reason))
    print("status_updated_time            = {0}".format(iothub_device.status_updated_time))
    print("")


# This sample creates and iotEdge device with SAS authentication
# For other authentication types use the appropriate create and update APIs:
#   X509:
#       new_device = iothub_registry_manager.create_device_with_x509(device_id, primary_thumbprint, secondary_thumbprint, status, iot_edge)
#   Certificate authority:
#       new_device = iothub_registry_manager.create_device_with_certificate_authority(device_id, status, iot_edge)
try:
    # Create IoTHubRegistryManager
    iothub_registry_manager = IoTHubRegistryManager(iothub_connection_str)

    # Create a device
    primary_key = "aaabbbcccdddeeefffggghhhiiijjjkkklllmmmnnnoo"
    secondary_key = "111222333444555666777888999000aaabbbcccdddee"
    device_state = "enabled"
    iot_edge = True
    new_device = iothub_registry_manager.create_device_with_sas(
        device_id, primary_key, secondary_key, device_state, iot_edge
    )
    print_device_info("create_device", new_device)

    # Get device twin
    twin = iothub_registry_manager.get_twin(device_id)
    print(twin)
    print(twin.capabilities)
    print("")

    # Delete the device
    iothub_registry_manager.delete_device(device_id)

except Exception as ex:
    print("Unexpected error {0}".format(ex))
except KeyboardInterrupt:
    print("iothub_registry_manager_sample stopped")
