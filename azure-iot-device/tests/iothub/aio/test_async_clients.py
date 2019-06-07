# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
import asyncio
import threading
import time
from azure.iot.device.iothub.aio import IoTHubDeviceClient, IoTHubModuleClient
from azure.iot.device.iothub.pipeline import PipelineAdapter, constant
from azure.iot.device.iothub.models import Message, MethodRequest, MethodResponse
from azure.iot.device.iothub.aio.async_inbox import AsyncClientInbox
from azure.iot.device.common import async_adapter

# auth_provider and pipeline fixtures are implicitly included


pytestmark = pytest.mark.asyncio


async def create_completed_future(result=None):
    f = asyncio.Future()
    f.set_result(result)
    return f


class SharedClientInstantiationTests(object):
    @pytest.mark.it("Sets on_connected handler in pipeline")
    async def test_sets_on_connected_handler_in_pipeline(self, client):
        assert client._pipeline.on_transport_connected is not None
        assert client._pipeline.on_transport_connected == client._on_state_change

    @pytest.mark.it("Sets on_disconnected handler in pipeline")
    async def test_sets_on_disconnected_handler_in_pipeline(self, client):
        assert client._pipeline.on_transport_disconnected is not None
        assert client._pipeline.on_transport_disconnected == client._on_state_change

    @pytest.mark.it("Sets on_method_request_received handler in pipeline")
    async def test_sets_on_method_request_received_handler_in_pipleline(self, client):
        assert client._pipeline.on_transport_method_request_received is not None
        assert (
            client._pipeline.on_transport_method_request_received
            == client._inbox_manager.route_method_request
        )


class SharedClientFromAuthenticationProviderTests(object):
    xfail_notimplemented = pytest.mark.xfail(raises=NotImplementedError, reason="Unimplemented")
    client_class = None  # Will be set in child classes

    @pytest.mark.it("Instantiates the client with desired authentication/protocol combination")
    @pytest.mark.parametrize(
        "protocol,expected_pipeline",
        [
            pytest.param("mqtt", PipelineAdapter, id="mqtt"),
            pytest.param("amqp", None, id="amqp", marks=xfail_notimplemented),
            pytest.param("http", None, id="http", marks=xfail_notimplemented),
        ],
    )
    async def test_instantiates_client(self, auth_provider, protocol, expected_pipeline):
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
    async def test_boundary_case_protocol_name_format(
        self, auth_provider, protocol, expected_pipeline
    ):
        client = self.client_class.from_authentication_provider(auth_provider, protocol)
        assert isinstance(client, self.client_class)
        assert isinstance(client._pipeline, expected_pipeline)

    @pytest.mark.it("Raises ValueError on invalid protocol input")
    @pytest.mark.parametrize("auth_provider", ["SymmetricKey"], ids=[""], indirect=True)
    # TODO: handle the auth_provider fixture differently so it doesn't result in empty [] in output
    async def test_bad_protocol_input_raises_error(self, auth_provider):
        with pytest.raises(ValueError):
            self.client_class.from_authentication_provider(auth_provider, "bad input")


class SharedClientConnectTests(object):
    @pytest.mark.it("Begins a 'connect' pipeline operation")
    async def test_calls_pipeline_connect(self, client, pipeline):
        await client.connect()
        assert pipeline.connect.call_count == 1

    @pytest.mark.it("Waits for the completion of the 'connect' pipeline operation before returning")
    async def test_waits_for_pipeline_op_completion(self, mocker, client, pipeline):
        cb_mock = mocker.patch.object(async_adapter, "AwaitableCallback").return_value
        cb_mock.completion.return_value = await create_completed_future(None)

        await client.connect()

        # Assert callback is sent to pipeline
        assert pipeline.connect.call_args[1]["callback"] is cb_mock
        # Assert callback completion is waited upon
        assert cb_mock.completion.call_count == 1


class SharedClientDisconnectTests(object):
    @pytest.mark.it("Begins a 'disconnect' pipeline operation")
    async def test_calls_pipeline_disconnect(self, client, pipeline):
        await client.disconnect()
        assert pipeline.disconnect.call_count == 1

    @pytest.mark.it(
        "Waits for the completion of the 'disconnect' pipeline operation before returning"
    )
    async def test_waits_for_pipeline_op_completion(self, mocker, client, pipeline):
        cb_mock = mocker.patch.object(async_adapter, "AwaitableCallback").return_value
        cb_mock.completion.return_value = await create_completed_future(None)

        await client.disconnect()

        # Assert callback is sent to pipeline
        assert pipeline.disconnect.call_args[1]["callback"] is cb_mock
        # Assert callback completion is waited upon
        assert cb_mock.completion.call_count == 1


class SharedClientDisconnectEventTests(object):
    @pytest.mark.it("Clears all pending MethodRequests upon disconnect")
    async def test_state_change_handler_clears_method_request_inboxes_on_disconnect(
        self, client, mocker
    ):
        clear_method_request_spy = mocker.spy(client._inbox_manager, "clear_all_method_requests")
        client._on_state_change("disconnected")
        assert clear_method_request_spy.call_count == 1


# TODO: rename
class SharedClientSendEventTests(object):
    @pytest.mark.it("Begins a 'send_event' pipeline operation")
    async def test_calls_pipeline_send_event(self, client, pipeline):
        message = Message("this is a message")
        await client.send_event(message)
        assert pipeline.send_event.call_count == 1
        assert pipeline.send_event.call_args[0][0] is message

    @pytest.mark.it(
        "Waits for the completion of the 'send_event' pipeline operation before returning"
    )
    async def test_waits_for_pipeline_op_completion(self, mocker, client, pipeline):
        cb_mock = mocker.patch.object(async_adapter, "AwaitableCallback").return_value
        cb_mock.completion.return_value = await create_completed_future(None)

        message = Message("this is a message")
        await client.send_event(message)

        # Assert callback is sent to pipeline
        assert pipeline.send_event.call_args[1]["callback"] is cb_mock
        # Assert callback completion is waited upon
        assert cb_mock.completion.call_count == 1

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
    async def test_wraps_data_in_message_and_calls_pipeline_send_event(
        self, client, pipeline, message_input
    ):
        await client.send_event(message_input)
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
    async def test_enables_methods_only_if_not_already_enabled(
        self, mocker, client, pipeline, method_name
    ):
        # patch this so receive_method_request won't block
        mocker.patch.object(
            AsyncClientInbox, "get", return_value=(await create_completed_future(None))
        )

        # Verify Input Messaging enabled if not enabled
        pipeline.feature_enabled.__getitem__.return_value = (
            False
        )  # Method Requests will appear disabled
        await client.receive_method_request(method_name)
        assert pipeline.enable_feature.call_count == 1
        assert pipeline.enable_feature.call_args[0][0] == constant.METHODS

        pipeline.enable_feature.reset_mock()

        # Verify Input Messaging not enabled if already enabled
        pipeline.feature_enabled.__getitem__.return_value = (
            True
        )  # Input Messages will appear enabled
        await client.receive_method_request(method_name)
        assert pipeline.enable_feature.call_count == 0

    @pytest.mark.it(
        "Returns a MethodRequest from the generic method inbox, if available, when called without method name"
    )
    async def test_called_without_method_name_returns_method_request_from_generic_method_inbox(
        self, mocker, client
    ):
        request = MethodRequest(request_id="1", name="some_method", payload={"key": "value"})
        inbox_mock = mocker.MagicMock(autospec=AsyncClientInbox)
        inbox_mock.get.return_value = await create_completed_future(request)
        manager_get_inbox_mock = mocker.patch.object(
            target=client._inbox_manager,
            attribute="get_method_request_inbox",
            return_value=inbox_mock,
        )

        received_request = await client.receive_method_request()
        assert manager_get_inbox_mock.call_count == 1
        assert manager_get_inbox_mock.call_args == mocker.call(None)
        assert inbox_mock.get.call_count == 1
        assert received_request is received_request

    @pytest.mark.it(
        "Returns MethodRequest from the corresponding method inbox, if available, when called with a method name"
    )
    async def test_called_with_method_name_returns_method_request_from_named_method_inbox(
        self, mocker, client
    ):
        method_name = "some_method"
        request = MethodRequest(request_id="1", name=method_name, payload={"key": "value"})
        inbox_mock = mocker.MagicMock(autospec=AsyncClientInbox)
        inbox_mock.get.return_value = await create_completed_future(request)
        manager_get_inbox_mock = mocker.patch.object(
            target=client._inbox_manager,
            attribute="get_method_request_inbox",
            return_value=inbox_mock,
        )

        received_request = await client.receive_method_request(method_name)
        assert manager_get_inbox_mock.call_count == 1
        assert manager_get_inbox_mock.call_args == mocker.call(method_name)
        assert inbox_mock.get.call_count == 1
        assert received_request is received_request


class SharedClientSendMethodResponseTests(object):
    @pytest.mark.it("Begins a 'send_method_response' pipeline operation")
    async def test_send_method_response_calls_pipeline(self, client, pipeline):
        response = MethodResponse(request_id="1", status=200, payload={"key": "value"})
        await client.send_method_response(response)
        assert pipeline.send_method_response.call_count == 1
        assert pipeline.send_method_response.call_args[0][0] is response

    @pytest.mark.it(
        "Waits for the completion of the 'send_method_response' pipeline operation before returning"
    )
    async def test_waits_for_pipeline_op_completion(self, mocker, client, pipeline):
        cb_mock = mocker.patch.object(async_adapter, "AwaitableCallback").return_value
        cb_mock.completion.return_value = await create_completed_future(None)

        response = MethodResponse(request_id="1", status=200, payload={"key": "value"})
        await client.send_method_response(response)

        # Assert callback is sent to pipeline
        assert pipeline.send_method_response.call_args[1]["callback"] is cb_mock
        # Assert callback completion is waited upon
        assert cb_mock.completion.call_count == 1


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


@pytest.mark.describe("IoTHubDeviceClient (Asynchronous) - Instantiation")
class TestIoTHubDeviceClientInstantiation(
    IoTHubDeviceClientTestsConfig, SharedClientInstantiationTests
):
    @pytest.mark.it("Sets on_c2d_message_received handler in pipeline")
    async def test_sets_on_c2d_message_received_handler_in_pipeline(self, client):
        assert client._pipeline.on_transport_c2d_message_received is not None
        assert (
            client._pipeline.on_transport_c2d_message_received
            == client._inbox_manager.route_c2d_message
        )


@pytest.mark.describe("IoTHubDeviceClient (Asynchronous) - .from_authentication_provider()")
class TestIoTHubDeviceClientFromAuthenticationProvider(
    IoTHubDeviceClientTestsConfig, SharedClientFromAuthenticationProviderTests
):
    pass


@pytest.mark.describe("IoTHubDeviceClient (Asynchronous) - .connect()")
class TestIoTHubDeviceClientConnect(IoTHubDeviceClientTestsConfig, SharedClientConnectTests):
    pass


@pytest.mark.describe("IoTHubDeviceClient (Asynchronous) - .disconnect()")
class TestIoTHubDeviceClientDisconnect(IoTHubDeviceClientTestsConfig, SharedClientDisconnectTests):
    pass


@pytest.mark.describe("IoTHubDeviceClient (Asynchronous) - EVENT: Disconnect")
class TestIoTHubDeviceClientDisconnectEvent(
    IoTHubDeviceClientTestsConfig, SharedClientDisconnectEventTests
):
    pass


@pytest.mark.describe("IoTHubDeviceClient (Asynchronous) - .send_event()")
class TestIoTHubDeviceClientSendEvent(IoTHubDeviceClientTestsConfig, SharedClientSendEventTests):
    pass


@pytest.mark.describe("IoTHubDeviceClient (Asynchronous) - .receive_c2d_message()")
class TestIoTHubDeviceClientReceiveC2DMessage(IoTHubDeviceClientTestsConfig):
    @pytest.mark.it("Implicitly enables C2D messaging feature if not already enabled")
    async def test_enables_c2d_messaging_only_if_not_already_enabled(
        self, mocker, client, pipeline
    ):
        # patch this receive_c2d_message won't block
        mocker.patch.object(
            AsyncClientInbox, "get", return_value=(await create_completed_future(None))
        )

        # Verify C2D Messaging enabled if not enabled
        pipeline.feature_enabled.__getitem__.return_value = False  # C2D will appear disabled
        await client.receive_c2d_message()
        assert pipeline.enable_feature.call_count == 1
        assert pipeline.enable_feature.call_args[0][0] == constant.C2D_MSG

        pipeline.enable_feature.reset_mock()

        # Verify C2D Messaging not enabled if already enabled
        pipeline.feature_enabled.__getitem__.return_value = True  # C2D will appear enabled
        await client.receive_c2d_message()
        assert pipeline.enable_feature.call_count == 0

    @pytest.mark.it("Returns a message from the C2D inbox, if available")
    async def test_returns_message_from_c2d_inbox(self, mocker, client):
        message = Message("this is a message")
        inbox_mock = mocker.MagicMock(autospec=AsyncClientInbox)
        inbox_mock.get.return_value = await create_completed_future(message)
        manager_get_inbox_mock = mocker.patch.object(
            client._inbox_manager, "get_c2d_message_inbox", return_value=inbox_mock
        )

        received_message = await client.receive_c2d_message()
        assert manager_get_inbox_mock.call_count == 1
        assert inbox_mock.get.call_count == 1
        assert received_message is message


@pytest.mark.describe("IoTHubDeviceClient (Asynchronous) - .receive_method_request()")
class TestIoTHubDeviceClientReceiveMethodRequest(
    IoTHubDeviceClientTestsConfig, SharedClientReceiveMethodRequestTests
):
    pass


@pytest.mark.describe("IoTHubDeviceClient (Asynchronous) - .send_method_response()")
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


@pytest.mark.describe("IoTHubModuleClient (Asynchronous) - Instantiation")
class TestIoTHubModuleClientInstantiation(
    IoTHubModuleClientTestsConfig, SharedClientInstantiationTests
):
    @pytest.mark.it("Sets on_input_message_received handler in pipeline")
    async def test_sets_on_input_message_received_handler_in_pipeline(self, client):
        assert client._pipeline.on_transport_input_message_received is not None
        assert (
            client._pipeline.on_transport_input_message_received
            == client._inbox_manager.route_input_message
        )


@pytest.mark.describe("IoTHubModuleClient (Asynchronous) - .from_authentication_provider()")
class TestIoTHubModuleClientFromAuthenticationProvider(
    IoTHubModuleClientTestsConfig, SharedClientFromAuthenticationProviderTests
):
    pass


@pytest.mark.describe("IoTHubModuleClient (Asynchronous) - .connect()")
class TestIoTHubModuleClientConnect(IoTHubModuleClientTestsConfig, SharedClientConnectTests):
    pass


@pytest.mark.describe("IoTHubModuleClient (Asynchronous) - .disconnect()")
class TestIoTHubModuleClientDisconnect(IoTHubModuleClientTestsConfig, SharedClientDisconnectTests):
    pass


@pytest.mark.describe("IoTHubModuleClient (Aynchronous) - EVENT: Disconnect")
class TestIoTHubModuleClientDisconnectEvent(
    IoTHubModuleClientTestsConfig, SharedClientDisconnectEventTests
):
    pass


@pytest.mark.describe("IoTHubModuleClient (Asynchronous) - .send_event()")
class TestIoTHubNModuleClientSendEvent(IoTHubModuleClientTestsConfig, SharedClientSendEventTests):
    pass


@pytest.mark.describe("IoTHubModuleClient (Asynchronous) - .send_to_output()")
class TestIoTHubModuleClientSendToOutput(IoTHubModuleClientTestsConfig):
    @pytest.mark.it("Begins a 'send_output_event' pipeline operation")
    async def test_calls_pipeline_send_to_output(self, client, pipeline):
        message = Message("this is a message")
        output_name = "some_output"
        await client.send_to_output(message, output_name)
        assert pipeline.send_output_event.call_count == 1
        assert pipeline.send_output_event.call_args[0][0] is message
        assert message.output_name == output_name

    @pytest.mark.it(
        "Waits for the completion of the 'send_output_event' pipeline operation before returning"
    )
    async def test_waits_for_pipeline_op_completion(self, mocker, client, pipeline):
        cb_mock = mocker.patch.object(async_adapter, "AwaitableCallback").return_value
        cb_mock.completion.return_value = await create_completed_future(None)

        message = Message("this is a message")
        output_name = "some_output"
        await client.send_to_output(message, output_name)

        # Assert callback is sent to pipeline
        assert pipeline.send_output_event.call_args[1]["callback"] is cb_mock
        # Assert callback completion is waited upon
        assert cb_mock.completion.call_count == 1

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
    async def test_send_to_output_calls_pipeline_wraps_data_in_message(
        self, client, pipeline, message_input
    ):
        output_name = "some_output"
        await client.send_to_output(message_input, output_name)
        assert pipeline.send_output_event.call_count == 1
        sent_message = pipeline.send_output_event.call_args[0][0]
        assert isinstance(sent_message, Message)
        assert sent_message.data == message_input


@pytest.mark.describe("IoTHubModuleClient (Asynchronous) - .receive_input_message()")
class TestIoTHubModuleClientReceiveInputMessage(IoTHubModuleClientTestsConfig):
    @pytest.mark.it("Implicitly enables input messaging feature if not already enabled")
    async def test_enables_input_messaging_only_if_not_already_enabled(
        self, mocker, client, pipeline
    ):
        # patch this receive_input_message won't block
        mocker.patch.object(
            AsyncClientInbox, "get", return_value=(await create_completed_future(None))
        )
        input_name = "some_input"

        # Verify Input Messaging enabled if not enabled
        pipeline.feature_enabled.__getitem__.return_value = (
            False
        )  # Input Messages will appear disabled
        await client.receive_input_message(input_name)
        assert pipeline.enable_feature.call_count == 1
        assert pipeline.enable_feature.call_args[0][0] == constant.INPUT_MSG

        pipeline.enable_feature.reset_mock()

        # Verify Input Messaging not enabled if already enabled
        pipeline.feature_enabled.__getitem__.return_value = (
            True
        )  # Input Messages will appear enabled
        await client.receive_input_message(input_name)
        assert pipeline.enable_feature.call_count == 0

    @pytest.mark.it("Returns a message from the input inbox, if available")
    async def test_returns_message_from_input_inbox(self, mocker, client):
        message = Message("this is a message")
        inbox_mock = mocker.MagicMock(autospec=AsyncClientInbox)
        inbox_mock.get.return_value = await create_completed_future(message)
        manager_get_inbox_mock = mocker.patch.object(
            client._inbox_manager, "get_input_message_inbox", return_value=inbox_mock
        )

        input_name = "some_input"
        received_message = await client.receive_input_message(input_name)
        assert manager_get_inbox_mock.call_count == 1
        assert manager_get_inbox_mock.call_args == mocker.call(input_name)
        assert inbox_mock.get.call_count == 1
        assert received_message is message
