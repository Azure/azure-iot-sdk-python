# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import sys
import os
from azure.iot.provisioning import IoTProvisioningServiceClient

connection_str = os.getenv("IOT_PROVISIONING_SERVICE_CONNECTION_STRING")
query_certificate_authorities = os.getenv("IOT_PROVISIONING_QUERY_CERTIFICATE_AUTHORITIES")
query_device_groups = os.getenv("IOT_PROVISIONING_QUERY_DEVICE_GROUPS")
query_device_records = os.getenv("IOT_PROVISIONING_QUERY_DEVICE_RECORDS")
query_group_records = os.getenv("IOT_PROVISIONING_QUERY_GROUP_RECORDS")
query_linked_hubs = os.getenv("IOT_PROVISIONING_QUERY_LINKED_HUBS")
query_provisioning_records = os.getenv("IOT_PROVISIONING_QUERY_PROVISIONING_RECORDS")
query_provisioning_records = os.getenv("IOT_PROVISIONING_QUERY_PROVISIONING_RECORDS")
query_provisioning_settings = os.getenv("IOT_PROVISIONING_QUERY_PROVISIONING_SETTINGS")

max_item_count = 10

try:
    # Create IoTProvisioningServiceClient
    iot_provisioning_service_client = IoTProvisioningServiceClient(connection_str)

    # Query certificate authorities
    certificate_authorities = iot_provisioning_service_client.query_certificate_authorities(
        query_certificate_authorities, max_item_count
    )
    print("Certificate authorities {0}: ".format(certificate_authorities))

    # Query device groups
    device_groups = iot_provisioning_service_client.query_device_groups(
        query_device_groups, max_item_count
    )
    print("Device groups {0}: ".format(device_groups))

    # Query device records
    device_records = iot_provisioning_service_client.query_device_records(
        query_device_records, max_item_count
    )
    print("Device records {0}: ".format(device_records))

    # Query group records
    group_records = iot_provisioning_service_client.query_group_records(
        query_group_records, max_item_count
    )
    print("Group records {0}: ".format(group_records))

    # Query linked hubs
    linked_hubs = iot_provisioning_service_client.query_linked_hubs(
        query_linked_hubs, max_item_count
    )
    print("Linked hubs {0}: ".format(linked_hubs))

    # Query provisioning records
    provisioning_records = iot_provisioning_service_client.query_provisioning_records(
        query_provisioning_records, max_item_count
    )
    print("Provisioning records {0}: ".format(provisioning_records))

    # Query provisioning settings
    provisioning_settings = iot_provisioning_service_client.query_provisioning_settings(
        query_provisioning_settings, max_item_count
    )
    print("Provisioning settings {0}: ".format(provisioning_settings))

except Exception as ex:
    print("Unexpected error {0}".format(ex))
except KeyboardInterrupt:
    print("iot_provisioning_service_client_sample stopped")
