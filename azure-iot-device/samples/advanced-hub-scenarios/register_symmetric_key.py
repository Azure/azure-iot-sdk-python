# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import os
import logging
import asyncio
from azure.iot.device import SymmetricKeySecurityClient
from azure.iot.device.aio import SymmetricKeyProvisioningDeviceClient


logging.basicConfig(level=logging.DEBUG)

provisioning_host = os.getenv("PROVISIONING_HOST")
id_scope = os.getenv("PROVISIONING_IDSCOPE")
registration_id = os.getenv("PROVISIONING_REGISTRATION_ID")
symmetric_key = os.getenv("PROVISIONING_SYMMETRIC_KEY")


async def main():
    async def register_device():
        symmetric_key_security_client = SymmetricKeySecurityClient(
            provisioning_host, registration_id, symmetric_key, id_scope
        )
        provisioning_device_client = SymmetricKeyProvisioningDeviceClient.create_from_security_client(
            symmetric_key_security_client, "mqtt"
        )

        await provisioning_device_client.register()

    await asyncio.gather(register_device())


if __name__ == "__main__":
    asyncio.run(main())

    # If using Python 3.6 or below, use the following code instead of asyncio.run(main()):
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(main())
    # loop.close()

# Output looks like
# INFO:azure.iot.device.provisioning.sk_provisioning_device_client:Successfully registered with Hub
