# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import sys
import os
import msrest
import uuid
import base64
from azure.iot.hub import IoTHubRegistryManager
from azure.iot.hub.models import Twin, TwinProperties
from azure.identity import DefaultAzureCredential

device_id = "test-device"  # os.getenv("IOTHUB_DEVICE_ID")


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


# IOT_HUB_HOSTNAME: The hostname of the Azure IoT Hub
url = os.getenv("IOT_HUB_HOSTNAME")

# DefaultAzureCredential is provided by azure-identity. It supports
# different authentication mechanisms and determines the appropriate
# credential type based of the environment it is executing in. See
# https://pypi.org/project/azure-identity/ for more information on
# authenticating with DefaultAzureCredential or other implementations of TokenCredential.
credential = DefaultAzureCredential()

# This sample creates and uses device with SAS authentication
# For other authentication types use the appropriate create and update APIs:
#   X509:
#       new_device = iothub_registry_manager.create_device_with_x509(device_id, primary_thumbprint, secondary_thumbprint, status)
#       device_updated = iothub_registry_manager.update_device_with_X509(device_id, etag, primary_thumbprint, secondary_thumbprint, status)
#   Certificate authority:
#       new_device = iothub_registry_manager.create_device_with_certificate_authority(device_id, status)
#       device_updated = iothub_registry_manager.update_device_with_certificate_authority(self, device_id, etag, status):
try:
    # Create IoTHubRegistryManager
    iothub_registry_manager = IoTHubRegistryManager.from_token_credential(url, credential)

    # Create a device
    primary_key = base64.b64encode(str(uuid.uuid4()).encode()).decode()
    secondary_key = base64.b64encode(str(uuid.uuid4()).encode()).decode()
    device_state = "enabled"
    new_device = iothub_registry_manager.create_device_with_sas(
        device_id, primary_key, secondary_key, device_state
    )
    print_device_info("create_device", new_device)

    # Get device information
    device = iothub_registry_manager.get_device(device_id)
    print_device_info("get_device", device)

    # Delete the device
    iothub_registry_manager.delete_device(device_id)

    print("GetServiceStatistics")
    registry_statistics = iothub_registry_manager.get_service_statistics()
    print(registry_statistics)

    print("GetDeviceRegistryStatistics")
    registry_statistics = iothub_registry_manager.get_device_registry_statistics()
    print(registry_statistics)

except msrest.exceptions.HttpOperationError as ex:
    print("HttpOperationError error {0}".format(ex.response.text))
except Exception as ex:
    print("Unexpected error {0}".format(ex))
except KeyboardInterrupt:
    print("{} stopped".format(__file__))
finally:
    print("{} finished".format(__file__))
