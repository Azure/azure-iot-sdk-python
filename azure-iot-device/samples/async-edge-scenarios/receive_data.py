# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import os
import asyncio
from six.moves import input
import threading
from azure.iot.device.aio import IoTHubModuleClient
from azure.iot.device import MethodResponse


async def main():
    # The client object is used to interact with your Azure IoT hub.
    module_client = IoTHubModuleClient.create_from_edge_environment()

    # connect the client.
    await module_client.connect()

    # event indicating when user is finished
    finished = threading.Event()

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
            await module_client.send_method_response(method_response)
        elif method_request.name == "shutdown":
            print("Received request to shut down")
            method_response = MethodResponse.create_from_method_request(method_request, 200, None)
            await module_client.send_method_response(method_response)
            # Setting this event will cause client shutdown
            finished.set()
        else:
            print("Unknown method request received: {}".format(method_request.name))
            method_response = MethodResponse.create_from_method_request(method_request, 400, None)
            await module_client.send_method_response(method_response)

    # set the received data handlers on the client
    module_client.on_message_received = message_handler
    module_client.on_twin_desired_properties_patch_received = twin_patch_handler
    module_client.on_method_request_received = method_handler

    # This will trigger when a MethodRequest for "shutdown" is sent
    finished.wait()
    # Once it is received, shut down the client
    await module_client.shutdown()


if __name__ == "__main__":
    asyncio.run(main())

    # If using Python 3.6 or below, use the following code instead of asyncio.run(main()):
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(main())
    # loop.close()
