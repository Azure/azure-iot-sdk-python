import pytest
from ..device.transport.transport import Transport, TransportProtocol
from ..device.transport.mqtt_wrapper import MQTTWrapper
from transitions import Machine

hostname = "beauxbatons.academy-net"
device_id = "MyFirebolt"


@pytest.fixture(scope='module')
def state_machine():
    state_machine = Machine(states=None, transitions=None, initial="learning")
    return state_machine


@pytest.fixture(scope='module')
def transport(state_machine):
    trans = Transport(TransportProtocol.MQTT, device_id, hostname, state_machine)
    return trans


def test_emptyinput():
    with pytest.raises(ValueError, message="Expecting ValueError",
                       match="Can not instantiate transport. Incomplete values."):
        Transport("", "", "", "")


def test_create():
    trans = Transport(TransportProtocol.MQTT, device_id, hostname, state_machine)
    assert trans.__getattribute__("_source") == device_id
    assert trans.__getattribute__("_hostname") == hostname
    assert trans.__getattribute__("_transport_protocol") == TransportProtocol.MQTT


def test_createmessagebroker_assigncallbacks(mocker, transport):
    mocker.patch.object(MQTTWrapper, "assign_callbacks")

    transport.create_message_broker_with_callbacks()
    MQTTWrapper.assign_callbacks.assert_called_once()


def test_set_options_on_message_broker(mocker, transport):
    username = "tomriddle"
    password = "iamvoldemort"
    mocker.patch.object(MQTTWrapper, "set_tls_options")
    mocker.patch.object(MQTTWrapper, "set_credentials")

    transport.set_options_on_message_broker(username, password)

    MQTTWrapper.set_tls_options.assert_called_once()
    MQTTWrapper.set_credentials.assert_called_once_with(username, password)


def test_sendevent(mocker, transport):
    topic = "devices/" + device_id + "/messages/events/"
    event = "Wingardian Leviosa"
    mocker.patch.object(MQTTWrapper, "publish")

    transport.send_event(topic, event)

    MQTTWrapper.publish.assert_called_once_with(topic, event)


def test_connect_to_message_broker(mocker, transport):
    mocker.patch.object(MQTTWrapper, "connect_and_start")

    transport.connect_to_message_broker()
    MQTTWrapper.connect_and_start.assert_called_once_with(hostname)


def test_disconnect_from_message_broker(mocker, transport):
    mocker.patch.object(MQTTWrapper, "disconnect_and_stop")

    transport.disconnect_from_message_broker()
    MQTTWrapper.disconnect_and_stop.assert_called_once()
