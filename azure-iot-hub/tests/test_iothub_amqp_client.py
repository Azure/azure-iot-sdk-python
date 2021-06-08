# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
import uamqp
from azure.core.credentials import AccessToken
from azure.iot.hub.iothub_amqp_client import (
    IoTHubAmqpClientSharedAccessKeyAuth,
    IoTHubAmqpClientTokenAuth,
)

"""---Constants---"""
fake_device_id = "device_id"
fake_message = "fake_message"
fake_app_prop = {"fake_prop1": "fake_value1"}
fake_sys_prop = {
    "contentType": "value1",
    "contentEncoding": "value2",
    "correlationId": "value3",
    "expiryTimeUtc": 1584727659,
    "messageId": 42,
}
fake_hostname = "hostname.mytest.net"
fake_shared_access_key_name = "test_key_name"
fake_shared_access_key = "Zm9vYmFy"
fake_token_scope = "https://token.net/.default"
fake_token = "fasdjkhg"
fake_token_expiry = 1584727659


class SharedAmqpClientTests(object):
    @pytest.fixture(autouse=True)
    def mock_uamqp_SendClient(self, mocker):
        mock_uamqp_SendClient = mocker.patch.object(uamqp, "SendClient")
        return mock_uamqp_SendClient

    @pytest.mark.it("Sends messages with application properties using the uamqp SendClient")
    def test_send_message_to_device_app_prop(self, client, mock_uamqp_SendClient):
        client.send_message_to_device(fake_device_id, fake_message, fake_app_prop)
        amqp_client_obj = mock_uamqp_SendClient.return_value

        assert amqp_client_obj.queue_message.call_count == 1
        assert amqp_client_obj.send_all_messages.call_count == 1

    @pytest.mark.it("Sends messages with system properties using the uamqp SendClient")
    def test_send_message_to_device_sys_prop(self, client, mock_uamqp_SendClient):
        client.send_message_to_device(fake_device_id, fake_message, fake_sys_prop)
        amqp_client_obj = mock_uamqp_SendClient.return_value

        assert amqp_client_obj.queue_message.call_count == 1
        assert amqp_client_obj.send_all_messages.call_count == 1

    @pytest.mark.it("Raises an Exception if send_all_messages fails")
    def test_raise_exception_on_send_fail(self, client, mocker, mock_uamqp_SendClient):
        amqp_client_obj = mock_uamqp_SendClient.return_value
        mocker.patch.object(
            amqp_client_obj, "send_all_messages", {uamqp.constants.MessageState.SendFailed}
        )
        with pytest.raises(Exception):
            client.send_message_to_device(fake_device_id, fake_message, fake_app_prop)

    @pytest.mark.it("Calls close() on the uamqp SendClient when disconnect_sync() is called")
    def test_disconnect_sync(self, client, mock_uamqp_SendClient):
        amqp_client_obj = mock_uamqp_SendClient.return_value
        client.disconnect_sync()

        assert amqp_client_obj.close.call_count == 1


#############################################
# IoTHubAmqpClientSharedAccessKeyAuth Tests #
#############################################


class IoTHubAmqpClientSharedAccessKeyAuthTestConfig(object):
    @pytest.fixture
    def required_kwargs(self):
        return {
            "hostname": fake_hostname,
            "shared_access_key_name": fake_shared_access_key_name,
            "shared_access_key": fake_shared_access_key,
        }

    @pytest.fixture
    def client(self, required_kwargs):
        return IoTHubAmqpClientSharedAccessKeyAuth(**required_kwargs)


@pytest.mark.describe("IoTHubAmqpClientSharedAccessKeyAuth")
class TestIoTHubAmqpClientSharedAccessKeyAuth(
    IoTHubAmqpClientSharedAccessKeyAuthTestConfig, SharedAmqpClientTests
):
    pass


###################################
# IoTHubAmqpClientTokenAuth Tests #
###################################


class IoTHubAmqpClientTokenAuthTestConfig(object):
    @pytest.fixture
    def mock_azure_identity_TokenCredential(self, mocker):
        mock = mocker.Mock()
        mock.get_token.return_value = AccessToken(fake_token, fake_token_expiry)
        return mock

    @pytest.fixture
    def required_kwargs(self, mock_azure_identity_TokenCredential):
        return {
            "hostname": fake_hostname,
            "token_credential": mock_azure_identity_TokenCredential,
            "token_scope": fake_token_scope,
        }

    @pytest.fixture
    def client(self, required_kwargs):
        return IoTHubAmqpClientTokenAuth(**required_kwargs)


@pytest.mark.describe("IoTHubAmqpClientTokenAuth")
class TestIoTHubAmqpClientTokenAuth(IoTHubAmqpClientTokenAuthTestConfig, SharedAmqpClientTests):
    @pytest.mark.it("Gets the token from the TokenCredential object")
    def test_get_token_from_token_credential_object(self, mock_azure_identity_TokenCredential):
        IoTHubAmqpClientTokenAuth(
            fake_hostname, mock_azure_identity_TokenCredential, fake_token_scope
        )
        mock_azure_identity_TokenCredential.get_token.assert_called_once_with(fake_token_scope)
