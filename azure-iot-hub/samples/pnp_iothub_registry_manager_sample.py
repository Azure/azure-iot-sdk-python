# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import sys
import os
from azure.iot.hub import IoTHubRegistryManager
from azure.iot.hub.models import Twin, TwinProperties
from azure.iot.hub.models import CloudToDeviceMethod

iothub_connection_str = os.getenv("IOTHUB_CONNECTION_STRING")
device_id = os.getenv("IOTHUB_DEVICE_ID")
method_name = os.getenv("IOTHUB_METHOD_NAME")
method_payload = os.getenv("IOTHUB_METHOD_PAYLOAD")


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
    iothub_registry_manager = IoTHubRegistryManager(iothub_connection_str)

    # Get device twin
    twin = iothub_registry_manager.get_twin(device_id)
    print(twin)
    print("")
    
    # Print the device's model ID
    additional_props = twin.additional_properties
    if "modelId" in additional_props:
        print("Model id for digital twin is")
        print("ModelId:" + additional_props["modelId"])
        print("")


    # Update twin
    twin_patch = Twin()
    twin_patch.properties = TwinProperties(desired={"targetTemperature": 42})
    updated_twin = iothub_registry_manager.update_twin(device_id, twin_patch, twin.etag)
    print(updated_twin)
    print("The twin patch has been successfully applied")

    # invoke device method
    deviceMethod = CloudToDeviceMethod(method_name=method_name, payload=method_payload)
    iothub_registry_manager.invoke_device_method(device_id, deviceMethod)
    print("The device method has been successfully invoked")

except Exception as ex:
    print("Unexpected error {0}".format(ex))
except KeyboardInterrupt:
    print("iothub_registry_manager_sample stopped")
