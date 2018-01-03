# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

from serviceclient.models import *
import unittest

tpm_label = "tpm"
x509_label = "x509"
client_label = "client"
signing_label = "signing"
ca_label = "ca"
test_ek = "test-ek"
test_srk = "test-srk"
test_cert1 = "test-cert1"
test_cert2 = "test-cert2"


class TestAttestationMechanismBuilder(unittest.TestCase):

    def assert_valid_tpm_attestation(self, att):
        self.assertIsInstance(att, AttestationMechanism)
        self.assertIsInstance(att.tpm, TpmAttestation)
        self.assertIsNone(att.x509)
        self.assertEqual(att.type, tpm_label)

    def assert_valid_x509_attestation(self, att, typ):
        self.assertIsInstance(att, AttestationMechanism)
        self.assertIsInstance(att.x509, X509Attestation)
        self.assertIsNone(att.tpm)
        self.assertEqual(att.type, x509_label)
        if typ == client_label:
            self.assertIsInstance(att.x509.client_certificates, X509Certificates)
            self.assertIsNone(att.x509.signing_certificates)
            self.assertIsNone(att.x509.ca_references)
            self.assert_valid_x509_certificates(att.x509.client_certificates)
        elif typ == signing_label:
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

    def test_create_tpm_attestation_no_srk(self):
        att = AttestationMechanismBuilder.create_tpm_attestation(test_ek)
        self.assert_valid_tpm_attestation(att)
        self.assertEqual(att.tpm.endorsement_key, test_ek)
        self.assertIsNone(att.tpm.storage_root_key)

    def test_create_tpm_attestation_w_srk(self):
        att = AttestationMechanismBuilder.create_tpm_attestation(test_ek, test_srk)
        self.assert_valid_tpm_attestation(att)
        self.assertEqual(att.tpm.endorsement_key, test_ek)
        self.assertEqual(att.tpm.storage_root_key, test_srk)

    def test_create_x509_attestation_client_certs_one_cert(self):
        att = AttestationMechanismBuilder.create_x509_attestation_client_certs(test_cert1)
        self.assert_valid_x509_attestation(att, client_label)
        self.assertEqual(att.x509.client_certificates.primary.certificate, test_cert1)
        self.assertIsNone(att.x509.client_certificates.primary.info)
        self.assertIsNone(att.x509.client_certificates.secondary)

    def test_create_x509_attestation_client_certs_both_certs(self):
        att = AttestationMechanismBuilder.create_x509_attestation_client_certs(test_cert1, test_cert2)
        self.assert_valid_x509_attestation(att, client_label)
        self.assertEqual(att.x509.client_certificates.primary.certificate, test_cert1)
        self.assertIsNone(att.x509.client_certificates.primary.info)
        self.assertEqual(att.x509.client_certificates.secondary.certificate, test_cert2)
        self.assertIsNone(att.x509.client_certificates.secondary.info)

    def test_create_x509_attestation_signing_certs_one_cert(self):
        att = AttestationMechanismBuilder.create_x509_attestation_signing_certs(test_cert1)
        self.assert_valid_x509_attestation(att, signing_label)
        self.assertEqual(att.x509.signing_certificates.primary.certificate, test_cert1)
        self.assertIsNone(att.x509.signing_certificates.primary.info)
        self.assertIsNone(att.x509.signing_certificates.secondary)

    def test_create_x509_attestation_signing_certs_both_certs(self):
        att = AttestationMechanismBuilder.create_x509_attestation_signing_certs(test_cert1, test_cert2)
        self.assert_valid_x509_attestation(att, signing_label)
        self.assertEqual(att.x509.signing_certificates.primary.certificate, test_cert1)
        self.assertIsNone(att.x509.signing_certificates.primary.info)
        self.assertEqual(att.x509.signing_certificates.secondary.certificate, test_cert2)
        self.assertIsNone(att.x509.signing_certificates.secondary.info)

    def test_create_x509_attestation_ca_refs_one_ref(self):
        att = AttestationMechanismBuilder.create_x509_attestation_ca_refs(test_cert1)
        self.assert_valid_x509_attestation(att, ca_label)
        self.assertEqual(att.x509.ca_references.primary, test_cert1)
        self.assertIsNone(att.x509.ca_references.secondary)

    def test_create_x509_attestation_ca_refs_both_refs(self):
        att = AttestationMechanismBuilder.create_x509_attestation_ca_refs(test_cert1, test_cert2)
        self.assert_valid_x509_attestation(att, ca_label)
        self.assertEqual(att.x509.ca_references.primary, test_cert1)
        self.assertEqual(att.x509.ca_references.secondary, test_cert2)


if __name__ == '__main__':
    unittest.main()
