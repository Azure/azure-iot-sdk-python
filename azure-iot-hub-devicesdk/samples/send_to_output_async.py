# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import asyncio
import time
import uuid
from azure.iot.hub.devicesdk.aio import ModuleClient
from azure.iot.hub.devicesdk import Message
from azure.iot.hub.devicesdk import auth

messages_to_send = 10


async def main():
    # The "Authentication Provider" is the object in charge of creating authentication "tokens" for the module client.
    auth_provider = auth.from_environment()
    # For now, the SDK only supports MQTT as a protocol.
    # Inputs/Ouputs are only supported in the context of Azure IoT Edge and module client
    # The module client object acts as an Azure IoT Edge module and interacts with an Azure IoT Edge hub
    # It needs an Authentication Provider to secure the communication with the Edge hub.
    # This authentication provider is created from environment & delegates token generation to iotedged.
    module_client = ModuleClient.from_authentication_provider(auth_provider, "mqtt")

    # Connect the client.
    await module_client.connect()

    # Send a filled out Message object
    async def send_test_message(i):
        print("sending message #" + str(i))
        msg = Message("test wind speed " + str(i))
        msg.message_id = uuid.uuid4()
        msg.correlation_id = "correlation-1234"
        msg.custom_properties["tornado-warning"] = "yes"
        await module_client.send_to_output(msg, "twister")
        print("done sending message #" + str(i))

    await asyncio.gather(*[send_test_message(i) for i in range(1, messages_to_send)])

    # finally, disconnect
    module_client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())

    # If using Python 3.6 or below, use the following code instead of asyncio.run(main()):
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(main())
    # loop.close()
