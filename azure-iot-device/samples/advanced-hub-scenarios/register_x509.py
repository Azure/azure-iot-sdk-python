# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------


# This is for illustration purposes only. The sample will not work currently.

import os
import logging
import asyncio
from azure.iot.device import X509SecurityClient, X509
from azure.iot.device.aio import X509ProvisioningDeviceClient


logging.basicConfig(level=logging.INFO)

provisioning_host = os.getenv("PROVISIONING_HOST")
id_scope = os.getenv("PROVISIONING_IDSCOPE")
registration_id = os.getenv("DPS_X509_REGISTRATION_ID")


async def main():
    async def register_device():
        x509_cert = X509(
            cert_file=os.getenv("X509_CERT_FILE"), key_file=os.getenv("X509_KEY_FILE")
        )
        x509_security_client = X509SecurityClient(
            provisioning_host, registration_id, id_scope, x509_cert
        )

        provisioning_device_client = X509ProvisioningDeviceClient.create_from_security_client(
            x509_security_client, "mqtt"
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
