# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
from azure.iot.device.iothub import IoTHubDeviceClient, IoTHubModuleClient
from azure.iot.device.iothub.pipeline import PipelineAdapter, constant
from azure.iot.device.iothub.models import Message, MethodRequest, MethodResponse
from azure.iot.device.iothub.sync_inbox import SyncClientInbox

# auth_provider and pipeline fixtures are implicitly included


class ClientSharedTests(object):
    client_class = None  # Will be set in child tests
    xfail_notimplemented = pytest.mark.xfail(raises=NotImplementedError, reason="Unimplemented")

    @pytest.mark.parametrize(
        "protocol,expected_pipeline",
        [
            pytest.param("mqtt", PipelineAdapter, id="mqtt"),
            pytest.param("amqp", None, id="amqp", marks=xfail_notimplemented),
            pytest.param("http", None, id="http", marks=xfail_notimplemented),
        ],
    )
    def test_from_authentication_provider_instantiates_client(
        self, auth_provider, protocol, expected_pipeline
    ):
        client = self.client_class.from_authentication_provider(auth_provider, protocol)
        assert isinstance(client, self.client_class)
        assert isinstance(client._pipeline, expected_pipeline)

    @pytest.mark.parametrize("auth_provider", ["SymmetricKey"], ids=[""], indirect=True)
    @pytest.mark.parametrize(
        "protocol,expected_pipeline",
        [
            pytest.param("MQTT", PipelineAdapter, id="ALL CAPS"),
            pytest.param("MqTt", PipelineAdapter, id="mIxEd CaSe"),
        ],
    )
    def test_from_authentication_provider_boundary_case_transport_name(
        self, auth_provider, protocol, expected_pipeline
    ):
        client = self.client_class.from_authentication_provider(auth_provider, protocol)
        assert isinstance(client, self.client_class)
        assert isinstance(client._pipeline, expected_pipeline)

    @pytest.mark.parametrize("auth_provider", ["SymmetricKey"], ids=[""], indirect=True)
    def test_from_authentication_provider_bad_input_raises_error_transport_name(
        self, auth_provider
    ):
        with pytest.raises(ValueError):
            self.client_class.from_authentication_provider(auth_provider, "bad input")

    def test_instantiation_sets_on_connected_handler_in_transport(self, client):
        assert client._pipeline.on_transport_connected is not None
        assert client._pipeline.on_transport_connected == client._on_state_change

    def test_instantiation_sets_on_disconnected_handler_in_transport(self, client):
        assert client._pipeline.on_transport_disconnected is not None
        assert client._pipeline.on_transport_disconnected == client._on_state_change

    def test_instantiation_sets_on_method_request_received_handler_in_transport(self, client):
        assert client._pipeline.on_transport_method_request_received is not None
        assert (
            client._pipeline.on_transport_method_request_received
            == client._inbox_manager.route_method_request
        )

    def test_state_change_handler_clears_method_request_inboxes_on_disconnect(self, client, mocker):
        clear_method_request_spy = mocker.spy(client._inbox_manager, "clear_all_method_requests")
        client._on_state_change("disconnected")
        assert clear_method_request_spy.call_count == 1

    def test_connect_calls_transport(self, client, pipeline):
        client.connect()
        assert pipeline.connect.call_count == 1

    def test_disconnect_calls_transport(self, client, pipeline):
        client.disconnect()
        assert pipeline.disconnect.call_count == 1

    def test_send_event_calls_transport(self, client, pipeline):
        message = Message("this is a message")
        client.send_event(message)
        assert pipeline.send_event.call_count == 1
        assert pipeline.send_event.call_args[0][0] is message

    def test_send_event_calls_transport_wraps_data_in_message(self, client, pipeline):
        naked_string = "this is a message"
        client.send_event(naked_string)
        assert pipeline.send_event.call_count == 1
        sent_message = pipeline.send_event.call_args[0][0]
        assert isinstance(sent_message, Message)
        assert sent_message.data == naked_string

    @pytest.mark.parametrize(
        "method_name",
        [pytest.param(None, id="Generic Method"), pytest.param("method_x", id="Named Method")],
    )
    def test_receive_method_request_enables_methods_only_if_not_already_enabled(
        self, mocker, client, pipeline, method_name
    ):
        mocker.patch.object(SyncClientInbox, "get")  # patch this receive_method_request won't block

        # Verify Input Messaging enabled if not enabled
        pipeline.feature_enabled.__getitem__.return_value = (
            False
        )  # Method Requests will appear disabled
        client.receive_method_request(method_name)
        assert pipeline.enable_feature.call_count == 1
        assert pipeline.enable_feature.call_args[0][0] == constant.METHODS

        pipeline.enable_feature.reset_mock()

        # Verify Input Messaging not enabled if already enabled
        pipeline.feature_enabled.__getitem__.return_value = (
            True
        )  # Input Messages will appear enabled
        client.receive_method_request(method_name)
        assert pipeline.enable_feature.call_count == 0

    def test_receive_method_request_called_without_method_name_returns_method_request_from_generic_method_inbox(
        self, mocker, client
    ):
        request = MethodRequest(request_id="1", name="some_method", payload={"key": "value"})
        inbox_mock = mocker.MagicMock(autospec=SyncClientInbox)
        inbox_mock.get.return_value = request
        manager_get_inbox_mock = mocker.patch.object(
            target=client._inbox_manager,
            attribute="get_method_request_inbox",
            return_value=inbox_mock,
        )

        received_request = client.receive_method_request()
        assert manager_get_inbox_mock.call_count == 1
        assert manager_get_inbox_mock.call_args == mocker.call(None)
        assert inbox_mock.get.call_count == 1
        assert received_request is received_request

    def test_receive_method_request_called_with_method_name_returns_method_request_from_named_method_inbox(
        self, mocker, client
    ):
        method_name = "some_method"
        request = MethodRequest(request_id="1", name=method_name, payload={"key": "value"})
        inbox_mock = mocker.MagicMock(autospec=SyncClientInbox)
        inbox_mock.get.return_value = request
        manager_get_inbox_mock = mocker.patch.object(
            target=client._inbox_manager,
            attribute="get_method_request_inbox",
            return_value=inbox_mock,
        )

        received_request = client.receive_method_request(method_name)
        assert manager_get_inbox_mock.call_count == 1
        assert manager_get_inbox_mock.call_args == mocker.call(method_name)
        assert inbox_mock.get.call_count == 1
        assert received_request is received_request

    @pytest.mark.parametrize(
        "method_name",
        [pytest.param(None, id="Generic Method"), pytest.param("method_x", id="Named Method")],
    )
    @pytest.mark.parametrize(
        "block,timeout",
        [
            pytest.param(True, None, id="Blocking, no timeout"),
            pytest.param(True, 10, id="Blocking with timeout"),
            pytest.param(False, None, id="Nonblocking"),
        ],
    )
    def test_receive_method_request_can_be_called_in_mode(
        self, mocker, client, block, timeout, method_name
    ):
        inbox_mock = mocker.MagicMock(autospec=SyncClientInbox)
        mocker.patch.object(
            target=client._inbox_manager,
            attribute="get_method_request_inbox",
            return_value=inbox_mock,
        )

        client.receive_method_request(method_name=method_name, block=block, timeout=timeout)
        assert inbox_mock.get.call_count == 1
        assert inbox_mock.get.call_args == mocker.call(block=block, timeout=timeout)

    @pytest.mark.parametrize(
        "method_name",
        [pytest.param(None, id="Generic Method"), pytest.param("method_x", id="Named Method")],
    )
    def test_receive_method_request_default_mode(self, mocker, client, method_name):
        inbox_mock = mocker.MagicMock(autospec=SyncClientInbox)
        mocker.patch.object(
            target=client._inbox_manager,
            attribute="get_method_request_inbox",
            return_value=inbox_mock,
        )
        client.receive_method_request(method_name=method_name)
        assert inbox_mock.get.call_count == 1
        assert inbox_mock.get.call_args == mocker.call(block=True, timeout=None)

    def test_send_method_response_calls_transport(self, client, pipeline):
        response = MethodResponse(request_id="1", status=200, payload={"key": "value"})
        client.send_method_response(response)
        assert pipeline.send_method_response.call_count == 1
        assert pipeline.send_method_response.call_args[0][0] is response


@pytest.mark.describe("IoTHubModuleClient (Synchronous)")
class TestIoTHubModuleClient(ClientSharedTests):
    client_class = IoTHubModuleClient

    @pytest.fixture
    def client(self, pipeline):
        return IoTHubModuleClient(pipeline)

    def test_instantiation_sets_on_input_message_received_handler_in_transport(self, client):
        assert client._pipeline.on_transport_input_message_received is not None
        assert (
            client._pipeline.on_transport_input_message_received
            == client._inbox_manager.route_input_message
        )

    def test_send_to_output_calls_transport(self, client, pipeline):
        message = Message("this is a message")
        output_name = "some_output"
        client.send_to_output(message, output_name)
        assert pipeline.send_output_event.call_count == 1
        assert pipeline.send_output_event.call_args[0][0] is message
        assert message.output_name == output_name

    def test_send_to_output_calls_transport_wraps_data_in_message(self, client, pipeline):
        naked_string = "this is a message"
        output_name = "some_output"
        client.send_to_output(naked_string, output_name)
        assert pipeline.send_output_event.call_count == 1
        sent_message = pipeline.send_output_event.call_args[0][0]
        assert isinstance(sent_message, Message)
        assert sent_message.data == naked_string

    def test_receive_input_message_enables_input_messaging_only_if_not_already_enabled(
        self, mocker, client, pipeline
    ):
        mocker.patch.object(SyncClientInbox, "get")  # patch this receive_input_message won't block
        input_name = "some_input"

        # Verify Input Messaging enabled if not enabled
        pipeline.feature_enabled.__getitem__.return_value = (
            False
        )  # Input Messages will appear disabled
        client.receive_input_message(input_name)
        assert pipeline.enable_feature.call_count == 1
        assert pipeline.enable_feature.call_args[0][0] == constant.INPUT_MSG

        pipeline.enable_feature.reset_mock()

        # Verify Input Messaging not enabled if already enabled
        pipeline.feature_enabled.__getitem__.return_value = (
            True
        )  # Input Messages will appear enabled
        client.receive_input_message(input_name)
        assert pipeline.enable_feature.call_count == 0

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
    def test_receive_input_message_can_be_called_in_mode(self, mocker, client, block, timeout):
        inbox_mock = mocker.MagicMock(autospec=SyncClientInbox)
        mocker.patch.object(
            client._inbox_manager, "get_input_message_inbox", return_value=inbox_mock
        )

        input_name = "some_input"
        client.receive_input_message(input_name, block=block, timeout=timeout)
        assert inbox_mock.get.call_count == 1
        assert inbox_mock.get.call_args == mocker.call(block=block, timeout=timeout)

    def test_receive_input_message_default_mode(self, mocker, client):
        inbox_mock = mocker.MagicMock(autospec=SyncClientInbox)
        mocker.patch.object(
            client._inbox_manager, "get_input_message_inbox", return_value=inbox_mock
        )

        input_name = "some_input"
        client.receive_input_message(input_name)
        assert inbox_mock.get.call_count == 1
        assert inbox_mock.get.call_args == mocker.call(block=True, timeout=None)


@pytest.mark.describe("IoTHubDeviceClient (Synchronous)")
class TestIoTHubDeviceClient(ClientSharedTests):
    client_class = IoTHubDeviceClient

    @pytest.fixture
    def client(self, pipeline):
        return IoTHubDeviceClient(pipeline)

    def test_instantiation_sets_on_c2d_message_received_handler_in_transport(self, client):
        assert client._pipeline.on_transport_c2d_message_received is not None
        assert (
            client._pipeline.on_transport_c2d_message_received
            == client._inbox_manager.route_c2d_message
        )

    def test_receive_c2d_message_enables_c2d_messaging_only_if_not_already_enabled(
        self, mocker, client, pipeline
    ):
        mocker.patch.object(SyncClientInbox, "get")  # patch this so receive_c2d_message won't block

        # Verify C2D Messaging enabled if not enabled
        pipeline.feature_enabled.__getitem__.return_value = False  # C2D will appear disabled
        client.receive_c2d_message()
        assert pipeline.enable_feature.call_count == 1
        assert pipeline.enable_feature.call_args[0][0] == constant.C2D_MSG

        pipeline.enable_feature.reset_mock()

        # Verify C2D Messaging not enabled if already enabled
        pipeline.feature_enabled.__getitem__.return_value = True  # C2D will appear enabled
        client.receive_c2d_message()
        assert pipeline.enable_feature.call_count == 0

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
    def test_receive_c2d_message_can_be_called_in_mode(self, mocker, client, block, timeout):
        inbox_mock = mocker.MagicMock(autospec=SyncClientInbox)
        mocker.patch.object(client._inbox_manager, "get_c2d_message_inbox", return_value=inbox_mock)

        client.receive_c2d_message(block=block, timeout=timeout)
        assert inbox_mock.get.call_count == 1
        assert inbox_mock.get.call_args == mocker.call(block=block, timeout=timeout)

    def test_receive_c2d_message_default_mode(self, mocker, client):
        inbox_mock = mocker.MagicMock(autospec=SyncClientInbox)
        mocker.patch.object(client._inbox_manager, "get_c2d_message_inbox", return_value=inbox_mock)

        client.receive_c2d_message()
        assert inbox_mock.get.call_count == 1
        assert inbox_mock.get.call_args == mocker.call(block=True, timeout=None)
