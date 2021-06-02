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
from azure.iot.device import X509


async def main():
    hostname = os.getenv("HOSTNAME")
    # The device that has been created on the portal using X509 CA signing or Self signing capabilities
    device_id = os.getenv("DEVICE_ID")

    x509 = X509(
        cert_file=os.getenv("X509_CERT_FILE"),
        key_file=os.getenv("X509_KEY_FILE"),
        pass_phrase=os.getenv("PASS_PHRASE"),
    )

    # The client object is used to interact with your Azure IoT hub.
    device_client = IoTHubDeviceClient.create_from_x509_certificate(
        hostname=hostname, device_id=device_id, x509=x509
    )

    await device_client.connect()

    # Define behavior for receiving a message
    # NOTE: this could be a function or a coroutine
    def message_received_handler(message):
        print("the data in the message received was ")
        print(message.data)
        print("custom properties are")
        print(message.custom_properties)

    # Set the message received handler on the client
    device_client.on_message_received = message_received_handler

    # Define behavior for halting the application
    def stdin_listener():
        while True:
            try:
                selection = input("Press Q to quit\n")
                if selection == "Q" or selection == "q":
                    print("Quitting...")
                    break
            except EOFError as err:
                print("Unexpcted error occured", str(err))
                time.sleep(100)

    # Run the stdin listener in the event loop
    loop = asyncio.get_running_loop()
    user_finished = loop.run_in_executor(None, stdin_listener)

    # Wait for user to indicate they are done listening for messages
    await user_finished

    # Finally, shut down the client
    await device_client.shutdown()


if __name__ == "__main__":
    asyncio.run(main())

    # If using Python 3.6 or below, use the following code instead of asyncio.run(main()):
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(main())
    # loop.close()
