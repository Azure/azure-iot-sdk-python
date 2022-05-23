# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import base64
import hashlib
import pytest
import uamqp
import hmac
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


@pytest.fixture(autouse=True)
def mock_uamqp_SendClient(mocker):
    mock_uamqp_SendClient = mocker.patch.object(uamqp, "SendClient")
    return mock_uamqp_SendClient


class SharedIotHubAmqpClientSendMessageToDeviceTests(object):
    @pytest.mark.it("Sends messages with application properties using the uamqp SendClient")
    def test_send_message_to_device_app_prop(self, client, mocker, mock_uamqp_SendClient):
        client.send_message_to_device(fake_device_id, fake_message, fake_app_prop)
        amqp_client_obj = mock_uamqp_SendClient.return_value

        # Message was queued
        assert amqp_client_obj.queue_message.call_count == 1
        msg_obj = amqp_client_obj.queue_message.call_args[0][0]
        # Message was configured with properties and destination
        assert str(msg_obj) == fake_message
        assert msg_obj.properties.to == bytes(
            str("/devices/" + fake_device_id + "/messages/devicebound").encode("utf-8")
        )
        assert msg_obj.application_properties == fake_app_prop
        # Message was sent
        assert amqp_client_obj.send_all_messages.call_count == 1
        assert amqp_client_obj.send_all_messages.call_args == mocker.call(close_on_done=False)

    @pytest.mark.it("Sends messages with system properties using the uamqp SendClient")
    def test_send_message_to_device_sys_prop(self, client, mocker, mock_uamqp_SendClient):
        client.send_message_to_device(fake_device_id, fake_message, fake_sys_prop)
        amqp_client_obj = mock_uamqp_SendClient.return_value

        # Message was queued
        assert amqp_client_obj.queue_message.call_count == 1
        msg_obj = amqp_client_obj.queue_message.call_args[0][0]
        # Message was configured with properties and destination
        assert str(msg_obj) == fake_message
        assert msg_obj.properties.to == bytes(
            str("/devices/" + fake_device_id + "/messages/devicebound").encode("utf-8")
        )
        assert msg_obj.application_properties == {}
        assert msg_obj.properties.content_type == bytes(
            str(fake_sys_prop["contentType"]).encode("utf-8")
        )
        assert msg_obj.properties.content_encoding == bytes(
            str(fake_sys_prop["contentEncoding"]).encode("utf-8")
        )
        assert msg_obj.properties.correlation_id == bytes(
            str(fake_sys_prop["correlationId"]).encode("utf-8")
        )
        assert msg_obj.properties.absolute_expiry_time == fake_sys_prop["expiryTimeUtc"]
        assert msg_obj.properties.message_id == fake_sys_prop["messageId"]
        # Message was sent
        assert amqp_client_obj.send_all_messages.call_count == 1
        assert amqp_client_obj.send_all_messages.call_args == mocker.call(close_on_done=False)

    @pytest.mark.it("Raises an Exception if send_all_messages fails")
    def test_raise_exception_on_send_fail(self, client, mocker, mock_uamqp_SendClient):
        amqp_client_obj = mock_uamqp_SendClient.return_value
        mocker.patch.object(
            amqp_client_obj, "send_all_messages", {uamqp.constants.MessageState.SendFailed}
        )
        with pytest.raises(Exception):
            client.send_message_to_device(fake_device_id, fake_message, fake_app_prop)


class SharedIotHubAmqpClientDisconnectSyncTests(object):
    @pytest.mark.it(
        "Calls close() on the uamqp SendClient and removes it when disconnect_sync() is called"
    )
    def test_disconnect_sync(self, client, mock_uamqp_SendClient):
        assert client.amqp_client is not None
        amqp_client_obj = mock_uamqp_SendClient.return_value

        client.disconnect_sync()

        assert amqp_client_obj.close.call_count == 1
        assert client.amqp_client is None


#############################################
# IoTHubAmqpClientSharedAccessKeyAuth Tests #
#############################################


class IoTHubAmqpClientSharedAccessKeyAuthTestConfig(object):
    @pytest.fixture
    def client(self):
        return IoTHubAmqpClientSharedAccessKeyAuth(
            hostname=fake_hostname,
            shared_access_key_name=fake_shared_access_key_name,
            shared_access_key=fake_shared_access_key,
        )


@pytest.mark.describe("IoTHubAmqpClientSharedAccessKeyAuth - Instantiation")
class TestIoTHubAmqpClientSharedAccessKeyAuthInstantiation(
    IoTHubAmqpClientSharedAccessKeyAuthTestConfig
):
    @pytest.mark.it(
        "Creates a JWTTokenAuth instance with the correct parameters and uses it to create an AMQP SendClient"
    )
    def test_create_JWTTokenAuth_with_sas_token(self, mocker, mock_uamqp_SendClient):
        amqp_token_init_mock = mocker.patch.object(uamqp.authentication, "JWTTokenAuth")
        amqp_token_mock = amqp_token_init_mock.return_value

        IoTHubAmqpClientSharedAccessKeyAuth(
            fake_hostname, fake_shared_access_key_name, fake_shared_access_key
        )

        # JWTTokenAuth creation
        assert amqp_token_init_mock.call_count == 1
        assert amqp_token_init_mock.call_args[1]["uri"] == "https://" + fake_hostname
        assert amqp_token_init_mock.call_args[1]["audience"] == "https://" + fake_hostname
        assert amqp_token_init_mock.call_args[1]["token_type"] == b"servicebus.windows.net:sastoken"
        assert amqp_token_mock.update_token.call_count == 1

        # AMQP SendClient is created
        assert mock_uamqp_SendClient.call_count == 1
        expected_target = "amqps://" + fake_hostname + "/messages/devicebound"
        assert mock_uamqp_SendClient.call_args == mocker.call(
            target=expected_target, auth=amqp_token_mock, keep_alive_interval=120
        )

    @pytest.mark.it("Creates an HMAC to generate a shared access signature")
    def test_creates_hmac(self, mocker):
        hmac_mock = mocker.patch.object(hmac, "HMAC")
        hmac_digest_mock = hmac_mock.return_value.digest
        hmac_digest_mock.return_value = b"\xd2\x06\xf7\x12\xf1\xe9\x95$\x90\xfd\x12\x9a\xb1\xbe\xb4\xf8\xf3\xc4\x1ap\x8a\xab'\x8a.D\xfb\x84\x96\xca\xf3z"

        IoTHubAmqpClientSharedAccessKeyAuth(
            fake_hostname, fake_shared_access_key_name, fake_shared_access_key
        )

        assert hmac_mock.call_count == 1
        assert hmac_mock.call_args == mocker.call(
            base64.b64decode(fake_shared_access_key + "="), mocker.ANY, hashlib.sha256
        )

        assert hmac_digest_mock.call_count == 1


@pytest.mark.describe("IoTHubAmqpClientSharedAccessKeyAuth - .send_message_to_device()")
class TestIoTHubAmqpClientSharedAccessKeyAuthSendMessageToDevice(
    IoTHubAmqpClientSharedAccessKeyAuthTestConfig, SharedIotHubAmqpClientSendMessageToDeviceTests
):
    pass


@pytest.mark.describe("IoTHubAmqpClientSharedAccessKeyAuth - .disconnect_sync()")
class TestIoTHubAmqpClientSharedAccessKeyAuthDisconnectSync(
    IoTHubAmqpClientSharedAccessKeyAuthTestConfig, SharedIotHubAmqpClientDisconnectSyncTests
):
    pass


###################################
# IoTHubAmqpClientTokenAuth Tests #
###################################


class IoTHubAmqpClientTokenAuthTestConfig(object):
    @pytest.fixture
    def mock_azure_identity_TokenCredential(self, mocker):
        mock = mocker.MagicMock()
        mock.get_token.return_value = AccessToken(fake_token, fake_token_expiry)
        return mock

    @pytest.fixture
    def client(self, mock_azure_identity_TokenCredential):
        return IoTHubAmqpClientTokenAuth(
            hostname=fake_hostname,
            token_credential=mock_azure_identity_TokenCredential,
            token_scope=fake_token_scope,
        )


@pytest.mark.describe("IoTHubAmqpClientTokenAuth - Instantiation")
class TestIotHubAmqpClientTokenAuthInstantiation(IoTHubAmqpClientTokenAuthTestConfig):
    @pytest.mark.it(
        "Creates a JWTTokenAuth instance with the correct parameters and uses it to create an AMQP SendClient when a token scope is specified"
    )
    def test_create_JWTTokenAuth_with_bearer_token_custom_scope(
        self, mocker, mock_azure_identity_TokenCredential, mock_uamqp_SendClient
    ):
        amqp_token_init_mock = mocker.patch.object(uamqp.authentication, "JWTTokenAuth")
        amqp_token_mock = amqp_token_init_mock.return_value

        IoTHubAmqpClientTokenAuth(
            fake_hostname, mock_azure_identity_TokenCredential, token_scope=fake_token_scope
        )

        # JWTTokenAuth Creation
        assert amqp_token_init_mock.call_count == 1
        assert amqp_token_init_mock.call_args[1]["uri"] == "https://" + fake_hostname
        assert amqp_token_init_mock.call_args[1]["audience"] == fake_token_scope
        assert amqp_token_init_mock.call_args[1]["token_type"] == b"bearer"
        assert amqp_token_mock.update_token.call_count == 1

        # AMQP SendClient is created
        assert mock_uamqp_SendClient.call_count == 1
        expected_target = "amqps://" + fake_hostname + "/messages/devicebound"
        assert mock_uamqp_SendClient.call_args == mocker.call(
            target=expected_target, auth=amqp_token_mock, keep_alive_interval=120
        )

    @pytest.mark.it(
        "Creates a JWTTokenAuth instance with the correct parameters and uses it to create an AMQP SendClient if no token scope is provided (uses the default scope of 'https://iothubs.azure.net/.default')"
    )
    def test_create_JWTTokenAuth_with_bearer_token_default_scope(
        self, mocker, mock_azure_identity_TokenCredential, mock_uamqp_SendClient
    ):
        amqp_token_init_mock = mocker.patch.object(uamqp.authentication, "JWTTokenAuth")
        amqp_token_mock = amqp_token_init_mock.return_value

        IoTHubAmqpClientTokenAuth(fake_hostname, mock_azure_identity_TokenCredential)

        # JWTTokenAuth Creation
        assert amqp_token_init_mock.call_count == 1
        assert amqp_token_init_mock.call_args[1]["uri"] == "https://" + fake_hostname
        assert amqp_token_init_mock.call_args[1]["audience"] == "https://iothubs.azure.net/.default"
        assert amqp_token_init_mock.call_args[1]["token_type"] == b"bearer"
        assert amqp_token_mock.update_token.call_count == 1

        # AMQP SendClient is created
        assert mock_uamqp_SendClient.call_count == 1
        expected_target = "amqps://" + fake_hostname + "/messages/devicebound"
        assert mock_uamqp_SendClient.call_args == mocker.call(
            target=expected_target, auth=amqp_token_mock, keep_alive_interval=120
        )

    @pytest.mark.it(
        "Retrieves the token from the azure-identity TokenCredential using the specified token scope"
    )
    def test_retrieve_token_from_azure_identity(self, mock_azure_identity_TokenCredential):
        IoTHubAmqpClientTokenAuth(
            fake_hostname, mock_azure_identity_TokenCredential, fake_token_scope
        )
        mock_azure_identity_TokenCredential.get_token.assert_called_once_with(fake_token_scope)


@pytest.mark.describe("IoTHubAmqpClientTokenAuth - .send_message_to_device()")
class TestIoTHubAmqpClientTokenAuthSendMessageToDevice(
    IoTHubAmqpClientTokenAuthTestConfig, SharedIotHubAmqpClientSendMessageToDeviceTests
):
    pass


@pytest.mark.describe("IoTHubAmqpClientTokenAuth - .disconnect_sync()")
class TestIoTHubAmqpClientTokenAuthDisconnectSync(
    IoTHubAmqpClientTokenAuthTestConfig, SharedIotHubAmqpClientDisconnectSyncTests
):
    pass
