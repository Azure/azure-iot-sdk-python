# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import os
import asyncio
from azure.iot.hub.devicesdk.aio import DeviceClient, ModuleClient

from azure.iot.hub.devicesdk.auth.authentication_provider_factory import (
    from_shared_access_signature,
    from_connection_string,
    from_environment,
)

# To understand authentication providers in depth, it is beneficial to be familiar with the Azure IoT Hub Security model:
# https://docs.microsoft.com/en-us/azure/iot-hub/iot-hub-devguide-security

# In a nutshell Authentication providers are used by the client to get the keys or certificates used
# to connect securely to an Azure IoT hub.
# An authentication provider object can be created in a few different ways:
# Below we show 3 different methods of creating auth providers
# Once the authentication provider has been created, it can be passed to the client
# (which could be a device client or module client)
# At this point the client has everything it needs and it only has to connect to the IoT Hub.


def alert_after_connection(status):
    print("I am at {} state".format(status))


async def create_shared_access_sig_auth_provider():
    """
    This creates an authentication provider from the pre-generated shared access signature of the device or module
    """
    sas_auth_provider = from_shared_access_signature(os.getenv("IOTHUB_DEVICE_SAS_STRING"))
    device_client_sas = await DeviceClient.from_authentication_provider(sas_auth_provider, "mqtt")
    device_client_sas.on_connection_state = alert_after_connection
    await device_client_sas.connect()


async def create_symmetric_key_auth_provider():
    """
    This creates an authentication provider from the connection string of the device or module
    """
    key_auth_provider = from_connection_string(os.getenv("IOTHUB_DEVICE_CONNECTION_STRING"))
    device_client_key = await DeviceClient.from_authentication_provider(key_auth_provider, "mqtt")
    await device_client_key.connect()


async def create_environ_auth_provider():
    """
    This creates an authentication provider from the system's environment variables.
    """
    env_auth_provider = from_environment()
    device_client_env = await DeviceClient.from_authentication_provider(env_auth_provider, "mqtt")
    await device_client_env.connect()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    # Here we use option 1, but option 2 and 3 can be used interchangeably.
    loop.run_until_complete(create_shared_access_sig_auth_provider())
    loop.close()
