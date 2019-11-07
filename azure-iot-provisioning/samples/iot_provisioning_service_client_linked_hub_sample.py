# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import sys
import os
from azure.iot.provisioning import IoTProvisioningServiceClient

connection_str = os.getenv("IOT_PROVISIONING_SERVICE_CONNECTION_STRING")
linked_hub_name_1 = os.getenv("IOT_PROVISIONING_LINKED_HUB_NAME_1")
linked_hub_name_2 = os.getenv("IOT_PROVISIONING_LINKED_HUB_NAME_2")
linked_hub_1 = os.getenv("IOT_PROVISIONING_LINKED_HUB_1")
linked_hub_2 = os.getenv("IOT_PROVISIONING_LINKED_HUB_2")

try:
    # Create IoTProvisioningServiceClient
    iot_provisioning_service_client = IoTProvisioningServiceClient(connection_str)

    # Create linked hub
    linked_hub_created = iot_provisioning_service_client.create_linked_hub(
        linked_hub_name_1, linked_hub_1
    )
    print("Linked hub 1 {0}: ".format(linked_hub_1.name))

    # Replace linked hub
    linked_hub_updated = iot_provisioning_service_client.replace_linked_hub(
        linked_hub_name_2, linked_hub_2, linked_hub_created.etag
    )
    print("Linked hub 2 {0}: ".format(linked_hub_2.name))

    # Get the linked hub
    linked_hub_get = iot_provisioning_service_client.get_linked_hub(linked_hub_name_2)
    print("Current linked hub {0}: ".format(linked_hub_get))

    # Delete linked hub
    iot_provisioning_service_client.delete_linked_hub(linked_hub_get.name, linked_hub_get.etag)

except Exception as ex:
    print("Unexpected error {0}".format(ex))
except KeyboardInterrupt:
    print("iot_provisioning_service_client_sample stopped")
