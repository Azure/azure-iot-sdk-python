# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import asyncio
from azure.iot.device.aio import ProvisioningDeviceClient
import os
from azure.iot.device.aio import IoTHubDeviceClient
from azure.iot.device import Message
import uuid
from azure.iot.device import X509
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

messages_to_send = 10
provisioning_host = os.getenv("PROVISIONING_HOST")
id_scope = os.getenv("PROVISIONING_IDSCOPE")
registration_id = os.getenv("PROVISIONING_REGISTRATION_ID")

dps_x509_cert_file = os.getenv("PROVISIONING_X509_CERT_FILE")
dps_x509_key_file = os.getenv("PROVISIONING_X509_KEY_FILE")

dps_sas_key = os.getenv("PROVISIONING_SAS_KEY")

csr_data = os.getenv("PROVISIONING_CSR")
csr_key_file = os.getenv("PROVISIONING_CSR_KEY_FILE")
issued_cert_file = os.getenv("PROVISIONING_ISSUED_CERT_FILE")

def x509_certificate_list_to_pem(cert_list):
    begin_cert_header = "-----BEGIN CERTIFICATE-----\r\n"
    end_cert_footer = "\r\n-----END CERTIFICATE-----"
    separator = end_cert_footer + "\r\n" + begin_cert_header
    return begin_cert_header + separator.join(cert_list) + end_cert_footer

async def main():
    if dps_x509_cert_file is not None and dps_x509_key_file is not None:
        print("Using x509 authentication")
        dps_x509 = X509(
            cert_file=dps_x509_cert_file,
            key_file=dps_x509_key_file,
        )

        provisioning_device_client = ProvisioningDeviceClient.create_from_x509_certificate(
            provisioning_host=provisioning_host,
            registration_id=registration_id,
            id_scope=id_scope,
            x509=dps_x509,
        )
    elif dps_sas_key is not None:
        print("Using symmetric-key authentication")
        provisioning_device_client = ProvisioningDeviceClient.create_from_symmetric_key(
            provisioning_host=provisioning_host,
            registration_id=registration_id,
            id_scope=id_scope,
            symmetric_key=dps_sas_key,
        )
    else:
        print("Either provide PROVISIONING_X509_CERT_FILE and PROVISIONING_X509_KEY_FILE or PROVISIONING_SAS_KEY")
        sys.exit(1)

    # set the CSR on the client
    provisioning_device_client.client_certificate_signing_request = csr_data

    registration_result = await provisioning_device_client.register()

    print("The complete registration result is")
    print(registration_result.registration_state)

    with open(issued_cert_file, "w") as out_ca_pem:
        # Write the issued certificate on the file.
        out_ca_pem.write(x509_certificate_list_to_pem(registration_result.registration_state.issued_client_certificate))

    if registration_result.status == "assigned":
        print("Will send telemetry from the provisioned device")

        iot_hub_x509 = X509(
            cert_file=issued_cert_file,
            key_file=csr_key_file,
        )

        device_client = IoTHubDeviceClient.create_from_x509_certificate(
            hostname=registration_result.registration_state.assigned_hub,
            device_id=registration_result.registration_state.device_id,
            x509=iot_hub_x509,
        )

        # Connect the client.
        await device_client.connect()

        async def send_test_message(i):
            print("sending message #" + str(i))
            msg = Message("test wind speed " + str(i))
            msg.message_id = uuid.uuid4()
            await device_client.send_message(msg)
            print("done sending message #" + str(i))

        # send `messages_to_send` messages in parallel
        await asyncio.gather(*[send_test_message(i) for i in range(1, messages_to_send + 1)])

        # finally, disconnect
        await device_client.shutdown()
    else:
        print("Can not send telemetry from the provisioned device")


if __name__ == "__main__":
    asyncio.run(main())

    # If using Python 3.6 or below, use the following code instead of asyncio.run(main()):
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(main())
    # loop.close()
