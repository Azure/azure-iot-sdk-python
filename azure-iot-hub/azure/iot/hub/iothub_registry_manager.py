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
    ServiceStatistics,
    RegistryStatistics,
    Configuration,
    ConfigurationContent,
    ConfigurationQueriesTestInput,
    ExportImportDevice,
    QuerySpecification,
    Twin,
    JobProperties,
    JobResponse,
    JobRequest,
    PurgeMessageQueueResult,
    CloudToDeviceMethod,
    CloudToDeviceMethodResult,
)

JobType = (
    "unknown",
    "export",
    "import",
    "backup",
    "readDeviceProperties",
    "writeDeviceProperties",
    "updateDeviceConfiguration",
    "rebootDevice",
    "factoryResetDevice",
    "firmwareUpdate",
    "scheduleDeviceMethod",
    "scheduleUpdateTwin",
    "restoreFromBackup",
    "failoverDataCopy",
)

JobStatus = (
    "unknown",
    "enqueued",
    "running",
    "completed",
    "failed",
    "cancelled",
    "scheduled",
    "queued",
)


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

    def create_device_with_sas(self, device_id, primary_key, secondary_key, status):
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
        }
        device = Device(**kwargs)

        return self.protocol.service.create_or_update_device(device_id, device)

    def create_device_with_x509(self, device_id, primary_thumbprint, secondary_thumbprint, status):
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
        }
        device = Device(**kwargs)

        return self.protocol.service.create_or_update_device(device_id, device)

    def create_device_with_certificate_authority(self, device_id, status):
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
        }
        device = Device(**kwargs)

        return self.protocol.service.create_or_update_device(device_id, device)

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

        return self.protocol.service.create_or_update_device(device_id, device, "*")

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

        return self.protocol.service.create_or_update_device(device_id, device)

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

        return self.protocol.service.create_or_update_device(device_id, device)

    def get_device(self, device_id):
        """Retrieves a device identity from IoTHub.

        :param str device_id: The name (Id) of the device.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The Device object containing the requested device.
        """
        return self.protocol.service.get_device(device_id)

    # Not recommended
    # def get_devices(self):
    #     return

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

        self.protocol.service.delete_device(device_id, etag)

    def create_module_with_sas(self, device_id, module_id, managed_by, primary_key, secondary_key):
        """Creates a module identity for a device on IoTHub using SAS authentication.

        :param str device_id: The name (Id) of the device.
        :param str module_id: The name (moduleID) of the module.
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

        return self.protocol.service.create_or_update_module(device_id, module_id, module)

    def create_module_with_x509(
        self, device_id, module_id, managed_by, primary_thumbprint, secondary_thumbprint
    ):
        """Creates a module identity for a device on IoTHub using X509 authentication.

        :param str device_id: The name (Id) of the device.
        :param str module_id: The name (moduleID) of the module.
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

        return self.protocol.service.create_or_update_module(device_id, module_id, module)

    def create_module_with_certificate_authority(self, device_id, module_id, managed_by):
        """Creates a module identity for a device on IoTHub using certificate authority.

        :param str device_id: The name (Id) of the device.
        :param str module_id: The name (moduleID) of the module.
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

        return self.protocol.service.create_or_update_module(device_id, module_id, module)

    def update_module_with_sas(
        self, device_id, module_id, managed_by, etag, primary_key, secondary_key
    ):
        """Updates a module identity for a device on IoTHub using SAS authentication.

        :param str device_id: The name (Id) of the device.
        :param str module_id: The name (moduleID) of the module.
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

        return self.protocol.service.create_or_update_module(device_id, module_id, module, "*")

    def update_module_with_x509(
        self, device_id, module_id, managed_by, etag, primary_thumbprint, secondary_thumbprint
    ):
        """Updates a module identity for a device on IoTHub using X509 authentication.

        :param str device_id: The name (Id) of the device.
        :param str module_id: The name (moduleID) of the module.
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

        return self.protocol.service.create_or_update_module(device_id, module_id, module)

    def update_module_with_certificate_authority(self, device_id, module_id, managed_by, etag):
        """Updates a module identity for a device on IoTHub using certificate authority.

        :param str device_id: The name (Id) of the device.
        :param str module_id: The name (moduleID) of the module.
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

        return self.protocol.service.create_or_update_module(device_id, module_id, module)

    def get_module(self, device_id, module_id):
        """Retrieves a module identity for a device from IoTHub.

        :param str device_id: The name (Id) of the device.
        :param str module_id: The name (moduleId) of the module.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The Module object containing the requested module.
        """
        return self.protocol.service.get_module(device_id, module_id)

    def get_modules(self, device_id):
        """Retrieves all module identities on a device.

        :param str device_id: The name (Id) of the device.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The list[Module] containing all the modules on the device.
        """
        return self.protocol.service.get_modules_on_device(device_id)

    def delete_module(self, device_id, module_id, etag=None):
        """Deletes a module identity for a device from IoTHub.

        :param str device_id: The name (Id) of the device.
        :param str module_id: The name (moduleId) of the module.
        :param str etag: The etag (if_match) value to use for the delete operation.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: None.
        """
        if etag is None:
            etag = "*"

        self.protocol.service.delete_module(device_id, module_id, etag)

    def get_service_statistics(self):
        """Retrieves the IoTHub service statistics.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The ServiceStatistics object.
        """
        return self.protocol.service.get_service_statistics()

    def get_device_registry_statistics(self):
        """Retrieves the IoTHub device registry statistics.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The RegistryStatistics object.
        """
        return self.protocol.service.get_device_registry_statistics()

    def get_configuration(self, configuration_id):
        """Retrieves the IoTHub configuration for a particular device.

        :param str configuration_id: The id of the configuration.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The Configuration object.
        """
        return self.protocol.service.get_configuration(configuration_id)

    def create_configuration(self, configuration_id, configuration):
        """Creates a configuration for devices or modules of an IoTHub.

        :param str configuration_id: The id of the configuration.
        :param Configuration configuration: The configuration to create.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: Configuration object containing the created configuration.
        """
        return self.protocol.service.create_or_update_configuration(configuration_id, configuration)

    def update_configuration(self, configuration_id, configuration, etag):
        """Updates a configuration for devices or modules of an IoTHub.

        :param str configuration_id: The id of the configuration.
        :param Configuration configuration: The configuration to create.
        :param str etag: The etag (if_match) value to use for the update operation.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: Configuration object containing the updated configuration.
        """
        return self.protocol.service.create_or_update_configuration(
            configuration_id, configuration, etag
        )

    def delete_configuration(self, configuration_id, etag=None):
        """Deletes a configuration from an IoTHub.

        :param str configuration_id: The id of the configuration.
        :param Configuration configuration: The configuration to create.
        :param str etag: The etag (if_match) value to use for the delete operation.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: Configuration object containing the updated configuration.
        """
        if etag is None:
            etag = "*"

        return self.protocol.service.delete_configuration(configuration_id, etag)

    def get_configurations(self, max_count=None):
        """Retrieves multiple configurations for device and modules of an IoTHub.
           Returns the specified number of configurations. Pagination is not supported.

        :param int max_count: The maximum number of configurations requested.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The list[Configuration] object.
        """
        return self.protocol.service.get_configurations(max_count)

    def test_configuration_queries(self, target_condition, custom_metric_queries):
        """Validates the target condition query and custom metric queries for a
           configuration.

        :param str target_condition: The target condition.
        :param {str} custom_metric_queries: The queries to validate.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The ConfigurationQueriesTestResponse object.
        """
        input = {
            "target_condition": target_condition,
            "custom_metric_queries": custom_metric_queries,
        }
        return self.protocol.service.test_configuration_queries(input)

    def bulk_create_or_update_devices(self, devices):
        """Create, update, or delete the identities of multiple devices from the
           IoT hub identity registry. Different operations (create, update, delete) on different
           devices are allowed.

        :param list[ExportImportDevice] devices: The list of device objects to operate on.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The BulkRegistryOperationResult object.
        """
        return self.protocol.service.bulk_create_or_update_devices(devices)

    def query_iot_hub(self, query):
        """Query an IoT hub to retrieve information regarding device twins using a
           SQL-like language.

        :param str query: The list of device objects to operate on.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The BulkRegistryOperationResult object.
        """
        query_specification = {"query": query}
        return self.protocol.service.query_iot_hub(query_specification)

    def apply_configuration_on_edge_device(
        self, device_id, device_configuration, modules_configuration, module_configuration
    ):
        """Applies the provided configuration content to the specified edge
           device. Modules content is mandantory.

        :param str device_id: The name (Id) of the edge device.
        :param str device_configuration: The device configuration to apply.
        :param str modules_configuration: The dictionary of multiple module configurations.
        :param str module_configuration: The single module configurations.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: An object.
        """
        configuration_content = {
            "device_content": device_configuration,
            "modules_content": modules_configuration,
            "module_content": module_configuration,
        }
        return self.protocol.service.apply_configuration_on_edge_device(
            device_id, configuration_content
        )

    def create_import_export_job(
        self,
        job_id,
        start_time,
        end_time,
        job_type,
        status,
        progress,
        input_blob_container_uri,
        input_blob_name,
        output_blob_container_uri,
        output_blob_name,
        exclude_keys_in_export,
        failure_reason,
    ):
        """Creates a new import/export job on an IoT hub.

        :param str job_id: The name of the job.
        :param datetime start_time: The start time in UTC.
        :param datetime end_time: The end time in UTC.
        :param JobType job_type: The type of the job.
        :param JobStatus status: The status of the job.
        :param int progress: The percentage of completion.
        :param str input_blob_container_uri: URI containing SAS token to a blob container that contains registry data to sync..
        :param str input_blob_name: The blob name to be used when importing from the provided input blob container.
        :param str output_blob_container_uri: URI containing SAS token to a blob container. This is used to output the status of the job and the results.
        :param str output_blob_name: The name of the blob that will be created in the provided output blob container. This blob will contain the exported device registry information for the IoT Hub.
        :param bool exclude_keys_in_export: Optional for export jobs; ignored for other jobs. Default: false. If false, authorization keys are included in export output. Keys are exported as null otherwise.
        :param str failure_reason: If status == failure, this represents a string containing the reason.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The JobProperties object.
        """
        job_properties = {
            "job_id": job_id,
            "start_time": start_time,
            "end_time": end_time,
            "job_type": job_type,
            "status": status,
            "progress": progress,
            "input_blob_container_uri": input_blob_container_uri,
            "input_blob_name": input_blob_name,
            "output_blob_container_uri": output_blob_container_uri,
            "output_blob_name": output_blob_name,
            "exclude_keys_in_export": exclude_keys_in_export,
            "failure_reason": failure_reason,
        }
        return self.protocol.service.create_import_export_job(job_properties)

    def get_import_export_jobs(self):
        """Gets the status of all import/export jobs in an iot hub.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The list[JobProperties] object.
        """
        return self.protocol.service.get_import_export_jobs()

    def get_import_export_job(self, job_id):
        """Gets the status of an import or export job in an iot hub.

        :param str job_id: The name of the job.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The JobProperties object.
        """
        return self.protocol.service.get_import_export_job(job_id)

    def cancel_import_export_job(self, job_id):
        """Cancels an import or export job in an IoT hub.

        :param str job_id: The name of the job.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: An object.
        """
        return self.protocol.service.cancel_import_export_job(job_id)

    def purge_command_queue(self, device_id):
        """Deletes all the pending commands for a device from the IoT hub.

        :param str device_id: The name (Id) of the device.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The PurgeMessageQueueResult object.
        """
        return self.protocol.service.purge_command_queue(device_id)

    def get_twin(self, device_id):
        """Gets a device twin.

        :param str device_id: The name (Id) of the device.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The Twin object.
        """
        return self.protocol.service.get_twin(device_id)

    def replace_twin(self, device_id, device_twin):
        """Replaces tags and desired properties of a device twin.

        :param str device_id: The name (Id) of the device.
        :param Twin device_twin: The twin info of the device.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The Twin object.
        """
        return self.protocol.service.replace_twin(device_id, device_twin)

    def update_twin(self, device_id, device_twin, etag):
        """Updates tags and desired properties of a device twin.

        :param str device_id: The name (Id) of the device.
        :param Twin device_twin: The twin info of the device.
        :param str etag: The etag (if_match) value to use for the update operation.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The Twin object.
        """
        return self.protocol.service.update_twin(device_id, device_twin, etag)

    def get_module_twin(self, device_id, module_id):
        """Gets a module twin.

        :param str device_id: The name (Id) of the device.
        :param str module_id: The name (Id) of the module.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The Twin object.
        """
        return self.protocol.service.get_module_twin(device_id, module_id)

    def replace_module_twin(self, device_id, module_id, module_twin):
        """Replaces tags and desired properties of a module twin.

        :param str device_id: The name (Id) of the device.
        :param str module_id: The name (Id) of the module.
        :param Twin module_twin: The twin info of the module.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The Twin object.
        """
        return self.protocol.service.replace_module_twin(device_id, module_id, module_twin)

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
        return self.protocol.service.update_module_twin(device_id, module_id, module_twin, etag)

    def get_job(self, job_id):
        """Retrieves details of a scheduled job from an IoT hub.

        :param str job_id: The name (Id) of the job.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The JobResponse object.
        """
        return self.protocol.service.get_job(job_id)

    def create_job(self, job_id, job_request):
        """Creates a new job to schedule update twins or device direct methods on
           an IoT hub at a scheduled time.

        :param str job_id: The name (Id) of the job.
        :param JobRequest job_request: The job request to create.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The JobResponse object.
        """
        return self.protocol.service.create_job(job_id, job_request)

    def cancel_job(self, job_id):
        """Cancels a scheduled job on an IoT hub.

        :param str job_id: The name (Id) of the job.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The JobResponse object.
        """
        return self.protocol.service.cancel_job(job_id)

    def query_jobs(self, job_type, job_status):
        """Query an IoT hub to retrieve information regarding jobs using the IoT
           Hub query language.

        :param JobType job_type: The type of the jobs to query.
        :param JobStatus job_status: The status of the jobs to query.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The JobResponse object.
        """
        return self.protocol.service.query_jobs(job_type, job_status)

    def invoke_device_method(self, device_id, direct_method_request):
        """Invoke a direct method on a device.

        :param str device_id: The name (Id) of the device.
        :param CloudToDeviceMethod direct_method_request: The method request.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The CloudToDeviceMethodResult object.
        """
        return self.protocol.service.invoke_device_method(device_id, direct_method_request)

    def invoke_device_module_method(self, device_id, module_id, direct_method_request):
        """Invoke a direct method on a device.

        :param str device_id: The name (Id) of the device.
        :param str module_id: The name (Id) of the module.
        :param CloudToDeviceMethod direct_method_request: The method request.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The CloudToDeviceMethodResult object.
        """
        return self.protocol.service.invoke_device_module_method(
            device_id, module_id, direct_method_request
        )
