# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import sys
import os
from azure.iot.hub import IoTHubRegistryManager
from azure.iot.hub.models import QuerySpecification

iothub_connection_str = os.getenv("IOTHUB_CONNECTION_STRING")


def print_twin(title, iothub_device):
    print(title + ":")
    print("device_id                      = {0}".format(iothub_device.device_id))
    print("module_id                      = {0}".format(iothub_device.module_id))
    print("authentication_type            = {0}".format(iothub_device.authentication_type))
    print("x509_thumbprint                = {0}".format(iothub_device.x509_thumbprint))
    print("etag                           = {0}".format(iothub_device.etag))
    print("device_etag                    = {0}".format(iothub_device.device_etag))
    print("tags                           = {0}".format(iothub_device.tags))
    print("version                        = {0}".format(iothub_device.version))

    print("status                         = {0}".format(iothub_device.status))
    print("status_reason                  = {0}".format(iothub_device.status_reason))
    print("status_update_time             = {0}".format(iothub_device.status_update_time))
    print("connection_state               = {0}".format(iothub_device.connection_state))
    print("last_activity_time             = {0}".format(iothub_device.last_activity_time))
    print(
        "cloud_to_device_message_count  = {0}".format(iothub_device.cloud_to_device_message_count)
    )
    print("device_scope                   = {0}".format(iothub_device.device_scope))

    print("properties                     = {0}".format(iothub_device.properties))
    print("additional_properties          = {0}".format(iothub_device.additional_properties))
    print("")


def print_query_result(title, query_result):
    print("")
    print("Type: {0}".format(query_result.type))
    print("Continuation token: {0}".format(query_result.continuation_token))
    if query_result.items:
        x = 1
        for d in query_result.items:
            print_twin("{0}: {0}".format(x), title, d)
            x += 1
    else:
        print("No item found")


try:
    # Create IoTHubRegistryManager
    iothub_registry_manager = IoTHubRegistryManager(iothub_connection_str)

    query_specification = QuerySpecification(query= "SELECT * FROM devices")

    # Get specified number of devices (in this case 4)    
    query_result0 = iothub_registry_manager.query_iot_hub(query_specification, None, 4)
    print_items("Query 4 device twins", query_result0)

    # Get all device twins using query
    query_result1 = iothub_registry_manager.query_iot_hub(query_specification)
    print_items("Query all device twins", query_result1)

    print_items("Query 4 device twins", query_result1.items)

    # Paging... Get more devices (over 1000)
    continuation_token = query_result1.continuation_token
    if continuation_token:
        query_result2 = iothub_registry_manager.query_iot_hub(query_specification, continuation_token)
        print_items("Query all device twins - continued", query_result2)


except Exception as ex:
    print("Unexpected error {0}".format(ex))
except KeyboardInterrupt:
    print("iothub_registry_manager_sample stopped")
