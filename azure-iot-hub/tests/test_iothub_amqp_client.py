# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
import time
import base64
import hmac
import hashlib
import copy
import logging
import uamqp
import azure.identity
from azure.iot.hub.iothub_amqp_client import (
    IoTHubAmqpClientSharedAccessKeyAuth,
    IoTHubAmqpClientTokenAuth,
)

try:
    from urllib import quote, quote_plus, urlencode  # Py2
except Exception:
    from urllib.parse import quote, quote_plus, urlencode

"""---Constants---"""

fake_shared_access_key = "Zm9vYmFy"
fake_token_scope = "https://token.net/.default"
fake_shared_access_key_name = "test_key_name"
fake_hostname = "hostname.mytest.net"
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
fake_empty_prop = {}
"""----Shared fixtures----"""


@pytest.fixture(scope="function", autouse=True)
def mock_uamqp_SendClient(mocker):
    mock_uamqp_SendClient = mocker.patch.object(uamqp, "SendClient")
    return mock_uamqp_SendClient


@pytest.fixture(scope="function", autouse=True)
def mock_azure_identity_DefaultAzureCredential(mocker):
    mock_azure_identity_DefaultAzureCredential = mocker.patch.object(
        azure.identity, "DefaultAzureCredential"
    )
    return mock_azure_identity_DefaultAzureCredential


@pytest.mark.describe("IoTHubAmqpClientSharedAccessKeyAuth - Amqp Client Connections")
class TestIoTHubAmqpClientSharedAccessKeyAuth(object):
    @pytest.mark.it("Send Message To Device")
    def test_send_message_to_device(self, mocker, mock_uamqp_SendClient):
        iothub_amqp_client = IoTHubAmqpClientSharedAccessKeyAuth(
            fake_hostname, fake_shared_access_key_name, fake_shared_access_key
        )
        iothub_amqp_client.send_message_to_device(fake_device_id, fake_message, fake_app_prop)
        amqp_client_obj = mock_uamqp_SendClient.return_value

        assert amqp_client_obj.queue_message.call_count == 1
        assert amqp_client_obj.send_all_messages.call_count == 1

    @pytest.mark.it("Send Message To Device system prop")
    def test_send_message_to_device_sys_props(self, mocker, mock_uamqp_SendClient):
        iothub_amqp_client = IoTHubAmqpClientSharedAccessKeyAuth(
            fake_hostname, fake_shared_access_key_name, fake_shared_access_key
        )
        iothub_amqp_client.send_message_to_device(fake_device_id, fake_message, fake_sys_prop)
        amqp_client_obj = mock_uamqp_SendClient.return_value

        assert amqp_client_obj.queue_message.call_count == 1
        assert amqp_client_obj.send_all_messages.call_count == 1

    @pytest.mark.it("Raises an Exception if send_all_messages Fails")
    def test_raise_exception_on_send_fail(self, mocker, mock_uamqp_SendClient):
        iothub_amqp_client = IoTHubAmqpClientSharedAccessKeyAuth(
            fake_hostname, fake_shared_access_key_name, fake_shared_access_key
        )
        amqp_client_obj = mock_uamqp_SendClient.return_value
        mocker.patch.object(
            amqp_client_obj, "send_all_messages", {uamqp.constants.MessageState.SendFailed}
        )
        with pytest.raises(Exception):
            iothub_amqp_client.send_message_to_device(fake_device_id, fake_message, fake_app_prop)

    @pytest.mark.it("Disconnect a Device")
    def test_disconnect_sync(self, mocker, mock_uamqp_SendClient):
        iothub_amqp_client = IoTHubAmqpClientSharedAccessKeyAuth(
            fake_hostname, fake_shared_access_key_name, fake_shared_access_key
        )
        amqp_client_obj = mock_uamqp_SendClient.return_value
        iothub_amqp_client.disconnect_sync()

        assert amqp_client_obj.close.call_count == 1


@pytest.mark.describe("IoTHubAmqpClientTokenAuth - Amqp Client Connections")
class TestIoTHubAmqpClientTokenAuth(object):
    @pytest.mark.it("Get Token From TokenCredential Object")
    def test_get_token_from_token_credential_object(
        self, mock_azure_identity_DefaultAzureCredential
    ):
        IoTHubAmqpClientTokenAuth(
            fake_hostname, azure.identity.DefaultAzureCredential(), fake_token_scope
        )
        token_credential_obj = mock_azure_identity_DefaultAzureCredential.return_value
        token_credential_obj.get_token.assert_called_once_with(fake_token_scope)

    @pytest.mark.it("Send Message To Device")
    def test_send_message_to_device(
        self, mocker, mock_uamqp_SendClient, mock_azure_identity_DefaultAzureCredential
    ):
        iothub_amqp_client = IoTHubAmqpClientTokenAuth(
            fake_hostname, azure.identity.DefaultAzureCredential(), fake_token_scope
        )
        iothub_amqp_client.send_message_to_device(fake_device_id, fake_message, fake_app_prop)
        amqp_client_obj = mock_uamqp_SendClient.return_value

        assert amqp_client_obj.queue_message.call_count == 1
        assert amqp_client_obj.send_all_messages.call_count == 1

    @pytest.mark.it("Send Message To Device system prop")
    def test_send_message_to_device_sys_props(self, mocker, mock_uamqp_SendClient):
        iothub_amqp_client = IoTHubAmqpClientTokenAuth(
            fake_hostname, azure.identity.DefaultAzureCredential()
        )
        iothub_amqp_client.send_message_to_device(fake_device_id, fake_message, fake_sys_prop)
        amqp_client_obj = mock_uamqp_SendClient.return_value

        assert amqp_client_obj.queue_message.call_count == 1
        assert amqp_client_obj.send_all_messages.call_count == 1

    @pytest.mark.it("Raises an Exception if send_all_messages Fails")
    def test_raise_exception_on_send_fail(self, mocker, mock_uamqp_SendClient):
        iothub_amqp_client = IoTHubAmqpClientTokenAuth(
            fake_hostname, azure.identity.DefaultAzureCredential()
        )
        amqp_client_obj = mock_uamqp_SendClient.return_value
        mocker.patch.object(
            amqp_client_obj, "send_all_messages", {uamqp.constants.MessageState.SendFailed}
        )
        with pytest.raises(Exception):
            iothub_amqp_client.send_message_to_device(fake_device_id, fake_message, fake_app_prop)

    @pytest.mark.it("Disconnect a Device")
    def test_disconnect_sync(self, mocker, mock_uamqp_SendClient):
        iothub_amqp_client = IoTHubAmqpClientTokenAuth(
            fake_hostname, azure.identity.DefaultAzureCredential()
        )
        amqp_client_obj = mock_uamqp_SendClient.return_value
        iothub_amqp_client.disconnect_sync()

        assert amqp_client_obj.close.call_count == 1
