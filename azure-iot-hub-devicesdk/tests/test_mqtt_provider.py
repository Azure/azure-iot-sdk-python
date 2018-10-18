# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

from azure.iot.hub.devicesdk.transport.mqtt.mqtt_provider import MQTTProvider
import paho.mqtt.client as mqtt
from transitions import Machine
import os
import ssl
from six import add_move, MovedModule

add_move(MovedModule("mock", "mock", "unittest.mock"))
from six.moves import mock
from mock import MagicMock


hostname = "beauxbatons.academy-net"
device_id = "MyFirebolt"
password = "Fortuna Major"


def test_create():
    provider = MQTTProvider(device_id, hostname, password)
    assert provider._device_id == device_id
    assert provider._hostname == hostname
    assert provider._username == hostname + "/" + device_id
    assert provider._password == password
    assert provider.on_mqtt_connected is not None

    assert provider._state_machine.states["disconnected"] is not None
    assert provider._state_machine.states["connecting"] is not None
    assert provider._state_machine.states["connected"] is not None
    assert provider._state_machine.states["disconnecting"] is not None

    assert provider._state_machine.events["trig_connect"] is not None
    assert provider._state_machine.events["trig_on_connect"] is not None
    assert provider._state_machine.events["trig_disconnect"] is not None
    assert provider._state_machine.events["trig_on_disconnect"] is not None

    assert provider._state_machine.initial == "disconnected"
    assert provider._state_machine.on_enter_connecting is not None
    assert provider._state_machine.on_enter_disconnecting is not None
    assert provider._state_machine.on_enter_connected is not None
    assert provider._state_machine.on_enter_disconnected is not None


def test_on_enter_connecting(mocker):
    mock_mqtt_client = MagicMock(spec=mqtt.Client)
    mock_constructor_mqtt_client = mocker.patch(
        "azure.iot.hub.devicesdk.transport.mqtt.mqtt_provider.mqtt.Client"
    )
    mock_constructor_mqtt_client.return_value = mock_mqtt_client

    mocker.patch.object(MQTTProvider, "_emit_connection_status")
    mocker.patch.object(mock_mqtt_client, "tls_set")
    mocker.patch.object(mock_mqtt_client, "tls_insecure_set")
    mocker.patch.object(mock_mqtt_client, "username_pw_set")
    mocker.patch.object(mock_mqtt_client, "connect")
    mocker.patch.object(mock_mqtt_client, "loop_start")

    mqtt_provider = MQTTProvider(device_id, hostname, password)
    mqtt_provider._on_enter_connecting()

    MQTTProvider._emit_connection_status.assert_called_once_with()
    mock_constructor_mqtt_client.assert_called_once_with(device_id, False, protocol=4)
    mock_mqtt_client.tls_set.assert_called_once_with(
        ca_certs=os.environ.get("IOTHUB_ROOT_CA_CERT"),
        certfile=None,
        keyfile=None,
        cert_reqs=ssl.CERT_REQUIRED,
        tls_version=ssl.PROTOCOL_TLSv1,
        ciphers=None,
    )
    mock_mqtt_client.tls_insecure_set.assert_called_once_with(False)
    mock_mqtt_client.connect.assert_called_once_with(host=hostname, port=8883)
    mock_mqtt_client.loop_start.assert_called_once_with()

    assert mock_mqtt_client.on_connect is not None
    assert mock_mqtt_client.on_disconnect is not None
    assert mock_mqtt_client.on_publish is not None


def test_on_enter_disconnecting(mocker):
    mocker.patch.object(MQTTProvider, "_emit_connection_status")

    mqtt_provider = MQTTProvider(device_id, hostname, password)
    mqtt_provider._on_enter_disconnecting()

    MQTTProvider._emit_connection_status.assert_called_once_with()


def test_connect(mocker):
    mock_machine_from_real = create_from_real_state_machine()
    mock_machine_constructor = mocker.patch(
        "azure.iot.hub.devicesdk.transport.mqtt.mqtt_provider.Machine"
    )
    mock_machine_constructor.return_value = mock_machine_from_real

    mqtt_provider = MQTTProvider(device_id, hostname, password)
    mqtt_provider.connect()

    mock_machine_from_real.trig_connect.assert_called_once_with()


def test_disconnect(mocker):
    mock_mqtt_client = MagicMock(spec=mqtt.Client)
    mock_constructor_mqtt_client = mocker.patch(
        "azure.iot.hub.devicesdk.transport.mqtt.mqtt_provider.mqtt.Client"
    )
    mock_constructor_mqtt_client.return_value = mock_mqtt_client
    mocker.patch.object(mock_mqtt_client, "loop_stop")

    mqtt_provider = MQTTProvider(device_id, hostname, password)
    mqtt_provider._on_enter_connecting()
    mqtt_provider.disconnect()

    mock_mqtt_client.loop_stop.assert_called_once_with()


def test_publish(mocker):
    topic = "topic/"
    event = "Tarantallegra"

    mock_mqtt_client = MagicMock(spec=mqtt.Client)
    mock_constructor_mqtt_client = mocker.patch(
        "azure.iot.hub.devicesdk.transport.mqtt.mqtt_provider.mqtt.Client"
    )
    mock_constructor_mqtt_client.return_value = mock_mqtt_client
    mocker.patch.object(mock_mqtt_client, "publish")

    mqtt_provider = MQTTProvider(device_id, hostname, password)
    mqtt_provider._on_enter_connecting()
    mqtt_provider.publish(topic, event)

    mock_mqtt_client.publish.assert_called_once_with(topic=topic, payload=event, qos=1)


def test_emit_connection_status(mocker):
    stub_on_connection_state = mocker.stub(name="on_mqtt_connected")

    mock_machine_from_real = create_from_real_state_machine()
    mock_machine_constructor = mocker.patch(
        "azure.iot.hub.devicesdk.transport.mqtt.mqtt_provider.Machine"
    )
    mock_machine_constructor.return_value = mock_machine_from_real
    connected_state = "connected"
    mock_machine_from_real.state = connected_state

    mqtt_provider = MQTTProvider(device_id, hostname, password)
    mqtt_provider.on_mqtt_connected = stub_on_connection_state
    mqtt_provider._emit_connection_status()

    stub_on_connection_state.assert_called_once_with(connected_state)


def create_from_real_state_machine():
    real_states = ["disconnected", "connecting", "connected", "disconnecting"]
    real_transitions = [
        {"trigger": "trig_connect", "source": "disconnected", "dest": "connecting"},
        {"trigger": "trig_on_connect", "source": "connecting", "dest": "connected"},
        {"trigger": "trig_disconnect", "source": "connected", "dest": "disconnecting"},
        {"trigger": "trig_on_disconnect", "source": "disconnecting", "dest": "disconnected"},
    ]

    real_state_machine = Machine(
        states=real_states, transitions=real_transitions, initial="disconnected"
    )

    mock_machine_from_real = MagicMock(real_state_machine)
    mock_machine_from_real.attach_mock(MagicMock, "on_enter_connecting")
    mock_machine_from_real.attach_mock(MagicMock, "on_enter_disconnecting")
    mock_machine_from_real.attach_mock(MagicMock, "on_enter_connected")
    mock_machine_from_real.attach_mock(MagicMock, "on_enter_disconnected")

    return mock_machine_from_real
