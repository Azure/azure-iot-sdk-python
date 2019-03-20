# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
from azure.iot.hub.devicesdk import DeviceClient, ModuleClient
from azure.iot.hub.devicesdk.transport.mqtt import MQTTTransport
from azure.iot.hub.devicesdk import Message
from azure.iot.hub.devicesdk.sync_inbox import SyncClientInbox
from azure.iot.hub.devicesdk.transport import constant

# auth_provider and transport fixtures are implicitly included


class ClientSharedTests(object):
    client_class = None  # Will be set in child tests
    xfail_notimplemented = pytest.mark.xfail(raises=NotImplementedError, reason="Unimplemented")

    @pytest.mark.parametrize(
        "protocol,expected_transport",
        [
            pytest.param("mqtt", MQTTTransport, id="mqtt"),
            pytest.param("amqp", None, id="amqp", marks=xfail_notimplemented),
            pytest.param("http", None, id="http", marks=xfail_notimplemented),
        ],
    )
    def test_from_authentication_provider_instantiates_client(
        self, auth_provider, protocol, expected_transport
    ):
        client = self.client_class.from_authentication_provider(auth_provider, protocol)
        assert isinstance(client, self.client_class)
        assert isinstance(client._transport, expected_transport)
        assert client.state == "initial"

    @pytest.mark.parametrize("auth_provider", ["SymmetricKey"], ids=[""], indirect=True)
    @pytest.mark.parametrize(
        "protocol,expected_transport",
        [
            pytest.param("MQTT", MQTTTransport, id="ALL CAPS"),
            pytest.param("MqTt", MQTTTransport, id="mIxEd CaSe"),
        ],
    )
    def test_from_authentication_provider_boundary_case_transport_name(
        self, auth_provider, protocol, expected_transport
    ):
        client = self.client_class.from_authentication_provider(auth_provider, protocol)
        assert isinstance(client, self.client_class)
        assert isinstance(client._transport, expected_transport)

    @pytest.mark.parametrize("auth_provider", ["SymmetricKey"], ids=[""], indirect=True)
    def test_from_authentication_provider_bad_input_raises_error_transport_name(
        self, auth_provider
    ):
        with pytest.raises(ValueError):
            self.client_class.from_authentication_provider(auth_provider, "bad input")

    def test_connect_calls_transport(self, client, transport):
        client.connect()
        assert transport.connect.call_count == 1

    def test_disconnect_calls_transport(self, client, transport):
        client.disconnect()
        assert transport.disconnect.call_count == 1

    def test_send_event_calls_transport(self, client, transport):
        message = Message("this is a message")
        client.send_event(message)
        assert transport.send_event.call_count == 1
        assert transport.send_event.call_args[0][0] == message

    def test_send_event_calls_transport_wraps_data_in_message(self, client, transport):
        naked_string = "this is a message"
        client.send_event(naked_string)
        assert transport.send_event.call_count == 1
        sent_message = transport.send_event.call_args[0][0]
        assert isinstance(sent_message, Message)
        assert sent_message.data == naked_string

    @pytest.mark.skip(reason="Not Implemented")
    def test_receive_method_request_enables_methods_only_if_not_already_enabled(
        self, client, transport
    ):
        pass

    @pytest.mark.skip(reason="Not Implemented")
    def test_receive_method_request_called_without_method_name_returns_method_request_from_generic_method_inbox(
        self, client, tranposrt
    ):
        pass

    @pytest.mark.skip(reason="Not Implemented")
    def test_receive_method_request_called_with_method_name_returns_method_request_from_named_method_inbox(
        self, client, transport
    ):
        pass

    @pytest.mark.skip(reason="Not Implemented")
    @pytest.mark.parametrize(
        "block,timeout",
        [
            pytest.param(True, None, id="Blocking, no timeout"),
            pytest.param(True, 10, id="Blocking with timeout"),
            pytest.param(False, None, id="Nonblocking"),
        ],
    )
    def test_receive_method_request_can_be_called_in_mode(self, mocker, client, block, timeout):
        pass

    @pytest.mark.skip(reason="Not Implemented")
    def test_send_method_response_calls_transport(self, client, transport):
        pass


class TestModuleClient(ClientSharedTests):
    client_class = ModuleClient

    @pytest.fixture
    def client(self, transport):
        return ModuleClient(transport)

    def test_send_to_output_calls_transport(self, client, transport):
        message = Message("this is a message")
        output_name = "some_output"
        client.send_to_output(message, output_name)
        assert transport.send_output_event.call_count == 1
        assert transport.send_output_event.call_args[0][0] == message
        assert message.output_name == output_name

    def test_send_to_output_calls_transport_wraps_data_in_message(self, client, transport):
        naked_string = "this is a message"
        output_name = "some_output"
        client.send_to_output(naked_string, output_name)
        assert transport.send_output_event.call_count == 1
        sent_message = transport.send_output_event.call_args[0][0]
        assert isinstance(sent_message, Message)
        assert sent_message.data == naked_string

    def test_receive_input_message_enables_input_messaging_only_if_not_already_enabled(
        self, mocker, client, transport
    ):
        mocker.patch.object(SyncClientInbox, "get")  # patch this receive_input_message won't block
        input_name = "some_input"

        # Verify Input Messaging enabled if not enabled
        transport.feature_enabled.__getitem__.return_value = (
            False
        )  # Input Messages will appear disabled
        client.receive_input_message(input_name)
        assert transport.enable_feature.call_count == 1
        assert transport.enable_feature.call_args[0][0] == constant.INPUT_MSG

        transport.enable_feature.reset_mock()

        # Verify Input Messaging not enabled if already enabled
        transport.feature_enabled.__getitem__.return_value = (
            True
        )  # Input Messages will appear enabled
        client.receive_input_message(input_name)
        assert transport.enable_feature.call_count == 0

    def test_receive_input_message_returns_message_from_input_inbox(self, mocker, client):
        message = Message("this is a message")
        inbox_mock = mocker.MagicMock(autospec=SyncClientInbox)
        inbox_mock.get.return_value = message
        manager_get_inbox_mock = mocker.patch.object(
            client._inbox_manager, "get_input_message_inbox", return_value=inbox_mock
        )

        input_name = "some_input"
        received_message = client.receive_input_message(input_name)
        assert manager_get_inbox_mock.call_count == 1
        assert manager_get_inbox_mock.call_args == mocker.call(input_name)
        assert inbox_mock.get.call_count == 1
        assert received_message is message

    @pytest.mark.parametrize(
        "block,timeout",
        [
            pytest.param(True, None, id="Blocking, no timeout"),
            pytest.param(True, 10, id="Blocking with timeout"),
            pytest.param(False, None, id="Nonblocking"),
        ],
    )
    def test_receive_c2d_message_can_called_in_mode(self, mocker, client, block, timeout):
        inbox_mock = mocker.MagicMock(autospec=SyncClientInbox)
        mocker.patch.object(
            client._inbox_manager, "get_input_message_inbox", return_value=inbox_mock
        )

        input_name = "some_input"
        client.receive_input_message(input_name, block=block, timeout=timeout)
        assert inbox_mock.get.call_count == 1
        assert inbox_mock.get.call_args == mocker.call(block=block, timeout=timeout)


class TestDeviceClient(ClientSharedTests):
    client_class = DeviceClient

    @pytest.fixture
    def client(self, transport):
        return DeviceClient(transport)

    def test_receive_c2d_message_enables_c2d_messaging_only_if_not_already_enabled(
        self, mocker, client, transport
    ):
        mocker.patch.object(SyncClientInbox, "get")  # patch this receive_c2d_message won't block

        # Verify C2D Messaging enabled if not enabled
        transport.feature_enabled.__getitem__.return_value = False  # C2D will appear disabled
        client.receive_c2d_message()
        assert transport.enable_feature.call_count == 1
        assert transport.enable_feature.call_args[0][0] == constant.C2D_MSG

        transport.enable_feature.reset_mock()

        # Verify C2D Messaging not enabled if already enabled
        transport.feature_enabled.__getitem__.return_value = True  # C2D will appear enabled
        client.receive_c2d_message()
        assert transport.enable_feature.call_count == 0

    def test_receive_c2d_message_returns_message_from_c2d_inbox(self, mocker, client):
        message = Message("this is a message")
        inbox_mock = mocker.MagicMock(autospec=SyncClientInbox)
        inbox_mock.get.return_value = message
        manager_get_inbox_mock = mocker.patch.object(
            client._inbox_manager, "get_c2d_message_inbox", return_value=inbox_mock
        )

        received_message = client.receive_c2d_message()
        assert manager_get_inbox_mock.call_count == 1
        assert inbox_mock.get.call_count == 1
        assert received_message is message

    @pytest.mark.parametrize(
        "block,timeout",
        [
            pytest.param(True, None, id="Blocking, no timeout"),
            pytest.param(True, 10, id="Blocking with timeout"),
            pytest.param(False, None, id="Nonblocking"),
        ],
    )
    def test_receive_c2d_message_can_called_in_mode(self, mocker, client, block, timeout):
        inbox_mock = mocker.MagicMock(autospec=SyncClientInbox)
        mocker.patch.object(client._inbox_manager, "get_c2d_message_inbox", return_value=inbox_mock)

        client.receive_c2d_message(block=block, timeout=timeout)
        assert inbox_mock.get.call_count == 1
        assert inbox_mock.get.call_args == mocker.call(block=block, timeout=timeout)
