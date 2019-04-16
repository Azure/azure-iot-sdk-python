# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
import logging
import six.moves.urllib as urllib
from azure.iot.device.iothub import Message
from azure.iot.device.iothub.transport.mqtt.mqtt_transport import MQTTTransport
from azure.iot.device.iothub.transport import constant
from azure.iot.device.iothub.auth.authentication_provider_factory import from_connection_string
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


def create_fake_output_message():
    msg = Message(fake_event)
    msg.message_id = fake_message_id
    msg.output_name = "fake_output_name"
    return msg


@pytest.fixture(scope="function")
def authentication_provider():
    connection_string = connection_string_format.format(
        fake_hostname, fake_device_id, fake_shared_access_key
    )
    auth_provider = from_connection_string(connection_string)
    return auth_provider


@pytest.fixture(scope="function")
def device_transport(authentication_provider):
    with patch("azure.iot.device.iothub.transport.mqtt.mqtt_transport.MQTTProvider"):
        transport = MQTTTransport(authentication_provider)
    transport.on_transport_connected = MagicMock()
    transport.on_transport_disconnected = MagicMock()
    yield transport
    transport.disconnect()


@pytest.fixture(scope="function")
def module_transport():
    connection_string_mod = connection_string_format_mod.format(
        fake_hostname, fake_device_id, fake_module_id, fake_shared_access_key
    )
    authentication_provider = from_connection_string(connection_string_mod)

    with patch("azure.iot.device.iothub.transport.mqtt.mqtt_transport.MQTTProvider"):
        transport = MQTTTransport(authentication_provider)
    transport.on_transport_connected = MagicMock()
    transport.on_transport_disconnected = MagicMock()
    yield transport
    transport.disconnect()


class TestInstantiation(object):
    def test_instantiates_correctly(self, authentication_provider):
        trans = MQTTTransport(authentication_provider)
        assert trans._auth_provider == authentication_provider
        assert trans._mqtt_provider is not None


class TestConnect:
    def test_connect_calls_connect_on_provider(self, device_transport):
        mock_mqtt_provider = device_transport._mqtt_provider
        device_transport.connect()
        mock_mqtt_provider.connect.assert_called_once_with(
            device_transport._auth_provider.get_current_sas_token()
        )
        mock_mqtt_provider.on_mqtt_connected()

    def test_connected_state_handler_called_wth_new_state_once_provider_gets_connected(
        self, device_transport
    ):
        mock_mqtt_provider = device_transport._mqtt_provider

        device_transport.connect()
        mock_mqtt_provider.on_mqtt_connected()

        device_transport.on_transport_connected.assert_called_once_with("connected")

    def test_connect_ignored_if_waiting_for_connect_complete(self, device_transport):
        mock_mqtt_provider = device_transport._mqtt_provider

        device_transport.connect()
        device_transport.connect()
        mock_mqtt_provider.on_mqtt_connected()

        mock_mqtt_provider.connect.assert_called_once_with(
            device_transport._auth_provider.get_current_sas_token()
        )
        device_transport.on_transport_connected.assert_called_once_with("connected")

    def test_connect_ignored_if_waiting_for_send_complete(self, device_transport):
        mock_mqtt_provider = device_transport._mqtt_provider

        device_transport.connect()
        mock_mqtt_provider.on_mqtt_connected()

        mock_mqtt_provider.reset_mock()
        device_transport.on_transport_connected.reset_mock()

        device_transport.send_event(create_fake_message())
        device_transport.connect()

        mock_mqtt_provider.connect.assert_not_called()
        device_transport.on_transport_connected.assert_not_called()

        mock_mqtt_provider.on_mqtt_published(0)

        mock_mqtt_provider.connect.assert_not_called()
        device_transport.on_transport_connected.assert_not_called()


class TestSendEvent:
    def test_send_message_with_no_properties(self, device_transport):
        fake_msg = Message("Petrificus Totalus")

        mock_mqtt_provider = device_transport._mqtt_provider

        device_transport.connect()
        mock_mqtt_provider.on_mqtt_connected()
        device_transport.send_event(fake_msg)

        mock_mqtt_provider.connect.assert_called_once_with(
            device_transport._auth_provider.get_current_sas_token()
        )
        mock_mqtt_provider.publish.assert_called_once_with(fake_topic, fake_msg.data)

    def test_send_message_with_output_name(self, module_transport):
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

        mock_mqtt_provider = module_transport._mqtt_provider

        module_transport.connect()
        mock_mqtt_provider.on_mqtt_connected()
        module_transport.send_event(fake_msg)

        mock_mqtt_provider.connect.assert_called_once_with(
            module_transport._auth_provider.get_current_sas_token()
        )
        mock_mqtt_provider.publish.assert_called_once_with(fake_output_topic, fake_msg.data)

    def test_sendevent_calls_publish_on_provider(self, device_transport):
        fake_msg = create_fake_message()

        mock_mqtt_provider = device_transport._mqtt_provider

        device_transport.connect()
        mock_mqtt_provider.on_mqtt_connected()
        device_transport.send_event(fake_msg)

        mock_mqtt_provider.connect.assert_called_once_with(
            device_transport._auth_provider.get_current_sas_token()
        )
        mock_mqtt_provider.publish.assert_called_once_with(encoded_fake_topic, fake_msg.data)

    def test_send_event_queues_and_connects_before_sending(self, device_transport):
        fake_msg = create_fake_message()
        mock_mqtt_provider = device_transport._mqtt_provider

        # send an event
        device_transport.send_event(fake_msg)

        # verify that we called connect
        mock_mqtt_provider.connect.assert_called_once_with(
            device_transport._auth_provider.get_current_sas_token()
        )

        # verify that we're not connected yet and verify that we havent't published yet
        device_transport.on_transport_connected.assert_not_called()
        mock_mqtt_provider.publish.assert_not_called()

        # finish the connection
        mock_mqtt_provider.on_mqtt_connected()

        # verify that our connected callback was called and verify that we published the event
        device_transport.on_transport_connected.assert_called_once_with("connected")
        mock_mqtt_provider.publish.assert_called_once_with(encoded_fake_topic, fake_msg.data)

    def test_send_event_queues_if_waiting_for_connect_complete(self, device_transport):
        fake_msg = create_fake_message()

        mock_mqtt_provider = device_transport._mqtt_provider

        # start connecting and verify that we've called into the provider
        device_transport.connect()
        mock_mqtt_provider.connect.assert_called_once_with(
            device_transport._auth_provider.get_current_sas_token()
        )

        # send an event
        device_transport.send_event(fake_msg)

        # verify that we're not connected yet and verify that we havent't published yet
        device_transport.on_transport_connected.assert_not_called()
        mock_mqtt_provider.publish.assert_not_called()

        # finish the connection
        mock_mqtt_provider.on_mqtt_connected()

        # verify that our connected callback was called and verify that we published the event
        device_transport.on_transport_connected.assert_called_once_with("connected")
        mock_mqtt_provider.publish.assert_called_once_with(encoded_fake_topic, fake_msg.data)

    def test_send_event_sends_overlapped_events(self, device_transport):
        fake_msg_1 = create_fake_message()
        fake_msg_2 = Message(fake_event_2)

        mock_mqtt_provider = device_transport._mqtt_provider

        # connect
        device_transport.connect()
        mock_mqtt_provider.on_mqtt_connected()

        # send an event
        callback_1 = MagicMock()
        device_transport.send_event(fake_msg_1, callback_1)
        mock_mqtt_provider.publish.assert_called_once_with(encoded_fake_topic, fake_msg_1.data)

        # while we're waiting for that send to complete, send another event
        callback_2 = MagicMock()
        device_transport.send_event(fake_msg_2, callback_2)

        # verify that we've called publish twice and verify that neither send_event
        # has completed (because we didn't do anything here to complete it).
        assert mock_mqtt_provider.publish.call_count == 2
        callback_1.assert_not_called()
        callback_2.assert_not_called()

    def test_puback_calls_client_callback(self, device_transport):
        fake_msg = create_fake_message()

        mock_mqtt_provider = device_transport._mqtt_provider
        mock_mqtt_provider.publish = MagicMock(return_value=42)

        # connect
        device_transport.connect()
        mock_mqtt_provider.on_mqtt_connected()

        # send an event
        callback = MagicMock()
        device_transport.send_event(fake_msg, callback)

        # fake the puback:
        mock_mqtt_provider.on_mqtt_published(42)

        # assert
        callback.assert_called_once_with()

    def test_connect_send_disconnect(self, device_transport):
        fake_msg = create_fake_message()

        mock_mqtt_provider = device_transport._mqtt_provider

        # connect
        device_transport.connect()
        mock_mqtt_provider.on_mqtt_connected()

        # send an event
        device_transport.send_event(fake_msg)
        mock_mqtt_provider.on_mqtt_published(0)

        # disconnect
        device_transport.disconnect()
        mock_mqtt_provider.disconnect.assert_called_once_with()


class TestDisconnect:
    def test_disconnect_calls_disconnect_on_provider(self, device_transport):
        mock_mqtt_provider = device_transport._mqtt_provider

        device_transport.connect()
        mock_mqtt_provider.on_mqtt_connected()
        device_transport.disconnect()

        mock_mqtt_provider.disconnect.assert_called_once_with()

    def test_disconnect_ignored_if_already_disconnected(self, device_transport):
        mock_mqtt_provider = device_transport._mqtt_provider

        device_transport.disconnect(None)

        mock_mqtt_provider.disconnect.assert_not_called()

    def test_disconnect_calls_client_disconnect_callback(self, device_transport):
        mock_mqtt_provider = device_transport._mqtt_provider

        device_transport.connect()
        mock_mqtt_provider.on_mqtt_connected()

        device_transport.disconnect()
        mock_mqtt_provider.on_mqtt_disconnected()

        device_transport.on_transport_disconnected.assert_called_once_with("disconnected")


class TestEnableInputMessage:
    def test_subscribe_calls_subscribe_on_provider(self, module_transport):
        mock_mqtt_provider = module_transport._mqtt_provider

        module_transport.connect()
        mock_mqtt_provider.on_mqtt_connected()
        module_transport.enable_feature(constant.INPUT_MSG)

        mock_mqtt_provider.subscribe.assert_called_once_with(
            subscribe_input_message_topic, subscribe_input_message_qos
        )

    def test_suback_calls_client_callback(self, module_transport):

        mock_mqtt_provider = module_transport._mqtt_provider
        mock_mqtt_provider.subscribe = MagicMock(return_value=42)

        # connect
        module_transport.connect()
        mock_mqtt_provider.on_mqtt_connected()

        # subscribe
        callback = MagicMock()
        module_transport.enable_feature(constant.INPUT_MSG, callback)

        # fake the suback:
        mock_mqtt_provider.on_mqtt_subscribed(42)

        # assert
        callback.assert_called_once_with()

    def test_sets_input_message_status_to_enabled(self, module_transport):
        mock_mqtt_provider = module_transport._mqtt_provider

        module_transport.connect()
        mock_mqtt_provider.on_mqtt_connected()
        module_transport.enable_feature(constant.INPUT_MSG)

        assert module_transport.feature_enabled[constant.INPUT_MSG]


class TestDisableInputMessage:
    def test_unsubscribe_of_input_calls_unsubscribe_on_provider(self, module_transport):
        mock_mqtt_provider = module_transport._mqtt_provider

        module_transport.connect()
        mock_mqtt_provider.on_mqtt_connected()
        module_transport.disable_feature(constant.INPUT_MSG)

        mock_mqtt_provider.unsubscribe.assert_called_once_with(subscribe_input_message_topic)

    def test_unsuback_of_input_calls_client_callback(self, module_transport):
        mock_mqtt_provider = module_transport._mqtt_provider
        mock_mqtt_provider.unsubscribe = MagicMock(return_value=56)

        # connect
        module_transport.connect()
        mock_mqtt_provider.on_mqtt_connected()

        # unsubscribe
        callback = MagicMock()
        module_transport.disable_feature(constant.INPUT_MSG, callback)

        # fake the unsuback:
        mock_mqtt_provider.on_mqtt_unsubscribed(56)

        # assert
        callback.assert_called_once_with()

    def test_sets_input_message_status_to_disabled(self, module_transport):
        mock_mqtt_provider = module_transport._mqtt_provider

        module_transport.connect()
        mock_mqtt_provider.on_mqtt_connected()
        module_transport.disable_feature(constant.INPUT_MSG)

        assert not module_transport.feature_enabled[constant.INPUT_MSG]


class TestEnableC2D:
    def test_subscribe_calls_subscribe_on_provider(self, device_transport):
        mock_mqtt_provider = device_transport._mqtt_provider

        device_transport.connect()
        mock_mqtt_provider.on_mqtt_connected()
        device_transport.enable_feature(constant.C2D_MSG)

        mock_mqtt_provider.subscribe.assert_called_once_with(subscribe_c2d_topic, subscribe_c2d_qos)

    def test_suback_calls_client_callback(self, device_transport):
        mock_mqtt_provider = device_transport._mqtt_provider
        mock_mqtt_provider.subscribe = MagicMock(return_value=42)

        # connect
        device_transport.connect()
        mock_mqtt_provider.on_mqtt_connected()

        # subscribe
        callback = MagicMock()
        device_transport.enable_feature(constant.C2D_MSG, callback)

        # fake the suback:
        mock_mqtt_provider.on_mqtt_subscribed(42)

        # assert
        callback.assert_called_once_with()

    def test_sets_c2d_message_status_to_enabled(self, device_transport):
        mock_mqtt_provider = device_transport._mqtt_provider

        device_transport.connect()
        mock_mqtt_provider.on_mqtt_connected()
        device_transport.enable_feature(constant.C2D_MSG)

        assert device_transport.feature_enabled[constant.C2D_MSG]


class TestDisableC2D:
    def test_unsubscribe_calls_unsubscribe_on_provider(self, device_transport):
        device_transport._c2d_topic = subscribe_c2d_topic
        mock_mqtt_provider = device_transport._mqtt_provider

        device_transport.connect()
        mock_mqtt_provider.on_mqtt_connected()
        device_transport.disable_feature(constant.C2D_MSG)

        mock_mqtt_provider.unsubscribe.assert_called_once_with(subscribe_c2d_topic)

    def test_unsuback_of_c2d_calls_client_callback(self, device_transport):
        device_transport._c2d_topic = subscribe_c2d_topic
        mock_mqtt_provider = device_transport._mqtt_provider
        mock_mqtt_provider.unsubscribe = MagicMock(return_value=56)

        # connect
        device_transport.connect()
        mock_mqtt_provider.on_mqtt_connected()

        # unsubscribe
        callback = MagicMock()
        device_transport.disable_feature(constant.C2D_MSG, callback)

        # fake the unsuback:
        mock_mqtt_provider.on_mqtt_unsubscribed(56)

        # assert
        callback.assert_called_once_with()

    def test_sets_c2d_message_status_to_disabled(self, device_transport):
        device_transport._c2d_topic = subscribe_c2d_topic
        mock_mqtt_provider = device_transport._mqtt_provider

        device_transport.connect()
        mock_mqtt_provider.on_mqtt_connected()
        device_transport.disable_feature(constant.C2D_MSG)

        assert not device_transport.feature_enabled[constant.C2D_MSG]


@pytest.mark.skip(reason="Not implemented")
class TestEnableMethods:
    def test_subscribe_calls_subscribe_on_provider(self, transport):
        pass

    def test_suback_calls_client_callback(self, transport):
        pass

    def test_sets_methods_status_to_enabled(self, transport):
        pass


@pytest.mark.skip(reason="Not implemented")
class TestDisableMethods:
    def test_unsubscribe_calls_unsubscribe_on_provider(self, transport):
        pass

    def test_unsuback_of_methods_calls_client_callback(self, transport):
        pass

    def test_sets_method_status_to_disabled(self, transport):
        pass


@pytest.mark.skip(reason="Not implemented")
class TestSendMethodResponse:
    pass


@pytest.mark.parametrize(
    "transport_function,parameters,provider_function,transport_callback",
    [
        ("send_event", (create_fake_message(),), "publish", "_on_provider_publish_complete"),
        (
            "send_output_event",
            (create_fake_output_message(),),
            "publish",
            "_on_provider_publish_complete",
        ),
        ("enable_feature", (constant.C2D_MSG,), "subscribe", "_on_provider_subscribe_complete"),
        (
            "disable_feature",
            (constant.C2D_MSG,),
            "unsubscribe",
            "_on_provider_unsubscribe_complete",
        ),
        ("enable_feature", (constant.INPUT_MSG,), "subscribe", "_on_provider_subscribe_complete"),
        (
            "disable_feature",
            (constant.INPUT_MSG,),
            "unsubscribe",
            "_on_provider_unsubscribe_complete",
        ),
    ],
)
class TestProviderCallbacks:
    def test_function_calls_callback_if_ack_received_early(
        self,
        device_transport,
        transport_function,
        parameters,
        provider_function,
        transport_callback,
    ):
        mock_mqtt_provider = device_transport._mqtt_provider
        fake_mid = 42

        # connect
        device_transport.connect()
        mock_mqtt_provider.on_mqtt_connected()

        # define mock provider function that calls the transport callback with the mid first, then returns the mid second
        def mock_provider_function_early_callback(*args, **kwargs):
            getattr(device_transport, transport_callback)(fake_mid)
            return fake_mid

        setattr(mock_mqtt_provider, provider_function, mock_provider_function_early_callback)

        # Call the transport function
        callback = MagicMock()
        getattr(device_transport, transport_function)(*parameters, callback=callback)

        # verify that our callback was called
        callback.assert_called_once_with()

    def test_function_calls_callback_if_ack_received_later(
        self,
        device_transport,
        transport_function,
        parameters,
        provider_function,
        transport_callback,
    ):
        mock_mqtt_provider = device_transport._mqtt_provider
        fake_mid = 42

        # connect
        device_transport.connect()
        mock_mqtt_provider.on_mqtt_connected()

        # define mock provider function that returns the mid.  We'll fake the callback later, after the mid is returned
        def mock_provider_function_returns_mid(*args, **kwargs):
            return fake_mid

        setattr(mock_mqtt_provider, provider_function, mock_provider_function_returns_mid)

        # Call the transport function
        callback = MagicMock()
        getattr(device_transport, transport_function)(*parameters, callback=callback)

        # verify that the transport hasn't called our callback yet
        callback.assert_not_called()

        # fake the provider callback
        getattr(device_transport, transport_callback)(fake_mid)

        # verify that our callback was finally called
        callback.assert_called_once_with()
