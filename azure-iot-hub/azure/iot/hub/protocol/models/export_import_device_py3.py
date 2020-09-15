# coding=utf-8
# --------------------------------------------------------------------------
# Code generated by Microsoft (R) AutoRest Code Generator.
# Changes may cause incorrect behavior and will be lost if the code is
# regenerated.
# --------------------------------------------------------------------------

from msrest.serialization import Model


class ExportImportDevice(Model):
    """ExportImportDevice.

    :param id: The unique identifier of the device.
    :type id: str
    :param module_id: The unique identifier of the module, if applicable.
    :type module_id: str
    :param e_tag: The string representing a weak ETag for the device RFC7232.
     The value is only used if import mode is updateIfMatchETag, in that case
     the import operation is performed only if this ETag matches the value
     maintained by the server.
    :type e_tag: str
    :param import_mode: The type of registry operation and ETag preferences.
     Possible values include: 'create', 'update', 'updateIfMatchETag',
     'delete', 'deleteIfMatchETag', 'updateTwin', 'updateTwinIfMatchETag'
    :type import_mode: str or ~protocol.models.enum
    :param status: The status of the module. If disabled, the module cannot
     connect to the service. Possible values include: 'enabled', 'disabled'
    :type status: str or ~protocol.models.enum
    :param status_reason: The 128 character-long string that stores the reason
     for the device identity status. All UTF-8 characters are allowed.
    :type status_reason: str
    :param authentication: The authentication mechanism used by the module.
     This parameter is optional and defaults to SAS if not provided. In that
     case, primary/secondary access keys are auto-generated.
    :type authentication: ~protocol.models.AuthenticationMechanism
    :param twin_etag: The string representing a weak ETag for the device twin
     RFC7232. The value is only used if import mode is updateIfMatchETag, in
     that case the import operation is performed only if this ETag matches the
     value maintained by the server.
    :type twin_etag: str
    :param tags: The JSON document read and written by the solution back end.
     The tags are not visible to device apps.
    :type tags: dict[str, object]
    :param properties: The desired and reported properties for the device.
    :type properties: ~protocol.models.PropertyContainer
    :param capabilities: The status of capabilities enabled on the device.
    :type capabilities: ~protocol.models.DeviceCapabilities
    :param device_scope: The scope of the device.
    :type device_scope: str
    """

    _attribute_map = {
        "id": {"key": "id", "type": "str"},
        "module_id": {"key": "moduleId", "type": "str"},
        "e_tag": {"key": "eTag", "type": "str"},
        "import_mode": {"key": "importMode", "type": "str"},
        "status": {"key": "status", "type": "str"},
        "status_reason": {"key": "statusReason", "type": "str"},
        "authentication": {"key": "authentication", "type": "AuthenticationMechanism"},
        "twin_etag": {"key": "twinETag", "type": "str"},
        "tags": {"key": "tags", "type": "{object}"},
        "properties": {"key": "properties", "type": "PropertyContainer"},
        "capabilities": {"key": "capabilities", "type": "DeviceCapabilities"},
        "device_scope": {"key": "deviceScope", "type": "str"},
    }

    def __init__(
        self,
        *,
        id: str = None,
        module_id: str = None,
        e_tag: str = None,
        import_mode=None,
        status=None,
        status_reason: str = None,
        authentication=None,
        twin_etag: str = None,
        tags=None,
        properties=None,
        capabilities=None,
        device_scope: str = None,
        **kwargs
    ) -> None:
        super(ExportImportDevice, self).__init__(**kwargs)
        self.id = id
        self.module_id = module_id
        self.e_tag = e_tag
        self.import_mode = import_mode
        self.status = status
        self.status_reason = status_reason
        self.authentication = authentication
        self.twin_etag = twin_etag
        self.tags = tags
        self.properties = properties
        self.capabilities = capabilities
        self.device_scope = device_scope
