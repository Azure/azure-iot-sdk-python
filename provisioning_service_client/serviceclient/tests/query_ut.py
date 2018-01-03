# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

from serviceclient.service_client import ProvisioningServiceClient
from serviceclient.models import QuerySpecification
from serviceclient.service.operations import  DeviceEnrollmentOperations
from serviceclient.service.operations.device_enrollment_operations import ClientRawResponse
import unittest
import mock


page1 = [1, 2, 3]

def mock_query_op(self, query_specification, api_version, custom_headers, raw, **operation_config):
    return ClientRawResponse(page1, None)


class TestCaseValidQuery(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cs = "HostName=test-uri.azure-devices-provisioning.net;SharedAccessKeyName=provisioningserviceowner;SharedAccessKey=dGVzdGluZyBhIHNhc3Rva2Vu"
        cls.psc = ProvisioningServiceClient(cs)


class TestCaseIndividualEnrollmentQuery(TestCaseValidQuery):

    def setUp(self):
        qs = QuerySpecification("*")
        self.query = self.psc.create_individual_enrollment_query(qs)

    @mock.patch.object(DeviceEnrollmentOperations, 'query')
    def test_next_manual_no_token(self, mock_query):
        res = self.query.next()
        self.assertEqual(res, page1)

if __name__ == '__main__':
    unittest.main()
