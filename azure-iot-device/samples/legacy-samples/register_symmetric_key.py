# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------


# This is for illustration purposes only. The sample will not work currently.

import os
import logging
from azure.iot.device import SymmetricKeySecurityClient
from azure.iot.device import SymmetricKeyProvisioningDeviceClient


logging.basicConfig(level=logging.ERROR)

provisioning_host = os.getenv("PROVISIONING_HOST")
id_scope = os.getenv("PROVISIONING_IDSCOPE")
registration_id = os.getenv("PROVISIONING_REGISTRATION_ID")
symmetric_key = os.getenv("PROVISIONING_SYMMETRIC_KEY")

print(provisioning_host)
print(id_scope)
print(registration_id)
print(symmetric_key)


symmetric_key_security_client = SymmetricKeySecurityClient(
    provisioning_host, registration_id, symmetric_key, id_scope
)
provisioning_device_client = SymmetricKeyProvisioningDeviceClient.create_from_security_client(
    symmetric_key_security_client, "mqtt"
)

provisioning_device_client.register()


# Output looks like
# INFO:azure.iot.device.provisioning.sk_provisioning_device_client:Successfully registered with Hub
