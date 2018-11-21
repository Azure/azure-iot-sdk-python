# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

import os
import copy
import pytest

import e2e_convenience
from azure.iot.provisioning.servicesdk import (
    ProvisioningServiceClient,
    QuerySpecification,
    BulkEnrollmentOperation,
    ProvisioningServiceErrorDetailsException,
)
from azure.iot.provisioning.servicesdk.models import (
    IndividualEnrollment,
    AttestationMechanism,
    InitialTwin,
    EnrollmentGroup,
    DeviceCapabilities,
    TwinCollection,
    InitialTwinProperties,
)

e2e_convenience._patch_attestation_mechanism()

CONNECTION_STRING = os.environ["CONNECTION_STRING"]
ENDORSEMENT_KEY = os.environ["ENDORSEMENT_KEY"]
SIGNING_CERTIFICATE = os.environ["SIGNING_CERTIFICATE"]
CLIENT_CERTIFICATE = os.environ["CLIENT_CERTIFICATE"]
CA_REFERENCE = os.environ["CA_REFERENCE"]

REGISTRATION_ID = "e2e-test-reg-id"
GROUP_ID = "e2e-test-group-id"
TAGS = {"tag1": "val1"}
DESIRED_PROPERTIES = {"dp1": "val1", "dp2": {"dp3": "val2"}}
CREATE = "create"
DELETE = "delete"
BULK_SIZE = 10


@pytest.fixture(scope="module")
def client():
    return ProvisioningServiceClient(CONNECTION_STRING)


@pytest.fixture
def tpm_attestation():
    return AttestationMechanism.create_with_tpm(ENDORSEMENT_KEY)


@pytest.fixture
def x509_attestation_client_certs():
    return AttestationMechanism.create_with_x509_client_certificates(CLIENT_CERTIFICATE)


@pytest.fixture
def x509_attestation_signing_certs():
    return AttestationMechanism.create_with_x509_signing_certificates(SIGNING_CERTIFICATE)


@pytest.fixture
def x509_attestation_ca_refs():
    return AttestationMechanism.create_with_x509_ca_references(CA_REFERENCE)


@pytest.fixture(params=[tpm_attestation, x509_attestation_client_certs])
def individual_enrollment(request):
    attestation = request.param()
    return IndividualEnrollment(registration_id=REGISTRATION_ID, attestation=attestation)


@pytest.fixture(params=[x509_attestation_signing_certs, x509_attestation_ca_refs])
def enrollment_group(request):
    attestation = request.param()
    return EnrollmentGroup(enrollment_group_id=GROUP_ID, attestation=attestation)


@pytest.fixture
def twin():
    tags_collection = TwinCollection(additional_properties=TAGS)
    dp_collection = TwinCollection(additional_properties=DESIRED_PROPERTIES)
    properties = InitialTwinProperties(desired=dp_collection)
    return InitialTwin(tags=tags_collection, properties=properties)


@pytest.fixture
def device_capabilities():
    return DeviceCapabilities(iot_edge=True)


@pytest.fixture
def purge_individual_enrollments(client):
    """Delete all individual enrollments from the hub
    """
    yield  # teardown only

    # Get all enrollments from the provisioning hub
    enrollments = []
    qs = QuerySpecification(query="*")
    cont = ""
    while cont is not None:
        qrr = client.query_individual_enrollments(
            query_specification=qs, x_ms_continuation=cont, raw=True
        )
        enrollments.extend(qrr.output)
        cont = qrr.headers.get("x-ms-continuation", None)

    # delete enrollments
    if enrollments:
        bulk_op = BulkEnrollmentOperation(enrollments=enrollments, mode=DELETE)
        client.run_bulk_enrollment_operation(bulk_op)


@pytest.fixture
def purge_enrollment_groups(client):
    """Delete all enrollment groups from the hub
    """
    yield  # teardown only

    # Get all enrollments from the provisioning hub
    enrollments = []
    qs = QuerySpecification(query="*")
    cont = ""
    while cont is not None:
        qrr = client.query_enrollment_groups(
            query_specification=qs, x_ms_continuation=cont, raw=True
        )
        enrollments.extend(qrr.output)
        cont = qrr.headers.get("x-ms-continuation", None)

    for enrollment in enrollments:
        client.delete_enrollment_group(enrollment.enrollment_group_id)


@pytest.mark.usefixtures("purge_individual_enrollments")
class TestIndividualEnrollment(object):
    def test_crud(self, client, individual_enrollment, twin, device_capabilities):
        ie = individual_enrollment

        # create
        ret_ie = client.create_or_update_individual_enrollment(ie.registration_id, ie)
        assert ret_ie.registration_id == REGISTRATION_ID

        # update
        ret_ie.initial_twin = twin
        ret_ie.capabilities = device_capabilities

        ret_ie = client.create_or_update_individual_enrollment(
            ret_ie.registration_id, ret_ie, ret_ie.etag
        )
        assert ret_ie.registration_id == REGISTRATION_ID
        assert ret_ie.initial_twin.tags.additional_properties == TAGS
        assert ret_ie.initial_twin.properties.desired.additional_properties == DESIRED_PROPERTIES
        assert ret_ie.capabilities.iot_edge is True

        # get
        ret_ie = client.get_individual_enrollment(REGISTRATION_ID)
        assert ret_ie.registration_id == REGISTRATION_ID
        assert ret_ie.initial_twin.tags.additional_properties == TAGS
        assert ret_ie.initial_twin.properties.desired.additional_properties == DESIRED_PROPERTIES
        assert ret_ie.capabilities.iot_edge is True

        # delete
        client.delete_individual_enrollment(REGISTRATION_ID)
        with pytest.raises(ProvisioningServiceErrorDetailsException):
            ret_ie = client.get_individual_enrollment(REGISTRATION_ID)

    def test_bulk_operation(self, client, individual_enrollment):
        # create
        enrollments = []
        for i in range(BULK_SIZE):
            new = copy.copy(individual_enrollment)
            new.registration_id = new.registration_id + str(i)
            enrollments.append(new)
        bulk_op = BulkEnrollmentOperation(enrollments=enrollments, mode=CREATE)
        res = client.run_bulk_enrollment_operation(bulk_op)
        assert res.is_successful

        # delete
        bulk_op = BulkEnrollmentOperation(enrollments=enrollments, mode=DELETE)
        res = client.run_bulk_enrollment_operation(bulk_op)
        assert res.is_successful

    def test_query(self):
        pass


@pytest.mark.usefixtures("purge_enrollment_groups")
class TestEnrollmentGroup(object):
    def test_crud(self, client, enrollment_group, twin):
        eg = enrollment_group

        # create
        ret_eg = client.create_or_update_enrollment_group(eg.enrollment_group_id, eg)
        assert ret_eg.enrollment_group_id == GROUP_ID

        # update
        ret_eg.initial_twin = twin
        ret_eg.capabilities = device_capabilities

        ret_eg = client.create_or_update_enrollment_group(
            ret_eg.enrollment_group_id, ret_eg, ret_eg.etag
        )
        assert ret_eg.enrollment_group_id == GROUP_ID
        assert ret_eg.initial_twin.tags.additional_properties == TAGS
        assert ret_eg.initial_twin.properties.desired.additional_properties == DESIRED_PROPERTIES

        # get
        ret_eg = client.get_enrollment_group(GROUP_ID)
        assert ret_eg.enrollment_group_id == GROUP_ID
        assert ret_eg.initial_twin.tags.additional_properties == TAGS
        assert ret_eg.initial_twin.properties.desired.additional_properties == DESIRED_PROPERTIES

        # delete
        client.delete_enrollment_group(GROUP_ID)
        with pytest.raises(ProvisioningServiceErrorDetailsException):
            ret_eg = client.get_enrollment_group(GROUP_ID)

    def test_query(self):
        pass
