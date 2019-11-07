# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import sys
import os
from azure.iot.provisioning import IoTProvisioningServiceClient

connection_str = os.getenv("IOT_PROVISIONING_SERVICE_CONNECTION_STRING")
device_group_name_1 = os.getenv("IOT_PROVISIONING_DEVICE_GROUP_NAME_1")
device_group_name_2 = os.getenv("IOT_PROVISIONING_DEVICE_GROUP_NAME_2")
device_group_1 = os.getenv("IOT_PROVISIONING_DEVICE_GROUP_1")
device_group_2 = os.getenv("IOT_PROVISIONING_DEVICE_GROUP_2")

try:
    # Create IoTProvisioningServiceClient
    iot_provisioning_service_client = IoTProvisioningServiceClient(connection_str)

    # Create device group
    device_group_created = iot_provisioning_service_client.create_device_group(
        device_group_name_1, device_group_1
    )
    print("Device group 1 {0}: ".format(device_group_1.name))

    # Replace device group
    device_group_updated = iot_provisioning_service_client.replace_device_group(
        device_group_name_2, device_group_2, device_group_created.etag
    )
    print("Device group 2 {0}: ".format(device_group_2.name))

    # Get the device group
    device_group_get = iot_provisioning_service_client.get_device_group(device_group_name_2)
    print("Current device group {0}: ".format(device_group_get))

    # Delete device group
    iot_provisioning_service_client.delete_device_group(
        device_group_get.name, device_group_get.etag
    )

except Exception as ex:
    print("Unexpected error {0}".format(ex))
except KeyboardInterrupt:
    print("iot_provisioning_service_client_sample stopped")
