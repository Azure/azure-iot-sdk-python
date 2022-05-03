# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

from azure_provisioning_e2e.service_helper import Helper, connection_string_to_hostname
from azure.iot.device import ProvisioningDeviceClient, X509
from provisioningserviceclient import ProvisioningServiceClient, IndividualEnrollment
from provisioningserviceclient.protocol.models import AttestationMechanism, ReprovisionPolicy
import pytest
import logging
import os
import uuid
from scripts.create_x509_chain_crypto import (
    create_private_key,
    create_csr,
)
from azure.iot.device import IoTHubDeviceClient

logging.basicConfig(level=logging.DEBUG)

PROVISIONING_HOST = os.getenv("PROVISIONING_DEVICE_ENDPOINT")
ID_SCOPE = os.getenv("PROVISIONING_DEVICE_IDSCOPE")
service_client = ProvisioningServiceClient.create_from_connection_string(
    os.getenv("PROVISIONING_SERVICE_CONNECTION_STRING")
)
device_registry_helper = Helper(os.getenv("IOTHUB_CONNECTION_STRING"))
linked_iot_hub = connection_string_to_hostname(os.getenv("IOTHUB_CONNECTION_STRING"))
# TODO Delete this line. This is a pre created variable in key vault now.
symmetric_key_for_cert_management = os.getenv("DPS_CERT_ISSUANCE_SYM_KEY")


@pytest.mark.it(
    "A device gets provisioned to the linked IoTHub with the device_id equal to the registration_id of the individual enrollment that has been created with a symmetric key authentication"
)
@pytest.mark.parametrize("protocol", ["mqtt", "mqttws"])
def test_device_register_with_no_device_id_for_a_symmetric_key_individual_enrollment(protocol):
    try:
        individual_enrollment_record = create_individual_enrollment(
            "e2e-dps-underthewhompingwillow" + str(uuid.uuid4())
        )

        registration_id = individual_enrollment_record.registration_id
        symmetric_key = individual_enrollment_record.attestation.symmetric_key.primary_key

        registration_result = result_from_register(registration_id, symmetric_key, protocol)

        assert_device_provisioned(
            device_id=registration_id, registration_result=registration_result
        )
        device_registry_helper.try_delete_device(registration_id)
    finally:
        service_client.delete_individual_enrollment_by_param(registration_id)


@pytest.mark.it(
    "A device gets provisioned to the linked IoTHub with the user supplied device_id different from the registration_id of the individual enrollment that has been created with a symmetric key authentication"
)
@pytest.mark.parametrize("protocol", ["mqtt", "mqttws"])
def test_device_register_with_device_id_for_a_symmetric_key_individual_enrollment(protocol):

    device_id = "e2edpstommarvoloriddle"
    try:
        individual_enrollment_record = create_individual_enrollment(
            registration_id="e2e-dps-prioriincantatem" + str(uuid.uuid4()), device_id=device_id
        )

        registration_id = individual_enrollment_record.registration_id
        symmetric_key = individual_enrollment_record.attestation.symmetric_key.primary_key

        registration_result = result_from_register(registration_id, symmetric_key, protocol)

        assert device_id != registration_id
        assert_device_provisioned(device_id=device_id, registration_result=registration_result)
        device_registry_helper.try_delete_device(device_id)
    finally:
        service_client.delete_individual_enrollment_by_param(registration_id)


@pytest.mark.it(
    "A device requests a client cert by sending a certificate signing request "
    "while being provisioned to the linked IoTHub with the device_id equal to the registration_id"
    "of the individual enrollment that has been created with a symmetric key authentication"
)
@pytest.mark.parametrize("protocol", ["mqtt", "mqttws"])
def test_device_register_with_client_cert_issuance_for_a_symmetric_key_individual_enrollment(
    protocol,
):
    key_file = "key.pem"
    csr_file = "request.pem"
    issued_cert_file = "cert.pem"
    try:
        # individual_enrollment_record = create_individual_enrollment(
        #     "e2e-dps-avis" + str(uuid.uuid4())
        # )
        #
        # registration_id = individual_enrollment_record.registration_id
        # symmetric_key = individual_enrollment_record.attestation.symmetric_key.primary_key

        registration_id = "e2e-dps-ventus"
        symmetric_key = symmetric_key_for_cert_management

        key_file = "key.pem"
        csr_file = "request.pem"
        issued_cert_file = "cert.pem"

        private_key = create_private_key(key_file)
        client_csr = create_csr(private_key, csr_file, registration_id)

        registration_result = result_from_register(
            registration_id, symmetric_key, protocol, client_csr=client_csr
        )

        assert_device_provisioned(
            device_id=registration_id, registration_result=registration_result
        )
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
        device_client.connect()
        # Assert that this X509 was able to connect.
        assert device_client.connected
        device_client.disconnect()

        # TODO Uncomment this line. Right now do not delete the enrollment as it is not created on the fly.
        # device_registry_helper.try_delete_device(registration_id)
    finally:
        # TODO Uncomment this line. Right now do not delete the enrollment as it is not created on the fly.
        # TODO This is a previously created enrollment record.
        # service_client.delete_individual_enrollment_by_param(registration_id)
        if os.path.exists(key_file):
            os.remove(key_file)
        if os.path.exists(csr_file):
            os.remove(csr_file)
        if os.path.exists(issued_cert_file):
            os.remove(issued_cert_file)


def create_individual_enrollment(registration_id, device_id=None):
    """
    Create an individual enrollment record using the service client
    :param registration_id: The registration id of the enrollment
    :param device_id:  Optional device id
    :return: And individual enrollment record
    """
    reprovision_policy = ReprovisionPolicy(migrate_device_data=True)
    attestation_mechanism = AttestationMechanism(type="symmetricKey")

    individual_provisioning_model = IndividualEnrollment.create(
        attestation=attestation_mechanism,
        registration_id=registration_id,
        device_id=device_id,
        reprovision_policy=reprovision_policy,
    )

    return service_client.create_or_update(individual_provisioning_model)


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
    assert device.authentication.type == "sas"
    assert device.device_id == device_id


def result_from_register(registration_id, symmetric_key, protocol, client_csr):
    protocol_boolean_mapping = {"mqtt": False, "mqttws": True}
    provisioning_device_client = ProvisioningDeviceClient.create_from_symmetric_key(
        provisioning_host=PROVISIONING_HOST,
        registration_id=registration_id,
        id_scope=ID_SCOPE,
        symmetric_key=symmetric_key,
        websockets=protocol_boolean_mapping[protocol],
    )

    if client_csr:
        provisioning_device_client.client_certificate_signing_request = client_csr
    return provisioning_device_client.register()
