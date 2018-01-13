# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

import serviceswagger.models as genmodels


def _wrap_internal_model(model):
    if isinstance(model, genmodels.IndividualEnrollment):
        wrapped = IndividualEnrollment(model)
    elif isinstance(model, genmodels.EnrollmentGroup):
        wrapped = EnrollmentGroup(model)
    elif isinstance(model, genmodels.DeviceRegistrationState):
        wrapped = DeviceRegistrationState(model)
    else:
        raise TypeError("Can't wrap this model")
    return wrapped

class IndividualEnrollment(object):

    def __init__(self, internal_model):
        self._internal = internal_model
        self._att_wrapper = AttestationMechanism(self._internal.attestation)

        if self._internal.registration_state is not None:
            self._drs_wrapper = DeviceRegistrationState(self._internal.registration_state)
        else:
            self._drs_wrapper = None

        if self._internal.initial_twin is not None:
            self._twin_wrapper = InitialTwin(self._internal.initial_twin)
        else:
            self._twin_wrapper = None

    @classmethod
    def create(cls, registration_id, attestation, device_id=None, iot_hub_host_name=None, \
                initial_twin=None, provisioning_status=None):
        att_internal = attestation._internal

        if initial_twin is not None:
            twin_internal = initial_twin._internal
        else:
            twin_internal = None

        internal = genmodels.IndividualEnrollment(registration_id, att_internal, \
            device_id=device_id, iot_hub_host_name=iot_hub_host_name, initial_twin=twin_internal, \
            provisioning_status=provisioning_status)

        new = cls(internal)
        new._att_wrapper = attestation
        new._twin_wrapper = initial_twin
        return new

    @property
    def registration_id(self):
        return self._internal.registration_id

    @registration_id.setter
    def registration_id(self, value):
        self._internal.registration_id = value

    @property
    def device_id(self):
        return self._internal.device_id

    @device_id.setter
    def device_id(self, value):
        self._internal.device_id = value

    @property
    def registration_state(self):
        return self._drs_wrapper

    @property
    def attestation(self):
        return self._att_wrapper

    @attestation.setter
    def attestation(self, value):
        self._internal.attestation = value._internal
        self._att_wrapper = value

    @property
    def iot_hub_host_name(self):
        return self._internal.iot_hub_host_name

    @iot_hub_host_name.setter
    def iot_hub_host_name(self, value):
        self._internal.iot_hub_host_name = value

    @property
    def initial_twin(self):
        return self._twin_wrapper

    @initial_twin.setter
    def initial_twin(self, value):
        self._internal.initial_twin = value._internal
        self._twin_wrapper = value

    @property
    def etag(self):
        return self._internal.etag

    @etag.setter
    def etag(self, value):
        self._internal.etag = value

    @property
    def provisioning_status(self):
        return self._internal.provisioning_status

    @provisioning_status.setter
    def provisioning_status(self, value):
        self._internal.provisioning_status = value

    @property
    def created_date_time_utc(self):
        return self._internal.created_date_time_utc

    @property
    def last_updated_date_time_utc(self):
        return self._internal.last_updated_date_time_utc


class EnrollmentGroup(genmodels.EnrollmentGroup):

    def __init__(self, internal_model):
        self._internal = internal_model
        self._att_wrapper = AttestationMechanism(self._internal.attestation)

        if self._internal.initial_twin is not None:
            self._twin_wrapper = InitialTwin(self._internal.initial_twin)
        else:
            self._twin_wrapper = None

    @classmethod
    def create(cls, enrollment_group_id, attestation, iot_hub_host_name=None, initial_twin=None, \
        provisioning_status=None):
        att_internal = attestation._internal

        if initial_twin is not None:
            twin_internal = initial_twin._internal
        else:
            twin_internal = None

        internal = genmodels.EnrollmentGroup(enrollment_group_id, att_internal, \
            iot_hub_host_name=iot_hub_host_name, initial_twin=twin_internal, \
            provisioning_status=provisioning_status)

        new = cls(internal)
        new._att_wrapper = attestation
        new._twin_wrapper = initial_twin
        return new

    @property
    def enrollment_group_id(self):
        return self._internal.enrollment_group_id

    @enrollment_group_id.setter
    def enrollment_group_id(self, value):
        self._internal.enrollment_group_id = value

    @property
    def attestation(self):
        return self._att_wrapper

    @attestation.setter
    def attestation(self, value):
        self._internal.attestation = value._internal
        self._att_wrapper = value

    @property
    def iot_hub_host_name(self):
        return self._internal.iot_hub_host_name

    @iot_hub_host_name.setter
    def iot_hub_host_name(self, value):
        self._internal.iot_hub_host_name = value

    @property
    def initial_twin(self):
        return self._twin_wrapper

    @initial_twin.setter
    def initial_twin(self, value):
        self._internal.initial_twin = value._internal
        self._twin_wrapper = value

    @property
    def etag(self):
        return self._internal.etag

    @etag.setter
    def etag(self, value):
        self._internal.etag = value

    @property
    def provisioning_status(self):
        return self._internal.provisioning_status

    @provisioning_status.setter
    def provisioning_status(self, value):
        self._internal.provisioning_status = value

    @property
    def created_date_time_utc(self):
        return self._internal.created_date_time_utc

    @property
    def last_updated_date_time_utc(self):
        return self._internal.last_updated_date_time_utc


class DeviceRegistrationState(genmodels.DeviceRegistrationState):
    
    def __init__(self, internal_model):
        self._internal = internal_model

    @property
    def registration_id(self):
        return self._internal.registration_id

    @property
    def created_date_time_utc(self):
        return self._internal.created_date_time_utc

    @property
    def assigned_hub(self):
        return self._internal.assigned_hub

    @property
    def device_id(self):
        return self._internal.device_id

    @property
    def status(self):
        return self._internal.status

    @property
    def error_code(self):
        return self._internal.error_code

    @property
    def error_message(self):
        return self._internal.error_message

    @property
    def last_updated_date_time_utc(self):
        return self._internal.last_updated_date_time_utc

    @property
    def etag(self):
        return self._internal.etag


class AttestationMechanism(object):

    def __init__(self, internal_model):
        self._internal = internal_model

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
        att = genmodels.AttestationMechanism("tpm", tpm=tpm)
        return cls(att)

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
        att = genmodels.AttestationMechanism("x509", x509=x509)
        return cls(att)

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
        att = genmodels.AttestationMechanism("x509", x509=x509)
        return cls(att)

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
        att = genmodels.AttestationMechanism("x509", x509=x509)
        return cls(att)

    @property
    def attestation_type(self):
        return self._internal.type


class InitialTwin(object):

    def __init__(self, internal_model):
        self._internal = internal_model

    @classmethod
    def create(cls, tags=None, desired_properties=None):
        tags_tc = genmodels.TwinCollection(tags)
        desired_properties_tc = genmodels.TwinCollection(desired_properties)
        properties = genmodels.InitialTwinProperties(desired_properties_tc)
        twin = genmodels.InitialTwin(tags_tc, properties)
        return cls(twin)

    @property
    def tags(self):
        return self._internal.tags.additional_properties

    @tags.setter
    def tags(self, value):
        self._internal.tags.additional_properties = value

    @property
    def desired_properties(self):
        return self._internal.properties.desired.additional_properties

    @desired_properties.setter
    def desired_properties(self, value):
        self._internal.properties.desired.additional_properties = value
