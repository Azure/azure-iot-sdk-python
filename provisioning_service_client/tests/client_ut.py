# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

import copy
import unittest

from six import add_move, MovedModule
add_move(MovedModule('mock', 'mock', 'unittest.mock'))
from six.moves import mock
from msrest.pipeline import ClientRawResponse

import context
from provisioningserviceclient.client import ProvisioningServiceClient, \
    BulkEnrollmentOperation, BulkEnrollmentOperationResult, ProvisioningServiceError
from provisioningserviceclient.models import IndividualEnrollment, EnrollmentGroup, \
    DeviceRegistrationState, AttestationMechanism, DeviceRegistrationState, InitialTwin, \
    TwinCollection, InitialTwinProperties
from provisioningserviceclient import QuerySpecification, Query
from provisioningserviceclient.protocol import ProvisioningServiceClient as GeneratedProvisioningServiceClient
import provisioningserviceclient.protocol.models as genmodels


RESP_MSG = "message"
REG_ID = "reg-id"
FAIL = 400
TAGS = {"key": "value1"}
DESIRED_PROPERTIES = {"key" : "value2"}


def dummy(arg1, arg2):
    pass


def create_PSED_Exception(status, message):
    resp = Response(status, message)
    return genmodels.ProvisioningServiceErrorDetailsException(dummy, resp)


class Response(object):
    def __init__(self, status_code, message):
        self.status_code = status_code
        self.reason = message

    def raise_for_status(self):
        pass


class TestCreationProvisioningServiceClient(unittest.TestCase):

    def test_create_w_params(self):
        psc = ProvisioningServiceClient("test-uri.azure-devices-provisioning.net", \
            "provisioningserviceowner", "dGVzdGluZyBhIHNhc3Rva2Vu")

        self.assertEqual(psc.host_name, "test-uri.azure-devices-provisioning.net")
        self.assertEqual(psc.shared_access_key_name, "provisioningserviceowner")
        self.assertEqual(psc.shared_access_key, "dGVzdGluZyBhIHNhc3Rva2Vu")
        self.assertIsInstance(psc._runtime_client, GeneratedProvisioningServiceClient)

    def test_basic_cs(self):
        cs = "HostName=test-uri.azure-devices-provisioning.net;SharedAccessKeyName=provisioningserviceowner;SharedAccessKey=dGVzdGluZyBhIHNhc3Rva2Vu"
        psc = ProvisioningServiceClient.create_from_connection_string(cs)

        self.assertEqual(psc.host_name, "test-uri.azure-devices-provisioning.net")
        self.assertEqual(psc.shared_access_key_name, "provisioningserviceowner")
        self.assertEqual(psc.shared_access_key, "dGVzdGluZyBhIHNhc3Rva2Vu")
        self.assertIsInstance(psc._runtime_client, GeneratedProvisioningServiceClient)

    def test_reordered_cs_args(self):
        cs = "SharedAccessKey=dGVzdGluZyBhIHNhc3Rva2Vu;HostName=test-uri.azure-devices-provisioning.net;SharedAccessKeyName=provisioningserviceowner"
        psc = ProvisioningServiceClient.create_from_connection_string(cs)

        self.assertEqual(psc.host_name, "test-uri.azure-devices-provisioning.net")
        self.assertEqual(psc.shared_access_key_name, "provisioningserviceowner")
        self.assertEqual(psc.shared_access_key, "dGVzdGluZyBhIHNhc3Rva2Vu")
        self.assertIsInstance(psc._runtime_client, GeneratedProvisioningServiceClient)

    def test_fail_too_many_cs_args(self):
        #ExtraVal additional cs val
        cs = "ExtraVal=testingValue;HostName=test-uri.azure-devices-provisioning.net;SharedAccessKeyName=provisioningserviceowner;SharedAccessKey=dGVzdGluZyBhIHNhc3Rva2Vu"
        with self.assertRaises(ValueError):
            psc = ProvisioningServiceClient.create_from_connection_string(cs)

    def test_fail_missing_cs_args(self):
        #HostName is missing
        cs = "SharedAccessKeyName=provisioningserviceowner;SharedAccessKey=dGVzdGluZyBhIHNhc3Rva2Vu"
        with self.assertRaises(ValueError):
            psc = ProvisioningServiceClient.create_from_connection_string(cs)

    def test_fail_replaced_cs_args(self):
        #ExtraVal replaces HostName in cs
        cs = "ExtraVal=testingValue;SharedAccessKeyName=provisioningserviceowner;SharedAccessKey=dGVzdGluZyBhIHNhc3Rva2Vu"
        with self.assertRaises(ValueError):
            psc = ProvisioningServiceClient.create_from_connection_string(cs)

    def test_fail_duplicate_cs_args(self):
        #SharedAccessKeyName defined twice
        cs = "SharedAccessKeyName=provisioningserviceowner;SharedAccessKey=dGVzdGluZyBhIHNhc3Rva2Vu;SharedAccessKeyName=duplicatevalue"
        with self.assertRaises(UnboundLocalError):
            psc = ProvisioningServiceClient.create_from_connection_string(cs)

    def test_fail_invalid_cs(self):
        cs = "not_a_connection_string"
        with self.assertRaises(ValueError):
            psc = ProvisioningServiceClient.create_from_connection_string(cs)


class TestValidProvisioningServiceClient(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cs = "HostName=test-uri.azure-devices-provisioning.net;SharedAccessKeyName=provisioningserviceowner;SharedAccessKey=dGVzdGluZyBhIHNhc3Rva2Vu"
        cls.psc = ProvisioningServiceClient.create_from_connection_string(cs)

    def expected_headers(self):
        headers = {}
        headers["Authorization"] = SAS
        return headers


class TestProvisioningServiceClientWithIndividualEnrollment(TestValidProvisioningServiceClient):

    def setUp(self):
        self.am = AttestationMechanism.create_with_tpm("my-ek")
        tags_tc = TwinCollection(additional_properties=TAGS)
        desired_properties_tc = TwinCollection(additional_properties=DESIRED_PROPERTIES)
        properties = InitialTwinProperties(desired=desired_properties_tc)
        twin = genmodels.InitialTwin(tags=tags_tc, properties=properties)
        self.ie = IndividualEnrollment.create("reg-id", self.am, initial_twin=twin)

        self.ret_ie = copy.deepcopy(self.ie)
        self.ret_ie.created_updated_time_utc = 1000
        self.ret_ie.last_updated_time_utc = 1000

        twin_wrapper = InitialTwin._create_from_internal(self.ie.initial_twin)
        self.ie.initial_twin = twin_wrapper

    @mock.patch.object(GeneratedProvisioningServiceClient, 'create_or_update_individual_enrollment')
    def test_create_or_update_ie_success(self, mock_create):
        mock_create.return_value = self.ret_ie
        ret = self.psc.create_or_update(self.ie)
        self.assertIs(ret, self.ret_ie)
        self.assertIsInstance(ret, IndividualEnrollment)
        self.assertIsInstance(self.ie.initial_twin, InitialTwin) #wrapper still exists on input
        self.assertIsInstance(ret.initial_twin, InitialTwin) #wrapping layer added
        self.assertIsInstance(ret.initial_twin._internal, genmodels.InitialTwin)
        mock_create.assert_called_with(self.ie.registration_id, self.ie, self.ie.etag)
    
    @mock.patch.object(GeneratedProvisioningServiceClient, 'create_or_update_individual_enrollment')
    def test_create_or_update_ie_protocol_exception(self, mock_create):
        mock_ex = create_PSED_Exception(FAIL, RESP_MSG)
        mock_create.side_effect = mock_ex
        with self.assertRaises(ProvisioningServiceError) as cm:
            ret = self.psc.create_or_update(self.ie)
        e = cm.exception
        self.assertIsInstance(self.ie.initial_twin, InitialTwin) #wrapper still exists on input
        self.assertEqual(self.psc.err_msg.format(FAIL, RESP_MSG), str(e))
        self.assertIs(e.cause, mock_ex)
        mock_create.assert_called_with(self.ie.registration_id, self.ie, self.ie.etag)

    @mock.patch.object(GeneratedProvisioningServiceClient, 'get_individual_enrollment')
    def test_get_individual_enrollment(self, mock_get):
        mock_get.return_value = self.ret_ie
        ret = self.psc.get_individual_enrollment(self.ie.registration_id)
        self.assertIs(ret, self.ret_ie)
        self.assertIsInstance(ret, IndividualEnrollment)
        self.assertIsInstance(ret.initial_twin, InitialTwin) #wrapping layer added
        self.assertIsInstance(ret.initial_twin._internal, genmodels.InitialTwin)
        mock_get.assert_called_with(self.ie.registration_id)

    @mock.patch.object(GeneratedProvisioningServiceClient, 'get_individual_enrollment')
    def test_get_individual_enrollment_protocol_exception(self, mock_get):
        mock_ex = create_PSED_Exception(FAIL, RESP_MSG)
        mock_get.side_effect = mock_ex
        with self.assertRaises(ProvisioningServiceError) as cm:
            ret = self.psc.get_individual_enrollment(self.ie.registration_id)
        e = cm.exception
        self.assertEqual(self.psc.err_msg.format(FAIL, RESP_MSG), str(e))
        self.assertIs(e.cause, mock_ex)
        mock_get.assert_called_with(self.ie.registration_id)

    @mock.patch.object(GeneratedProvisioningServiceClient, 'get_individual_enrollment_attestation_mechanism')
    def test_get_individual_enrollment_attestation_mechanism(self, mock_get):
        mock_get.return_value = self.am
        ret = self.psc.get_individual_enrollment_attestation_mechanism(self.ie.registration_id)
        self.assertIs(ret, self.am)
        self.assertIsInstance(ret, AttestationMechanism)
        mock_get.assert_called_with(self.ie.registration_id)

    @mock.patch.object(GeneratedProvisioningServiceClient, 'get_individual_enrollment_attestation_mechanism')
    def test_get_individual_enrollment_attestation_mechanism_protocol_exception(self, mock_get):
        mock_ex = create_PSED_Exception(FAIL, RESP_MSG)
        mock_get.side_effect = mock_ex
        with self.assertRaises(ProvisioningServiceError) as cm:
            ret = self.psc.get_individual_enrollment_attestation_mechanism(self.ie.registration_id)
        e = cm.exception
        self.assertEqual(self.psc.err_msg.format(FAIL, RESP_MSG), str(e))
        self.assertIs(e.cause, mock_ex)
        mock_get.assert_called_with(self.ie.registration_id)

    @mock.patch.object(GeneratedProvisioningServiceClient, 'delete_individual_enrollment')
    def test_delete_individual_enrollment_by_param_w_etag(self, mock_delete):
        ret = self.psc.delete_individual_enrollment_by_param(self.ie.registration_id, self.ie.etag)
        self.assertIsNone(ret)
        mock_delete.assert_called_with(self.ie.registration_id, self.ie.etag)

    @mock.patch.object(GeneratedProvisioningServiceClient, 'delete_individual_enrollment')
    def test_delete_individual_enrollment_by_param_no_etag(self, mock_delete):
        ret = self.psc.delete_individual_enrollment_by_param(self.ie.registration_id)
        self.assertIsNone(ret)
        mock_delete.assert_called_with(self.ie.registration_id, None)

    @mock.patch.object(GeneratedProvisioningServiceClient, 'delete_individual_enrollment')
    def test_delete_individual_enrollment_by_param_protocol_exception(self, mock_delete):
        mock_ex = create_PSED_Exception(FAIL, RESP_MSG)
        mock_delete.side_effect = mock_ex
        with self.assertRaises(ProvisioningServiceError) as cm:
            ret = self.psc.delete_individual_enrollment_by_param(self.ie.registration_id, self.ie.etag)
        e = cm.exception
        self.assertEqual(self.psc.err_msg.format(FAIL, RESP_MSG), str(e))
        self.assertIs(e.cause, mock_ex)
        mock_delete.assert_called_with(self.ie.registration_id, self.ie.etag)

    @mock.patch.object(ProvisioningServiceClient, 'delete_individual_enrollment_by_param')
    def test_delete_individual_enrollment(self, mock_psc_delete):
        self.psc.delete(self.ie)
        mock_psc_delete.assert_called_with(self.ie.registration_id, self.ie.etag)


class TestProvisioningServiceClientWithEnrollmentGroup(TestValidProvisioningServiceClient):
    
    def setUp(self):
        self.am = AttestationMechanism.create_with_x509_signing_certs("test-cert")
        tags_tc = TwinCollection(additional_properties=TAGS)
        desired_properties_tc = TwinCollection(additional_properties=DESIRED_PROPERTIES)
        properties = InitialTwinProperties(desired=desired_properties_tc)
        twin = genmodels.InitialTwin(tags=tags_tc, properties=properties)
        self.eg = EnrollmentGroup.create("grp-id", self.am, initial_twin=twin)

        self.ret_eg = copy.deepcopy(self.eg)
        self.ret_eg.created_updated_time_utc = 1000
        self.ret_eg.last_updated_time_utc = 1000

        twin_wrapper = InitialTwin._create_from_internal(self.eg.initial_twin)
        self.eg.initial_twin = twin_wrapper

    @mock.patch.object(GeneratedProvisioningServiceClient, 'create_or_update_enrollment_group')
    def test_create_or_update_eg(self, mock_create):
        mock_create.return_value = self.ret_eg
        ret = self.psc.create_or_update(self.eg)
        self.assertIs(ret, self.ret_eg)
        self.assertIsInstance(ret, EnrollmentGroup)
        self.assertIsInstance(self.eg.initial_twin, InitialTwin) #wrapper still exists on input
        self.assertIsInstance(ret.initial_twin, InitialTwin) #wrapping layer added
        self.assertIsInstance(ret.initial_twin._internal, genmodels.InitialTwin)
        mock_create.assert_called_with(self.eg.enrollment_group_id, self.eg, self.eg.etag)

    @mock.patch.object(GeneratedProvisioningServiceClient, 'create_or_update_enrollment_group')
    def test_create_or_update_eg_protocol_exception(self, mock_create):
        mock_ex = create_PSED_Exception(FAIL, RESP_MSG)
        mock_create.side_effect = mock_ex
        with self.assertRaises(ProvisioningServiceError) as cm:
            ret = self.psc.create_or_update(self.eg)
        e = cm.exception
        self.assertEqual(self.psc.err_msg.format(FAIL, RESP_MSG), str(e))
        self.assertIs(e.cause, mock_ex)
        self.assertIsInstance(self.eg.initial_twin, InitialTwin) #wrapper still exists on input
        mock_create.assert_called_with(self.eg.enrollment_group_id, self.eg, self.eg.etag)

    @mock.patch.object(GeneratedProvisioningServiceClient, 'get_enrollment_group')
    def test_get_enrollment_group(self, mock_get):
        mock_get.return_value = self.ret_eg
        ret = self.psc.get_enrollment_group(self.eg.enrollment_group_id)
        self.assertIs(ret, self.ret_eg)
        self.assertIsInstance(ret, EnrollmentGroup)
        self.assertIsInstance(ret.initial_twin, InitialTwin) #wrapping layer added
        self.assertIsInstance(ret.initial_twin._internal, genmodels.InitialTwin)
        mock_get.assert_called_with(self.eg.enrollment_group_id)

    @mock.patch.object(GeneratedProvisioningServiceClient, 'get_enrollment_group')
    def test_get_enrollment_group_protocol_exception(self, mock_get):
        mock_ex = create_PSED_Exception(FAIL, RESP_MSG)
        mock_get.side_effect = mock_ex
        with self.assertRaises(ProvisioningServiceError) as cm:
            ret = self.psc.get_enrollment_group(self.eg.enrollment_group_id)
        e = cm.exception
        self.assertEqual(self.psc.err_msg.format(FAIL, RESP_MSG), str(e))
        self.assertIs(e.cause, mock_ex)
        mock_get.assert_called_with(self.eg.enrollment_group_id)

    @mock.patch.object(GeneratedProvisioningServiceClient, 'get_enrollment_group_attestation_mechanism')
    def test_get_enrollment_group_attestation_mechanism(self, mock_get):
        mock_get.return_value = self.am
        ret = self.psc.get_enrollment_group_attestation_mechanism(self.eg.enrollment_group_id)
        self.assertIs(ret, self.am)
        self.assertIsInstance(ret, AttestationMechanism)
        mock_get.assert_called_with(self.eg.enrollment_group_id)

    @mock.patch.object(GeneratedProvisioningServiceClient, 'get_enrollment_group_attestation_mechanism')
    def test_get_enrollment_group_attestation_mechanism_protocol_exception(self, mock_get):
        mock_ex = create_PSED_Exception(FAIL, RESP_MSG)
        mock_get.side_effect = mock_ex
        with self.assertRaises(ProvisioningServiceError) as cm:
            ret = self.psc.get_enrollment_group_attestation_mechanism(self.eg.enrollment_group_id)
        e = cm.exception
        self.assertEqual(self.psc.err_msg.format(FAIL, RESP_MSG), str(e))
        self.assertIs(e.cause, mock_ex)
        mock_get.assert_called_with(self.eg.enrollment_group_id)

    @mock.patch.object(GeneratedProvisioningServiceClient, 'delete_enrollment_group')
    def test_delete_enrollment_group_by_param_w_etag(self, mock_delete):
        ret = self.psc.delete_enrollment_group_by_param(self.eg.enrollment_group_id, self.eg.etag)
        self.assertIsNone(ret)
        mock_delete.assert_called_with(self.eg.enrollment_group_id, self.eg.etag)

    @mock.patch.object(GeneratedProvisioningServiceClient, 'delete_enrollment_group')
    def test_delete_enrollment_group_by_param_no_etag(self, mock_delete):
        ret = self.psc.delete_enrollment_group_by_param(self.eg.enrollment_group_id)
        self.assertIsNone(ret)
        mock_delete.assert_called_with(self.eg.enrollment_group_id, None)

    @mock.patch.object(GeneratedProvisioningServiceClient, 'delete_enrollment_group')
    def test_delete_enrollment_group_by_param_protocol_exception(self, mock_delete):
        mock_ex = create_PSED_Exception(FAIL, RESP_MSG)
        mock_delete.side_effect = mock_ex
        with self.assertRaises(ProvisioningServiceError) as cm:
            ret = self.psc.delete_enrollment_group_by_param(self.eg.enrollment_group_id, self.eg.etag)
        e = cm.exception
        self.assertEqual(self.psc.err_msg.format(FAIL, RESP_MSG), str(e))
        self.assertIs(e.cause, mock_ex)
        mock_delete.assert_called_with(self.eg.enrollment_group_id, self.eg.etag)

    @mock.patch.object(ProvisioningServiceClient, 'delete_enrollment_group_by_param')
    def test_delete_enrollment_group(self, mock_psc_delete):
        self.psc.delete(self.eg)
        mock_psc_delete.assert_called_with(self.eg.enrollment_group_id, self.eg.etag)


class TestProvisioningServiceClientWithRegistrationState(TestValidProvisioningServiceClient):

    def setUp(self):
        self.drs = DeviceRegistrationState()
        self.drs.registration_id = "reg-id"
        self.drs.status = "assigned"
        self.drs.etag = "etag"

        self.ret_drs = copy.deepcopy(self.drs)
        self.ret_drs.created_updated_time_utc = 1000
        self.ret_drs.last_updated_time_utc = 1000

    @mock.patch.object(GeneratedProvisioningServiceClient, 'get_device_registration_state')
    def test_get_registration_state(self, mock_get):
        mock_get.return_value = self.ret_drs
        ret = self.psc.get_registration_state(self.drs.registration_id)
        self.assertIs(ret, self.ret_drs)
        self.assertIsInstance(ret, DeviceRegistrationState)
        mock_get.assert_called_with(self.drs.registration_id)

    @mock.patch.object(GeneratedProvisioningServiceClient, 'get_device_registration_state')
    def test_get_registration_state_protocol_exception(self, mock_get):
        mock_ex = create_PSED_Exception(FAIL, RESP_MSG)
        mock_get.side_effect = mock_ex
        with self.assertRaises(ProvisioningServiceError) as cm:
            ret = self.psc.get_registration_state(self.drs.registration_id)
        e = cm.exception
        self.assertEqual(str(e), self.psc.err_msg.format(FAIL, RESP_MSG))
        self.assertIs(e.cause, mock_ex)
        mock_get.assert_called_with(self.drs.registration_id)

    @mock.patch.object(GeneratedProvisioningServiceClient, 'delete_device_registration_state')
    def test_delete_registration_state_by_param_w_etag(self, mock_delete):
        ret = self.psc.delete_registration_state_by_param(self.drs.registration_id, self.drs.etag)
        self.assertIsNone(ret)
        mock_delete.assert_called_with(self.drs.registration_id, self.drs.etag)

    @mock.patch.object(GeneratedProvisioningServiceClient, 'delete_device_registration_state')
    def test_delete_registration_state_by_param_no_etag(self, mock_delete):
        ret = self.psc.delete_registration_state_by_param(self.drs.registration_id)
        self.assertIsNone(ret)
        mock_delete.assert_called_with(self.drs.registration_id, None)

    @mock.patch.object(GeneratedProvisioningServiceClient, 'delete_device_registration_state')
    def test_delete_registration_state_by_param_protocol_exception(self, mock_delete):
        mock_ex = create_PSED_Exception(FAIL, RESP_MSG)
        mock_delete.side_effect = mock_ex
        with self.assertRaises(ProvisioningServiceError) as cm:
            ret = self.psc.delete_registration_state_by_param(self.drs.registration_id, self.drs.etag)
        e = cm.exception
        self.assertEqual(str(e), self.psc.err_msg.format(FAIL, RESP_MSG))
        self.assertIs(e.cause, mock_ex)
        mock_delete.assert_called_with(self.drs.registration_id, self.drs.etag)

    @mock.patch.object(ProvisioningServiceClient, 'delete_registration_state_by_param')
    def test_delete_registration_state(self, mock_psc_delete):
        self.psc.delete(self.drs)
        mock_psc_delete.assert_called_with(self.drs.registration_id, self.drs.etag)


class TestProvisioningServiceClientBulkOperation(TestValidProvisioningServiceClient):

    def setUp(self):
        enrollments = []
        for i in range(5):
            att = AttestationMechanism.create_with_tpm("test-ek")
            tags_tc = TwinCollection(additional_properties=TAGS)
            desired_properties_tc = TwinCollection(additional_properties=DESIRED_PROPERTIES)
            properties = InitialTwinProperties(desired=desired_properties_tc)
            twin = genmodels.InitialTwin(tags=tags_tc, properties=properties)
            twin_wrapper = InitialTwin._create_from_internal(twin)
            enrollments.append(IndividualEnrollment.create("reg-id" + str(i), att, initial_twin=twin_wrapper))
        self.bulkop = BulkEnrollmentOperation("create", enrollments)

        self.bulkop_resp = BulkEnrollmentOperationResult(is_successful=True)

    @mock.patch.object(GeneratedProvisioningServiceClient, 'run_bulk_enrollment_operation')
    def test_run_bulk_operation_op_success(self, mock_bulk_op):
        mock_bulk_op.return_value = self.bulkop_resp
        ret = self.psc.run_bulk_operation(self.bulkop)
        self.assertEqual(ret, self.bulkop_resp)
        self.assertIsInstance(ret, BulkEnrollmentOperationResult)
        for enrollment in self.bulkop.enrollments:
            self.assertIsInstance(enrollment.initial_twin, InitialTwin) #wrapper still on input
        mock_bulk_op.assert_called_with(self.bulkop)

    @mock.patch.object(GeneratedProvisioningServiceClient, 'run_bulk_enrollment_operation')
    def test_run_bulk_operation_op_fail(self, mock_bulk_op):
        self.bulkop_resp.is_successful = False
        mock_bulk_op.return_value = self.bulkop_resp
        ret = self.psc.run_bulk_operation(self.bulkop)
        self.assertEqual(ret, self.bulkop_resp)
        self.assertIsInstance(ret, BulkEnrollmentOperationResult)
        for enrollment in self.bulkop.enrollments:
            self.assertIsInstance(enrollment.initial_twin, InitialTwin) #wrapper still on input
        mock_bulk_op.assert_called_with(self.bulkop)

    @mock.patch.object(GeneratedProvisioningServiceClient, 'run_bulk_enrollment_operation')
    def test_run_bulk_operation_protocol_exception(self, mock_bulk_op):
        mock_ex = create_PSED_Exception(FAIL, RESP_MSG)
        mock_bulk_op.side_effect = mock_ex
        with self.assertRaises(ProvisioningServiceError) as cm:
            ret = self.psc.run_bulk_operation(self.bulkop)
        e = cm.exception
        self.assertEqual(str(e), self.psc.err_msg.format(FAIL, RESP_MSG))
        self.assertIs(e.cause, mock_ex)
        for enrollment in self.bulkop.enrollments:
            self.assertIsInstance(enrollment.initial_twin, InitialTwin) #wrapper still on input
        mock_bulk_op.assert_called_with(self.bulkop)


class TestProvisioningServiceClientOtherOperations(TestValidProvisioningServiceClient):

    @mock.patch('provisioningserviceclient.client.Query', autospec=True)
    def test_create_individual_enrollment_query_default_page(self, mock_query):

        qs = QuerySpecification("*")
        ret = self.psc.create_individual_enrollment_query(qs)
        mock_query.assert_called_with(qs, self.psc._runtime_client.query_individual_enrollments, None)
        self.assertIs(ret, mock_query.return_value)

    @mock.patch('provisioningserviceclient.client.Query', autospec=True)
    def test_create_individual_enrollment_query_custom_page(self, mock_query):
        qs = QuerySpecification("*")
        page_size = 50
        ret = self.psc.create_individual_enrollment_query(qs, page_size)
        mock_query.assert_called_with(qs, self.psc._runtime_client.query_individual_enrollments, page_size)
        self.assertIs(ret, mock_query.return_value)

    @mock.patch('provisioningserviceclient.client.Query', autospec=True)
    def test_create_enrollment_group_query_default_page(self, mock_query):
        qs = QuerySpecification("*")
        ret = self.psc.create_enrollment_group_query(qs)
        mock_query.assert_called_with(qs, self.psc._runtime_client.query_enrollment_groups, None)
        self.assertIs(ret, mock_query.return_value)

    @mock.patch('provisioningserviceclient.client.Query', autospec=True)
    def test_create_enrollment_group_query_custom_page(self, mock_query):
        qs = QuerySpecification("*")
        page_size = 50
        ret = self.psc.create_enrollment_group_query(qs, page_size)
        mock_query.assert_called_with(qs, self.psc._runtime_client.query_enrollment_groups, page_size)
        self.assertIs(ret, mock_query.return_value)

    @mock.patch('provisioningserviceclient.client.Query', autospec=True)
    def test_create_registration_state_query_default_page(self, mock_query):
        id = REG_ID
        ret = self.psc.create_registration_state_query(id)
        mock_query.assert_called_with(id, self.psc._runtime_client.query_device_registration_states, None)
        self.assertIs(ret, mock_query.return_value)

    @mock.patch('provisioningserviceclient.client.Query', autospec=True)
    def test_create_registration_state_query_custom_page(self, mock_query):
        id = REG_ID
        page_size = 50
        ret = self.psc.create_registration_state_query(id, page_size)
        mock_query.assert_called_with(id, self.psc._runtime_client.query_device_registration_states, page_size)
        self.assertIs(ret, mock_query.return_value)


class TestProvisioningServiceCleintWithBadInputs(TestValidProvisioningServiceClient):

    def test_create_or_update_wrong_obj_fail(self):
        with self.assertRaises(TypeError):
            self.psc.create_or_update(object())

    def test_delete_wrong_obj_fail(self):
        with self.assertRaises(TypeError):
            self.psc.delete(object())
        

if __name__ == '__main__':
    unittest.main()
