# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
from azure.iot.hub.protocol.models import AuthenticationMechanism
from azure.iot.hub.iothub_configuration_manager import IoTHubConfigurationManager
from azure.iot.hub.auth import ConnectionStringAuthentication
from azure.iot.hub.protocol.iot_hub_gateway_service_ap_is import IotHubGatewayServiceAPIs

"""---Constants---"""

fake_shared_access_key = "Zm9vYmFy"
fake_shared_access_key_name = "alohomora"
fake_hostname = "beauxbatons.academy-net"
fake_device_id = "MyPensieve"
fake_etag = "taggedbymisnitryofmagic"
fake_configuration_id = "fake_configuration_id"


class fake_configuration_object:
    id = fake_configuration_id


fake_configuration = fake_configuration_object()
fake_max_count = 42
fake_configuration_queries = "fake_configuration_queries"
fake_configuration_content = "fake_configuration_content"


"""----Shared fixtures----"""


@pytest.fixture(scope="function", autouse=True)
def mock_configuration_operations(mocker):
    mock_configuration_operations_init = mocker.patch(
        "azure.iot.hub.protocol.iot_hub_gateway_service_ap_is.ConfigurationOperations"
    )
    return mock_configuration_operations_init.return_value


@pytest.fixture(scope="function")
def iothub_configuration_manager():
    connection_string = "HostName={hostname};DeviceId={device_id};SharedAccessKeyName={skn};SharedAccessKey={sk}".format(
        hostname=fake_hostname,
        device_id=fake_device_id,
        skn=fake_shared_access_key_name,
        sk=fake_shared_access_key,
    )
    iothub_configuration_manager = IoTHubConfigurationManager.from_connection_string(
        connection_string
    )
    return iothub_configuration_manager


@pytest.mark.describe("IoTHubConfigurationManager - .from_connection_string()")
class TestFromConnectionString(object):
    @pytest.mark.parametrize(
        "connection_string",
        [
            "HostName={hostname};DeviceId={device_id};SharedAccessKeyName={skn};SharedAccessKey={sk}".format(
                hostname=fake_hostname,
                device_id=fake_device_id,
                skn=fake_shared_access_key_name,
                sk=fake_shared_access_key,
            ),
            "HostName={hostname};SharedAccessKeyName={skn};SharedAccessKey={sk}".format(
                hostname=fake_hostname, skn=fake_shared_access_key_name, sk=fake_shared_access_key
            ),
            "HostName={hostname};DeviceId={device_id};SharedAccessKey={sk}".format(
                hostname=fake_hostname, device_id=fake_device_id, sk=fake_shared_access_key
            ),
        ],
    )
    @pytest.mark.it(
        "Creates an instance of ConnectionStringAuthentication and passes it to IotHubGatewayServiceAPIs constructor"
    )
    def test_connection_string_auth(self, connection_string):
        client = IoTHubConfigurationManager.from_connection_string(
            connection_string=connection_string
        )

        assert repr(client.auth) == connection_string
        assert client.protocol.config.base_url == "https://" + client.auth["HostName"]
        assert client.protocol.config.credentials == client.auth

    @pytest.mark.it("Sets the auth and protocol attributes")
    def test_instantiates_auth_and_protocol_attributes(self, iothub_configuration_manager):
        assert isinstance(iothub_configuration_manager.auth, ConnectionStringAuthentication)
        assert isinstance(iothub_configuration_manager.protocol, IotHubGatewayServiceAPIs)

    @pytest.mark.it(
        "Raises a ValueError exception when instantiated with an empty connection string"
    )
    def test_instantiates_with_empty_connection_string(self):
        with pytest.raises(ValueError):
            IoTHubConfigurationManager.from_connection_string("")

    @pytest.mark.it(
        "Raises a ValueError exception when instantiated with a connection string without HostName"
    )
    def test_instantiates_with_connection_string_no_host_name(self):
        connection_string = (
            "DeviceId={device_id};SharedAccessKeyName={skn};SharedAccessKey={sk}".format(
                device_id=fake_device_id, skn=fake_shared_access_key_name, sk=fake_shared_access_key
            )
        )
        with pytest.raises(ValueError):
            IoTHubConfigurationManager.from_connection_string(connection_string)

    @pytest.mark.it("Instantiates with an connection string without DeviceId")
    def test_instantiates_with_connection_string_no_device_id(self):
        connection_string = (
            "HostName={hostname};SharedAccessKeyName={skn};SharedAccessKey={sk}".format(
                hostname=fake_hostname, skn=fake_shared_access_key_name, sk=fake_shared_access_key
            )
        )
        obj = IoTHubConfigurationManager.from_connection_string(connection_string)
        assert isinstance(obj, IoTHubConfigurationManager)

    @pytest.mark.it("Instantiates with an connection string without SharedAccessKeyName")
    def test_instantiates_with_connection_string_no_shared_access_key_name(self):
        connection_string = "HostName={hostname};DeviceId={device_id};SharedAccessKey={sk}".format(
            hostname=fake_hostname, device_id=fake_device_id, sk=fake_shared_access_key
        )
        obj = IoTHubConfigurationManager.from_connection_string(connection_string)
        assert isinstance(obj, IoTHubConfigurationManager)

    @pytest.mark.it(
        "Raises a ValueError exception when instantiated with a connection string without SharedAccessKey"
    )
    def test_instantiates_with_connection_string_no_shared_access_key(self):
        connection_string = (
            "HostName={hostname};DeviceId={device_id};SharedAccessKeyName={skn}".format(
                hostname=fake_hostname, device_id=fake_device_id, skn=fake_shared_access_key_name
            )
        )
        with pytest.raises(ValueError):
            IoTHubConfigurationManager.from_connection_string(connection_string)


@pytest.mark.describe("IoTHubConfigurationManager - .from_token_credential()")
class TestFromTokenCredential(object):
    @pytest.mark.it(
        "Creates an instance of AzureIdentityCredentialAdapter and passes it to IotHubGatewayServiceAPIs constructor"
    )
    def test_token_credential_auth(self, mocker):
        mock_azure_identity_TokenCredential = mocker.MagicMock()

        client = IoTHubConfigurationManager.from_token_credential(
            fake_hostname, mock_azure_identity_TokenCredential
        )

        assert client.auth._policy._credential == mock_azure_identity_TokenCredential
        assert client.protocol.config.base_url == "https://" + fake_hostname
        assert client.protocol.config.credentials == client.auth


@pytest.mark.describe("IoTHubConfigurationManager - .get_configuration()")
class TestGetConfiguration(object):
    @pytest.mark.it("Gets configuration")
    def test_get(self, mocker, mock_configuration_operations, iothub_configuration_manager):
        iothub_configuration_manager.get_configuration(fake_configuration_id)

        assert mock_configuration_operations.get.call_count == 1
        assert mock_configuration_operations.get.call_args == mocker.call(fake_configuration_id)


@pytest.mark.describe("IoTHubConfigurationManager - .create_configuration()")
class TestCreateConfiguration(object):
    @pytest.mark.it("Creates configuration")
    def test_create_configuration(
        self, mocker, mock_configuration_operations, iothub_configuration_manager
    ):
        iothub_configuration_manager.create_configuration(fake_configuration)

        assert mock_configuration_operations.create_or_update.call_count == 1
        assert mock_configuration_operations.create_or_update.call_args == mocker.call(
            fake_configuration_id, fake_configuration
        )


@pytest.mark.describe("IoTHubConfigurationManager - .update_configuration()")
class TestUpdateConfiguration(object):
    @pytest.mark.it("Updates configuration")
    def test_update_configuration(
        self, mocker, mock_configuration_operations, iothub_configuration_manager
    ):
        iothub_configuration_manager.update_configuration(fake_configuration, fake_etag)

        assert mock_configuration_operations.create_or_update.call_count == 1
        assert mock_configuration_operations.create_or_update.call_args == mocker.call(
            fake_configuration_id, fake_configuration, fake_etag
        )


@pytest.mark.describe("IoTHubConfigurationManager - .delete_configuration()")
class TestDeleteConfiguration(object):
    @pytest.mark.it("Deletes configuration")
    def test_delete_configuration(
        self, mocker, mock_configuration_operations, iothub_configuration_manager
    ):
        iothub_configuration_manager.delete_configuration(fake_configuration_id)

        assert mock_configuration_operations.delete.call_count == 1
        assert mock_configuration_operations.delete.call_args == mocker.call(
            fake_configuration_id, "*"
        )

    @pytest.mark.it("Deletes configuration with an etag")
    def test_delete_configuration_with_etag(
        self, mocker, mock_configuration_operations, iothub_configuration_manager
    ):
        iothub_configuration_manager.delete_configuration(
            configuration_id=fake_configuration_id, etag=fake_etag
        )

        assert mock_configuration_operations.delete.call_count == 1
        assert mock_configuration_operations.delete.call_args == mocker.call(
            fake_configuration_id, fake_etag
        )


@pytest.mark.describe("IoTHubConfigurationManager - .get_configurations()")
class TestGetConfigurations(object):
    @pytest.mark.it("Get configurations")
    def test_get_configurations(
        self, mocker, mock_configuration_operations, iothub_configuration_manager
    ):
        iothub_configuration_manager.get_configurations(fake_max_count)

        assert mock_configuration_operations.get_configurations.call_count == 1
        assert mock_configuration_operations.get_configurations.call_args == mocker.call(
            fake_max_count
        )


@pytest.mark.describe("IoTHubConfigurationManager - .test_configuration_queries()")
class TestTestConfigurationQueries(object):
    @pytest.mark.it("Test test_configuration_queries")
    def test_test_configuration_queries(
        self, mocker, mock_configuration_operations, iothub_configuration_manager
    ):
        iothub_configuration_manager.test_configuration_queries(fake_configuration_queries)
        assert mock_configuration_operations.test_queries.call_count == 1
        assert mock_configuration_operations.test_queries.call_args == mocker.call(
            fake_configuration_queries
        )


@pytest.mark.describe("IoTHubConfigurationManager - .apply_configuration_on_edge_device()")
class TestApplyConfigurationOnEdgeDevice(object):
    @pytest.mark.it("Test apply configuration on edge device")
    def test_apply_configuration_on_edge_device(
        self, mocker, mock_configuration_operations, iothub_configuration_manager
    ):
        iothub_configuration_manager.apply_configuration_on_edge_device(
            fake_device_id, fake_configuration_content
        )
        assert mock_configuration_operations.apply_on_edge_device.call_count == 1
        assert mock_configuration_operations.apply_on_edge_device.call_args == mocker.call(
            fake_device_id, fake_configuration_content
        )
