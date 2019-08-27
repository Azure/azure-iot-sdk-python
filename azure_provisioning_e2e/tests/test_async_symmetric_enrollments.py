# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

from azure_provisioning_e2e.service_helper import Helper, connection_string_to_hostname
from azure.iot.device.aio import ProvisioningDeviceClient
from provisioningserviceclient import ProvisioningServiceClient, IndividualEnrollment
from provisioningserviceclient.protocol.models import AttestationMechanism, ReprovisionPolicy
import pytest
import logging
import os


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


@pytest.mark.it(
    "A device gets provisioned to the linked IoTHub with the device_id equal to the registration_id of the individual enrollment that has been created with a symmetric key authentication"
)
async def test_device_register_with_no_device_id_for_a_symmetric_key_individual_enrollment():
    try:
        individual_enrollment_record = create_individual_enrollment("e2e-dps-legilimens")

        registration_id = individual_enrollment_record.registration_id
        symmetric_key = individual_enrollment_record.attestation.symmetric_key.primary_key

        registration_result = await result_from_register(registration_id, symmetric_key)

        assert_device_provisioned(
            device_id=registration_id, registration_result=registration_result
        )
        device_registry_helper.try_delete_device(registration_id)
    finally:
        service_client.delete_individual_enrollment_by_param(registration_id)


@pytest.mark.it(
    "A device gets provisioned to the linked IoTHub with the user supplied device_id different from the registration_id of the individual enrollment that has been created with a symmetric key authentication"
)
async def test_device_register_with_device_id_for_a_symmetric_key_individual_enrollment():

    device_id = "e2edpsgoldensnitch"
    try:
        individual_enrollment_record = create_individual_enrollment(
            registration_id="e2e-dps-levicorpus", device_id=device_id
        )

        registration_id = individual_enrollment_record.registration_id
        symmetric_key = individual_enrollment_record.attestation.symmetric_key.primary_key

        registration_result = await result_from_register(registration_id, symmetric_key)

        assert device_id != registration_id
        assert_device_provisioned(device_id=device_id, registration_result=registration_result)
        device_registry_helper.try_delete_device(device_id)
    finally:
        pass
        service_client.delete_individual_enrollment_by_param(registration_id)


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


# TODO Eventually should return result after the APi changes
async def result_from_register(registration_id, symmetric_key):
    provisioning_device_client = ProvisioningDeviceClient.create_from_symmetric_key(
        provisioning_host=PROVISIONING_HOST,
        registration_id=registration_id,
        id_scope=ID_SCOPE,
        symmetric_key=symmetric_key,
    )

    return await provisioning_device_client.register()
