# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import os
import asyncio
from azure.iot.device import X509
from azure.iot.device.aio import ProvisioningDeviceClient

provisioning_host = os.getenv("PROVISIONING_HOST")
id_scope = os.getenv("PROVISIONING_IDSCOPE")
registration_id = os.getenv("DPS_X509_REGISTRATION_ID")


async def main():
    x509 = X509(
        cert_file=os.getenv("X509_CERT_FILE"),
        key_file=os.getenv("X509_KEY_FILE"),
        pass_phrase=os.getenv("PASS_PHRASE"),
    )
    provisioning_device_client = ProvisioningDeviceClient.create_from_x509_certificate(
        provisioning_host=provisioning_host,
        registration_id=registration_id,
        id_scope=id_scope,
        x509=x509,
    )

    registration_result = await provisioning_device_client.register()

    print("The complete registration result is")
    print(registration_result.registration_state)


if __name__ == "__main__":
    asyncio.run(main())

    # If using Python 3.6 or below, use the following code instead of asyncio.run(main()):
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(main())
    # loop.close()
