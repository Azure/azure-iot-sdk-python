# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

from .auth import ConnectionStringAuthentication
from .protocol.iot_hub_gateway_service_ap_is20190630 import (
    IotHubGatewayServiceAPIs20190630 as protocol_client,
)
from .protocol.models import (
    Device,
    Module,
    SymmetricKey,
    X509Thumbprint,
    AuthenticationMechanism,
    Configuration,
    ServiceStatistics,
    RegistryStatistics,
)


class IoTHubRegistryManager(object):
    """A class to provide convenience APIs for IoTHub Registry Manager operations,
    based on top of the auto generated IotHub REST APIs
    """

    def __init__(self, connection_string):
        """Initializer for a Registry Manager Service client.

        After a successful creation the class has been authenticated with IoTHub and
        it is ready to call the member APIs to communicate with IoTHub.

        :param: str connection_string: The authentication information
        (IoTHub connection string) to connect to IoTHub.

        :returns: IoTHubRegistryManager object.
        """

        self.auth = ConnectionStringAuthentication(connection_string)
        self.protocol = protocol_client(self.auth, "https://" + self.auth["HostName"])

    def create_device_with_sas(self, device_id, primary_key, secondary_key, status):
        """Creates a device identity on IoTHub using SAS authentication.

        :param str device_id: The name (deviceId) of the device.
        :param str primary_key: Primary authentication key.
        :param str secondary_key: Secondary authentication key.
        :param str status: Initital state of the created device (enabled or disabled).

        :raises: HttpOperationError if the HTTP response status is not in [200].

        :returns: Device object containing the created device.
        """
        symmetric_key = SymmetricKey(primary_key=primary_key, secondary_key=secondary_key)

        kwargs = {
            "device_id": device_id,
            "status": status,
            "authentication": AuthenticationMechanism(type="sas", symmetric_key=symmetric_key),
        }
        device = Device(**kwargs)

        return self.protocol.service.create_or_update_device(device_id, device)

    def create_device_with_x509(self, device_id, primary_thumbprint, secondary_thumbprint, status):
        """Creates a device identity on IoTHub using X509 authentication.

        :param str device_id: The name (deviceId) of the device.
        :param str primary_thumbprint: Primary X509 thumbprint.
        :param str secondary_thumbprint: Secondary X509 thumbprint.
        :param str status: Initital state of the created device (enabled or disabled).

        :raises: HttpOperationError if the HTTP response status is not in [200].

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
        }
        device = Device(**kwargs)

        return self.protocol.service.create_or_update_device(device_id, device)

    def create_device_with_certificate_authority(self, device_id, status):
        """Creates a device identity on IoTHub using certificate authority.

        :param str device_id: The name (deviceId) of the device.
        :param str status: Initital state of the created device (enabled or disabled).

        :raises: HttpOperationError if the HTTP response status is not in [200].

        :returns: Device object containing the created device.
        """
        kwargs = {
            "device_id": device_id,
            "status": status,
            "authentication": AuthenticationMechanism(type="certificateAuthority"),
        }
        device = Device(**kwargs)

        return self.protocol.service.create_or_update_device(device_id, device)

    def update_device_with_sas(self, device_id, etag, primary_key, secondary_key, status):
        """Updates a device identity on IoTHub using SAS authentication.

        :param str device_id: The name (deviceId) of the device.
        :param str etag: The etag (if_match) value to use for the update operation.
        :param str primary_key: Primary authentication key.
        :param str secondary_key: Secondary authentication key.
        :param str status: Initital state of the created device (enabled or disabled).

        :raises: HttpOperationError if the HTTP response status is not in [200].

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

        return self.protocol.service.create_or_update_device(device_id, device, "*")

    def update_device_with_x509(
        self, device_id, etag, primary_thumbprint, secondary_thumbprint, status
    ):
        """Updates a device identity on IoTHub using X509 authentication.

        :param str device_id: The name (deviceId) of the device.
        :param str etag: The etag (if_match) value to use for the update operation.
        :param str primary_thumbprint: Primary X509 thumbprint.
        :param str secondary_thumbprint: Secondary X509 thumbprint.
        :param str status: Initital state of the created device (enabled or disabled).

        :raises: HttpOperationError if the HTTP response status is not in [200].

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

        return self.protocol.service.create_or_update_device(device_id, device)

    def update_device_with_certificate_authority(self, device_id, etag, status):
        """Updates a device identity on IoTHub using certificate authority.

        :param str device_id: The name (deviceId) of the device.
        :param str etag: The etag (if_match) value to use for the update operation.
        :param str status: Initital state of the created device (enabled or disabled).

        :raises: HttpOperationError if the HTTP response status is not in [200].

        :returns: The updated Device object containing the created device.
        """
        kwargs = {
            "device_id": device_id,
            "status": status,
            "etag": etag,
            "authentication": AuthenticationMechanism(type="certificateAuthority"),
        }
        device = Device(**kwargs)

        return self.protocol.service.create_or_update_device(device_id, device)

    def get_device(self, device_id):
        """Retrieves a device identity from IoTHub.

        :param str device_id: The name (deviceId) of the device.

        :raises: HttpOperationError if the HTTP response status is not in [200].

        :returns: The Device object containing the requested device.
        """
        return self.protocol.service.get_device(device_id)

    def get_configuration(self, device_id):
        """Retrieves the IoTHub configuration for a particular device.

        :param str device_id: The name (deviceId) of the device.

        :raises: HttpOperationError if the HTTP response status is not in [200].

        :returns: The Configuration object.
        """
        return self.protocol.service.get_configuration(id)

    def delete_device(self, device_id, etag=None):
        """Deletes a device identity from IoTHub.

        :param str device_id: The name (deviceId) of the device.

        :raises: HttpOperationError if the HTTP response status is not in [200].

        :returns: None.
        """
        if etag is None:
            etag = "*"

        self.protocol.service.delete_device(device_id, etag)

    def get_service_statistics(self):
        """Retrieves the IoTHub service statistics.

        :raises: HttpOperationError if the HTTP response status is not in [200].

        :returns: The ServiceStatistics object.
        """
        return self.protocol.service.get_service_statistics()

    def get_device_registry_statistics(self):
        """Retrieves the IoTHub device registry statistics.

        :raises: HttpOperationError if the HTTP response status is not in [200].

        :returns: The RegistryStatistics object.
        """
        return self.protocol.service.get_device_registry_statistics()

    def create_module_with_sas(
        self, device_id, module_id, managed_by, primary_key, secondary_key, status
    ):
        """Creates a module identity for a device on IoTHub using SAS authentication.

        :param str device_id: The name (deviceId) of the device.
        :param str module_id: The name (moduleID) of the module.
        :param str managed_by: The name of the manager device (edge).
        :param str primary_key: Primary authentication key.
        :param str secondary_key: Secondary authentication key.
        :param str status: Initital state of the created device (enabled or disabled).

        :raises: HttpOperationError if the HTTP response status is not in [200].

        :returns: Module object containing the created module.
        """
        symmetric_key = SymmetricKey(primary_key=primary_key, secondary_key=secondary_key)

        kwargs = {
            "device_id": device_id,
            "module_id": module_id,
            "managed_by": managed_by,
            "status": status,
            "authentication": AuthenticationMechanism(type="sas", symmetric_key=symmetric_key),
        }
        module = Module(**kwargs)

        return self.protocol.service.create_or_update_module(device_id, module_id, module)

    def create_module_with_x509(
        self, device_id, module_id, managed_by, primary_thumbprint, secondary_thumbprint, status
    ):
        """Creates a module identity for a device on IoTHub using X509 authentication.

        :param str device_id: The name (deviceId) of the device.
        :param str module_id: The name (moduleID) of the module.
        :param str managed_by: The name of the manager device (edge).
        :param str primary_thumbprint: Primary X509 thumbprint.
        :param str secondary_thumbprint: Secondary X509 thumbprint.
        :param str status: Initital state of the created device (enabled or disabled).

        :raises: HttpOperationError if the HTTP response status is not in [200].

        :returns: Module object containing the created module.
        """
        x509_thumbprint = X509Thumbprint(
            primary_thumbprint=primary_thumbprint, secondary_thumbprint=secondary_thumbprint
        )

        kwargs = {
            "device_id": device_id,
            "module_id": module_id,
            "managed_by": managed_by,
            "status": status,
            "authentication": AuthenticationMechanism(
                type="selfSigned", x509_thumbprint=x509_thumbprint
            ),
        }
        module = Module(**kwargs)

        return self.protocol.service.create_or_update_module(device_id, module_id, module)

    def create_module_with_certificate_authority(self, device_id, module_id, managed_by, status):
        """Creates a module identity for a device on IoTHub using certificate authority.

        :param str device_id: The name (deviceId) of the device.
        :param str module_id: The name (moduleID) of the module.
        :param str managed_by: The name of the manager device (edge).
        :param str status: Initital state of the created device (enabled or disabled).

        :raises: HttpOperationError if the HTTP response status is not in [200].

        :returns: Module object containing the created module.
        """
        kwargs = {
            "device_id": device_id,
            "module_id": module_id,
            "managed_by": managed_by,
            "status": status,
            "authentication": AuthenticationMechanism(type="certificateAuthority"),
        }
        module = Module(**kwargs)

        return self.protocol.service.create_or_update_module(device_id, module_id, module)

    def update_module_with_sas(
        self, device_id, module_id, managed_by, etag, primary_key, secondary_key, status
    ):
        """Updates a module identity for a device on IoTHub using SAS authentication.

        :param str device_id: The name (deviceId) of the device.
        :param str module_id: The name (moduleID) of the module.
        :param str managed_by: The name of the manager device (edge).
        :param str etag: The etag (if_match) value to use for the update operation.
        :param str primary_key: Primary authentication key.
        :param str secondary_key: Secondary authentication key.
        :param str status: Initital state of the created device (enabled or disabled).

        :raises: HttpOperationError if the HTTP response status is not in [200].

        :returns: The updated Module object containing the created module.
        """
        symmetric_key = SymmetricKey(primary_key=primary_key, secondary_key=secondary_key)

        kwargs = {
            "device_id": device_id,
            "module_id": module_id,
            "managed_by": managed_by,
            "status": status,
            "etag": etag,
            "authentication": AuthenticationMechanism(type="sas", symmetric_key=symmetric_key),
        }
        module = Module(**kwargs)

        return self.protocol.service.create_or_update_module(device_id, module_id, module, "*")

    def update_module_with_x509(
        self,
        device_id,
        module_id,
        managed_by,
        etag,
        primary_thumbprint,
        secondary_thumbprint,
        status,
    ):
        """Updates a module identity for a device on IoTHub using X509 authentication.

        :param str device_id: The name (deviceId) of the device.
        :param str module_id: The name (moduleID) of the module.
        :param str managed_by: The name of the manager device (edge).
        :param str etag: The etag (if_match) value to use for the update operation.
        :param str primary_thumbprint: Primary X509 thumbprint.
        :param str secondary_thumbprint: Secondary X509 thumbprint.
        :param str status: Initital state of the created device (enabled or disabled).

        :raises: HttpOperationError if the HTTP response status is not in [200].

        :returns: The updated Module object containing the created module.
        """
        x509_thumbprint = X509Thumbprint(
            primary_thumbprint=primary_thumbprint, secondary_thumbprint=secondary_thumbprint
        )

        kwargs = {
            "device_id": device_id,
            "module_id": module_id,
            "managed_by": managed_by,
            "status": status,
            "etag": etag,
            "authentication": AuthenticationMechanism(
                type="selfSigned", x509_thumbprint=x509_thumbprint
            ),
        }
        module = Module(**kwargs)

        return self.protocol.service.create_or_update_module(device_id, module_id, module)

    def update_module_with_certificate_authority(
        self, device_id, module_id, managed_by, etag, status
    ):
        """Updates a module identity for a device on IoTHub using certificate authority.

        :param str device_id: The name (deviceId) of the device.
        :param str module_id: The name (moduleID) of the module.
        :param str managed_by: The name of the manager device (edge).
        :param str etag: The etag (if_match) value to use for the update operation.
        :param str status: Initital state of the created device (enabled or disabled).

        :raises: HttpOperationError if the HTTP response status is not in [200].

        :returns: The updated Module object containing the created module.
        """
        kwargs = {
            "device_id": device_id,
            "module_id": module_id,
            "managed_by": managed_by,
            "status": status,
            "etag": etag,
            "authentication": AuthenticationMechanism(type="certificateAuthority"),
        }
        module = Module(**kwargs)

        return self.protocol.service.create_or_update_module(device_id, module_id, module)

    def get_module(self, device_id, module_id):
        """Retrieves a module identity for a device from IoTHub.

        :param str device_id: The name (deviceId) of the device.
        :param str module_id: The name (moduleId) of the module.

        :raises: HttpOperationError if the HTTP response status is not in [200].

        :returns: The Module object containing the requested module.
        """
        return self.protocol.service.get_module(device_id, module_id)

    def delete_module(self, device_id, etag=None):
        """Deletes a module identity for a device from IoTHub.

        :param str device_id: The name (deviceId) of the device.

        :raises: HttpOperationError if the HTTP response status is not in [200].

        :returns: None.
        """
        if etag is None:
            etag = "*"

        self.protocol.service.delete_module(device_id, etag)
