# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

import six

import context #only needed in this directory
from provisioningserviceclient import ProvisioningServiceClient, QuerySpecification
from provisioningserviceclient.models import EnrollmentGroup, AttestationMechanism


def main():
    connection_string = "[Connection String]"
    signing_cert = "[Signing Cert]"
    group_id = "[Group ID]"

    #set up the provisioning service client
    psc = ProvisioningServiceClient.create_from_connection_string(connection_string)

    #build EnrollmentGroup model
    att = AttestationMechanism.create_with_x509_signing_certs(signing_cert)
    eg = EnrollmentGroup.create(group_id, att)

    #create EnrollmentGroup on the Provisioning Service
    eg = psc.create_or_update(eg)
    six.print_(eg)

    #get EnrollmentGroup from the Provisioning Service (note: this step is useless here, as eg is already up to date)
    eg = psc.get_enrollment_group(group_id)
    six.print_(eg)

    #make a Provisioning Service query
    qs = QuerySpecification("*")
    page_size = 2 #two results per page -> don't pass this parameter if you just want all of them at once
    query = psc.create_enrollment_group_query(qs, page_size)

    results = []
    for page in query:
        results += page
    six.print_(results)
    #alternatively, call query.next() to get a new page

    #delete EnrollmentGroup from the Provisioning Service
    psc.delete(eg)
    #could also use psc.delete_enrollment_group_by_param(eg.group_id, eg.etag)


if __name__ == '__main__':
    main()
