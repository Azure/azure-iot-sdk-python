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


async def main():
    # The client object is used to interact with your Azure IoT hub.
    module_client = IoTHubModuleClient.create_from_edge_environment()

    # connect the client.
    await module_client.connect()

    # define behavior for receiving an input message on input1
    async def input1_listener(module_client):
        while True:
            input_message = await module_client.receive_message_on_input("input1")  # blocking call
            print("the data in the message received on input1 was ")
            print(input_message.data)
            print("custom properties are")
            print(input_message.custom_properties)

    # define behavior for receiving an input message on input2
    async def input2_listener(module_client):
        while True:
            input_message = await module_client.receive_message_on_input("input2")  # blocking call
            print("the data in the message received on input2 was ")
            print(input_message.data)
            print("custom properties are")
            print(input_message.custom_properties)

    # define behavior for halting the application
    def stdin_listener():
        while True:
            selection = input("Press Q to quit\n")
            if selection == "Q" or selection == "q":
                print("Quitting...")
                break

    # Schedule task for listeners
    listeners = asyncio.gather(input1_listener(module_client), input2_listener(module_client))

    # Run the stdin listener in the event loop
    loop = asyncio.get_running_loop()
    user_finished = loop.run_in_executor(None, stdin_listener)

    # Wait for user to indicate they are done listening for messages
    await user_finished

    # Cancel listening
    listeners.cancel()

    # Finally, disconnect
    await module_client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())

    # If using Python 3.6 or below, use the following code instead of asyncio.run(main()):
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(main())
    # loop.close()
