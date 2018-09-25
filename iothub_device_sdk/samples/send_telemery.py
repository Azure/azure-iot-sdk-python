# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

import logging
from iothub_device_sdk.device.device_client import DeviceClient

logging.basicConfig(level=logging.INFO)

conn_str = "DEVICE_CONNECTION_STRING"
simpleDevice = DeviceClient.from_connection_string(conn_str)


def connection_state_callback(status):
    print("connection status: " + status)
    if status == "connected":
        simpleDevice.send_event("Expecto Patronum")


simpleDevice.on_connection_state = connection_state_callback
simpleDevice.connect_to_iot_hub()

while True:
    continue
