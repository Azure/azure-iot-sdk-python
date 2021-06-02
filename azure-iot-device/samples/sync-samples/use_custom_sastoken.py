# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import os
from six.moves import input
import threading
import time
from azure.iot.device import IoTHubDeviceClient

# Interval (in seconds) of how often to provide a new sastoken
NEW_TOKEN_INTERVAL = 1800


# NOTE: This code needs to be completed in order to work.
# Fill out the get_new_sastoken() method to return a NEW custom sastoken from your solution.
# It must return a unique value each time it is called.
def get_new_sastoken():
    pass


# The connection string for a device should never be stored in code. For the sake of simplicity we're using an environment variable here.
sastoken = get_new_sastoken()
# The client object is used to interact with your Azure IoT hub.
device_client = IoTHubDeviceClient.create_from_sastoken(sastoken)


# connect the client.
device_client.connect()


# define behavior for receiving a message
def message_handler(message):
    print("the data in the message received was ")
    print(message.data)
    print("custom properties are")
    print(message.custom_properties)


# set the message handler on the client
device_client.on_message_received = message_handler


# define behavior for providing new sastokens to prevent expiry
def sastoken_keepalive():
    while True:
        time.sleep(NEW_TOKEN_INTERVAL)
        sastoken = get_new_sastoken()
        print("New sastoken: {}".format(sastoken))
        device_client.update_sastoken(sastoken)


# run the sastoken keepalive in a new daemon thread
t = threading.Thread(target=sastoken_keepalive)
t.daemon = True
t.start()

# Wait for user to indicate they are done listening for messages
while True:
    selection = input("Press Q to quit\n")
    if selection == "Q" or selection == "q":
        print("Quitting...")
        break


# finally, shut down the client
device_client.shutdown()
