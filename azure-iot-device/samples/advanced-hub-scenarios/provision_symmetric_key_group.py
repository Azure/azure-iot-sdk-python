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
# This is the group symmetric key
master_symmetric_key = os.getenv("PROVISIONING_MASTER_SYMMETRIC_KEY")

# These are the names of the devices that will eventually show up on the IoTHub
device_id_1 = os.getenv("PROVISIONING_DEVICE_ID_1")
device_id_2 = os.getenv("PROVISIONING_DEVICE_ID_2")
device_id_3 = os.getenv("PROVISIONING_DEVICE_ID_3")

device_ids = [device_id_1, device_id_2, device_id_3]


def derive_device_key(device_id):
    """
    The unique device ID and the group master key should be encoded into "utf-8"
    After this the encoded group master key must be used to compute an HMAC-SHA256 of the encoded registration ID.
    Finally the result must be converted into Base64 format.
    The device key is the "utf-8" decoding of the above result.
    """
    message = device_id.encode("utf-8")
    signing_key = base64.b64decode(master_symmetric_key.encode("utf-8"))
    signed_hmac = hmac.HMAC(signing_key, message, hashlib.sha256)
    device_key_encoded = base64.b64encode(signed_hmac.digest())
    return device_key_encoded.decode("utf-8")


async def main():
    async def register_device(device_id):
        provisioning_device_client = ProvisioningDeviceClient.create_from_symmetric_key(
            provisioning_host=provisioning_host,
            registration_id=device_id,
            id_scope=id_scope,
            symmetric_key=derive_device_key(device_id),
        )

        return await provisioning_device_client.register()

    results = await asyncio.gather(
        register_device(device_id_1), register_device(device_id_2), register_device(device_id_3)
    )
    for index in range(0, len(device_ids)):
        registration_result = results[index]
        print("The complete state of registration result is")
        print(registration_result.registration_state)


if __name__ == "__main__":
    asyncio.run(main())

    # If using Python 3.6 or below, use the following code instead of asyncio.run(main()):
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(main())
    # loop.close()
