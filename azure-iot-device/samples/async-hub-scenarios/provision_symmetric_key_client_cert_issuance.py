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
import logging
from azure.iot.device import X509

messages_to_send = 10
provisioning_host = os.getenv("PROVISIONING_HOST")
id_scope = os.getenv("PROVISIONING_IDSCOPE")
registration_id = os.getenv("PROVISIONING_REGISTRATION_ID")
symmetric_key = os.getenv("PROVISIONING_SYMMETRIC_KEY")

logging.basicConfig(level=logging.DEBUG, filename="newfile.log")


async def main():
    provisioning_device_client = ProvisioningDeviceClient.create_from_symmetric_key(
        provisioning_host=provisioning_host,
        registration_id=registration_id,
        id_scope=id_scope,
        symmetric_key=symmetric_key,  # authenticate for DPS
        client_certificate_csr="some csr data",  # kwarg
    )

    registration_result = await provisioning_device_client.register()

    print("The complete registration result is")
    print(registration_result.registration_state)

    print("the issued certificate")
    # include new field called "issued_client_certificate" in the model of registration result.
    print(registration_result.registration_state.issued_client_certificate)

    with open("device_cert.pem", "w") as out_ca_pem:
        cert_data = registration_result.registration_state.issued_client_certificate
        # not sure if i need to do this
        # cert_pem_data = str(base64.b64decode(cert_data), "ascii")
        out_ca_pem.write(cert_data)

    if registration_result.status == "assigned":
        print("Will send telemetry from the provisioned device")

        x509 = X509(
            cert_file=os.getenv("X509_CERT_FILE"),
            key_file=os.getenv("X509_KEY_FILE"),
            pass_phrase=os.getenv("PASS_PHRASE"),
        )

        device_client = IoTHubDeviceClient.create_from_x509_certificate(
            hostname=registration_result.registration_state.assigned_hub,
            device_id=registration_result.registration_state.device_id,
            x509=x509,
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
        await device_client.disconnect()
    else:
        print("Can not send telemetry from the provisioned device")


if __name__ == "__main__":
    asyncio.run(main())

    # If using Python 3.6 or below, use the following code instead of asyncio.run(main()):
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(main())
    # loop.close()
