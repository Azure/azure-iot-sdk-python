# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

import six

import context #only needed in this directory
from provisioningserviceclient import ProvisioningServiceClient, QuerySpecification, \
    BulkEnrollmentOperation
from provisioningserviceclient.models import IndividualEnrollment, AttestationMechanism


def main():
    connection_string = "[Connection String]"
    endorsement_key = "[Endorsement Key]"
    registration_id = "[Registration ID]"

    #set up the provisioning service client
    psc = ProvisioningServiceClient.create_from_connection_string(connection_string)

    #build IndividualEnrollment model

    att = AttestationMechanism.create_with_tpm(endorsement_key)
    ie = IndividualEnrollment.create(registration_id, att)

    #create IndividualEnrollment on the Provisioning Service
    ie = psc.create_or_update(ie)
    six.print_(ie)

    #get IndividualEnrollment from the Provisioning Service (note: this step is useless here, as ie is already up to date)
    ie = psc.get_individual_enrollment(registration_id)
    six.print_(ie)

    #delete IndividualEnrollment from the Provisioning Service
    psc.delete(ie)
    #could also use psc.delete_individual_enrollment_by_param(ie.registration_id, ie.etag)

    #bulk create IndividualEnrollments
    enrollments = []
    for i in range(5):
        enrollments.append(IndividualEnrollment.create(registration_id + str(i + 1), att))
    bulk_op = BulkEnrollmentOperation("create", enrollments)

    results = psc.run_bulk_operation(bulk_op)
    six.print_(ie)

    #make a Provisioning Service query
    qs = QuerySpecification("*")
    page_size = 2 #two results per page -> don't pass this parameter if you just want all of them at once
    query = psc.create_individual_enrollment_query(qs, page_size)

    results = []
    for page in query:
        results += page
    #alternatively, call query.next() to get a new page
    six.print_(results)

    #delete the bulk created enrollments
    bulk_op.mode = "delete"
    psc.run_bulk_operation(bulk_op)


if __name__ == '__main__':
    main()
