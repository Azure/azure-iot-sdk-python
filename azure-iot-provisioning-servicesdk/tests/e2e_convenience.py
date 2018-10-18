# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

from azure.iot.provisioning.servicesdk.models import (
    TpmAttestation,
    X509CertificateWithInfo,
    X509Attestation,
    X509CAReferences,
    AttestationMechanism,
    X509Certificates,
)


def _patch_attestation_mechanism():
    """Add convenience methods to Attestation Mechanism for ease of use
    """

    def create_with_tpm(cls, endorsement_key, storage_root_key=None):
        """Create an Attestation Mechanism using a TPM Attestation

        :param str endorsement_key: Endorsement Key
        :param str storage_root_key: Storage Root Key
        :return: AttestationMechanism using TPM Attestation
        :rtype: ~protocol.models.AttestationMechanism
        """
        tpm = TpmAttestation(endorsement_key=endorsement_key, storage_root_key=storage_root_key)
        return cls(type="tpm", tpm=tpm)

    def _create_x509_certificates(primary_cert, secondary_cert=None):
        """Creates X509Certificates model
        """
        primary = X509CertificateWithInfo(certificate=primary_cert)
        secondary = None
        if secondary_cert:
            secondary = X509CertificateWithInfo(certificate=secondary_cert)
        return X509Certificates(primary=primary, secondary=secondary)

    def create_with_x509_client_certificates(cls, primary, secondary=None):
        """Create an Attestation Mechanism using a X509 Attestation with Client Certificates.
        Only valid for IndividualEnrollment

        :param str primary: Primary certificate (Base 64 encoded)
        :param str secondary: Secondary certificate (Base64 encoded)
        :return: AttestationMechanism using X509 Attestation wtih Client Certificates
        :rtype: ~protocol.models.AttestationMechanism
        """
        certs = _create_x509_certificates(primary, secondary)
        x509 = X509Attestation(client_certificates=certs)
        return cls(type="x509", x509=x509)

    def create_with_x509_signing_certificates(cls, primary, secondary=None):
        """Create an Attestation Mechanism using a X509 Attestation with Signing Certificates.
        Only valid for EnrollmentGroup

        :param str primary: Primary certificate (Base 64 encoded)
        :param str secondary: Secondary certificate (Base64 encoded)
        :return: AttestationMechanism using X509 Attestation wtih Signing Certificates
        :rtype: ~protocol.models.AttestationMechanism
        """
        certs = _create_x509_certificates(primary, secondary)
        x509 = X509Attestation(signing_certificates=certs)
        return cls(type="x509", x509=x509)

    def create_with_x509_ca_references(cls, primary, secondary=None):
        """Create an Attestation Mechanism using a X509 Attestation with CA References

        :param str primary: Primary CA Reference
        :param str secondary: Secondary CA Reference
        :return: AttestationMechanism using X509 Attestation wtih CA References
        :rtype: ~protocol.models.AttestationMechanism
        """
        ca_refs = X509CAReferences(primary=primary, secondary=secondary)
        x509 = X509Attestation(ca_references=ca_refs)
        return cls(type="x509", x509=x509)

    setattr(AttestationMechanism, "create_with_tpm", classmethod(create_with_tpm))
    setattr(
        AttestationMechanism,
        "create_with_x509_client_certificates",
        classmethod(create_with_x509_client_certificates),
    )
    setattr(
        AttestationMechanism,
        "create_with_x509_signing_certificates",
        classmethod(create_with_x509_signing_certificates),
    )
    setattr(
        AttestationMechanism,
        "create_with_x509_ca_references",
        classmethod(create_with_x509_ca_references),
    )
