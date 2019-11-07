# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import sys
import os
from azure.iot.provisioning import IoTProvisioningServiceClient

connection_str = os.getenv("IOT_PROVISIONING_SERVICE_CONNECTION_STRING")
provisioning_settings_name_1 = os.getenv("IOT_PROVISIONING_PROVISIONING_SETTINGS_NAME_1")
provisioning_settings_name_2 = os.getenv("IOT_PROVISIONING_PROVISIONING_SETTINGS_NAME_2")
provisioning_settings_1 = os.getenv("IOT_PROVISIONING_PROVISIONING_SETTINGS_1")
provisioning_settings_2 = os.getenv("IOT_PROVISIONING_PROVISIONING_SETTINGS_2")

try:
    # Create IoTProvisioningServiceClient
    iot_provisioning_service_client = IoTProvisioningServiceClient(connection_str)

    # Create provisioning settings
    provisioning_settings_created = iot_provisioning_service_client.create_provisioning_settings(
        provisioning_settings_name_1, provisioning_settings_1
    )
    print("Provisioning settings 1 {0}: ".format(provisioning_settings_1.name))

    # Replace provisioning settings
    provisioning_settings_updated = iot_provisioning_service_client.replace_provisioning_settings(
        provisioning_settings_name_2, provisioning_settings_2, provisioning_settings_created.etag
    )
    print("Provisioning settings 2 {0}: ".format(provisioning_settings_2.name))

    # Get the provisioning settings
    provisioning_settings_get = iot_provisioning_service_client.get_provisioning_settings(
        provisioning_settings_name_2
    )
    print("Current provisioning settings {0}: ".format(provisioning_settings_get))

    # Delete provisioning settings
    iot_provisioning_service_client.delete_provisioning_settings(
        provisioning_settings_get.name, provisioning_settings_get.etag
    )

except Exception as ex:
    print("Unexpected error {0}".format(ex))
except KeyboardInterrupt:
    print("iot_provisioning_service_client_sample stopped")
