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


async def main():
    # To understand authentication providers, it is beneficial to be familiar with the Azure IoT Hub Security model:
    # https://docs.microsoft.com/en-us/azure/iot-hub/iot-hub-devguide-security

    # Authentication providers are used by the client to get the keys or certificates used
    # to connect securely to an Azure IoT hub.

    # An authentication provider object can be created from a few different things:
    # - A shared access signature:
    # sas_auth_provider = from_shared_access_signature(os.getenv("IOTHUB_DEVICE_SAS_STRING"))

    # - A symmetric key:
    key_auth_provider = from_connection_string("IOTHUB_DEVICE_CONNECTION_STRING")

    # - Pre-defined environment variables (this is especially useful when running as an Azure IoT Edge module)
    # env_auth_provider = from_environment()

    # Once the authentication provider has been created, it can be passed to the client:
    device_client = await DeviceClient.from_authentication_provider(key_auth_provider, "mqtt")

    # At that point the device client has all it needs to connect
    await device_client.connect()

    # The module client works the same way:
    # module_client = await ModuleClient.from_authentication_provider(env_auth_provider, "mqtt")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.close()
