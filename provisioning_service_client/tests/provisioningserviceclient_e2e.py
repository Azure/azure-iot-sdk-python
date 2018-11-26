# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

import sys
import os

import six

import context
from provisioningserviceclient import ProvisioningServiceClient, QuerySpecification, \
    BulkEnrollmentOperation, ProvisioningServiceError
from provisioningserviceclient.models import IndividualEnrollment, AttestationMechanism, \
    InitialTwin, EnrollmentGroup, DeviceCapabilities


PROVISIONING_CONNECTION_STRING = ""
PROVISIONING_E2E_ENDORSEMENT_KEY = ""
PROVISIONING_E2E_X509_CERT = ""
REGISTRATION_ID = "e2e-test-reg-id"
GROUP_ID = "e2e-test-group-id"
TAGS = {"tag1": "val1"}
DESIRED_PROPERTIES = {"dp1": "val1", "dp2": {"dp3": "val2"}}
CREATE = "create"
DELETE = "delete"
BULK_SIZE = 10


def read_environment_vars():
    global PROVISIONING_CONNECTION_STRING
    global PROVISIONING_E2E_ENDORSEMENT_KEY
    global PROVISIONING_E2E_X509_CERT

    PROVISIONING_CONNECTION_STRING = os.environ["PROVISIONING_CONNECTION_STRING"]
    six.print_("PROVISIONING_CONNECTION_STRING: {}".format(PROVISIONING_CONNECTION_STRING))
    PROVISIONING_E2E_ENDORSEMENT_KEY = os.environ["PROVISIONING_E2E_ENDORSEMENT_KEY"]
    six.print_("PROVISIONING_E2E_ENDORSEMENT_KEY: {}".format(PROVISIONING_E2E_ENDORSEMENT_KEY))
    PROVISIONING_E2E_X509_CERT = os.environ["PROVISIONING_E2E_X509_CERT"]
    six.print_("PROVISIONING_E2E_X509_CERT: {}".format(PROVISIONING_E2E_X509_CERT))


def run_scenario_individual_enrollment():
    psc = ProvisioningServiceClient.create_from_connection_string(PROVISIONING_CONNECTION_STRING)
    att = AttestationMechanism.create_with_tpm(PROVISIONING_E2E_ENDORSEMENT_KEY)
    ie = IndividualEnrollment.create(REGISTRATION_ID, att)

    #create
    ret_ie = psc.create_or_update(ie)
    assert ret_ie.registration_id == REGISTRATION_ID

    #update
    twin = InitialTwin.create(TAGS, DESIRED_PROPERTIES)
    ret_ie.initial_twin = twin
    capabilities = DeviceCapabilities.create(True)
    ret_ie.capabilities = capabilities

    ret_ie = psc.create_or_update(ret_ie)
    assert ret_ie.registration_id == REGISTRATION_ID
    assert ret_ie.initial_twin.tags == TAGS
    assert ret_ie.initial_twin.desired_properties == DESIRED_PROPERTIES
    assert ret_ie.capabilities.iot_edge == True

    #get
    ret_ie = psc.get_individual_enrollment(REGISTRATION_ID)
    assert ret_ie.registration_id == REGISTRATION_ID
    assert ret_ie.initial_twin.tags == TAGS
    assert ret_ie.initial_twin.desired_properties == DESIRED_PROPERTIES

    #get attestation mechanism
    ret_am = psc.get_individual_enrollment_attestation_mechanism(REGISTRATION_ID)
    assert ret_am.tpm.endorsement_key == PROVISIONING_E2E_ENDORSEMENT_KEY

    #delete
    psc.delete(ret_ie)
    try:
        ret_ie = psc.get_individual_enrollment(REGISTRATION_ID)
    except ProvisioningServiceError:
        pass
    else:
        raise AssertionError

    #bulk enrollment
    enrollments = []
    for i in range(BULK_SIZE):
        new = IndividualEnrollment.create(REGISTRATION_ID + str(i), att)
        enrollments.append(new)
    bulk_op = BulkEnrollmentOperation(CREATE, enrollments)
    res = psc.run_bulk_operation(bulk_op)
    assert res.is_successful

    #query
    qs = QuerySpecification("*")
    q = psc.create_individual_enrollment_query(qs)
    q_results = q.next()
    assert len(q_results) == BULK_SIZE

    #cleanup
    bulk_op = BulkEnrollmentOperation(DELETE, enrollments)
    res = psc.run_bulk_operation(bulk_op)
    assert res.is_successful


def run_scenario_enrollment_group():
    psc = ProvisioningServiceClient.create_from_connection_string(PROVISIONING_CONNECTION_STRING)
    att = AttestationMechanism.create_with_x509_signing_certs(PROVISIONING_E2E_X509_CERT)
    eg = EnrollmentGroup.create(GROUP_ID, att)

    #create
    ret_eg = psc.create_or_update(eg)
    assert ret_eg.enrollment_group_id == GROUP_ID

    #update
    twin = InitialTwin.create(TAGS, DESIRED_PROPERTIES)
    ret_eg.initial_twin = twin
    ret_eg = psc.create_or_update(ret_eg)
    assert ret_eg.enrollment_group_id == GROUP_ID
    assert ret_eg.initial_twin.tags == TAGS
    assert ret_eg.initial_twin.desired_properties == DESIRED_PROPERTIES

    #get
    ret_eg = psc.get_enrollment_group(GROUP_ID)
    assert ret_eg.enrollment_group_id == GROUP_ID
    assert ret_eg.initial_twin.tags == TAGS
    assert ret_eg.initial_twin.desired_properties == DESIRED_PROPERTIES

    #get attestation mechansim
    ret_am = psc.get_enrollment_group_attestation_mechanism(GROUP_ID)

    #query
    qs = QuerySpecification("*")
    q = psc.create_enrollment_group_query(qs)
    q_results = q.next()
    assert len(q_results) == 1

    #delete
    psc.delete(ret_eg)
    try:
        ret_eg = psc.get_enrollment_group(GROUP_ID)
    except ProvisioningServiceError:
        pass
    else:
        raise AssertionError


def clear_dps_hub():
    psc = ProvisioningServiceClient.create_from_connection_string(PROVISIONING_CONNECTION_STRING)

    #Individual Enrollments
    qs = QuerySpecification("*")
    query = psc.create_individual_enrollment_query(qs)
    items = []
    for page in query:
        items += page
    bulkop = BulkEnrollmentOperation("delete", items)
    psc.run_bulk_operation(bulkop)

    #Enrollment Groups
    query = psc.create_enrollment_group_query(qs)
    for page in query:
        for enrollment in page:
            psc.delete(enrollment)


def main():
    six.print_("Provisioning Service Client E2E Tests Started!")
    six.print_("----------------------------------------------")

    try:
        six.print_("Reading environment variables...")
        read_environment_vars()
        six.print_("SUCCESS")
        six.print_("Running Individual Enrollment Scenario...")
        run_scenario_individual_enrollment()
        six.print_("PASSED")
        six.print_("Running Enrollment Group Scenario...")
        run_scenario_enrollment_group()
        six.print_("PASSED")
        six.print_("Provisioning Service Client E2E Tests OK!")
        six.print_("-----------------------------------------")
        return 0
    except Exception:
        six.print_("FAILED")
        six.print_("Provisioning Service Client E2E Tests FAILED!")
        six.print_("---------------------------------------------")
    try:
        clear_dps_hub()
    except Exception:
        six.print_("vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv")
        six.print_("WARNING: FAILED TO CLEAN UP E2E TESTING HUB. PLEASE MANUALLY REMOVE ALL ENROLLMENTS")
        six.print_("^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^")
    return 1


if __name__ == '__main__':
    sys.exit(main())
