# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import sys
import os
from azure.iot.provisioning import IoTProvisioningServiceClient

connection_str = os.getenv("IOT_PROVISIONING_SERVICE_CONNECTION_STRING")
device_record_name_1 = os.getenv("IOT_PROVISIONING_DEVICE_RECORD_NAME_1")
device_record_name_2 = os.getenv("IOT_PROVISIONING_DEVICE_RECORD_NAME_2")
device_record_1 = os.getenv("IOT_PROVISIONING_DEVICE_RECORD_1")
device_record_2 = os.getenv("IOT_PROVISIONING_DEVICE_RECORD_2")
device_id = os.getenv("IOT_PROVISIONING_DEVICE_ID")

try:
    # Create IoTProvisioningServiceClient
    iot_provisioning_service_client = IoTProvisioningServiceClient(connection_str)

    # Create device record
    device_record_created = iot_provisioning_service_client.create_device_record(
        device_record_name_1, device_id, device_record_1
    )
    print("Device record 1 {0}: ".format(device_record_1.name))

    # Replace device record
    device_record_updated = iot_provisioning_service_client.replace_device_record(
        device_record_name_2, device_id, device_record_2, device_record_created.etag
    )
    print("Device record 2 {0}: ".format(device_record_2.name))

    # Get device record
    device_record_get = iot_provisioning_service_client.get_device_record(
        device_record_name_2, device_id
    )
    print("Current device record {0}: ".format(device_record_get))

    # Create device record
    iot_provisioning_service_client.delete_device_record(
        device_record_get.name, device_id, device_record_get.etag
    )

except Exception as ex:
    print("Unexpected error {0}".format(ex))
except KeyboardInterrupt:
    print("iot_provisioning_service_client_sample stopped")
