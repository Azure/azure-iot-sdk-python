# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

from provisioning_e2e.service_helper import Helper, connection_string_to_hostname
from azure.iot.device.aio import ProvisioningDeviceClient, IoTHubDeviceClient
from azure.iot.device.common import X509
from ..provisioningservice.protocol.models import (
    IndividualEnrollment,
    AttestationMechanism,
    ReprovisionPolicy,
    EnrollmentGroup,
    X509CertificateWithInfo,
    X509Attestation,
    X509CAReferences,
    ClientCertificateIssuancePolicy,
    # SymmetricKeyAttestation,
)
from ..provisioningservice.client import ProvisioningServiceClient

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
    create_private_key,
    create_csr,
)
from ..provisioningservice.protocol.models import X509Certificates

# pytestmark = [pytest.mark.skip, pytest.mark.asyncio]
pytestmark = pytest.mark.asyncio
logging.basicConfig(level=logging.DEBUG)

intermediate_common_name = "e2edpshomenumdps"
intermediate_password = "revelio"
device_common_name = "e2edpslocomotor" + str(uuid.uuid4())
device_password = "mortis"

service_client = ProvisioningServiceClient.create_from_connection_string(
    os.getenv("PROVISIONING_SERVICE_CONNECTION_STRING")
)
device_registry_helper = Helper(os.getenv("IOTHUB_CONNECTION_STRING"))
linked_iot_hub = connection_string_to_hostname(os.getenv("IOTHUB_CONNECTION_STRING"))

PROVISIONING_HOST = os.getenv("PROVISIONING_DEVICE_ENDPOINT")
ID_SCOPE = os.getenv("PROVISIONING_DEVICE_IDSCOPE")
CLIENT_CERT_AUTH_NAME = os.getenv("CLIENT_CERTIFICATE_AUTHORITY_NAME")

type_to_device_indices = {
    "individual_with_device_id": [1],
    "individual_no_device_id": [2],
    "group_intermediate": [3, 4, 5],
    "group_ca": [6, 7, 8],
    "group_symmetric": [9, 10, 11],
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


@pytest.mark.it(
    "A device requests a client cert by sending a certificate signing request "
    "while being provisioned to the linked IoTHub with the device_id equal to the registration_id"
    "of the individual enrollment that has been created with a symmetric key authentication"
)
@pytest.mark.parametrize("protocol", ["mqtt", "mqttws"])
async def test_device_register_with_client_cert_issuance_for_a_symmetric_key_individual_enrollment(
    protocol,
):
    registration_id = "e2e-dps-locomotor" + str(uuid.uuid4())
    key_file = "key.pem"
    csr_file = "request.pem"
    issued_cert_file = "cert.pem"
    try:
        attestation_mechanism = AttestationMechanism(type="symmetricKey")
        individual_enrollment_record = create_individual_enrollment(
            registration_id=registration_id,
            attestation_mechanism=attestation_mechanism,
            client_ca_name=CLIENT_CERT_AUTH_NAME,
        )
        symmetric_key = individual_enrollment_record.attestation.symmetric_key.primary_key
        private_key = create_private_key(key_file)
        create_csr(private_key, csr_file, registration_id)

        registration_result = await register_via_symmetric_key(
            registration_id, symmetric_key, protocol, csr_file=csr_file
        )

        assert_device_provisioned(
            device_id=registration_id, registration_result=registration_result
        )
        await connect_device_with_operational_cert(
            registration_result=registration_result,
            issued_cert_file=issued_cert_file,
            key_file=key_file,
        )
        device_registry_helper.try_delete_device(registration_id)
    finally:
        service_client.delete_individual_enrollment_by_param(registration_id)
        delete_client_certs(key_file, csr_file, issued_cert_file)


@pytest.mark.it(
    "A group of devices request client certs by sending certificate signing requests while being provisioned"
    " to the linked IoTHub inside a group enrollment that has been created with a symmetric key authentication"
)
@pytest.mark.parametrize("protocol", ["mqtt"])
async def test_device_register_with_client_cert_issuance_for_a_symmetric_key_group_enrollment(
    protocol,
):
    group_id = "e2e-symmetric-group" + str(uuid.uuid4())
    devices_indices = type_to_device_indices.get("group_symmetric")
    device_count_in_group = len(devices_indices)
    common_device_id = "e2edpsgroupsymmetric"
    try:
        # master_key = str(uuid.uuid4())
        # symmetric_key = SymmetricKeyAttestation(primary_key=master_key)
        attestation_mechanism = AttestationMechanism(type="symmetricKey")
        # attestation_mechanism = AttestationMechanism(
        #     type="symmetricKey", symmetric_key=symmetric_key
        # )
        eg = create_enrollment_group(group_id=group_id, attestation_mechanism=attestation_mechanism)
        master_key = eg.attestation.symmetric_key.primary_key
        print("a valid master key has been created")
        print(master_key)
        print("enrollment group has been created")
        count = 0

        for index in devices_indices:
            count = count + 1
            device_id = common_device_id + str(index)
            device_key = derive_device_key(device_id, master_key)

            key_file = "key" + str(index) + ".pem"
            csr_file = "request" + str(index) + ".pem"

            private_key = create_private_key(key_file)
            create_csr(private_key, csr_file, device_id)
            registration_result = await register_via_symmetric_key(
                registration_id=device_id,
                symmetric_key=device_key,
                protocol=protocol,
                csr_file=csr_file,
            )

            assert_device_provisioned(device_id=device_id, registration_result=registration_result)
            issued_cert_file = "cert" + str(index) + ".pem"
            await connect_device_with_operational_cert(
                registration_result=registration_result,
                issued_cert_file=issued_cert_file,
                key_file=key_file,
            )
        assert count == device_count_in_group
        device_registry_helper.try_delete_device(device_id)
    finally:
        for index in devices_indices:
            key_file = "key" + str(index) + ".pem"
            csr_file = "request" + str(index) + ".pem"
            issued_cert_file = "cert" + str(index) + ".pem"
            delete_client_certs(key_file, csr_file, issued_cert_file)
        print("deleting enrollment group")
        # service_client.delete_enrollment_group_by_param(group_id)


@pytest.mark.skip()
@pytest.mark.it(
    "A device gets provisioned to the linked IoTHub with the user supplied device_id different from the registration_id of the individual enrollment that has been created with a selfsigned X509 authentication"
)
@pytest.mark.parametrize("protocol", ["mqtt", "mqttws"])
async def test_device_register_with_device_id_for_a_x509_individual_enrollment(protocol):
    device_id = "e2edpsthunderbolt"
    device_index = type_to_device_indices.get("individual_with_device_id")[0]
    registration_id = device_common_name + str(device_index)
    try:
        cert_content = read_cert_content_from_file(device_index=device_index)
        x509 = create_x509_client_or_sign_certs(is_client=True, primary_cert=cert_content)
        attestation_mechanism = AttestationMechanism(type="x509", x509=x509)
        individual_enrollment_record = create_individual_enrollment(
            registration_id=registration_id,
            attestation_mechanism=attestation_mechanism,
            device_id=device_id,
            client_ca_name=CLIENT_CERT_AUTH_NAME,
        )
        registration_id = individual_enrollment_record.registration_id

        device_cert_file = "demoCA/newcerts/device_cert" + str(device_index) + ".pem"
        device_key_file = "demoCA/private/device_key" + str(device_index) + ".pem"

        key_file = "key.pem"
        csr_file = "request.pem"

        private_key = create_private_key(key_file)
        create_csr(private_key, csr_file, registration_id)

        registration_result = await register_via_x509(
            registration_id, device_cert_file, device_key_file, protocol, csr_file=csr_file
        )

        assert device_id != registration_id
        assert_device_provisioned(device_id=device_id, registration_result=registration_result)
        issued_cert_file = "cert.pem"
        await connect_device_with_operational_cert(
            registration_result=registration_result,
            issued_cert_file=issued_cert_file,
            key_file=key_file,
        )
        device_registry_helper.try_delete_device(device_id)
    finally:
        delete_client_certs(key_file, csr_file, issued_cert_file)
        service_client.delete_individual_enrollment_by_param(registration_id)


@pytest.mark.skip()
@pytest.mark.it(
    "A device gets provisioned to the linked IoTHub with device_id equal to the registration_id of the "
    "individual enrollment that has been created with a selfsigned X509 authentication"
)
@pytest.mark.parametrize("protocol", ["mqtt", "mqttws"])
async def test_device_register_with_no_device_id_for_a_x509_individual_enrollment(protocol):
    device_index = type_to_device_indices.get("individual_no_device_id")[0]
    registration_id = device_common_name + str(device_index)
    try:
        cert_content = read_cert_content_from_file(device_index=device_index)
        x509 = create_x509_client_or_sign_certs(is_client=True, primary_cert=cert_content)
        attestation_mechanism = AttestationMechanism(type="x509", x509=x509)
        individual_enrollment_record = create_individual_enrollment(
            registration_id=registration_id,
            attestation_mechanism=attestation_mechanism,
            client_ca_name=CLIENT_CERT_AUTH_NAME,
        )

        registration_id = individual_enrollment_record.registration_id

        device_cert_file = "demoCA/newcerts/device_cert" + str(device_index) + ".pem"
        device_key_file = "demoCA/private/device_key" + str(device_index) + ".pem"

        key_file = "key.pem"
        csr_file = "request.pem"

        private_key = create_private_key(key_file)
        create_csr(private_key, csr_file, registration_id)

        registration_result = await register_via_x509(
            registration_id, device_cert_file, device_key_file, protocol, csr_file=csr_file
        )

        assert_device_provisioned(
            device_id=registration_id, registration_result=registration_result
        )

        issued_cert_file = "cert.pem"

        await connect_device_with_operational_cert(
            registration_result=registration_result,
            issued_cert_file=issued_cert_file,
            key_file=key_file,
        )
        device_registry_helper.try_delete_device(registration_id)
    finally:
        delete_client_certs(key_file, csr_file, issued_cert_file)
        service_client.delete_individual_enrollment_by_param(registration_id)


@pytest.mark.it(
    "A group of devices get provisioned to the linked IoTHub with device_ids equal to the individual registration_ids "
    "inside a group enrollment that has been created with intermediate X509 authentication"
)
async def test_group_of_devices_register_with_no_device_id_for_a_x509_intermediate_authentication_group_enrollment():
    protocol = "mqtt"
    group_id = "e2e-intermediate-durmstrang" + str(uuid.uuid4())
    common_device_id = "e2edpsinterdevice"
    devices_indices = type_to_device_indices.get("group_intermediate")
    device_count_in_group = len(devices_indices)

    try:
        intermediate_cert_filename = "demoCA/newcerts/intermediate_cert.pem"
        with open(intermediate_cert_filename, "r") as intermediate_pem:
            intermediate_cert_content = intermediate_pem.read()

        x509 = create_x509_client_or_sign_certs(
            is_client=False,
            primary_cert=intermediate_cert_content,
        )
        attestation_mechanism = AttestationMechanism(type="x509", x509=x509)
        create_enrollment_group(group_id=group_id, attestation_mechanism=attestation_mechanism)
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

            key_file = "key" + str(index) + ".pem"
            csr_file = "request" + str(index) + ".pem"

            private_key = create_private_key(key_file)
            create_csr(private_key, csr_file, device_id)

            registration_result = await register_via_x509(
                registration_id=device_id,
                device_cert_file=device_inter_cert_chain_file,
                device_key_file=device_key_input_file,
                protocol=protocol,
                csr_file=csr_file,
            )

            assert_device_provisioned(device_id=device_id, registration_result=registration_result)
            print("device was provisioned")
            print(device_id)
            issued_cert_file = "cert" + str(index) + ".pem"

            await connect_device_with_operational_cert(
                registration_result=registration_result,
                issued_cert_file=issued_cert_file,
                key_file=key_file,
            )
            device_registry_helper.try_delete_device(device_id)

        assert count == device_count_in_group

    finally:
        for index in devices_indices:
            key_file = "key" + str(index) + ".pem"
            csr_file = "request" + str(index) + ".pem"
            issued_cert_file = "cert" + str(index) + ".pem"
            delete_client_certs(key_file, csr_file, issued_cert_file)

        service_client.delete_enrollment_group_by_param(group_id)


@pytest.mark.skip(
    reason="The enrollment is never properly created on the pipeline and it is always created without any CA reference and eventually the registration fails"
)
@pytest.mark.it(
    "A group of devices get provisioned to the linked IoTHub with device_ids equal to the individual registration_ids inside a group enrollment that has been created with an already uploaded ca cert X509 authentication"
)
async def test_group_of_devices_register_with_no_device_id_for_a_x509_ca_authentication_group_enrollment():
    protocol = "mqtt"
    group_id = "e2e-ca-ilvermorny" + str(uuid.uuid4())
    common_device_id = "e2edpscadevice"
    devices_indices = type_to_device_indices.get("group_ca")
    device_count_in_group = len(devices_indices)
    try:
        DPS_GROUP_CA_CERT = os.getenv("PROVISIONING_ROOT_CERT")
        x509 = create_x509_ca_refs(primary_ref=DPS_GROUP_CA_CERT)
        attestation_mechanism = AttestationMechanism(type="x509", x509=x509)
        create_enrollment_group(group_id=group_id, attestation_mechanism=attestation_mechanism)
        count = 0
        intermediate_cert_filename = "demoCA/newcerts/intermediate_cert.pem"
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
                        logging.debug("Filename is {}".format(fname))
                        content = infile.read()
                        logging.debug(content)
                        outfile.write(content)

            key_file = "key" + str(index) + ".pem"
            csr_file = "request" + str(index) + ".pem"

            private_key = create_private_key(key_file)
            create_csr(private_key, csr_file, device_id)

            registration_result = await register_via_x509(
                registration_id=device_id,
                device_cert_file=device_inter_cert_chain_file,
                device_key_file=device_key_input_file,
                protocol=protocol,
                csr_file=csr_file,
            )

            assert_device_provisioned(device_id=device_id, registration_result=registration_result)
            print("device was provisioned for ca")
            print(device_id)

            issued_cert_file = "cert" + str(index) + ".pem"

            await connect_device_with_operational_cert(
                registration_result=registration_result,
                issued_cert_file=issued_cert_file,
                key_file=key_file,
            )
            device_registry_helper.try_delete_device(device_id)

        assert count == device_count_in_group
    finally:
        for index in devices_indices:
            key_file = "key" + str(index) + ".pem"
            csr_file = "request" + str(index) + ".pem"
            issued_cert_file = "cert" + str(index) + ".pem"
            delete_client_certs(key_file, csr_file, issued_cert_file)
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
    assert device.authentication.type == "selfSigned"
    print("assertions")
    print(device_id)
    print(device.authentication.type)
    assert device.device_id == device_id


def create_individual_enrollment(
    registration_id,
    attestation_mechanism,
    device_id=None,
    client_ca_name=None,
):
    reprovision_policy = ReprovisionPolicy(migrate_device_data=True)
    client_certificate_issuance_policy = None
    if client_ca_name:
        client_certificate_issuance_policy = ClientCertificateIssuancePolicy(
            certificate_authority_name=client_ca_name
        )

    individual_provisioning_model = IndividualEnrollment(
        attestation=attestation_mechanism,
        registration_id=registration_id,
        reprovision_policy=reprovision_policy,
        device_id=device_id,
        client_certificate_issuance_policy=client_certificate_issuance_policy,
    )

    return service_client.create_or_update_individual_enrollment(individual_provisioning_model)


def create_x509_client_or_sign_certs(is_client, primary_cert, secondary_cert=None):

    primary = X509CertificateWithInfo(certificate=primary_cert)
    secondary = None
    if secondary_cert:
        secondary = X509CertificateWithInfo(certificate=secondary_cert)
    certs = X509Certificates(primary=primary, secondary=secondary)
    if is_client:
        x509_attestation = X509Attestation(client_certificates=certs)
    else:
        x509_attestation = X509Attestation(signing_certificates=certs)
    return x509_attestation


def create_x509_ca_refs(primary_ref, secondary_ref=None):
    ca_refs = X509CAReferences(primary=primary_ref, secondary=secondary_ref)
    x509_attestation = X509Attestation(ca_references=ca_refs)
    return x509_attestation


def read_cert_content_from_file(device_index):
    device_cert_input_file = "demoCA/newcerts/device_cert" + str(device_index) + ".pem"
    with open(device_cert_input_file, "r") as in_device_cert:
        device_cert_content = in_device_cert.read()
    return device_cert_content


def delete_client_certs(key_file, csr_file, issued_cert_file):
    if os.path.exists(key_file):
        os.remove(key_file)
    if os.path.exists(csr_file):
        os.remove(csr_file)
    if os.path.exists(issued_cert_file):
        os.remove(issued_cert_file)


async def register_via_x509(
    registration_id, device_cert_file, device_key_file, protocol, csr_file=None
):
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
        with open(csr_file, "r") as csr:
            csr_data = csr.read()
            # Set the CSR on the client to send it to DPS
            provisioning_device_client.client_certificate_signing_request = str(csr_data)

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
            provisioning_device_client.client_certificate_signing_request = str(csr_data)
    return await provisioning_device_client.register()


def create_enrollment_group(group_id, attestation_mechanism):

    reprovision_policy = ReprovisionPolicy(migrate_device_data=True)
    client_certificate_issuance_policy = ClientCertificateIssuancePolicy(
        certificate_authority_name=CLIENT_CERT_AUTH_NAME
    )
    enrollment_group_provisioning_model = EnrollmentGroup(
        enrollment_group_id=group_id,
        attestation=attestation_mechanism,
        reprovision_policy=reprovision_policy,
        client_certificate_issuance_policy=client_certificate_issuance_policy,
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


async def connect_device_with_operational_cert(registration_result, issued_cert_file, key_file):

    with open(issued_cert_file, "w") as out_ca_pem:
        # Write the issued certificate on the file. This forms the certificate portion of the X509 object.
        cert_data = registration_result.registration_state.issued_client_certificate
        out_ca_pem.write(cert_data)

    x509 = X509(
        cert_file=issued_cert_file,
        key_file=key_file,
    )

    device_client = IoTHubDeviceClient.create_from_x509_certificate(
        hostname=registration_result.registration_state.assigned_hub,
        device_id=registration_result.registration_state.device_id,
        x509=x509,
    )
    # Connect the client.
    await device_client.connect()
    # Assert that this X509 was able to connect.
    assert device_client.connected
    await device_client.disconnect()
