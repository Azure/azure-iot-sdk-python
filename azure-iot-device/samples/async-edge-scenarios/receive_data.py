# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import asyncio
import signal
import threading
from azure.iot.device.aio import IoTHubModuleClient
from azure.iot.device import MethodResponse


# Event indicating client stop
stop_event = threading.Event()


def create_client():
    # The client object is used to interact with your Azure IoT hub.
    client = IoTHubModuleClient.create_from_edge_environment()

    # Define behavior for receiving an input message on input1 and input2
    # NOTE: this could be a coroutine or a function
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

    # Define behavior for receiving a twin desired properties patch
    # NOTE: this could be a coroutine or function
    def twin_patch_handler(patch):
        print("the data in the desired properties patch was: {}".format(patch))

    # Define behavior for receiving methods
    async def method_handler(method_request):
        if method_request.name == "get_data":
            print("Received request for data")
            method_response = MethodResponse.create_from_method_request(
                method_request, 200, "some data"
            )
            await client.send_method_response(method_response)
        else:
            print("Unknown method request received: {}".format(method_request.name))
            method_response = MethodResponse.create_from_method_request(method_request, 400, None)
            await client.send_method_response(method_response)

    # set the received data handlers on the client
    client.on_message_received = message_handler
    client.on_twin_desired_properties_patch_received = twin_patch_handler
    client.on_method_request_received = method_handler

    return client


async def run_sample(client):
    # Customize this coroutine to do whatever tasks the module initiates
    # e.g. sending messages
    await client.connect()
    while not stop_event.is_set():
        await asyncio.sleep(1000)


def main():
    # NOTE: Client is implicitly connected due to the handler being set on it
    client = create_client()

    # Define a handler to cleanup when module is is terminated by Edge
    def module_termination_handler(signal, frame):
        print("IoTHubClient sample stopped by Edge")
        stop_event.set()

    # Set the Edge termination handler
    signal.signal(signal.SIGTERM, module_termination_handler)

    # Run the sample
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(run_sample(client))
    except Exception as e:
        print("Unexpected error %s " % e)
        raise
    finally:
        print("Shutting down IoT Hub Client...")
        loop.run_until_complete(client.shutdown())
        loop.close()


if __name__ == "__main__":
    main()
