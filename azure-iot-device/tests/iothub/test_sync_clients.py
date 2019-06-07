# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
import threading
import time
from azure.iot.device.iothub import IoTHubDeviceClient, IoTHubModuleClient
from azure.iot.device.iothub.pipeline import PipelineAdapter, constant
from azure.iot.device.iothub.models import Message, MethodRequest, MethodResponse
from azure.iot.device.iothub.sync_inbox import SyncClientInbox, InboxEmpty

# auth_provider and pipeline fixtures are implicitly included


class SharedClientInstantiationTests(object):
    @pytest.mark.it("Sets on_connected handler in pipeline")
    def test_sets_on_connected_handler_in_pipeline(self, client):
        assert client._pipeline.on_transport_connected is not None
        assert client._pipeline.on_transport_connected == client._on_state_change

    @pytest.mark.it("Sets on_disconnected handler in pipeline")
    def test_sets_on_disconnected_handler_in_pipeline(self, client):
        assert client._pipeline.on_transport_disconnected is not None
        assert client._pipeline.on_transport_disconnected == client._on_state_change

    @pytest.mark.it("Sets on_method_request_received handler in pipeline")
    def test_sets_on_method_request_received_handler_in_pipleline(self, client):
        assert client._pipeline.on_transport_method_request_received is not None
        assert (
            client._pipeline.on_transport_method_request_received
            == client._inbox_manager.route_method_request
        )


class SharedClientFromAuthenticationProviderTests(object):
    xfail_notimplemented = pytest.mark.xfail(raises=NotImplementedError, reason="Unimplemented")
    client_class = None  # Will be set in the config classes

    @pytest.mark.it("Instantiates the client with desired authentication/protocol combination")
    @pytest.mark.parametrize(
        "protocol,expected_pipeline",
        [
            pytest.param("mqtt", PipelineAdapter, id="mqtt"),
            pytest.param("amqp", None, id="amqp", marks=xfail_notimplemented),
            pytest.param("http", None, id="http", marks=xfail_notimplemented),
        ],
    )
    def test_instantiates_client(self, auth_provider, protocol, expected_pipeline):
        client = self.client_class.from_authentication_provider(auth_provider, protocol)
        assert isinstance(client, self.client_class)
        assert isinstance(client._pipeline, expected_pipeline)

    @pytest.mark.it("Handles variant protocol input")
    @pytest.mark.parametrize("auth_provider", ["SymmetricKey"], ids=[""], indirect=True)
    @pytest.mark.parametrize(
        "protocol,expected_pipeline",
        [
            pytest.param("MQTT", PipelineAdapter, id="ALL CAPS"),
            pytest.param("MqTt", PipelineAdapter, id="mIxEd CaSe"),
        ],
    )
    def test_boundary_case_protocol_name_format(self, auth_provider, protocol, expected_pipeline):
        client = self.client_class.from_authentication_provider(auth_provider, protocol)
        assert isinstance(client, self.client_class)
        assert isinstance(client._pipeline, expected_pipeline)

    @pytest.mark.it("Raises ValueError on invalid protocol input")
    @pytest.mark.parametrize("auth_provider", ["SymmetricKey"], ids=[""], indirect=True)
    # TODO: handle the auth_provider fixture differently so it doesn't result in empty [] in output
    def test_bad_protocol_input_raises_error(self, auth_provider):
        with pytest.raises(ValueError):
            self.client_class.from_authentication_provider(auth_provider, "bad input")


class SharedClientConnectTests(object):
    @pytest.mark.it("Begins a 'connect' pipeline operation")
    def test_calls_pipeline_connect(self, client, pipeline):
        client.connect()
        assert pipeline.connect.call_count == 1

    @pytest.mark.it("Waits for the completion of the 'connect' pipeline operation before returning")
    def test_waits_for_pipeline_op_completion(self, mocker, client_manual_cb, pipeline_manual_cb):
        client = client_manual_cb
        pipeline = pipeline_manual_cb
        event_init_mock = mocker.patch.object(threading, "Event")
        event_mock = event_init_mock.return_value

        def check_callback_completes_event():
            # Assert waiting for Event to complete
            assert event_mock.wait.call_count == 1
            assert event_mock.set.call_count == 0

            # Manually trigger callback
            cb = pipeline.connect.call_args[1]["callback"]
            cb()

            # Assert Event is now completed
            assert event_mock.set.call_count == 1

        event_mock.wait.side_effect = check_callback_completes_event

        client.connect()


class SharedClientDisconnectTests(object):
    @pytest.mark.it("Begins a 'disconnect' pipeline operation")
    def test_calls_pipeline_disconnect(self, client, pipeline):
        client.disconnect()
        assert pipeline.disconnect.call_count == 1

    @pytest.mark.it(
        "Waits for the completion of the 'disconnect' pipeline operation before returning"
    )
    def test_waits_for_pipeline_op_completion(self, mocker, client_manual_cb, pipeline_manual_cb):
        client = client_manual_cb
        pipeline = pipeline_manual_cb
        event_init_mock = mocker.patch.object(threading, "Event")
        event_mock = event_init_mock.return_value

        def check_callback_completes_event():
            # Assert waiting for Event to complete
            assert event_mock.wait.call_count == 1
            assert event_mock.set.call_count == 0

            # Manually trigger callback
            cb = pipeline.disconnect.call_args[1]["callback"]
            cb()

            # Assert Event is now completed
            assert event_mock.set.call_count == 1

        event_mock.wait.side_effect = check_callback_completes_event

        client.disconnect()


class SharedClientDisconnectEventTests(object):
    @pytest.mark.it("Clears all pending MethodRequests upon disconnect")
    def test_state_change_handler_clears_method_request_inboxes_on_disconnect(self, client, mocker):
        clear_method_request_spy = mocker.spy(client._inbox_manager, "clear_all_method_requests")
        client._on_state_change("disconnected")
        assert clear_method_request_spy.call_count == 1


# TODO: rename
class SharedClientSendEventTests(object):
    @pytest.mark.it("Begins a 'send_event' pipeline operation")
    def test_calls_pipeline_send_event(self, client, pipeline):
        message = Message("this is a message")
        client.send_event(message)
        assert pipeline.send_event.call_count == 1
        assert pipeline.send_event.call_args[0][0] is message

    @pytest.mark.it(
        "Waits for the completion of the 'send_event' pipeline operation before returning"
    )
    def test_waits_for_pipeline_op_completion(self, mocker, client_manual_cb, pipeline_manual_cb):
        client = client_manual_cb
        pipeline = pipeline_manual_cb
        event_init_mock = mocker.patch.object(threading, "Event")
        event_mock = event_init_mock.return_value

        def check_callback_completes_event():
            # Assert waiting for Event to complete
            assert event_mock.wait.call_count == 1
            assert event_mock.set.call_count == 0

            # Manually trigger callback
            cb = pipeline.send_event.call_args[1]["callback"]
            cb()

            # Assert Event is now completed
            assert event_mock.set.call_count == 1

        event_mock.wait.side_effect = check_callback_completes_event

        client.send_event(Message("this is a message"))

    @pytest.mark.it(
        "Wraps 'message' input parameter in a Message object if it is not a Message object"
    )
    @pytest.mark.parametrize(
        "message_input",
        [
            pytest.param("message", id="String input"),
            pytest.param(222, id="Integer input"),
            pytest.param(object(), id="Object input"),
            pytest.param(None, id="None input"),
            pytest.param([1, "str"], id="List input"),
            pytest.param({"a": 2}, id="Dictionary input"),
        ],
    )
    def test_wraps_data_in_message_and_calls_pipeline_send_event(
        self, client, pipeline, message_input
    ):
        client.send_event(message_input)
        assert pipeline.send_event.call_count == 1
        sent_message = pipeline.send_event.call_args[0][0]
        assert isinstance(sent_message, Message)
        assert sent_message.data == message_input


class SharedClientReceiveMethodRequestTests(object):
    @pytest.mark.it("Implicitly enables methods feature if not already enabled")
    @pytest.mark.parametrize(
        "method_name",
        [pytest.param(None, id="Generic Method"), pytest.param("method_x", id="Named Method")],
    )
    def test_enables_methods_only_if_not_already_enabled(
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

    @pytest.mark.it(
        "Returns a MethodRequest from the generic method inbox, if available, when called without method name"
    )
    def test_called_without_method_name_returns_method_request_from_generic_method_inbox(
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

    @pytest.mark.it(
        "Returns MethodRequest from the corresponding method inbox, if available, when called with a method name"
    )
    def test_called_with_method_name_returns_method_request_from_named_method_inbox(
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

    @pytest.mark.it("Can be called in various modes")
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

    @pytest.mark.it("Defaults to blocking mode with no timeout")
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

    @pytest.mark.it("Blocks until a method request is available, in blocking mode")
    @pytest.mark.parametrize(
        "method_name",
        [pytest.param(None, id="Generic Method"), pytest.param("method_x", id="Named Method")],
    )
    def test_no_method_request_in_inbox_blocking_mode(self, client, method_name):
        request = MethodRequest(request_id="1", name=method_name, payload={"key": "value"})

        inbox = client._inbox_manager.get_method_request_inbox(method_name)
        assert inbox.empty()

        def insert_item_after_delay():
            time.sleep(0.5)
            inbox._put(request)

        insertion_thread = threading.Thread(target=insert_item_after_delay)
        insertion_thread.start()

        received_request = client.receive_method_request(method_name, block=True)
        assert received_request is request
        # This proves that the blocking happens because 'received_request' can't be
        # 'request' until after a half second delay on the insert. But because the
        # 'received_request' IS 'request', it means that client.receive_method_request
        # did not return until after the delay.

    @pytest.mark.it(
        "Raises InboxEmpty exception after a timeout while blocking, in blocking mode with a specified timeout"
    )
    @pytest.mark.parametrize(
        "method_name",
        [pytest.param(None, id="Generic Method"), pytest.param("method_x", id="Named Method")],
    )
    def test_times_out_waiting_for_message_blocking_mode(self, client, method_name):
        with pytest.raises(InboxEmpty):
            client.receive_method_request(method_name, block=True, timeout=1)

    @pytest.mark.it(
        "Raises InboxEmpty exception immediately if there are no messages, in nonblocking mode"
    )
    @pytest.mark.parametrize(
        "method_name",
        [pytest.param(None, id="Generic Method"), pytest.param("method_x", id="Named Method")],
    )
    def test_no_message_in_inbox_nonblocking_mode(self, client, method_name):
        with pytest.raises(InboxEmpty):
            client.receive_method_request(method_name, block=False)


class SharedClientSendMethodResponseTests(object):
    @pytest.mark.it("Begins a 'send_method_response' pipeline operation")
    def test_send_method_response_calls_pipeline(self, client, pipeline):
        response = MethodResponse(request_id="1", status=200, payload={"key": "value"})
        client.send_method_response(response)
        assert pipeline.send_method_response.call_count == 1
        assert pipeline.send_method_response.call_args[0][0] is response

    @pytest.mark.it(
        "Waits for the completion of the 'send_method_response' pipeline operation before returning"
    )
    def test_waits_for_pipeline_op_completion(self, mocker, client_manual_cb, pipeline_manual_cb):
        client = client_manual_cb
        pipeline = pipeline_manual_cb
        event_init_mock = mocker.patch.object(threading, "Event")
        event_mock = event_init_mock.return_value

        def check_callback_completes_event():
            # Assert waiting for Event to complete
            assert event_mock.wait.call_count == 1
            assert event_mock.set.call_count == 0

            # Manually trigger callback
            cb = pipeline.send_method_response.call_args[1]["callback"]
            cb()

            # Assert Event is now completed
            assert event_mock.set.call_count == 1

        event_mock.wait.side_effect = check_callback_completes_event

        response = MethodResponse(request_id="1", status=200, payload={"key": "value"})
        client.send_method_response(response)


################
# DEVICE TESTS #
################
class IoTHubDeviceClientTestsConfig(object):
    client_class = IoTHubDeviceClient

    @pytest.fixture
    def client(self, pipeline):
        """This client automatically resolves callbacks sent to the pipeline.
        It should be used for the majority of tests.
        """
        return IoTHubDeviceClient(pipeline)

    @pytest.fixture
    def client_manual_cb(self, pipeline_manual_cb):
        """This client requires manual triggering of the callbacks sent to the pipeline.
        It should only be used for tests where manual control fo a callback is required.
        """
        return IoTHubDeviceClient(pipeline_manual_cb)


@pytest.mark.describe("IoTHubDeviceClient (Synchronous) - Instantiation")
class TestIoTHubDeviceClientInstantiation(
    IoTHubDeviceClientTestsConfig, SharedClientInstantiationTests
):
    @pytest.mark.it("Sets on_c2d_message_received handler in pipeline")
    def test_sets_on_c2d_message_received_handler_in_pipeline(self, client):
        assert client._pipeline.on_transport_c2d_message_received is not None
        assert (
            client._pipeline.on_transport_c2d_message_received
            == client._inbox_manager.route_c2d_message
        )


@pytest.mark.describe("IoTHubDeviceClient (Synchronous) - .from_authentication_provider()")
class TestIoTHubDeviceClientFromAuthenticationProvider(
    IoTHubDeviceClientTestsConfig, SharedClientFromAuthenticationProviderTests
):
    pass


@pytest.mark.describe("IoTHubDeviceClient (Synchronous) - .connect()")
class TestIoTHubDeviceClientConnect(IoTHubDeviceClientTestsConfig, SharedClientConnectTests):
    pass


@pytest.mark.describe("IoTHubDeviceClient (Synchronous) - .disconnect()")
class TestIoTHubDeviceClientDisconnect(IoTHubDeviceClientTestsConfig, SharedClientDisconnectTests):
    pass


@pytest.mark.describe("IoTHubDeviceClient (Synchronous) - EVENT: Disconnect")
class TestIoTHubDeviceClientDisconnectEvent(
    IoTHubDeviceClientTestsConfig, SharedClientDisconnectEventTests
):
    pass


@pytest.mark.describe("IoTHubDeviceClient (Synchronous) - .send_event()")
class TestIoTHubDeviceClientSendEvent(IoTHubDeviceClientTestsConfig, SharedClientSendEventTests):
    pass


@pytest.mark.describe("IoTHubDeviceClient (Synchronous) - .receive_c2d_message()")
class TestIoTHubDeviceClientReceiveC2DMessage(IoTHubDeviceClientTestsConfig):
    @pytest.mark.it("Implicitly enables C2D messaging feature if not already enabled")
    def test_enables_c2d_messaging_only_if_not_already_enabled(self, mocker, client, pipeline):
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

    @pytest.mark.it("Returns a message from the C2D inbox, if available")
    def test_returns_message_from_c2d_inbox(self, mocker, client):
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

    @pytest.mark.it("Can be called in various modes")
    @pytest.mark.parametrize(
        "block,timeout",
        [
            pytest.param(True, None, id="Blocking, no timeout"),
            pytest.param(True, 10, id="Blocking with timeout"),
            pytest.param(False, None, id="Nonblocking"),
        ],
    )
    def test_can_be_called_in_mode(self, mocker, client, block, timeout):
        inbox_mock = mocker.MagicMock(autospec=SyncClientInbox)
        mocker.patch.object(client._inbox_manager, "get_c2d_message_inbox", return_value=inbox_mock)

        client.receive_c2d_message(block=block, timeout=timeout)
        assert inbox_mock.get.call_count == 1
        assert inbox_mock.get.call_args == mocker.call(block=block, timeout=timeout)

    @pytest.mark.it("Defaults to blocking mode with no timeout")
    def test_default_mode(self, mocker, client):
        inbox_mock = mocker.MagicMock(autospec=SyncClientInbox)
        mocker.patch.object(client._inbox_manager, "get_c2d_message_inbox", return_value=inbox_mock)

        client.receive_c2d_message()
        assert inbox_mock.get.call_count == 1
        assert inbox_mock.get.call_args == mocker.call(block=True, timeout=None)

    @pytest.mark.it("Blocks until a message is available, in blocking mode")
    def test_no_message_in_inbox_blocking_mode(self, client):
        message = Message("this is a message")

        c2d_inbox = client._inbox_manager.get_c2d_message_inbox()
        assert c2d_inbox.empty()

        def insert_item_after_delay():
            time.sleep(0.5)
            c2d_inbox._put(message)

        insertion_thread = threading.Thread(target=insert_item_after_delay)
        insertion_thread.start()

        received_message = client.receive_c2d_message(block=True)
        assert received_message is message
        # This proves that the blocking happens because 'received_message' can't be
        # 'message' until after a half second delay on the insert. But because the
        # 'received_message' IS 'message', it means that client.receive_c2d_message
        # did not return until after the delay.

    @pytest.mark.it(
        "Raises InboxEmpty exception after a timeout while blocking, in blocking mode with a specified timeout"
    )
    def test_times_out_waiting_for_message_blocking_mode(self, client):
        with pytest.raises(InboxEmpty):
            client.receive_c2d_message(block=True, timeout=1)

    @pytest.mark.it(
        "Raises InboxEmpty exception immediately if there are no messages, in nonblocking mode"
    )
    def test_no_message_in_inbox_nonblocking_mode(self, client):
        with pytest.raises(InboxEmpty):
            client.receive_c2d_message(block=False)


@pytest.mark.describe("IoTHubDeviceClient (Synchronous) - .receive_method_request()")
class TestIoTHubDeviceClientReceiveMethodRequest(
    IoTHubDeviceClientTestsConfig, SharedClientReceiveMethodRequestTests
):
    pass


@pytest.mark.describe("IoTHubDeviceClient (Synchronous) - .send_method_response()")
class TestIoTHubDeviceClientSendMethodResponse(
    IoTHubDeviceClientTestsConfig, SharedClientSendMethodResponseTests
):
    pass


################
# MODULE TESTS #
################
class IoTHubModuleClientTestsConfig(object):
    client_class = IoTHubModuleClient

    @pytest.fixture
    def client(self, pipeline):
        """This client automatically resolves callbacks sent to the pipeline.
        It should be used for the majority of tests.
        """
        return IoTHubModuleClient(pipeline)

    @pytest.fixture
    def client_manual_cb(self, pipeline_manual_cb):
        """This client requires manual triggering of the callbacks sent to the pipeline.
        It should only be used for tests where manual control fo a callback is required.
        """
        return IoTHubModuleClient(pipeline_manual_cb)


@pytest.mark.describe("IoTHubModuleClient (Synchronous) - Instantiation")
class TestIoTHubModuleClientInstantiation(
    IoTHubModuleClientTestsConfig, SharedClientInstantiationTests
):
    @pytest.mark.it("Sets on_input_message_received handler in pipeline")
    def test_sets_on_input_message_received_handler_in_pipeline(self, client):
        assert client._pipeline.on_transport_input_message_received is not None
        assert (
            client._pipeline.on_transport_input_message_received
            == client._inbox_manager.route_input_message
        )


@pytest.mark.describe("IoTHubModuleClient (Synchronous) - .from_authentication_provider()")
class TestIoTHubModuleClientFromAuthenticationProvider(
    IoTHubModuleClientTestsConfig, SharedClientFromAuthenticationProviderTests
):
    pass


@pytest.mark.describe("IoTHubModuleClient (Synchronous) - .connect()")
class TestIoTHubModuleClientConnect(IoTHubModuleClientTestsConfig, SharedClientConnectTests):
    pass


@pytest.mark.describe("IoTHubModuleClient (Synchronous) - .disconnect()")
class TestIoTHubModuleClientDisconnect(IoTHubModuleClientTestsConfig, SharedClientDisconnectTests):
    pass


@pytest.mark.describe("IoTHubModuleClient (Synchronous) - EVENT: Disconnect")
class TestIoTHubModuleClientDisconnectEvent(
    IoTHubModuleClientTestsConfig, SharedClientDisconnectEventTests
):
    pass


@pytest.mark.describe("IoTHubModuleClient (Synchronous) - .send_event()")
class TestIoTHubNModuleClientSendEvent(IoTHubModuleClientTestsConfig, SharedClientSendEventTests):
    pass


@pytest.mark.describe("IoTHubModuleClient (Synchronous) - .send_to_output()")
class TestIoTHubModuleClientSendToOutput(IoTHubModuleClientTestsConfig):
    @pytest.mark.it("Begins a 'send_output_event' pipeline operation")
    def test_calls_pipeline_send_to_output(self, client, pipeline):
        message = Message("this is a message")
        output_name = "some_output"
        client.send_to_output(message, output_name)
        assert pipeline.send_output_event.call_count == 1
        assert pipeline.send_output_event.call_args[0][0] is message
        assert message.output_name == output_name

    @pytest.mark.it(
        "Waits for the completion of the 'send_output_event' pipeline operation before returning"
    )
    def test_waits_for_pipeline_op_completion(self, mocker, client_manual_cb, pipeline_manual_cb):
        client = client_manual_cb
        pipeline = pipeline_manual_cb
        event_init_mock = mocker.patch.object(threading, "Event")
        event_mock = event_init_mock.return_value

        def check_callback_completes_event():
            # Assert waiting for Event to complete
            assert event_mock.wait.call_count == 1
            assert event_mock.set.call_count == 0

            # Manually trigger callback
            cb = pipeline.send_output_event.call_args[1]["callback"]
            cb()

            # Assert Event is now completed
            assert event_mock.set.call_count == 1

        event_mock.wait.side_effect = check_callback_completes_event

        message = Message("this is a message")
        output_name = "some_output"
        client.send_to_output(message, output_name)

    @pytest.mark.it(
        "Wraps 'message' input parameter in Message object if it is not a Message object"
    )
    @pytest.mark.parametrize(
        "message_input",
        [
            pytest.param("message", id="String input"),
            pytest.param(222, id="Integer input"),
            pytest.param(object(), id="Object input"),
            pytest.param(None, id="None input"),
            pytest.param([1, "str"], id="List input"),
            pytest.param({"a": 2}, id="Dictionary input"),
        ],
    )
    def test_send_to_output_calls_pipeline_wraps_data_in_message(
        self, client, pipeline, message_input
    ):
        output_name = "some_output"
        client.send_to_output(message_input, output_name)
        assert pipeline.send_output_event.call_count == 1
        sent_message = pipeline.send_output_event.call_args[0][0]
        assert isinstance(sent_message, Message)
        assert sent_message.data == message_input


@pytest.mark.describe("IoTHubModuleClient (Synchronous) - .receive_input_message()")
class TestIoTHubModuleClientReceiveInputMessage(IoTHubModuleClientTestsConfig):
    @pytest.mark.it("Implicitly enables input messaging feature if not already enabled")
    def test_enables_input_messaging_only_if_not_already_enabled(self, mocker, client, pipeline):
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

    @pytest.mark.it("Returns a message from the input inbox, if available")
    def test_returns_message_from_input_inbox(self, mocker, client):
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

    @pytest.mark.it("Can be called in various modes")
    @pytest.mark.parametrize(
        "block,timeout",
        [
            pytest.param(True, None, id="Blocking, no timeout"),
            pytest.param(True, 10, id="Blocking with timeout"),
            pytest.param(False, None, id="Nonblocking"),
        ],
    )
    def test_can_be_called_in_mode(self, mocker, client, block, timeout):
        inbox_mock = mocker.MagicMock(autospec=SyncClientInbox)
        mocker.patch.object(
            client._inbox_manager, "get_input_message_inbox", return_value=inbox_mock
        )

        input_name = "some_input"
        client.receive_input_message(input_name, block=block, timeout=timeout)
        assert inbox_mock.get.call_count == 1
        assert inbox_mock.get.call_args == mocker.call(block=block, timeout=timeout)

    @pytest.mark.it("Defaults to blocking mode with no timeout")
    def test_default_mode(self, mocker, client):
        inbox_mock = mocker.MagicMock(autospec=SyncClientInbox)
        mocker.patch.object(
            client._inbox_manager, "get_input_message_inbox", return_value=inbox_mock
        )

        input_name = "some_input"
        client.receive_input_message(input_name)
        assert inbox_mock.get.call_count == 1
        assert inbox_mock.get.call_args == mocker.call(block=True, timeout=None)

    @pytest.mark.it("Blocks until a message is available, in blocking mode")
    def test_no_message_in_inbox_blocking_mode(self, client):
        input_name = "some_input"
        message = Message("this is a message")

        input_inbox = client._inbox_manager.get_input_message_inbox(input_name)
        assert input_inbox.empty()

        def insert_item_after_delay():
            time.sleep(0.5)
            input_inbox._put(message)

        insertion_thread = threading.Thread(target=insert_item_after_delay)
        insertion_thread.start()

        received_message = client.receive_input_message(input_name, block=True)
        assert received_message is message
        # This proves that the blocking happens because 'received_message' can't be
        # 'message' until after a half second delay on the insert. But because the
        # 'received_message' IS 'message', it means that client.receive_input_message
        # did not return until after the delay.

    @pytest.mark.it(
        "Raises InboxEmpty exception after a timeout while blocking, in blocking mode with a specified timeout"
    )
    def test_times_out_waiting_for_message_blocking_mode(self, client):
        input_name = "some_input"
        with pytest.raises(InboxEmpty):
            client.receive_input_message(input_name, block=True, timeout=1)

    @pytest.mark.it(
        "Raises InboxEmpty exception immediately if there are no messages, in nonblocking mode"
    )
    def test_no_message_in_inbox_nonblocking_mode(self, client):
        input_name = "some_input"
        with pytest.raises(InboxEmpty):
            client.receive_input_message(input_name, block=False)


@pytest.mark.describe("IoTHubModuleClient (Synchronous) - .receive_method_request()")
class TestIoTHubModuleClientReceiveMethodRequest(
    IoTHubModuleClientTestsConfig, SharedClientReceiveMethodRequestTests
):
    pass


@pytest.mark.describe("IoTHubModuleClient (Synchronous) - .send_method_response()")
class TestIoTHubModuleClientSendMethodResponse(
    IoTHubModuleClientTestsConfig, SharedClientSendMethodResponseTests
):
    pass
