# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

from .auth import ConnectionStringAuthentication
from .protocol.iot_hub_gateway_service_ap_is import IotHubGatewayServiceAPIs as protocol_client
from .protocol.models import Configuration, ConfigurationContent, ConfigurationQueriesTestInput


class IoTHubConfigurationManager(object):
    """A class to provide convenience APIs for IoTHub Registry Manager operations,
    based on top of the auto generated IotHub REST APIs
    """

    def __init__(self, connection_string):
        """Initializer for a Configuration Manager Service client.

        After a successful creation the class has been authenticated with IoTHub and
        it is ready to call the member APIs to communicate with IoTHub.

        :param str connection_string: The IoTHub connection string used to authenticate connection
            with IoTHub.

        :returns: Instance of the IoTHubRegistryManager object.
        :rtype: :class:`azure.iot.hub.IoTHubRegistryManager`
        """

        self.auth = ConnectionStringAuthentication(connection_string)
        self.protocol = protocol_client(self.auth, "https://" + self.auth["HostName"])

    def get_configuration(self, configuration_id):
        """Retrieves the IoTHub configuration for a particular device.

        :param str configuration_id: The id of the configuration.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The Configuration object.
        """
        return self.protocol.configuration.get(configuration_id)

    def create_configuration(self, configuration):
        """Creates a configuration for devices or modules of an IoTHub.

        :param str configuration_id: The id of the configuration.
        :param Configuration configuration: The configuration to create.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: Configuration object containing the created configuration.
        """
        return self.protocol.configuration.create_or_update(configuration.id, configuration)

    def update_configuration(self, configuration, etag):
        """Updates a configuration for devices or modules of an IoTHub.
           Note: that configuration Id and Content cannot be updated by the user.

        :param str configuration_id: The id of the configuration.
        :param Configuration configuration: The configuration contains the updated configuration.
        :param str etag: The etag (if_match) value to use for the update operation.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: Configuration object containing the updated configuration.
        """
        return self.protocol.configuration.create_or_update(configuration.id, configuration, etag)

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

        return self.protocol.configuration.delete(configuration_id, etag)

    def get_configurations(self, max_count=None):
        """Retrieves multiple configurations for device and modules of an IoTHub.
           Returns the specified number of configurations. Pagination is not supported.

        :param int max_count: The maximum number of configurations requested.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The list[Configuration] object.
        """
        return self.protocol.configuration.get_configurations(max_count)

    def test_configuration_queries(self, configuration_queries_test_input):
        """Validates the target condition query and custom metric queries for a
           configuration.

        :param ConfigurationQueriesTestInput configuration_queries_test_input: The queries test input.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: The ConfigurationQueriesTestResponse object.
        """
        return self.protocol.configuration.test_queries(configuration_queries_test_input)

    def apply_configuration_on_edge_device(self, device_id, configuration_content):
        """Applies the provided configuration content to the specified edge
           device. Modules content is mandantory.

        :param ConfigurationContent configuration_content: The name (Id) of the edge device.

        :raises: `HttpOperationError<msrest.exceptions.HttpOperationError>`
            if the HTTP response status is not in [200].

        :returns: An object.
        """
        return self.protocol.configuration.apply_on_edge_device(device_id, configuration_content)
