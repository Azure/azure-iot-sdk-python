import pytest
from ..device.transport.mqtt_wrapper import MQTTWrapper
import paho.mqtt.client as mqtt
from paho.mqtt.client import Client as MQTTClient
from transitions import Machine
import os
import ssl

hostname = "beauxbatons.academy-net"
device_id = "MyFirebolt"


@pytest.fixture(scope='module')
def state_machine():
    state_machine = Machine(states=None, transitions=None, initial="learning")
    return state_machine


@pytest.fixture(scope='module')
def mqtt_wrapper(state_machine):
    return MQTTWrapper(device_id, hostname, state_machine)


def test_create_emptyinput():
    with pytest.raises(ValueError, message="Expecting ValueError",
                       match="Can not instantiate MQTT broker. Incomplete values."):
        MQTTWrapper("", "", "")


def test_create_noneinput():
    with pytest.raises(ValueError, message="Expecting ValueError",
                       match="Can not instantiate MQTT broker. Incomplete values."):
        MQTTWrapper(None, None, None)


def test_create_none_empty_input():
    with pytest.raises(ValueError, message="Expecting ValueError",
                       match="Can not instantiate MQTT broker. Incomplete values."):
        MQTTWrapper(None, "", None)


def test_create(state_machine):
    wrapper = MQTTWrapper(device_id, hostname, state_machine)
    assert wrapper.__getattribute__("_client_id") == device_id
    assert wrapper.__getattribute__("_hostname") == hostname
    assert wrapper.__getattribute__("_state_machine") == state_machine

    mqttclient = wrapper.__getattribute__("_mqtt_client")
    mqttclient.__getattribute__("_client_id") == device_id
    mqttclient.__getattribute__("_protocol") == mqtt.MQTTv311


def test_set_tls_options(mocker, mqtt_wrapper):
    mocker.patch.object(MQTTClient, "tls_set")
    mocker.patch.object(MQTTClient, "tls_insecure_set")

    mqtt_wrapper.set_tls_options()
    MQTTClient.tls_set.assert_called_once_with(ca_certs=os.environ.get("IOTHUB_ROOT_CA_CERT"),
                              certfile=None, keyfile=None, cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1,
                              ciphers=None)
    MQTTClient.tls_insecure_set.assert_called_once()


def test_set_credentials(mocker, mqtt_wrapper):
    username = "tomriddle"
    password = "iamvoldemort"

    mocker.patch.object(MQTTClient, "username_pw_set")

    mqtt_wrapper.set_credentials(username, password)
    MQTTClient.username_pw_set.assert_called_once_with(username=username, password=password)


def test_connect_and_start(mocker, mqtt_wrapper):
    mocker.patch.object(mqtt_wrapper, "_mqtt_client")

    mqtt_wrapper.connect_and_start(hostname)
    mqtt_wrapper._mqtt_client.connect.assert_called_once_with(host=hostname, port=8883)
    mqtt_wrapper._mqtt_client.loop_start.assert_called_once()


def test_publish(mocker, mqtt_wrapper):
    topic = "devices/" + device_id + "/messages/events/"
    event = "Wingardian Leviosa"

    mocker.patch.object(MQTTClient, "publish")

    mqtt_wrapper.publish(topic, event)

    MQTTClient.publish.assert_called_once_with(topic=topic, payload=event, qos=1)


def test_disconnect_and_stop(mocker, mqtt_wrapper):
    mocker.patch.object(MQTTClient, "loop_stop")

    mqtt_wrapper.disconnect_and_stop()
    MQTTClient.loop_stop.assert_called_once()
