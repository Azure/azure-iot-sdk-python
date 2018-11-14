# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

# from .protocol import models as genmodels
# from .protocol import DeviceRegistrationState, ReprovisionPolicy, CustomAllocationDefinition

from .protocol.models import *
from .protocol.models import InitialTwin as GeneratedInitialTwin

def _patch_models():
    _patch_individual_enrollment()
    _patch_enrollment_group()
    _patch_attestation_mechanism()
    _patch_device_capabilities()
    _patch_initial_twin()

def _patch_individual_enrollment():
    """Add convenience/back-compat methods to IndividualEnrollment
    """

    def create(cls, registration_id, attestation, device_id=None, iot_hub_host_name=None,
        initial_twin=None, provisioning_status="enabled", device_capabilities=None,
        reprovision_policy=None, allocation_policy=None, iot_hubs=None, 
        custom_allocation_definition=None):
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
         'disabled' (optional - default "enabled")
        :param device_capabilities: Device Capabilities (optional)
        :type device_capabilities: :class:`DeviceCapabilities
         <provisioningserviceclient.models.DeviceCapabilities>`
        :param reprovision_policy: The behavior when a device is re-provisioned to
        an IoT hub.
        :type reprovision_policy: `ReprovisionPolicy<provisioningserviceclient.models.ReprovisionPolicy>`
        :param str allocation_policy: The allocation policy of this resource.
        :param iot_hubs: The list of names of IoT hubs the device(s) in this
        resource can be allocated to. Must be a subset of tenant level list of IoT
        hubs.
        :type iot_hubs: list[str]
        :param custom_allocation_definition: Custom allocation definition.
        :type custom_allocation_definition: :class:`CustomAllocationDefinition
         <provisioningserviceclient.models.CustomAllocationDefinition>`
        :returns: New instance of :class:`IndividualEnrollment
         <provisioningserviceclient.models.IndividualEnrollment>`
        :rtype: :class:`IndividualEnrollment<provisioningserviceclient.models.IndividualEnrollment>`
        """
        return cls(registration_id=registration_id, attestation=attestation, device_id=device_id,
            iot_hub_host_name=iot_hub_host_name, initial_twin=initial_twin, provisioning_status=provisioning_status,
            capabilities=device_capabilities, reprovision_policy=reprovision_policy, allocation_policy=allocation_policy,
            iot_hubs=iot_hubs, custom_allocation_definition=custom_allocation_definition)
    
    setattr(IndividualEnrollment, "create", classmethod(create))

def _patch_enrollment_group():
    """Add conveneince/back-compat methods to EnrollmentGroup
    """

    def create(cls, enrollment_group_id, attestation, iot_hub_host_name=None, initial_twin=None,
        provisioning_status="enabled", reprovision_policy=None, allocation_policy=None, iot_hubs=None,
        custom_allocation_definition=None):
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
         'disabled' (optional - default enabled)
        :param reprovision_policy: The behavior when a device is re-provisioned to
         an IoT hub.
        :type reprovision_policy: `ReprovisionPolicy<provisioningserviceclient.models.ReprovisionPolicy>`
        :param str allocation_policy: The allocation policy of this resource.
        :param iot_hubs: The list of names of IoT hubs the device(s) in this
         resource can be allocated to. Must be a subset of tenant level list of IoT
         hubs.
        :type iot_hubs: list[str]
        :param custom_allocation_definition: Custom allocation definition.
        :type custom_allocation_definition: :class:`CustomAllocationDefinition
         <provisioningserviceclient.models.CustomAllocationDefinition>`
        :returns: New instance of :class:`EnrollmentGroup
         <provisioningserviceclient.models.EnrollmentGroup>`
        :rtype: :class:`EnrollentGroup<provisioningserviceclient.models.EnrollmentGroup>`
        """
        return cls(enrollment_group_id=enrollment_group_id, attestation=attestation, 
            iot_hub_host_name=iot_hub_host_name, initial_twin=initial_twin, 
            provisioning_status=provisioning_status, reprovision_policy=reprovision_policy,
            allocation_policy=allocation_policy, iot_hubs=iot_hubs, 
            custom_allocation_definition=custom_allocation_definition)

    setattr(EnrollmentGroup, "create", classmethod(create))


def _patch_device_capabilities():
    """Add convenience/back-compat methods to DeviceCapabilities
    """

    def create(cls, iot_edge=False):
        """
        Create a new Device Capabilities instance.

        :param bool iot_edge: IoT Edge capable
        :returns: New instance of :class:`DeviceCapabilities
         <provisioningserviceclient.models.DeviceCapabilities>`
        :rtype: :class:`DeviceCapabilities<provisioningserviceclient.models.DeviceCapabilities>`
        """
        return cls(iot_edge=iot_edge)

    setattr(DeviceCapabilities, "create", classmethod(create))


def _patch_attestation_mechanism():
    """Add convenience/back-compat methods to AttestationMechanism
    """

    def create_with_tpm(cls, endorsement_key, storage_root_key=None):
        """
        Create an Attestation Mechanism using a TPM

        :param str endorsement_key: TPM endorsement key
        :param str storage_root_key: TPM storage root key (optional)
        :returns: New instance of :class:`AttestationMechnaism
         <provisioningserviceclient.models.AttestationMechanism>`
        :rtype: :class:`AttestationMechnaism<provisioningserviceclient.models.AttestationMechanism>`
        """
        tpm = TpmAttestation(endorsement_key=endorsement_key, storage_root_key=storage_root_key)
        return cls(type="tpm", tpm=tpm)

    def create_with_x509_client_certs(cls, cert1, cert2=None):
        """
        Create an AttestationMechanism using X509 client certificates

        :param str cert1: Primary client certificate
        :param str cert2: Secondary client certificate (optional)
        :returns: New instance of :class:`AttestationMechnaism
         <provisioningserviceclient.models.AttestationMechanism>`
        :rtype: :class:`AttestationMechnaism<provisioningserviceclient.models.AttestationMechanism>`
        """
        primary = X509CertificateWithInfo(certificate=cert1)
        secondary = None
        if cert2:
            secondary = X509CertificateWithInfo(certificate=cert2)
        certs = X509Certificates(primary=primary, secondary=secondary)
        x509 = X509Attestation(client_certificates=certs)
        return cls(type="x509", x509=x509)

    def create_with_x509_signing_certs(cls, cert1, cert2=None):
        """
        Create an AttestationMechanism using X509 signing certificates

        :param str cert1: Primary signing certificate
        :param str cert2: Secondary signing certificate (optional)
        :returns: New instance of :class:`AttestationMechnaism
         <provisioningserviceclient.models.AttestationMechanism>`
        :rtype: :class:`AttestationMechnaism<provisioningserviceclient.models.AttestationMechanism>`
        """
        primary = X509CertificateWithInfo(certificate=cert1)
        secondary = None
        if cert2:
            secondary = X509CertificateWithInfo(certificate=cert2)
        certs = X509Certificates(primary=primary, secondary=secondary)
        x509 = X509Attestation(signing_certificates=certs)
        return cls(type="x509", x509=x509)

    def create_with_x509_ca_refs(cls, ref1, ref2=None):
        """
        Create an AttestationMechanism using X509 CA References

        :param str ref1: Primary CA reference
        :param str ref2: Secondary CA reference (optional)
        :returns: New instance of :class:`AttestationMechnaism
         <provisioningserviceclient.models.AttestationMechanism>`
        :rtype: :class:`AttestationMechnaism<provisioningserviceclient.models.AttestationMechanism>`
        """
        ca_refs = X509CAReferences(primary=ref1, secondary=ref2)
        x509 = X509Attestation(ca_references=ca_refs)
        return cls(type="x509", x509=x509)

    def attestation_type(self):
        return self.type

    setattr(AttestationMechanism, "create_with_tpm", classmethod(create_with_tpm))
    setattr(
        AttestationMechanism,
        "create_with_x509_client_certs",
        classmethod(create_with_x509_client_certs),
    )
    setattr(
        AttestationMechanism,
        "create_with_x509_signing_certs",
        classmethod(create_with_x509_signing_certs),
    )
    setattr(
        AttestationMechanism,
        "create_with_x509_ca_refs",
        classmethod(create_with_x509_ca_refs),
    )
    setattr(AttestationMechanism, "attestation_type", property(attestation_type))

class InitialTwin(object):
    """
    Initial Twin model.
    :param dict tags: The tags for the Initial Twin
    :param dict desired_properties: The desired properties for the Initial Twin
    :ivar tags: Initial Twin tags
    :ivar desired_properties: Desired properties of the Initial Twin
    """

    def __init__(self, tags=None, desired_properties=None):
        tags_tc = TwinCollection(additional_properties=tags)
        desired_properties_tc = TwinCollection(additional_properties=desired_properties)
        properties = InitialTwinProperties(desired=desired_properties_tc)
        twin = GeneratedInitialTwin(tags=tags_tc, properties=properties)
        self._create_internal(twin)

    @classmethod
    def create(cls, tags=None, desired_properties=None):
        """
        Create an Initial Twin

        :param dict tags: The tags for the Initial Twin
        :param dict desired_properties: The desired properties for the Initial Twin
        :returns: New instance of :class:`InitialTwin<provisioningserviceclient.models.InitialTwin>`
        :rtype: :class:`InitialTwin<provisioningserviceclient.models.InitialTwin>`
        """
        return cls(tags=tags, desired_properties=desired_properties)

    def _create_internal(self, internal_model):
        self._internal = internal_model
        self._internal._wrapper = self

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

    def _unwrap(self):
        return self._internal

def _patch_initial_twin():
    """Add convenience/back-compat methods for InitialTwin
    """

    def _wrap(self):
        """Keep a pointer to a wrapper class
        """
        if hasattr(self, "_wrapper"):   #Not EAFP, but this case is common enough to use LBYL
            wrapper = self._wrapper
        else:
            wrapper = InitialTwin._create_internal(self)
            self._wrapper = wrapper
        return wrapper

    setattr(GeneratedInitialTwin, "_wrap", _wrap)


# def _patch_initial_twin():
#     """Add convenience/back-compat methods for InitialTwin
#     """

#     def create(cls, tags=None, desired_properties=None):
#         """
#         Create an Initial Twin

#         :param dict tags: The tags for the Initial Twin
#         :param dict desired_properties: The desired properties for the Initial Twin
#         :returns: New instance of :class:`InitialTwin<provisioningserviceclient.models.InitialTwin>`
#         :rtype: :class:`InitialTwin<provisioningserviceclient.models.InitialTwin>`
#         """
#         tags_tc = TwinCollection(additional_properties=tags)
#         desired_properties_tc = TwinCollection(additional_properties=desired_properties)
#         properties = InitialTwinProperties(desired=desired_properties_tc)
#         return cls(tags=tags, properties=properties)

#     def tags_get(self):
#         return self.tags.additional_properties

#     def tags_set(self, value):
#         setattr(self, "tags")
#         self.tags.additional_properties = value

#     def desired_properties_get(self):
#         return self.properties.desired.additional_properties

#     def desired_properties_set(self, value):
#         self.properties.desired.additional_properties = value

#     setattr(InitialTwin, "create", classmethod(create))
#     setattr(InitialTwin, "tags", property(tags_get, tags_set))
#     setattr(InitialTwin, "desired_properties", property(desired_properties_get, desired_properties_set))
