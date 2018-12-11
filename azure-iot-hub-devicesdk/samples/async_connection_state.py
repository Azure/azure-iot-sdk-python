# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------
import os
import asyncio
import logging
from azure.iot.hub.devicesdk.device_client import DeviceClient
from azure.iot.hub.devicesdk.auth.authentication_provider_factory import from_connection_string

logging.basicConfig(level=logging.INFO)


async def main():
    # The connection string for a device should never be stored in code. For the sake of simplicity we're using an environment variable here.
    conn_str = os.getenv("IOTHUB_DEVICE_CONNECTION_STRING")

    # The authentication provider is the object that manages the connection credentials for the client.
    auth_provider = from_connection_string(conn_str)

    # For now, the SDK only supports MQTT as a protocol. the client object is used to interact with your Azure IoT hub.
    # It needs an authentication provider to secure the communication with the hub, using either tokens or x509 certificates
    device_client = DeviceClient.from_authentication_provider(auth_provider, "mqtt")

    # The DeviceClient object will call its `on_connection_state` property every time the state of the client connection changes.
    def connection_state_callback(status):
        print("connection status: " + status)

    device_client.on_connection_state = connection_state_callback

    await device_client.connect_async()
    await device_client.disconnect_async()


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
