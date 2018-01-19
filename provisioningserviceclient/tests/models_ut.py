# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

import unittest

from six import add_move, MovedModule
add_move(MovedModule('mock', 'mock', 'unittest.mock'))
from six.moves import mock

from provisioningserviceclient.models import AttestationMechanism, IndividualEnrollment, \
    EnrollmentGroup, DeviceRegistrationState, InitialTwin
import serviceswagger.models as genmodels


TPM_LABEL = "tpm"
X509_LABEL = "x509"
CLIENT_LABEL = "client"
SIGNING_LABEL = "signing"
CA_LABEL = "ca"
TEST_EK = "test-ek"
TEST_SRK = "test-srk"
TEST_CERT1 = "test-cert1"
TEST_CERT2 = "test-cert2"
TEST_REG_ID = "test-reg-id"
TEST_DEV_ID = "test-dev-id"
TEST_HOST_NAME = "test-host-name"
TEST_ETAG = "test-etag"
TEST_TIME = "test-time"
TEST_TIME2 = "test-time2"
TEST_ERR_CODE = 9000
TEST_ERR_MSG = "test-error"
TEST_TAGS = {"tag_key" : "tag_val"}
TEST_PROPERTIES = {"property_key" : "property_val"}
NEWVAL = "newval"
NEWDICT = {"new":"value"}
REG_STATUS_ASSIGNED = "assigned"
PROV_STATUS_ENABLED = "enabled"


class TestIndividualEnrollmentCreation(unittest.TestCase):

    def test_ie_constructor_full_model(self):
        tpm = genmodels.TpmAttestation(TEST_EK)
        att = genmodels.AttestationMechanism(TPM_LABEL, tpm=tpm)
        drs = genmodels.DeviceRegistrationState(TEST_REG_ID, REG_STATUS_ASSIGNED)
        twin = genmodels.InitialTwin()
        ie = genmodels.IndividualEnrollment(TEST_REG_ID, att, TEST_DEV_ID, drs, TEST_HOST_NAME,
                                            twin, TEST_ETAG, REG_STATUS_ASSIGNED, TEST_TIME, TEST_TIME2)
        ret = IndividualEnrollment(ie)
        self.assertIsInstance(ret, IndividualEnrollment)
        self.assertIs(ret._internal, ie)
        self.assertIsInstance(ret._att_wrapper, AttestationMechanism)
        self.assertIs(ret._att_wrapper._internal, att)
        self.assertIsInstance(ret._drs_wrapper, DeviceRegistrationState)
        self.assertIs(ret._drs_wrapper._internal, drs)
        self.assertIsInstance(ret._twin_wrapper, InitialTwin)
        self.assertIs(ret._twin_wrapper._internal, twin)

    def test_ie_constructor_min_model(self):
        tpm = genmodels.TpmAttestation(TEST_EK)
        att = genmodels.AttestationMechanism(TPM_LABEL, tpm=tpm)
        ie = genmodels.IndividualEnrollment(TEST_REG_ID, att)
        ret = IndividualEnrollment(ie)
        self.assertIsInstance(ret, IndividualEnrollment)
        self.assertIs(ret._internal, ie)
        self.assertIsInstance(ret._att_wrapper, AttestationMechanism)
        self.assertIs(ret._att_wrapper._internal, att)
        self.assertIsNone(ret._drs_wrapper)
        self.assertIsNone(ret._twin_wrapper)

    def test_ie_create_full_model(self):
        att = AttestationMechanism.create_with_tpm(TEST_EK)
        ts = InitialTwin.create()
        ret = IndividualEnrollment.create(TEST_REG_ID, att, TEST_DEV_ID, TEST_HOST_NAME, ts, \
            PROV_STATUS_ENABLED)
        internal = ret._internal
        self.assertIsInstance(ret, IndividualEnrollment)
        self.assertEqual(internal.registration_id, TEST_REG_ID)
        self.assertEqual(internal.device_id, TEST_DEV_ID)
        self.assertEqual(internal.iot_hub_host_name, TEST_HOST_NAME)
        self.assertEqual(internal.provisioning_status, PROV_STATUS_ENABLED)
        self.assertEqual(internal.attestation, att._internal)
        self.assertIs(ret._att_wrapper, att)
        self.assertEqual(internal.initial_twin, ts._internal)
        self.assertIs(ret._twin_wrapper, ts)
        self.assertIsNone(internal.registration_state)
        self.assertIsNone(ret._drs_wrapper)
        self.assertIsNone(internal.etag)
        self.assertIsNone(internal.created_date_time_utc)
        self.assertIsNone(internal.last_updated_date_time_utc)

    def test_ie_create_min_model(self):
        att = AttestationMechanism.create_with_tpm(TEST_EK)
        ret = IndividualEnrollment.create(TEST_REG_ID, att)
        internal = ret._internal
        self.assertIsInstance(ret, IndividualEnrollment)
        self.assertEqual(internal.registration_id, TEST_REG_ID)
        self.assertIsNone(internal.device_id)
        self.assertIsNone(internal.iot_hub_host_name)
        self.assertIsNone(internal.provisioning_status)
        self.assertEqual(internal.attestation, att._internal)
        self.assertIs(ret._att_wrapper, att)
        self.assertIsNone(internal.initial_twin)
        self.assertIsNone(ret._twin_wrapper)
        self.assertIsNone(internal.registration_state)
        self.assertIsNone(ret._drs_wrapper)
        self.assertIsNone(internal.etag)
        self.assertIsNone(internal.created_date_time_utc)
        self.assertIsNone(internal.last_updated_date_time_utc)


class TestIndividualEnrollmentAttributes(unittest.TestCase):

    def setUp(self):
        tpm = genmodels.TpmAttestation(TEST_EK)
        self.gen_att = genmodels.AttestationMechanism(TPM_LABEL, tpm=tpm)
        self.gen_drs = genmodels.DeviceRegistrationState(TEST_REG_ID, REG_STATUS_ASSIGNED)
        self.gen_twin = genmodels.InitialTwin()
        gen_ie = genmodels.IndividualEnrollment(TEST_REG_ID, self.gen_att, TEST_DEV_ID, self.gen_drs, \
            TEST_HOST_NAME, self.gen_twin, TEST_ETAG, PROV_STATUS_ENABLED, TEST_TIME, TEST_TIME2)
        self.ie = IndividualEnrollment(gen_ie)

    def test_ie_get_reg_id(self):
        res = self.ie.registration_id
        self.assertIs(res, TEST_REG_ID)

    def test_ie_set_reg_id(self):
        self.ie.registration_id = NEWVAL
        self.assertIs(self.ie._internal.registration_id, NEWVAL)

    def test_ie_get_device_id(self):
        res = self.ie.device_id
        self.assertIs(res, TEST_DEV_ID)

    def test_ie_set_device_id(self):
        self.ie.device_id = NEWVAL
        self.assertIs(self.ie._internal.device_id, NEWVAL)

    def test_ie_get_registration_state(self):
        res = self.ie.registration_state
        self.assertIsInstance(res, DeviceRegistrationState)
        self.assertIs(res._internal, self.gen_drs)

    def test_ie_set_registration_state(self):
        with self.assertRaises(AttributeError):
            self.ie.registration_state = NEWVAL
        self.assertIs(self.ie._internal.registration_state, self.gen_drs)

    def test_ie_get_attestation(self):
        res = self.ie.attestation
        self.assertIsInstance(res, AttestationMechanism)
        self.assertIs(res._internal, self.gen_att)

    def test_ie_set_attestation(self):
        att = AttestationMechanism.create_with_tpm(TEST_EK)
        self.ie.attestation = att
        self.assertIs(self.ie._internal.attestation, att._internal)
        self.assertIs(self.ie._att_wrapper, att)

    def test_ie_get_iot_hub_host_name(self):
        res = self.ie.iot_hub_host_name
        self.assertIs(res, TEST_HOST_NAME)

    def test_ie_set_iot_hub_host_name(self):
        self.ie.iot_hub_host_name = NEWVAL
        self.assertIs(self.ie._internal.iot_hub_host_name, NEWVAL)

    def test_ie_get_initial_twin(self):
        res = self.ie.initial_twin
        self.assertIsInstance(res, InitialTwin)
        self.assertIs(res._internal, self.gen_twin)

    def test_ie_set_initial_twin(self):
        ts = InitialTwin.create()
        self.ie.initial_twin = ts
        self.assertIs(self.ie._internal.initial_twin, ts._internal)
        self.assertIs(self.ie._twin_wrapper, ts)

    def test_ie_get_etag(self):
        res = self.ie.etag
        self.assertIs(res, TEST_ETAG)

    def test_ie_set_etag(self):
        self.ie.etag = NEWVAL
        self.assertIs(self.ie._internal.etag, NEWVAL)

    def test_ie_get_provisioning_status(self):
        res = self.ie.provisioning_status
        self.assertIs(res, PROV_STATUS_ENABLED)

    def test_ie_set_provisioning_status(self):
        self.ie.provisioning_status = NEWVAL
        self.assertIs(self.ie._internal.provisioning_status, NEWVAL)

    def test_ie_get_created_date_time_utc(self):
        res = self.ie.created_date_time_utc
        self.assertIs(res, TEST_TIME)

    def test_ie_set_created_date_time_utc(self):
        with self.assertRaises(AttributeError):
            self.ie.created_date_time_utc = NEWVAL
        self.assertIs(self.ie._internal.created_date_time_utc, TEST_TIME)

    def test_ie_get_last_updated_date_time_utc(self):
        res = self.ie.last_updated_date_time_utc
        self.assertIs(res, TEST_TIME2)

    def test_ie_set_last_updated_date_time_utc(self):
        with self.assertRaises(AttributeError):
            self.ie.last_updated_date_time_utc = NEWVAL
        self.assertIs(self.ie._internal.last_updated_date_time_utc, TEST_TIME2)


class TestEnrollmentGroupCreation(unittest.TestCase):

    def test_eg_constructor_full_model(self):
        x509 = genmodels.X509Attestation()
        att = genmodels.AttestationMechanism(X509_LABEL, x509=x509)
        twin = genmodels.InitialTwin()
        eg = genmodels.EnrollmentGroup(TEST_REG_ID, att, TEST_HOST_NAME, twin, TEST_ETAG, \
            PROV_STATUS_ENABLED, TEST_TIME, TEST_TIME2)
        ret = EnrollmentGroup(eg)
        self.assertIsInstance(ret, EnrollmentGroup)
        self.assertIs(ret._internal, eg)
        self.assertIsInstance(ret._att_wrapper, AttestationMechanism)
        self.assertIs(ret._att_wrapper._internal, att)
        self.assertIsInstance(ret._twin_wrapper, InitialTwin)
        self.assertIs(ret._twin_wrapper._internal, twin)

    def test_eg_constructor_min_model(self):
        x509 = genmodels.X509Attestation()
        att = genmodels.AttestationMechanism(X509_LABEL, x509=x509)
        eg = genmodels.EnrollmentGroup(TEST_REG_ID, att)
        ret = EnrollmentGroup(eg)
        self.assertIsInstance(ret, EnrollmentGroup)
        self.assertIs(ret._internal, eg)
        self.assertIsInstance(ret._att_wrapper, AttestationMechanism)
        self.assertIs(ret._att_wrapper._internal, att)
        self.assertIsNone(ret._twin_wrapper)

    def test_eg_create_full_model(self):
        att = AttestationMechanism.create_with_x509_ca_refs(TEST_CERT1)
        ts = InitialTwin.create()
        ret = EnrollmentGroup.create(TEST_REG_ID, att, TEST_HOST_NAME, ts, PROV_STATUS_ENABLED)
        internal = ret._internal
        self.assertIsInstance(ret, EnrollmentGroup)
        self.assertEqual(internal.enrollment_group_id, TEST_REG_ID)
        self.assertEqual(internal.iot_hub_host_name, TEST_HOST_NAME)
        self.assertEqual(internal.provisioning_status, PROV_STATUS_ENABLED)
        self.assertEqual(internal.attestation, att._internal)
        self.assertIs(ret._att_wrapper, att)
        self.assertEqual(internal.initial_twin, ts._internal)
        self.assertIs(ret._twin_wrapper, ts)
        self.assertIsNone(internal.etag)
        self.assertIsNone(internal.created_date_time_utc)
        self.assertIsNone(internal.last_updated_date_time_utc)

    def test_eg_create_min_model(self):
        att = AttestationMechanism.create_with_x509_ca_refs(TEST_CERT1)
        ret = EnrollmentGroup.create(TEST_REG_ID, att)
        internal = ret._internal
        self.assertIsInstance(ret, EnrollmentGroup)
        self.assertEqual(internal.enrollment_group_id, TEST_REG_ID)
        self.assertIsNone(internal.iot_hub_host_name)
        self.assertIsNone(internal.provisioning_status)
        self.assertEqual(internal.attestation, att._internal)
        self.assertIs(ret._att_wrapper, att)
        self.assertIsNone(internal.initial_twin)
        self.assertIsNone(ret._twin_wrapper)
        self.assertIsNone(internal.etag)
        self.assertIsNone(internal.created_date_time_utc)
        self.assertIsNone(internal.last_updated_date_time_utc)


class TestEnrollmentGroupAttributes(unittest.TestCase):

    def setUp(self):
        x509 = genmodels.X509Attestation(TEST_CERT1)
        self.gen_att = genmodels.AttestationMechanism(X509_LABEL, x509=x509)
        self.gen_twin = genmodels.InitialTwin()
        gen_eg = genmodels.EnrollmentGroup(TEST_REG_ID, self.gen_att, TEST_HOST_NAME, \
            self.gen_twin, TEST_ETAG, PROV_STATUS_ENABLED, TEST_TIME, TEST_TIME2)
        self.eg = EnrollmentGroup(gen_eg)

    def test_eg_get_enrollment_group_id(self):
        res = self.eg.enrollment_group_id
        self.assertIs(res, TEST_REG_ID)

    def test_eg_set_enrollment_group_id(self):
        self.eg.enrollment_group_id = NEWVAL
        self.assertIs(self.eg._internal.enrollment_group_id, NEWVAL)

    def test_eg_get_attestation(self):
        res = self.eg.attestation
        self.assertIsInstance(res, AttestationMechanism)
        self.assertIs(res._internal, self.gen_att)

    def test_eg_set_attestation(self):
        att = AttestationMechanism.create_with_x509_ca_refs(TEST_CERT1)
        self.eg.attestation = att
        self.assertIs(self.eg._internal.attestation, att._internal)
        self.assertIs(self.eg._att_wrapper, att)

    def test_eg_get_iot_hub_host_name(self):
        res = self.eg.iot_hub_host_name
        self.assertIs(res, TEST_HOST_NAME)

    def test_eg_set_iot_hub_host_name(self):
        self.eg.iot_hub_host_name = NEWVAL
        self.assertIs(self.eg._internal.iot_hub_host_name, NEWVAL)

    def test_eg_get_initial_twin(self):
        res = self.eg.initial_twin
        self.assertIsInstance(res, InitialTwin)
        self.assertIs(res._internal, self.gen_twin)

    def test_eg_set_initial_twin(self):
        ts = InitialTwin.create()
        self.eg.initial_twin = ts
        self.assertIs(self.eg._internal.initial_twin, ts._internal)
        self.assertIs(self.eg._twin_wrapper, ts)

    def test_eg_get_etag(self):
        res = self.eg.etag
        self.assertIs(res, TEST_ETAG)

    def test_eg_set_etag(self):
        self.eg.etag = NEWVAL
        self.assertIs(self.eg._internal.etag, NEWVAL)

    def test_eg_get_provisioning_status(self):
        res = self.eg.provisioning_status
        self.assertIs(res, PROV_STATUS_ENABLED)

    def test_eg_set_provisioning_status(self):
        self.eg.provisioning_status = NEWVAL
        self.assertIs(self.eg._internal.provisioning_status, NEWVAL)

    def test_eg_get_created_date_time_utc(self):
        res = self.eg.created_date_time_utc
        self.assertIs(res, TEST_TIME)

    def test_eg_set_created_date_time_utc(self):
        with self.assertRaises(AttributeError):
            self.eg.created_date_time_utc = NEWVAL
        self.assertIs(self.eg._internal.created_date_time_utc, TEST_TIME)

    def test_eg_get_last_updated_date_time_utc(self):
        res = self.eg.last_updated_date_time_utc
        self.assertIs(res, TEST_TIME2)

    def test_eg_set_last_updated_date_time_utc(self):
        with self.assertRaises(AttributeError):
            self.eg.last_updated_date_time_utc = NEWVAL
        self.assertIs(self.eg._internal.last_updated_date_time_utc, TEST_TIME2)


class TestDeviceRegistrationStateCreation(unittest.TestCase):

    def test_drs_constructor(self):
        gen_drs = genmodels.DeviceRegistrationState(TEST_REG_ID, REG_STATUS_ASSIGNED, TEST_TIME, \
            TEST_HOST_NAME, TEST_DEV_ID, TEST_ERR_CODE, TEST_ERR_MSG, TEST_TIME2, TEST_ETAG)
        drs = DeviceRegistrationState(gen_drs)
        self.assertIsInstance(drs, DeviceRegistrationState)
        self.assertIs(drs._internal, gen_drs)


class TestDeviceRegistrationStateAttributes(unittest.TestCase):

    def setUp(self):
        gen_drs = genmodels.DeviceRegistrationState(TEST_REG_ID, REG_STATUS_ASSIGNED, TEST_TIME, \
            TEST_HOST_NAME, TEST_DEV_ID, TEST_ERR_CODE, TEST_ERR_MSG, TEST_TIME2, TEST_ETAG)
        self.drs = DeviceRegistrationState(gen_drs)

    def test_drs_get_registration_id(self):
        res = self.drs.registration_id
        self.assertIs(res, TEST_REG_ID)

    def test_drs_set_registration_id(self):
        with self.assertRaises(AttributeError):
            self.drs.registration_id = NEWVAL
        self.assertIs(self.drs._internal.registration_id, TEST_REG_ID)

    def test_drs_get_created_date_time_utc(self):
        res = self.drs.created_date_time_utc
        self.assertIs(res, TEST_TIME)

    def test_drs_set_created_date_time_utc(self):
        with self.assertRaises(AttributeError):
            self.drs.created_date_time_utc = NEWVAL
        self.assertIs(self.drs._internal.created_date_time_utc, TEST_TIME)

    def test_drs_get_assigned_hub(self):
        res = self.drs.assigned_hub
        self.assertIs(res, TEST_HOST_NAME)

    def test_drs_set_assigned_hub(self):
        with self.assertRaises(AttributeError):
            self.drs.assigned_hub = NEWVAL
        self.assertIs(self.drs._internal.assigned_hub, TEST_HOST_NAME)

    def test_drs_get_device_id(self):
        res = self.drs.device_id
        self.assertIs(res, TEST_DEV_ID)

    def test_drs_set_device_id(self):
        with self.assertRaises(AttributeError):
            self.drs.device_id = NEWVAL
        self.assertIs(self.drs._internal.device_id, TEST_DEV_ID)

    def test_drs_get_status(self):
        res = self.drs.status
        self.assertIs(res, REG_STATUS_ASSIGNED)

    def test_drs_set_status(self):
        with self.assertRaises(AttributeError):
            self.drs.status = NEWVAL
        self.assertIs(self.drs._internal.status, REG_STATUS_ASSIGNED)

    def test_drs_get_error_code(self):
        res = self.drs.error_code
        self.assertIs(res, TEST_ERR_CODE)

    def test_drs_set_error_code(self):
        with self.assertRaises(AttributeError):
            self.drs.error_code = NEWVAL
        self.assertIs(self.drs._internal.error_code, TEST_ERR_CODE)

    def test_drs_get_error_message(self):
        res = self.drs.error_message
        self.assertIs(res, TEST_ERR_MSG)

    def test_drs_set_error_message(self):
        with self.assertRaises(AttributeError):
            self.drs.error_message = NEWVAL
        self.assertIs(self.drs._internal.error_message, TEST_ERR_MSG)


class TestAttestationMechanismCreation(unittest.TestCase):

    def assert_valid_tpm_attestation(self, att):
        self.assertIsInstance(att, genmodels.AttestationMechanism)
        self.assertIsInstance(att.tpm, genmodels.TpmAttestation)
        self.assertIsNone(att.x509)
        self.assertEqual(att.type, TPM_LABEL)

    def assert_valid_x509_attestation(self, att, typ):
        self.assertIsInstance(att, genmodels.AttestationMechanism)
        self.assertIsInstance(att.x509, genmodels.X509Attestation)
        self.assertIsNone(att.tpm)
        self.assertEqual(att.type, X509_LABEL)
        if typ == CLIENT_LABEL:
            self.assertIsInstance(att.x509.client_certificates, genmodels.X509Certificates)
            self.assertIsNone(att.x509.signing_certificates)
            self.assertIsNone(att.x509.ca_references)
            self.assert_valid_x509_certificates(att.x509.client_certificates)
        elif typ == SIGNING_LABEL:
            self.assertIsInstance(att.x509.signing_certificates, genmodels.X509Certificates)
            self.assertIsNone(att.x509.client_certificates)
            self.assertIsNone(att.x509.ca_references)
            self.assert_valid_x509_certificates(att.x509.signing_certificates)
        else:
            self.assertIsInstance(att.x509.ca_references, genmodels.X509CAReferences)
            self.assertIsNone(att.x509.client_certificates)
            self.assertIsNone(att.x509.signing_certificates)

    def assert_valid_x509_certificates(self, certs):
        self.assertIsInstance(certs.primary, genmodels.X509CertificateWithInfo)
        if (certs.secondary):
            self.assertIsInstance(certs.secondary, genmodels.X509CertificateWithInfo)

    def test_am_create_with_constructor(self):
        tpm = genmodels.TpmAttestation(TEST_EK)
        att = genmodels.AttestationMechanism(TPM_LABEL, tpm=tpm)
        ret = AttestationMechanism(att)
        self.assertIsInstance(ret, AttestationMechanism)
        self.assertIs(ret._internal, att)

    def test_create_with_tpm_no_srk(self):
        att = AttestationMechanism.create_with_tpm(TEST_EK)
        self.assertIsInstance(att, AttestationMechanism)
        self.assert_valid_tpm_attestation(att._internal)
        self.assertEqual(att._internal.tpm.endorsement_key, TEST_EK)
        self.assertIsNone(att._internal.tpm.storage_root_key)

    def test_create_with_tpm_w_srk(self):
        att = AttestationMechanism.create_with_tpm(TEST_EK, TEST_SRK)
        self.assertIsInstance(att, AttestationMechanism)
        self.assert_valid_tpm_attestation(att._internal)
        self.assertEqual(att._internal.tpm.endorsement_key, TEST_EK)
        self.assertEqual(att._internal.tpm.storage_root_key, TEST_SRK)

    def test_create_with_x509_client_certs_one_cert(self):
        att = AttestationMechanism.create_with_x509_client_certs(TEST_CERT1)
        self.assertIsInstance(att, AttestationMechanism)
        self.assert_valid_x509_attestation(att._internal, CLIENT_LABEL)
        self.assertEqual(att._internal.x509.client_certificates.primary.certificate, TEST_CERT1)
        self.assertIsNone(att._internal.x509.client_certificates.primary.info)
        self.assertIsNone(att._internal.x509.client_certificates.secondary)

    def test_create_with_x509_client_certs_both_certs(self):
        att = AttestationMechanism.create_with_x509_client_certs(TEST_CERT1, TEST_CERT2)
        self.assertIsInstance(att, AttestationMechanism)
        self.assert_valid_x509_attestation(att._internal, CLIENT_LABEL)
        self.assertEqual(att._internal.x509.client_certificates.primary.certificate, TEST_CERT1)
        self.assertIsNone(att._internal.x509.client_certificates.primary.info)
        self.assertEqual(att._internal.x509.client_certificates.secondary.certificate, TEST_CERT2)
        self.assertIsNone(att._internal.x509.client_certificates.secondary.info)

    def test_create_with_x509_signing_certs_one_cert(self):
        att = AttestationMechanism.create_with_x509_signing_certs(TEST_CERT1)
        self.assertIsInstance(att, AttestationMechanism)
        self.assert_valid_x509_attestation(att._internal, SIGNING_LABEL)
        self.assertEqual(att._internal.x509.signing_certificates.primary.certificate, TEST_CERT1)
        self.assertIsNone(att._internal.x509.signing_certificates.primary.info)
        self.assertIsNone(att._internal.x509.signing_certificates.secondary)

    def test_create_with_x509_signing_certs_both_certs(self):
        att = AttestationMechanism.create_with_x509_signing_certs(TEST_CERT1, TEST_CERT2)
        self.assertIsInstance(att, AttestationMechanism)
        self.assert_valid_x509_attestation(att._internal, SIGNING_LABEL)
        self.assertEqual(att._internal.x509.signing_certificates.primary.certificate, TEST_CERT1)
        self.assertIsNone(att._internal.x509.signing_certificates.primary.info)
        self.assertEqual(att._internal.x509.signing_certificates.secondary.certificate, TEST_CERT2)
        self.assertIsNone(att._internal.x509.signing_certificates.secondary.info)

    def test_create_with_x509_ca_refs_one_ref(self):
        att = AttestationMechanism.create_with_x509_ca_refs(TEST_CERT1)
        self.assertIsInstance(att, AttestationMechanism)
        self.assert_valid_x509_attestation(att._internal, CA_LABEL)
        self.assertEqual(att._internal.x509.ca_references.primary, TEST_CERT1)
        self.assertIsNone(att._internal.x509.ca_references.secondary)

    def test_create_with_x509_ca_refs_both_refs(self):
        att = AttestationMechanism.create_with_x509_ca_refs(TEST_CERT1, TEST_CERT2)
        self.assertIsInstance(att, AttestationMechanism)
        self.assert_valid_x509_attestation(att._internal, CA_LABEL)
        self.assertEqual(att._internal.x509.ca_references.primary, TEST_CERT1)
        self.assertEqual(att._internal.x509.ca_references.secondary, TEST_CERT2)


class TestAttestationMechanismAttributes(unittest.TestCase):

    def setUp(self):
        gen_tpm = genmodels.TpmAttestation(TEST_EK)
        gen_att = genmodels.AttestationMechanism(TPM_LABEL, tpm=gen_tpm)
        self.att = AttestationMechanism(gen_att)

    def test_get_attestation_type(self):
        res = self.att.attestation_type
        self.assertIs(res, TPM_LABEL)

    def test_set_attestation_type(self):
        with self.assertRaises(AttributeError):
            self.att.attestation_type = NEWVAL
        self.assertIs(self.att._internal.type, TPM_LABEL)


class TestInitialTwinCreation(unittest.TestCase):

    def test_ts_constructor(self):
        tags_tc = genmodels.TwinCollection(TEST_TAGS)
        desired_properties_tc = genmodels.TwinCollection(TEST_PROPERTIES)
        properties = genmodels.InitialTwinProperties(desired_properties_tc)
        twin = genmodels.InitialTwin(tags_tc, properties)
        res = InitialTwin(twin)
        self.assertIsInstance(res, InitialTwin)
        self.assertIs(res._internal, twin)

    def test_ts_create_full(self):
        res = InitialTwin.create(TEST_TAGS, TEST_PROPERTIES)
        self.assertIs(res._internal.tags.additional_properties, TEST_TAGS)
        self.assertIs(res._internal.properties.desired.additional_properties, TEST_PROPERTIES)

    def test_ts_create_empty(self):
        res = InitialTwin.create()
        self.assertIsNone(res._internal.tags.additional_properties)
        self.assertIsNone(res._internal.properties.desired.additional_properties)


class TestInitialTwinAttributes(unittest.TestCase):

    def setUp(self):
        tags_tc = genmodels.TwinCollection(TEST_TAGS)
        desired_properties_tc = genmodels.TwinCollection(TEST_PROPERTIES)
        properties = genmodels.InitialTwinProperties(desired_properties_tc)
        gen_twin = genmodels.InitialTwin(tags_tc, properties)
        self.twin = InitialTwin(gen_twin)

    def test_ts_get_tags(self):
        res = self.twin.tags
        self.assertIs(res, TEST_TAGS)

    def test_ts_set_tags(self):
        self.twin.tags = NEWDICT
        self.assertIs(self.twin._internal.tags.additional_properties, NEWDICT)

    def test_ts_get_desired_properties(self):
        res = self.twin.desired_properties
        self.assertIs(res, TEST_PROPERTIES)

    def test_ts_set_desired_properties(self):
        self.twin.desired_properties = NEWDICT
        self.assertIs(self.twin._internal.properties.desired.additional_properties, NEWDICT)


if __name__ == '__main__':
    unittest.main()
