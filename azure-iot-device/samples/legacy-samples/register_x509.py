# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------


# This is for illustration purposes only. The sample will not work currently.

import os
from azure.iot.device import ProvisioningDeviceClient, X509

provisioning_host = os.getenv("PROVISIONING_HOST")
id_scope = os.getenv("PROVISIONING_IDSCOPE")
registration_id = os.getenv("DPS_X509_REGISTRATION_ID")

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

provisioning_device_client.register()
