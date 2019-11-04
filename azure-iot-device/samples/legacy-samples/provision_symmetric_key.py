# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import os
from azure.iot.device import ProvisioningDeviceClient

# TODO Remove logging
import logging

logging.basicConfig(level=logging.DEBUG)

provisioning_host = os.getenv("PROVISIONING_HOST")
id_scope = os.getenv("PROVISIONING_IDSCOPE")
registration_id = os.getenv("PROVISIONING_REGISTRATION_ID")
symmetric_key = os.getenv("PROVISIONING_SYMMETRIC_KEY")

provisioning_device_client = ProvisioningDeviceClient.create_from_symmetric_key(
    provisioning_host=provisioning_host,
    registration_id=registration_id,
    id_scope=id_scope,
    symmetric_key=symmetric_key,
)

registration_result = provisioning_device_client.register()
# The result can be directly printed to view the important details.
print(registration_result)

# Individual attributes can be seen as well
print("The status was :-")
print(registration_result.status)
print("The etag is :-")
print(registration_result.registration_state.etag)
