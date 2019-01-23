# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

import pytest
import logging
import six.moves.urllib as urllib
from azure.iot.hub.devicesdk.message import Message
from azure.iot.hub.devicesdk.transport.mqtt.mqtt_transport import MQTTTransport
from azure.iot.hub.devicesdk.auth.authentication_provider_factory import from_connection_string
from mock import MagicMock, patch
from datetime import date

logging.basicConfig(level=logging.INFO)

connection_string_format = "HostName={};DeviceId={};SharedAccessKey={}"
connection_string_format_mod = "HostName={};DeviceId={};ModuleId={};SharedAccessKey={}"
fake_shared_access_key = "Zm9vYmFy"
fake_hostname = "beauxbatons.academy-net"
fake_device_id = "MyPensieve"
fake_module_id = "MemoryCharms"
fake_event = "Wingardian Leviosa"
fake_event_2 = fake_event + " again!"

before_sys_key = "%24."
after_sys_key = "="
topic_separator = "&"
message_id_key = "mid"
fake_message_id = "spell-1234"
custom_property_value = "yes"
custom_property_name = "dementor_alert"
fake_topic = "devices/" + fake_device_id + "/messages/events/"
encoded_fake_topic = (
    fake_topic
    + before_sys_key
    + message_id_key
    + after_sys_key
    + fake_message_id
    + topic_separator
    + custom_property_name
    + after_sys_key
    + custom_property_value
)
subscribe_input_message_topic = (
    "devices/" + fake_device_id + "/modules/" + fake_module_id + "/inputs/#"
)
subscribe_input_message_qos = 1

subscribe_c2d_topic = "devices/" + fake_device_id + "/messages/devicebound/#"
subscribe_c2d_qos = 1


def create_fake_message():
    msg = Message(fake_event)
    msg.message_id = fake_message_id
    msg.custom_properties[custom_property_name] = custom_property_value
    return msg


@pytest.fixture(scope="function")
def authentication_provider():
    connection_string = connection_string_format.format(
        fake_hostname, fake_device_id, fake_shared_access_key
    )
    auth_provider = from_connection_string(connection_string)
    return auth_provider


@pytest.fixture(scope="function")
def transport(authentication_provider):
    with patch("azure.iot.hub.devicesdk.transport.mqtt.mqtt_transport.MQTTProvider"):
        transport = MQTTTransport(authentication_provider)
    transport.on_transport_connected = MagicMock()
    transport.on_transport_disconnected = MagicMock()
    yield transport
    transport.disconnect()


@pytest.fixture(scope="function")
def transport_module():
    connection_string_mod = connection_string_format_mod.format(
        fake_hostname, fake_device_id, fake_module_id, fake_shared_access_key
    )
    authentication_provider = from_connection_string(connection_string_mod)

    with patch("azure.iot.hub.devicesdk.transport.mqtt.mqtt_transport.MQTTProvider"):
        transport = MQTTTransport(authentication_provider)
    transport.on_transport_connected = MagicMock()
    transport.on_transport_disconnected = MagicMock()
    yield transport
    transport.disconnect()


def test_instantiation_creates_proper_transport(authentication_provider):
    trans = MQTTTransport(authentication_provider)
    assert trans._auth_provider == authentication_provider
    assert trans._mqtt_provider is not None


class TestConnect:
    def test_connect_calls_connect_on_provider(self, transport):
        mock_mqtt_provider = transport._mqtt_provider
        transport.connect()
        mock_mqtt_provider.connect.assert_called_once_with(
            transport._auth_provider.get_current_sas_token()
        )
        mock_mqtt_provider.on_mqtt_connected()

    def test_connected_state_handler_called_wth_new_state_once_provider_gets_connected(
        self, transport
    ):
        mock_mqtt_provider = transport._mqtt_provider

        transport.connect()
        mock_mqtt_provider.on_mqtt_connected()

        transport.on_transport_connected.assert_called_once_with("connected")

    def test_connect_ignored_if_waiting_for_connect_complete(self, transport):
        mock_mqtt_provider = transport._mqtt_provider

        transport.connect()
        transport.connect()
        mock_mqtt_provider.on_mqtt_connected()

        mock_mqtt_provider.connect.assert_called_once_with(
            transport._auth_provider.get_current_sas_token()
        )
        transport.on_transport_connected.assert_called_once_with("connected")

    def test_connect_ignored_if_waiting_for_send_complete(self, transport):
        mock_mqtt_provider = transport._mqtt_provider

        transport.connect()
        mock_mqtt_provider.on_mqtt_connected()

        mock_mqtt_provider.reset_mock()
        transport.on_transport_connected.reset_mock()

        transport.send_event(create_fake_message())
        transport.connect()

        mock_mqtt_provider.connect.assert_not_called()
        transport.on_transport_connected.assert_not_called()

        mock_mqtt_provider.on_mqtt_published(0)

        mock_mqtt_provider.connect.assert_not_called()
        transport.on_transport_connected.assert_not_called()


class TestSendEvent:
    def test_send_message_with_no_properties(self, transport):
        fake_msg = Message("Petrificus Totalus")

        mock_mqtt_provider = transport._mqtt_provider

        transport.connect()
        mock_mqtt_provider.on_mqtt_connected()
        transport.send_event(fake_msg)

        mock_mqtt_provider.connect.assert_called_once_with(
            transport._auth_provider.get_current_sas_token()
        )
        mock_mqtt_provider.publish.assert_called_once_with(fake_topic, fake_msg.data)

    def test_send_message_with_output_name(self, transport_module):
        fake_msg = Message("Petrificus Totalus")
        fake_msg.custom_properties[custom_property_name] = custom_property_value
        fake_msg.output_name = "fake_output_name"

        fake_output_topic = (
            "devices/"
            + fake_device_id
            + "/modules/"
            + fake_module_id
            + "/messages/events/"
            + before_sys_key
            + "on"
            + after_sys_key
            + "fake_output_name"
            + topic_separator
            + custom_property_name
            + after_sys_key
            + custom_property_value
        )

        mock_mqtt_provider = transport_module._mqtt_provider

        transport_module.connect()
        mock_mqtt_provider.on_mqtt_connected()
        transport_module.send_event(fake_msg)

        mock_mqtt_provider.connect.assert_called_once_with(
            transport_module._auth_provider.get_current_sas_token()
        )
        mock_mqtt_provider.publish.assert_called_once_with(fake_output_topic, fake_msg.data)

    def test_sendevent_calls_publish_on_provider(self, transport):
        fake_msg = create_fake_message()

        mock_mqtt_provider = transport._mqtt_provider

        transport.connect()
        mock_mqtt_provider.on_mqtt_connected()
        transport.send_event(fake_msg)

        mock_mqtt_provider.connect.assert_called_once_with(
            transport._auth_provider.get_current_sas_token()
        )
        mock_mqtt_provider.publish.assert_called_once_with(encoded_fake_topic, fake_msg.data)

    def test_send_event_queues_and_connects_before_sending(self, transport):
        fake_msg = create_fake_message()
        mock_mqtt_provider = transport._mqtt_provider

        # send an event
        transport.send_event(fake_msg)

        # verify that we called connect
        mock_mqtt_provider.connect.assert_called_once_with(
            transport._auth_provider.get_current_sas_token()
        )

        # verify that we're not connected yet and verify that we havent't published yet
        transport.on_transport_connected.assert_not_called()
        mock_mqtt_provider.publish.assert_not_called()

        # finish the connection
        mock_mqtt_provider.on_mqtt_connected()

        # verify that our connected callback was called and verify that we published the event
        transport.on_transport_connected.assert_called_once_with("connected")
        mock_mqtt_provider.publish.assert_called_once_with(encoded_fake_topic, fake_msg.data)

    def test_send_event_queues_if_waiting_for_connect_complete(self, transport):
        fake_msg = create_fake_message()

        mock_mqtt_provider = transport._mqtt_provider

        # start connecting and verify that we've called into the provider
        transport.connect()
        mock_mqtt_provider.connect.assert_called_once_with(
            transport._auth_provider.get_current_sas_token()
        )

        # send an event
        transport.send_event(fake_msg)

        # verify that we're not connected yet and verify that we havent't published yet
        transport.on_transport_connected.assert_not_called()
        mock_mqtt_provider.publish.assert_not_called()

        # finish the connection
        mock_mqtt_provider.on_mqtt_connected()

        # verify that our connected callback was called and verify that we published the event
        transport.on_transport_connected.assert_called_once_with("connected")
        mock_mqtt_provider.publish.assert_called_once_with(encoded_fake_topic, fake_msg.data)

    def test_send_event_sends_overlapped_events(self, transport):
        fake_msg_1 = create_fake_message()
        fake_msg_2 = Message(fake_event_2)

        mock_mqtt_provider = transport._mqtt_provider

        # connect
        transport.connect()
        mock_mqtt_provider.on_mqtt_connected()

        # send an event
        callback_1 = MagicMock()
        transport.send_event(fake_msg_1, callback_1)
        mock_mqtt_provider.publish.assert_called_once_with(encoded_fake_topic, fake_msg_1.data)

        # while we're waiting for that send to complete, send another event
        callback_2 = MagicMock()
        transport.send_event(fake_msg_2, callback_2)

        # verify that we've called publish twice and verify that neither send_event
        # has completed (because we didn't do anything here to complete it).
        assert mock_mqtt_provider.publish.call_count == 2
        callback_1.assert_not_called()
        callback_2.assert_not_called()

    def test_puback_calls_client_callback(self, transport):
        fake_msg = create_fake_message()

        mock_mqtt_provider = transport._mqtt_provider
        mock_mqtt_provider.publish = MagicMock(return_value=42)

        # connect
        transport.connect()
        mock_mqtt_provider.on_mqtt_connected()

        # send an event
        callback = MagicMock()
        transport.send_event(fake_msg, callback)

        # fake the puback:
        mock_mqtt_provider.on_mqtt_published(42)

        # assert
        callback.assert_called_once_with()

    def test_connect_send_disconnect(self, transport):
        fake_msg = create_fake_message()

        mock_mqtt_provider = transport._mqtt_provider

        # connect
        transport.connect()
        mock_mqtt_provider.on_mqtt_connected()

        # send an event
        transport.send_event(fake_msg)
        mock_mqtt_provider.on_mqtt_published(0)

        # disconnect
        transport.disconnect()
        mock_mqtt_provider.disconnect.assert_called_once_with()


class TestDisconnect:
    def test_disconnect_calls_disconnect_on_provider(self, transport):
        mock_mqtt_provider = transport._mqtt_provider

        transport.connect()
        mock_mqtt_provider.on_mqtt_connected()
        transport.disconnect()

        mock_mqtt_provider.disconnect.assert_called_once_with()

    def test_disconnect_ignored_if_already_disconnected(self, transport):
        mock_mqtt_provider = transport._mqtt_provider

        transport.disconnect(None)

        mock_mqtt_provider.disconnect.assert_not_called()

    def test_disconnect_calls_client_disconnect_callback(self, transport):
        mock_mqtt_provider = transport._mqtt_provider

        transport.connect()
        mock_mqtt_provider.on_mqtt_connected()

        transport.disconnect()
        mock_mqtt_provider.on_mqtt_disconnected()

        transport.on_transport_disconnected.assert_called_once_with("disconnected")


class TestEnableInputMessage:
    def test_subscribe_calls_subscribe_on_provider(self, transport_module):
        transport = transport_module
        mock_mqtt_provider = transport._mqtt_provider

        transport.connect()
        mock_mqtt_provider.on_mqtt_connected()
        transport.enable_input_messages()

        mock_mqtt_provider.subscribe.assert_called_once_with(
            subscribe_input_message_topic, subscribe_input_message_qos
        )

    def test_suback_calls_client_callback(self, transport_module):
        transport = transport_module

        mock_mqtt_provider = transport._mqtt_provider
        mock_mqtt_provider.subscribe = MagicMock(return_value=42)

        # connect
        transport.connect()
        mock_mqtt_provider.on_mqtt_connected()

        # subscribe
        callback = MagicMock()
        transport.enable_input_messages(callback)

        # fake the suback:
        mock_mqtt_provider.on_mqtt_subscribed(42)

        # assert
        callback.assert_called_once_with()


class TestEnableC2D:
    def test_subscribe_calls_subscribe_on_provider(self, transport):
        mock_mqtt_provider = transport._mqtt_provider

        transport.connect()
        mock_mqtt_provider.on_mqtt_connected()
        transport.enable_c2d_messages()

        mock_mqtt_provider.subscribe.assert_called_once_with(subscribe_c2d_topic, subscribe_c2d_qos)

    def test_suback_calls_client_callback(self, transport):
        mock_mqtt_provider = transport._mqtt_provider
        mock_mqtt_provider.subscribe = MagicMock(return_value=42)

        # connect
        transport.connect()
        mock_mqtt_provider.on_mqtt_connected()

        # subscribe
        callback = MagicMock()
        transport.enable_c2d_messages(callback)

        # fake the suback:
        mock_mqtt_provider.on_mqtt_subscribed(42)

        # assert
        callback.assert_called_once_with()
