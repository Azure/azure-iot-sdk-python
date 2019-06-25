# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging
import pytest
import asyncio
import threading
import time
import os
from azure.iot.device.iothub.aio import IoTHubDeviceClient, IoTHubModuleClient
from azure.iot.device.iothub.pipeline import IoTHubPipeline, constant
from azure.iot.device.iothub.models import Message, MethodRequest, MethodResponse
from azure.iot.device.iothub.aio.async_inbox import AsyncClientInbox
from azure.iot.device.common import async_adapter
from azure.iot.device.iothub.auth import IoTEdgeError

# auth_provider and pipeline fixtures are implicitly included


pytestmark = pytest.mark.asyncio


async def create_completed_future(result=None):
    f = asyncio.Future()
    f.set_result(result)
    return f


class SharedClientInstantiationTests(object):
    @pytest.mark.it("Sets on_connected handler in pipeline")
    async def test_sets_on_connected_handler_in_pipeline(self, client):
        assert client._pipeline.on_connected is not None
        assert client._pipeline.on_connected == client._on_state_change

    @pytest.mark.it("Sets on_disconnected handler in pipeline")
    async def test_sets_on_disconnected_handler_in_pipeline(self, client):
        assert client._pipeline.on_disconnected is not None
        assert client._pipeline.on_disconnected == client._on_state_change

    @pytest.mark.it("Sets on_method_request_eeceived handler in pipeline")
    async def test_sets_on_method_request_received_handler_in_pipleline(self, client):
        assert client._pipeline.on_method_request_received is not None
        assert (
            client._pipeline.on_method_request_received
            == client._inbox_manager.route_method_request
        )


class SharedClientCreateFromConnectionStringTests(object):
    @pytest.mark.it("Instantiates the client, given a valid connection string")
    async def test_instantiates_client(self, client_class, connection_string):
        client = client_class.create_from_connection_string(connection_string)
        assert isinstance(client, client_class)

    # TODO: If auth package was refactored to use ConnectionString class, tests from that
    # class would increase the coverage
    @pytest.mark.it("Raises ValueError when given an invalid connection string")
    @pytest.mark.parametrize(
        "bad_cs",
        [
            pytest.param("not-a-connection-string", id="Garbage string"),
            pytest.param("", id="Empty string"),
            pytest.param(object(), id="Non-string input"),
            pytest.param(
                "HostName=Invalid;DeviceId=Invalid;SharedAccessKey=Invalid",
                id="Malformed Connection String",
                marks=pytest.mark.xfail(reason="Bug in pipeline + need for auth refactor"),  # TODO
                # Note that this sometimes prints warning text (only for async) - I think it's a bug in pytest-asyncio
            ),
        ],
    )
    async def test_raises_value_error_on_bad_connection_string(self, client_class, bad_cs):
        with pytest.raises(ValueError):
            client_class.create_from_connection_string(bad_cs)

    @pytest.mark.it(
        "Uses a SymmetricKeyAuthenticationProvider to create the client's IoTHub pipeline"
    )
    async def test_auth_provider_and_pipeline(self, mocker, client_class):
        mock_auth_parse = mocker.patch(
            "azure.iot.device.iothub.auth.SymmetricKeyAuthenticationProvider"
        ).parse
        mock_pipeline_init = mocker.patch("azure.iot.device.iothub.abstract_clients.IoTHubPipeline")

        client = client_class.create_from_connection_string(mocker.MagicMock())

        assert mock_auth_parse.call_count == 1
        assert mock_pipeline_init.call_count == 1
        assert mock_pipeline_init.call_args == mocker.call(mock_auth_parse.return_value)
        assert client._pipeline == mock_pipeline_init.return_value


class SharedClientFromCreateFromSharedAccessSignature(object):
    @pytest.mark.it("Instantiates the client, given a valid SAS token")
    async def test_instantiates_client(self, client_class, sas_token_string):
        client = client_class.create_from_shared_access_signature(sas_token_string)
        assert isinstance(client, client_class)

    # TODO: If auth package was refactored to use SasToken class, tests from that
    # class would increase the coverage here.
    @pytest.mark.it("Raises ValueError when given an invalid SAS token")
    @pytest.mark.parametrize(
        "bad_sas",
        [
            pytest.param(object(), id="Non-string input"),
            pytest.param(
                "SharedAccessSignature sr=Invalid&sig=Invalid&se=Invalid", id="Malformed SAS token"
            ),
        ],
    )
    async def test_raises_value_error_on_bad_sas_token(self, client_class, bad_sas):
        with pytest.raises(ValueError):
            client_class.create_from_shared_access_signature(bad_sas)

    @pytest.mark.it(
        "Uses a SharedAccessSignatureAuthenticationProvider to create the client's IoTHub pipeline"
    )
    async def test_auth_provider_and_pipeline(self, mocker, client_class):
        mock_auth_parse = mocker.patch(
            "azure.iot.device.iothub.auth.SharedAccessSignatureAuthenticationProvider"
        ).parse
        mock_pipeline_init = mocker.patch("azure.iot.device.iothub.abstract_clients.IoTHubPipeline")

        client = client_class.create_from_shared_access_signature(mocker.MagicMock())

        assert mock_auth_parse.call_count == 1
        assert mock_pipeline_init.call_count == 1
        assert mock_pipeline_init.call_args == mocker.call(mock_auth_parse.return_value)
        assert client._pipeline == mock_pipeline_init.return_value


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
    @pytest.mark.it("Begins a 'send_d2c_message' pipeline operation")
    async def test_calls_pipeline_send_d2c_message(self, client, pipeline):
        message = Message("this is a message")
        await client.send_d2c_message(message)
        assert pipeline.send_d2c_message.call_count == 1
        assert pipeline.send_d2c_message.call_args[0][0] is message

    @pytest.mark.it(
        "Waits for the completion of the 'send_d2c_message' pipeline operation before returning"
    )
    async def test_waits_for_pipeline_op_completion(self, mocker, client, pipeline):
        cb_mock = mocker.patch.object(async_adapter, "AwaitableCallback").return_value
        cb_mock.completion.return_value = await create_completed_future(None)

        message = Message("this is a message")
        await client.send_d2c_message(message)

        # Assert callback is sent to pipeline
        assert pipeline.send_d2c_message.call_args[1]["callback"] is cb_mock
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
    async def test_wraps_data_in_message_and_calls_pipeline_send_d2c_message(
        self, client, pipeline, message_input
    ):
        await client.send_d2c_message(message_input)
        assert pipeline.send_d2c_message.call_count == 1
        sent_message = pipeline.send_d2c_message.call_args[0][0]
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


class SharedClientGetTwinTests(object):
    @pytest.mark.it("Implicitly enables twin messaging feature if not already enabled")
    async def test_enables_twin_only_if_not_already_enabled(self, mocker, client, pipeline):
        # patch this so get_twin won't block
        def immediate_callback(callback):
            callback(None)

        mocker.patch.object(pipeline, "get_twin", side_effect=immediate_callback)

        # Verify twin enabled if not enabled
        pipeline.feature_enabled.__getitem__.return_value = False  # twin will appear disabled
        await client.get_twin()
        assert pipeline.enable_feature.call_count == 1
        assert pipeline.enable_feature.call_args[0][0] == constant.TWIN

        pipeline.enable_feature.reset_mock()

        # Verify twin not enabled if already enabled
        pipeline.feature_enabled.__getitem__.return_value = True  # twin will appear enabled
        await client.get_twin()
        assert pipeline.enable_feature.call_count == 0

    @pytest.mark.it("Begins a 'get_twin' pipeline operation")
    async def test_get_twin_calls_pipeline(self, client, pipeline):
        await client.get_twin()
        assert pipeline.get_twin.call_count == 1

    @pytest.mark.it(
        "Waits for the completion of the 'get_twin' pipeline operation before returning"
    )
    async def test_waits_for_pipeline_op_completion(self, mocker, client, pipeline):
        cb_mock = mocker.patch.object(async_adapter, "AwaitableCallback").return_value
        cb_mock.completion.return_value = await create_completed_future(None)
        pipeline.feature_enabled.__getitem__.return_value = True  # twin will appear enabled

        await client.get_twin()

        # Assert callback is sent to pipeline
        pipeline.get_twin.call_args[1]["callback"] is cb_mock
        # Assert callback completion is waited upon
        assert cb_mock.completion.call_count == 1

    @pytest.mark.it("Returns the twin that the pipeline returned")
    async def test_verifies_twin_returned(self, mocker, client, pipeline):
        twin = {"reported": {"foo": "bar"}}

        # make the pipeline the twin
        def immediate_callback(callback):
            callback(twin)

        mocker.patch.object(pipeline, "get_twin", side_effect=immediate_callback)

        returned_twin = await client.get_twin()
        assert returned_twin == twin


class SharedClientPatchTwinReportedPropertiesTests(object):
    @pytest.fixture
    def patch(self):
        return {"properties": {"reported": {"foo": 1}}}

    @pytest.mark.it("Implicitly enables twin messaging feature if not already enabled")
    async def test_enables_twin_only_if_not_already_enabled(self, mocker, client, pipeline):
        # patch this so x_get_twin won't block
        def immediate_callback(patch, callback):
            callback(None)

        mocker.patch.object(
            pipeline, "patch_twin_reported_properties", side_effect=immediate_callback
        )

        # Verify twin enabled if not enabled
        pipeline.feature_enabled.__getitem__.return_value = False  # twin will appear disabled
        await client.get_twin()
        assert pipeline.enable_feature.call_count == 1
        assert pipeline.enable_feature.call_args[0][0] == constant.TWIN

        pipeline.enable_feature.reset_mock()

        # Verify twin not enabled if already enabled
        pipeline.feature_enabled.__getitem__.return_value = True  # twin will appear enabled
        await client.get_twin()
        assert pipeline.enable_feature.call_count == 0

    @pytest.mark.it("Begins a 'patch_twin_reported_properties' pipeline operation")
    async def test_patch_twin_reported_properties_calls_pipeline(self, client, pipeline, patch):
        await client.patch_twin_reported_properties(patch)
        assert pipeline.patch_twin_reported_properties.call_count == 1
        assert pipeline.patch_twin_reported_properties.call_args[1]["patch"] is patch

    @pytest.mark.it(
        "Waits for the completion of the 'patch_twin_reported_properties' pipeline operation before returning"
    )
    async def test_waits_for_pipeline_op_completion(self, mocker, client, pipeline, patch):
        cb_mock = mocker.patch.object(async_adapter, "AwaitableCallback").return_value
        cb_mock.completion.return_value = await create_completed_future(None)
        pipeline.feature_enabled.__getitem__.return_value = True  # twin will appear enabled

        await client.patch_twin_reported_properties(patch)

        # Assert callback is sent to pipeline
        assert pipeline.patch_twin_reported_properties.call_args[1]["callback"] is cb_mock
        # Assert callback completion is waited upon
        assert cb_mock.completion.call_count == 1


class SharedClientReceiveTwinDesiredPropertiesPatchTests(object):
    @pytest.fixture
    def patch(self):
        return {"properties": {"desired": {"foo": 1}}}

    @pytest.mark.it("Implicitly enables twin patch messaging feature if not already enabled")
    async def test_enables_c2d_messaging_only_if_not_already_enabled(
        self, mocker, client, pipeline
    ):
        # patch this receive_twin_desired_properites_patch won't block
        mocker.patch.object(
            AsyncClientInbox, "get", return_value=(await create_completed_future(None))
        )

        # Verify twin patches are enabled if not enabled
        pipeline.feature_enabled.__getitem__.return_value = (
            False
        )  # twin patches will appear disabled
        await client.receive_twin_desired_properties_patch()
        assert pipeline.enable_feature.call_count == 1
        assert pipeline.enable_feature.call_args[0][0] == constant.TWIN_PATCHES

        pipeline.enable_feature.reset_mock()

        # Verify twin patches are not enabled if already enabled
        pipeline.feature_enabled.__getitem__.return_value = True  # twin patches will appear enabled
        await client.receive_twin_desired_properties_patch()
        assert pipeline.enable_feature.call_count == 0

    @pytest.mark.it("Returns a message from the twin patch inbox, if available")
    async def test_returns_message_from_twin_patch_inbox(self, mocker, client, patch):
        inbox_mock = mocker.MagicMock(autospec=AsyncClientInbox)
        inbox_mock.get.return_value = await create_completed_future(patch)
        manager_get_inbox_mock = mocker.patch.object(
            client._inbox_manager, "get_twin_patch_inbox", return_value=inbox_mock
        )

        received_patch = await client.receive_twin_desired_properties_patch()
        assert manager_get_inbox_mock.call_count == 1
        assert inbox_mock.get.call_count == 1
        assert received_patch is patch


################
# DEVICE TESTS #
################
class IoTHubDeviceClientTestsConfig(object):
    @pytest.fixture
    def client_class(self):
        return IoTHubDeviceClient

    @pytest.fixture
    def client(self, pipeline):
        """This client automatically resolves callbacks sent to the pipeline.
        It should be used for the majority of tests.
        """
        return IoTHubDeviceClient(pipeline)

    @pytest.fixture
    def connection_string(self, device_connection_string):
        """This fixture is parametrized to provie all valid device connection strings.
        See client_fixtures.py
        """
        return device_connection_string

    @pytest.fixture
    def sas_token_string(self, device_sas_token_string):
        return device_sas_token_string


@pytest.mark.describe("IoTHubDeviceClient (Asynchronous) - Instantiation")
class TestIoTHubDeviceClientInstantiation(
    IoTHubDeviceClientTestsConfig, SharedClientInstantiationTests
):
    @pytest.mark.it("Sets on_c2d_message_received handler in pipeline")
    async def test_sets_on_c2d_message_received_handler_in_pipeline(self, client):
        assert client._pipeline.on_c2d_message_received is not None
        assert client._pipeline.on_c2d_message_received == client._inbox_manager.route_c2d_message


@pytest.mark.describe("IoTHubDeviceClient (Asynchronous) - .create_from_connection_string()")
class TestIoTHubDeviceClientCreateFromConnectionString(
    IoTHubDeviceClientTestsConfig, SharedClientCreateFromConnectionStringTests
):
    pass


@pytest.mark.describe("IoTHubDeviceClient (Asynchronous) - .create_from_shared_access_signature()")
class TestIoTHubDeviceClientCreateFromSharedAccessSignature(
    IoTHubDeviceClientTestsConfig, SharedClientFromCreateFromSharedAccessSignature
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


@pytest.mark.describe("IoTHubDeviceClient (Asynchronous) - .send_d2c_message()")
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


@pytest.mark.describe("IoTHubDeviceClient (Asynchronous) - .get_twin()")
class TestIoTHubDeviceClientGetTwin(IoTHubDeviceClientTestsConfig, SharedClientGetTwinTests):
    pass


@pytest.mark.describe("IoTHubDeviceClient (Asynchronous) - .patch_twin_reported_properties()")
class TestIoTHubDeviceClientPatchTwinReportedProperties(
    IoTHubDeviceClientTestsConfig, SharedClientPatchTwinReportedPropertiesTests
):
    pass


@pytest.mark.describe(
    "IoTHubDeviceClient (Asynchronous) - .receive_twin_desired_properties_patch()"
)
class TestIoTHubDeviceClientReceiveTwinDesiredPropertiesPatch(
    IoTHubDeviceClientTestsConfig, SharedClientReceiveTwinDesiredPropertiesPatchTests
):
    pass


################
# MODULE TESTS #
################
class IoTHubModuleClientTestsConfig(object):
    @pytest.fixture
    def client_class(self):
        return IoTHubModuleClient

    @pytest.fixture
    def client(self, pipeline):
        """This client automatically resolves callbacks sent to the pipeline.
        It should be used for the majority of tests.
        """
        return IoTHubModuleClient(pipeline)

    @pytest.fixture
    def connection_string(self, module_connection_string):
        """This fixture is parametrized to provie all valid device connection strings.
        See client_fixtures.py
        """
        return module_connection_string

    @pytest.fixture
    def sas_token_string(self, module_sas_token_string):
        return module_sas_token_string


@pytest.mark.describe("IoTHubModuleClient (Asynchronous) - Instantiation")
class TestIoTHubModuleClientInstantiation(
    IoTHubModuleClientTestsConfig, SharedClientInstantiationTests
):
    @pytest.mark.it("Sets on_input_message_received handler in pipeline")
    async def test_sets_on_input_message_received_handler_in_pipeline(self, client):
        assert client._pipeline.on_input_message_received is not None
        assert (
            client._pipeline.on_input_message_received == client._inbox_manager.route_input_message
        )


@pytest.mark.describe("IoTHubModuleClient (Asynchronous) - .create_from_connection_string()")
class TestIoTHubModuleClientCreateFromConnectionString(
    IoTHubModuleClientTestsConfig, SharedClientCreateFromConnectionStringTests
):
    pass


@pytest.mark.describe("IoTHubModuleClient (Asynchronous) - .create_from_shared_access_signature()")
class TestIoTHubModuleClientCreateFromSharedAccessSignature(
    IoTHubModuleClientTestsConfig, SharedClientFromCreateFromSharedAccessSignature
):
    pass


@pytest.mark.describe("IoTHubModuleClient (Asynchronous) - .create_from_edge_environment()")
class TestIoTHubModuleClientCreateFromEdgeEnvironment(IoTHubModuleClientTestsConfig):
    @pytest.mark.it("Instantiates the client, given a valid Edge container environment")
    async def test_instantiates_client(self, mocker, client_class, edge_container_env_vars):
        mocker.patch.dict(os.environ, edge_container_env_vars)
        # must patch auth provider because it immediately tries to access Edge HSM
        mocker.patch("azure.iot.device.iothub.auth.IoTEdgeAuthenticationProvider")
        client = client_class.create_from_edge_environment()
        assert isinstance(client, client_class)

    @pytest.mark.it("Uses an IoTEdgeAuthenticationProvider to create the client's IoTHub pipeline")
    async def test_auth_provider_and_pipeline(self, mocker, client_class, edge_container_env_vars):
        mocker.patch.dict(os.environ, edge_container_env_vars)
        mock_auth_init = mocker.patch("azure.iot.device.iothub.auth.IoTEdgeAuthenticationProvider")
        mock_pipeline_init = mocker.patch("azure.iot.device.iothub.abstract_clients.IoTHubPipeline")

        client = client_class.create_from_edge_environment()

        assert mock_auth_init.call_count == 1
        assert mock_pipeline_init.call_count == 1
        assert mock_pipeline_init.call_args == mocker.call(mock_auth_init.return_value)
        assert client._pipeline == mock_pipeline_init.return_value

    @pytest.mark.it(
        "Raises IoTEdgeError if the Edge container is missing required environment variables"
    )
    @pytest.mark.parametrize(
        "missing_env_var",
        [
            "IOTEDGE_MODULEID",
            "IOTEDGE_DEVICEID",
            "IOTEDGE_IOTHUBHOSTNAME",
            "IOTEDGE_GATEWAYHOSTNAME",
            "IOTEDGE_APIVERSION",
            "IOTEDGE_MODULEGENERATIONID",
            "IOTEDGE_WORKLOADURI",
        ],
    )
    async def test_bad_environment(
        self, mocker, client_class, edge_container_env_vars, missing_env_var
    ):
        # Remove a variable from the fixture
        del edge_container_env_vars[missing_env_var]
        mocker.patch.dict(os.environ, edge_container_env_vars)

        with pytest.raises(IoTEdgeError):
            client_class.create_from_edge_environment()

    @pytest.mark.it("Raises IoTEdgeError if there is an error using the Edge for authentication")
    async def test_bad_edge_auth(self, mocker, client_class, edge_container_env_vars):
        mocker.patch.dict(os.environ, edge_container_env_vars)
        mock_auth = mocker.patch("azure.iot.device.iothub.auth.IoTEdgeAuthenticationProvider")
        mock_auth.side_effect = IoTEdgeError

        with pytest.raises(IoTEdgeError):
            client_class.create_from_edge_environment()


@pytest.mark.describe("IoTHubModuleClient (Asynchronous) - .connect()")
class TestIoTHubModuleClientConnect(IoTHubModuleClientTestsConfig, SharedClientConnectTests):
    pass


@pytest.mark.describe("IoTHubModuleClient (Asynchronous) - .disconnect()")
class TestIoTHubModuleClientDisconnect(IoTHubModuleClientTestsConfig, SharedClientDisconnectTests):
    pass


@pytest.mark.describe("IoTHubModuleClient (Asynchronous) - EVENT: Disconnect")
class TestIoTHubModuleClientDisconnectEvent(
    IoTHubModuleClientTestsConfig, SharedClientDisconnectEventTests
):
    pass


@pytest.mark.describe("IoTHubModuleClient (Asynchronous) - .send_d2c_message()")
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


@pytest.mark.describe("IoTHubModuleClient (Asynchronous) - .receive_method_request()")
class TestIoTHubModuleClientReceiveMethodRequest(
    IoTHubModuleClientTestsConfig, SharedClientReceiveMethodRequestTests
):
    pass


@pytest.mark.describe("IoTHubModuleClient (Asynchronous) - .send_method_response()")
class TestIoTHubModuleClientSendMethodResponse(
    IoTHubModuleClientTestsConfig, SharedClientSendMethodResponseTests
):
    pass


@pytest.mark.describe("IoTHubModuleClient (Asynchronous) - .get_twin()")
class TestIoTHubModuleClientGetTwin(IoTHubModuleClientTestsConfig, SharedClientGetTwinTests):
    pass


@pytest.mark.describe("IoTHubModuleClient (Asynchronous) - .patch_twin_reported_properties()")
class TestIoTHubModuleClientPatchTwinReportedProperties(
    IoTHubModuleClientTestsConfig, SharedClientPatchTwinReportedPropertiesTests
):
    pass


@pytest.mark.describe(
    "IoTHubModuleClient (Asynchronous) - .receive_twin_desired_properties_patch()"
)
class TestIoTHubModuleClientReceiveTwinDesiredPropertiesPatch(
    IoTHubModuleClientTestsConfig, SharedClientReceiveTwinDesiredPropertiesPatchTests
):
    pass
