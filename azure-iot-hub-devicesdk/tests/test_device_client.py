# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

from azure.iot.hub.devicesdk.device_client import DeviceClient
from azure.iot.hub.devicesdk.auth.authentication_provider_factory import from_connection_string
from azure.iot.hub.devicesdk.transport.mqtt.mqtt_transport import MQTTTransport
import pytest

from six import add_move, MovedModule

add_move(MovedModule("mock", "mock", "unittest.mock"))
from six.moves import mock
from mock import MagicMock


connection_string_format = "HostName={};DeviceId={};SharedAccessKey={}"
shared_access_key = "Zm9vYmFy"
hostname = "beauxbatons.academy-net"
device_id = "MyPensieve"


@pytest.fixture
def connection_string():
    connection_string = connection_string_format.format(hostname, device_id, shared_access_key)
    return connection_string


@pytest.fixture
def authentication_provider(connection_string):
    auth_provider = from_connection_string(connection_string)
    return auth_provider


def test_device_client_connect_in_turn_calls_transport_connect(authentication_provider):
    mock_transport = MagicMock(spec=MQTTTransport)
    device_client = DeviceClient(authentication_provider, mock_transport)

    device_client.connect()

    mock_transport.connect.assert_called_once_with()


def test_device_client_get_transport_state_callback_calls_on_connection_state_handler(mocker, authentication_provider):
    stub_on_connection_state = mocker.stub(name="on_connection_state")

    mock_transport = MQTTTransport(authentication_provider)
    device_client = DeviceClient(authentication_provider, mock_transport)
    device_client.on_connection_state = stub_on_connection_state

    new_state = "apparating"
    device_client._get_transport_connected_state_callback(new_state)

    stub_on_connection_state.assert_called_once_with(new_state)


def test_device_client_emit_connection_status_calls_on_connection_state_handler(mocker, authentication_provider):
    stub_on_connection_state = mocker.stub(name="on_connection_state")

    mock_transport = MQTTTransport(authentication_provider)
    device_client = DeviceClient(authentication_provider, mock_transport)
    device_client.on_connection_state = stub_on_connection_state
    new_state = "apparating"
    device_client.state = new_state

    device_client._emit_connection_status()

    stub_on_connection_state.assert_called_once_with(new_state)


def test_device_client_send_event_in_turn_calls_transport_send_event(authentication_provider):
    mock_transport = MagicMock(spec=MQTTTransport)

    event = "Levicorpus"
    device_client = DeviceClient(authentication_provider, mock_transport)
    device_client.state = "connected"
    device_client.connect()
    device_client.send_event(event)

    mock_transport.send_event.assert_called_once_with(event)


def test_transport_any_error_surfaces_to_device_client(authentication_provider):
    mock_transport = MagicMock(spec=MQTTTransport)
    mock_transport.send_event.side_effect = RuntimeError("Some runtime error happened")

    event = "Caput Draconis"
    device_client = DeviceClient(authentication_provider, mock_transport)
    device_client.state = "connected"
    device_client.connect()
    with pytest.raises(RuntimeError, match="Some runtime error happened"):
        device_client.send_event(event)

    mock_transport.send_event.assert_called_once_with(event)
