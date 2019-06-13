# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------


# This is for illustration purposes only. The sample will not work currently.

import os
import logging

from azure.iot.device import X509SecurityClient
from azure.iot.device.common import X509
from azure.iot.device import X509ProvisioningDeviceClient


logging.basicConfig(level=logging.INFO)

provisioning_host = os.getenv("PROVISIONING_HOST")
id_scope = os.getenv("PROVISIONING_IDSCOPE")
registration_id = os.getenv("DPS_X509_REGISTRATION_ID")

x509_cert = X509(cert_file=os.getenv("X509_CERT_FILE"), key_file=os.getenv("X509_KEY_FILE"))
x509_security_client = X509SecurityClient(provisioning_host, registration_id, id_scope, x509_cert)

provisioning_device_client = X509ProvisioningDeviceClient.create_from_security_client(
    x509_security_client, "mqtt"
)

provisioning_device_client.register()


# Output looks like
# INFO:azure.iot.device.provisioning.sk_provisioning_device_client:Successfully registered with Hub
