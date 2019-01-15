# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------
import os
import asyncio
import logging
import uuid
from azure.iot.hub.devicesdk import DeviceClient, Message
from azure.iot.hub.devicesdk.auth.authentication_provider_factory import (
    from_connection_string,
)  # this is a overlong import, fix

logging.basicConfig(level=logging.INFO)

messages_to_send = 10


async def main():
    # The connection string for a device should never be stored in code. For the sake of simplicity we're using an environment variable here.
    conn_str = os.getenv("IOTHUB_DEVICE_CONNECTION_STRING")

    # The "Authentication Provider" is the object in charge of creating authentication "tokens" for the device client.
    # TODO: open question: do we want async versions of from_connection_string and from_authentication_provider?
    auth_provider = from_connection_string(conn_str)

    # For now, the SDK only supports MQTT as a protocol. the client object is used to interact with your Azure IoT hub.
    # It needs an Authentication Provider to secure the communication with the hub, using either tokens or x509 certificates
    device_client = await DeviceClient.from_authentication_provider(auth_provider, "mqtt")

    # The connection state callback allows us to detect when the client is connected and disconnected:
    def connection_state_callback(status):
        print("connection status: " + status)

    # Register the connection state callback with the client...
    # TODO: open question: connection_state_callback is a sync callback.  Do we want to support async callbacks?
    device_client.on_connection_state = connection_state_callback

    # ... and connect the client.
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
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.close()
