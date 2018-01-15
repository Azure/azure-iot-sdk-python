# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

import copy
import unittest

from six import add_move, MovedModule
add_move(MovedModule('mock', 'mock', 'unittest.mock'))
from six.moves import mock
from msrest.pipeline import ClientRawResponse

from utils.sastoken import SasTokenFactory
from provisioningserviceclient.service_client import ProvisioningServiceClient, \
    BulkEnrollmentOperation, BulkEnrollmentOperationResult, ProvisioningServiceError, \
    _is_successful, _copy_and_unwrap_bulkop
from provisioningserviceclient.models import IndividualEnrollment, EnrollmentGroup, \
    DeviceRegistrationState, AttestationMechanism, DeviceRegistrationState
from provisioningserviceclient.query import QuerySpecification, Query
from serviceswagger import DeviceProvisioningServiceServiceRuntimeClient
from serviceswagger.operations import DeviceEnrollmentOperations, \
    DeviceEnrollmentGroupOperations, RegistrationStateOperations
import serviceswagger.models as genmodels


SAS = "dummy_token"
RESP_MSG = "message"
REG_ID = "reg-id"
SUCCESS = 200
SUCCESS_DEL = 204
FAIL = 400
UNEXPECTED_FAIL = 793


def dummy(arg1, arg2):
    pass


def create_raw_response(body, status, message):
    resp = Response(status, message)
    return ClientRawResponse(body, resp)


def create_PSED_Exception(status, message):
    resp = Response(status, message)
    return genmodels.ProvisioningServiceErrorDetailsException(dummy, resp)


class Response(object):
    def __init__(self, status_code, message):
        self.status_code = status_code
        self.reason = message

    def raise_for_status(arg1):
        pass


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
        headers["Authorization"] = SAS
        return headers


class TestProvisioningServiceClientWithIndividualEnrollment(TestValidProvisioningServiceClient):

    def setUp(self):
        tpm_am = AttestationMechanism.create_with_tpm("my-ek")
        self.ie = IndividualEnrollment.create("reg-id", tpm_am)

        self.ret_ie = copy.deepcopy(self.ie._internal)
        self.ret_ie.created_updated_time_utc = 1000
        self.ret_ie.last_updated_time_utc = 1000

    @mock.patch.object(DeviceEnrollmentOperations, 'create_or_update')
    @mock.patch.object(SasTokenFactory, 'generate_sastoken', return_value=SAS)
    def test_create_or_update_ie_success(self, mock_sas, mock_create):
        mock_create.return_value = create_raw_response(self.ret_ie, SUCCESS, RESP_MSG)
        ret = self.psc.create_or_update(self.ie)
        self.assertIs(ret._internal, self.ret_ie)
        self.assertIsInstance(ret, IndividualEnrollment)
        mock_create.assert_called_with(self.ie.registration_id, self.ie._internal, self.ie.etag, \
            self.expected_headers(), True)

    @mock.patch.object(DeviceEnrollmentOperations, 'create_or_update')
    @mock.patch.object(SasTokenFactory, 'generate_sastoken', return_value=SAS)
    def test_create_or_update_ie_fail(self, mock_sas, mock_create):
        mock_create.return_value = create_raw_response(None, FAIL, RESP_MSG)
        with self.assertRaises(ProvisioningServiceError) as cm:
            ret = self.psc.create_or_update(self.ie)
        e = cm.exception
        self.assertEqual(RESP_MSG, str(e))
        self.assertIsNone(e.cause)
        mock_create.assert_called_with(self.ie.registration_id, self.ie._internal, self.ie.etag, \
            self.expected_headers(), True)

    @mock.patch.object(DeviceEnrollmentOperations, 'create_or_update')
    @mock.patch.object(SasTokenFactory, 'generate_sastoken', return_value=SAS)
    def test_create_or_update_ie_service_exception(self, mock_sas, mock_create):
        mock_ex = create_PSED_Exception(UNEXPECTED_FAIL, RESP_MSG)
        mock_create.side_effect = mock_ex
        with self.assertRaises(ProvisioningServiceError) as cm:
            ret = self.psc.create_or_update(self.ie)
        e = cm.exception
        self.assertEqual(self.psc.err_msg_unexpected.format(UNEXPECTED_FAIL), str(e))
        self.assertIs(e.cause, mock_ex)
        mock_create.assert_called_with(self.ie.registration_id, self.ie._internal, self.ie.etag, \
            self.expected_headers(), True)

    @mock.patch.object(DeviceEnrollmentOperations, 'get')
    @mock.patch.object(SasTokenFactory, 'generate_sastoken', return_value=SAS)
    def test_get_individual_enrollment(self, mock_sas, mock_get):
        mock_get.return_value = create_raw_response(self.ret_ie, SUCCESS, RESP_MSG)
        ret = self.psc.get_individual_enrollment(self.ie.registration_id)
        self.assertIs(ret._internal, self.ret_ie)
        self.assertIsInstance(ret, IndividualEnrollment)
        mock_get.assert_called_with(self.ie.registration_id, self.expected_headers(), True)

    @mock.patch.object(DeviceEnrollmentOperations, 'get')
    @mock.patch.object(SasTokenFactory, 'generate_sastoken', return_value=SAS)
    def test_get_individual_enrollment_fail(self, mock_sas, mock_get):
        mock_get.return_value = create_raw_response(None, FAIL, RESP_MSG)
        with self.assertRaises(ProvisioningServiceError) as cm:
            ret = self.psc.get_individual_enrollment(self.ie.registration_id)
        e = cm.exception
        self.assertEqual(RESP_MSG, str(e))
        self.assertIsNone(e.cause)
        mock_get.assert_called_with(self.ie.registration_id, self.expected_headers(), True)

    @mock.patch.object(DeviceEnrollmentOperations, 'get')
    @mock.patch.object(SasTokenFactory, 'generate_sastoken', return_value=SAS)
    def test_get_individual_enrollment_service_exception(self, mock_sas, mock_get):
        mock_ex = create_PSED_Exception(UNEXPECTED_FAIL, RESP_MSG)
        mock_get.side_effect = mock_ex
        with self.assertRaises(ProvisioningServiceError) as cm:
            ret = self.psc.get_individual_enrollment(self.ie.registration_id)
        e = cm.exception
        self.assertEqual(self.psc.err_msg_unexpected.format(UNEXPECTED_FAIL), str(e))
        self.assertIs(e.cause, mock_ex)
        mock_get.assert_called_with(self.ie.registration_id, self.expected_headers(), True)

    @mock.patch.object(DeviceEnrollmentOperations, 'delete')
    @mock.patch.object(SasTokenFactory, 'generate_sastoken', return_value=SAS)
    def test_delete_individual_enrollment_by_param_w_etag(self, mock_sas, mock_delete):
        mock_delete.return_value = create_raw_response(None, SUCCESS_DEL, RESP_MSG)
        ret = self.psc.delete_individual_enrollment_by_param(self.ie.registration_id, self.ie.etag)
        self.assertIsNone(ret)
        mock_delete.assert_called_with(self.ie.registration_id, self.ie.etag, self.expected_headers(), True)

    @mock.patch.object(DeviceEnrollmentOperations, 'delete')
    @mock.patch.object(SasTokenFactory, 'generate_sastoken', return_value=SAS)
    def test_delete_individual_enrollment_by_param_no_etag(self, mock_sas, mock_delete):
        mock_delete.return_value = create_raw_response(None, SUCCESS_DEL, RESP_MSG)
        ret = self.psc.delete_individual_enrollment_by_param(self.ie.registration_id)
        self.assertIsNone(ret)
        mock_delete.assert_called_with(self.ie.registration_id, None , self.expected_headers(), True)

    @mock.patch.object(DeviceEnrollmentOperations, 'delete')
    @mock.patch.object(SasTokenFactory, 'generate_sastoken', return_value=SAS)
    def test_delete_individual_enrollment_by_param_fail(self, mock_sas, mock_delete):
        mock_delete.return_value = create_raw_response(None, FAIL, RESP_MSG)
        with self.assertRaises(ProvisioningServiceError) as cm:
            ret = self.psc.delete_individual_enrollment_by_param(self.ie.registration_id, self.ie.etag)
        e = cm.exception
        self.assertEqual(RESP_MSG, str(e))
        self.assertIsNone(e.cause)
        mock_delete.assert_called_with(self.ie.registration_id, self.ie.etag, self.expected_headers(), True)

    @mock.patch.object(DeviceEnrollmentOperations, 'delete')
    @mock.patch.object(SasTokenFactory, 'generate_sastoken', return_value=SAS)
    def test_delete_individual_enrollment_by_param_service_exception(self, mock_sas, mock_delete):
        mock_ex = create_PSED_Exception(UNEXPECTED_FAIL, RESP_MSG)
        mock_delete.side_effect = mock_ex
        with self.assertRaises(ProvisioningServiceError) as cm:
            ret = self.psc.delete_individual_enrollment_by_param(self.ie.registration_id, self.ie.etag)
        e = cm.exception
        self.assertEqual(self.psc.err_msg_unexpected.format(UNEXPECTED_FAIL), str(e))
        self.assertIs(e.cause, mock_ex)
        mock_delete.assert_called_with(self.ie.registration_id, self.ie.etag, self.expected_headers(), True)

    @mock.patch.object(ProvisioningServiceClient, 'delete_individual_enrollment_by_param')
    def test_delete_individual_enrollment(self, mock_psc_delete):
        self.psc.delete(self.ie)
        mock_psc_delete.assert_called_with(self.ie.registration_id, self.ie.etag)


class TestProvisioningServiceClientWithEnrollmentGroup(TestValidProvisioningServiceClient):

    def setUp(self):
        x509_am = AttestationMechanism.create_with_x509_signing_certs("test-cert")
        self.eg = EnrollmentGroup.create("grp-id", x509_am)

        self.ret_eg = copy.deepcopy(self.eg)
        self.ret_eg.created_updated_time_utc = 1000
        self.ret_eg.last_updated_time_utc = 1000

    @mock.patch.object(DeviceEnrollmentGroupOperations, 'create_or_update')
    @mock.patch.object(SasTokenFactory, 'generate_sastoken', return_value=SAS)
    def test_create_or_update_eg(self, mock_sas, mock_create):
        mock_create.return_value = create_raw_response(self.ret_eg, SUCCESS, RESP_MSG)
        ret = self.psc.create_or_update(self.eg)
        self.assertIs(ret._internal, self.ret_eg)
        self.assertIsInstance(ret, EnrollmentGroup)
        mock_create.assert_called_with(self.eg.enrollment_group_id, self.eg._internal, self.eg.etag, \
            self.expected_headers(), True)

    @mock.patch.object(DeviceEnrollmentGroupOperations, 'create_or_update')
    @mock.patch.object(SasTokenFactory, 'generate_sastoken', return_value=SAS)
    def test_create_or_update_eg_fail(self, mock_sas, mock_create):
        mock_create.return_value = create_raw_response(None, FAIL, RESP_MSG)
        with self.assertRaises(ProvisioningServiceError) as cm:
            ret = self.psc.create_or_update(self.eg)
        e = cm.exception
        self.assertEqual(RESP_MSG, str(e))
        self.assertIsNone(e.cause)
        mock_create.assert_called_with(self.eg.enrollment_group_id, self.eg._internal, self.eg.etag, \
            self.expected_headers(), True)

    @mock.patch.object(DeviceEnrollmentGroupOperations, 'create_or_update')
    @mock.patch.object(SasTokenFactory, 'generate_sastoken', return_value=SAS)
    def test_create_or_update_eg_service_exception(self, mock_sas, mock_create):
        mock_ex = create_PSED_Exception(UNEXPECTED_FAIL, RESP_MSG)
        mock_create.side_effect = mock_ex
        with self.assertRaises(ProvisioningServiceError) as cm:
            ret = self.psc.create_or_update(self.eg)
        e = cm.exception
        self.assertEqual(self.psc.err_msg_unexpected.format(UNEXPECTED_FAIL), str(e))
        self.assertIs(e.cause, mock_ex)
        mock_create.assert_called_with(self.eg.enrollment_group_id, self.eg._internal, self.eg.etag, \
            self.expected_headers(), True)

    @mock.patch.object(DeviceEnrollmentGroupOperations, 'get')
    @mock.patch.object(SasTokenFactory, 'generate_sastoken', return_value=SAS)
    def test_get_enrollment_group(self, mock_sas, mock_get):
        mock_get.return_value = create_raw_response(self.ret_eg, SUCCESS, RESP_MSG)
        ret = self.psc.get_enrollment_group(self.eg.enrollment_group_id)
        self.assertIs(ret._internal, self.ret_eg)
        self.assertIsInstance(ret, EnrollmentGroup)
        mock_get.assert_called_with(self.eg.enrollment_group_id, self.expected_headers(), True)

    @mock.patch.object(DeviceEnrollmentGroupOperations, 'get')
    @mock.patch.object(SasTokenFactory, 'generate_sastoken', return_value=SAS)
    def test_get_enrollment_group_fail(self, mock_sas, mock_get):
        mock_get.return_value = create_raw_response(None, FAIL, RESP_MSG)
        with self.assertRaises(ProvisioningServiceError) as cm:
            ret = self.psc.get_enrollment_group(self.eg.enrollment_group_id)
        e = cm.exception
        self.assertEqual(RESP_MSG, str(e))
        self.assertIsNone(e.cause)
        mock_get.assert_called_with(self.eg.enrollment_group_id, self.expected_headers(), True)

    @mock.patch.object(DeviceEnrollmentGroupOperations, 'get')
    @mock.patch.object(SasTokenFactory, 'generate_sastoken', return_value=SAS)
    def test_get_enrollment_group_service_exception(self, mock_sas, mock_get):
        mock_ex = create_PSED_Exception(UNEXPECTED_FAIL, RESP_MSG)
        mock_get.side_effect = mock_ex
        with self.assertRaises(ProvisioningServiceError) as cm:
            ret = self.psc.get_enrollment_group(self.eg.enrollment_group_id)
        e = cm.exception
        self.assertEqual(self.psc.err_msg_unexpected.format(UNEXPECTED_FAIL), str(e))
        self.assertIs(e.cause, mock_ex)
        mock_get.assert_called_with(self.eg.enrollment_group_id, self.expected_headers(), True)

    @mock.patch.object(DeviceEnrollmentGroupOperations, 'delete')
    @mock.patch.object(SasTokenFactory, 'generate_sastoken', return_value=SAS)
    def test_delete_enrollment_group_by_param_w_etag(self, mock_sas, mock_delete):
        mock_delete.return_value = create_raw_response(None, SUCCESS_DEL, RESP_MSG)
        ret = self.psc.delete_enrollment_group_by_param(self.eg.enrollment_group_id, self.eg.etag)
        self.assertIsNone(ret)
        mock_delete.assert_called_with(self.eg.enrollment_group_id, self.eg.etag, self.expected_headers(), True)

    @mock.patch.object(DeviceEnrollmentGroupOperations, 'delete')
    @mock.patch.object(SasTokenFactory, 'generate_sastoken', return_value=SAS)
    def test_delete_enrollment_group_by_param_no_etag(self, mock_sas, mock_delete):
        mock_delete.return_value = create_raw_response(None, SUCCESS_DEL, RESP_MSG)
        ret = self.psc.delete_enrollment_group_by_param(self.eg.enrollment_group_id)
        self.assertIsNone(ret)
        mock_delete.assert_called_with(self.eg.enrollment_group_id, None , self.expected_headers(), True)

    @mock.patch.object(DeviceEnrollmentGroupOperations, 'delete')
    @mock.patch.object(SasTokenFactory, 'generate_sastoken', return_value=SAS)
    def test_delete_enrollment_group_by_param_fail(self, mock_sas, mock_delete):
        mock_delete.return_value = create_raw_response(None, FAIL, RESP_MSG)
        with self.assertRaises(ProvisioningServiceError) as cm:
            ret = self.psc.delete_enrollment_group_by_param(self.eg.enrollment_group_id, self.eg.etag)
        e = cm.exception
        self.assertEqual(RESP_MSG, str(e))
        self.assertIsNone(e.cause)
        mock_delete.assert_called_with(self.eg.enrollment_group_id, self.eg.etag, self.expected_headers(), True)

    @mock.patch.object(DeviceEnrollmentGroupOperations, 'delete')
    @mock.patch.object(SasTokenFactory, 'generate_sastoken', return_value=SAS)
    def test_delete_enrollment_group_by_param_service_exception(self, mock_sas, mock_delete):
        mock_ex = create_PSED_Exception(UNEXPECTED_FAIL, RESP_MSG)
        mock_delete.side_effect = mock_ex
        with self.assertRaises(ProvisioningServiceError) as cm:
            ret = self.psc.delete_enrollment_group_by_param(self.eg.enrollment_group_id, self.eg.etag)
        e = cm.exception
        self.assertEqual(self.psc.err_msg_unexpected.format(UNEXPECTED_FAIL), str(e))
        self.assertIs(e.cause, mock_ex)
        mock_delete.assert_called_with(self.eg.enrollment_group_id, self.eg.etag, self.expected_headers(), True)

    @mock.patch.object(ProvisioningServiceClient, 'delete_enrollment_group_by_param')
    def test_delete_enrollment_group(self, mock_psc_delete):
        self.psc.delete(self.eg)
        mock_psc_delete.assert_called_with(self.eg.enrollment_group_id, self.eg.etag)


class TestProvisioningServiceClientWithRegistrationState(TestValidProvisioningServiceClient):

    def setUp(self):
        self.drs = DeviceRegistrationState(genmodels.DeviceRegistrationState("reg-id", "assigned"))

        self.ret_drs = copy.deepcopy(self.drs._internal)
        self.ret_drs.created_updated_time_utc = 1000
        self.ret_drs.last_updated_time_utc = 1000

    @mock.patch.object(RegistrationStateOperations, 'get_registration_state')
    @mock.patch.object(SasTokenFactory, 'generate_sastoken', return_value=SAS)
    def test_get_registration_state(self, mock_sas, mock_get):
        mock_get.return_value = create_raw_response(self.ret_drs, SUCCESS, RESP_MSG)
        ret = self.psc.get_registration_state(self.drs.registration_id)
        self.assertIs(ret._internal, self.ret_drs)
        self.assertIsInstance(ret, DeviceRegistrationState)
        mock_get.assert_called_with(self.drs.registration_id, self.expected_headers(), True)

    @mock.patch.object(RegistrationStateOperations, 'get_registration_state')
    @mock.patch.object(SasTokenFactory, 'generate_sastoken', return_value=SAS)
    def test_get_registration_state_fail(self, mock_sas, mock_get):
        mock_get.return_value = create_raw_response(self.ret_drs, FAIL, RESP_MSG)
        with self.assertRaises(ProvisioningServiceError) as cm:
            ret = self.psc.get_registration_state(self.drs.registration_id)
        e = cm.exception
        self.assertEqual(str(e), RESP_MSG)
        self.assertIsNone(e.cause)
        mock_get.assert_called_with(self.drs.registration_id, self.expected_headers(), True)

    @mock.patch.object(RegistrationStateOperations, 'get_registration_state')
    @mock.patch.object(SasTokenFactory, 'generate_sastoken', return_value=SAS)
    def test_get_registration_state_service_fail(self, mock_sas, mock_get):
        mock_ex = create_PSED_Exception(UNEXPECTED_FAIL, RESP_MSG)
        mock_get.side_effect = mock_ex
        with self.assertRaises(ProvisioningServiceError) as cm:
            ret = self.psc.get_registration_state(self.drs.registration_id)
        e = cm.exception
        self.assertEqual(str(e), self.psc.err_msg_unexpected.format(UNEXPECTED_FAIL))
        self.assertIs(e.cause, mock_ex)
        mock_get.assert_called_with(self.drs.registration_id, self.expected_headers(), True)

    @mock.patch.object(RegistrationStateOperations, 'delete_registration_state')
    @mock.patch.object(SasTokenFactory, 'generate_sastoken', return_value=SAS)
    def test_delete_registration_state_by_param_w_etag(self, mock_sas, mock_delete):
        mock_delete.return_value = create_raw_response(None, SUCCESS_DEL, RESP_MSG)
        ret = self.psc.delete_registration_state_by_param(self.drs.registration_id, self.drs.etag)
        self.assertIsNone(ret)
        mock_delete.assert_called_with(self.drs.registration_id, self.drs.etag, self.expected_headers(), True)

    @mock.patch.object(RegistrationStateOperations, 'delete_registration_state')
    @mock.patch.object(SasTokenFactory, 'generate_sastoken', return_value=SAS)
    def test_delete_registration_state_by_param_no_etag(self, mock_sas, mock_delete):
        mock_delete.return_value = create_raw_response(None, SUCCESS_DEL, RESP_MSG)
        ret = self.psc.delete_registration_state_by_param(self.drs.registration_id)
        self.assertIsNone(ret)
        mock_delete.assert_called_with(self.drs.registration_id, None, self.expected_headers(), True)

    @mock.patch.object(RegistrationStateOperations, 'delete_registration_state')
    @mock.patch.object(SasTokenFactory, 'generate_sastoken', return_value=SAS)
    def test_delete_registration_state_fail(self, mock_sas, mock_delete):
        mock_delete.return_value = create_raw_response(None, FAIL, RESP_MSG)
        with self.assertRaises(ProvisioningServiceError) as cm:
            ret = self.psc.delete_registration_state_by_param(self.drs.registration_id, self.drs.etag)
        e = cm.exception
        self.assertEqual(str(e), RESP_MSG)
        self.assertIsNone(e.cause)
        mock_delete.assert_called_with(self.drs.registration_id, self.drs.etag, self.expected_headers(), True)

    @mock.patch.object(RegistrationStateOperations, 'delete_registration_state')
    @mock.patch.object(SasTokenFactory, 'generate_sastoken', return_value=SAS)
    def test_delete_registration_state_service_exception(self, mock_sas, mock_delete):
        mock_ex = create_PSED_Exception(UNEXPECTED_FAIL, RESP_MSG)
        mock_delete.side_effect = mock_ex
        with self.assertRaises(ProvisioningServiceError) as cm:
            ret = self.psc.delete_registration_state_by_param(self.drs.registration_id, self.drs.etag)
        e = cm.exception
        self.assertEqual(str(e), self.psc.err_msg_unexpected.format(UNEXPECTED_FAIL))
        self.assertIs(e.cause, mock_ex)
        mock_delete.assert_called_with(self.drs.registration_id, self.drs.etag, self.expected_headers(), True)


class TestProvisioningServiceClientBulkOperation(TestValidProvisioningServiceClient):

    def setUp(self):
        enrollments = []
        for i in range(5):
            att = AttestationMechanism.create_with_tpm("test-ek")
            enrollments.append(IndividualEnrollment.create("reg-id" + str(i), att))
        self.bulkop = BulkEnrollmentOperation("create", enrollments)

        internal = []
        for enrollment in self.bulkop.enrollments:
            internal.append(enrollment._internal)
        self.internal_bulkop = BulkEnrollmentOperation("create", internal)

        self.bulkop_resp = BulkEnrollmentOperationResult(True)

    @mock.patch.object(DeviceEnrollmentOperations, 'bulk_operation')
    @mock.patch('provisioningserviceclient.service_client._copy_and_unwrap_bulkop')
    @mock.patch.object(SasTokenFactory, 'generate_sastoken', return_value=SAS)
    def test_run_bulk_operation_op_success(self, mock_sas, mock_unwrap, mock_bulk_op):
        mock_bulk_op.return_value = create_raw_response(self.bulkop_resp, SUCCESS, RESP_MSG)
        mock_unwrap.return_value = self.internal_bulkop
        ret = self.psc.run_bulk_operation(self.bulkop)
        self.assertEqual(ret, self.bulkop_resp)
        self.assertIsInstance(ret, BulkEnrollmentOperationResult)
        mock_bulk_op.assert_called_with(self.internal_bulkop, self.expected_headers(), True)

    @mock.patch.object(DeviceEnrollmentOperations, 'bulk_operation')
    @mock.patch('provisioningserviceclient.service_client._copy_and_unwrap_bulkop')
    @mock.patch.object(SasTokenFactory, 'generate_sastoken', return_value=SAS)
    def test_run_bulk_operation_op_fail(self, mock_sas, mock_unwrap, mock_bulk_op):
        self.bulkop_resp.is_successful = False
        mock_bulk_op.return_value = create_raw_response(self.bulkop_resp, SUCCESS, RESP_MSG)
        mock_unwrap.return_value = self.internal_bulkop
        ret = self.psc.run_bulk_operation(self.bulkop)
        self.assertEqual(ret, self.bulkop_resp)
        self.assertIsInstance(ret, BulkEnrollmentOperationResult)
        mock_bulk_op.assert_called_with(self.internal_bulkop, self.expected_headers(), True)

    @mock.patch.object(DeviceEnrollmentOperations, 'bulk_operation')
    @mock.patch('provisioningserviceclient.service_client._copy_and_unwrap_bulkop')
    @mock.patch.object(SasTokenFactory, 'generate_sastoken', return_value=SAS)
    def test_run_bulk_operation_fail_response(self, mock_sas, mock_unwrap, mock_bulk_op):
        mock_bulk_op.return_value = create_raw_response(None, FAIL, RESP_MSG)
        mock_unwrap.return_value = self.internal_bulkop
        with self.assertRaises(ProvisioningServiceError) as cm:
            ret = self.psc.run_bulk_operation(self.bulkop)
        e = cm.exception
        self.assertEqual(str(e), RESP_MSG)
        self.assertIsNone(e.cause)
        mock_bulk_op.assert_called_with(self.internal_bulkop, self.expected_headers(), True)

    @mock.patch.object(DeviceEnrollmentOperations, 'bulk_operation')
    @mock.patch('provisioningserviceclient.service_client._copy_and_unwrap_bulkop')
    @mock.patch.object(SasTokenFactory, 'generate_sastoken', return_value=SAS)
    def test_run_bulk_operation_service_exception(self, mock_sas, mock_unwrap, mock_bulk_op):
        mock_unwrap.return_value = self.internal_bulkop
        mock_ex = create_PSED_Exception(UNEXPECTED_FAIL, RESP_MSG)
        mock_bulk_op.side_effect = mock_ex
        with self.assertRaises(ProvisioningServiceError) as cm:
            ret = self.psc.run_bulk_operation(self.bulkop)
        e = cm.exception
        self.assertEqual(str(e), self.psc.err_msg_unexpected.format(UNEXPECTED_FAIL))
        self.assertIs(e.cause, mock_ex)
        mock_bulk_op.assert_called_with(self.internal_bulkop, self.expected_headers(), True)


class TestProvisioningServiceClientOtherOperations(TestValidProvisioningServiceClient):

    @mock.patch('provisioningserviceclient.service_client.Query', autospec=True)
    def test_create_individual_enrollment_query_default_page(self, mock_query):

        qs = QuerySpecification("*")
        ret = self.psc.create_individual_enrollment_query(qs)
        mock_query.assert_called_with(qs, self.psc._runtime_client.device_enrollment.query, \
            self.psc._sastoken_factory, None)
        self.assertIs(ret, mock_query.return_value)

    @mock.patch('provisioningserviceclient.service_client.Query', autospec=True)
    def test_create_individual_enrollment_query_custom_page(self, mock_query):
        qs = QuerySpecification("*")
        page_size = 50
        ret = self.psc.create_individual_enrollment_query(qs, page_size)
        mock_query.assert_called_with(qs, self.psc._runtime_client.device_enrollment.query, \
            self.psc._sastoken_factory, page_size)
        self.assertIs(ret, mock_query.return_value)

    @mock.patch('provisioningserviceclient.service_client.Query', autospec=True)
    def test_create_enrollment_group_query_default_page(self, mock_query):
        qs = QuerySpecification("*")
        ret = self.psc.create_enrollment_group_query(qs)
        mock_query.assert_called_with(qs, self.psc._runtime_client.device_enrollment_group.query, \
            self.psc._sastoken_factory, None)
        self.assertIs(ret, mock_query.return_value)

    @mock.patch('provisioningserviceclient.service_client.Query', autospec=True)
    def test_create_enrollment_group_query_custom_page(self, mock_query):
        qs = QuerySpecification("*")
        page_size = 50
        ret = self.psc.create_enrollment_group_query(qs, page_size)
        mock_query.assert_called_with(qs, self.psc._runtime_client.device_enrollment_group.query, \
            self.psc._sastoken_factory, page_size)
        self.assertIs(ret, mock_query.return_value)

    @mock.patch('provisioningserviceclient.service_client.Query', autospec=True)
    def test_create_registration_state_query_default_page(self, mock_query):
        id = REG_ID
        ret = self.psc.create_registration_state_query(id)
        mock_query.assert_called_with(id, self.psc._runtime_client.registration_state.query_registration_state, \
            self.psc._sastoken_factory, None)
        self.assertIs(ret, mock_query.return_value)

    @mock.patch('provisioningserviceclient.service_client.Query', autospec=True)
    def test_create_registration_state_query_custom_page(self, mock_query):
        id = REG_ID
        page_size = 50
        ret = self.psc.create_registration_state_query(id, page_size)
        mock_query.assert_called_with(id, self.psc._runtime_client.registration_state.query_registration_state, \
            self.psc._sastoken_factory, page_size)
        self.assertIs(ret, mock_query.return_value)


class TestProvisioningServiceCleintWithBadInputs(TestValidProvisioningServiceClient):

    def test_create_or_update_wrong_obj_fail(self):
        with self.assertRaises(TypeError):
            self.psc.create_or_update(object())

    def test_delete_wrong_obj_fail(self):
        with self.assertRaises(TypeError):
            self.psc.delete(object())


class TestHelperFunctions(unittest.TestCase):

    def test_is_successful(self):
        for i in range(999):
            ret = _is_successful(i)

            if i == 200 or i == 204:
                self.assertTrue(ret)
            else:
                self.assertFalse(ret)

    def test_copy_and_unwrap_bulkop(self):
        enrollments = []
        for i in range(5):
            att = AttestationMechanism.create_with_tpm("test-ek")
            enrollments.append(IndividualEnrollment.create("reg-id" + str(i), att))
        bulkop = BulkEnrollmentOperation("create", enrollments)

        res = _copy_and_unwrap_bulkop(bulkop)

        for i in range(len(res.enrollments)):
            self.assertIs(res.enrollments[i], bulkop.enrollments[i]._internal)
        

if __name__ == '__main__':
    unittest.main()
