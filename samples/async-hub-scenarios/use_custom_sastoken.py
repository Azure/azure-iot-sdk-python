# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import asyncio
from azure.iot.device.aio import IoTHubDeviceClient


# NOTE: This code needs to be completed in order to work.
# Fill out the get_new_sastoken() method to return a NEW custom sastoken from your solution.
# It must return a unique value each time it is called.
def get_new_sastoken():
    pass


async def main():

    # Get a sastoken you generated
    sastoken = get_new_sastoken()
    # The client object is used to interact with your Azure IoT hub.
    device_client = IoTHubDeviceClient.create_from_sastoken(sastoken)

    # connect the client.
    await device_client.connect()

    # define behavior for receiving a message
    # NOTE: this could be a function or a coroutine
    def message_received_handler(message):
        print("the data in the message received was ")
        print(message.data)
        print("custom properties are")
        print(message.custom_properties)
        print("content Type: {0}".format(message.content_type))
        print("")

    # define behavior for updating sastoken
    async def sastoken_update_handler():
        print("Updating SAS Token...")
        sastoken = get_new_sastoken()
        await device_client.update_sastoken(sastoken)
        print("SAS Token updated")

    # set the message received handler on the client
    device_client.on_message_received = message_received_handler
    # set the sastoken update handler on the client
    device_client.on_new_sastoken_required = sastoken_update_handler

    # define behavior for halting the application
    def stdin_listener():
        while True:
            selection = input("Press Q to quit\n")
            if selection == "Q" or selection == "q":
                print("Quitting...")
                break

    # Run the stdin listener in the event loop
    loop = asyncio.get_running_loop()
    user_finished = loop.run_in_executor(None, stdin_listener)

    # Wait for user to indicate they are done listening for messages
    await user_finished

    # Finally, shut down the client
    await device_client.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
