# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

from serviceclient.service_client import ProvisioningServiceClient, VERSION
from serviceclient.sastoken import SasTokenFactory
from serviceclient.models import IndividualEnrollment, EnrollmentGroup, \
    DeviceRegistrationState, AttestationMechanismBuilder, BulkEnrollmentOperation, \
    BulkEnrollmentOperationResult, QuerySpecification
from serviceclient.query import Query
from serviceclient.service import DeviceProvisioningServiceServiceRuntimeClient
from serviceclient.service.operations import DeviceEnrollmentOperations, \
    DeviceEnrollmentGroupOperations, RegistrationStatusOperations
import unittest
import mock

def make_ie_tpm():
    tpm_am = AttestationMechanismBuilder.create_tpm_attestation("my-ek")
    ie_tpm = IndividualEnrollment("reg-id", tpm_am)
    ie_tpm.etag = "test-etag"
    return ie_tpm

def make_ret_ie_tpm():
    ret_ie = make_ie_tpm()
    ret_ie.created_updated_time_utc = 1000
    ret_ie.last_updated_time_utc = 1000
    return ret_ie

def make_eg_x509():
    x509_am = AttestationMechanismBuilder.create_x509_attestation_ca_refs("my-ca")
    eg_x509 = EnrollmentGroup("grp-id", x509_am)
    eg_x509.etag = "test-etag"
    return eg_x509

def make_ret_eg_x509():
    ret_eg = make_eg_x509()
    ret_eg.created_updated_time_utc = 1000
    ret_eg.last_updated_time_utc = 1000
    return ret_eg

def make_drs():
    drs = DeviceRegistrationState()
    drs.registration_id = "reg-id"
    return drs

def make_ie_bulk_op():
    enrollments = []
    for i in range(5):
        ie = make_ie_tpm()
        ie.registration_id = "reg-id" + str(i)
        enrollments.append(ie)
    bulk_op = BulkEnrollmentOperation("create", enrollments)

sas = "dummy_token"
ie_tpm = make_ie_tpm()
ie_bulk_op = make_ie_bulk_op()
eg_x509 = make_eg_x509()
drs = make_drs()
ret_ie_tpm = make_ret_ie_tpm()
ret_eg_x509 = make_ret_eg_x509()
ret_bulk_op_res = BulkEnrollmentOperationResult(True)


class TestCreationProvisioningServiceClient(unittest.TestCase):

    def test_basic(self):
        cs = "HostName=test-uri.azure-devices-provisioning.net;SharedAccessKeyName=provisioningserviceowner;SharedAccessKey=dGVzdGluZyBhIHNhc3Rva2Vu"
        psc = ProvisioningServiceClient(cs)

        self.assertEqual(psc.host_name, "test-uri.azure-devices-provisioning.net")
        self.assertEqual(psc.shared_access_key_name, "provisioningserviceowner")
        self.assertEqual(psc.shared_access_key, "dGVzdGluZyBhIHNhc3Rva2Vu")

    def test_reordered_cs_args(self):
        cs = "SharedAccessKey=dGVzdGluZyBhIHNhc3Rva2Vu;HostName=test-uri.azure-devices-provisioning.net;SharedAccessKeyName=provisioningserviceowner"
        psc = ProvisioningServiceClient(cs)

        self.assertEqual(psc.host_name, "test-uri.azure-devices-provisioning.net")
        self.assertEqual(psc.shared_access_key_name, "provisioningserviceowner")
        self.assertEqual(psc.shared_access_key, "dGVzdGluZyBhIHNhc3Rva2Vu")

    def test_fail_too_many_cs_args(self):
        #ExtraVal additional cs val
        cs = "ExtraVal=testingValue;HostName=test-uri.azure-devices-provisioning.net;SharedAccessKeyName=provisioningserviceowner;SharedAccessKey=dGVzdGluZyBhIHNhc3Rva2Vu"
        with self.assertRaises(ValueError):
            psc = ProvisioningServiceClient(cs)

    def test_fail_missing_cs_args(self):
        #HostName is missing
        cs = "SharedAccessKeyName=provisioningserviceowner;SharedAccessKey=dGVzdGluZyBhIHNhc3Rva2Vu"
        with self.assertRaises(ValueError):
            psc = ProvisioningServiceClient(cs)

    def test_fail_replaced_cs_args(self):
        #ExtraVal replaces HostName in cs
        cs = "ExtraVal=testingValue;SharedAccessKeyName=provisioningserviceowner;SharedAccessKey=dGVzdGluZyBhIHNhc3Rva2Vu"
        with self.assertRaises(ValueError):
            psc = ProvisioningServiceClient(cs)

    def test_fail_duplicate_cs_args(self):
        #SharedAccessKeyName defined twice
        cs = "SharedAccessKeyName=provisioningserviceowner;SharedAccessKey=dGVzdGluZyBhIHNhc3Rva2Vu;SharedAccessKeyName=duplicatevalue"
        with self.assertRaises(AttributeError):
            psc = ProvisioningServiceClient(cs)

    def test_fail_invalid_cs(self):
        cs = "not_a_connection_string"
        with self.assertRaises(ValueError):
            psc = ProvisioningServiceClient(cs)


class TestValidProvisioningServiceClient(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cs = "HostName=test-uri.azure-devices-provisioning.net;SharedAccessKeyName=provisioningserviceowner;SharedAccessKey=dGVzdGluZyBhIHNhc3Rva2Vu"
        cls.psc = ProvisioningServiceClient(cs)

    def expected_headers(self):
        headers = {}
        headers["Authorization"] = sas
        return headers


class TestProvisioningServiceClientWithIndividualEnrollment(TestValidProvisioningServiceClient):

    @mock.patch.object(DeviceEnrollmentOperations, 'create_or_update', return_value=ret_ie_tpm)
    @mock.patch.object(SasTokenFactory, 'generate_sastoken', return_value=sas)
    def test_create_or_update_ie(self, mock_sas, mock_create):
        ret = self.psc.create_or_update(ie_tpm)
        self.assertEqual(ret, ret_ie_tpm)
        mock_create.assert_called_with(ie_tpm.registration_id, ie_tpm, VERSION,
                                       ie_tpm.etag, self.expected_headers())

    @mock.patch.object(DeviceEnrollmentOperations, 'get', return_value=ret_ie_tpm)
    @mock.patch.object(SasTokenFactory, 'generate_sastoken', return_value=sas)
    def test_get_individual_enrollment(self, mock_sas, mock_get):
        ret = self.psc.get_individual_enrollment(ie_tpm.registration_id)
        self.assertEqual(ret, ret_ie_tpm)
        mock_get.assert_called_with(ie_tpm.registration_id, VERSION, self.expected_headers()) 

    @mock.patch.object(DeviceEnrollmentOperations, 'delete')
    @mock.patch.object(SasTokenFactory, 'generate_sastoken', return_value=sas)
    def test_delete_individual_enrollment_by_param_w_etag(self, mock_sas, mock_delete):
        self.psc.delete_individual_enrollment_by_param(ie_tpm.registration_id, ie_tpm.etag)
        mock_delete.assert_called_with(ie_tpm.registration_id, VERSION, ie_tpm.etag, self.expected_headers())

    @mock.patch.object(DeviceEnrollmentOperations, 'delete')
    @mock.patch.object(SasTokenFactory, 'generate_sastoken', return_value=sas)
    def test_delete_individual_enrollment_by_param_no_etag(self, mock_sas, mock_delete):
        self.psc.delete_individual_enrollment_by_param(ie_tpm.registration_id)
        mock_delete.assert_called_with(ie_tpm.registration_id, VERSION, None , self.expected_headers())

    @mock.patch.object(ProvisioningServiceClient, 'delete_individual_enrollment_by_param')
    def test_delete_individual_enrollment(self, mock_psc_delete):
        self.psc.delete(ie_tpm)
        mock_psc_delete.assert_called_with(ie_tpm.registration_id, ie_tpm.etag)

    @mock.patch.object(DeviceEnrollmentOperations, 'bulk_operation', return_value=ret_bulk_op_res)
    @mock.patch.object(SasTokenFactory, 'generate_sastoken', return_value=sas)
    def test_run_bulk_operation(self, mock_sas, mock_bulk_op):
        ret = self.psc.run_bulk_operation(ie_bulk_op)
        self.assertEqual(ret, ret_bulk_op_res)
        mock_bulk_op.assert_called_with(ie_bulk_op, VERSION, self.expected_headers())


class TestProvisioningServiceClientWithEnrollmentGroup(TestValidProvisioningServiceClient):

    @mock.patch.object(DeviceEnrollmentGroupOperations, 'create_or_update', return_value=ret_eg_x509)
    @mock.patch.object(SasTokenFactory, 'generate_sastoken', return_value=sas)
    def test_create_or_update_eg(self, mock_sas, mock_create):
        ret = self.psc.create_or_update(eg_x509)
        self.assertEqual(ret, ret_eg_x509)
        mock_create.assert_called_with(eg_x509.enrollment_group_id, eg_x509, VERSION,
                                       eg_x509.etag, self.expected_headers())

    @mock.patch.object(DeviceEnrollmentGroupOperations, 'get', return_value=ret_eg_x509)
    @mock.patch.object(SasTokenFactory, 'generate_sastoken', return_value=sas)
    def test_get_enrollment_group(self, mock_sas, mock_get):
        ret = self.psc.get_enrollment_group(eg_x509.enrollment_group_id)
        self.assertEqual(ret, ret_eg_x509)
        mock_get.assert_called_with(eg_x509.enrollment_group_id, VERSION, self.expected_headers())

    @mock.patch.object(DeviceEnrollmentGroupOperations, 'delete')
    @mock.patch.object(SasTokenFactory, 'generate_sastoken', return_value=sas)
    def test_delete_enrollment_group_by_param_w_etag(self, mock_sas, mock_delete):
        self.psc.delete_enrollment_group_by_param(eg_x509.enrollment_group_id, eg_x509.etag)
        mock_delete.assert_called_with(eg_x509.enrollment_group_id, VERSION, eg_x509.etag, self.expected_headers())

    @mock.patch.object(DeviceEnrollmentGroupOperations, 'delete')
    @mock.patch.object(SasTokenFactory, 'generate_sastoken', return_value=sas)
    def test_delete_enrollment_group_by_param_no_etag(self, mock_sas, mock_delete):
        self.psc.delete_enrollment_group_by_param(eg_x509.enrollment_group_id)
        mock_delete.assert_called_with(eg_x509.enrollment_group_id, VERSION, None , self.expected_headers())

    @mock.patch.object(ProvisioningServiceClient, 'delete_enrollment_group_by_param')
    def test_delete_enrollment_group(self, mock_psc_delete):
        self.psc.delete(eg_x509)
        mock_psc_delete.assert_called_with(eg_x509.enrollment_group_id, eg_x509.etag)


class TestProvisioningServiceClientWithRegistrationState(TestValidProvisioningServiceClient):

    @mock.patch.object(RegistrationStatusOperations, 'get_registration_state', return_value=drs)
    @mock.patch.object(SasTokenFactory, 'generate_sastoken', return_value=sas)
    def test_get_registration_state(self, mock_sas, mock_get):
        ret = self.psc.get_registration_state(drs.registration_id)
        self.assertEqual(ret, drs)
        mock_get.assert_called_with(drs.registration_id, VERSION, self.expected_headers())

    @mock.patch.object(RegistrationStatusOperations, 'delete_registration_state')
    @mock.patch.object(SasTokenFactory, 'generate_sastoken', return_value=sas)
    def test_delete_registration_state_by_param_w_etag(self, mock_sas, mock_delete):
        self.psc.delete_registration_state_by_param(drs.registration_id, drs.etag)
        mock_delete.assert_called_with(drs.registration_id, VERSION, drs.etag, self.expected_headers())

    @mock.patch.object(RegistrationStatusOperations, 'delete_registration_state')
    @mock.patch.object(SasTokenFactory, 'generate_sastoken', return_value=sas)
    def test_delete_registration_state_by_param_no_etag(self, mock_sas, mock_delete):
        self.psc.delete_registration_state_by_param(drs.registration_id)
        mock_delete.assert_called_with(drs.registration_id, VERSION, None, self.expected_headers())


class TestProvisioningServiceClientOtherOperations(TestValidProvisioningServiceClient):

    def test_create_individual_enrollment_query_default_page(self):
        qs = QuerySpecification("*")
        ret = self.psc.create_individual_enrollment_query(qs)
        self.assertIsInstance(ret, Query)
        self.assertEqual(ret._query_spec, qs)
        self.assertEqual(ret._query_fn, self.psc._runtime_client.device_enrollment.query)
        self.assertEqual(ret._sastoken_factory, self.psc._sastoken_factory)
        self.assertEqual(ret.page_size, 10)
        self.assertEqual(ret._api_version, VERSION)

    def test_create_individual_enrollment_query_custom_page(self):
        qs = QuerySpecification("*")
        page_size = 50
        ret = self.psc.create_individual_enrollment_query(qs, page_size)
        self.assertIsInstance(ret, Query)
        self.assertEqual(ret._query_spec, qs)
        self.assertEqual(ret._query_fn, self.psc._runtime_client.device_enrollment.query)
        self.assertEqual(ret._sastoken_factory, self.psc._sastoken_factory)
        self.assertEqual(ret.page_size, page_size)
        self.assertEqual(ret._api_version, VERSION)


class TestProvisioningServiceCleintWithBadInputs(TestValidProvisioningServiceClient):

    def test_create_or_update_wrong_obj_fail(self):
        with self.assertRaises(TypeError):
            self.psc.create_or_update(object())

    def test_delete_wrong_obj_fail(self):
        with self.assertRaises(TypeError):
            self.psc.delete(object())


if __name__ == '__main__':
    unittest.main()
