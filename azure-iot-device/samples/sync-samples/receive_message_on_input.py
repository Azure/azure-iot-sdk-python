# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

import threading
from azure.iot.device import IoTHubModuleClient

# Inputs/Ouputs are only supported in the context of Azure IoT Edge and module client
# The module client object acts as an Azure IoT Edge module and interacts with an Azure IoT Edge hub
module_client = IoTHubModuleClient.create_from_edge_environment()

# connect the client.
module_client.connect()


# define behavior for receiving an input message on input1
def input1_listener(module_client):
    while True:
        input_message = module_client.receive_message_on_input("input1")  # blocking call
        print("the data in the message received on input1 was ")
        print(input_message.data)
        print("custom properties are")
        print(input_message.custom_properties)


# define behavior for receiving an input message on input2
def input2_listener(module_client):
    while True:
        input_message = module_client.receive_message_on_input("input2")  # blocking call
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
    selection = input("Press Q to quit\n")
    if selection == "Q" or selection == "q":
        print("Quitting...")
        break

# finally, disconnect
module_client.disconnect()
