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


CONNECTION_STRING = ""
ENDORSEMENT_KEY = ""
SIGNING_CERTIFICATE = ""
REGISTRATION_ID = "e2e-test-reg-id"
GROUP_ID = "e2e-test-group-id"
TAGS = {"tag1": "val1"}
DESIRED_PROPERTIES = {"dp1": "val1", "dp2": {"dp3": "val2"}}
CREATE = "create"
DELETE = "delete"
BULK_SIZE = 10


def read_environment_vars():
    global CONNECTION_STRING
    global ENDORSEMENT_KEY
    global SIGNING_CERTIFICATE

    CONNECTION_STRING = os.environ["CONNECTION_STRING"]
    six.print_("CONNECTION_STRING: {}".format(CONNECTION_STRING))
    ENDORSEMENT_KEY = os.environ["ENDORSEMENT_KEY"]
    six.print_("ENDORSEMENT_KEY: {}".format(ENDORSEMENT_KEY))
    SIGNING_CERTIFICATE = os.environ["SIGNING_CERTIFICATE"]
    six.print_("SIGNING_CERTIFICATE: {}".format(SIGNING_CERTIFICATE))


def run_scenario_individual_enrollment():
    psc = ProvisioningServiceClient.create_from_connection_string(CONNECTION_STRING)
    att = AttestationMechanism.create_with_tpm(ENDORSEMENT_KEY)
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
    psc = ProvisioningServiceClient.create_from_connection_string(CONNECTION_STRING)
    att = AttestationMechanism.create_with_x509_signing_certs(SIGNING_CERTIFICATE)
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


def main():
    six.print_("Provisioning Service Client E2E Tests Started!")
    six.print_("----------------------------------------------")

    #try:
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
    # except Exception:
    #     six.print_("FAILED")
    #     six.print_("Provisioning Service Client E2E Tests FAILED!")
    #     six.print_("---------------------------------------------")
    #     return 1


if __name__ == '__main__':
    sys.exit(main())
