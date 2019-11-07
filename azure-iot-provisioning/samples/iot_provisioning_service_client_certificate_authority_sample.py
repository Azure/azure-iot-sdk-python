# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import sys
import os
from azure.iot.provisioning import IoTProvisioningServiceClient

connection_str = os.getenv("IOT_PROVISIONING_SERVICE_CONNECTION_STRING")
certificate_authority_name_1 = os.getenv("IOT_PROVISIONING_CERTIFICATE_AUTHORITY_NAME_1")
certificate_authority_name_2 = os.getenv("IOT_PROVISIONING_CERTIFICATE_AUTHORITY_NAME_2")
certificate_authority_1 = os.getenv("IOT_PROVISIONING_CERTIFICATE_AUTHORITY_1")
certificate_authority_2 = os.getenv("IOT_PROVISIONING_CERTIFICATE_AUTHORITY_2")

try:
    # Create IoTProvisioningServiceClient
    iot_provisioning_service_client = IoTProvisioningServiceClient(connection_str)

    # Create certificate authority
    certificate_authority_created = iot_provisioning_service_client.create_certificate_authority(
        certificate_authority_name_1, certificate_authority_1
    )
    print("Certificate authority 1 {0}: ".format(certificate_authority_1.name))

    # Replace certificate authority
    certificate_authority_updated = iot_provisioning_service_client.replace_certificate_authority(
        certificate_authority_name_2, certificate_authority_2, certificate_authority_created.etag
    )
    print("Certificate authority 2 {0}: ".format(certificate_authority_2.name))

    # Get the certificate authority
    certificate_authority_get = iot_provisioning_service_client.get_certificate_authority(
        certificate_authority_name_2
    )
    print("Current certificate authority {0}: ".format(certificate_authority_get))

    # Delete certificate authority
    iot_provisioning_service_client.delete_certificate_authority(
        certificate_authority_get.name, certificate_authority_get.etag
    )

except Exception as ex:
    print("Unexpected error {0}".format(ex))
except KeyboardInterrupt:
    print("iot_provisioning_service_client_sample stopped")
