# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import os
import asyncio
import logging
import uuid
from azure.iot.device.aio import IoTHubModuleClient
from azure.iot.device import Message
from azure.iot.device import auth

messages_to_send = 10


async def main():
    # The "Authentication Provider" is the object in charge of creating authentication "tokens" for the device client.
    auth_provider = auth.from_environment()

    # For now, the SDK only supports MQTT as a protocol. the client object is used to interact with your Azure IoT hub.
    # It needs an Authentication Provider to secure the communication with the hub, using either tokens or x509 certificates
    device_client = IoTHubModuleClient.from_authentication_provider(auth_provider, "mqtt")

    # Connect the client.
    await device_client.connect()

    async def send_test_message(i):
        print("sending message #" + str(i))
        msg = Message("test wind speed " + str(i))
        msg.message_id = uuid.uuid4()
        msg.correlation_id = "correlation-1234"
        msg.custom_properties["tornado-warning"] = "yes"
        await device_client.send_event(msg)
        print("done sending message #" + str(i))

    # send `messages_to_send` messages in parallel
    await asyncio.gather(*[send_test_message(i) for i in range(1, messages_to_send + 1)])

    # finally, disconnect
    await device_client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())

    # If using Python 3.6 or below, use the following code instead of asyncio.run(main()):
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(main())
    # loop.close()
