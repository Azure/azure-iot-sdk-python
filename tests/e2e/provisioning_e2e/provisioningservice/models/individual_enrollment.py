class IndividualEnrollment(object):
    """The device enrollment record.

    Variables are only populated by the server, and will be ignored when
    sending a request.

    All required parameters must be populated in order to send to Azure.

    :param capabilities: Capabilities of the device
    :type capabilities: ~protocol.models.DeviceCapabilities
    :param registration_id: Required. The registration ID is alphanumeric,
     lowercase, and may contain hyphens.
    :type registration_id: str
    :param device_id: Desired IoT Hub device ID (optional).
    :type device_id: str
    :ivar registration_state: Current registration status.
    :vartype registration_state: ~protocol.models.DeviceRegistrationState
    :param attestation: Required. Attestation method used by the device.
    :type attestation: ~protocol.models.AttestationMechanism
    :param iot_hub_host_name: The Iot Hub host name.
    :type iot_hub_host_name: str
    :param initial_twin: Initial device twin.
    :type initial_twin: ~protocol.models.InitialTwin
    :param etag: The entity tag associated with the resource.
    :type etag: str
    :param provisioning_status: The provisioning status. Possible values
     include: 'enabled', 'disabled'. Default value: "enabled" .
    :type provisioning_status: str or ~protocol.models.enum
    :param reprovision_policy: The behavior when a device is re-provisioned to
     an IoT hub.
    :type reprovision_policy: ~protocol.models.ReprovisionPolicy
    :ivar created_date_time_utc: The DateTime this resource was created.
    :vartype created_date_time_utc: datetime
    :ivar last_updated_date_time_utc: The DateTime this resource was last
     updated.
    :vartype last_updated_date_time_utc: datetime
    :param allocation_policy: The allocation policy of this resource. This
     policy overrides the tenant level allocation policy for this individual
     enrollment or enrollment group. Possible values include 'hashed': Linked
     IoT hubs are equally likely to have devices provisioned to them,
     'geoLatency':  Devices are provisioned to an IoT hub with the lowest
     latency to the device.If multiple linked IoT hubs would provide the same
     lowest latency, the provisioning service hashes devices across those hubs,
     'static' : Specification of the desired IoT hub in the enrollment list
     takes priority over the service-level allocation policy, 'custom': Devices
     are provisioned to an IoT hub based on your own custom logic. The
     provisioning service passes information about the device to the logic, and
     the logic returns the desired IoT hub as well as the desired initial
     configuration. We recommend using Azure Functions to host your logic.
     Possible values include: 'hashed', 'geoLatency', 'static', 'custom'
    :type allocation_policy: str or ~protocol.models.enum
    :param iot_hubs: The list of names of IoT hubs the device(s) in this
     resource can be allocated to. Must be a subset of tenant level list of IoT
     hubs.
    :type iot_hubs: list[str]
    :param custom_allocation_definition: Custom allocation definition.
    :type custom_allocation_definition:
     ~protocol.models.CustomAllocationDefinition
    """

    def __init__(self, registration_id, **kwargs):
        self.registration_id = registration_id
        self.capabilities = kwargs.get("capabilities", None)
        self.device_id = kwargs.get("device_id", None)
        self.registration_state = None
        self.attestation = kwargs.get("attestation", None)
        self.iot_hub_host_name = kwargs.get("iot_hub_host_name", None)
        self.initial_twin = kwargs.get("initial_twin", None)
        self.etag = kwargs.get("etag", None)
        self.provisioning_status = kwargs.get("provisioning_status", "enabled")
        self.reprovision_policy = kwargs.get("reprovision_policy", None)
        self.created_date_time_utc = None
        self.last_updated_date_time_utc = None
        self.allocation_policy = kwargs.get("allocation_policy", None)
        self.iot_hubs = kwargs.get("iot_hubs", None)
        self.custom_allocation_definition = kwargs.get("custom_allocation_definition", None)
        self.client_certificate_issuance_policy = kwargs.get(
            "client_certificate_issuance_policy", None
        )
