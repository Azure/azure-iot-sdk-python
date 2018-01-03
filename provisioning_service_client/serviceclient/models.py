# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

#from service.models import AttestationMechanism
#from service.models import TpmAttestation
#from service.models import X509Attestation, X509CAReferences, \
#    X509CertificateInfo, X509CertificateWithInfo, X509Certificates

from service.models import *


class AttestationMechanismBuilder(object):

    @classmethod
    def create_tpm_attestation(self, ek, srk=None):
        """
        Create an AttestationMechanism for TPM

        Paramters:
        ek (str) - Endorsement Key
        srk (str)[optional] - Storage Root Key

        Returns:
        AttestationMechanism for TPM
        """
        tpm = TpmAttestation(ek, srk)
        return AttestationMechanism("tpm", tpm=tpm)

    @classmethod
    def create_x509_attestation_client_certs(self, cert1, cert2=None):
        """
        Create an AttestationMechanism for X509 using client certificates

        Parameters:
        cert1 (str) - Primary client certificate
        cert2 (str)[optional] - Secondary client certificate

        Returns:
        AttestationMechanism for X509
        """
        primary = X509CertificateWithInfo(cert1)
        secondary = None
        if cert2:
            secondary = X509CertificateWithInfo(cert2)
        certs = X509Certificates(primary, secondary)
        x509 = X509Attestation(client_certificates=certs)
        return AttestationMechanism("x509", x509=x509)

    @classmethod
    def create_x509_attestation_signing_certs(self, cert1, cert2=None):
        """
        Create an AttestationMechanism for X509 using signing certificates

        Parameters:
        cert1 (str) - Primary signing certificate
        cert2 (str)[optional] - Secondary signing certificate

        Returns:
        AttestationMechanism for X509
        """
        primary = X509CertificateWithInfo(cert1)
        secondary = None
        if cert2:
            secondary = X509CertificateWithInfo(cert2)
        certs = X509Certificates(primary, secondary)
        x509 = X509Attestation(signing_certificates=certs)
        return AttestationMechanism("x509", x509=x509)

    @classmethod
    def create_x509_attestation_ca_refs(self, ref1, ref2=None):
        """
        Create an AttestationMechanism for X509 using CA References

        Parameters:
        ref1 (str) - Primary CA reference
        ref2 (str)[optional] - Secondary CA reference

        Returns:
        AttestationMechanism for X509
        """
        ca_refs = X509CAReferences(ref1, ref2)
        x509 = X509Attestation(ca_references=ca_refs)
        return AttestationMechanism("x509", x509=x509)
