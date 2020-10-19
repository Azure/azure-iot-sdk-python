# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import os
import asyncio
import time
from six.moves import input
from azure.iot.device.aio import IoTHubDeviceClient

# Interval (in seconds) of how often to provide a new sastoken
NEW_TOKEN_INTERVAL = 1800


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

    # set the mesage received handler on the client
    device_client.on_message_received = message_received_handler

    # define behavior for halting the application
    def stdin_listener():
        while True:
            selection = input("Press Q to quit\n")
            if selection == "Q" or selection == "q":
                print("Quitting...")
                break

    # define behavior for providing new sastokens to prevent expiry
    async def sastoken_keepalive():
        while True:
            await asyncio.sleep(NEW_TOKEN_INTERVAL)
            sastoken = get_new_sastoken()
            device_client.update_sastoken(sastoken)

    # Run the stdin listener in the event loop
    loop = asyncio.get_running_loop()
    user_finished = loop.run_in_executor(None, stdin_listener)

    # Also run the sastoken keepalive in the event loop
    keepalive_task = asyncio.create_task(sastoken_keepalive())

    # Wait for user to indicate they are done listening for messages
    await user_finished

    # Cancel the sastoken update task
    keepalive_task.cancel()

    # Finally, disconnect
    await device_client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())

    # If using Python 3.6 or below, use the following code instead of asyncio.run(main()):
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(main())
    # loop.close()
