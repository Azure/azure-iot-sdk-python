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
import sys

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(thread)s %(funcName)s %(message)s",
    filename="certificate_issuance.log",
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

messages_to_send = 3
provisioning_host = os.getenv("PROVISIONING_HOST")
id_scope = os.getenv("PROVISIONING_IDSCOPE")
registration_id = os.getenv("PROVISIONING_REGISTRATION_ID")

dps_x509_cert_file = os.getenv("PROVISIONING_X509_CERT_FILE")
dps_x509_key_file = os.getenv("PROVISIONING_X509_KEY_FILE")
# Or
dps_sas_key = os.getenv("PROVISIONING_SYMMETRIC_KEY")

dps_csr_data = os.getenv("PROVISIONING_CSR")
dps_csr_key_file = os.getenv("PROVISIONING_CSR_KEY_FILE")
dps_issued_cert_file = os.getenv("PROVISIONING_ISSUED_CERT_FILE")

iothub_csr_data = os.getenv("IOTHUB_CSR")
iothub_csr_key_file = dps_csr_key_file  # Must be the same.
iothub_issued_cert_file = os.getenv("IOTHUB_ISSUED_CERT_FILE")


def x509_certificate_to_pem_format(certificate_info):
    begin_cert_header = "-----BEGIN CERTIFICATE-----\r\n"
    end_cert_footer = "\r\n-----END CERTIFICATE-----"
    return begin_cert_header + certificate_info + end_cert_footer


def write_certificate_data_to_pem_file(certificate_info, certificate_file_path):
    with open(certificate_file_path, "w") as out_cert_pem:
        out_cert_pem.write(x509_certificate_to_pem_format(certificate_info))


async def connect_device_client_and_send_test_messages(
    iothub_hostname, device_id, device_certificate, device_private_key
) -> IoTHubDeviceClient:
    iot_hub_x509 = X509(
        cert_file=device_certificate,
        key_file=device_private_key,
    )

    device_client = IoTHubDeviceClient.create_from_x509_certificate(
        hostname=iothub_hostname,
        device_id=device_id,
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

    return device_client


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
        print(
            "Either provide PROVISIONING_X509_CERT_FILE and PROVISIONING_X509_KEY_FILE or PROVISIONING_SYMMETRIC_KEY"
        )
        sys.exit(1)

    # set the CSR on the client
    provisioning_device_client.client_certificate_signing_request = dps_csr_data

    registration_result = await provisioning_device_client.register()

    print("The complete registration result is {}".format(registration_result.registration_state))

    write_certificate_data_to_pem_file(
        registration_result.registration_state.issued_client_certificate[
            0
        ],  # Use only leaf-certificate.
        dps_issued_cert_file,
    )

    if registration_result.status == "assigned":
        print("Will send telemetry from the provisioned device")

        device_client = await connect_device_client_and_send_test_messages(
            iothub_hostname=registration_result.registration_state.assigned_hub,
            device_id=registration_result.registration_state.device_id,
            device_certificate=dps_issued_cert_file,
            device_private_key=dps_csr_key_file,
        )

        if iothub_csr_data is not None and iothub_issued_cert_file is not None:

            print("Performing Azure IoT Hub certificate re-issuance")

            # Get new issued certificate from IoT Hub
            csr_response = await device_client.send_certificate_signing_request(
                iothub_csr_data, "*"
            )
            print(
                "IoT Hub certificate re-issuance completed. Status-code={}".format(
                    csr_response.status_code
                )
            )

            # Now, disconnect and reconnect with the new issued certificate
            print("Reconnecting to Azure IoT Hub with re-issued certificate")

            await device_client.shutdown()

            write_certificate_data_to_pem_file(
                csr_response.certificates[0],  # Use only leaf-certificate.
                iothub_issued_cert_file,
            )

            device_client = await connect_device_client_and_send_test_messages(
                iothub_hostname=registration_result.registration_state.assigned_hub,
                device_id=registration_result.registration_state.device_id,
                device_certificate=iothub_issued_cert_file,
                device_private_key=iothub_csr_key_file,
            )
        else:
            print("Skipping Azure IoT Hub certificate re-issuance")

        # Finally, disconnect device client.
        await device_client.shutdown()
    else:
        print("Can not send telemetry from the provisioned device")


if __name__ == "__main__":
    asyncio.run(main())
