# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

import unittest
from six import add_move, MovedModule
add_move(MovedModule('mock', 'mock', 'unittest.mock'))
from six.moves import mock

import context
from provisioningserviceclient.models import *
from provisioningserviceclient.protocol.models import InitialTwin as GeneratedInitialTwin

DUMMY_REG_ID = "test-reg-id"
DUMMY_DEV_ID = "test-dev-id"
DUMMY_HOST_NAME = "test-host-name"
DUMMY_ETAG = "test-etag"
DUMMY_TIME = "test-time"
DUMMY_TIME2 = "test-time2"
DUMMY_IOT_HUBS = ["hub1", "hub2"]
DUMMY_ATTESTATION = "DUMMY ATTESTATION"
DUMMY_TWIN = "DUMMY TWIN"
DUMMY_ERR_CODE = 9000
DUMMY_ERR_MSG = "test-error"
DUMMY_EK = "test-ek"
DUMMY_SRK = "test-srk"
DUMMY_CERT1 = "test-cert1"
DUMMY_CERT2 = "test-cert2"
DUMMY_TAGS = {"tag_key" : "tag_val"}
DUMMY_PROPERTIES = {"property_key" : "property_val"}

DUMMY_DEVICE_CAPABILITIES = "DUMMY DEVICE_CAPABILITIES"
DUMMY_REPROVISION_POLICY = "DUMMY REPROVISION POLICY"
DUMMY_ALLOCATION_DEFINITION = "DUMMY ALLOCATION DEFINITION"
DUMMY_REGISTRATION_STATE = "DUMMY REGISTRATION STATE"
DUMMY_TPM_ATTESTATION = "DUMMY TPM ATTESTATION"
DUMMY_INTERNAL_TWIN = "DUMMY INTERNAL TWIN"

PROV_STATUS_ENABLED = "enabled"
PROV_STATUS_DISABLED = "disabled"
ALLOCATION_POLICY_HASHED = "hashed"
REG_STATUS_ASSIGNED = "assigned"
TPM_LABEL = "tpm"
X509_LABEL = "x509"
CLIENT_LABEL = "client"
SIGNING_LABEL = "signing"
CA_LABEL = "ca"

class TestIndividualEnrollment(unittest.TestCase):
    def test_create_min(self):
        ie = IndividualEnrollment.create(DUMMY_REG_ID, DUMMY_ATTESTATION)
        self.assertIs(ie.registration_id, DUMMY_REG_ID)
        self.assertIs(ie.attestation, DUMMY_ATTESTATION)
        self.assertIs(ie.provisioning_status, PROV_STATUS_ENABLED) #default
        self.assertIsNone(ie.device_id)
        self.assertIsNone(ie.iot_hub_host_name)
        self.assertIsNone(ie.initial_twin)
        self.assertIsNone(ie.capabilities)
        self.assertIsNone(ie.reprovision_policy)
        self.assertIsNone(ie.allocation_policy)
        self.assertIsNone(ie.iot_hubs)
        self.assertIsNone(ie.custom_allocation_definition)
        self.assertIsNone(ie.registration_state)
        self.assertIsNone(ie.etag)
        self.assertIsNone(ie.created_date_time_utc)
        self.assertIsNone(ie.last_updated_date_time_utc)

    def test_create_max(self):
        ie = IndividualEnrollment.create(DUMMY_REG_ID, DUMMY_ATTESTATION, DUMMY_DEV_ID,
            DUMMY_HOST_NAME, DUMMY_TWIN, PROV_STATUS_DISABLED, DUMMY_DEVICE_CAPABILITIES,
            DUMMY_REPROVISION_POLICY, ALLOCATION_POLICY_HASHED, DUMMY_IOT_HUBS, DUMMY_ALLOCATION_DEFINITION)
        self.assertIs(ie.registration_id, DUMMY_REG_ID)
        self.assertIs(ie.attestation, DUMMY_ATTESTATION)
        self.assertIs(ie.device_id, DUMMY_DEV_ID)
        self.assertIs(ie.iot_hub_host_name, DUMMY_HOST_NAME)
        self.assertIs(ie.initial_twin, DUMMY_TWIN)
        self.assertIs(ie.provisioning_status, PROV_STATUS_DISABLED)
        self.assertIs(ie.capabilities, DUMMY_DEVICE_CAPABILITIES)
        self.assertIs(ie.reprovision_policy, DUMMY_REPROVISION_POLICY)
        self.assertIs(ie.allocation_policy, ALLOCATION_POLICY_HASHED)
        self.assertIs(ie.iot_hubs, DUMMY_IOT_HUBS)
        self.assertIs(ie.custom_allocation_definition, DUMMY_ALLOCATION_DEFINITION)
        self.assertIsNone(ie.registration_state)
        self.assertIsNone(ie.etag)
        self.assertIsNone(ie.created_date_time_utc)
        self.assertIsNone(ie.last_updated_date_time_utc)

    def test_back_compat_attributes(self):
        """DO NOT MODIFY THIS TEST. EVER. IT TESTS BACKWARDS COMPATIBILITY.
        """
        #Populate all fields from older version
        ie = IndividualEnrollment.create(DUMMY_REG_ID, DUMMY_ATTESTATION, DUMMY_DEV_ID,
            DUMMY_HOST_NAME, DUMMY_TWIN, PROV_STATUS_DISABLED, DUMMY_DEVICE_CAPABILITIES)
        ie.registration_state = DUMMY_REGISTRATION_STATE
        ie.etag = DUMMY_ETAG
        ie.created_date_time_utc = DUMMY_TIME
        ie.last_updated_date_time_utc = DUMMY_TIME2

        #check back compat
        self.assertIs(ie.registration_id, DUMMY_REG_ID)
        self.assertIs(ie.attestation, DUMMY_ATTESTATION)
        self.assertIs(ie.device_id, DUMMY_DEV_ID)
        self.assertIs(ie.iot_hub_host_name, DUMMY_HOST_NAME)
        self.assertIs(ie.initial_twin, DUMMY_TWIN)
        self.assertIs(ie.provisioning_status, PROV_STATUS_DISABLED)
        self.assertIs(ie.capabilities, DUMMY_DEVICE_CAPABILITIES)
        self.assertIs(ie.registration_state, DUMMY_REGISTRATION_STATE)
        self.assertIs(ie.etag, DUMMY_ETAG)
        self.assertIs(ie.created_date_time_utc, DUMMY_TIME)
        self.assertIs(ie.last_updated_date_time_utc, DUMMY_TIME2)


class TestEnrollmentGroupCreation(unittest.TestCase):

    def test_create_min(self):
        eg = EnrollmentGroup.create(DUMMY_REG_ID, DUMMY_ATTESTATION)
        self.assertIs(eg.enrollment_group_id, DUMMY_REG_ID)
        self.assertIs(eg.attestation, DUMMY_ATTESTATION)
        self.assertIsNone(eg.iot_hub_host_name)
        self.assertIsNone(eg.initial_twin)
        self.assertIs(eg.provisioning_status, PROV_STATUS_ENABLED) #default
        self.assertIsNone(eg.reprovision_policy)
        self.assertIsNone(eg.allocation_policy)
        self.assertIsNone(eg.iot_hubs)
        self.assertIsNone(eg.custom_allocation_definition)
        self.assertIsNone(eg.etag)
        self.assertIsNone(eg.created_date_time_utc)
        self.assertIsNone(eg.last_updated_date_time_utc)

    def test_create_max(self):
        eg = EnrollmentGroup.create(DUMMY_REG_ID, DUMMY_ATTESTATION, DUMMY_HOST_NAME, DUMMY_TWIN,
            PROV_STATUS_DISABLED, DUMMY_REPROVISION_POLICY, ALLOCATION_POLICY_HASHED, DUMMY_IOT_HUBS,
            DUMMY_ALLOCATION_DEFINITION)
        self.assertIs(eg.enrollment_group_id, DUMMY_REG_ID)
        self.assertIs(eg.attestation, DUMMY_ATTESTATION)
        self.assertIs(eg.iot_hub_host_name, DUMMY_HOST_NAME)
        self.assertIs(eg.initial_twin, DUMMY_TWIN)
        self.assertIsNone(eg.etag)
        self.assertIs(eg.provisioning_status, PROV_STATUS_DISABLED)
        self.assertIs(eg.reprovision_policy, DUMMY_REPROVISION_POLICY)
        self.assertIsNone(eg.created_date_time_utc)
        self.assertIsNone(eg.last_updated_date_time_utc)
        self.assertIs(eg.allocation_policy, ALLOCATION_POLICY_HASHED)
        self.assertIs(eg.iot_hubs, DUMMY_IOT_HUBS)
        self.assertIs(eg.custom_allocation_definition, DUMMY_ALLOCATION_DEFINITION)

    def test_back_compat_attributes(self):
        """DO NOT MODIFY THIS TEST. EVER. IT TESTS BACKWARDS COMPATIBILITY.
        """
        #Populate all fields from older version
        eg = EnrollmentGroup.create(DUMMY_REG_ID, DUMMY_ATTESTATION, DUMMY_HOST_NAME, DUMMY_TWIN,
            PROV_STATUS_DISABLED)
        eg.etag = DUMMY_ETAG
        eg.created_date_time_utc = DUMMY_TIME
        eg.last_updated_date_time_utc = DUMMY_TIME2

        #check back compat
        self.assertIs(eg.enrollment_group_id, DUMMY_REG_ID)
        self.assertIs(eg.attestation, DUMMY_ATTESTATION)
        self.assertIs(eg.iot_hub_host_name, DUMMY_HOST_NAME)
        self.assertIs(eg.initial_twin, DUMMY_TWIN)
        self.assertIs(eg.provisioning_status, PROV_STATUS_DISABLED)
        self.assertIs(eg.etag, DUMMY_ETAG)
        self.assertIs(eg.created_date_time_utc, DUMMY_TIME)
        self.assertIs(eg.last_updated_date_time_utc, DUMMY_TIME2)


class TestDeviceCapabilities(unittest.TestCase):

    def test_create_min(self):
        cap = DeviceCapabilities.create()
        self.assertFalse(cap.iot_edge)

    def test_create_max(self):
        cap = DeviceCapabilities.create(True)
        self.assertTrue(cap.iot_edge)

    def test_back_compat_attributes(self):
        """DO NOT MODIFY THIS TEST. EVER. IT TESTS BACKWARDS COMPATIBILITY.
        """
        cap = DeviceCapabilities.create(True)
        self.assertTrue(cap.iot_edge)


class TestDeviceRegistrationState(unittest.TestCase):

    #No new tests required, because user only reads attributes from this object

    def test_back_compat_attributes(self):
        """DO NOT MODIFY THIS TEST. EVER. IT TESTS BACKWARDS COMPATIBILITY.
        """
        #Populate fields from older version ONLY
        drs = DeviceRegistrationState()
        drs.registration_id = DUMMY_REG_ID
        drs.created_date_time_utc = DUMMY_TIME
        drs.assigned_hub = DUMMY_HOST_NAME
        drs.device_id = DUMMY_DEV_ID
        drs.status = REG_STATUS_ASSIGNED
        drs.error_code = DUMMY_ERR_CODE
        drs.error_message = DUMMY_ERR_MSG
        drs.last_updated_date_time_utc = DUMMY_TIME2
        drs.etag = DUMMY_ETAG

        self.assertIs(drs.registration_id, DUMMY_REG_ID)
        self.assertIs(drs.created_date_time_utc, DUMMY_TIME)
        self.assertIs(drs.assigned_hub, DUMMY_HOST_NAME)
        self.assertIs(drs.device_id, DUMMY_DEV_ID)
        self.assertIs(drs.status, REG_STATUS_ASSIGNED)
        self.assertIs(drs.error_code, DUMMY_ERR_CODE)
        self.assertIs(drs.error_message, DUMMY_ERR_MSG)
        self.assertIs(drs.last_updated_date_time_utc, DUMMY_TIME2)
        self.assertIs(drs.etag, DUMMY_ETAG)


class TestAttestationMechanism(unittest.TestCase):

    def assert_valid_tpm_attestation(self, att):
        self.assertIsInstance(att, AttestationMechanism)
        self.assertIsInstance(att.tpm, TpmAttestation)
        self.assertIsNone(att.x509)
        self.assertEqual(att.type, TPM_LABEL)

    def assert_valid_x509_attestation(self, att, typ):
        self.assertIsInstance(att, AttestationMechanism)
        self.assertIsInstance(att.x509, X509Attestation)
        self.assertIsNone(att.tpm)
        self.assertEqual(att.type, X509_LABEL)
        if typ == CLIENT_LABEL:
            self.assertIsInstance(att.x509.client_certificates, X509Certificates)
            self.assertIsNone(att.x509.signing_certificates)
            self.assertIsNone(att.x509.ca_references)
            self.assert_valid_x509_certificates(att.x509.client_certificates)
        elif typ == SIGNING_LABEL:
            self.assertIsInstance(att.x509.signing_certificates, X509Certificates)
            self.assertIsNone(att.x509.client_certificates)
            self.assertIsNone(att.x509.ca_references)
            self.assert_valid_x509_certificates(att.x509.signing_certificates)
        else:
            self.assertIsInstance(att.x509.ca_references, X509CAReferences)
            self.assertIsNone(att.x509.client_certificates)
            self.assertIsNone(att.x509.signing_certificates)

    def assert_valid_x509_certificates(self, certs):
        self.assertIsInstance(certs.primary, X509CertificateWithInfo)
        if (certs.secondary):
            self.assertIsInstance(certs.secondary, X509CertificateWithInfo)

    def test_create_with_tpm_min(self):
        att = AttestationMechanism.create_with_tpm(DUMMY_EK)
        self.assert_valid_tpm_attestation(att)
        self.assertEqual(att.tpm.endorsement_key, DUMMY_EK)
        self.assertIsNone(att.tpm.storage_root_key)

    def test_create_with_tpm_max(self):
        att = AttestationMechanism.create_with_tpm(DUMMY_EK, DUMMY_SRK)
        self.assert_valid_tpm_attestation(att)
        self.assertEqual(att.tpm.endorsement_key, DUMMY_EK)
        self.assertEqual(att.tpm.storage_root_key, DUMMY_SRK)

    def test_create_with_x509_client_certs_one_cert(self):
        att = AttestationMechanism.create_with_x509_client_certs(DUMMY_CERT1)
        self.assert_valid_x509_attestation(att, CLIENT_LABEL)
        self.assertEqual(att.x509.client_certificates.primary.certificate, DUMMY_CERT1)
        self.assertIsNone(att.x509.client_certificates.primary.info)
        self.assertIsNone(att.x509.client_certificates.secondary)

    def test_create_with_x509_client_certs_both_certs(self):
        att = AttestationMechanism.create_with_x509_client_certs(DUMMY_CERT1, DUMMY_CERT2)
        self.assert_valid_x509_attestation(att, CLIENT_LABEL)
        self.assertEqual(att.x509.client_certificates.primary.certificate, DUMMY_CERT1)
        self.assertIsNone(att.x509.client_certificates.primary.info)
        self.assertEqual(att.x509.client_certificates.secondary.certificate, DUMMY_CERT2)
        self.assertIsNone(att.x509.client_certificates.secondary.info)

    def test_create_with_x509_signing_certs_one_cert(self):
        att = AttestationMechanism.create_with_x509_signing_certs(DUMMY_CERT1)
        self.assert_valid_x509_attestation(att, SIGNING_LABEL)
        self.assertEqual(att.x509.signing_certificates.primary.certificate, DUMMY_CERT1)
        self.assertIsNone(att.x509.signing_certificates.primary.info)
        self.assertIsNone(att.x509.signing_certificates.secondary)

    def test_create_with_x509_signing_certs_both_certs(self):
        att = AttestationMechanism.create_with_x509_signing_certs(DUMMY_CERT1, DUMMY_CERT2)
        self.assert_valid_x509_attestation(att, SIGNING_LABEL)
        self.assertEqual(att.x509.signing_certificates.primary.certificate, DUMMY_CERT1)
        self.assertIsNone(att.x509.signing_certificates.primary.info)
        self.assertEqual(att.x509.signing_certificates.secondary.certificate, DUMMY_CERT2)
        self.assertIsNone(att.x509.signing_certificates.secondary.info)

    def test_create_with_x509_ca_refs_one_ref(self):
        att = AttestationMechanism.create_with_x509_ca_refs(DUMMY_CERT1)
        self.assert_valid_x509_attestation(att, CA_LABEL)
        self.assertEqual(att.x509.ca_references.primary, DUMMY_CERT1)
        self.assertIsNone(att.x509.ca_references.secondary)

    def test_create_with_x509_ca_refs_both_refs(self):
        att = AttestationMechanism.create_with_x509_ca_refs(DUMMY_CERT1, DUMMY_CERT2)
        self.assert_valid_x509_attestation(att, CA_LABEL)
        self.assertEqual(att.x509.ca_references.primary, DUMMY_CERT1)
        self.assertEqual(att.x509.ca_references.secondary, DUMMY_CERT2)

    def test_back_compat_attributes(self):
        """DO NOT MODIFY THIS TEST. EVER. IT TESTS BACKWARDS COMPATIBILITY.
        """
        #Populate all fields from older version
        att = AttestationMechanism.create_with_tpm(DUMMY_EK, DUMMY_SRK)

        #Check back compat
        self.assertIs(att.attestation_type, TPM_LABEL)


class TestInitialTwin(unittest.TestCase):

    def test_init_full(self):
        twin = InitialTwin(DUMMY_TAGS, DUMMY_PROPERTIES)
        self.assertIs(twin._internal.tags.additional_properties, DUMMY_TAGS)
        self.assertIs(twin._internal.properties.desired.additional_properties, DUMMY_PROPERTIES)
        self.assertIs(twin._internal._wrapper, twin)

    def test_init_empty(self):
        twin = InitialTwin()
        self.assertIsNone(twin._internal.tags.additional_properties)
        self.assertIsNone(twin._internal.properties.desired.additional_properties)
        self.assertIs(twin._internal._wrapper, twin)

    def test_create_full(self):
        twin = InitialTwin.create(DUMMY_TAGS, DUMMY_PROPERTIES)
        self.assertIs(twin._internal.tags.additional_properties, DUMMY_TAGS)
        self.assertIs(twin._internal.properties.desired.additional_properties, DUMMY_PROPERTIES)
        self.assertIs(twin._internal._wrapper, twin)

    def test_create_empty(self):
        twin = InitialTwin.create()
        self.assertIsNone(twin._internal.tags.additional_properties)
        self.assertIsNone(twin._internal.properties.desired.additional_properties)
        self.assertIs(twin._internal._wrapper, twin)

    def test_create_from_internal(self):
        internal = GeneratedInitialTwin(tags=None, properties=None)
        twin = InitialTwin._create_from_internal(internal)
        self.assertIs(twin._internal, internal)
        self.assertIs(twin._internal._wrapper, twin)

    def test_unwrap(self):
        twin = InitialTwin.create(DUMMY_TAGS, DUMMY_PROPERTIES)
        res = twin._unwrap()
        self.assertIs(twin._internal, res)

    def test_wrap_wrapper_instantiated(self):
        twin = InitialTwin.create(DUMMY_TAGS, DUMMY_PROPERTIES)
        res = twin._internal._wrap()
        self.assertIs(res, twin)

    def test_wrap_wrapper_uninstantiated(self):
        twin = GeneratedInitialTwin(tags=None, properties=None)
        res = twin._wrap()
        self.assertIsInstance(res, InitialTwin)
        self.assertIs(res._internal, twin)

    def test_back_compat_attributes(self):
        """DO NOT MODIFY THIS TEST. EVER. IT TESTS BACKWARDS COMPATIBILITY.
        """
        #Populate all fields from older version
        twin = InitialTwin.create(DUMMY_TAGS, DUMMY_PROPERTIES)
        self.assertIs(twin.tags, DUMMY_TAGS)
        self.assertIs(twin.desired_properties, DUMMY_PROPERTIES)


if __name__ == '__main__':
    unittest.main()
