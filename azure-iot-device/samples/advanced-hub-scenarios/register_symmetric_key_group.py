# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import os
import asyncio
import base64
import hmac
import hashlib
from azure.iot.device.aio import ProvisioningDeviceClient

provisioning_host = os.getenv("PROVISIONING_HOST")
id_scope = os.getenv("PROVISIONING_IDSCOPE")
# This is the enrollment group name
registration_id = os.getenv("PROVISIONING_GROUP_REGISTRATION_ID")
# This is the group symmetric key
master_symmetric_key = os.getenv("PROVISIONING_MASTER_SYMMETRIC_KEY")


def derive_device_key():
    message = registration_id.encode("utf-8")
    signing_key = base64.b64decode(master_symmetric_key.encode("utf-8"))
    signed_hmac = hmac.HMAC(signing_key, message, hashlib.sha256)
    device_key_encoded = base64.b64encode(signed_hmac.digest())
    return device_key_encoded.decode("utf-8")


async def main():
    async def register_device():
        provisioning_device_client = ProvisioningDeviceClient.create_from_symmetric_key(
            provisioning_host=provisioning_host,
            registration_id=registration_id,
            id_scope=id_scope,
            symmetric_key=derive_device_key(),
        )

        return await provisioning_device_client.register()

    results = await asyncio.gather(register_device())
    registration_result = results[0]
    print("The complete registration result is")
    print(registration_result.registration_state)


if __name__ == "__main__":
    asyncio.run(main())

    # If using Python 3.6 or below, use the following code instead of asyncio.run(main()):
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(main())
    # loop.close()
