# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

import threading
import signal
import time
from azure.iot.device import IoTHubModuleClient


# Event indicating client stop
stop_event = threading.Event()


def create_client():
    # Inputs/Outputs are only supported in the context of Azure IoT Edge and module client
    # The module client object acts as an Azure IoT Edge module and interacts with an Azure IoT Edge hub
    client = IoTHubModuleClient.create_from_edge_environment()

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
    client.on_message_received = message_handler

    return client


def main():
    # The client object is used to interact with your Azure IoT hub.
    client = create_client()

    def module_termination_handler(signal, frame):
        print("IoTHubClient sample stopped by Edge")
        stop_event.set()

    # Attach a handler to do cleanup when module is terminated by Edge
    signal.signal(signal.SIGTERM, module_termination_handler)

    try:
        client.connect()
        while not stop_event.is_set():
            time.sleep(100)
    except Exception as e:
        print("Unexpected error %s " % e)
        raise
    finally:
        print("Shutting down client")
        client.shutdown()


if __name__ == "__main__":
    main()
