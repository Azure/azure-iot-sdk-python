# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import os
from six.moves import input
import threading
from azure.iot.device import IoTHubDeviceClient

# The connection string for a device should never be stored in code. For the sake of simplicity we're using an environment variable here.
conn_str = os.getenv("IOTHUB_DEVICE_CONNECTION_STRING")
# The client object is used to interact with your Azure IoT hub.
device_client = IoTHubDeviceClient.create_from_connection_string(conn_str)


# connect the client.
device_client.connect()


# define behavior for receiving a message
def message_listener(device_client):
    while True:
        message = device_client.receive_message()  # blocking call
        print("the data in the message received was ")
        print(message.data)
        print("custom properties are")
        print(message.custom_properties)


# Run a listener thread in the background
listen_thread = threading.Thread(target=message_listener, args=(device_client,))
listen_thread.daemon = True
listen_thread.start()


# Wait for user to indicate they are done listening for messages
while True:
    selection = input("Press Q to quit\n")
    if selection == "Q" or selection == "q":
        print("Quitting...")
        break


# finally, disconnect
device_client.disconnect()
