# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

from azure.iot.hub.devicesdk.device_client import DeviceClient
from azure.iot.hub.devicesdk.symmetric_key_authentication_provider import (
    SymmetricKeyAuthenticationProvider,
)
from azure.iot.hub.devicesdk.transport.mqtt.mqtt_transport import MQTTTransport
from azure.iot.hub.devicesdk.transport.transport_config import TransportConfig, TransportProtocol
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
    auth_provider = SymmetricKeyAuthenticationProvider.create_authentication_from_connection_string(
        connection_string
    )
    return auth_provider


@pytest.fixture
def mqtt_transport_config():
    return TransportConfig(TransportProtocol.MQTT)


def test_create_from_incomplete_connection_string():
    with pytest.raises(ValueError, match="Invalid Connection String - Incomplete"):
        connection_string = "HostName=beauxbatons.academy-net;SharedAccessKey=Zm9vYmFy"
        DeviceClient.create_from_connection_string(connection_string, mqtt_transport_config)


def test_create_from_duplicatekeys_connection_string():
    with pytest.raises(ValueError, match="Invalid Connection String - Unable to parse"):
        connection_string = (
            "HostName=beauxbatons.academy-net;HostName=TheDeluminator;HostName=Zm9vYmFy"
        )
        DeviceClient.create_from_connection_string(connection_string, mqtt_transport_config)


# Without the proper delimiter the dictionary function itself can't take place
def test_create_from_badparsing_connection_string():
    with pytest.raises(ValueError):
        connection_string = "HostName+beauxbatons.academy-net!DeviceId+TheDeluminator!"
        DeviceClient.create_from_connection_string(connection_string, mqtt_transport_config)


def test_create_from_badkeys_connection_string():
    with pytest.raises(ValueError, match="Invalid Connection String - Invalid Key"):
        connection_string = "BadHostName=beauxbatons.academy-net;BadDeviceId=TheDeluminator;SharedAccessKey=Zm9vYmFy"
        DeviceClient.create_from_connection_string(connection_string, mqtt_transport_config)


def test_static(connection_string, mqtt_transport_config):
    device_client = DeviceClient.create_from_connection_string(
        connection_string, mqtt_transport_config
    )

    assert device_client._transport_config == mqtt_transport_config
    assert device_client.state == "initial"
    assert device_client._transport is None


def test_connect(mocker, authentication_provider, mqtt_transport_config):
    mocker.patch.object(DeviceClient, "_emit_connection_status")
    mocker.patch.object(MQTTTransport, "connect")

    device_client = DeviceClient(authentication_provider, mqtt_transport_config)
    assert device_client.state == "initial"
    assert device_client._transport is None

    device_client.connect()

    assert isinstance(device_client._transport, MQTTTransport)

    MQTTTransport.connect.assert_called_once_with()
    DeviceClient._emit_connection_status.assert_called_once_with()


def test_get_transport_state(mocker, mqtt_transport_config):
    stub_on_connection_state = mocker.stub(name="on_connection_state")

    device_client = DeviceClient(authentication_provider, mqtt_transport_config)
    device_client.on_connection_state = stub_on_connection_state

    new_state = "apparating"
    device_client._get_transport_connected_state_callback(new_state)

    stub_on_connection_state.assert_called_once_with(new_state)


def test_emit_connection_status(mocker, mqtt_transport_config):
    stub_on_connection_state = mocker.stub(name="on_connection_state")

    device_client = DeviceClient(authentication_provider, mqtt_transport_config)
    device_client.on_connection_state = stub_on_connection_state
    new_state = "apparating"
    device_client.state = new_state

    device_client._emit_connection_status()

    stub_on_connection_state.assert_called_once_with(new_state)


def test_send_event_magic_mock(mocker, authentication_provider, mqtt_transport_config):
    mock_transport = MagicMock(spec=MQTTTransport)
    mock_transport_config = mocker.patch.object(TransportConfig, "get_specific_transport")
    mock_transport_config.return_value = mock_transport

    mocker.patch.object(mock_transport, "send_event")
    mocker.patch.object(DeviceClient, "_emit_connection_status")

    event = "Caput Draconis"
    device_client = DeviceClient(authentication_provider, mqtt_transport_config)
    assert device_client.state == "initial"
    assert device_client._transport is None
    device_client.state = "connected"
    device_client.connect()
    device_client.send_event(event)

    TransportConfig.get_specific_transport.assert_called_once_with(authentication_provider)
    mock_transport.send_event.assert_called_once_with(event)
    DeviceClient._emit_connection_status.assert_called_once_with()


def test_send_event_error(mocker, authentication_provider, mqtt_transport_config):
    mocker.patch.object(TransportConfig, "get_specific_transport")
    mocker.patch.object(DeviceClient, "_emit_connection_status")

    with pytest.raises(ValueError, match="No connection present to send event."):
        event = "Caput Draconis"
        device_client = DeviceClient(authentication_provider, mqtt_transport_config)
        assert device_client.state == "initial"
        assert device_client._transport is None
        device_client.state = "disconnected"
        device_client.connect()
        device_client.send_event(event)

    TransportConfig.get_specific_transport.assert_called_once_with(authentication_provider)
