# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import os
import threading
from six.moves import input
from azure.iot.device import IoTHubDeviceClient

conn_str = os.getenv("IOTHUB_DEVICE_CONNECTION_STRING")
device_client = IoTHubDeviceClient.create_from_connection_string(conn_str)

# connect the client.
device_client.connect()


# define behavior for receiving a C2D message
def twin_patch_listener(device_client):
    while True:
        patch = device_client.receive_twin_desired_properties_patch()  # blocking call
        print("the data in the desired properties patch was: {}".format(patch))


# Run a listener thread in the background
listen_thread = threading.Thread(target=twin_patch_listener, args=(device_client,))
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
