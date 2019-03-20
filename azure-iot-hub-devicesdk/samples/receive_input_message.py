# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------
import logging
import threading
from azure.iot.hub.devicesdk import ModuleClient
from azure.iot.hub.devicesdk.auth.authentication_provider_factory import from_environment

logging.basicConfig(level=logging.ERROR)

# The "Authentication Provider" is the object in charge of creating authentication "tokens" for the module client.
auth_provider_receiver = from_environment()
# For now, the SDK only supports MQTT as a protocol.
# Inputs/Ouputs are only supported in the context of Azure IoT Edge and module client
# The module client object acts as an Azure IoT Edge module and interacts with an Azure IoT Edge hub
# It needs an Authentication Provider to secure the communication with the Edge hub.
# This authentication provider is created from environment & delegates token generation to iotedged.

module_client_receiver = ModuleClient.from_authentication_provider(auth_provider_receiver, "mqtt")

# module_client_receiver the client.
module_client_receiver.connect()

# enable the device to receive c2d messages
input_message_queue = module_client_receiver.get_input_message_queue("input1")


# define behavior for receiving an input message
def input_message_listener(message_queue):
    while True:
        input_message = message_queue.get()
        print("the data in the message received was ")
        print(input_message.data)
        print("custom properties are")
        print(input_message.custom_properties)


# Run a listener thread in the background
listen_thread = threading.Thread(target=input_message_listener, args=(input_message_queue,))
listen_thread.daemon = True
listen_thread.start()

while True:
    selection = input("Press Q: Quit for exiting\n")
    if selection == "Q" or selection == "q":
        print("Quitting")
        break

# finally, disconnect
module_client_receiver.disconnect()


# The output looks like
# """
# the data in the message received was
# b'{"machine":{"temperature":62.428344488227,"pressure":5.7196848151144684},"ambient":{"temperature":20.638392061990867,"humidity":24},"timeCreated":"2019-03-04T19:41:35.0233948Z"}'
# custom properties are
# {'sequenceNumber': '77', 'batchId': '30f3895a-8abb-4cb5-962d-1e33d7a5ba04', '$.cdid': 'PySampleEdgeDevice', '$.cmid': 'Ralph'}
# """
