# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

import pytest
import logging
from azure.iot.hub.devicesdk.transport.mqtt.mqtt_transport import MQTTTransport
from azure.iot.hub.devicesdk.transport.mqtt.mqtt_provider import MQTTProvider
from azure.iot.hub.devicesdk.auth.authentication_provider_factory import from_connection_string
from six import add_move, MovedModule

add_move(MovedModule("mock", "mock", "unittest.mock"))
from six.moves import mock
from mock import MagicMock

logging.basicConfig(level=logging.INFO)

connection_string_format = "HostName={};DeviceId={};SharedAccessKey={}"
fake_shared_access_key = "Zm9vYmFy"
fake_hostname = "beauxbatons.academy-net"
fake_device_id = "MyPensieve"
fake_event = "Wingardian Leviosa"
fake_event_2 = fake_event + " again!"
fake_topic = "devices/" + fake_device_id + "/messages/events/"


@pytest.fixture(scope="function")
def authentication_provider():
    connection_string = connection_string_format.format(fake_hostname, fake_device_id, fake_shared_access_key)
    auth_provider = from_connection_string(connection_string)
    return auth_provider


@pytest.fixture(scope="function")
def transport(authentication_provider):
    with mock.patch("azure.iot.hub.devicesdk.transport.mqtt.mqtt_transport.MQTTProvider"):
        transport = MQTTTransport(authentication_provider)
    transport.on_transport_connected = MagicMock()
    return transport


def test_instantiation_creates_proper_transport(authentication_provider):
    trans = MQTTTransport(authentication_provider)
    assert trans._auth_provider == authentication_provider
    assert trans._mqtt_provider is not None


class TestConnect():
    def test_connect_calls_connect_on_provider(self, transport):
        mock_mqtt_provider = transport._mqtt_provider
        transport.connect()
        mock_mqtt_provider.connect.assert_called_once_with()

    def test_connected_state_handler_called_wth_new_state_once_provider_gets_connected(self, transport):
        mock_mqtt_provider = transport._mqtt_provider

        transport.connect()
        mock_mqtt_provider.on_mqtt_connected()

        transport.on_transport_connected.assert_called_once_with("connected")

    def test_connect_ignored_if_waiting_for_connect_complete(self, transport):
        mock_mqtt_provider = transport._mqtt_provider

        transport.connect()
        transport.connect()
        mock_mqtt_provider.on_mqtt_connected()

        mock_mqtt_provider.connect.assert_called_once_with()
        transport.on_transport_connected.assert_called_once_with("connected")

    def test_connect_ignored_if_waiting_for_send_complete(self, transport):
        mock_mqtt_provider = transport._mqtt_provider

        transport.connect()
        mock_mqtt_provider.on_mqtt_connected()

        mock_mqtt_provider.reset_mock()
        transport.on_transport_connected.reset_mock()

        transport.send_event(fake_event)
        transport.connect()

        mock_mqtt_provider.connect.assert_not_called()
        transport.on_transport_connected.assert_not_called()

        mock_mqtt_provider.on_mqtt_published()

        mock_mqtt_provider.connect.assert_not_called()
        transport.on_transport_connected.assert_not_called()


class TestSendEvent():
    def test_sendevent_calls_publish_on_provider(self, transport):
        mock_mqtt_provider = transport._mqtt_provider

        transport.connect()
        mock_mqtt_provider.on_mqtt_connected()
        transport.send_event(fake_event)

        mock_mqtt_provider.connect.assert_called_once_with()
        mock_mqtt_provider.publish.assert_called_once_with(fake_topic, fake_event)

    def test_send_event_queues_and_connects_before_sending(self, transport):
        mock_mqtt_provider = transport._mqtt_provider

        # send an event
        transport.send_event(fake_event)
        
        # verify that we called connect
        mock_mqtt_provider.connect.assert_called_once_with()

        # verify that we're not connected yet and verify that we havent't published yet 
        transport.on_transport_connected.assert_not_called()
        mock_mqtt_provider.publish.assert_not_called()

        # finish the connection
        mock_mqtt_provider.on_mqtt_connected()

        # verify that our connected callback was called and verify that we published the event
        transport.on_transport_connected.assert_called_once_with("connected")
        mock_mqtt_provider.publish.assert_called_once_with(fake_topic, fake_event)

    def test_send_event_queues_if_waiting_for_connect_complete(self, transport):
        mock_mqtt_provider = transport._mqtt_provider

        # start connecting and verify that we've called into the provider
        transport.connect()
        mock_mqtt_provider.connect.assert_called_once_with()

        # send an event
        transport.send_event(fake_event)

        # verify that we're not connected yet and verify that we havent't published yet 
        transport.on_transport_connected.assert_not_called()
        mock_mqtt_provider.publish.assert_not_called()

        # finish the connection
        mock_mqtt_provider.on_mqtt_connected()

        # verify that our connected callback was called and verify that we published the event
        transport.on_transport_connected.assert_called_once_with("connected")
        mock_mqtt_provider.publish.assert_called_once_with(fake_topic, fake_event)

    def test_send_event_queues_if_waiting_for_send_complete(self, transport):
        mock_mqtt_provider = transport._mqtt_provider

        # connect
        transport.connect()
        mock_mqtt_provider.on_mqtt_connected()

        # send an event
        transport.send_event(fake_event)
        mock_mqtt_provider.publish.assert_called_once_with(fake_topic, fake_event)

        # while we're waiting for that send to complete, send another event
        mock_mqtt_provider.publish.reset_mock()
        transport.send_event(fake_event_2)
        mock_mqtt_provider.publish.assert_not_called()

        # finish sending the first event
        mock_mqtt_provider.on_mqtt_published()

        # and verify that we're sending the second event
        mock_mqtt_provider.publish.assert_called_once_with(fake_topic, fake_event_2)

class TestDisconnect():
    def test_disconnect_calls_disconnect_on_provider(self, transport):
        mock_mqtt_provider = transport._mqtt_provider

        transport.connect()
        mock_mqtt_provider.on_mqtt_connected()
        transport.disconnect()

        mock_mqtt_provider.disconnect.assert_called_once_with()

    def test_disconnect_ignored_if_already_disconnected(self, transport):
        mock_mqtt_provider = transport._mqtt_provider

        transport.disconnect()

        mock_mqtt_provider.disconnect.assert_not_called()

