# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import os
import asyncio
from azure.iot.device.aio import IoTHubDeviceClient, IoTHubModuleClient

from azure.iot.device import auth

# To understand authentication providers in depth, it is beneficial to be familiar with the Azure IoT Hub Security model:
# https://docs.microsoft.com/en-us/azure/iot-hub/iot-hub-devguide-security

# In a nutshell Authentication providers are used by the client to get the keys or certificates used
# to connect securely to an Azure IoT hub.
# An authentication provider object can be created in a few different ways:
# Below we show 3 different methods of creating auth providers
# Once the authentication provider has been created, it can be passed to the client
# (which could be a device client or module client)
# At this point the client has everything it needs and it only has to connect to the IoT Hub.


async def create_shared_access_sig_auth_provider():
    """
    This creates an authentication provider from the pre-generated shared access signature of the device or module
    """
    sas_auth_provider = auth.from_shared_access_signature(os.getenv("IOTHUB_DEVICE_SAS_STRING"))
    device_client_sas = IoTHubDeviceClient.from_authentication_provider(sas_auth_provider, "mqtt")
    print("Authenticating with SharedAccessSignature string...")
    await device_client_sas.connect()
    print("Successfully authenticated!")


async def create_symmetric_key_auth_provider():
    """
    This creates an authentication provider from the connection string of the device or module
    """
    key_auth_provider = auth.from_connection_string(os.getenv("IOTHUB_DEVICE_CONNECTION_STRING"))
    device_client_key = IoTHubDeviceClient.from_authentication_provider(key_auth_provider, "mqtt")
    print("Authenticating with Device Connection String...")
    await device_client_key.connect()
    print("Successfully authenticated!")


if __name__ == "__main__":
    # Here we use option 1, but option 2 and 3 can be used interchangeably.
    asyncio.run(create_shared_access_sig_auth_provider())

    # If using Python 3.6 or below, use the following code instead of the above:
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(create_shared_access_sig_auth_provider())
    # loop.close()
