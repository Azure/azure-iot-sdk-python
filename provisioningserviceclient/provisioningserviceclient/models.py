# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

import serviceswagger.models as genmodels


def _convert_to_wrapper(model):
    """
    Convert a generated model into a wrapper model of same type. Supported types:
    AttestationMechanism, IndividualEnrollment, EnrollmentGroup, DeviceRegistrationState,
    InitialTwinState

    Parameters:
    model - Model from the generated service
    """
    model_type = type(model)

    if model_type is genmodels.AttestationMechanism:
        model.__class__ = AttestationMechanism

    elif model_type is genmodels.IndividualEnrollment:
        model.__class__ = IndividualEnrollment
        _convert_to_wrapper(model.attestation)
        if model.initial_twin:
            _convert_to_wrapper(model.initial_twin)
        if model.registration_state:
            _convert_to_wrapper(model.registration_state)

    elif model_type is genmodels.EnrollmentGroup:
        model.__class__ = EnrollmentGroup
        _convert_to_wrapper(model.attestation)
        if model.initial_twin:
            _convert_to_wrapper(model.initial_twin)

    elif model_type is genmodels.DeviceRegistrationState:
        model.__class__ = DeviceRegistrationState

    elif model_type is genmodels.InitialTwin:
        model.__class__ = InitialTwin

    else:
        raise ValueError("unsupported type")


class IndividualEnrollment(genmodels.IndividualEnrollment):
    
    def __init__(self, registration_id, attestation, device_id=None, iot_hub_host_name=None, \
                initial_twin=None, provisioning_status=None):
        return super(self.__class__, self).__init__(registration_id, attestation, device_id=device_id, \
            iot_hub_host_name=iot_hub_host_name, initial_twin=initial_twin, \
            provisioning_status=provisioning_status)


class EnrollmentGroup(genmodels.EnrollmentGroup):
    
    def __init__(self, enrollment_group_id, attestation, iot_hub_host_name=None, initial_twin=None, \
        provisioning_status=None):
        return super(self.__clas__, self).__init__(enrollment_group_id, attestation, \
            iot_hub_host_name=iot_hub_host_name, initial_twin=initial_twin, \
            provisioning_status=provisioning_status)


class DeviceRegistrationState(genmodels.DeviceRegistrationState):
    pass


class AttestationMechanism(genmodels.AttestationMechanism):

    @classmethod
    def create_with_tpm(cls, ek, srk=None):
        """
        Create an AttestationMechanism for TPM

        Paramters:
        ek (str) - Endorsement Key
        srk (str)[optional] - Storage Root Key

        Returns:
        AttestationMechanism for TPM
        """
        tpm = genmodels.TpmAttestation(ek, srk)
        return cls("tpm", tpm=tpm)

    @classmethod
    def create_with_x509_client_certs(cls, cert1, cert2=None):
        """
        Create an AttestationMechanism for X509 using client certificates

        Parameters:
        cert1 (str) - Primary client certificate
        cert2 (str)[optional] - Secondary client certificate

        Returns:
        AttestationMechanism for X509
        """
        primary = genmodels.X509CertificateWithInfo(cert1)
        secondary = None
        if cert2:
            secondary = genmodels.X509CertificateWithInfo(cert2)
        certs = genmodels.X509Certificates(primary, secondary)
        x509 = genmodels.X509Attestation(client_certificates=certs)
        return cls("x509", x509=x509)

    @classmethod
    def create_with_x509_signing_certs(cls, cert1, cert2=None):
        """
        Create an AttestationMechanism for X509 using signing certificates

        Parameters:
        cert1 (str) - Primary signing certificate
        cert2 (str)[optional] - Secondary signing certificate

        Returns:
        AttestationMechanism for X509
        """
        primary = genmodels.X509CertificateWithInfo(cert1)
        secondary = None
        if cert2:
            secondary = genmodels.X509CertificateWithInfo(cert2)
        certs = genmodels.X509Certificates(primary, secondary)
        x509 = genmodels.X509Attestation(signing_certificates=certs)
        return cls("x509", x509=x509)

    @classmethod
    def create_with_x509_ca_refs(cls, ref1, ref2=None):
        """
        Create an AttestationMechanism for X509 using CA References

        Parameters:
        ref1 (str) - Primary CA reference
        ref2 (str)[optional] - Secondary CA reference

        Returns:
        AttestationMechanism for X509
        """
        ca_refs = genmodels.X509CAReferences(ref1, ref2)
        x509 = genmodels.X509Attestation(ca_references=ca_refs)
        return cls("x509", x509=x509)


class InitialTwin(genmodels.InitialTwin):

    def __init__(self, tags=None, desired_properties=None):

        tags_tc = genmodles.TwinCollection(tags)
        desired_properties_tc = genmodels.TwinCollection(desired_properties)
        properties = genmodels.InitialTwinProperties(desired_properties_tc)
        
        return super(self.__class__, self).__init__(tags_tc, properties)

    #@property
    #def tags(self):
    #    return self.tags.additional_properties

    #@tags.setter
    #def tags(self, value):
    #    self.tags.additional_properties = value

    #@property
    #def desired_properties(self):
    #    return self.properties.desired.additional_properties

    #@desired_properties.setter
    #def desired_properties(self, value):
    #    self.properties.desired.additional_properties = value


