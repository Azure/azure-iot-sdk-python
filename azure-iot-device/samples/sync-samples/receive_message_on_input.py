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


# define behavior for receiving a message on inputs 1 and 2
def message_handler(message):
    if message.input_name == "input1":
        print("Message received on INPUT 1")
        print("the data in the message received was ")
        print(message.data)
        print("custom properties are")
        print(message.custom_properties)
    elif message.input_name == "input2":
        print("Message received on INPUT 2")
        print("the data in the message received was ")
        print(message.data)
        print("custom properties are")
        print(message.custom_properties)
    else:
        print("message received on unknown input")


# set the message handler on the client
module_client.on_message_received = message_handler


while True:
    selection = input("Press Q to quit\n")
    if selection == "Q" or selection == "q":
        print("Quitting...")
        break

# finally, disconnect
module_client.disconnect()
