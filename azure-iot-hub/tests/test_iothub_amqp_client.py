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
from uamqp import utils, errors
from azure.iot.hub.iothub_amqp_client import IoTHubAmqpClient

try:
    from urllib import quote, quote_plus, urlencode  # Py2
except Exception:
    from urllib.parse import quote, quote_plus, urlencode

"""---Constants---"""

fake_shared_access_key = "Zm9vYmFy"
fake_shared_access_key_name = "test_key_name"
fake_hostname = "hostname.mytest-net"
fake_device_id = "device_id"
fake_message = "fake_message"

"""----Shared fixtures----"""


@pytest.fixture(scope="function", autouse=True)
def mock_uamqp_SendClient(mocker):
    mock_uamqp_SendClient = mocker.patch.object(uamqp, "SendClient")
    return mock_uamqp_SendClient


@pytest.mark.describe("IoTHubAmqpClient - .send_message_to_device()")
class TestSendMessageToDevice(object):
    @pytest.mark.it("Send Message To Device")
    def test_send_message_to_device(self, mocker, mock_uamqp_SendClient):
        iothub_amqp_client = IoTHubAmqpClient(
            fake_hostname, fake_shared_access_key_name, fake_shared_access_key
        )
        iothub_amqp_client.send_message_to_device(fake_device_id, fake_message)
        amqp_client_obj = mock_uamqp_SendClient.return_value

        assert amqp_client_obj.queue_message.call_count == 1
        assert amqp_client_obj.send_all_messages.call_count == 1

    @pytest.mark.it("Raises an Exception if send_all_messages Fails")
    def test_raise_exception_on_send_fail(self, mocker, mock_uamqp_SendClient):
        iothub_amqp_client = IoTHubAmqpClient(
            fake_hostname, fake_shared_access_key_name, fake_shared_access_key
        )
        amqp_client_obj = mock_uamqp_SendClient.return_value
        mocker.patch.object(
            amqp_client_obj, "send_all_messages", {uamqp.constants.MessageState.SendFailed}
        )
        with pytest.raises(Exception):
            iothub_amqp_client.send_message_to_device(fake_device_id, fake_message)
