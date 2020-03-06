# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
from azure.iot.hub.protocol.models import AuthenticationMechanism
from azure.iot.hub.iothub_configuration_manager import IoTHubConfigurationManager

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
    iothub_configuration_manager = IoTHubConfigurationManager(connection_string)
    return iothub_configuration_manager


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
