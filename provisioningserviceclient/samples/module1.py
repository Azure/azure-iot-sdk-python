# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

import copy
import context #only needed in this directory

from provisioningserviceclient import ProvisioningServiceClient, QuerySpecification, Query, \
    BulkEnrollmentOperation
from provisioningserviceclient.models import IndividualEnrollment, AttestationMechanism
from provisioningserviceclient import BulkEnrollmentOperation
import serviceswagger.models as genmodels

if __name__ == '__main__':
    connection_string = "HostName=carter-dps-2.azure-devices-provisioning.net;SharedAccessKeyName=provisioningserviceowner;SharedAccessKey=uNqKlY3IR6fB+p78K9mck9PrDsF2uLYpt0r91Hq2gh0="
    
    #set up the provisioning service client
    psc = ProvisioningServiceClient(connection_string)

    #build IndividualEnrollment model
    endorsement_key = "AToAAQALAAMAsgAgg3GXZ0SEs/gakMyNRqXXJP1S124GUgtk8qHaGzMUaaoABgCAAEMAEAgAAAAAAAEAxsj2gUScTk1UjuioeTlfGYZrrimExB+bScH75adUMRIi2UOMxG1kw4y+9RW/IVoMl4e620VxZad0ARX2gUqVjYO7KPVt3dyKhZS3dkcvfBisBhP1XH9B33VqHG9SHnbnQXdBUaCgKAfxome8UmBKfe+naTsE5fkvjb/do3/dD6l4sGBwFCnKRdln4XpM03zLpoHFao8zOwt8l/uP3qUIxmCYv9A7m69Ms+5/pCkTu/rK4mRDsfhZ0QLfbzVI6zQFOKF/rwsfBtFeWlWtcuJMKlXdD8TXWElTzgh7JS4qhFzreL0c1mI0GCj+Aws0usZh7dLIVPnlgZcBhgy1SSDQMQ=="
    registration_id = "java-test"
    att = AttestationMechanism.create_with_tpm(endorsement_key)
    #att.__class__ = genmodels.AttestationMechanism

    qs = QuerySpecification("*")
    q = psc.create_individual_enrollment_query(qs, 1)
    q.next()
    q.next()

    #print ie
    #att = AttestationMechanism.create_with_tpm(endorsement_key)
    #ie1 = IndividualEnrollment("python-test", att)
    #ie2 = IndividualEnrollment("java-test", att)
    #enrollments = [ie1, ie2]
    #bulkop = BulkEnrollmentOperation("create", enrollments)
    #result = psc.run_bulk_operation(bulkop)
    #print result
