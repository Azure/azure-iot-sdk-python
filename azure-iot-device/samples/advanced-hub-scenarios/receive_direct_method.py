# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import os
import asyncio
import json
import logging
import threading
from six.moves import input
from azure.iot.device.aio import IoTHubDeviceClient
from azure.iot.device import auth

logging.basicConfig(level=logging.ERROR)


async def main():
    # The connection string for a device should never be stored in code. For the sake of simplicity we're using an environment variable here.
    conn_str = os.getenv("IOTHUB_DEVICE_CONNECTION_STRING")
    # The "Authentication Provider" is the object in charge of creating authentication "tokens" for the device client.
    auth_provider = auth.from_connection_string(conn_str)
    # For now, the SDK only supports MQTT as a protocol. the client object is used to interact with your Azure IoT hub.
    # It needs an Authentication Provider to secure the communication with the hub, using either tokens or x509 certificates
    device_client = IoTHubDeviceClient.from_authentication_provider(auth_provider, "mqtt")

    # connect the client.
    await device_client.connect()

    # define behavior for handling methods
    async def method1_listener(device_client):
        while True:
            method_request = await device_client.receive_method("method1")  # Wait for method1 calls
            payload = json.dumps({"result": True, "data": "some data"})  # set response payload
            status = 200  # set return status code
            print("executed method1")
            await device_client.send_method_response(
                method_request, payload, status
            )  # send response

    async def method2_listener(device_client):
        while True:
            method_request = await device_client.receive_method("method2")  # Wait for method2 calls
            payload = json.dumps({"result": True, "data": 1234})  # set response payload
            status = 200  # set return status code
            print("executed method2")
            await device_client.send_method_response(
                method_request, payload, status
            )  # send response

    async def generic_method_listener(device_client):
        while True:
            method_request = await device_client.receive_method()  # Wait for unknown method calls
            payload = json.dumps(
                {"result": False, "data": "unknown method"}  # set response payload
            )
            status = 400  # set return status code
            print("executed unknown method: " + method_request.name)
            await device_client.send_method_response(
                method_request, payload, status
            )  # send response

    # define behavior for halting the application
    def stdin_listener():
        while True:
            selection = input("Press Q to quit\n")
            if selection == "Q" or selection == "q":
                print("Quitting...")
                break

    # Schedule tasks for Method Listener
    listeners = asyncio.gather(
        method1_listener(device_client),
        method2_listener(device_client),
        generic_method_listener(device_client),
    )

    # Run the stdin listener in the event loop
    loop = asyncio.get_running_loop()
    user_finished = loop.run_in_executor(None, stdin_listener)

    # Wait for user to indicate they are done listening for method calls
    await user_finished

    # Cancel listening
    listeners.cancel()

    # Finally, disconnect
    await device_client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())

    # If using Python 3.6 or below, use the following code instead of asyncio.run(main()):
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(main())
    # loop.close()
