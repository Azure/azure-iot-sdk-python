# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

from provisioning_e2e.service_helper import Helper, connection_string_to_hostname
from azure.iot.device.aio import ProvisioningDeviceClient
from provisioningservice.protocol import models
from provisioningservice.client import ProvisioningServiceClient
import pytest
import logging
import os
import uuid

pytestmark = pytest.mark.asyncio
logging.basicConfig(level=logging.DEBUG)

PROVISIONING_HOST = os.getenv("PROVISIONING_DEVICE_ENDPOINT")
ID_SCOPE = os.getenv("PROVISIONING_DEVICE_IDSCOPE")
conn_str = os.getenv("PROVISIONING_SERVICE_CONNECTION_STRING")
service_client = ProvisioningServiceClient.create_from_connection_string(
    os.getenv("PROVISIONING_SERVICE_CONNECTION_STRING")
)
service_client = ProvisioningServiceClient.create_from_connection_string(conn_str)
device_registry_helper = Helper(os.getenv("IOTHUB_CONNECTION_STRING"))
linked_iot_hub = connection_string_to_hostname(os.getenv("IOTHUB_CONNECTION_STRING"))
CLIENT_CERT_AUTH_NAME = os.getenv("CLIENT_CERTIFICATE_AUTHORITY_NAME")

logger = logging.getLogger(__name__)


@pytest.mark.it(
    "A device gets provisioned to the linked IoTHub with the device_id equal to the registration_id"
    "of the individual enrollment that has been created with a symmetric key authentication"
)
@pytest.mark.parametrize("protocol", ["mqtt", "mqttws"])
async def test_device_register_with_no_device_id_for_a_symmetric_key_individual_enrollment(
    protocol,
):
    registration_id = ""
    try:
        individual_enrollment_record = create_individual_enrollment(
            "e2e-dps-legilimens" + str(uuid.uuid4())
        )

        registration_id = individual_enrollment_record.registration_id
        symmetric_key = individual_enrollment_record.attestation.symmetric_key.primary_key

        registration_result = await result_from_register(registration_id, symmetric_key, protocol)

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
async def test_device_register_with_device_id_for_a_symmetric_key_individual_enrollment(protocol):
    registration_id = ""
    device_id = "e2edpsgoldensnitch"
    try:
        individual_enrollment_record = create_individual_enrollment(
            registration_id="e2e-dps-levicorpus" + str(uuid.uuid4()), device_id=device_id
        )

        registration_id = individual_enrollment_record.registration_id
        symmetric_key = individual_enrollment_record.attestation.symmetric_key.primary_key

        registration_result = await result_from_register(registration_id, symmetric_key, protocol)

        assert device_id != registration_id
        assert_device_provisioned(device_id=device_id, registration_result=registration_result)
        device_registry_helper.try_delete_device(device_id)
    finally:
        service_client.delete_individual_enrollment_by_param(registration_id)


def create_individual_enrollment(registration_id, device_id=None, client_ca_name=None):
    """
    Create an individual enrollment record using the service client
    :param registration_id: The registration id of the enrollment
    :param device_id:  Optional device id
    :return: And individual enrollment record
    """
    reprovision_policy = models.ReprovisionPolicy(migrate_device_data=True)
    attestation_mechanism = models.AttestationMechanism(type="symmetricKey")
    client_certificate_issuance_policy = None
    if client_ca_name:
        client_certificate_issuance_policy = models.ClientCertificateIssuancePolicy(
            certificate_authority_name=client_ca_name
        )
    individual_provisioning_model = models.IndividualEnrollment(
        attestation=attestation_mechanism,
        registration_id=registration_id,
        device_id=device_id,
        reprovision_policy=reprovision_policy,
        client_certificate_issuance_policy=client_certificate_issuance_policy,
    )

    return service_client.create_or_update_individual_enrollment(individual_provisioning_model)


def assert_device_provisioned(device_id, registration_result, client_cert=False):
    """
    Assert that the device has been provisioned correctly to iothub from the registration result as well as from the device registry
    :param device_id: The device id
    :param registration_result: The registration result
    :param client_cert: Boolean expecting client cert to be issued
    """
    assert registration_result.status == "assigned"
    assert registration_result.registration_state.device_id == device_id
    assert registration_result.registration_state.assigned_hub == linked_iot_hub

    device = device_registry_helper.get_device(device_id)
    assert device is not None
    if client_cert:
        assert device.authentication.type == "selfSigned"
    else:
        assert device.authentication.type == "sas"
    assert device.device_id == device_id

    if client_cert:
        assert registration_result.registration_state.issued_client_certificate is not None


async def result_from_register(registration_id, symmetric_key, protocol, csr_file=None):
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
