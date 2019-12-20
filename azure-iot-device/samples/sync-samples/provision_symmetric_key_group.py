# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import os
import base64
import hmac
import hashlib
from azure.iot.device import ProvisioningDeviceClient

provisioning_host = os.getenv("PROVISIONING_HOST")
id_scope = os.getenv("PROVISIONING_IDSCOPE")

# These are the names of the devices that will eventually show up on the IoTHub
device_id_1 = os.getenv("PROVISIONING_DEVICE_ID_1")
device_id_2 = os.getenv("PROVISIONING_DEVICE_ID_2")
device_id_3 = os.getenv("PROVISIONING_DEVICE_ID_3")

# For computation of device keys
device_ids_to_keys = {}

# Keep a dictionary for results
results = {}

# NOTE : Only for illustration purposes.
# This is how a device key can be derived from the group symmetric key.
# This is just a helper function to show how it is done.
# Please don't directly store the group key on the device.
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
device_ids_to_keys[device_id_1] = derived_device_key_2
device_ids_to_keys[device_id_1] = derived_device_key_3


def register_device(registration_id):

    provisioning_device_client = ProvisioningDeviceClient.create_from_symmetric_key(
        provisioning_host=provisioning_host,
        registration_id=registration_id,
        id_scope=id_scope,
        symmetric_key=device_ids_to_keys[registration_id],
    )

    return provisioning_device_client.register()


for device_id in device_ids_to_keys:
    registration_result = register_device(registration_id=device_id)
    results[device_id] = registration_result


for device_id in device_ids_to_keys:
    # The result can be directly printed to view the important details.
    registration_result = results[device_id]
    print(registration_result)
    # Individual attributes can be seen as well
    print("The request_id was :-")
    print(registration_result.request_id)
    print("The etag is :-")
    print(registration_result.registration_state.etag)
    print("\n")
