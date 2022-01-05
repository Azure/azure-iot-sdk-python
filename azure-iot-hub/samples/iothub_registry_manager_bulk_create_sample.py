# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import sys
import os
import msrest
import uuid
from azure.iot.hub import IoTHubRegistryManager
from azure.iot.hub.models import ExportImportDevice, AuthenticationMechanism, SymmetricKey

iothub_connection_str = os.getenv("IOTHUB_CONNECTION_STRING")


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


try:
    # Create IoTHubRegistryManager
    iothub_registry_manager = IoTHubRegistryManager.from_connection_string(iothub_connection_str)

    primary_key1 = str(uuid.uuid4())
    secondary_key1 = str(uuid.uuid4())
    symmetric_key1 = SymmetricKey(primary_key=primary_key1, secondary_key=secondary_key1)
    authentication1 = AuthenticationMechanism(type="sas", symmetric_key=symmetric_key1)
    device1 = ExportImportDevice(id="BulkDevice1", status="enabled", authentication=authentication1)

    primary_key2 = str(uuid.uuid4())
    secondary_key2 = str(uuid.uuid4())
    symmetric_key2 = SymmetricKey(primary_key=primary_key2, secondary_key=secondary_key2)
    authentication2 = AuthenticationMechanism(type="sas", symmetric_key=symmetric_key2)
    device2 = ExportImportDevice(id="BulkDevice2", status="enabled", authentication=authentication2)

    # Create devices
    device1.import_mode = "create"
    device2.import_mode = "create"
    device_list = [device1, device2]

    iothub_registry_manager.bulk_create_or_update_devices(device_list)

    # Get devices (max. 1000 with get_devices API)
    max_number_of_devices = 10
    devices = iothub_registry_manager.get_devices(max_number_of_devices)
    if devices:
        x = 0
        for d in devices:
            print_device_info("Get devices {0}".format(x), d)
            x += 1
    else:
        print("No device found")

    # Delete devices
    device1.import_mode = "delete"
    device2.import_mode = "delete"
    device_list = [device1, device2]

    iothub_registry_manager.bulk_create_or_update_devices(device_list)

except msrest.exceptions.HttpOperationError as ex:
    print("HttpOperationError error {0}".format(ex.response.text))
except Exception as ex:
    print("Unexpected error {0}".format(ex))
except KeyboardInterrupt:
    print("{} stopped".format(__file__))
finally:
    print("{} finished".format(__file__))
