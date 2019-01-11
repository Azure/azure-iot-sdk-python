# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

from azure.iot.hub.devicesdk.module_client import ModuleClient
from azure.iot.hub.devicesdk.auth.authentication_provider_factory import from_connection_string
from azure.iot.hub.devicesdk.transport.abstract_transport import AbstractTransport
from azure.iot.hub.devicesdk.message import Message
import pytest
from mock import MagicMock, patch
import azure.iot.hub.devicesdk.message

# import azure.iot.hub.devicesdk.message as mes

connection_string_format = "HostName={};DeviceId={};ModuleId={};SharedAccessKey={}"
shared_access_key = "Zm9vYmFy"
hostname = "beauxbatons.academy-net"
device_id = "MyPensieve"
module_id = "MemoryCharms"


@pytest.fixture(scope="module")
def connection_string():
    connection_string = connection_string_format.format(
        hostname, device_id, module_id, shared_access_key
    )
    return connection_string


@pytest.fixture(scope="function")
def authentication_provider(connection_string):
    auth_provider = from_connection_string(connection_string)
    return auth_provider


class FakeTransport(AbstractTransport):
    def __init__(self, auth_provider):
        pass

    def connect(self, callback):
        callback()

    def send_event(self, event, callback):
        callback()

    def send_output_event(self, event, callback):
        callback()

    def disconnect(self, callback):
        callback()


@pytest.fixture(scope="function")
def mock_transport(authentication_provider):
    return MagicMock(wraps=FakeTransport(authentication_provider))


def test_module_client_send_to_output_assigns_output_name_and_in_turn_calls_transport_send_event(
    authentication_provider, mock_transport
):
    output_name = "fake_output_name"
    event = Message("Levicorpus")
    client = ModuleClient(authentication_provider, mock_transport)
    client.connect()
    client.send_to_output(event, output_name)

    assert event.output_name == output_name
    assert mock_transport.send_output_event.call_count == 1
    assert mock_transport.send_output_event.call_args[0][0] == event


@patch("azure.iot.hub.devicesdk.module_client.isinstance")
@patch("azure.iot.hub.devicesdk.module_client.Message")
def test_module_client_send_string_constructs_message_assigns_output_name_and_calls_transport(
    mock_message_constructor, mock_instance_method, authentication_provider, mock_transport
):
    mock_instance_method.return_value = False

    output_name = "fake_output_name"
    event = "Levicorpus"
    client = ModuleClient(authentication_provider, mock_transport)
    client.connect()
    client.send_to_output(event, output_name)

    assert mock_message_constructor.return_value.output_name == output_name
    assert mock_transport.send_output_event.call_count == 1
    assert mock_transport.send_output_event.call_args[0][0] == mock_message_constructor.return_value
