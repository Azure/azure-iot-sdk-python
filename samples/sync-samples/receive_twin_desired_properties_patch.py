# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import os
from azure.iot.device import IoTHubDeviceClient

conn_str = os.getenv("IOTHUB_DEVICE_CONNECTION_STRING")
device_client = IoTHubDeviceClient.create_from_connection_string(conn_str)

# connect the client.
device_client.connect()


# define behavior for receiving a twin patch
def twin_patch_handler(patch):
    print("the data in the desired properties patch was: {}".format(patch))


# set the twin patch handler on the client
device_client.on_twin_desired_properties_patch_received = twin_patch_handler


# Wait for user to indicate they are done listening for messages
while True:
    selection = input("Press Q to quit\n")
    if selection == "Q" or selection == "q":
        print("Quitting...")
        break


# finally, shut down the client
device_client.shutdown()
