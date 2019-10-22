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
import io
from azure.iot.device import exceptions as client_exceptions
from azure.iot.device.iothub.aio import IoTHubDeviceClient, IoTHubModuleClient
from azure.iot.device.iothub.pipeline import IoTHubPipeline, constant
from azure.iot.device.iothub.pipeline import exceptions as pipeline_exceptions
from azure.iot.device.iothub.models import Message, MethodRequest
from azure.iot.device.iothub.aio.async_inbox import AsyncClientInbox
from azure.iot.device.common import async_adapter
from azure.iot.device.iothub.auth import IoTEdgeError
from azure.iot.device.common.models.x509 import X509

pytestmark = pytest.mark.asyncio
logging.basicConfig(level=logging.DEBUG)


async def create_completed_future(result=None):
    f = asyncio.Future()
    f.set_result(result)
    return f


# automatically mock the pipeline for all tests in this file.
@pytest.fixture(autouse=True)
def mock_pipeline_init(mocker):
    return mocker.patch("azure.iot.device.iothub.pipeline.IoTHubPipeline")


class SharedClientInstantiationTests(object):
    @pytest.mark.it(
        "Stores the IoTHubPipeline from the 'iothub_pipeline' parameter in the '_iothub_pipeline' attribute"
    )
    async def test_iothub_pipeline_attribute(self, client_class, iothub_pipeline):
        client = client_class(iothub_pipeline)

        assert client._iothub_pipeline is iothub_pipeline

    @pytest.mark.it("Sets on_connected handler in the IoTHubPipeline")
    async def test_sets_on_connected_handler_in_pipeline(self, client_class, iothub_pipeline):
        client = client_class(iothub_pipeline)

        assert client._iothub_pipeline.on_connected is not None
        assert client._iothub_pipeline.on_connected == client._on_connected

    @pytest.mark.it("Sets on_disconnected handler in the IoTHubPipeline")
    async def test_sets_on_disconnected_handler_in_pipeline(self, client_class, iothub_pipeline):
        client = client_class(iothub_pipeline)

        assert client._iothub_pipeline.on_disconnected is not None
        assert client._iothub_pipeline.on_disconnected == client._on_disconnected

    @pytest.mark.it("Sets on_method_request_received handler in the IoTHubPipeline")
    async def test_sets_on_method_request_received_handler_in_pipleline(
        self, client_class, iothub_pipeline
    ):
        client = client_class(iothub_pipeline)

        assert client._iothub_pipeline.on_method_request_received is not None
        assert (
            client._iothub_pipeline.on_method_request_received
            == client._inbox_manager.route_method_request
        )


class SharedClientCreateFromConnectionStringTests(object):
    @pytest.mark.it(
        "Uses the connection string and CA certificate combination to create a SymmetricKeyAuthenticationProvider"
    )
    @pytest.mark.parametrize(
        "ca_cert",
        [
            pytest.param(None, id="No CA certificate"),
            pytest.param("some-certificate", id="With CA certificate"),
        ],
    )
    @pytest.mark.parametrize(
        "websockets",
        [
            pytest.param(None, id=" Default (No Websockets) "),
            pytest.param(False, id=" No Websockets "),
            pytest.param(True, id=" With Websockets "),
        ],
    )
    async def test_auth_provider_creation(
        self, mocker, client_class, connection_string, ca_cert, websockets
    ):
        mock_auth_parse = mocker.patch(
            "azure.iot.device.iothub.auth.SymmetricKeyAuthenticationProvider"
        ).parse
        mock_config_init = mocker.patch(
            "azure.iot.device.iothub.abstract_clients.config.IoTHubPipelineConfig"
        )

        args = (connection_string,)
        kwargs = {}
        if ca_cert:
            kwargs["ca_cert"] = ca_cert
        if websockets:
            kwargs["websockets"] = websockets
        client_class.create_from_connection_string(*args, **kwargs)

        assert mock_config_init.call_count == 1
        if websockets:
            assert mock_config_init.call_args == mocker.call(websockets=websockets)
        else:
            assert mock_config_init.call_args == ()

        assert mock_auth_parse.call_count == 1
        assert mock_auth_parse.call_args == mocker.call(connection_string)
        assert mock_auth_parse.return_value.ca_cert is ca_cert

    @pytest.mark.it("Uses the SymmetricKeyAuthenticationProvider to create an IoTHubPipeline")
    @pytest.mark.parametrize(
        "ca_cert",
        [
            pytest.param(None, id="No CA certificate"),
            pytest.param("some-certificate", id="With CA certificate"),
        ],
    )
    @pytest.mark.parametrize(
        "websockets",
        [
            pytest.param(None, id=" Default (No Websockets) "),
            pytest.param(False, id=" No Websockets "),
            pytest.param(True, id=" With Websockets "),
        ],
    )
    async def test_pipeline_creation(
        self, mocker, client_class, connection_string, ca_cert, websockets, mock_pipeline_init
    ):
        mock_auth = mocker.patch(
            "azure.iot.device.iothub.auth.SymmetricKeyAuthenticationProvider"
        ).parse.return_value

        mock_config_init = mocker.patch(
            "azure.iot.device.iothub.abstract_clients.config.IoTHubPipelineConfig"
        )

        args = (connection_string,)
        kwargs = {}
        if ca_cert:
            kwargs["ca_cert"] = ca_cert
        if websockets:
            kwargs["websockets"] = websockets
        client_class.create_from_connection_string(*args, **kwargs)

        assert mock_config_init.call_count == 1
        if websockets:
            assert mock_config_init.call_args == ({"websockets": websockets},)
        else:
            assert mock_config_init.call_args == ()

        assert mock_pipeline_init.call_count == 1
        assert mock_pipeline_init.call_args == mocker.call(mock_auth, mock_config_init.return_value)

    @pytest.mark.it("Uses the IoTHubPipeline to instantiate the client")
    @pytest.mark.parametrize(
        "ca_cert",
        [
            pytest.param(None, id="No CA certificate"),
            pytest.param("some-certificate", id="With CA certificate"),
        ],
    )
    async def test_client_instantiation(self, mocker, client_class, connection_string, ca_cert):
        mock_pipeline = mocker.patch("azure.iot.device.iothub.pipeline.IoTHubPipeline").return_value
        spy_init = mocker.spy(client_class, "__init__")
        args = (connection_string,)
        kwargs = {}
        if ca_cert:
            kwargs["ca_cert"] = ca_cert
        client_class.create_from_connection_string(*args, **kwargs)

        assert spy_init.call_count == 1
        assert spy_init.call_args == mocker.call(mocker.ANY, mock_pipeline)

    @pytest.mark.it("Returns the instantiated client")
    @pytest.mark.parametrize(
        "ca_cert",
        [
            pytest.param(None, id="No CA certificate"),
            pytest.param("some-certificate", id="With CA certificate"),
        ],
    )
    async def test_returns_client(self, client_class, connection_string, ca_cert):
        args = (connection_string,)
        kwargs = {}
        if ca_cert:
            kwargs["ca_cert"] = ca_cert
        client = client_class.create_from_connection_string(*args, **kwargs)

        assert isinstance(client, client_class)

    # TODO: If auth package was refactored to use ConnectionString class, tests from that
    # class would increase the coverage here.
    @pytest.mark.it("Raises ValueError when given an invalid connection string")
    @pytest.mark.parametrize(
        "bad_cs",
        [
            pytest.param("not-a-connection-string", id="Garbage string"),
            pytest.param(object(), id="Non-string input"),
            pytest.param(
                "HostName=Invalid;DeviceId=Invalid;SharedAccessKey=Invalid",
                id="Malformed Connection String",
                marks=pytest.mark.xfail(reason="Bug in pipeline + need for auth refactor"),  # TODO
            ),
        ],
    )
    async def test_raises_value_error_on_bad_connection_string(self, client_class, bad_cs):
        with pytest.raises(ValueError):
            client_class.create_from_connection_string(bad_cs)


class SharedClientCreateFromSharedAccessSignature(object):
    @pytest.mark.it("Uses the SAS token to create a SharedAccessSignatureAuthenticationProvider")
    async def test_auth_provider_creation(self, mocker, client_class, sas_token_string):
        mock_auth_parse = mocker.patch(
            "azure.iot.device.iothub.auth.SharedAccessSignatureAuthenticationProvider"
        ).parse

        client_class.create_from_shared_access_signature(sas_token_string)

        assert mock_auth_parse.call_count == 1
        assert mock_auth_parse.call_args == mocker.call(sas_token_string)

    @pytest.mark.it(
        "Uses the SharedAccessSignatureAuthenticationProvider to create an IoTHubPipeline"
    )
    async def test_pipeline_creation(
        self, mocker, client_class, sas_token_string, mock_pipeline_init
    ):
        mock_auth = mocker.patch(
            "azure.iot.device.iothub.auth.SharedAccessSignatureAuthenticationProvider"
        ).parse.return_value

        mock_config_init = mocker.patch(
            "azure.iot.device.iothub.abstract_clients.config.IoTHubPipelineConfig"
        )

        client_class.create_from_shared_access_signature(sas_token_string)

        assert mock_pipeline_init.call_count == 1
        assert mock_pipeline_init.call_args == mocker.call(mock_auth, mock_config_init.return_value)

    @pytest.mark.it("Uses the IoTHubPipeline to instantiate the client")
    async def test_client_instantiation(self, mocker, client_class, sas_token_string):
        mock_pipeline = mocker.patch("azure.iot.device.iothub.pipeline.IoTHubPipeline").return_value
        spy_init = mocker.spy(client_class, "__init__")

        client_class.create_from_shared_access_signature(sas_token_string)

        assert spy_init.call_count == 1
        assert spy_init.call_args == mocker.call(mocker.ANY, mock_pipeline)

    @pytest.mark.it("Returns the instantiated client")
    async def test_returns_client(self, mocker, client_class, sas_token_string):
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


class SharedClientConnectTests(object):
    @pytest.mark.it("Begins a 'connect' pipeline operation")
    async def test_calls_pipeline_connect(self, client, iothub_pipeline):
        await client.connect()
        assert iothub_pipeline.connect.call_count == 1

    @pytest.mark.it("Waits for the completion of the 'connect' pipeline operation before returning")
    async def test_waits_for_pipeline_op_completion(self, mocker, client, iothub_pipeline):
        cb_mock = mocker.patch.object(async_adapter, "AwaitableCallback").return_value
        cb_mock.completion.return_value = await create_completed_future(None)

        await client.connect()

        # Assert callback is sent to pipeline
        assert iothub_pipeline.connect.call_args[1]["callback"] is cb_mock
        # Assert callback completion is waited upon
        assert cb_mock.completion.call_count == 1

    @pytest.mark.it(
        "Raises a client error if the `connect` pipeline operation calls back with a pipeline error"
    )
    @pytest.mark.parametrize(
        "pipeline_error,client_error",
        [
            pytest.param(
                pipeline_exceptions.ConnectionDroppedError,
                client_exceptions.ConnectionDroppedError,
                id="ConnectionDroppedError->ConnectionDroppedError",
            ),
            pytest.param(
                pipeline_exceptions.ConnectionFailedError,
                client_exceptions.ConnectionFailedError,
                id="ConnectionFailedError->ConnectionFailedError",
            ),
            pytest.param(
                pipeline_exceptions.UnauthorizedError,
                client_exceptions.CredentialError,
                id="UnauthorizedError->CredentialError",
            ),
            pytest.param(
                pipeline_exceptions.ProtocolClientError,
                client_exceptions.ClientError,
                id="ProtocolClientError->ClientError",
            ),
            pytest.param(Exception, client_exceptions.ClientError, id="Exception->ClientError"),
        ],
    )
    async def test_raises_error_on_pipeline_op_error(
        self, mocker, client, iothub_pipeline, pipeline_error, client_error
    ):
        my_pipeline_error = pipeline_error()

        def fail_connect(callback):
            callback(error=my_pipeline_error)

        iothub_pipeline.connect = mocker.MagicMock(side_effect=fail_connect)
        with pytest.raises(client_error) as e_info:
            await client.connect()
        assert e_info.value.__cause__ is my_pipeline_error
        assert iothub_pipeline.connect.call_count == 1


class SharedClientDisconnectTests(object):
    @pytest.mark.it("Begins a 'disconnect' pipeline operation")
    async def test_calls_pipeline_disconnect(self, client, iothub_pipeline):
        await client.disconnect()
        assert iothub_pipeline.disconnect.call_count == 1

    @pytest.mark.it(
        "Waits for the completion of the 'disconnect' pipeline operation before returning"
    )
    async def test_waits_for_pipeline_op_completion(self, mocker, client, iothub_pipeline):
        cb_mock = mocker.patch.object(async_adapter, "AwaitableCallback").return_value
        cb_mock.completion.return_value = await create_completed_future(None)

        await client.disconnect()

        # Assert callback is sent to pipeline
        assert iothub_pipeline.disconnect.call_args[1]["callback"] is cb_mock
        # Assert callback completion is waited upon
        assert cb_mock.completion.call_count == 1

    @pytest.mark.it(
        "Raises a client error if the `disconnect` pipeline operation calls back with a pipeline error"
    )
    @pytest.mark.parametrize(
        "pipeline_error,client_error",
        [
            pytest.param(
                pipeline_exceptions.ProtocolClientError,
                client_exceptions.ClientError,
                id="ProtocolClientError->ClientError",
            ),
            pytest.param(Exception, client_exceptions.ClientError, id="Exception->ClientError"),
        ],
    )
    async def test_raises_error_on_pipeline_op_error(
        self, mocker, client, iothub_pipeline, pipeline_error, client_error
    ):
        my_pipeline_error = pipeline_error()

        def fail_disconnect(callback):
            callback(error=my_pipeline_error)

        iothub_pipeline.disconnect = mocker.MagicMock(side_effect=fail_disconnect)
        with pytest.raises(client_error) as e_info:
            await client.disconnect()
        assert e_info.value.__cause__ is my_pipeline_error
        assert iothub_pipeline.disconnect.call_count == 1


class SharedClientDisconnectEventTests(object):
    @pytest.mark.it("Clears all pending MethodRequests upon disconnect")
    async def test_state_change_handler_clears_method_request_inboxes_on_disconnect(
        self, client, mocker
    ):
        clear_method_request_spy = mocker.spy(client._inbox_manager, "clear_all_method_requests")
        client._on_disconnected()
        assert clear_method_request_spy.call_count == 1


class SharedClientSendD2CMessageTests(object):
    @pytest.mark.it("Begins a 'send_message' pipeline operation")
    async def test_calls_pipeline_send_message(self, client, iothub_pipeline, message):
        await client.send_message(message)
        assert iothub_pipeline.send_message.call_count == 1
        assert iothub_pipeline.send_message.call_args[0][0] is message

    @pytest.mark.it(
        "Waits for the completion of the 'send_message' pipeline operation before returning"
    )
    async def test_waits_for_pipeline_op_completion(self, mocker, client, iothub_pipeline, message):
        cb_mock = mocker.patch.object(async_adapter, "AwaitableCallback").return_value
        cb_mock.completion.return_value = await create_completed_future(None)

        await client.send_message(message)

        # Assert callback is sent to pipeline
        assert iothub_pipeline.send_message.call_args[1]["callback"] is cb_mock
        # Assert callback completion is waited upon
        assert cb_mock.completion.call_count == 1

    @pytest.mark.it(
        "Raises a client error if the `send_message` pipeline operation calls back with a pipeline error"
    )
    @pytest.mark.parametrize(
        "pipeline_error,client_error",
        [
            pytest.param(
                pipeline_exceptions.ConnectionDroppedError,
                client_exceptions.ConnectionDroppedError,
                id="ConnectionDroppedError->ConnectionDroppedError",
            ),
            pytest.param(
                pipeline_exceptions.ConnectionFailedError,
                client_exceptions.ConnectionFailedError,
                id="ConnectionFailedError->ConnectionFailedError",
            ),
            pytest.param(
                pipeline_exceptions.UnauthorizedError,
                client_exceptions.CredentialError,
                id="UnauthorizedError->CredentialError",
            ),
            pytest.param(
                pipeline_exceptions.ProtocolClientError,
                client_exceptions.ClientError,
                id="ProtocolClientError->ClientError",
            ),
            pytest.param(Exception, client_exceptions.ClientError, id="Exception->ClientError"),
        ],
    )
    async def test_raises_error_on_pipeline_op_error(
        self, mocker, client, iothub_pipeline, message, client_error, pipeline_error
    ):
        my_pipeline_error = pipeline_error()

        def fail_send_message(message, callback):
            callback(error=my_pipeline_error)

        iothub_pipeline.send_message = mocker.MagicMock(side_effect=fail_send_message)
        with pytest.raises(client_error) as e_info:
            await client.send_message(message)
        assert e_info.value.__cause__ is my_pipeline_error
        assert iothub_pipeline.send_message.call_count == 1

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
    async def test_wraps_data_in_message_and_calls_pipeline_send_message(
        self, client, iothub_pipeline, message_input
    ):
        await client.send_message(message_input)
        assert iothub_pipeline.send_message.call_count == 1
        sent_message = iothub_pipeline.send_message.call_args[0][0]
        assert isinstance(sent_message, Message)
        assert sent_message.data == message_input


class SharedClientReceiveMethodRequestTests(object):
    @pytest.mark.it("Implicitly enables methods feature if not already enabled")
    @pytest.mark.parametrize(
        "method_name",
        [pytest.param(None, id="Generic Method"), pytest.param("method_x", id="Named Method")],
    )
    async def test_enables_methods_only_if_not_already_enabled(
        self, mocker, client, iothub_pipeline, method_name
    ):
        # patch this so receive_method_request won't block
        mocker.patch.object(
            AsyncClientInbox, "get", return_value=(await create_completed_future(None))
        )

        # Verify Input Messaging enabled if not enabled
        iothub_pipeline.feature_enabled.__getitem__.return_value = (
            False
        )  # Method Requests will appear disabled
        await client.receive_method_request(method_name)
        assert iothub_pipeline.enable_feature.call_count == 1
        assert iothub_pipeline.enable_feature.call_args[0][0] == constant.METHODS

        iothub_pipeline.enable_feature.reset_mock()

        # Verify Input Messaging not enabled if already enabled
        iothub_pipeline.feature_enabled.__getitem__.return_value = (
            True
        )  # Input Messages will appear enabled
        await client.receive_method_request(method_name)
        assert iothub_pipeline.enable_feature.call_count == 0

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
    async def test_send_method_response_calls_pipeline(
        self, client, iothub_pipeline, method_response
    ):
        await client.send_method_response(method_response)
        assert iothub_pipeline.send_method_response.call_count == 1
        assert iothub_pipeline.send_method_response.call_args[0][0] is method_response

    @pytest.mark.it(
        "Waits for the completion of the 'send_method_response' pipeline operation before returning"
    )
    async def test_waits_for_pipeline_op_completion(
        self, mocker, client, iothub_pipeline, method_response
    ):
        cb_mock = mocker.patch.object(async_adapter, "AwaitableCallback").return_value
        cb_mock.completion.return_value = await create_completed_future(None)

        await client.send_method_response(method_response)

        # Assert callback is sent to pipeline
        assert iothub_pipeline.send_method_response.call_args[1]["callback"] is cb_mock
        # Assert callback completion is waited upon
        assert cb_mock.completion.call_count == 1

    @pytest.mark.it(
        "Raises a client error if the `send_method-response` pipeline operation calls back with a pipeline error"
    )
    @pytest.mark.parametrize(
        "pipeline_error,client_error",
        [
            pytest.param(
                pipeline_exceptions.ConnectionDroppedError,
                client_exceptions.ConnectionDroppedError,
                id="ConnectionDroppedError->ConnectionDroppedError",
            ),
            pytest.param(
                pipeline_exceptions.ConnectionFailedError,
                client_exceptions.ConnectionFailedError,
                id="ConnectionFailedError->ConnectionFailedError",
            ),
            pytest.param(
                pipeline_exceptions.UnauthorizedError,
                client_exceptions.CredentialError,
                id="UnauthorizedError->CredentialError",
            ),
            pytest.param(
                pipeline_exceptions.ProtocolClientError,
                client_exceptions.ClientError,
                id="ProtocolClientError->ClientError",
            ),
            pytest.param(Exception, client_exceptions.ClientError, id="Exception->ClientError"),
        ],
    )
    async def test_raises_error_on_pipeline_op_error(
        self, mocker, client, iothub_pipeline, method_response, pipeline_error, client_error
    ):
        my_pipeline_error = pipeline_error()

        def fail_send_method_response(response, callback):
            callback(error=my_pipeline_error)

        iothub_pipeline.send_method_response = mocker.MagicMock(
            side_effect=fail_send_method_response
        )
        with pytest.raises(client_error) as e_info:
            await client.send_method_response(method_response)
        assert e_info.value.__cause__ is my_pipeline_error
        assert iothub_pipeline.send_method_response.call_count == 1


class SharedClientGetTwinTests(object):
    @pytest.mark.it("Implicitly enables twin messaging feature if not already enabled")
    async def test_enables_twin_only_if_not_already_enabled(
        self, mocker, client, iothub_pipeline, fake_twin
    ):
        # patch this so get_twin won't block
        def immediate_callback(callback):
            callback(twin=fake_twin)

        mocker.patch.object(iothub_pipeline, "get_twin", side_effect=immediate_callback)

        # Verify twin enabled if not enabled
        iothub_pipeline.feature_enabled.__getitem__.return_value = (
            False
        )  # twin will appear disabled
        await client.get_twin()
        assert iothub_pipeline.enable_feature.call_count == 1
        assert iothub_pipeline.enable_feature.call_args[0][0] == constant.TWIN

        iothub_pipeline.enable_feature.reset_mock()

        # Verify twin not enabled if already enabled
        iothub_pipeline.feature_enabled.__getitem__.return_value = True  # twin will appear enabled
        await client.get_twin()
        assert iothub_pipeline.enable_feature.call_count == 0

    @pytest.mark.it("Begins a 'get_twin' pipeline operation")
    async def test_get_twin_calls_pipeline(self, client, iothub_pipeline, mocker, fake_twin):
        def immediate_callback(callback):
            callback(twin=fake_twin)

        mocker.patch.object(iothub_pipeline, "get_twin", side_effect=immediate_callback)
        await client.get_twin()
        assert iothub_pipeline.get_twin.call_count == 1

    @pytest.mark.it(
        "Waits for the completion of the 'get_twin' pipeline operation before returning"
    )
    async def test_waits_for_pipeline_op_completion(self, mocker, client, iothub_pipeline):
        cb_mock = mocker.patch.object(async_adapter, "AwaitableCallback").return_value
        cb_mock.completion.return_value = await create_completed_future(None)
        iothub_pipeline.feature_enabled.__getitem__.return_value = True  # twin will appear enabled

        await client.get_twin()

        # Assert callback is sent to pipeline
        iothub_pipeline.get_twin.call_args[1]["callback"] is cb_mock
        # Assert callback completion is waited upon
        assert cb_mock.completion.call_count == 1

    @pytest.mark.it(
        "Raises a client error if the `get_twin` pipeline operation calls back with a pipeline error"
    )
    @pytest.mark.parametrize(
        "pipeline_error,client_error",
        [
            pytest.param(
                pipeline_exceptions.ConnectionDroppedError,
                client_exceptions.ConnectionDroppedError,
                id="ConnectionDroppedError->ConnectionDroppedError",
            ),
            pytest.param(
                pipeline_exceptions.ConnectionFailedError,
                client_exceptions.ConnectionFailedError,
                id="ConnectionFailedError->ConnectionFailedError",
            ),
            pytest.param(
                pipeline_exceptions.UnauthorizedError,
                client_exceptions.CredentialError,
                id="UnauthorizedError->CredentialError",
            ),
            pytest.param(
                pipeline_exceptions.ProtocolClientError,
                client_exceptions.ClientError,
                id="ProtocolClientError->ClientError",
            ),
            pytest.param(Exception, client_exceptions.ClientError, id="Exception->ClientError"),
        ],
    )
    async def test_raises_error_on_pipeline_op_error(
        self, mocker, client, iothub_pipeline, pipeline_error, client_error
    ):
        my_pipeline_error = pipeline_error()

        def fail_get_twin(callback):
            callback(error=my_pipeline_error)

        iothub_pipeline.get_twin = mocker.MagicMock(side_effect=fail_get_twin)
        with pytest.raises(client_error) as e_info:
            await client.get_twin()
        assert e_info.value.__cause__ is my_pipeline_error
        assert iothub_pipeline.get_twin.call_count == 1

    @pytest.mark.it("Returns the twin that the pipeline returned")
    async def test_verifies_twin_returned(self, mocker, client, iothub_pipeline, fake_twin):

        # make the pipeline the twin
        def immediate_callback(callback):
            callback(twin=fake_twin)

        mocker.patch.object(iothub_pipeline, "get_twin", side_effect=immediate_callback)

        returned_twin = await client.get_twin()
        assert returned_twin == fake_twin


class SharedClientPatchTwinReportedPropertiesTests(object):
    @pytest.mark.it("Implicitly enables twin messaging feature if not already enabled")
    async def test_enables_twin_only_if_not_already_enabled(
        self, mocker, client, iothub_pipeline, twin_patch_reported
    ):
        # patch this so x_get_twin won't block
        def immediate_callback(patch, callback):
            callback()

        mocker.patch.object(
            iothub_pipeline, "patch_twin_reported_properties", side_effect=immediate_callback
        )

        # Verify twin enabled if not enabled
        iothub_pipeline.feature_enabled.__getitem__.return_value = (
            False
        )  # twin will appear disabled
        await client.patch_twin_reported_properties(twin_patch_reported)
        assert iothub_pipeline.enable_feature.call_count == 1
        assert iothub_pipeline.enable_feature.call_args[0][0] == constant.TWIN

        iothub_pipeline.enable_feature.reset_mock()

        # Verify twin not enabled if already enabled
        iothub_pipeline.feature_enabled.__getitem__.return_value = True  # twin will appear enabled
        await client.patch_twin_reported_properties(twin_patch_reported)
        assert iothub_pipeline.enable_feature.call_count == 0

    @pytest.mark.it("Begins a 'patch_twin_reported_properties' pipeline operation")
    async def test_patch_twin_reported_properties_calls_pipeline(
        self, client, iothub_pipeline, twin_patch_reported
    ):
        await client.patch_twin_reported_properties(twin_patch_reported)
        assert iothub_pipeline.patch_twin_reported_properties.call_count == 1
        assert (
            iothub_pipeline.patch_twin_reported_properties.call_args[1]["patch"]
            is twin_patch_reported
        )

    @pytest.mark.it(
        "Waits for the completion of the 'patch_twin_reported_properties' pipeline operation before returning"
    )
    async def test_waits_for_pipeline_op_completion(
        self, mocker, client, iothub_pipeline, twin_patch_reported
    ):
        cb_mock = mocker.patch.object(async_adapter, "AwaitableCallback").return_value
        cb_mock.completion.return_value = await create_completed_future(None)
        iothub_pipeline.feature_enabled.__getitem__.return_value = True  # twin will appear enabled

        await client.patch_twin_reported_properties(twin_patch_reported)

        # Assert callback is sent to pipeline
        assert iothub_pipeline.patch_twin_reported_properties.call_args[1]["callback"] is cb_mock
        # Assert callback completion is waited upon
        assert cb_mock.completion.call_count == 1

    @pytest.mark.it(
        "Raises a client error if the `patch_twin_reported_properties` pipeline operation calls back with a pipeline error"
    )
    @pytest.mark.parametrize(
        "pipeline_error,client_error",
        [
            pytest.param(
                pipeline_exceptions.ConnectionDroppedError,
                client_exceptions.ConnectionDroppedError,
                id="ConnectionDroppedError->ConnectionDroppedError",
            ),
            pytest.param(
                pipeline_exceptions.ConnectionFailedError,
                client_exceptions.ConnectionFailedError,
                id="ConnectionFailedError->ConnectionFailedError",
            ),
            pytest.param(
                pipeline_exceptions.UnauthorizedError,
                client_exceptions.CredentialError,
                id="UnauthorizedError->CredentialError",
            ),
            pytest.param(
                pipeline_exceptions.ProtocolClientError,
                client_exceptions.ClientError,
                id="ProtocolClientError->ClientError",
            ),
            pytest.param(Exception, client_exceptions.ClientError, id="Exception->ClientError"),
        ],
    )
    async def test_raises_error_on_pipeline_op_error(
        self, mocker, client, iothub_pipeline, twin_patch_reported, pipeline_error, client_error
    ):
        my_pipeline_error = pipeline_error()

        def fail_patch_twin_reported_properties(patch, callback):
            callback(error=my_pipeline_error)

        iothub_pipeline.patch_twin_reported_properties = mocker.MagicMock(
            side_effect=fail_patch_twin_reported_properties
        )
        with pytest.raises(client_error) as e_info:
            await client.patch_twin_reported_properties(twin_patch_reported)
        assert e_info.value.__cause__ is my_pipeline_error
        assert iothub_pipeline.patch_twin_reported_properties.call_count == 1


class SharedClientReceiveTwinDesiredPropertiesPatchTests(object):
    @pytest.mark.it("Implicitly enables twin patch messaging feature if not already enabled")
    async def test_enables_c2d_messaging_only_if_not_already_enabled(
        self, mocker, client, iothub_pipeline
    ):
        # patch this receive_twin_desired_properites_patch won't block
        mocker.patch.object(
            AsyncClientInbox, "get", return_value=(await create_completed_future(None))
        )

        # Verify twin patches are enabled if not enabled
        iothub_pipeline.feature_enabled.__getitem__.return_value = (
            False
        )  # twin patches will appear disabled
        await client.receive_twin_desired_properties_patch()
        assert iothub_pipeline.enable_feature.call_count == 1
        assert iothub_pipeline.enable_feature.call_args[0][0] == constant.TWIN_PATCHES

        iothub_pipeline.enable_feature.reset_mock()

        # Verify twin patches are not enabled if already enabled
        iothub_pipeline.feature_enabled.__getitem__.return_value = (
            True
        )  # twin patches will appear enabled
        await client.receive_twin_desired_properties_patch()
        assert iothub_pipeline.enable_feature.call_count == 0

    @pytest.mark.it("Returns a message from the twin patch inbox, if available")
    async def test_returns_message_from_twin_patch_inbox(self, mocker, client, twin_patch_desired):
        inbox_mock = mocker.MagicMock(autospec=AsyncClientInbox)
        inbox_mock.get.return_value = await create_completed_future(twin_patch_desired)
        manager_get_inbox_mock = mocker.patch.object(
            client._inbox_manager, "get_twin_patch_inbox", return_value=inbox_mock
        )

        received_patch = await client.receive_twin_desired_properties_patch()
        assert manager_get_inbox_mock.call_count == 1
        assert inbox_mock.get.call_count == 1
        assert received_patch is twin_patch_desired


################
# DEVICE TESTS #
################
class IoTHubDeviceClientTestsConfig(object):
    @pytest.fixture
    def client_class(self):
        return IoTHubDeviceClient

    @pytest.fixture
    def client(self, iothub_pipeline):
        """This client automatically resolves callbacks sent to the pipeline.
        It should be used for the majority of tests.
        """
        return IoTHubDeviceClient(iothub_pipeline)

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
    @pytest.mark.it("Sets on_c2d_message_received handler in the IoTHubPipeline")
    async def test_sets_on_c2d_message_received_handler_in_pipeline(
        self, client_class, iothub_pipeline
    ):
        client = client_class(iothub_pipeline)

        assert client._iothub_pipeline.on_c2d_message_received is not None
        assert (
            client._iothub_pipeline.on_c2d_message_received
            == client._inbox_manager.route_c2d_message
        )

    @pytest.mark.it("Sets the '_edge_pipeline' attribute to None")
    async def test_edge_pipeline_is_none(self, client_class, iothub_pipeline):
        client = client_class(iothub_pipeline)

        assert client._edge_pipeline is None


@pytest.mark.describe("IoTHubDeviceClient (Asynchronous) - .create_from_connection_string()")
class TestIoTHubDeviceClientCreateFromConnectionString(
    IoTHubDeviceClientTestsConfig, SharedClientCreateFromConnectionStringTests
):
    pass


@pytest.mark.describe("IoTHubDeviceClient (Asynchronous) - .create_from_shared_access_signature()")
class TestIoTHubDeviceClientCreateFromSharedAccessSignature(
    IoTHubDeviceClientTestsConfig, SharedClientCreateFromSharedAccessSignature
):
    pass


@pytest.mark.describe("IoTHubDeviceClient (Asynchronous) - .create_from_x509_certificate()")
class TestIoTHubDeviceClientCreateFromX509Certificate(IoTHubDeviceClientTestsConfig):
    hostname = "durmstranginstitute.farend"
    device_id = "MySnitch"

    @pytest.mark.it("Uses the provided arguments to create a X509AuthenticationProvider")
    async def test_auth_provider_creation(self, mocker, client_class, x509):
        mock_auth_init = mocker.patch("azure.iot.device.iothub.auth.X509AuthenticationProvider")

        client_class.create_from_x509_certificate(
            x509=x509, hostname=self.hostname, device_id=self.device_id
        )

        assert mock_auth_init.call_count == 1
        assert mock_auth_init.call_args == mocker.call(
            x509=x509, hostname=self.hostname, device_id=self.device_id
        )

    @pytest.mark.it("Uses the X509AuthenticationProvider to create an IoTHubPipeline")
    async def test_pipeline_creation(self, mocker, client_class, x509, mock_pipeline_init):
        mock_auth = mocker.patch(
            "azure.iot.device.iothub.auth.X509AuthenticationProvider"
        ).return_value

        mock_config = mocker.patch(
            "azure.iot.device.iothub.abstract_clients.config.IoTHubPipelineConfig"
        ).return_value

        client_class.create_from_x509_certificate(
            x509=x509, hostname=self.hostname, device_id=self.device_id
        )

        assert mock_pipeline_init.call_count == 1
        assert mock_pipeline_init.call_args == mocker.call(mock_auth, mock_config)

    @pytest.mark.it("Uses the IoTHubPipeline to instantiate the client")
    async def test_client_instantiation(self, mocker, client_class, x509):
        mock_pipeline = mocker.patch("azure.iot.device.iothub.pipeline.IoTHubPipeline").return_value
        spy_init = mocker.spy(client_class, "__init__")

        client_class.create_from_x509_certificate(
            x509=x509, hostname=self.hostname, device_id=self.device_id
        )

        assert spy_init.call_count == 1
        assert spy_init.call_args == mocker.call(mocker.ANY, mock_pipeline)

    @pytest.mark.it("Returns the instantiated client")
    async def test_returns_client(self, mocker, client_class, x509):
        client = client_class.create_from_x509_certificate(
            x509=x509, hostname=self.hostname, device_id=self.device_id
        )

        assert isinstance(client, client_class)


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


@pytest.mark.describe("IoTHubDeviceClient (Asynchronous) - .send_message()")
class TestIoTHubDeviceClientSendD2CMessage(
    IoTHubDeviceClientTestsConfig, SharedClientSendD2CMessageTests
):
    pass


@pytest.mark.describe("IoTHubDeviceClient (Asynchronous) - .receive_message()")
class TestIoTHubDeviceClientReceiveC2DMessage(IoTHubDeviceClientTestsConfig):
    @pytest.mark.it("Implicitly enables C2D messaging feature if not already enabled")
    async def test_enables_c2d_messaging_only_if_not_already_enabled(
        self, mocker, client, iothub_pipeline
    ):
        # patch this receive_message won't block
        mocker.patch.object(
            AsyncClientInbox, "get", return_value=(await create_completed_future(None))
        )

        # Verify C2D Messaging enabled if not enabled
        iothub_pipeline.feature_enabled.__getitem__.return_value = False  # C2D will appear disabled
        await client.receive_message()
        assert iothub_pipeline.enable_feature.call_count == 1
        assert iothub_pipeline.enable_feature.call_args[0][0] == constant.C2D_MSG

        iothub_pipeline.enable_feature.reset_mock()

        # Verify C2D Messaging not enabled if already enabled
        iothub_pipeline.feature_enabled.__getitem__.return_value = True  # C2D will appear enabled
        await client.receive_message()
        assert iothub_pipeline.enable_feature.call_count == 0

    @pytest.mark.it("Returns a message from the C2D inbox, if available")
    async def test_returns_message_from_c2d_inbox(self, mocker, client, message):
        inbox_mock = mocker.MagicMock(autospec=AsyncClientInbox)
        inbox_mock.get.return_value = await create_completed_future(message)
        manager_get_inbox_mock = mocker.patch.object(
            client._inbox_manager, "get_c2d_message_inbox", return_value=inbox_mock
        )

        received_message = await client.receive_message()
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
    def client(self, iothub_pipeline):
        """This client automatically resolves callbacks sent to the pipeline.
        It should be used for the majority of tests.
        """
        return IoTHubModuleClient(iothub_pipeline)

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
    @pytest.mark.it("Sets on_input_message_received handler in the IoTHubPipeline")
    async def test_sets_on_input_message_received_handler_in_pipeline(
        self, client_class, iothub_pipeline
    ):
        client = client_class(iothub_pipeline)

        assert client._iothub_pipeline.on_input_message_received is not None
        assert (
            client._iothub_pipeline.on_input_message_received
            == client._inbox_manager.route_input_message
        )

    @pytest.mark.it(
        "Stores the EdgePipeline from the optionally-provided 'edge_pipeline' parameter in the '_edge_pipeline' attribute"
    )
    async def test_sets_edge_pipeline_attribute(self, client_class, iothub_pipeline, edge_pipeline):
        client = client_class(iothub_pipeline, edge_pipeline)

        assert client._edge_pipeline is edge_pipeline

    @pytest.mark.it(
        "Sets the '_edge_pipeline' attribute to None, if the 'edge_pipeline' parameter is not provided"
    )
    async def test_edge_pipeline_default_none(self, client_class, iothub_pipeline):
        client = client_class(iothub_pipeline)

        assert client._edge_pipeline is None


@pytest.mark.describe("IoTHubModuleClient (Asynchronous) - .create_from_connection_string()")
class TestIoTHubModuleClientCreateFromConnectionString(
    IoTHubModuleClientTestsConfig, SharedClientCreateFromConnectionStringTests
):
    pass


@pytest.mark.describe("IoTHubModuleClient (Asynchronous) - .create_from_shared_access_signature()")
class TestIoTHubModuleClientCreateFromSharedAccessSignature(
    IoTHubModuleClientTestsConfig, SharedClientCreateFromSharedAccessSignature
):
    pass


@pytest.mark.describe(
    "IoTHubModuleClient (Asynchronous) - .create_from_edge_environment() -- Edge Container Environment"
)
class TestIoTHubModuleClientCreateFromEdgeEnvironmentWithContainerEnv(
    IoTHubModuleClientTestsConfig
):
    @pytest.mark.it(
        "Uses Edge container environment variables to create an IoTEdgeAuthenticationProvider"
    )
    async def test_auth_provider_creation(self, mocker, client_class, edge_container_environment):
        mocker.patch.dict(os.environ, edge_container_environment)
        mock_auth_init = mocker.patch("azure.iot.device.iothub.auth.IoTEdgeAuthenticationProvider")

        client_class.create_from_edge_environment()

        assert mock_auth_init.call_count == 1
        assert mock_auth_init.call_args == mocker.call(
            hostname=edge_container_environment["IOTEDGE_IOTHUBHOSTNAME"],
            device_id=edge_container_environment["IOTEDGE_DEVICEID"],
            module_id=edge_container_environment["IOTEDGE_MODULEID"],
            gateway_hostname=edge_container_environment["IOTEDGE_GATEWAYHOSTNAME"],
            module_generation_id=edge_container_environment["IOTEDGE_MODULEGENERATIONID"],
            workload_uri=edge_container_environment["IOTEDGE_WORKLOADURI"],
            api_version=edge_container_environment["IOTEDGE_APIVERSION"],
        )

    @pytest.mark.it(
        "Ignores any Edge local debug environment variables that may be present, in favor of using Edge container variables"
    )
    async def test_auth_provider_creation_hybrid_env(
        self, mocker, client_class, edge_container_environment, edge_local_debug_environment
    ):
        # This test verifies that with a hybrid environment, the auth provider will always be
        # an IoTEdgeAuthenticationProvider, even if local debug variables are present
        hybrid_environment = {**edge_container_environment, **edge_local_debug_environment}
        mocker.patch.dict(os.environ, hybrid_environment)
        mock_edge_auth_init = mocker.patch(
            "azure.iot.device.iothub.auth.IoTEdgeAuthenticationProvider"
        )
        mock_sk_auth_parse = mocker.patch(
            "azure.iot.device.iothub.auth.SymmetricKeyAuthenticationProvider"
        ).parse

        client_class.create_from_edge_environment()

        assert mock_edge_auth_init.call_count == 1
        assert mock_sk_auth_parse.call_count == 0  # we did NOT use SK auth
        assert mock_edge_auth_init.call_args == mocker.call(
            hostname=edge_container_environment["IOTEDGE_IOTHUBHOSTNAME"],
            device_id=edge_container_environment["IOTEDGE_DEVICEID"],
            module_id=edge_container_environment["IOTEDGE_MODULEID"],
            gateway_hostname=edge_container_environment["IOTEDGE_GATEWAYHOSTNAME"],
            module_generation_id=edge_container_environment["IOTEDGE_MODULEGENERATIONID"],
            workload_uri=edge_container_environment["IOTEDGE_WORKLOADURI"],
            api_version=edge_container_environment["IOTEDGE_APIVERSION"],
        )

    @pytest.mark.it(
        "Uses the IoTEdgeAuthenticationProvider to create an IoTHubPipeline and an EdgePipeline"
    )
    @pytest.mark.parametrize(
        "websockets",
        [
            pytest.param(None, id=" Default (No Websockets) "),
            pytest.param(False, id=" No Websockets "),
            pytest.param(True, id=" With Websockets "),
        ],
    )
    async def test_pipeline_creation(
        self, mocker, client_class, edge_container_environment, websockets
    ):
        mocker.patch.dict(os.environ, edge_container_environment)
        mock_auth = mocker.patch(
            "azure.iot.device.iothub.auth.IoTEdgeAuthenticationProvider"
        ).return_value
        mock_config_init = mocker.patch(
            "azure.iot.device.iothub.abstract_clients.config.IoTHubPipelineConfig"
        )

        mock_iothub_pipeline_init = mocker.patch("azure.iot.device.iothub.pipeline.IoTHubPipeline")
        mock_edge_pipeline_init = mocker.patch("azure.iot.device.iothub.pipeline.EdgePipeline")

        kwargs = {}
        if websockets:
            kwargs["websockets"] = websockets

        client_class.create_from_edge_environment(**kwargs)

        assert mock_iothub_pipeline_init.call_count == 1
        assert mock_iothub_pipeline_init.call_args == mocker.call(
            mock_auth, mock_config_init.return_value
        )
        assert mock_edge_pipeline_init.call_count == 1
        assert mock_edge_pipeline_init.call_args == mocker.call(mock_auth)

    @pytest.mark.it("Uses the IoTHubPipeline and the EdgePipeline to instantiate the client")
    async def test_client_instantiation(self, mocker, client_class, edge_container_environment):
        mocker.patch.dict(os.environ, edge_container_environment)
        # Always patch the IoTEdgeAuthenticationProvider to prevent I/O operations
        mocker.patch("azure.iot.device.iothub.auth.IoTEdgeAuthenticationProvider")
        mock_iothub_pipeline = mocker.patch(
            "azure.iot.device.iothub.pipeline.IoTHubPipeline"
        ).return_value
        mock_edge_pipeline = mocker.patch(
            "azure.iot.device.iothub.pipeline.EdgePipeline"
        ).return_value
        spy_init = mocker.spy(client_class, "__init__")

        client_class.create_from_edge_environment()

        assert spy_init.call_count == 1
        assert spy_init.call_args == mocker.call(
            mocker.ANY, mock_iothub_pipeline, edge_pipeline=mock_edge_pipeline
        )

    @pytest.mark.it("Returns the instantiated client")
    async def test_returns_client(self, mocker, client_class, edge_container_environment):
        mocker.patch.dict(os.environ, edge_container_environment)
        # Always patch the IoTEdgeAuthenticationProvider to prevent I/O operations
        mocker.patch("azure.iot.device.iothub.auth.IoTEdgeAuthenticationProvider")

        client = client_class.create_from_edge_environment()

        assert isinstance(client, client_class)

    @pytest.mark.it("Raises OSError if the environment is missing required variables")
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
        self, mocker, client_class, edge_container_environment, missing_env_var
    ):
        # Remove a variable from the fixture
        del edge_container_environment[missing_env_var]
        mocker.patch.dict(os.environ, edge_container_environment)

        with pytest.raises(OSError):
            client_class.create_from_edge_environment()

    @pytest.mark.it("Raises OSError if there is an error using the Edge for authentication")
    async def test_bad_edge_auth(self, mocker, client_class, edge_container_environment):
        mocker.patch.dict(os.environ, edge_container_environment)
        mock_auth = mocker.patch("azure.iot.device.iothub.auth.IoTEdgeAuthenticationProvider")
        error = IoTEdgeError()
        mock_auth.side_effect = error
        with pytest.raises(OSError) as e_info:
            client_class.create_from_edge_environment()
        assert e_info.value.__cause__ is error


@pytest.mark.describe(
    "IoTHubModuleClient (Asynchronous) - .create_from_edge_environment() -- Edge Local Debug Environment"
)
class TestIoTHubModuleClientCreateFromEdgeEnvironmentWithDebugEnv(IoTHubModuleClientTestsConfig):
    @pytest.fixture
    def mock_open(self, mocker):
        return mocker.patch.object(io, "open")

    @pytest.mark.it(
        "Extracts the CA certificate from the file indicated by the EdgeModuleCACertificateFile environment variable"
    )
    async def test_read_ca_cert(
        self, mocker, client_class, edge_local_debug_environment, mock_open
    ):
        mock_file_handle = mock_open.return_value.__enter__.return_value
        mocker.patch.dict(os.environ, edge_local_debug_environment)
        client_class.create_from_edge_environment()
        assert mock_open.call_count == 1
        assert mock_open.call_args == mocker.call(
            edge_local_debug_environment["EdgeModuleCACertificateFile"], mode="r"
        )
        assert mock_file_handle.read.call_count == 1

    @pytest.mark.it(
        "Uses Edge local debug environment variables to create a SymmetricKeyAuthenticationProvider (with CA cert)"
    )
    async def test_auth_provider_creation(
        self, mocker, client_class, edge_local_debug_environment, mock_open
    ):
        expected_cert = mock_open.return_value.__enter__.return_value.read.return_value
        mocker.patch.dict(os.environ, edge_local_debug_environment)
        mock_auth_parse = mocker.patch(
            "azure.iot.device.iothub.auth.SymmetricKeyAuthenticationProvider"
        ).parse

        client_class.create_from_edge_environment()

        assert mock_auth_parse.call_count == 1
        assert mock_auth_parse.call_args == mocker.call(
            edge_local_debug_environment["EdgeHubConnectionString"]
        )
        assert mock_auth_parse.return_value.ca_cert == expected_cert

    @pytest.mark.it(
        "Only uses Edge local debug variables if no Edge container variables are present in the environment"
    )
    async def test_auth_provider_and_pipeline_hybrid_env(
        self,
        mocker,
        client_class,
        edge_container_environment,
        edge_local_debug_environment,
        mock_open,
    ):
        # This test verifies that with a hybrid environment, the auth provider will always be
        # an IoTEdgeAuthenticationProvider, even if local debug variables are present
        hybrid_environment = {**edge_container_environment, **edge_local_debug_environment}
        mocker.patch.dict(os.environ, hybrid_environment)
        mock_edge_auth_init = mocker.patch(
            "azure.iot.device.iothub.auth.IoTEdgeAuthenticationProvider"
        )
        mock_sk_auth_parse = mocker.patch(
            "azure.iot.device.iothub.auth.SymmetricKeyAuthenticationProvider"
        ).parse

        client_class.create_from_edge_environment()

        assert mock_edge_auth_init.call_count == 1
        assert mock_sk_auth_parse.call_count == 0  # we did NOT use SK auth
        assert mock_edge_auth_init.call_args == mocker.call(
            hostname=edge_container_environment["IOTEDGE_IOTHUBHOSTNAME"],
            device_id=edge_container_environment["IOTEDGE_DEVICEID"],
            module_id=edge_container_environment["IOTEDGE_MODULEID"],
            gateway_hostname=edge_container_environment["IOTEDGE_GATEWAYHOSTNAME"],
            module_generation_id=edge_container_environment["IOTEDGE_MODULEGENERATIONID"],
            workload_uri=edge_container_environment["IOTEDGE_WORKLOADURI"],
            api_version=edge_container_environment["IOTEDGE_APIVERSION"],
        )

    @pytest.mark.it(
        "Uses the SymmetricKeyAuthenticationProvider to create an IoTHubPipeline and an EdgePipeline"
    )
    @pytest.mark.parametrize(
        "websockets",
        [
            pytest.param(None, id=" Default (No Websockets) "),
            pytest.param(False, id=" No Websockets "),
            pytest.param(True, id=" With Websockets "),
        ],
    )
    async def test_pipeline_creation(
        self, mocker, client_class, edge_local_debug_environment, mock_open, websockets
    ):
        mocker.patch.dict(os.environ, edge_local_debug_environment)
        mock_auth = mocker.patch(
            "azure.iot.device.iothub.auth.SymmetricKeyAuthenticationProvider"
        ).parse.return_value
        mock_config_init = mocker.patch(
            "azure.iot.device.iothub.abstract_clients.config.IoTHubPipelineConfig"
        )
        mock_iothub_pipeline_init = mocker.patch("azure.iot.device.iothub.pipeline.IoTHubPipeline")
        mock_edge_pipeline_init = mocker.patch("azure.iot.device.iothub.pipeline.EdgePipeline")

        kwargs = {}
        if websockets:
            kwargs["websockets"] = websockets
        client_class.create_from_edge_environment(**kwargs)

        assert mock_config_init.call_count == 1
        if websockets:
            assert mock_config_init.call_args == ({"websockets": websockets},)
        else:
            assert mock_config_init.call_args == ()

        assert mock_iothub_pipeline_init.call_count == 1
        assert mock_iothub_pipeline_init.call_args == mocker.call(
            mock_auth, mock_config_init.return_value
        )
        assert mock_edge_pipeline_init.call_count == 1
        assert mock_edge_pipeline_init.call_args == mocker.call(mock_auth)

    @pytest.mark.it("Uses the IoTHubPipeline and the EdgePipeline to instantiate the client")
    async def test_client_instantiation(
        self, mocker, client_class, edge_local_debug_environment, mock_open
    ):
        mocker.patch.dict(os.environ, edge_local_debug_environment)
        mock_iothub_pipeline = mocker.patch(
            "azure.iot.device.iothub.pipeline.IoTHubPipeline"
        ).return_value
        mock_edge_pipeline = mocker.patch(
            "azure.iot.device.iothub.pipeline.EdgePipeline"
        ).return_value
        spy_init = mocker.spy(client_class, "__init__")

        client_class.create_from_edge_environment()

        assert spy_init.call_count == 1
        assert spy_init.call_args == mocker.call(
            mocker.ANY, mock_iothub_pipeline, edge_pipeline=mock_edge_pipeline
        )

    @pytest.mark.it("Returns the instantiated client")
    async def test_returns_client(
        self, mocker, client_class, edge_local_debug_environment, mock_open
    ):
        mocker.patch.dict(os.environ, edge_local_debug_environment)

        client = client_class.create_from_edge_environment()

        assert isinstance(client, client_class)

    @pytest.mark.it("Raises OSError if the environment is missing required variables")
    @pytest.mark.parametrize(
        "missing_env_var", ["EdgeHubConnectionString", "EdgeModuleCACertificateFile"]
    )
    async def test_bad_environment(
        self, mocker, client_class, edge_local_debug_environment, missing_env_var, mock_open
    ):
        # Remove a variable from the fixture
        del edge_local_debug_environment[missing_env_var]
        mocker.patch.dict(os.environ, edge_local_debug_environment)

        with pytest.raises(OSError):
            client_class.create_from_edge_environment()

    # TODO: If auth package was refactored to use ConnectionString class, tests from that
    # class would increase the coverage here.
    @pytest.mark.it(
        "Raises ValueError if the connection string in the EdgeHubConnectionString environment varialbe is invalid"
    )
    @pytest.mark.parametrize(
        "bad_cs",
        [
            pytest.param("not-a-connection-string", id="Garbage string"),
            pytest.param("", id="Empty string"),
            pytest.param(
                "HostName=Invalid;DeviceId=Invalid;ModuleId=Invalid;SharedAccessKey=Invalid;GatewayHostName=Invalid",
                id="Malformed Connection String",
                marks=pytest.mark.xfail(reason="Bug in pipeline + need for auth refactor"),  # TODO
            ),
        ],
    )
    async def test_bad_connection_string(
        self, mocker, client_class, edge_local_debug_environment, bad_cs, mock_open
    ):
        edge_local_debug_environment["EdgeHubConnectionString"] = bad_cs
        mocker.patch.dict(os.environ, edge_local_debug_environment)

        with pytest.raises(ValueError):
            client_class.create_from_edge_environment()

    @pytest.mark.it(
        "Raises ValueError if the filepath in the EdgeModuleCACertificateFile environment variable is invalid"
    )
    async def test_bad_filepath(
        self, mocker, client_class, edge_local_debug_environment, mock_open
    ):
        mocker.patch.dict(os.environ, edge_local_debug_environment)
        error = FileNotFoundError()
        mock_open.side_effect = error
        with pytest.raises(ValueError) as e_info:
            client_class.create_from_edge_environment()
        assert e_info.value.__cause__ is error

    @pytest.mark.it(
        "Raises ValueError if the file referenced by the filepath in the EdgeModuleCACertificateFile environment variable cannot be opened"
    )
    async def test_bad_file_io(self, mocker, client_class, edge_local_debug_environment, mock_open):
        mocker.patch.dict(os.environ, edge_local_debug_environment)
        error = OSError()
        mock_open.side_effect = error
        with pytest.raises(ValueError) as e_info:
            client_class.create_from_edge_environment()
        assert e_info.value.__cause__ is error


@pytest.mark.describe("IoTHubModuleClient (Asynchronous) - .create_from_x509_certificate()")
class TestIoTHubModuleClientCreateFromX509Certificate(IoTHubModuleClientTestsConfig):
    hostname = "durmstranginstitute.farend"
    device_id = "MySnitch"
    module_id = "Charms"

    @pytest.mark.it("Uses the provided arguments to create a X509AuthenticationProvider")
    async def test_auth_provider_creation(self, mocker, client_class, x509):
        mock_auth_init = mocker.patch("azure.iot.device.iothub.auth.X509AuthenticationProvider")

        client_class.create_from_x509_certificate(
            x509=x509, hostname=self.hostname, device_id=self.device_id, module_id=self.module_id
        )

        assert mock_auth_init.call_count == 1
        assert mock_auth_init.call_args == mocker.call(
            x509=x509, hostname=self.hostname, device_id=self.device_id, module_id=self.module_id
        )

    @pytest.mark.parametrize(
        "websockets",
        [
            pytest.param(None, id=" Default (No Websockets) "),
            pytest.param(False, id=" No Websockets "),
            pytest.param(True, id=" With Websockets "),
        ],
    )
    @pytest.mark.it("Uses the X509AuthenticationProvider to create an IoTHubPipeline")
    async def test_pipeline_creation(
        self, mocker, client_class, x509, mock_pipeline_init, websockets
    ):
        mock_auth = mocker.patch(
            "azure.iot.device.iothub.auth.X509AuthenticationProvider"
        ).return_value

        mock_config_init = mocker.patch(
            "azure.iot.device.iothub.abstract_clients.config.IoTHubPipelineConfig"
        )
        kwargs = {}
        if websockets:
            kwargs["websockets"] = websockets

        client_class.create_from_x509_certificate(
            x509=x509,
            hostname=self.hostname,
            device_id=self.device_id,
            module_id=self.module_id,
            **kwargs
        )

        assert mock_config_init.call_count == 1
        if websockets:
            assert mock_config_init.call_args == ({"websockets": websockets},)
        else:
            assert mock_config_init.call_args == ()

        assert mock_pipeline_init.call_count == 1
        assert mock_pipeline_init.call_args == mocker.call(mock_auth, mock_config_init.return_value)

    @pytest.mark.it("Uses the IoTHubPipeline to instantiate the client")
    async def test_client_instantiation(self, mocker, client_class, x509):
        mock_pipeline = mocker.patch("azure.iot.device.iothub.pipeline.IoTHubPipeline").return_value
        spy_init = mocker.spy(client_class, "__init__")

        client_class.create_from_x509_certificate(
            x509=x509, hostname=self.hostname, device_id=self.device_id, module_id=self.module_id
        )

        assert spy_init.call_count == 1
        assert spy_init.call_args == mocker.call(mocker.ANY, mock_pipeline)

    @pytest.mark.it("Returns the instantiated client")
    async def test_returns_client(self, mocker, client_class, x509):
        client = client_class.create_from_x509_certificate(
            x509=x509, hostname=self.hostname, device_id=self.device_id, module_id=self.module_id
        )

        assert isinstance(client, client_class)


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


@pytest.mark.describe("IoTHubModuleClient (Asynchronous) - .send_message()")
class TestIoTHubNModuleClientSendD2CMessage(
    IoTHubModuleClientTestsConfig, SharedClientSendD2CMessageTests
):
    pass


@pytest.mark.describe("IoTHubModuleClient (Asynchronous) - .send_message_to_output()")
class TestIoTHubModuleClientSendToOutput(IoTHubModuleClientTestsConfig):
    @pytest.mark.it("Begins a 'send_output_event' pipeline operation")
    async def test_calls_pipeline_send_message_to_output(self, client, iothub_pipeline, message):
        output_name = "some_output"
        await client.send_message_to_output(message, output_name)
        assert iothub_pipeline.send_output_event.call_count == 1
        assert iothub_pipeline.send_output_event.call_args[0][0] is message
        assert message.output_name == output_name

    @pytest.mark.it(
        "Waits for the completion of the 'send_output_event' pipeline operation before returning"
    )
    async def test_waits_for_pipeline_op_completion(self, mocker, client, iothub_pipeline, message):
        cb_mock = mocker.patch.object(async_adapter, "AwaitableCallback").return_value
        cb_mock.completion.return_value = await create_completed_future(None)

        output_name = "some_output"
        await client.send_message_to_output(message, output_name)

        # Assert callback is sent to pipeline
        assert iothub_pipeline.send_output_event.call_args[1]["callback"] is cb_mock
        # Assert callback completion is waited upon
        assert cb_mock.completion.call_count == 1

    @pytest.mark.it(
        "Raises a client error if the `send_output_event` pipeline operation calls back with a pipeline error"
    )
    @pytest.mark.parametrize(
        "pipeline_error,client_error",
        [
            pytest.param(
                pipeline_exceptions.ConnectionDroppedError,
                client_exceptions.ConnectionDroppedError,
                id="ConnectionDroppedError->ConnectionDroppedError",
            ),
            pytest.param(
                pipeline_exceptions.ConnectionFailedError,
                client_exceptions.ConnectionFailedError,
                id="ConnectionFailedError->ConnectionFailedError",
            ),
            pytest.param(
                pipeline_exceptions.UnauthorizedError,
                client_exceptions.CredentialError,
                id="UnauthorizedError->CredentialError",
            ),
            pytest.param(
                pipeline_exceptions.ProtocolClientError,
                client_exceptions.ClientError,
                id="ProtocolClientError->ClientError",
            ),
            pytest.param(Exception, client_exceptions.ClientError, id="Exception->ClientError"),
        ],
    )
    async def test_raises_error_on_pipeline_op_error(
        self, mocker, client, iothub_pipeline, message, pipeline_error, client_error
    ):
        my_pipeline_error = pipeline_error()

        def fail_send_output_event(message, callback):
            callback(error=my_pipeline_error)

        iothub_pipeline.send_output_event = mocker.MagicMock(side_effect=fail_send_output_event)
        with pytest.raises(client_error) as e_info:
            output_name = "some_output"
            await client.send_message_to_output(message, output_name)
        assert e_info.value.__cause__ is my_pipeline_error
        assert iothub_pipeline.send_output_event.call_count == 1

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
    async def test_send_message_to_output_calls_pipeline_wraps_data_in_message(
        self, client, iothub_pipeline, message_input
    ):
        output_name = "some_output"
        await client.send_message_to_output(message_input, output_name)
        assert iothub_pipeline.send_output_event.call_count == 1
        sent_message = iothub_pipeline.send_output_event.call_args[0][0]
        assert isinstance(sent_message, Message)
        assert sent_message.data == message_input


@pytest.mark.describe("IoTHubModuleClient (Asynchronous) - .receive_message_on_input()")
class TestIoTHubModuleClientReceiveInputMessage(IoTHubModuleClientTestsConfig):
    @pytest.mark.it("Implicitly enables input messaging feature if not already enabled")
    async def test_enables_input_messaging_only_if_not_already_enabled(
        self, mocker, client, iothub_pipeline
    ):
        # patch this receive_message_on_input won't block
        mocker.patch.object(
            AsyncClientInbox, "get", return_value=(await create_completed_future(None))
        )
        input_name = "some_input"

        # Verify Input Messaging enabled if not enabled
        iothub_pipeline.feature_enabled.__getitem__.return_value = (
            False
        )  # Input Messages will appear disabled
        await client.receive_message_on_input(input_name)
        assert iothub_pipeline.enable_feature.call_count == 1
        assert iothub_pipeline.enable_feature.call_args[0][0] == constant.INPUT_MSG

        iothub_pipeline.enable_feature.reset_mock()

        # Verify Input Messaging not enabled if already enabled
        iothub_pipeline.feature_enabled.__getitem__.return_value = (
            True
        )  # Input Messages will appear enabled
        await client.receive_message_on_input(input_name)
        assert iothub_pipeline.enable_feature.call_count == 0

    @pytest.mark.it("Returns a message from the input inbox, if available")
    async def test_returns_message_from_input_inbox(self, mocker, client, message):
        inbox_mock = mocker.MagicMock(autospec=AsyncClientInbox)
        inbox_mock.get.return_value = await create_completed_future(message)
        manager_get_inbox_mock = mocker.patch.object(
            client._inbox_manager, "get_input_message_inbox", return_value=inbox_mock
        )

        input_name = "some_input"
        received_message = await client.receive_message_on_input(input_name)
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
