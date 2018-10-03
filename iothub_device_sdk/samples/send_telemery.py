# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

import logging
from iothub_device_sdk.device.device_client import DeviceClient
from iothub_device_sdk.device.transport.transport import TransportProtocol

logging.basicConfig(level=logging.INFO)

conn_str = "HostName=IOTHubQuickStart.azure-devices.net;DeviceId=MyPythonDevice;SharedAccessKey=WHYHkHEwa2FUTsbNJDL+j+4xHPYCndroM03bXyjhAWk="
simpleDevice = DeviceClient.from_connection_string(conn_str, TransportProtocol.MQTT)


def connection_state_callback(status):
    print("connection status: " + status)
    if status == "connected":
        simpleDevice.send_event("Mimbulus Mimbletonia")

simpleDevice.on_connection_state = connection_state_callback
simpleDevice.connect()

while True:
    continue




