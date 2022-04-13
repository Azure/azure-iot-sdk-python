# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import asyncio
from azure.iot.device.aio import ProvisioningDeviceClient
import os

messages_to_send = 10
provisioning_host = os.getenv("PROVISIONING_HOST")
id_scope = os.getenv("PROVISIONING_IDSCOPE")
registration_id = os.getenv("PROVISIONING_REGISTRATION_ID")
symmetric_key = os.getenv("PROVISIONING_SYMMETRIC_KEY")


async def main():
    provisioning_device_client = ProvisioningDeviceClient.create_from_symmetric_key(
        provisioning_host=provisioning_host,
        registration_id=registration_id,
        id_scope=id_scope,
        symmetric_key=symmetric_key,  # authenticate for DPS
    )
    # The trust bundle feature is orthogonal, we do not need to send CSR.
    registration_result = await provisioning_device_client.register()

    print("The complete registration result is")
    print(registration_result.registration_state)

    trust_bundle = registration_result.registration_state.trust_bundle
    if not trust_bundle:
        print("Trust bundle is empty")
    else:
        etag = trust_bundle.get("etag", None)
        # If the TrustBundle is updated, the application needs to update the Trusted Root.
        # Old etag and current etag can be compared to arrive at this decision.
        # New certificates in the bundle should be added to the correct store.
        # Certificates previously installed but not present in the bundle should be removed.
        if etag:
            print("New trust bundle version.")

        certificates = trust_bundle.get("certificates", None)
        if not certificates:
            print("Unexpected trust bundle response")
        else:
            count_certs = len(certificates)
            print("Trust bundle has {number} number of certificates".format(number=count_certs))
            for i in range(0, count_certs):
                certificate = certificates[i]
                if not certificate:
                    print("Unable to parse certificate")
                else:
                    cert_content = certificate.get("certificate", None)
                    if not cert_content:
                        print("Certificate has NO content")
                    else:
                        self_signed = False
                        metadata = certificate.get("metadata", None)
                        subject = metadata.get("subjectName", None)
                        issuer = metadata.get("issuerName", None)
                        if not subject or not issuer:
                            print("Invalid CA certificate")
                        elif subject == issuer:
                            # If the TrustBundle certificate is a CA root, it should be installed within the
                            # Trusted Root store.
                            self_signed = True
                            print("It is a self-signed = {}, certificate".format(self_signed))
                        else:
                            print("It is a NOT a self-signed = {}, certificate".format(self_signed))
                            print("Subject = {}".format(subject))
                            print("Issuer = {}".format(issuer))
                            print("Content of PEM = {}".format(cert_content))


if __name__ == "__main__":
    asyncio.run(main())

    # If using Python 3.6 or below, use the following code instead of asyncio.run(main()):
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(main())
    # loop.close()
