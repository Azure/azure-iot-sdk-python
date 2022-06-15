# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
from . import iothub_amqp_client
from .auth import ConnectionStringAuthentication, AzureIdentityCredentialAdapter
from .protocol.iot_hub_gateway_service_ap_is import IotHubGatewayServiceAPIs as protocol_client
from .protocol.models import (
    Device,
    Module,
    SymmetricKey,
    X509Thumbprint,
    AuthenticationMechanism,
    DeviceCapabilities,
)


def _ensure_quoted(etag):
    if not isinstance(etag, str) or (len(etag) > 1 and etag[0] == '"' and etag[-1] == '"'):
        return etag
    return '"' + etag + '"'


class QueryResult(object):
    """The query result.
    :param type: The query result type. Possible values include: 'unknown', 'twin', 'deviceJob', 'jobResponse', 'raw', 'enrollment', 'enrollmentGroup', 'deviceRegistration'
    :type type: str or ~protocol.models.enum
    :param items: The query result items, as a collection.
    :type items: list[object]
    :param continuation_token: Request continuation token.
    :type continuation_token: str
    """

    _attribute_map = {
        "type": {"key": "type", "type": "str"},
        "items": {"key": "items", "type": "[object]"},
        "continuation_token": {"key": "continuationToken", "type": "str"},
    }

    def __init__(self, **kwargs):
        super(QueryResult, self).__init__(**kwargs)
        self.type = kwargs.get("type", None)
        self.items = kwargs.get("items", None)
        self.continuation_token = kwargs.get("continuation_token", None)


class IoTHubRegistryManager(object):
    """A class to provide convenience APIs for IoTHub Registry Manager operations,
    based on top of the auto generated IotHub REST APIs
    """

    def __init__(self, connection_string=None, host=None, token_credential=None):
        """Initializer for a Registry Manager Service client.

        Users should not call this directly. Rather, they should the from_connection_string()
        or from_token_credential() factory methods.

        After a successful creation the class has been authenticated with IoTHub and
        it is ready to call the member APIs to communicate with IoTHub.

        :param str connection_string: The IoTHub connection string used to authenticate connection
            with IoTHub if we are using connection_str authentication. Default value: None
        :param str host: The Azure service url if we are using token credential authentication.
            Default value: None
        :param str auth: The Azure authentication object if we are using token credential authentication.
            Default value: None

        :returns: Instance of the IoTHubRegistryManager object.
        :rtype: :class:`azure.iot.hub.IoTHubRegistryManager`
        """
        self.amqp_svc_client = None
        if connection_string is not None:
            conn_string_auth = ConnectionStringAuthentication(connection_string)
            self.protocol = protocol_client(
                conn_string_auth, "https://" + conn_string_auth["HostName"]
            )
            self.amqp_svc_client = iothub_amqp_client.IoTHubAmqpClientSharedAccessKeyAuth(
                conn_string_auth["HostName"],
                conn_string_auth["SharedAccessKeyName"],
                conn_string_auth["SharedAccessKey"],
            )
        else:
            self.protocol = protocol_client(
                AzureIdentityCredentialAdapter(token_credential), "https://" + host
            )
            self.amqp_svc_client = iothub_amqp_client.IoTHubAmqpClientTokenAuth(
                host, token_credential
            )

    @classmethod
    def from_connection_string(cls, connection_string):
        """Classmethod initializer for a Registry Manager Service client.
        Creates Registry Manager class from connection string.

        After a successful creation the class has been authenticated with IoTHub and
        it is ready to call the member APIs to communicate with IoTHub.

        :param str connection_string: The IoTHub connection string used to authenticate connection
            with IoTHub.

        :rtype: :class:`azure.iot.hub.IoTHubRegistryManager`
        """
        return cls(connection_string=connection_string)

    @classmethod
    def from_token_credential(cls, url, token_credential):
        """Classmethod initializer for a Registry Manager Service client.
        Creates Registry Manager class from host name url and Azure token credential.

        After a successful creation the class has been authenticated with IoTHub and
        it is ready to call the member APIs to communicate with IoTHub.

        :param str url: The Azure service url (host name).
        :param token_credential: The Azure token credential object
        :type token_credential: :class:`azure.core.TokenCredential`

        :rtype: :class:`azure.iot.hub.IoTHubRegistryManager`
        """
        return cls(host=url, token_credential=token_credential)

    def __del__(self):
        """
        Deinitializer for a Registry Manager Service client.
        """
        if self.amqp_svc_client is not None:
            self.amqp_svc_client.disconnect_sync()

    def create_device_with_sas(
        self,
        device_id,
        primary_key,
        secondary_key,
        status,
        iot_edge=False,
        status_reason=None,
        device_scope=None,
        parent_scopes=None,
    ):
        """Creates a device identity on IoTHub using SAS authentication.

        :param str device_id: The name (Id) of the device.
        :param str primary_key: Primary authentication key.
        :param str secondary_key: Secondary authentication key.
        :param str status: Initial state of the created device.
            (Possible values: "enabled" or "disabled")
        :param bool iot_edge: Whether or not the created device is an IoT Edge device. Default value: False
        :param str status_reason: The reason for the device identity status. Default value: None
        :param str device_scope: The scope of the device. Default value: None
            Auto generated and immutable for edge devices and modifiable in leaf devices to create child/parent relationship.
            For leaf devices, the value to set a parent edge device can be retrieved from the parent edge device's device_scope property.
        :param Union[list[str], str] parent_scopes: The scopes of the upper level edge devices if applicable. Default value: None
            For edge devices, the value to set a parent edge device can be retrieved from the parent edge device's device_scope property.
            For leaf devices, this could be set to the same value as device_scope or left for the service to copy over.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: Device object containing the created device.
        """
        symmetric_key = SymmetricKey(primary_key=primary_key, secondary_key=secondary_key)

        if isinstance(parent_scopes, str):
            parent_scopes = [parent_scopes]

        kwargs = {
            "device_id": device_id,
            "status": status,
            "authentication": AuthenticationMechanism(type="sas", symmetric_key=symmetric_key),
            "capabilities": DeviceCapabilities(iot_edge=iot_edge),
            "status_reason": status_reason,
            "device_scope": device_scope,
            "parent_scopes": parent_scopes,
        }
        device = Device(**kwargs)

        return self.protocol.devices.create_or_update_identity(device_id, device)

    def create_device_with_x509(
        self,
        device_id,
        primary_thumbprint,
        secondary_thumbprint,
        status,
        iot_edge=False,
        status_reason=None,
        device_scope=None,
        parent_scopes=None,
    ):
        """Creates a device identity on IoTHub using X509 authentication.

        :param str device_id: The name (Id) of the device.
        :param str primary_thumbprint: Primary X509 thumbprint.
        :param str secondary_thumbprint: Secondary X509 thumbprint.
        :param str status: Initial state of the created device.
            (Possible values: "enabled" or "disabled")
        :param bool iot_edge: Whether or not the created device is an IoT Edge device. Default value: False
        :param str status_reason: The reason for the device identity status. Default value: None
        :param str device_scope: The scope of the device. Default value: None
            Auto generated and immutable for edge devices and modifiable in leaf devices to create child/parent relationship.
            For leaf devices, the value to set a parent edge device can be retrieved from the parent edge device's device_scope property.
        :param Union[list[str], str] parent_scopes: The scopes of the upper level edge devices if applicable. Default value: None
            For edge devices, the value to set a parent edge device can be retrieved from the parent edge device's device_scope property.
            For leaf devices, this could be set to the same value as device_scope or left for the service to copy over.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: Device object containing the created device.
        """
        x509_thumbprint = X509Thumbprint(
            primary_thumbprint=primary_thumbprint, secondary_thumbprint=secondary_thumbprint
        )

        if isinstance(parent_scopes, str):
            parent_scopes = [parent_scopes]

        kwargs = {
            "device_id": device_id,
            "status": status,
            "authentication": AuthenticationMechanism(
                type="selfSigned", x509_thumbprint=x509_thumbprint
            ),
            "capabilities": DeviceCapabilities(iot_edge=iot_edge),
            "status_reason": status_reason,
            "device_scope": device_scope,
            "parent_scopes": parent_scopes,
        }
        device = Device(**kwargs)

        return self.protocol.devices.create_or_update_identity(device_id, device)

    def create_device_with_certificate_authority(
        self,
        device_id,
        status,
        iot_edge=False,
        status_reason=None,
        device_scope=None,
        parent_scopes=None,
    ):
        """Creates a device identity on IoTHub using certificate authority.

        :param str device_id: The name (Id) of the device.
        :param str status: Initial state of the created device.
            (Possible values: "enabled" or "disabled").
        :param bool iot_edge: Whether or not the created device is an IoT Edge device. Default value: False
        :param str status_reason: The reason for the device identity status. Default value: None
        :param str device_scope: The scope of the device. Default value: None
            Auto generated and immutable for edge devices and modifiable in leaf devices to create child/parent relationship.
            For leaf devices, the value to set a parent edge device can be retrieved from the parent edge device's device_scope property.
        :param Union[list[str], str] parent_scopes: The scopes of the upper level edge devices if applicable. Default value: None
            For edge devices, the value to set a parent edge device can be retrieved from the parent edge device's device_scope property.
            For leaf devices, this could be set to the same value as device_scope or left for the service to copy over.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: Device object containing the created device.
        """
        if isinstance(parent_scopes, str):
            parent_scopes = [parent_scopes]

        kwargs = {
            "device_id": device_id,
            "status": status,
            "authentication": AuthenticationMechanism(type="certificateAuthority"),
            "capabilities": DeviceCapabilities(iot_edge=iot_edge),
            "status_reason": status_reason,
            "device_scope": device_scope,
            "parent_scopes": parent_scopes,
        }
        device = Device(**kwargs)

        return self.protocol.devices.create_or_update_identity(device_id, device)

    def update_device_with_sas(
        self,
        device_id,
        etag,
        primary_key,
        secondary_key,
        status,
        iot_edge=False,
        status_reason=None,
        device_scope=None,
        parent_scopes=None,
    ):
        """Updates a device identity on IoTHub using SAS authentication.

        :param str device_id: The name (Id) of the device.
        :param str etag: The etag (if_match) value to use for the update operation.
        :param str primary_key: Primary authentication key.
        :param str secondary_key: Secondary authentication key.
        :param str status: Initial state of the created device.
            (Possible values: "enabled" or "disabled").
        :param bool iot_edge: Whether or not the created device is an IoT Edge device. Default value: False
        :param str status_reason: The reason for the device identity status. Default value: None
        :param str device_scope: The scope of the device. Default value: None
            Auto generated and immutable for edge devices and modifiable in leaf devices to create child/parent relationship.
            For leaf devices, the value to set a parent edge device can be retrieved from the parent edge device's device_scope property.
        :param Union[list[str], str] parent_scopes: The scopes of the upper level edge devices if applicable. Default value: None
            For edge devices, the value to set a parent edge device can be retrieved from the parent edge device's device_scope property.
            For leaf devices, this could be set to the same value as device_scope or left for the service to copy over.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The updated Device object containing the created device.
        """
        symmetric_key = SymmetricKey(primary_key=primary_key, secondary_key=secondary_key)

        if isinstance(parent_scopes, str):
            parent_scopes = [parent_scopes]

        kwargs = {
            "device_id": device_id,
            "status": status,
            "authentication": AuthenticationMechanism(type="sas", symmetric_key=symmetric_key),
            "capabilities": DeviceCapabilities(iot_edge=iot_edge),
            "status_reason": status_reason,
            "device_scope": device_scope,
            "parent_scopes": parent_scopes,
        }
        device = Device(**kwargs)

        if etag is None:
            etag = "*"

        return self.protocol.devices.create_or_update_identity(
            device_id, device, _ensure_quoted(etag)
        )

    def update_device_with_x509(
        self,
        device_id,
        etag,
        primary_thumbprint,
        secondary_thumbprint,
        status,
        iot_edge=False,
        status_reason=None,
        device_scope=None,
        parent_scopes=None,
    ):
        """Updates a device identity on IoTHub using X509 authentication.

        :param str device_id: The name (Id) of the device.
        :param str etag: The etag (if_match) value to use for the update operation.
        :param str primary_thumbprint: Primary X509 thumbprint.
        :param str secondary_thumbprint: Secondary X509 thumbprint.
        :param str status: Initial state of the created device.
            (Possible values: "enabled" or "disabled").
        :param bool iot_edge: Whether or not the created device is an IoT Edge device. Default value: False
        :param str status_reason: The reason for the device identity status. Default value: None
        :param str device_scope: The scope of the device. Default value: None
            Auto generated and immutable for edge devices and modifiable in leaf devices to create child/parent relationship.
            For leaf devices, the value to set a parent edge device can be retrieved from the parent edge device's device_scope property.
        :param Union[list[str], str] parent_scopes: The scopes of the upper level edge devices if applicable. Default value: None
            For edge devices, the value to set a parent edge device can be retrieved from the parent edge device's device_scope property.
            For leaf devices, this could be set to the same value as device_scope or left for the service to copy over.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The updated Device object containing the created device.
        """
        x509_thumbprint = X509Thumbprint(
            primary_thumbprint=primary_thumbprint, secondary_thumbprint=secondary_thumbprint
        )

        if isinstance(parent_scopes, str):
            parent_scopes = [parent_scopes]

        kwargs = {
            "device_id": device_id,
            "status": status,
            "authentication": AuthenticationMechanism(
                type="selfSigned", x509_thumbprint=x509_thumbprint
            ),
            "capabilities": DeviceCapabilities(iot_edge=iot_edge),
            "status_reason": status_reason,
            "device_scope": device_scope,
            "parent_scopes": parent_scopes,
        }
        device = Device(**kwargs)

        if etag is None:
            etag = "*"

        return self.protocol.devices.create_or_update_identity(
            device_id, device, _ensure_quoted(etag)
        )

    def update_device_with_certificate_authority(
        self,
        device_id,
        etag,
        status,
        iot_edge=False,
        status_reason=None,
        device_scope=None,
        parent_scopes=None,
    ):
        """Updates a device identity on IoTHub using certificate authority.

        :param str device_id: The name (Id) of the device.
        :param str etag: The etag (if_match) value to use for the update operation.
        :param str status: Initial state of the created device.
            (Possible values: "enabled" or "disabled").
        :param bool iot_edge: Whether or not the created device is an IoT Edge device. Default value: False
        :param str status_reason: The reason for the device identity status. Default value: None
        :param str device_scope: The scope of the device. Default value: None
            Auto generated and immutable for edge devices and modifiable in leaf devices to create child/parent relationship.
            For leaf devices, the value to set a parent edge device can be retrieved from the parent edge device's device_scope property.
        :param Union[list[str], str] parent_scopes: The scopes of the upper level edge devices if applicable. Default value: None
            For edge devices, the value to set a parent edge device can be retrieved from the parent edge device's device_scope property.
            For leaf devices, this could be set to the same value as device_scope or left for the service to copy over.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The updated Device object containing the created device.
        """
        if isinstance(parent_scopes, str):
            parent_scopes = [parent_scopes]

        kwargs = {
            "device_id": device_id,
            "status": status,
            "authentication": AuthenticationMechanism(type="certificateAuthority"),
            "capabilities": DeviceCapabilities(iot_edge=iot_edge),
            "status_reason": status_reason,
            "device_scope": device_scope,
            "parent_scopes": parent_scopes,
        }
        device = Device(**kwargs)

        if etag is None:
            etag = "*"

        return self.protocol.devices.create_or_update_identity(
            device_id, device, _ensure_quoted(etag)
        )

    def get_device(self, device_id):
        """Retrieves a device identity from IoTHub.

        :param str device_id: The name (Id) of the device.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The Device object containing the requested device.
        """
        return self.protocol.devices.get_identity(device_id)

    def delete_device(self, device_id, etag=None):
        """Deletes a device identity from IoTHub.

        :param str device_id: The name (Id) of the device.
        :param str etag: The etag (if_match) value to use for the delete operation.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: None.
        """
        if etag is None:
            etag = "*"

        self.protocol.devices.delete_identity(device_id, _ensure_quoted(etag))

    def create_module_with_sas(self, device_id, module_id, managed_by, primary_key, secondary_key):
        """Creates a module identity for a device on IoTHub using SAS authentication.

        :param str device_id: The name (Id) of the device.
        :param str module_id: The name (Id) of the module.
        :param str managed_by: The name of the manager device (edge).
        :param str primary_key: Primary authentication key.
        :param str secondary_key: Secondary authentication key.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: Module object containing the created module.
        """
        symmetric_key = SymmetricKey(primary_key=primary_key, secondary_key=secondary_key)

        kwargs = {
            "device_id": device_id,
            "module_id": module_id,
            "managed_by": managed_by,
            "authentication": AuthenticationMechanism(type="sas", symmetric_key=symmetric_key),
        }
        module = Module(**kwargs)

        return self.protocol.modules.create_or_update_identity(device_id, module_id, module)

    def create_module_with_x509(
        self, device_id, module_id, managed_by, primary_thumbprint, secondary_thumbprint
    ):
        """Creates a module identity for a device on IoTHub using X509 authentication.

        :param str device_id: The name (Id) of the device.
        :param str module_id: The name (Id) of the module.
        :param str managed_by: The name of the manager device (edge).
        :param str primary_thumbprint: Primary X509 thumbprint.
        :param str secondary_thumbprint: Secondary X509 thumbprint.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: Module object containing the created module.
        """
        x509_thumbprint = X509Thumbprint(
            primary_thumbprint=primary_thumbprint, secondary_thumbprint=secondary_thumbprint
        )

        kwargs = {
            "device_id": device_id,
            "module_id": module_id,
            "managed_by": managed_by,
            "authentication": AuthenticationMechanism(
                type="selfSigned", x509_thumbprint=x509_thumbprint
            ),
        }
        module = Module(**kwargs)

        return self.protocol.modules.create_or_update_identity(device_id, module_id, module)

    def create_module_with_certificate_authority(self, device_id, module_id, managed_by):
        """Creates a module identity for a device on IoTHub using certificate authority.

        :param str device_id: The name (Id) of the device.
        :param str module_id: The name (Id) of the module.
        :param str managed_by: The name of the manager device (edge).

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: Module object containing the created module.
        """
        kwargs = {
            "device_id": device_id,
            "module_id": module_id,
            "managed_by": managed_by,
            "authentication": AuthenticationMechanism(type="certificateAuthority"),
        }
        module = Module(**kwargs)

        return self.protocol.modules.create_or_update_identity(device_id, module_id, module)

    def update_module_with_sas(
        self, device_id, module_id, managed_by, etag, primary_key, secondary_key
    ):
        """Updates a module identity for a device on IoTHub using SAS authentication.

        :param str device_id: The name (Id) of the device.
        :param str module_id: The name (Id) of the module.
        :param str managed_by: The name of the manager device (edge).
        :param str etag: The etag (if_match) value to use for the update operation.
        :param str primary_key: Primary authentication key.
        :param str secondary_key: Secondary authentication key.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The updated Module object containing the created module.
        """
        symmetric_key = SymmetricKey(primary_key=primary_key, secondary_key=secondary_key)

        kwargs = {
            "device_id": device_id,
            "module_id": module_id,
            "managed_by": managed_by,
            "authentication": AuthenticationMechanism(type="sas", symmetric_key=symmetric_key),
        }
        module = Module(**kwargs)

        if etag is None:
            etag = "*"

        return self.protocol.modules.create_or_update_identity(
            device_id, module_id, module, _ensure_quoted(etag)
        )

    def update_module_with_x509(
        self, device_id, module_id, managed_by, etag, primary_thumbprint, secondary_thumbprint
    ):
        """Updates a module identity for a device on IoTHub using X509 authentication.

        :param str device_id: The name (Id) of the device.
        :param str module_id: The name (Id) of the module.
        :param str managed_by: The name of the manager device (edge).
        :param str etag: The etag (if_match) value to use for the update operation.
        :param str primary_thumbprint: Primary X509 thumbprint.
        :param str secondary_thumbprint: Secondary X509 thumbprint.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The updated Module object containing the created module.
        """
        x509_thumbprint = X509Thumbprint(
            primary_thumbprint=primary_thumbprint, secondary_thumbprint=secondary_thumbprint
        )

        kwargs = {
            "device_id": device_id,
            "module_id": module_id,
            "managed_by": managed_by,
            "authentication": AuthenticationMechanism(
                type="selfSigned", x509_thumbprint=x509_thumbprint
            ),
        }
        module = Module(**kwargs)

        if etag is None:
            etag = "*"

        return self.protocol.modules.create_or_update_identity(
            device_id, module_id, module, _ensure_quoted(etag)
        )

    def update_module_with_certificate_authority(self, device_id, module_id, managed_by, etag):
        """Updates a module identity for a device on IoTHub using certificate authority.

        :param str device_id: The name (Id) of the device.
        :param str module_id: The name (Id) of the module.
        :param str managed_by: The name of the manager device (edge).
        :param str etag: The etag (if_match) value to use for the update operation.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The updated Module object containing the created module.
        """
        kwargs = {
            "device_id": device_id,
            "module_id": module_id,
            "managed_by": managed_by,
            "etag": etag,
            "authentication": AuthenticationMechanism(type="certificateAuthority"),
        }
        module = Module(**kwargs)

        if etag is None:
            etag = "*"

        return self.protocol.modules.create_or_update_identity(
            device_id, module_id, module, _ensure_quoted(etag)
        )

    def get_module(self, device_id, module_id):
        """Retrieves a module identity for a device from IoTHub.

        :param str device_id: The name (Id) of the device.
        :param str module_id: The name (Id) of the module.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The Module object containing the requested module.
        """
        return self.protocol.modules.get_identity(device_id, module_id)

    def get_modules(self, device_id):
        """Retrieves all module identities on a device.

        :param str device_id: The name (Id) of the device.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The list[Module] containing all the modules on the device.
        """
        return self.protocol.modules.get_modules_on_device(device_id)

    def delete_module(self, device_id, module_id, etag=None):
        """Deletes a module identity for a device from IoTHub.

        :param str device_id: The name (Id) of the device.
        :param str module_id: The name (Id) of the module.
        :param str etag: The etag (if_match) value to use for the delete operation.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: None.
        """
        if etag is None:
            etag = "*"

        self.protocol.modules.delete_identity(device_id, module_id, _ensure_quoted(etag))

    def get_service_statistics(self):
        """Retrieves the IoTHub service statistics.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The ServiceStatistics object.
        """
        return self.protocol.statistics.get_service_statistics()

    def get_device_registry_statistics(self):
        """Retrieves the IoTHub device registry statistics.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The RegistryStatistics object.
        """
        return self.protocol.statistics.get_device_statistics()

    def get_devices(self, max_number_of_devices=None):
        """Get the identities of multiple devices from the IoTHub identity
           registry. Not recommended. Use the IoTHub query language to retrieve
           device twin and device identity information. See
           https://docs.microsoft.com/en-us/rest/api/iothub/service/queryiothub
           and
           https://docs.microsoft.com/en-us/azure/iot-hub/iot-hub-devguide-query-language
           for more information.

        :param int max_number_of_devices: This parameter when specified, defines the maximum number
           of device identities that are returned. Any value outside the range of
           1-1000 is considered to be 1000

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: List of device info.
        """
        return self.protocol.devices.get_devices(max_number_of_devices)

    def bulk_create_or_update_devices(self, devices):
        """Create, update, or delete the identities of multiple devices from the
           IoTHub identity registry.

           Create, update, or delete the identities of multiple devices from the
           IoTHub identity registry. A device identity can be specified only once
           in the list. Different operations (create, update, delete) on different
           devices are allowed. A maximum of 100 devices can be specified per
           invocation. For large scale operations, consider using the import
           feature using blob
           storage(https://docs.microsoft.com/azure/iot-hub/iot-hub-devguide-identity-registry#import-and-export-device-identities).

        :param list[ExportImportDevice] devices: The list of device objects to operate on.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The BulkRegistryOperationResult object.
        """
        return self.protocol.bulk_registry.update_registry(devices)

    def query_iot_hub(self, query_specification, continuation_token=None, max_item_count=None):
        """Query an IoTHub to retrieve information regarding device twins using a
           SQL-like language.
           See https://docs.microsoft.com/azure/iot-hub/iot-hub-devguide-query-language
           for more information. Pagination of results is supported. This returns
           information about device twins only.

        :param QuerySpecification query: The query specification.
        :param str continuation_token: Continuation token for paging
        :param str max_item_count: Maximum number of requested device twins

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The QueryResult object.
        """
        raw_response = self.protocol.query.get_twins(
            query_specification, continuation_token, max_item_count, None, True
        )

        queryResult = QueryResult()
        if raw_response.headers:
            queryResult.type = raw_response.headers["x-ms-item-type"]
            queryResult.continuation_token = raw_response.headers["x-ms-continuation"]
        queryResult.items = raw_response.output

        return queryResult

    def get_twin(self, device_id):
        """Gets a device twin.

        :param str device_id: The name (Id) of the device.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The Twin object.
        """
        return self.protocol.devices.get_twin(device_id)

    def replace_twin(self, device_id, device_twin, etag=None):
        """Replaces tags and desired properties of a device twin.

        :param str device_id: The name (Id) of the device.
        :param Twin device_twin: The twin info of the device.
        :param str etag: The etag (if_match) value to use for the replace operation.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The Twin object.
        """
        if etag is None:
            etag = "*"

        return self.protocol.devices.replace_twin(device_id, device_twin, _ensure_quoted(etag))

    def update_twin(self, device_id, device_twin, etag=None):
        """Updates tags and desired properties of a device twin.

        :param str device_id: The name (Id) of the device.
        :param Twin device_twin: The twin info of the device.
        :param str etag: The etag (if_match) value to use for the update operation.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The Twin object.
        """
        if etag is None:
            etag = "*"

        return self.protocol.devices.update_twin(device_id, device_twin, _ensure_quoted(etag))

    def get_module_twin(self, device_id, module_id):
        """Gets a module twin.

        :param str device_id: The name (Id) of the device.
        :param str module_id: The name (Id) of the module.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The Twin object.
        """
        return self.protocol.modules.get_twin(device_id, module_id)

    def replace_module_twin(self, device_id, module_id, module_twin, etag=None):
        """Replaces tags and desired properties of a module twin.

        :param str device_id: The name (Id) of the device.
        :param str module_id: The name (Id) of the module.
        :param Twin module_twin: The twin info of the module.
        :param str etag: The etag (if_match) value to use for the replace operation.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The Twin object.
        """
        if etag is None:
            etag = "*"

        return self.protocol.modules.replace_twin(
            device_id, module_id, module_twin, _ensure_quoted(etag)
        )

    def update_module_twin(self, device_id, module_id, module_twin, etag=None):
        """Updates tags and desired properties of a module twin.

        :param str device_id: The name (Id) of the device.
        :param str module_id: The name (Id) of the module.
        :param Twin module_twin: The twin info of the module.
        :param str etag: The etag (if_match) value to use for the update operation.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The Twin object.
        """
        if etag is None:
            etag = "*"

        return self.protocol.modules.update_twin(
            device_id, module_id, module_twin, _ensure_quoted(etag)
        )

    def invoke_device_method(self, device_id, direct_method_request):
        """Invoke a direct method on a device.

        :param str device_id: The name (Id) of the device.
        :param CloudToDeviceMethod direct_method_request: The method request.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The CloudToDeviceMethodResult object.
        """
        if direct_method_request.payload is None:
            direct_method_request.payload = ""

        return self.protocol.devices.invoke_method(device_id, direct_method_request)

    def invoke_device_module_method(self, device_id, module_id, direct_method_request):
        """Invoke a direct method on a device.

        :param str device_id: The name (Id) of the device.
        :param str module_id: The name (Id) of the module.
        :param CloudToDeviceMethod direct_method_request: The method request.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The CloudToDeviceMethodResult object.
        """
        if direct_method_request.payload is None:
            direct_method_request.payload = ""

        return self.protocol.modules.invoke_method(device_id, module_id, direct_method_request)

    def send_c2d_message(self, device_id, message, properties={}):
        """Send a C2D message to a IoTHub Device.

        :param str device_id: The name (Id) of the device.
        :param str message: The message that is to be delivered to the device.
        :param dict properties: The properties to be send with the message.  Can contain
            application properties and system properties

        :raises: Exception if the Send command is not able to send the message
        """
        self.amqp_svc_client.send_message_to_device(device_id, message, properties)
