# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import os
from azure.iot.device import IoTHubDeviceClient, Message

# The device connection string to authenticate the device with your IoT hub.
CONNECTION_STRING = os.getenv("IOTHUB_DEVICE_CONNECTION_STRING")

if CONNECTION_STRING is None:
    print(
        "Must set environment variable 'IOTHUB_DEVICE_CONNECTION_STRING' in the format '<hub name>.device.azure-devices.<dns suffix>' in order to use TLS 1.3"
    )
    raise Exception

if ".device.azure-devices." not in CONNECTION_STRING:
    # classic connection strings that look like '<hub-name>.azure-devices.<dns suffix>' only support up to TLS 1.2
    print(
        "Device connection string must match the format '<hub name>.device.azure-devices.<dns suffix>' in order to use TLS 1.3"
    )
    raise Exception

# The client object is used to interact with your Azure IoT hub.
device_client = IoTHubDeviceClient.create_from_connection_string(CONNECTION_STRING)

# Connect the client.
print("opening the connection")
device_client.connect()

print("sending message")
msg = Message("Hello from TLS 1.3 connection!")
device_client.send_message(msg)

# finally, shut down the client
print("closing the connection")
device_client.shutdown()
