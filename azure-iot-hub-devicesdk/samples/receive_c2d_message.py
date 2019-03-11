# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import os
from six.moves import input
import logging
import threading
from azure.iot.hub.devicesdk import DeviceClient
from azure.iot.hub.devicesdk.auth.authentication_provider_factory import from_connection_string

logging.basicConfig(level=logging.ERROR)


# The connection string for a device should never be stored in code. For the sake of simplicity we're using an environment variable here.
conn_str = os.getenv("IOTHUB_DEVICE_CONNECTION_STRING")
# The "Authentication Provider" is the object in charge of creating authentication "tokens" for the device client.
auth_provider = from_connection_string(conn_str)
# For now, the SDK only supports MQTT as a protocol. the client object is used to interact with your Azure IoT hub.
# It needs an Authentication Provider to secure the communication with the hub, using either tokens or x509 certificates
device_client = DeviceClient.from_authentication_provider(auth_provider, "mqtt")


# connect the client.
device_client.connect()


# define behavior for receiving a C2D message
def c2d_listener(device_client):
    while True:
        c2d_message = device_client.receive_c2d_message()  # blocking call
        print("the data in the message received was ")
        print(c2d_message.data)
        print("custom properties are")
        print(c2d_message.custom_properties)


# Run a listener thread in the background
listen_thread = threading.Thread(target=c2d_listener, args=(device_client,))
listen_thread.daemon = True
listen_thread.start()


# Wait for user to indicate they are done listening for messages
while True:
    selection = input("Press Q: Quit for exiting\n")
    if selection == "Q" or selection == "q":
        print("Quitting")
        break


# finally, disconnect
device_client.disconnect()
