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
from azure.iot.device.aio import IoTHubDeviceClient
from azure.iot.device import Message
import uuid

messages_to_send = 5

provisioning_host = os.getenv("PROVISIONING_HOST")
id_scope = os.getenv("PROVISIONING_IDSCOPE")

# These are the names of the devices that will eventually show up on the IoTHub
# Please make sure that there are no spaces in these device ids.
device_id_1 = os.getenv("PROVISIONING_DEVICE_ID_1")
device_id_2 = os.getenv("PROVISIONING_DEVICE_ID_2")
device_id_3 = os.getenv("PROVISIONING_DEVICE_ID_3")

# For computation of device keys
device_ids_to_keys = {}


# NOTE : Only for illustration purposes.
# This is how a device key can be derived from the group symmetric key.
# This is just a helper function to show how it is done.
# Please don't directly store the group master key on the device.
# Follow the following method to compute the device key somewhere else.


def derive_device_key(device_id, group_symmetric_key):
    """
    The unique device ID and the group master key should be encoded into "utf-8"
    After this the encoded group master key must be used to compute an HMAC-SHA256 of the encoded registration ID.
    Finally the result must be converted into Base64 format.
    The device key is the "utf-8" decoding of the above result.
    """
    message = device_id.encode("utf-8")
    signing_key = base64.b64decode(group_symmetric_key.encode("utf-8"))
    signed_hmac = hmac.HMAC(signing_key, message, hashlib.sha256)
    device_key_encoded = base64.b64encode(signed_hmac.digest())
    return device_key_encoded.decode("utf-8")


# derived_device_key has been computed already using the helper function somewhere else
# AND NOT on this sample. Do not use the direct master key on this sample to compute device key.
derived_device_key_1 = "some_value_already_computed"
derived_device_key_2 = "some_value_already_computed"
derived_device_key_3 = "some_value_already_computed"

device_ids_to_keys[device_id_1] = derived_device_key_1
device_ids_to_keys[device_id_2] = derived_device_key_2
device_ids_to_keys[device_id_3] = derived_device_key_3


async def send_test_message(i, client):
    print("sending message # {index} for client with id {id}".format(index=i, id=client.id))
    msg = Message("test wind speed " + str(i))
    msg.message_id = uuid.uuid4()
    await client.send_message(msg)
    print("done sending message # {index} for client with id {id}".format(index=i, id=client.id))


async def main():
    async def register_device(registration_id):
        provisioning_device_client = ProvisioningDeviceClient.create_from_symmetric_key(
            provisioning_host=provisioning_host,
            registration_id=registration_id,
            id_scope=id_scope,
            symmetric_key=device_ids_to_keys[registration_id],
        )

        return await provisioning_device_client.register()

    results = await asyncio.gather(
        register_device(device_id_1), register_device(device_id_2), register_device(device_id_3)
    )

    clients_to_device_ids = {}

    for index in range(0, len(results)):
        registration_result = results[index]
        print("The complete state of registration result is")
        print(registration_result.registration_state)

        if registration_result.status == "assigned":
            device_id = registration_result.registration_state.device_id

            print(
                "Will send telemetry from the provisioned device with id {id}".format(id=device_id)
            )
            device_client = IoTHubDeviceClient.create_from_symmetric_key(
                symmetric_key=device_ids_to_keys[device_id],
                hostname=registration_result.registration_state.assigned_hub,
                device_id=registration_result.registration_state.device_id,
            )
            # Assign the Id just for print statements
            device_client.id = device_id

            clients_to_device_ids[device_id] = device_client

        else:
            print("Can not send telemetry from the provisioned device")

    # connect all the clients
    await asyncio.gather(*[client.connect() for client in clients_to_device_ids.values()])

    # send `messages_to_send` messages in parallel.
    await asyncio.gather(
        *[
            send_test_message(i, client)
            for i, client in [
                (i, client)
                for i in range(1, messages_to_send + 1)
                for client in clients_to_device_ids.values()
            ]
        ]
    )

    # disconnect all the clients
    await asyncio.gather(*[client.disconnect() for client in clients_to_device_ids.values()])


if __name__ == "__main__":
    asyncio.run(main())
