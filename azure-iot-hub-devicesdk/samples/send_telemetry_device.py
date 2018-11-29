# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------
import os
from threading import Timer
from azure.iot.hub.devicesdk.device_client import DeviceClient
from azure.iot.hub.devicesdk.auth.authentication_provider_factory import from_connection_string

# The connection string for a device should never be stored in code. For the sake of simplicity we're using an environment variable here.
conn_str = os.getenv("IOTHUB_DEVICE_CONNECTION_STRING")
# The "Authentication Provider" is the object in charge of creating authentication "tokens" for the device client.
auth_provider = from_connection_string(conn_str)
# For now, the SDK only supports MQTT as a protocol. the client object is used to interact with your Azure IoT hub.
# It needs an Authentication Provider to secure the communication with the hub, using either tokens or x509 certificates
device_client = DeviceClient.from_authentication_provider(auth_provider, "mqtt")
event_sender = None


# This function will be called by a timer on a regular basis, once connected
def send_payload():
    print("sending!")
    device_client.send_event("test_payload")
    start_sender()


def start_sender():
    # This defines a timer that fires after 5 seconds
    global event_sender
    event_sender = Timer(5.0, send_payload)
    event_sender.start()


def cancel_sender():
    event_sender.cancel()


# The connection state callback allows us to detect when the client is connected and disconnected:
def connection_state_callback(status):
    print("connection status: " + status)
    if status == "connected":
        start_sender()
    elif status == "disconnected":
        cancel_sender()


# Register the connection state callback with the client...
device_client.on_connection_state = connection_state_callback
# ... and connect the client. The timer will start when the client reaches the connected state.
device_client.connect()

input("Press Enter to exit at any time...\n\n")
cancel_sender()
