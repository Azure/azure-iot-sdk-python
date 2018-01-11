# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

import unittest

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


class TestAttestationMechanism(unittest.TestCase):

    def assert_valid_tpm_attestation(self, att):
        self.assertIsInstance(att, AttestationMechanism)
        self.assertIsInstance(att.tpm, genmodels.TpmAttestation)
        self.assertIsNone(att.x509)
        self.assertEqual(att.type, TPM_LABEL)

    def assert_valid_x509_attestation(self, att, typ):
        self.assertIsInstance(att, AttestationMechanism)
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

    def test_create_with_tpm_no_srk(self):
        att = AttestationMechanism.create_with_tpm(TEST_EK)
        self.assert_valid_tpm_attestation(att)
        self.assertEqual(att.tpm.endorsement_key, TEST_EK)
        self.assertIsNone(att.tpm.storage_root_key)

    def test_create_with_tpm_w_srk(self):
        att = AttestationMechanism.create_with_tpm(TEST_EK, TEST_SRK)
        self.assert_valid_tpm_attestation(att)
        self.assertEqual(att.tpm.endorsement_key, TEST_EK)
        self.assertEqual(att.tpm.storage_root_key, TEST_SRK)

    def test_create_with_x509_client_certs_one_cert(self):
        att = AttestationMechanism.create_with_x509_client_certs(TEST_CERT1)
        self.assert_valid_x509_attestation(att, CLIENT_LABEL)
        self.assertEqual(att.x509.client_certificates.primary.certificate, TEST_CERT1)
        self.assertIsNone(att.x509.client_certificates.primary.info)
        self.assertIsNone(att.x509.client_certificates.secondary)

    def test_create_with_x509_client_certs_both_certs(self):
        att = AttestationMechanism.create_with_x509_client_certs(TEST_CERT1, TEST_CERT2)
        self.assert_valid_x509_attestation(att, CLIENT_LABEL)
        self.assertEqual(att.x509.client_certificates.primary.certificate, TEST_CERT1)
        self.assertIsNone(att.x509.client_certificates.primary.info)
        self.assertEqual(att.x509.client_certificates.secondary.certificate, TEST_CERT2)
        self.assertIsNone(att.x509.client_certificates.secondary.info)

    def test_create_with_x509_signing_certs_one_cert(self):
        att = AttestationMechanism.create_with_x509_signing_certs(TEST_CERT1)
        self.assert_valid_x509_attestation(att, SIGNING_LABEL)
        self.assertEqual(att.x509.signing_certificates.primary.certificate, TEST_CERT1)
        self.assertIsNone(att.x509.signing_certificates.primary.info)
        self.assertIsNone(att.x509.signing_certificates.secondary)

    def test_create_with_x509_signing_certs_both_certs(self):
        att = AttestationMechanism.create_with_x509_signing_certs(TEST_CERT1, TEST_CERT2)
        self.assert_valid_x509_attestation(att, SIGNING_LABEL)
        self.assertEqual(att.x509.signing_certificates.primary.certificate, TEST_CERT1)
        self.assertIsNone(att.x509.signing_certificates.primary.info)
        self.assertEqual(att.x509.signing_certificates.secondary.certificate, TEST_CERT2)
        self.assertIsNone(att.x509.signing_certificates.secondary.info)

    def test_create_with_x509_ca_refs_one_ref(self):
        att = AttestationMechanism.create_with_x509_ca_refs(TEST_CERT1)
        self.assert_valid_x509_attestation(att, CA_LABEL)
        self.assertEqual(att.x509.ca_references.primary, TEST_CERT1)
        self.assertIsNone(att.x509.ca_references.secondary)

    def test_create_with_x509_ca_refs_both_refs(self):
        att = AttestationMechanism.create_with_x509_ca_refs(TEST_CERT1, TEST_CERT2)
        self.assert_valid_x509_attestation(att, CA_LABEL)
        self.assertEqual(att.x509.ca_references.primary, TEST_CERT1)
        self.assertEqual(att.x509.ca_references.secondary, TEST_CERT2)


if __name__ == '__main__':
    unittest.main()
