# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

from provisioning_e2e.service_helper import Helper, connection_string_to_hostname
from azure.iot.device.aio import ProvisioningDeviceClient, IoTHubDeviceClient
from azure.iot.device.common import X509

from dev_utils.provisioningservice.protocol import models
from dev_utils.provisioningservice.client import ProvisioningServiceClient

import pytest
import logging
import os
import uuid
import base64
import hmac
import hashlib

from . import path_adjust  # noqa: F401

# Refers to an item in "scripts" in the root. This is made to work via the above path_adjust
from create_x509_chain_crypto import (
    before_cert_creation_from_pipeline,
    call_intermediate_cert_and_device_cert_creation_from_pipeline,
    delete_directories_certs_created_from_pipeline,
    create_ec_private_key,
    create_csr,
)

pytestmark = pytest.mark.asyncio
logging.basicConfig(level=logging.DEBUG)

intermediate_common_name = "e2edpswingardium"
intermediate_password = "leviosa"
device_common_name = "e2edpsexpecto" + str(uuid.uuid4())
device_password = "patronum"

service_client = ProvisioningServiceClient.create_from_connection_string(
    os.getenv("PROVISIONING_SERVICE_CONNECTION_STRING")
)
device_registry_helper = Helper(os.getenv("IOTHUB_CONNECTION_STRING"))
linked_iot_hub = connection_string_to_hostname(os.getenv("IOTHUB_CONNECTION_STRING"))

PROVISIONING_HOST = os.getenv("PROVISIONING_DEVICE_ENDPOINT")
ID_SCOPE = os.getenv("PROVISIONING_DEVICE_IDSCOPE")
ADR_CERT_MGMT_POLICY_NAME = os.getenv("ADR_CERT_MGMT_POLICY_NAME")

type_to_device_indices = {
    "group_intermediate": [3, 4],
    "group_symmetric": [6, 7],
}


@pytest.fixture(scope="module", autouse=True)
def before_all_tests(request):
    logging.info("set up certificates before cert related tests")
    before_cert_creation_from_pipeline()
    call_intermediate_cert_and_device_cert_creation_from_pipeline(
        intermediate_common_name=intermediate_common_name,
        device_common_name=device_common_name,
        ca_password=os.getenv("PROVISIONING_ROOT_PASSWORD"),
        intermediate_password=intermediate_password,
        device_password=device_password,
        device_count=8,
    )

    def after_module():
        logging.info("tear down certificates after cert related tests")
        delete_directories_certs_created_from_pipeline()

    request.addfinalizer(after_module)


# TODO : Don't do mqttws as it conflicts with SAME cert problem, Need complete set of new certs with mqtts
@pytest.mark.it(
    "A group of devices get provisioned to the linked IoTHub with device_ids equal to the individual registration_ids inside a group enrollment that has been created with intermediate X509 authentication"
)
@pytest.mark.parametrize("protocol", ["mqtt"])
@pytest.mark.timeout(120)
@pytest.mark.skipif(
    ADR_CERT_MGMT_POLICY_NAME is None,
    reason="Deployment with ADR cert management policy is required to run this test",
)
async def test_group_of_devices_register_with_no_device_id_for_a_x509_intermediate_authentication_group_enrollment(
    protocol,
):
    group_id = "e2e-intermediate-csr-" + str(uuid.uuid4())
    common_device_id = "e2edpscsrdevice"
    devices_indices = type_to_device_indices.get("group_intermediate")

    try:
        intermediate_cert_filename = "demoCA/newcerts/intermediate_cert.pem"
        with open(intermediate_cert_filename, "r") as intermediate_pem:
            intermediate_cert_content = intermediate_pem.read()

        x509 = create_x509_client_or_sign_certs(
            is_client=False, primary_cert=intermediate_cert_content
        )

        create_enrollment_group(
            group_id=group_id,
            attestation_mechanism=models.AttestationMechanism(type="x509", x509=x509),
            credential_policy_name=ADR_CERT_MGMT_POLICY_NAME,
        )

        count = 0
        common_device_key_input_file = "demoCA/private/device_key"
        common_device_cert_input_file = "demoCA/newcerts/device_cert"
        common_device_inter_cert_chain_file = "demoCA/newcerts/out_inter_device_chain_cert"

        for index in devices_indices:
            count = count + 1
            device_id = common_device_id + str(index)

            device_key_input_file = common_device_key_input_file + str(index) + ".pem"
            device_cert_input_file = common_device_cert_input_file + str(index) + ".pem"
            device_inter_cert_chain_file = common_device_inter_cert_chain_file + str(index) + ".pem"
            filenames = [device_cert_input_file, intermediate_cert_filename]
            with open(device_inter_cert_chain_file, "w") as outfile:
                for fname in filenames:
                    with open(fname) as infile:
                        outfile.write(infile.read())

            csr_key_file = "csr_key_" + str(index) + ".pem"
            dps_csr_file = "dps_csr_" + str(index) + ".pem"
            csr_private_key = create_ec_private_key(csr_key_file)
            create_csr(csr_private_key, dps_csr_file, device_id)

            registration_result = await register_via_x509(
                registration_id=device_id,
                device_cert_file=device_inter_cert_chain_file,
                device_key_file=device_key_input_file,
                protocol=protocol,
                csr_file=dps_csr_file,
            )

            assert_device_provisioned(device_id=device_id, registration_result=registration_result)

            device_client = await connect_device_with_issued_certificate(
                registration_result=registration_result, key_file=csr_key_file
            )

            iot_csr_file = "iot_hub_csr_" + str(index) + ".pem"
            create_csr(
                csr_private_key, iot_csr_file, registration_result.registration_state.device_id
            )

            csr_response = await device_client.send_certificate_signing_request(
                str(uuid.uuid4()), read_csr_from_file(iot_csr_file), "*"
            )
            assert csr_response.status_code == 200
            assert len(csr_response.certificates) == 3  # leaf, intermediate and root certs

            await device_client.disconnect()

            device_client = await connect_device_with_issued_certificate(
                registration_result=registration_result,
                key_file=csr_key_file,
                iot_hub_csr_response=csr_response,
            )

            await device_client.disconnect()

            device_registry_helper.try_delete_device(device_id)
            delete_client_certs(csr_key_file, dps_csr_file, iot_csr_file)

        assert count == len(
            devices_indices
        )  # Verify that all devices in the group were provisioned.

    finally:
        service_client.delete_enrollment_group_by_param(group_id)


@pytest.mark.it(
    "A group of devices request client certs by sending certificate signing requests while being provisioned"
    " to the linked IoTHub inside a group enrollment that has been created with a symmetric key authentication"
)
@pytest.mark.parametrize("protocol", ["mqtt"])
@pytest.mark.timeout(120)
@pytest.mark.skipif(
    ADR_CERT_MGMT_POLICY_NAME is None,
    reason="Deployment with ADR cert management policy is required to run this test",
)
async def test_device_register_with_client_cert_issuance_for_a_symmetric_key_group_enrollment(
    protocol,
):
    group_id = "e2e-symmetric-csr-" + str(uuid.uuid4())
    common_device_id = "e2edpscsrskdev"
    devices_indices = type_to_device_indices.get("group_symmetric")

    try:
        eg = create_enrollment_group(
            group_id=group_id,
            attestation_mechanism=models.AttestationMechanism(type="symmetricKey"),
            credential_policy_name=ADR_CERT_MGMT_POLICY_NAME,
        )

        count = 0
        for index in devices_indices:
            count = count + 1
            device_id = common_device_id + str(index)
            device_key = derive_device_key(device_id, eg.attestation.symmetric_key.primary_key)

            csr_key_file = "csr_key_" + str(index) + ".pem"
            dps_csr_file = "dps_csr_" + str(index) + ".pem"
            csr_private_key = create_ec_private_key(csr_key_file)
            create_csr(csr_private_key, dps_csr_file, device_id)

            registration_result = await register_via_symmetric_key(
                registration_id=device_id,
                symmetric_key=device_key,
                protocol=protocol,
                csr_file=dps_csr_file,
            )

            assert_device_provisioned(device_id=device_id, registration_result=registration_result)

            device_client = await connect_device_with_issued_certificate(
                registration_result=registration_result, key_file=csr_key_file
            )

            iot_csr_file = "iot_hub_csr_" + str(index) + ".pem"
            create_csr(
                csr_private_key, iot_csr_file, registration_result.registration_state.device_id
            )

            csr_response = await device_client.send_certificate_signing_request(
                str(uuid.uuid4()), read_csr_from_file(iot_csr_file), "*"
            )
            assert csr_response.status_code == 200
            assert len(csr_response.certificates) == 3  # leaf, intermediate and root certs

            await device_client.disconnect()

            device_client = await connect_device_with_issued_certificate(
                registration_result=registration_result,
                key_file=csr_key_file,
                iot_hub_csr_response=csr_response,
            )

            await device_client.disconnect()

            device_registry_helper.try_delete_device(device_id)
            delete_client_certs(csr_key_file, dps_csr_file, iot_csr_file)

        assert count == len(
            devices_indices
        )  # Verify that all devices in the group were provisioned.

    finally:
        service_client.delete_enrollment_group_by_param(group_id)


def assert_device_provisioned(device_id, registration_result):
    """
    Assert that the device has been provisioned correctly to iothub from the registration result as well as from the device registry
    :param device_id: The device id
    :param registration_result: The registration result
    """
    assert registration_result.status == "assigned"
    assert registration_result.registration_state.device_id == device_id
    assert registration_result.registration_state.assigned_hub == linked_iot_hub

    device = device_registry_helper.get_device(device_id)
    assert device is not None
    assert device.authentication.type == "certificateAuthority"
    print("assertions")
    print(device_id)  # leaf, intermediate, root
    print(device.authentication.type)
    assert device.device_id == device_id
    assert (
        len(registration_result.registration_state.issued_client_certificate) == 3
    )  # leaf, intermediate, root


def create_x509_client_or_sign_certs(is_client, primary_cert, secondary_cert=None):

    primary = models.X509CertificateWithInfo(certificate=primary_cert)
    secondary = None
    if secondary_cert:
        secondary = models.X509CertificateWithInfo(certificate=secondary_cert)
    certs = models.X509Certificates(primary=primary, secondary=secondary)
    if is_client:
        x509_attestation = models.X509Attestation(client_certificates=certs)
    else:
        x509_attestation = models.X509Attestation(signing_certificates=certs)
    return x509_attestation


def delete_client_certs(*args):
    for cert_file in args:
        if os.path.exists(cert_file):
            os.remove(cert_file)


def strip_csr_headers(csr_data):
    # Strip PEM header/footer and whitespace to get raw base64 content
    csr_b64 = (
        csr_data.replace("-----BEGIN CERTIFICATE REQUEST-----", "")
        .replace("-----END CERTIFICATE REQUEST-----", "")
        .replace("\n", "")
        .strip()
    )
    return csr_b64


def read_csr_from_file(csr_file):
    with open(csr_file, "r") as csr:
        csr_data = csr.read()
        return strip_csr_headers(csr_data)


async def register_via_x509(
    registration_id, device_cert_file, device_key_file, protocol, csr_file=None
):
    print("registering device {}".format(registration_id))
    x509 = X509(cert_file=device_cert_file, key_file=device_key_file, pass_phrase=device_password)
    protocol_boolean_mapping = {"mqtt": False, "mqttws": True}
    provisioning_device_client = ProvisioningDeviceClient.create_from_x509_certificate(
        provisioning_host=PROVISIONING_HOST,
        registration_id=registration_id,
        id_scope=ID_SCOPE,
        x509=x509,
        websockets=protocol_boolean_mapping[protocol],
    )

    if csr_file:
        provisioning_device_client.client_certificate_signing_request = read_csr_from_file(csr_file)

    return await provisioning_device_client.register()


async def register_via_symmetric_key(registration_id, symmetric_key, protocol, csr_file=None):
    # We have this mapping because the pytest logs look better with "mqtt" and "mqttws"
    # instead of just "True" and "False".
    protocol_boolean_mapping = {"mqtt": False, "mqttws": True}
    provisioning_device_client = ProvisioningDeviceClient.create_from_symmetric_key(
        provisioning_host=PROVISIONING_HOST,
        registration_id=registration_id,
        id_scope=ID_SCOPE,
        symmetric_key=symmetric_key,
        websockets=protocol_boolean_mapping[protocol],
    )
    if csr_file:
        with open(csr_file, "r") as csr:
            csr_data = csr.read()
            # Set the CSR on the client to send it to DPS
            provisioning_device_client.client_certificate_signing_request = strip_csr_headers(
                csr_data
            )
    return await provisioning_device_client.register()


def create_enrollment_group(group_id, attestation_mechanism, credential_policy_name=None):

    reprovision_policy = models.ReprovisionPolicy(migrate_device_data=True)

    enrollment_group_provisioning_model = models.EnrollmentGroup(
        enrollment_group_id=group_id,
        attestation=attestation_mechanism,
        reprovision_policy=reprovision_policy,
        credential_policy_name=credential_policy_name,
    )
    return service_client.create_or_update_enrollment_group(enrollment_group_provisioning_model)


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


def add_certificate_headers(cert_data):
    return "-----BEGIN CERTIFICATE-----\r\n" + cert_data + "\r\n-----END CERTIFICATE-----"


async def connect_device_with_issued_certificate(
    registration_result, key_file, iot_hub_csr_response=None
):
    issued_leaf_cert_file = (
        "issued_cert_" + registration_result.registration_state.device_id + ".pem"
    )

    with open(issued_leaf_cert_file, "w") as out_ca_pem:
        # Write the issued certificate on the file. This forms the certificate portion of the X509 object.
        if iot_hub_csr_response:
            cert_b64_data = iot_hub_csr_response.certificates[
                0
            ]  # use the certificate issued by IoT Hub in response to the CSR request
        else:
            cert_b64_data = registration_result.registration_state.issued_client_certificate[
                0
            ]  # use only leaf certificate.

        out_ca_pem.write(add_certificate_headers(cert_b64_data))

    x509 = X509(
        cert_file=issued_leaf_cert_file,
        key_file=key_file,
    )

    device_client = IoTHubDeviceClient.create_from_x509_certificate(
        hostname=registration_result.registration_state.assigned_hub,
        device_id=registration_result.registration_state.device_id,
        x509=x509,
    )
    # Connect the client.
    await device_client.connect()

    delete_client_certs(issued_leaf_cert_file)

    # Assert that this X509 was able to connect.
    assert device_client.connected

    return device_client
