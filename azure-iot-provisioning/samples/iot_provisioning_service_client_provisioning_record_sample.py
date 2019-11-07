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
device_id = os.getenv("IOT_PROVISIONING_DEVICE_ID")

try:
    # Create IoTProvisioningServiceClient
    iot_provisioning_service_client = IoTProvisioningServiceClient(connection_str)

    # Get device record
    provisioning_record = iot_provisioning_service_client.get_provisioning_record(
        device_group_name, device_id
    )
    print("Provisioning record 1 {0}: ".format(provisioning_record))

except Exception as ex:
    print("Unexpected error {0}".format(ex))
except KeyboardInterrupt:
    print("iot_provisioning_service_client_sample stopped")
