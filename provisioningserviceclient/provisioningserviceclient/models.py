# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

import serviceswagger.models as genmodels


def _wrap_internal_model(model):
    """
    Wrap an internal provisioning service model

    :param model: Provisining service model to be wrapped
    :type model: :class:`IndividualEnrollment<serviceswagger.models.IndividualEnrollment>`
     or :class:`EnrollmentGroup<serviceswagger.models.EnrollmentGroup>`
     or :class:`DeviceRegistrationState<serviceswagger.models.DeviceRegistrationState>`
    :returns: Wrapped model of corresponding class
    :rtype: :class:`IndividualEnrollment<provisioningserviceclient.models.IndividualEnrollment>`
     or :class:`EnrollmentGroup<provisioningserviceclient.models.EnrollmentGroup>`
     or :class:`DeviceRegistrationState<provisioningserviceclient.models.DeviceRegistrationState>`
    :raises: TypeError if model of invalid type
    """
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
    """
    Individual Enrollment model. To instantiate please use the "create" class method

    :param internal_model: Internal model of an Individual Enrollment
    :type internal_model: :class:`IndividualEnrollment<serviceswagger.models.IndividualEnrollment>`
    :ivar registration_id: Registration ID.
    :ivar device_id: Desired IoT Hub device ID
    :ivar registration_state: Current registration state
    :ivar attestation: Attestation method used by the device.
    :ivar iot_hub_host_name: The IoT Hub host name.
    :ivar initial_twin: Initial device twin.
    :ivar etag: The entity tag associated with the resource.
    :ivar provisioning_status: The provisioning status.
    :ivar created_date_time_utc: The DateTime this resource was created.
    :ivar last_updated_date_time_utc: The DateTime this resource was last updated.
    """

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
    def create(cls, registration_id, attestation, device_id=None, iot_hub_host_name=None,\
        initial_twin=None, provisioning_status=None):
        """
        Create a new Individual Enrollment instance

        :param str registration_id: Registration ID
        :param attestation: Attestation Mechanism used by the device
        :type attestation: :class:`AttestationMechanism
         <provisioningserviceclient.models.AttestationMechanism>`
        :param str device_id: Desired IoT Hub device ID (optional)
        :param str iot_hub_host_name: The IoT Hub host name (optional)
        :param initial_twin: Initial device twin (optional)
        :type initial_twin: :class:`InitialTwin<provisioningserviceclient.models.InitialTwin>`
        :param str provisioning_status: The provisioning status. Possible values are 'enabled',
         'disabled' (optional)
        :returns: New instance of :class:`IndividualEnrollment
         <provisioningserviceclient.models.IndividualEnrollment>`
        :rtype: :class:`IndividualEnrollment<provisioningserviceclient.models.IndividualEnrollment>`
        """
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


class EnrollmentGroup(object):
    """
    Enrollment Group model. To instantiate please use the "create" class method

    :param internal_model: Internal model of an Enrollment Group
    :type internal_model: :class:`EnrollmentGroup<serviceswagger.models.EnrollmentGroup>`
    :ivar enrollment_group_id: Enrollment Group ID.
    :ivar attestation: Attestation method used by the device.
    :ivar iot_hub_host_name: The Iot Hub host name.
    :ivar initial_twin: Initial device twin.
    :ivar etag: The entity tag associated with the resource.
    :ivar provisioning_status: The provisioning status.
    :ivar created_date_time_utc: The DateTime this resource was created.
    :ivar last_updated_date_time_utc: The DateTime this resource was last
     updated.
    """
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
        """
        Create a new Enrollment Group instance

        :param str enrollment_group_id: Enrollment Group ID
        :param attestation: Attestation Mechanism used by the device
        :type attestation: :class:`AttestationMechanism
         <provisioningserviceclient.models.AttestationMechanism>`
        :param str iot_hub_host_name: The IoT Hub host name (optional)
        :param initial_twin: Initial device twin (optional)
        :type initial_twin: :class:`InitialTwin<provisioningserviceclient.models.InitialTwin>`
        :param str provisioning_status: The provisioning status. Possible values are 'enabled',
         'disabled' (optional)
        :returns: New instance of :class:`EnrollmentGroup
         <provisioningserviceclient.models.EnrollmentGroup>`
        :rtype: :class:`EnrollentGroup<provisioningserviceclient.models.EnrollmentGroup>`
        """
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


class DeviceRegistrationState(object):
    """
    Device Registration State model. Do not instantiate on your own

    :param internal_model: Internal model of a Device Registration State
    :type internal_model: :class:`DeviceRegistrationState
     <serviceswagger.models.DeviceRegistrationState>`
    :ivar registration_id: Registration ID.
    :ivar created_date_time_utc: Registration create date time (in UTC).
    :ivar assigned_hub: Assigned Azure IoT Hub.
    :ivar device_id: Device ID.
    :ivar status: Enrollment status.
    :ivar error_code: Error code.
    :ivar error_message: Error message.
    :ivar last_updated_date_time_utc: Last updated date time (in UTC).
    :ivar etag: The entity tag associated with the resource.
    """
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
    """
    Attestation Mechanism model. Please instantiate using one of the 'create_with...' class methods

    :param internal_model: Internal model of an Attestation Mechanism
    :type internal_model: :class:`AttestationMechanism<swaggerservice.models.AttestationMechanism>`
    :ivar attestation_type: Possible values include: 'none', 'tpm', 'x509'
    """

    def __init__(self, internal_model):
        self._internal = internal_model

    @classmethod
    def create_with_tpm(cls, endorsement_key, storage_root_key=None):
        """
        Create an Attestation Mechanism using a TPM

        :param str endorsement_key: TPM endorsement key
        :param str storage_root_key: TPM storage root key (optional)
        :returns: New instance of :class:`AttestationMechnaism
         <provisioningserviceclient.models.AttestationMechanism>`
        :rtype: :class:`AttestationMechnaism<provisioningserviceclient.models.AttestationMechanism>`
        """
        tpm = genmodels.TpmAttestation(endorsement_key, storage_root_key)
        att = genmodels.AttestationMechanism("tpm", tpm=tpm)
        return cls(att)

    @classmethod
    def create_with_x509_client_certs(cls, cert1, cert2=None):
        """
        Create an AttestationMechanism using X509 client certificates

        :param str cert1: Primary client certificate
        :param str cert2: Secondary client certificate (optional)
        :returns: New instance of :class:`AttestationMechnaism
         <provisioningserviceclient.models.AttestationMechanism>`
        :rtype: :class:`AttestationMechnaism<provisioningserviceclient.models.AttestationMechanism>`
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
        Create an AttestationMechanism using X509 signing certificates

        :param str cert1: Primary signing certificate
        :param str cert2: Secondary signing certificate (optional)
        :returns: New instance of :class:`AttestationMechnaism
         <provisioningserviceclient.models.AttestationMechanism>`
        :rtype: :class:`AttestationMechnaism<provisioningserviceclient.models.AttestationMechanism>`
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
        Create an AttestationMechanism using X509 CA References

        :param str ref1: Primary CA reference
        :param str ref2: Secondary CA reference (optional)
        :returns: New instance of :class:`AttestationMechnaism
         <provisioningserviceclient.models.AttestationMechanism>`
        :rtype: :class:`AttestationMechnaism<provisioningserviceclient.models.AttestationMechanism>`
        """
        ca_refs = genmodels.X509CAReferences(ref1, ref2)
        x509 = genmodels.X509Attestation(ca_references=ca_refs)
        att = genmodels.AttestationMechanism("x509", x509=x509)
        return cls(att)

    @property
    def attestation_type(self):
        return self._internal.type


class InitialTwin(object):
    """
    Initial Twin model. Please instantiate using the 'create' class method

    :param internal_model: Internal model of an InitialTwin
    :type internal_model: :class:`InitialTwin<swaggerservice.models.InitialTwin>`
    :ivar tags: Initial Twin tags
    :ivar desired_properties: Desired properties of the Initial Twin
    """

    def __init__(self, internal_model):
        self._internal = internal_model

    @classmethod
    def create(cls, tags=None, desired_properties=None):
        """
        Create an Initial Twin

        :param dict tags: The tags for the Initial Twin
        :param dict desired_properties: The desired properties for the Initial Twin
        :returns: New instance of :class:`InitialTwin<provisioningserviceclient.models.InitialTwin>`
        :rtype: :class:`InitialTwin<provisioningserviceclient.models.InitialTwin>`
        """
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
