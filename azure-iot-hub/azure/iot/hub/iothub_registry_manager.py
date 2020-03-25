# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
from .iothub_amqp_client import IoTHubAmqpClient as iothub_amqp_client
from .auth import ConnectionStringAuthentication
from .protocol.iot_hub_gateway_service_ap_is import IotHubGatewayServiceAPIs as protocol_client
from .protocol.models import (
    Device,
    Module,
    SymmetricKey,
    X509Thumbprint,
    AuthenticationMechanism,
    ServiceStatistics,
    RegistryStatistics,
    QuerySpecification,
    Twin,
    CloudToDeviceMethod,
    CloudToDeviceMethodResult,
    DeviceCapabilities,
)


class QueryResult(object):
    """The query result.
    :param type: The query result type. Possible values include: 'unknown',
     'twin', 'deviceJob', 'jobResponse', 'raw', 'enrollment',
     'enrollmentGroup', 'deviceRegistration'
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

    def __init__(self, connection_string):
        """Initializer for a Registry Manager Service client.

        After a successful creation the class has been authenticated with IoTHub and
        it is ready to call the member APIs to communicate with IoTHub.

        :param str connection_string: The IoTHub connection string used to authenticate connection
            with IoTHub.

        :returns: Instance of the IoTHubRegistryManager object.
        :rtype: :class:`azure.iot.hub.IoTHubRegistryManager`
        """
        self.auth = ConnectionStringAuthentication(connection_string)
        self.protocol = protocol_client(self.auth, "https://" + self.auth["HostName"])
        self.amqp_svc_client = iothub_amqp_client(
            self.auth["HostName"], self.auth["SharedAccessKeyName"], self.auth["SharedAccessKey"]
        )

    def __del__(self):
        """
        Deinitializer for a Registry Manager Service client.
        """
        self.amqp_svc_client.disconnect_sync()

    def create_device_with_sas(self, device_id, primary_key, secondary_key, status, iot_edge=False):
        """Creates a device identity on IoTHub using SAS authentication.

        :param str device_id: The name (Id) of the device.
        :param str primary_key: Primary authentication key.
        :param str secondary_key: Secondary authentication key.
        :param str status: Initital state of the created device.
            (Possible values: "enabled" or "disabled")

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: Device object containing the created device.
        """
        symmetric_key = SymmetricKey(primary_key=primary_key, secondary_key=secondary_key)

        kwargs = {
            "device_id": device_id,
            "status": status,
            "authentication": AuthenticationMechanism(type="sas", symmetric_key=symmetric_key),
            "capabilities": DeviceCapabilities(iot_edge=iot_edge),
        }
        device = Device(**kwargs)

        return self.protocol.registry_manager.create_or_update_device(device_id, device)

    def create_device_with_x509(
        self, device_id, primary_thumbprint, secondary_thumbprint, status, iot_edge=False
    ):
        """Creates a device identity on IoTHub using X509 authentication.

        :param str device_id: The name (Id) of the device.
        :param str primary_thumbprint: Primary X509 thumbprint.
        :param str secondary_thumbprint: Secondary X509 thumbprint.
        :param str status: Initital state of the created device.
            (Possible values: "enabled" or "disabled")

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: Device object containing the created device.
        """
        x509_thumbprint = X509Thumbprint(
            primary_thumbprint=primary_thumbprint, secondary_thumbprint=secondary_thumbprint
        )

        kwargs = {
            "device_id": device_id,
            "status": status,
            "authentication": AuthenticationMechanism(
                type="selfSigned", x509_thumbprint=x509_thumbprint
            ),
            "capabilities": DeviceCapabilities(iot_edge=iot_edge),
        }
        device = Device(**kwargs)

        return self.protocol.registry_manager.create_or_update_device(device_id, device)

    def create_device_with_certificate_authority(self, device_id, status, iot_edge=False):
        """Creates a device identity on IoTHub using certificate authority.

        :param str device_id: The name (Id) of the device.
        :param str status: Initial state of the created device.
            (Possible values: "enabled" or "disabled").

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: Device object containing the created device.
        """
        kwargs = {
            "device_id": device_id,
            "status": status,
            "authentication": AuthenticationMechanism(type="certificateAuthority"),
            "capabilities": DeviceCapabilities(iot_edge=iot_edge),
        }
        device = Device(**kwargs)

        return self.protocol.registry_manager.create_or_update_device(device_id, device)

    def update_device_with_sas(self, device_id, etag, primary_key, secondary_key, status):
        """Updates a device identity on IoTHub using SAS authentication.

        :param str device_id: The name (Id) of the device.
        :param str etag: The etag (if_match) value to use for the update operation.
        :param str primary_key: Primary authentication key.
        :param str secondary_key: Secondary authentication key.
        :param str status: Initital state of the created device.
            (Possible values: "enabled" or "disabled").

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The updated Device object containing the created device.
        """
        symmetric_key = SymmetricKey(primary_key=primary_key, secondary_key=secondary_key)

        kwargs = {
            "device_id": device_id,
            "status": status,
            "etag": etag,
            "authentication": AuthenticationMechanism(type="sas", symmetric_key=symmetric_key),
        }
        device = Device(**kwargs)

        return self.protocol.registry_manager.create_or_update_device(device_id, device, "*")

    def update_device_with_x509(
        self, device_id, etag, primary_thumbprint, secondary_thumbprint, status
    ):
        """Updates a device identity on IoTHub using X509 authentication.

        :param str device_id: The name (Id) of the device.
        :param str etag: The etag (if_match) value to use for the update operation.
        :param str primary_thumbprint: Primary X509 thumbprint.
        :param str secondary_thumbprint: Secondary X509 thumbprint.
        :param str status: Initital state of the created device.
            (Possible values: "enabled" or "disabled").

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The updated Device object containing the created device.
        """
        x509_thumbprint = X509Thumbprint(
            primary_thumbprint=primary_thumbprint, secondary_thumbprint=secondary_thumbprint
        )

        kwargs = {
            "device_id": device_id,
            "status": status,
            "etag": etag,
            "authentication": AuthenticationMechanism(
                type="selfSigned", x509_thumbprint=x509_thumbprint
            ),
        }
        device = Device(**kwargs)

        return self.protocol.registry_manager.create_or_update_device(device_id, device)

    def update_device_with_certificate_authority(self, device_id, etag, status):
        """Updates a device identity on IoTHub using certificate authority.

        :param str device_id: The name (Id) of the device.
        :param str etag: The etag (if_match) value to use for the update operation.
        :param str status: Initital state of the created device.
            (Possible values: "enabled" or "disabled").

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The updated Device object containing the created device.
        """
        kwargs = {
            "device_id": device_id,
            "status": status,
            "etag": etag,
            "authentication": AuthenticationMechanism(type="certificateAuthority"),
        }
        device = Device(**kwargs)

        return self.protocol.registry_manager.create_or_update_device(device_id, device)

    def get_device(self, device_id):
        """Retrieves a device identity from IoTHub.

        :param str device_id: The name (Id) of the device.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The Device object containing the requested device.
        """
        return self.protocol.registry_manager.get_device(device_id)

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

        self.protocol.registry_manager.delete_device(device_id, etag)

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

        return self.protocol.registry_manager.create_or_update_module(device_id, module_id, module)

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

        return self.protocol.registry_manager.create_or_update_module(device_id, module_id, module)

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

        return self.protocol.registry_manager.create_or_update_module(device_id, module_id, module)

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
            "etag": etag,
            "authentication": AuthenticationMechanism(type="sas", symmetric_key=symmetric_key),
        }
        module = Module(**kwargs)

        return self.protocol.registry_manager.create_or_update_module(
            device_id, module_id, module, "*"
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
            "etag": etag,
            "authentication": AuthenticationMechanism(
                type="selfSigned", x509_thumbprint=x509_thumbprint
            ),
        }
        module = Module(**kwargs)

        return self.protocol.registry_manager.create_or_update_module(device_id, module_id, module)

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

        return self.protocol.registry_manager.create_or_update_module(device_id, module_id, module)

    def get_module(self, device_id, module_id):
        """Retrieves a module identity for a device from IoTHub.

        :param str device_id: The name (Id) of the device.
        :param str module_id: The name (Id) of the module.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The Module object containing the requested module.
        """
        return self.protocol.registry_manager.get_module(device_id, module_id)

    def get_modules(self, device_id):
        """Retrieves all module identities on a device.

        :param str device_id: The name (Id) of the device.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The list[Module] containing all the modules on the device.
        """
        return self.protocol.registry_manager.get_modules_on_device(device_id)

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

        self.protocol.registry_manager.delete_module(device_id, module_id, etag)

    def get_service_statistics(self):
        """Retrieves the IoTHub service statistics.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The ServiceStatistics object.
        """
        return self.protocol.registry_manager.get_service_statistics()

    def get_device_registry_statistics(self):
        """Retrieves the IoTHub device registry statistics.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The RegistryStatistics object.
        """
        return self.protocol.registry_manager.get_device_statistics()

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
        return self.protocol.registry_manager.get_devices(max_number_of_devices)

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
        return self.protocol.registry_manager.bulk_device_crud(devices)

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
        raw_response = self.protocol.registry_manager.query_iot_hub(
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
        return self.protocol.twin.get_device_twin(device_id)

    def replace_twin(self, device_id, device_twin):
        """Replaces tags and desired properties of a device twin.

        :param str device_id: The name (Id) of the device.
        :param Twin device_twin: The twin info of the device.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The Twin object.
        """
        return self.protocol.twin.replace_device_twin(device_id, device_twin)

    def update_twin(self, device_id, device_twin, etag):
        """Updates tags and desired properties of a device twin.

        :param str device_id: The name (Id) of the device.
        :param Twin device_twin: The twin info of the device.
        :param str etag: The etag (if_match) value to use for the update operation.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The Twin object.
        """
        return self.protocol.twin.update_device_twin(device_id, device_twin, etag)

    def get_module_twin(self, device_id, module_id):
        """Gets a module twin.

        :param str device_id: The name (Id) of the device.
        :param str module_id: The name (Id) of the module.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The Twin object.
        """
        return self.protocol.twin.get_module_twin(device_id, module_id)

    def replace_module_twin(self, device_id, module_id, module_twin):
        """Replaces tags and desired properties of a module twin.

        :param str device_id: The name (Id) of the device.
        :param str module_id: The name (Id) of the module.
        :param Twin module_twin: The twin info of the module.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The Twin object.
        """
        return self.protocol.twin.replace_module_twin(device_id, module_id, module_twin)

    def update_module_twin(self, device_id, module_id, module_twin, etag):
        """Updates tags and desired properties of a module twin.

        :param str device_id: The name (Id) of the device.
        :param str module_id: The name (Id) of the module.
        :param Twin module_twin: The twin info of the module.
        :param str etag: The etag (if_match) value to use for the update operation.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The Twin object.
        """
        return self.protocol.twin.update_module_twin(device_id, module_id, module_twin, etag)

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

        return self.protocol.device_method.invoke_device_method(device_id, direct_method_request)

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

        return self.protocol.device_method.invoke_module_method(
            device_id, module_id, direct_method_request
        )

    def send_c2d_message(self, device_id, message):
        """Send a C2D mesage to a IoTHub Device.

        :param str device_id: The name (Id) of the device.
        :param str message: The message that is to be delievered to the device.

        :raises: Exception if the Send command is not able to send the message
        """

        self.amqp_svc_client.send_message_to_device(device_id, message)
