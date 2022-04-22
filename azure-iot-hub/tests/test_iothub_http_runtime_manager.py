# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
from azure.iot.hub.iothub_http_runtime_manager import IoTHubHttpRuntimeManager
from azure.iot.hub.auth import ConnectionStringAuthentication
from azure.iot.hub.protocol.iot_hub_gateway_service_ap_is import IotHubGatewayServiceAPIs

"""---Constants---"""

fake_hostname = "beauxbatons.academy-net"
fake_device_id = "MyPensieve"
fake_shared_access_key_name = "alohomora"
fake_shared_access_key = "Zm9vYmFy"
fake_lock_token = "fake_lock_token"


"""----Shared fixtures----"""


@pytest.fixture(scope="function", autouse=True)
def mock_http_runtime_operations(mocker):
    mock_http_runtime_operations_init = mocker.patch(
        "azure.iot.hub.protocol.iot_hub_gateway_service_ap_is.CloudToDeviceMessagesOperations"
    )
    return mock_http_runtime_operations_init.return_value


@pytest.fixture(scope="function")
def iothub_http_runtime_manager():
    connection_string = "HostName={hostname};DeviceId={device_id};SharedAccessKeyName={skn};SharedAccessKey={sk}".format(
        hostname=fake_hostname,
        device_id=fake_device_id,
        skn=fake_shared_access_key_name,
        sk=fake_shared_access_key,
    )
    iothub_http_runtime_manager = IoTHubHttpRuntimeManager.from_connection_string(connection_string)
    return iothub_http_runtime_manager


@pytest.mark.describe("IoTHubHttpRuntimeManager - .from_connection_string()")
class TestFromConnectionString:
    @pytest.mark.parametrize(
        "connection_string",
        [
            pytest.param(
                "HostName={hostname};DeviceId={device_id};SharedAccessKeyName={skn};SharedAccessKey={sk}".format(
                    hostname=fake_hostname,
                    device_id=fake_device_id,
                    skn=fake_shared_access_key_name,
                    sk=fake_shared_access_key,
                ),
                id="connection string with HostName, DeviceId, SharedAccessKeyName, and SharedAccessKey",
            ),
            pytest.param(
                "HostName={hostname};SharedAccessKeyName={skn};SharedAccessKey={sk}".format(
                    hostname=fake_hostname,
                    skn=fake_shared_access_key_name,
                    sk=fake_shared_access_key,
                ),
                id="connection string without DeviceId",
            ),
            pytest.param(
                "HostName={hostname};DeviceId={device_id};SharedAccessKey={sk}".format(
                    hostname=fake_hostname, device_id=fake_device_id, sk=fake_shared_access_key
                ),
                id="connection string without SharedAccessKeyName",
            ),
        ],
    )
    @pytest.mark.it(
        "Creates an instance of ConnectionStringAuthentication and passes it to IotHubGatewayServiceAPIs constructor"
    )
    def test_connection_string_auth(self, connection_string):
        client = IoTHubHttpRuntimeManager.from_connection_string(
            connection_string=connection_string
        )

        assert repr(client.auth) == connection_string
        assert client.protocol.config.base_url == "https://" + client.auth["HostName"]
        assert client.protocol.config.credentials == client.auth

    @pytest.mark.it("Sets the auth and protocol attributes")
    def test_instantiates_auth_and_protocol_attributes(self, iothub_http_runtime_manager):
        assert isinstance(iothub_http_runtime_manager.auth, ConnectionStringAuthentication)
        assert isinstance(iothub_http_runtime_manager.protocol, IotHubGatewayServiceAPIs)

    @pytest.mark.it(
        "Raises a ValueError exception when instantiated with an empty connection string"
    )
    def test_instantiates_with_empty_connection_string(self):
        with pytest.raises(ValueError):
            IoTHubHttpRuntimeManager.from_connection_string("")

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
            IoTHubHttpRuntimeManager.from_connection_string(connection_string)

    @pytest.mark.it("Instantiates with an connection string without DeviceId")
    def test_instantiates_with_connection_string_no_device_id(self):
        connection_string = (
            "HostName={hostname};SharedAccessKeyName={skn};SharedAccessKey={sk}".format(
                hostname=fake_hostname, skn=fake_shared_access_key_name, sk=fake_shared_access_key
            )
        )
        obj = IoTHubHttpRuntimeManager.from_connection_string(connection_string)
        assert isinstance(obj, IoTHubHttpRuntimeManager)

    @pytest.mark.it("Instantiates with an connection string without SharedAccessKeyName")
    def test_instantiates_with_connection_string_no_shared_access_key_name(self):
        connection_string = "HostName={hostname};DeviceId={device_id};SharedAccessKey={sk}".format(
            hostname=fake_hostname, device_id=fake_device_id, sk=fake_shared_access_key
        )
        obj = IoTHubHttpRuntimeManager.from_connection_string(connection_string)
        assert isinstance(obj, IoTHubHttpRuntimeManager)

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
            IoTHubHttpRuntimeManager.from_connection_string(connection_string)


@pytest.mark.describe("IoTHubHttpRuntimeManager - .from_token_credential()")
class TestFromTokenCredential:
    @pytest.mark.it(
        "Creates an instance of AzureIdentityCredentialAdapter and passes it to IotHubGatewayServiceAPIs constructor"
    )
    def test_token_credential_auth(self, mocker):
        mock_azure_identity_TokenCredential = mocker.MagicMock()

        client = IoTHubHttpRuntimeManager.from_token_credential(
            fake_hostname, mock_azure_identity_TokenCredential
        )

        assert client.auth._policy._credential == mock_azure_identity_TokenCredential
        assert client.protocol.config.base_url == "https://" + fake_hostname
        assert client.protocol.config.credentials == client.auth


@pytest.mark.describe("IoTHubHttpRuntimeManager - .receive_feedback_notification()")
class TestReceiveFeedbackNotification(object):
    @pytest.mark.it("Uses protocol layer HTTP runtime to receive feedback notifications")
    def test_receive_feedback_notification(
        self, mocker, mock_http_runtime_operations, iothub_http_runtime_manager
    ):
        ret_val = iothub_http_runtime_manager.receive_feedback_notification()
        assert mock_http_runtime_operations.receive_feedback_notification.call_count == 1
        assert mock_http_runtime_operations.receive_feedback_notification.call_args == mocker.call()
        assert ret_val == mock_http_runtime_operations.receive_feedback_notification()


@pytest.mark.describe("IoTHubHttpRuntimeManager - .complete_feedback_notification()")
class TestCompleteFeedbackNotification(object):
    @pytest.mark.it("Uses protocol layer HTTP runtime to complete feedback notifications")
    def test_complete_feedback_notification(
        self, mocker, mock_http_runtime_operations, iothub_http_runtime_manager
    ):
        ret_val = iothub_http_runtime_manager.complete_feedback_notification(fake_lock_token)
        assert mock_http_runtime_operations.complete_feedback_notification.call_count == 1
        assert mock_http_runtime_operations.complete_feedback_notification.call_args == mocker.call(
            fake_lock_token
        )
        assert ret_val == mock_http_runtime_operations.complete_feedback_notification()


@pytest.mark.describe("IoTHubHttpRuntimeManager - .abandon_feedback_notification()")
class TestAbandonFeedbackNotification(object):
    @pytest.mark.it("Uses protocol layer HTTP runtime to abandon feedback notifications")
    def test_abandon_feedback_notification(
        self, mocker, mock_http_runtime_operations, iothub_http_runtime_manager
    ):
        ret_val = iothub_http_runtime_manager.abandon_feedback_notification(fake_lock_token)
        assert mock_http_runtime_operations.abandon_feedback_notification.call_count == 1
        assert mock_http_runtime_operations.abandon_feedback_notification.call_args == mocker.call(
            fake_lock_token
        )
        assert ret_val == mock_http_runtime_operations.abandon_feedback_notification()
