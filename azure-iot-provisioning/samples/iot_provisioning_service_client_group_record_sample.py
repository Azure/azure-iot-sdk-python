# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import sys
import os
from azure.iot.provisioning import IoTProvisioningServiceClient

connection_str = os.getenv("IOT_PROVISIONING_SERVICE_CONNECTION_STRING")
device_group_name = os.getenv("IOT_PROVISIONING_DEVICE_GROUP_NAME")
group_record_name_1 = os.getenv("IOT_PROVISIONING_GROUP_RECORD_NAME_1")
group_record_name_2 = os.getenv("IOT_PROVISIONING_GROUP_RECORD_NAME_2")
group_record_1 = os.getenv("IOT_PROVISIONING_GROUP_RECORD_1")
group_record_2 = os.getenv("IOT_PROVISIONING_GROUP_RECORD_2")

try:
    # Create IoTProvisioningServiceClient
    iot_provisioning_service_client = IoTProvisioningServiceClient(connection_str)

    # Create group record
    group_record_created = iot_provisioning_service_client.create_group_record(
        device_group_name, group_record_name_1, group_record_1
    )
    print("Group record 1 {0}: ".format(group_record_1.name))

    # Replace group record
    group_record_updated = iot_provisioning_service_client.replace_group_record(
        device_group_name, group_record_name_2, group_record_2, group_record_created.etag
    )
    print("Group record 2 {0}: ".format(group_record_2.name))

    # Get group record
    group_record_get = iot_provisioning_service_client.get_group_record(
        device_group_name, group_record_name_2
    )
    print("Current group record {0}: ".format(group_record_get))

    # Delete group record
    iot_provisioning_service_client.delete_group_record(
        device_group_name, group_record_get.name, group_record_get.etag
    )

except Exception as ex:
    print("Unexpected error {0}".format(ex))
except KeyboardInterrupt:
    print("iot_provisioning_service_client_sample stopped")
