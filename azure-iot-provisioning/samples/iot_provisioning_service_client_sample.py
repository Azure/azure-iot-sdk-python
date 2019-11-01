# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import sys
import os
from azure.iot.provisioning import IoTProvisioningServiceClient

connection_str = os.getenv("IOT_PROVISIONING_SERVICE_CONNECTION_STRING")
device_id = "test_device"

try:
    # Create IoTProvisioningServiceClient
    iot_provisioning_service_client = IoTProvisioningServiceClient(connection_str)
    certificate_authority = iot_provisioning_service_client.get_certificate_authority()
    print(certificate_authority)


except Exception as ex:
    print("Unexpected error {0}".format(ex))
except KeyboardInterrupt:
    print("iot_provisioning_service_client_sample stopped")
