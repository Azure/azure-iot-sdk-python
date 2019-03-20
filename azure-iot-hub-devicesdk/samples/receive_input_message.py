# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------
import logging
import threading
from azure.iot.hub.devicesdk import ModuleClient
from azure.iot.hub.devicesdk import auth

logging.basicConfig(level=logging.ERROR)

# The "Authentication Provider" is the object in charge of creating authentication "tokens" for the module client.
auth_provider_receiver = auth.from_environment()
# For now, the SDK only supports MQTT as a protocol.
# Inputs/Ouputs are only supported in the context of Azure IoT Edge and module client
# The module client object acts as an Azure IoT Edge module and interacts with an Azure IoT Edge hub
# It needs an Authentication Provider to secure the communication with the Edge hub.
# This authentication provider is created from environment & delegates token generation to iotedged.

module_client = ModuleClient.from_authentication_provider(auth_provider_receiver, "mqtt")

# connect the client.
module_client.connect()


# define behavior for receiving an input message on input1
def input1_listener(module_client):
    while True:
        input_message = module_client.receive_input_message("input1")  # blocking call
        print("the data in the message received on input1 was ")
        print(input_message.data)
        print("custom properties are")
        print(input_message.custom_properties)


# define behavior for receiving an input message on input2
def input2_listener(module_client):
    while True:
        input_message = module_client.receive_input_message("input2")  # blocking call
        print("the data in the message received on input2 was ")
        print(input_message.data)
        print("custom properties are")
        print(input_message.custom_properties)


# Run listener threads in the background
listen_thread = threading.Thread(target=input1_listener, args=(module_client,))
listen_thread.daemon = True
listen_thread.start()

listen_thread = threading.Thread(target=input2_listener, args=(module_client,))
listen_thread.daemon = True
listen_thread.start()

while True:
    selection = input("Press Q: Quit for exiting\n")
    if selection == "Q" or selection == "q":
        print("Quitting")
        break

# finally, disconnect
module_client.disconnect()
