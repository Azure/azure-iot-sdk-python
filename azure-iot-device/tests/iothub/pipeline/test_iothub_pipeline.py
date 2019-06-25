# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
import logging
import six.moves.urllib as urllib
from azure.iot.device.iothub import Message
from azure.iot.device.iothub.pipeline import IoTHubPipeline, constant
from azure.iot.device.iothub.auth import SymmetricKeyAuthenticationProvider
from mock import MagicMock, patch, ANY
from datetime import date

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

subscribe_c2d_topic = "devices/" + fake_device_id + "/messages/devicebound/#"
subscribe_methods_topic = "$iothub/methods/POST/#"

send_msg_qos = 1


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
    auth_provider = SymmetricKeyAuthenticationProvider.parse(connection_string)
    return auth_provider


@pytest.fixture(scope="function")
def device_pipeline_adapter(authentication_provider):
    with patch(
        "azure.iot.device.iothub.pipeline.iothub_pipeline.pipeline_stages_mqtt.MQTTClientOperator"
    ):
        iothub_pipeline = IoTHubPipeline(authentication_provider)
    iothub_pipeline.on_connected = MagicMock()
    iothub_pipeline.on_disconnected = MagicMock()
    yield iothub_pipeline
    iothub_pipeline.disconnect()


@pytest.fixture(scope="function")
def module_pipeline_adapter():
    connection_string_mod = connection_string_format_mod.format(
        fake_hostname, fake_device_id, fake_module_id, fake_shared_access_key
    )
    authentication_provider = SymmetricKeyAuthenticationProvider.parse(connection_string_mod)

    with patch(
        "azure.iot.device.iothub.pipeline.iothub_pipeline.pipeline_stages_mqtt.MQTTClientOperator"
    ):
        iothub_pipeline = IoTHubPipeline(authentication_provider)
    iothub_pipeline.on_connected = MagicMock()
    iothub_pipeline.on_disconnected = MagicMock()
    yield iothub_pipeline
    iothub_pipeline.disconnect()


class TestInstantiation(object):
    def test_instantiates_correctly(self, authentication_provider):
        trans = IoTHubPipeline(authentication_provider)
        assert trans._auth_provider == authentication_provider
        assert trans._pipeline is not None


class TestConnect:
    def test_connect_calls_connect_on_provider(self, device_pipeline_adapter):
        mock_mqtt_client_operator = device_pipeline_adapter._pipeline.client_operator
        device_pipeline_adapter.connect()
        mock_mqtt_client_operator.connect.assert_called_once_with(
            password=device_pipeline_adapter._auth_provider.get_current_sas_token(),
            client_certificate=None,
        )
        mock_mqtt_client_operator.on_mqtt_connected()

    def test_connected_state_handler_called_wth_new_state_once_provider_gets_connected(
        self, device_pipeline_adapter
    ):
        mock_mqtt_client_operator = device_pipeline_adapter._pipeline.client_operator

        device_pipeline_adapter.connect()
        mock_mqtt_client_operator.on_mqtt_connected()

        device_pipeline_adapter.on_connected.assert_called_once_with("connected")

    def test_connect_ignored_if_waiting_for_connect_complete(self, device_pipeline_adapter):
        mock_mqtt_client_operator = device_pipeline_adapter._pipeline.client_operator

        device_pipeline_adapter.connect()
        device_pipeline_adapter.connect()
        mock_mqtt_client_operator.on_mqtt_connected()

        mock_mqtt_client_operator.connect.assert_called_once_with(
            password=device_pipeline_adapter._auth_provider.get_current_sas_token(),
            client_certificate=None,
        )
        device_pipeline_adapter.on_connected.assert_called_once_with("connected")

    def test_connect_ignored_if_waiting_for_send_complete(self, device_pipeline_adapter):
        mock_mqtt_client_operator = device_pipeline_adapter._pipeline.client_operator

        device_pipeline_adapter.connect()
        mock_mqtt_client_operator.on_mqtt_connected()

        mock_mqtt_client_operator.reset_mock()
        device_pipeline_adapter.on_connected.reset_mock()

        device_pipeline_adapter.send_d2c_message(create_fake_message())
        device_pipeline_adapter.connect()

        mock_mqtt_client_operator.connect.assert_not_called()
        device_pipeline_adapter.on_connected.assert_not_called()

        mock_mqtt_client_operator.on_mqtt_published(0)

        mock_mqtt_client_operator.connect.assert_not_called()
        device_pipeline_adapter.on_connected.assert_not_called()


class TestSendEvent:
    def test_send_message_with_no_properties(self, device_pipeline_adapter):
        fake_msg = Message("Petrificus Totalus")

        mock_mqtt_client_operator = device_pipeline_adapter._pipeline.client_operator

        device_pipeline_adapter.connect()
        mock_mqtt_client_operator.on_mqtt_connected()
        device_pipeline_adapter.send_d2c_message(fake_msg)

        mock_mqtt_client_operator.connect.assert_called_once_with(
            password=device_pipeline_adapter._auth_provider.get_current_sas_token(),
            client_certificate=None,
        )
        mock_mqtt_client_operator.publish.assert_called_once_with(
            topic=fake_topic, payload=fake_msg.data, callback=ANY
        )

    def test_send_message_with_output_name(self, module_pipeline_adapter):
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

        mock_mqtt_client_operator = module_pipeline_adapter._pipeline.client_operator

        module_pipeline_adapter.connect()
        mock_mqtt_client_operator.on_mqtt_connected()
        module_pipeline_adapter.send_d2c_message(fake_msg)

        mock_mqtt_client_operator.connect.assert_called_once_with(
            password=module_pipeline_adapter._auth_provider.get_current_sas_token(),
            client_certificate=None,
        )
        mock_mqtt_client_operator.publish.assert_called_once_with(
            topic=fake_output_topic, payload=fake_msg.data, callback=ANY
        )

    def test_sendevent_calls_publish_on_provider(self, device_pipeline_adapter):
        fake_msg = create_fake_message()

        mock_mqtt_client_operator = device_pipeline_adapter._pipeline.client_operator

        device_pipeline_adapter.connect()
        mock_mqtt_client_operator.on_mqtt_connected()
        device_pipeline_adapter.send_d2c_message(fake_msg)

        mock_mqtt_client_operator.connect.assert_called_once_with(
            password=device_pipeline_adapter._auth_provider.get_current_sas_token(),
            client_certificate=None,
        )
        mock_mqtt_client_operator.publish.assert_called_once_with(
            topic=encoded_fake_topic, payload=fake_msg.data, callback=ANY
        )

    def test_send_d2c_message_queues_and_connects_before_sending(self, device_pipeline_adapter):
        fake_msg = create_fake_message()
        mock_mqtt_client_operator = device_pipeline_adapter._pipeline.client_operator

        # send an event
        device_pipeline_adapter.send_d2c_message(fake_msg)

        # verify that we called connect
        mock_mqtt_client_operator.connect.assert_called_once_with(
            password=device_pipeline_adapter._auth_provider.get_current_sas_token(),
            client_certificate=None,
        )

        # verify that we're not connected yet and verify that we havent't published yet
        device_pipeline_adapter.on_connected.assert_not_called()
        mock_mqtt_client_operator.publish.assert_not_called()

        # finish the connection
        mock_mqtt_client_operator.on_mqtt_connected()

        # verify that our connected callback was called and verify that we published the event
        device_pipeline_adapter.on_connected.assert_called_once_with("connected")
        mock_mqtt_client_operator.publish.assert_called_once_with(
            topic=encoded_fake_topic, payload=fake_msg.data, callback=ANY
        )

    def test_send_d2c_message_queues_if_waiting_for_connect_complete(self, device_pipeline_adapter):
        fake_msg = create_fake_message()

        mock_mqtt_client_operator = device_pipeline_adapter._pipeline.client_operator

        # start connecting and verify that we've called into the protocol wrapper
        device_pipeline_adapter.connect()
        mock_mqtt_client_operator.connect.assert_called_once_with(
            password=device_pipeline_adapter._auth_provider.get_current_sas_token(),
            client_certificate=None,
        )

        # send an event
        device_pipeline_adapter.send_d2c_message(fake_msg)

        # verify that we're not connected yet and verify that we havent't published yet
        device_pipeline_adapter.on_connected.assert_not_called()
        mock_mqtt_client_operator.publish.assert_not_called()

        # finish the connection
        mock_mqtt_client_operator.on_mqtt_connected()

        # verify that our connected callback was called and verify that we published the event
        device_pipeline_adapter.on_connected.assert_called_once_with("connected")
        mock_mqtt_client_operator.publish.assert_called_once_with(
            topic=encoded_fake_topic, payload=fake_msg.data, callback=ANY
        )

    def test_send_d2c_message_sends_overlapped_events(self, device_pipeline_adapter):
        fake_msg_1 = create_fake_message()
        fake_msg_2 = Message(fake_event_2)

        mock_mqtt_client_operator = device_pipeline_adapter._pipeline.client_operator

        # connect
        device_pipeline_adapter.connect()
        mock_mqtt_client_operator.on_mqtt_connected()

        # send an event
        callback_1 = MagicMock()
        device_pipeline_adapter.send_d2c_message(fake_msg_1, callback_1)
        mock_mqtt_client_operator.publish.assert_called_once_with(
            topic=encoded_fake_topic, payload=fake_msg_1.data, callback=ANY
        )

        # while we're waiting for that send to complete, send another event
        callback_2 = MagicMock()
        device_pipeline_adapter.send_d2c_message(fake_msg_2, callback_2)

        # verify that we've called publish twice and verify that neither send_d2c_message
        # has completed (because we didn't do anything here to complete it).
        assert mock_mqtt_client_operator.publish.call_count == 2
        callback_1.assert_not_called()
        callback_2.assert_not_called()

    def test_connect_send_disconnect(self, device_pipeline_adapter):
        fake_msg = create_fake_message()

        mock_mqtt_client_operator = device_pipeline_adapter._pipeline.client_operator

        # connect
        device_pipeline_adapter.connect()
        mock_mqtt_client_operator.on_mqtt_connected()

        # send an event
        device_pipeline_adapter.send_d2c_message(fake_msg)
        mock_mqtt_client_operator.on_mqtt_published(0)

        # disconnect
        device_pipeline_adapter.disconnect()
        mock_mqtt_client_operator.disconnect.assert_called_once_with()


class TestDisconnect:
    def test_disconnect_calls_disconnect_on_provider(self, device_pipeline_adapter):
        mock_mqtt_client_operator = device_pipeline_adapter._pipeline.client_operator

        device_pipeline_adapter.connect()
        mock_mqtt_client_operator.on_mqtt_connected()
        device_pipeline_adapter.disconnect()

        mock_mqtt_client_operator.disconnect.assert_called_once_with()

    def test_disconnect_ignored_if_already_disconnected(self, device_pipeline_adapter):
        mock_mqtt_client_operator = device_pipeline_adapter._pipeline.client_operator

        device_pipeline_adapter.disconnect(None)

        mock_mqtt_client_operator.disconnect.assert_not_called()

    def test_disconnect_calls_client_disconnect_callback(self, device_pipeline_adapter):
        mock_mqtt_client_operator = device_pipeline_adapter._pipeline.client_operator

        device_pipeline_adapter.connect()
        mock_mqtt_client_operator.on_mqtt_connected()

        device_pipeline_adapter.disconnect()
        mock_mqtt_client_operator.on_mqtt_disconnected()

        device_pipeline_adapter.on_disconnected.assert_called_once_with("disconnected")


class TestEnableInputMessage:
    def test_subscribe_calls_subscribe_on_provider(self, module_pipeline_adapter):
        mock_mqtt_client_operator = module_pipeline_adapter._pipeline.client_operator

        module_pipeline_adapter.connect()
        mock_mqtt_client_operator.on_mqtt_connected()
        module_pipeline_adapter.enable_feature(constant.INPUT_MSG)

        mock_mqtt_client_operator.subscribe.assert_called_once_with(
            topic=subscribe_input_message_topic, callback=ANY
        )

    def test_sets_input_message_status_to_enabled(self, module_pipeline_adapter):
        mock_mqtt_client_operator = module_pipeline_adapter._pipeline.client_operator

        module_pipeline_adapter.connect()
        mock_mqtt_client_operator.on_mqtt_connected()
        module_pipeline_adapter.enable_feature(constant.INPUT_MSG)

        assert module_pipeline_adapter.feature_enabled[constant.INPUT_MSG]


class TestDisableInputMessage:
    def test_unsubscribe_of_input_calls_unsubscribe_on_provider(self, module_pipeline_adapter):
        mock_mqtt_client_operator = module_pipeline_adapter._pipeline.client_operator

        module_pipeline_adapter.connect()
        mock_mqtt_client_operator.on_mqtt_connected()
        module_pipeline_adapter.disable_feature(constant.INPUT_MSG)

        mock_mqtt_client_operator.unsubscribe.assert_called_once_with(
            topic=subscribe_input_message_topic, callback=ANY
        )

    def test_sets_input_message_status_to_disabled(self, module_pipeline_adapter):
        mock_mqtt_client_operator = module_pipeline_adapter._pipeline.client_operator

        module_pipeline_adapter.connect()
        mock_mqtt_client_operator.on_mqtt_connected()
        module_pipeline_adapter.disable_feature(constant.INPUT_MSG)

        assert not module_pipeline_adapter.feature_enabled[constant.INPUT_MSG]


class TestEnableC2D:
    def test_subscribe_calls_subscribe_on_provider(self, device_pipeline_adapter):
        mock_mqtt_client_operator = device_pipeline_adapter._pipeline.client_operator

        device_pipeline_adapter.connect()
        mock_mqtt_client_operator.on_mqtt_connected()
        device_pipeline_adapter.enable_feature(constant.C2D_MSG)

        mock_mqtt_client_operator.subscribe.assert_called_once_with(
            topic=subscribe_c2d_topic, callback=ANY
        )

    def test_sets_c2d_message_status_to_enabled(self, device_pipeline_adapter):
        mock_mqtt_client_operator = device_pipeline_adapter._pipeline.client_operator

        device_pipeline_adapter.connect()
        mock_mqtt_client_operator.on_mqtt_connected()
        device_pipeline_adapter.enable_feature(constant.C2D_MSG)

        assert device_pipeline_adapter.feature_enabled[constant.C2D_MSG]


class TestDisableC2D:
    def test_unsubscribe_calls_unsubscribe_on_provider(self, device_pipeline_adapter):
        device_pipeline_adapter._c2d_topic = subscribe_c2d_topic
        mock_mqtt_client_operator = device_pipeline_adapter._pipeline.client_operator

        device_pipeline_adapter.connect()
        mock_mqtt_client_operator.on_mqtt_connected()
        device_pipeline_adapter.disable_feature(constant.C2D_MSG)

        mock_mqtt_client_operator.unsubscribe.assert_called_once_with(
            topic=subscribe_c2d_topic, callback=ANY
        )

    def test_sets_c2d_message_status_to_disabled(self, device_pipeline_adapter):
        device_pipeline_adapter._c2d_topic = subscribe_c2d_topic
        mock_mqtt_client_operator = device_pipeline_adapter._pipeline.client_operator

        device_pipeline_adapter.connect()
        mock_mqtt_client_operator.on_mqtt_connected()
        device_pipeline_adapter.disable_feature(constant.C2D_MSG)

        assert not device_pipeline_adapter.feature_enabled[constant.C2D_MSG]


class TestEnableMethods:
    def test_subscribe_calls_subscribe_on_provider(self, device_pipeline_adapter):
        mock_mqtt_client_operator = device_pipeline_adapter._pipeline.client_operator

        device_pipeline_adapter.connect()
        mock_mqtt_client_operator.on_mqtt_connected()
        device_pipeline_adapter.enable_feature(constant.METHODS)

        mock_mqtt_client_operator.subscribe.assert_called_once_with(
            topic=subscribe_methods_topic, callback=ANY
        )

    def test_sets_methods_status_to_enabled(self, device_pipeline_adapter):
        mock_mqtt_client_operator = device_pipeline_adapter._pipeline.client_operator

        device_pipeline_adapter.connect()
        mock_mqtt_client_operator.on_mqtt_connected()
        device_pipeline_adapter.enable_feature(constant.METHODS)

        assert device_pipeline_adapter.feature_enabled[constant.METHODS]


class TestDisableMethods:
    def test_unsubscribe_calls_unsubscribe_on_provider(self, device_pipeline_adapter):
        mock_mqtt_client_operator = device_pipeline_adapter._pipeline.client_operator

        device_pipeline_adapter.connect()
        mock_mqtt_client_operator.on_mqtt_connected()
        device_pipeline_adapter.disable_feature(constant.METHODS)

        mock_mqtt_client_operator.unsubscribe.assert_called_once_with(
            topic=subscribe_methods_topic, callback=ANY
        )

    def test_sets_method_status_to_disabled(self, device_pipeline_adapter):
        mock_mqtt_client_operator = device_pipeline_adapter._pipeline.client_operator

        device_pipeline_adapter.connect()
        mock_mqtt_client_operator.on_mqtt_connected()
        device_pipeline_adapter.disable_feature(constant.METHODS)

        assert not device_pipeline_adapter.feature_enabled[constant.METHODS]


@pytest.mark.skip(reason="Not implemented")
class TestSendMethodResponse(object):
    pass


@pytest.mark.skip(reason="Not implemented")
class TestGetTwin(object):
    pass


@pytest.mark.skip(reason="Not implmented")
class TestPatchTwinReportedProperties(object):
    pass
