# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

from azure.iot.hub.devicesdk.internal_client import InternalClient
from azure.iot.hub.devicesdk.device_client import DeviceClient
from azure.iot.hub.devicesdk.module_client import ModuleClient
from azure.iot.hub.devicesdk.auth.authentication_provider_factory import from_connection_string
from azure.iot.hub.devicesdk.transport.abstract_transport import AbstractTransport
import pytest

from six import add_move, MovedModule

add_move(MovedModule("mock", "mock", "unittest.mock"))
from six.moves import mock
from mock import MagicMock


connection_string_format = "HostName={};DeviceId={};SharedAccessKey={}"
shared_access_key = "Zm9vYmFy"
hostname = "beauxbatons.academy-net"
device_id = "MyPensieve"


@pytest.fixture(scope="module")
def connection_string():
    connection_string = connection_string_format.format(hostname, device_id, shared_access_key)
    return connection_string


@pytest.fixture(scope="function")
def authentication_provider(connection_string):
    auth_provider = from_connection_string(connection_string)
    return auth_provider

@pytest.fixture(scope="function")
def mock_transport():
    return MagicMock(spec=AbstractTransport)


def test_internal_client_connect_in_turn_calls_transport_connect(authentication_provider, mock_transport):
    client = InternalClient(authentication_provider, mock_transport)

    client.connect()

    mock_transport.connect.assert_called_once_with()


def test_connected_state_handler_called_wth_new_state_once_transport_gets_connected(mocker, authentication_provider, mock_transport):
    client = InternalClient(authentication_provider, mock_transport)
    stub_on_connection_state = mocker.stub(name="on_connection_state")
    client.on_connection_state = stub_on_connection_state

    client.connect()
    mock_transport.on_transport_connected("connected")

    assert client.state == "connected"
    stub_on_connection_state.assert_called_once_with("connected")

def test_connected_state_handler_called_wth_new_state_once_transport_gets_connected(mocker, authentication_provider, mock_transport):
    client = InternalClient(authentication_provider, mock_transport)
    stub_on_connection_state = mocker.stub(name="on_connection_state")
    client.on_connection_state = stub_on_connection_state

    client.connect()
    mock_transport.on_transport_connected("connected")

    stub_on_connection_state.reset_mock()

    client.disconnect()
    mock_transport.on_transport_disconnected("disconnected")

    assert client.state == "disconnected"
    stub_on_connection_state.assert_called_once_with("disconnected")

def test_internal_client_send_event_in_turn_calls_transport_send_event(authentication_provider, mock_transport):

    event = "Levicorpus"
    client = InternalClient(authentication_provider, mock_transport)
    client.state = "connected"
    client.connect()
    client.send_event(event)

    mock_transport.send_event.assert_called_once_with(event)


def test_transport_any_error_surfaces_to_internal_client(authentication_provider, mock_transport):
    mock_transport.send_event.side_effect = RuntimeError("Some runtime error happened")

    event = "Caput Draconis"
    client = InternalClient(authentication_provider, mock_transport)
    client.state = "connected"
    client.connect()
    with pytest.raises(RuntimeError, match="Some runtime error happened"):
        client.send_event(event)

    mock_transport.send_event.assert_called_once_with(event)


@pytest.mark.parametrize("kind_of_client, auth", [
    ("Module", authentication_provider),
    ("Device", authentication_provider),
])
def test_client_gets_created_correctly(mocker, kind_of_client, auth, mock_transport):
    mock_constructor_transport = mocker.patch("azure.iot.hub.devicesdk.internal_client.MQTTTransport")
    mock_constructor_transport.return_value = mock_transport

    if kind_of_client == "Module":
        module_client = ModuleClient.from_authentication_provider(authentication_provider, "mqtt")

        assert module_client._auth_provider == authentication_provider
        assert module_client._transport == mock_transport
        assert isinstance(module_client, ModuleClient)

    else:
        device_client = DeviceClient.from_authentication_provider(authentication_provider, "mqtt")

        assert device_client._auth_provider == authentication_provider
        assert device_client._transport == mock_transport
        assert isinstance(device_client, DeviceClient)


@pytest.mark.parametrize("kind_of_client, auth", [
    ("Module", authentication_provider),
    ("Device", authentication_provider),
])
def test_raises_on_creation_of_client_when_transport_is_incorrect(kind_of_client, auth):
    with pytest.raises(NotImplementedError, match="No specific transport can be instantiated based on the choice."):
        if kind_of_client == "Module":
            ModuleClient.from_authentication_provider(authentication_provider, "floo")
        else:
            DeviceClient.from_authentication_provider(authentication_provider, "floo")
