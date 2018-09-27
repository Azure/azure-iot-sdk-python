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


def test_sendevent(mocker, transport):
    topic = "devices/" + device_id + "/messages/events/"
    event = "Wingardian Leviosa"
    mocker.patch.object(transport, '_mqtt_wrapper')

    transport.send_event(topic, event)
    transport._mqtt_wrapper.publish.assert_called_once_with(topic, event)


def test_createmessagebroker_assigncallbacks(mocker, transport, state_machine):
    mocker.patch.object(MQTTWrapper, "create_mqtt_client_wrapper")
    mocker.patch.object(transport, '_mqtt_wrapper')

    transport.create_message_broker_with_callbacks()
    MQTTWrapper.create_mqtt_client_wrapper.assert_called_once_with(device_id, hostname, state_machine)
    transport._mqtt_wrapper.assign_callbacks.assert_called_once()


def test_set_options_on_message_broker(mocker, transport):
    username = "tomriddle"
    password = "iamvoldemort"

    mocker.patch.object(transport, '_mqtt_wrapper')

    transport.set_options_on_message_broker(username, password)

    transport._mqtt_wrapper.set_tls_options.assert_called_once()
    transport._mqtt_wrapper.set_credentials.assert_called_once_with(username, password)


def test_connect_to_message_broker(mocker, transport):
    mocker.patch.object(transport, '_mqtt_wrapper')

    transport.connect_to_message_broker()
    transport._mqtt_wrapper.connect_and_start.assert_called_once_with(hostname)


def test_disconnect_from_message_broker(mocker, transport):
    mocker.patch.object(transport, '_mqtt_wrapper')

    transport.disconnect_from_message_broker()
    transport._mqtt_wrapper.disconnect_and_stop.assert_called_once()





