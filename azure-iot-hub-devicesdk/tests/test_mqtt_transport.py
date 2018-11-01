# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

import pytest
from azure.iot.hub.devicesdk.transport.mqtt.mqtt_transport import MQTTTransport
from azure.iot.hub.devicesdk.transport.mqtt.mqtt_provider import MQTTProvider
from azure.iot.hub.devicesdk.auth.authentication_provider_factory import from_connection_string
from six import add_move, MovedModule

add_move(MovedModule("mock", "mock", "unittest.mock"))
from six.moves import mock
from mock import MagicMock


connection_string_format = "HostName={};DeviceId={};SharedAccessKey={}"
fake_shared_access_key = "Zm9vYmFy"
fake_hostname = "beauxbatons.academy-net"
fake_device_id = "MyPensieve"


@pytest.fixture(scope="module")
def authentication_provider():
    connection_string = connection_string_format.format(fake_hostname, fake_device_id, fake_shared_access_key)
    auth_provider = from_connection_string(connection_string)
    return auth_provider


@pytest.fixture(scope="module")
def transport(authentication_provider):
    transport = MQTTTransport(authentication_provider)
    return transport


def test_instantiation_creates_proper_transport():
    connection_string = connection_string_format.format(fake_hostname, fake_device_id, fake_shared_access_key)
    authentication_provider = from_connection_string(connection_string)
    trans = MQTTTransport(authentication_provider)
    assert trans._auth_provider == authentication_provider
    assert trans._mqtt_provider is None


def test_connect_in_turn_calls_connect_on_provider(mocker, transport):
    mock_mqtt_provider = MagicMock(spec=MQTTProvider)
    mock_mqtt_provider_constructor = mocker.patch(
        "azure.iot.hub.devicesdk.transport.mqtt.mqtt_transport.MQTTProvider"
    )
    mock_mqtt_provider_constructor.return_value = mock_mqtt_provider

    mocker.patch.object(mock_mqtt_provider, "connect")

    transport.connect()
    mock_mqtt_provider.connect.assert_called_once_with()


def test_sendevent_in_turn_calls_publish_on_provider(mocker, transport):
    topic = "devices/" + fake_device_id + "/messages/events/"
    event = "Wingardian Leviosa"

    mock_mqtt_provider = MagicMock(spec=MQTTProvider)
    mock_mqtt_provider_constructor = mocker.patch(
        "azure.iot.hub.devicesdk.transport.mqtt.mqtt_transport.MQTTProvider"
    )
    mock_mqtt_provider_constructor.return_value = mock_mqtt_provider
    mocker.patch.object(mock_mqtt_provider, "connect")
    mocker.patch.object(mock_mqtt_provider, "publish")

    transport.connect()
    transport.send_event(event)

    mock_mqtt_provider.connect.assert_called_once_with()
    mock_mqtt_provider.publish.assert_called_once_with(topic, event)


def test_disconnect_in_turn_calls_disconnect_on_provider(mocker, transport):
    mock_mqtt_provider = MagicMock(spec=MQTTProvider)
    mock_mqtt_provider_constructor = mocker.patch(
        "azure.iot.hub.devicesdk.transport.mqtt.mqtt_transport.MQTTProvider"
    )
    mock_mqtt_provider_constructor.return_value = mock_mqtt_provider
    mocker.patch.object(mock_mqtt_provider, "disconnect")

    transport.connect()
    transport.disconnect()

    mock_mqtt_provider.disconnect.assert_called_once_with()


def test_connected_state_handler_called_wth_new_state_once_provider_gets_connected(mocker, transport):
    mock_mqtt_provider = MagicMock(spec=MQTTProvider)
    mock_mqtt_provider_constructor = mocker.patch(
        "azure.iot.hub.devicesdk.transport.mqtt.mqtt_transport.MQTTProvider"
    )
    mock_mqtt_provider_constructor.return_value = mock_mqtt_provider
    mocker.patch.object(mock_mqtt_provider, "connect")

    stub_on_transport_connected = mocker.stub(name="on_transport_connected")
    transport.on_transport_connected = stub_on_transport_connected

    fake_new_state = "noiseless_blackness"
    transport.connect()
    mock_mqtt_provider.on_mqtt_connected(fake_new_state)

    stub_on_transport_connected.assert_called_once_with(fake_new_state)
