# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import os
from azure.iot.device import IoTHubDeviceClient, X509

hostname = os.getenv("HOSTNAME")
# The device that has been created on the portal using X509 CA signing or Self signing capabilities
device_id = os.getenv("DEVICE_ID")

x509 = X509(
    cert_file=os.getenv("X509_CERT_FILE"),
    key_file=os.getenv("X509_KEY_FILE"),
    pass_phrase=os.getenv("X509_PASS_PHRASE"),
)

# The client object is used to interact with your Azure IoT hub.
device_client = IoTHubDeviceClient.create_from_x509_certificate(
    hostname=hostname, device_id=device_id, x509=x509
)


# connect the client.
device_client.connect()


# define behavior for receiving a message
def message_received_handler(message):
    print("the data in the message received was ")
    print(message.data)
    print("custom properties are")
    print(message.custom_properties)


# Set the message received handler on the client
device_client.on_message_received = message_received_handler


# Wait for user to indicate they are done listening for messages
while True:
    selection = input("Press Q to quit\n")
    if selection == "Q" or selection == "q":
        print("Quitting...")
        break


# finally, shut down the client
device_client.shutdown()
