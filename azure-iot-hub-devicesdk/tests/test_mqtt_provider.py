# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

from azure.iot.hub.devicesdk.transport.mqtt.mqtt_provider import MQTTProvider
import paho.mqtt.client as mqtt
import os
import ssl
from six import add_move, MovedModule

add_move(MovedModule("mock", "mock", "unittest.mock"))
from six.moves import mock
from mock import MagicMock
from mock import patch


fake_hostname = "beauxbatons.academy-net"
fake_device_id = "MyFirebolt"
fake_password = "Fortuna Major"
fake_username = fake_hostname + "/" + fake_device_id


@patch.object(ssl, "SSLContext")
def test_connect_triggers_state_machine_connect_which_calls_on_enter_connecting(mock_ssl, mocker):
    mock_mqtt_client = MagicMock(spec=mqtt.Client)
    mock_constructor_mqtt_client = mocker.patch(
        "azure.iot.hub.devicesdk.transport.mqtt.mqtt_provider.mqtt.Client"
    )
    mock_constructor_mqtt_client.return_value = mock_mqtt_client

    mqtt_provider = MQTTProvider(fake_device_id, fake_hostname, fake_username, fake_password)
    mocker.patch.object(MQTTProvider, "_emit_connection_status")
    mqtt_provider.connect()

    MQTTProvider._emit_connection_status.assert_called_once_with()

    mock_constructor_mqtt_client.assert_called_once_with(fake_device_id, False, protocol=4)
    mock_ssl.assert_called_once_with(ssl.PROTOCOL_TLSv1_2)
    assert(mock_mqtt_client.tls_set_context.call_count == 1)
    context = mock_mqtt_client.tls_set_context.call_args[0][0]
    assert(context.check_hostname == True)
    assert(context.verify_mode == ssl.CERT_REQUIRED)
    context.load_default_certs.assert_called_once_with()
    mock_mqtt_client.tls_insecure_set.assert_called_once_with(False)
    mock_mqtt_client.connect.assert_called_once_with(host=fake_hostname, port=8883)
    mock_mqtt_client.loop_start.assert_called_once_with()

    assert mock_mqtt_client.on_connect is not None
    assert mock_mqtt_client.on_disconnect is not None
    assert mock_mqtt_client.on_publish is not None


def test_mqtt_client_connect_callback_triggers_state_machine_on_connect_which_calls_handler(mocker):
    mock_mqtt_client = MagicMock(spec=mqtt.Client)
    mock_constructor_mqtt_client = mocker.patch(
        "azure.iot.hub.devicesdk.transport.mqtt.mqtt_provider.mqtt.Client"
    )
    mock_constructor_mqtt_client.return_value = mock_mqtt_client

    mqtt_provider = MQTTProvider(fake_device_id, fake_hostname, fake_username, fake_password)
    stub_on_mqtt_connected = mocker.stub(name="on_mqtt_connected")
    mqtt_provider.on_mqtt_connected = stub_on_mqtt_connected

    mqtt_provider.connect()
    mock_mqtt_client.on_connect(None, None, None, 0)

    connected_state = "connected"
    stub_on_mqtt_connected.assert_called_once_with(connected_state)


def test_disconnect_calls_loopstop_on_mqttclient(mocker):
    mock_mqtt_client = MagicMock(spec=mqtt.Client)
    mock_constructor_mqtt_client = mocker.patch(
        "azure.iot.hub.devicesdk.transport.mqtt.mqtt_provider.mqtt.Client"
    )
    mock_constructor_mqtt_client.return_value = mock_mqtt_client
    mocker.patch.object(mock_mqtt_client, "loop_stop")

    mqtt_provider = MQTTProvider(fake_device_id, fake_hostname, fake_username, fake_password)
    mqtt_provider._on_enter_connecting()
    mqtt_provider.disconnect()

    mock_mqtt_client.loop_stop.assert_called_once_with()


def test_publish_calls_publish_on_mqtt_client(mocker):
    topic = "topic/"
    event = "Tarantallegra"

    mock_mqtt_client = MagicMock(spec=mqtt.Client)
    mock_constructor_mqtt_client = mocker.patch(
        "azure.iot.hub.devicesdk.transport.mqtt.mqtt_provider.mqtt.Client"
    )
    mock_constructor_mqtt_client.return_value = mock_mqtt_client
    mocker.patch.object(mock_mqtt_client, "publish")

    mqtt_provider = MQTTProvider(fake_device_id, fake_hostname, fake_username, fake_password)
    mqtt_provider._on_enter_connecting()
    mqtt_provider.publish(topic, event)

    mock_mqtt_client.publish.assert_called_once_with(topic=topic, payload=event, qos=1)
