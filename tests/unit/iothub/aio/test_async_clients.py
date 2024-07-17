# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging
import pytest
import asyncio
import time
import urllib
import sys
from azure.iot.device import exceptions as client_exceptions
from azure.iot.device.common.auth import sastoken as st
from azure.iot.device.iothub.aio import IoTHubDeviceClient, IoTHubModuleClient
from azure.iot.device.iothub.pipeline import constant as pipeline_constant
from azure.iot.device.iothub.pipeline import exceptions as pipeline_exceptions
from azure.iot.device.iothub.pipeline import IoTHubPipelineConfig
from azure.iot.device.iothub.models import Message, MethodRequest
from azure.iot.device.iothub.abstract_clients import (
    RECEIVE_TYPE_NONE_SET,
    RECEIVE_TYPE_HANDLER,
    RECEIVE_TYPE_API,
)
from azure.iot.device.iothub.aio.async_inbox import AsyncClientInbox
from azure.iot.device.common import async_adapter
from azure.iot.device import constant as device_constant
from ..shared_client_tests import (
    SharedIoTHubClientInstantiationTests,
    SharedIoTHubClientPROPERTYHandlerTests,
    SharedIoTHubClientPROPERTYReceiverHandlerTests,
    SharedIoTHubClientPROPERTYConnectedTests,
    SharedIoTHubClientOCCURRENCEConnectTests,
    SharedIoTHubClientOCCURRENCEDisconnectTests,
    SharedIoTHubClientOCCURRENCENewSastokenRequired,
    SharedIoTHubClientOCCURRENCEBackgroundException,
    SharedIoTHubClientCreateFromConnectionStringTests,
    SharedIoTHubDeviceClientCreateFromSastokenTests,
    SharedIoTHubDeviceClientCreateFromSymmetricKeyTests,
    SharedIoTHubDeviceClientCreateFromX509CertificateTests,
    SharedIoTHubModuleClientCreateFromSastokenTests,
    SharedIoTHubModuleClientCreateFromX509CertificateTests,
    SharedIoTHubModuleClientCreateFromEdgeEnvironmentWithContainerEnvTests,
    SharedIoTHubModuleClientCreateFromEdgeEnvironmentWithDebugEnvTests,
)

pytestmark = pytest.mark.asyncio
logging.basicConfig(level=logging.DEBUG)


async def create_completed_future(result=None):
    f = asyncio.Future()
    f.set_result(result)
    return f


##########################
# SHARED CLIENT FIXTURES #
##########################
@pytest.fixture(params=["Handler Function", "Handler Coroutine"])
def handler(request):
    if request.param == "Handler Function":

        def _handler_function(arg):
            pass

        return _handler_function

    else:

        async def _handler_coroutine(arg):
            pass

        return _handler_coroutine


#######################
# SHARED CLIENT TESTS #
#######################
class SharedClientShutdownTests(object):
    @pytest.mark.it("Performs a client disconnect (and everything that entails)")
    async def test_calls_disconnect(self, mocker, client):
        # We merely check that disconnect is called here. Doing so does several things, which
        # are covered by the disconnect tests themselves. Those tests will NOT be duplicated here
        client.disconnect = mocker.MagicMock()
        client.disconnect.return_value = await create_completed_future(None)
        assert client.disconnect.call_count == 0

        await client.shutdown()

        assert client.disconnect.call_count == 1

    @pytest.mark.it("Begins a 'shutdown' pipeline operation")
    async def test_calls_pipeline_shutdown(self, mocker, client, mqtt_pipeline):
        # mock out implicit disconnect
        client.disconnect = mocker.MagicMock()
        client.disconnect.return_value = await create_completed_future(None)

        await client.shutdown()

        assert mqtt_pipeline.shutdown.call_count == 1

    @pytest.mark.it(
        "Waits for the completion of the 'shutdown' pipeline operation before returning"
    )
    async def test_waits_for_pipeline_op_completion(self, mocker, client, mqtt_pipeline):
        # mock out implicit disconnect
        client.disconnect = mocker.MagicMock()
        client.disconnect.return_value = await create_completed_future(None)
        # mock out callback
        cb_mock = mocker.patch.object(async_adapter, "AwaitableCallback").return_value
        cb_mock.completion.return_value = await create_completed_future(None)

        await client.shutdown()

        # Assert callback is sent to pipeline
        assert mqtt_pipeline.shutdown.call_args[1]["callback"] is cb_mock
        # Assert callback completion is waited upon
        assert cb_mock.completion.call_count == 1

    @pytest.mark.it(
        "Raises a client error if the `shutdown` pipeline operation calls back with a pipeline error"
    )
    @pytest.mark.parametrize(
        "pipeline_error,client_error",
        [
            pytest.param(
                pipeline_exceptions.OperationCancelled,
                client_exceptions.OperationCancelled,
                id="OperationCancelled -> OperationCancelled",
            ),
            # The only other expected errors are unexpected ones.
            pytest.param(Exception, client_exceptions.ClientError, id="Exception->ClientError"),
        ],
    )
    async def test_raises_error_on_pipeline_op_error(
        self, mocker, client, mqtt_pipeline, pipeline_error, client_error
    ):
        # mock out implicit disconnect
        client.disconnect = mocker.MagicMock()
        client.disconnect.return_value = await create_completed_future(None)

        my_pipeline_error = pipeline_error()

        def fail_shutdown(callback):
            callback(error=my_pipeline_error)

        mqtt_pipeline.shutdown.side_effect = fail_shutdown

        with pytest.raises(client_error) as e_info:
            await client.shutdown()
        assert e_info.value.__cause__ is my_pipeline_error

    @pytest.mark.it(
        "Stops the client event handlers after the `shutdown` pipeline operation is complete"
    )
    async def test_stops_client_event_handlers(self, mocker, client, mqtt_pipeline):
        # mock out implicit disconnect
        client.disconnect = mocker.MagicMock()
        client.disconnect.return_value = await create_completed_future(None)
        # Spy on handler manager stop. Note that while it does get called twice in shutdown, it
        # only happens once here because we have mocked disconnect (where first stoppage) occurs
        hm_stop_spy = mocker.spy(client._handler_manager, "stop")

        def check_handlers_and_complete(callback):
            assert hm_stop_spy.call_count == 0
            callback()

        mqtt_pipeline.shutdown.side_effect = check_handlers_and_complete

        await client.shutdown()

        assert hm_stop_spy.call_count == 1
        assert hm_stop_spy.call_args == mocker.call(receiver_handlers_only=False)


class SharedClientConnectTests(object):
    @pytest.mark.it("Begins a 'connect' pipeline operation")
    async def test_calls_pipeline_connect(self, client, mqtt_pipeline):
        await client.connect()
        assert mqtt_pipeline.connect.call_count == 1

    @pytest.mark.it("Waits for the completion of the 'connect' pipeline operation before returning")
    async def test_waits_for_pipeline_op_completion(self, mocker, client, mqtt_pipeline):
        cb_mock = mocker.patch.object(async_adapter, "AwaitableCallback").return_value
        cb_mock.completion.return_value = await create_completed_future(None)

        await client.connect()

        # Assert callback is sent to pipeline
        assert mqtt_pipeline.connect.call_args[1]["callback"] is cb_mock
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
            pytest.param(
                pipeline_exceptions.TlsExchangeAuthError,
                client_exceptions.ClientError,
                id="TlsExchangeAuthError->ClientError",
            ),
            pytest.param(
                pipeline_exceptions.ProtocolProxyError,
                client_exceptions.ClientError,
                id="ProtocolProxyError->ClientError",
            ),
            pytest.param(
                pipeline_exceptions.OperationCancelled,
                client_exceptions.OperationCancelled,
                id="OperationCancelled -> OperationCancelled",
            ),
            pytest.param(
                pipeline_exceptions.OperationTimeout,
                client_exceptions.OperationTimeout,
                id="OperationTimeout->OperationTimeout",
            ),
            pytest.param(Exception, client_exceptions.ClientError, id="Exception->ClientError"),
        ],
    )
    async def test_raises_error_on_pipeline_op_error(
        self, mocker, client, mqtt_pipeline, pipeline_error, client_error
    ):
        my_pipeline_error = pipeline_error()

        def fail_connect(callback):
            callback(error=my_pipeline_error)

        mqtt_pipeline.connect = mocker.MagicMock(side_effect=fail_connect)
        with pytest.raises(client_error) as e_info:
            await client.connect()
        assert e_info.value.__cause__ is my_pipeline_error
        assert mqtt_pipeline.connect.call_count == 1


class SharedClientDisconnectTests(object):
    @pytest.mark.it(
        "Runs a 'disconnect' pipeline operation, stops the receiver handlers, then runs a second 'disconnect' pipeline operation"
    )
    async def test_calls_pipeline_disconnect(self, mocker, client, mqtt_pipeline):
        manager_mock = mocker.MagicMock()
        client._handler_manager = mocker.MagicMock()
        manager_mock.attach_mock(mqtt_pipeline.disconnect, "disconnect")
        manager_mock.attach_mock(client._handler_manager.stop, "stop")

        await client.disconnect()
        assert mqtt_pipeline.disconnect.call_count == 2
        assert client._handler_manager.stop.call_count == 1
        assert manager_mock.mock_calls == [
            mocker.call.disconnect(callback=mocker.ANY),
            mocker.call.stop(receiver_handlers_only=True),
            mocker.call.disconnect(callback=mocker.ANY),
        ]

    @pytest.mark.it(
        "Waits for the completion of both 'disconnect' pipeline operations before returning"
    )
    async def test_waits_for_pipeline_op_completion(self, mocker, client, mqtt_pipeline):
        # Make a mock that returns two different objects (since there are two AwaitableCallbacks used)
        cb_mock1 = mocker.MagicMock()
        cb_mock2 = mocker.MagicMock()
        cb_mock1.completion.return_value = await create_completed_future(None)
        cb_mock2.completion.return_value = await create_completed_future(None)
        cb_mock_init = mocker.patch.object(async_adapter, "AwaitableCallback")
        cb_mock_init.side_effect = [cb_mock1, cb_mock2]

        await client.disconnect()

        # Disconnect called twice
        assert mqtt_pipeline.disconnect.call_count == 2
        # Assert callbacks sent to pipeline
        assert mqtt_pipeline.disconnect.call_args_list[0][1]["callback"] is cb_mock1
        assert mqtt_pipeline.disconnect.call_args_list[1][1]["callback"] is cb_mock2
        # Assert callback completions were waited upon
        assert cb_mock1.completion.call_count == 1
        assert cb_mock2.completion.call_count == 1

        # Give the AwaitableCallback mock a standardized return value again, since
        # .disconnect() will be called in cleanup
        cb_mock_init.side_effect = None
        cb_mock_init.return_value.completion.return_value = await create_completed_future(None)

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
            pytest.param(
                pipeline_exceptions.OperationCancelled,
                client_exceptions.OperationCancelled,
                id="OperationCancelled -> OperationCancelled",
            ),
            pytest.param(Exception, client_exceptions.ClientError, id="Exception->ClientError"),
        ],
    )
    async def test_raises_error_on_pipeline_op_error(
        self, mocker, client, mqtt_pipeline, pipeline_error, client_error
    ):
        my_pipeline_error = pipeline_error()

        def fail_disconnect(callback):
            callback(error=my_pipeline_error)

        mqtt_pipeline.disconnect.side_effect = fail_disconnect
        with pytest.raises(client_error) as e_info:
            await client.disconnect()
        assert e_info.value.__cause__ is my_pipeline_error
        assert mqtt_pipeline.disconnect.call_count == 1

        # Unset the side effect, since disconnect is used to clean up fixtures.
        mqtt_pipeline.disconnect.side_effect = None


class SharedClientUpdateSasTokenTests(object):
    # NOTE: Classes that inherit from this class must define some additional fixtures not included
    # here, which will be specific to a device or module:
    #   - sas_config: returns an IoTHubPipelineConfiguration configured for Device/Module
    #   - uri: A uri that matches the uri in the SAS from sas_token_string fixture
    #   - nonmatching_uri: A uri that does NOT match to the uri in the SAS from sas_token_string
    #   - invalid_uri: A uri that is invalid (poorly formed, missing data, etc.)

    @pytest.fixture
    def device_id(self, sas_token_string):
        # NOTE: This is kind of unconventional, but this is the easiest way to extract the
        # device id from a sastoken string
        sastoken = st.NonRenewableSasToken(sas_token_string)
        token_uri_pieces = sastoken.resource_uri.split("/")
        device_id = token_uri_pieces[2]
        return device_id

    @pytest.fixture
    def hostname(self, sas_token_string):
        # NOTE: This is kind of unconventional, but this is the easiest way to extract the
        # hostname from a sastoken string
        sastoken = st.NonRenewableSasToken(sas_token_string)
        token_uri_pieces = sastoken.resource_uri.split("/")
        hostname = token_uri_pieces[0]
        return hostname

    @pytest.fixture
    def sas_client(self, client_class, mqtt_pipeline, http_pipeline, sas_config):
        """Client configured as if using user-provided, non-renewable SAS auth"""
        mqtt_pipeline.pipeline_configuration = sas_config
        http_pipeline.pipeline_configuration = sas_config
        return client_class(mqtt_pipeline, http_pipeline)

    @pytest.fixture
    def sas_client_manual_cb(
        self, client_class, mqtt_pipeline_manual_cb, http_pipeline_manual_cb, sas_config
    ):
        mqtt_pipeline_manual_cb.pipeline_configuration = sas_config
        http_pipeline_manual_cb.pipeline_configuration = sas_config
        return client_class(mqtt_pipeline_manual_cb, http_pipeline_manual_cb)

    @pytest.fixture
    def new_sas_token_string(self, uri):
        # New SASToken String that matches old device id, module_id and hostname
        signature = "AvCQCS7uVk8Lxau7rBs/jek4iwENIwLwpEV7NIJySc0="
        new_token_string = "SharedAccessSignature sr={uri}&sig={signature}&se={expiry}".format(
            uri=urllib.parse.quote(uri, safe=""),
            signature=urllib.parse.quote(signature, safe=""),
            expiry=int(time.time()) + 3600,
        )
        return new_token_string

    @pytest.mark.it(
        "Creates a new NonRenewableSasToken and sets it on the PipelineConfig, if the new SAS Token string matches the existing SAS Token's information"
    )
    async def test_updates_token_if_match_vals(self, sas_client, new_sas_token_string):
        old_sas_token_string = str(sas_client._mqtt_pipeline.pipeline_configuration.sastoken)

        # Update to new token
        await sas_client.update_sastoken(new_sas_token_string)

        # Sastoken was updated
        assert (
            str(sas_client._mqtt_pipeline.pipeline_configuration.sastoken) == new_sas_token_string
        )
        assert (
            str(sas_client._mqtt_pipeline.pipeline_configuration.sastoken) != old_sas_token_string
        )

    @pytest.mark.it("Begins a 'reauthorize connection' pipeline operation")
    async def test_calls_pipeline_reauthorize(
        self, sas_client, new_sas_token_string, mqtt_pipeline
    ):
        await sas_client.update_sastoken(new_sas_token_string)
        assert mqtt_pipeline.reauthorize_connection.call_count == 1

    @pytest.mark.it(
        "Waits for the completion of the 'reauthorize connection' pipeline operation before returning"
    )
    async def test_waits_for_pipeline_op_completion(
        self, mocker, sas_client, mqtt_pipeline, new_sas_token_string
    ):
        cb_mock = mocker.patch.object(async_adapter, "AwaitableCallback").return_value
        cb_mock.completion.return_value = await create_completed_future(None)

        await sas_client.update_sastoken(new_sas_token_string)

        # Assert callback is sent to pipeline
        assert mqtt_pipeline.reauthorize_connection.call_args[1]["callback"] is cb_mock
        # Assert callback completion is waited upon
        assert cb_mock.completion.call_count == 1

    @pytest.mark.it(
        "Raises a ClientError if the 'reauthorize connection' pipeline operation calls back with a pipeline error"
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
            pytest.param(
                pipeline_exceptions.TlsExchangeAuthError,
                client_exceptions.ClientError,
                id="TlsExchangeAuthError->ClientError",
            ),
            pytest.param(
                pipeline_exceptions.ProtocolProxyError,
                client_exceptions.ClientError,
                id="ProtocolProxyError->ClientError",
            ),
            pytest.param(
                pipeline_exceptions.OperationCancelled,
                client_exceptions.OperationCancelled,
                id="OperationCancelled -> OperationCancelled",
            ),
            pytest.param(
                pipeline_exceptions.OperationTimeout,
                client_exceptions.OperationTimeout,
                id="OperationTimeout->OperationTimeout",
            ),
            pytest.param(Exception, client_exceptions.ClientError, id="Exception->ClientError"),
        ],
    )
    async def test_raises_error_on_pipeline_op_error(
        self, mocker, sas_client, mqtt_pipeline, new_sas_token_string, client_error, pipeline_error
    ):
        # NOTE: If/When the MQTT pipeline is updated so that the reauthorize op waits for
        # reconnection in order to return (currently it just waits for the disconnect),
        # there will need to be additional connect-related errors in the parametrization.
        my_pipeline_error = pipeline_error()

        def fail_reauth(callback):
            callback(error=my_pipeline_error)

        mqtt_pipeline.reauthorize_connection = mocker.MagicMock(side_effect=fail_reauth)
        with pytest.raises(client_error) as e_info:
            await sas_client.update_sastoken(new_sas_token_string)
        assert e_info.value.__cause__ is my_pipeline_error
        assert mqtt_pipeline.reauthorize_connection.call_count == 1

    @pytest.mark.it(
        "Raises a ClientError if the client was created with an X509 certificate instead of SAS"
    )
    async def test_created_with_x509(self, mocker, sas_client, new_sas_token_string):
        # Modify client to seem as if created with X509
        x509_client = sas_client
        x509_client._mqtt_pipeline.pipeline_configuration.sastoken = None
        x509_client._mqtt_pipeline.pipeline_configuration.x509 = mocker.MagicMock()

        # Client raises error
        with pytest.raises(client_exceptions.ClientError):
            await x509_client.update_sastoken(new_sas_token_string)

    @pytest.mark.it(
        "Raises a ClientError if the client was created with a renewable, non-user provided SAS (e.g. from connection string, symmetric key, etc.)"
    )
    async def test_created_with_renewable_sas(self, mocker, sas_client, uri, new_sas_token_string):
        # Modify client to seem as if created with renewable SAS
        mock_signing_mechanism = mocker.MagicMock()
        mock_signing_mechanism.sign.return_value = "ajsc8nLKacIjGsYyB4iYDFCZaRMmmDrUuY5lncYDYPI="
        renewable_token = st.RenewableSasToken(uri, mock_signing_mechanism)
        sas_client._mqtt_pipeline.pipeline_configuration.sastoken = renewable_token

        # Client raises error
        with pytest.raises(client_exceptions.ClientError):
            await sas_client.update_sastoken(new_sas_token_string)

    @pytest.mark.it("Raises a ValueError if there is an error creating a new NonRenewableSasToken")
    async def test_token_error(self, mocker, sas_client, new_sas_token_string):
        # NOTE: specific inputs that could cause this are tested in the sastoken test module
        sastoken_mock = mocker.patch.object(st.NonRenewableSasToken, "__init__")
        token_err = st.SasTokenError("Some SasToken failure")
        sastoken_mock.side_effect = token_err

        with pytest.raises(ValueError) as e_info:
            await sas_client.update_sastoken(new_sas_token_string)
        assert e_info.value.__cause__ is token_err

    @pytest.mark.it("Raises ValueError if the provided SAS token string has already expired")
    async def test_expired_token(self, mocker, sas_client, uri):
        sastoken_str = "SharedAccessSignature sr={resource}&sig={signature}&se={expiry}".format(
            resource=urllib.parse.quote(uri, safe=""),
            signature=urllib.parse.quote("ajsc8nLKacIjGsYyB4iYDFCZaRMmmDrUuY5lncYDYPI=", safe=""),
            expiry=int(time.time() - 3600),  # expired
        )

        with pytest.raises(ValueError):
            await sas_client.update_sastoken(sastoken_str)

    @pytest.mark.it(
        "Raises ValueError if the provided SAS token string does not match the previous SAS details"
    )
    async def test_nonmatching_uri_in_new_token(self, sas_client, nonmatching_uri):
        signature = "AvCQCS7uVk8Lxau7rBs/jek4iwENIwLwpEV7NIJySc0="
        sastoken_str = "SharedAccessSignature sr={uri}&sig={signature}&se={expiry}".format(
            uri=urllib.parse.quote(nonmatching_uri, safe=""),
            signature=urllib.parse.quote(signature),
            expiry=int(time.time()) + 3600,
        )

        with pytest.raises(ValueError):
            await sas_client.update_sastoken(sastoken_str)

    @pytest.mark.it("Raises ValueError if the provided SAS token string has an invalid URI")
    async def test_raises_value_error_invalid_uri(self, mocker, sas_client, invalid_uri):
        sastoken_str = "SharedAccessSignature sr={resource}&sig={signature}&se={expiry}".format(
            resource=urllib.parse.quote(invalid_uri, safe=""),
            signature=urllib.parse.quote("ajsc8nLKacIjGsYyB4iYDFCZaRMmmDrUuY5lncYDYPI=", safe=""),
            expiry=int(time.time() + 3600),
        )

        with pytest.raises(ValueError):
            await sas_client.update_sastoken(sastoken_str)


class SharedClientSendD2CMessageTests(object):
    @pytest.mark.it("Begins a 'send_message' pipeline operation")
    async def test_calls_pipeline_send_message(self, client, mqtt_pipeline, message):
        await client.send_message(message)
        assert mqtt_pipeline.send_message.call_count == 1
        assert mqtt_pipeline.send_message.call_args[0][0] is message

    @pytest.mark.it(
        "Waits for the completion of the 'send_message' pipeline operation before returning"
    )
    async def test_waits_for_pipeline_op_completion(self, mocker, client, mqtt_pipeline, message):
        cb_mock = mocker.patch.object(async_adapter, "AwaitableCallback").return_value
        cb_mock.completion.return_value = await create_completed_future(None)

        await client.send_message(message)

        # Assert callback is sent to pipeline
        assert mqtt_pipeline.send_message.call_args[1]["callback"] is cb_mock
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
                pipeline_exceptions.NoConnectionError,
                client_exceptions.NoConnectionError,
                id="NoConnectionError->NoConnectionError",
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
            pytest.param(
                pipeline_exceptions.OperationCancelled,
                client_exceptions.OperationCancelled,
                id="OperationCancelled -> OperationCancelled",
            ),
            pytest.param(
                pipeline_exceptions.OperationTimeout,
                client_exceptions.OperationTimeout,
                id="OperationTimeout -> OperationTimeout",
            ),
            pytest.param(Exception, client_exceptions.ClientError, id="Exception->ClientError"),
        ],
    )
    async def test_raises_error_on_pipeline_op_error(
        self, mocker, client, mqtt_pipeline, message, client_error, pipeline_error
    ):
        my_pipeline_error = pipeline_error()

        def fail_send_message(message, callback):
            callback(error=my_pipeline_error)

        mqtt_pipeline.send_message = mocker.MagicMock(side_effect=fail_send_message)
        with pytest.raises(client_error) as e_info:
            await client.send_message(message)
        assert e_info.value.__cause__ is my_pipeline_error
        assert mqtt_pipeline.send_message.call_count == 1

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
        self, client, mqtt_pipeline, message_input
    ):
        await client.send_message(message_input)
        assert mqtt_pipeline.send_message.call_count == 1
        sent_message = mqtt_pipeline.send_message.call_args[0][0]
        assert isinstance(sent_message, Message)
        assert sent_message.data == message_input

    @pytest.mark.it("Raises error when message data size is greater than 256 KB")
    async def test_raises_error_when_message_data_greater_than_256(self, client, mqtt_pipeline):
        data_input = "serpensortia" * 256000
        message = Message(data_input)
        with pytest.raises(ValueError) as e_info:
            await client.send_message(message)
        assert "256 KB" in e_info.value.args[0]
        assert mqtt_pipeline.send_message.call_count == 0

    @pytest.mark.it("Raises error when message size is greater than 256 KB")
    async def test_raises_error_when_message_size_greater_than_256(self, client, mqtt_pipeline):
        data_input = "serpensortia"
        message = Message(data_input)
        message.custom_properties["spell"] = data_input * 256000
        with pytest.raises(ValueError) as e_info:
            await client.send_message(message)
        assert "256 KB" in e_info.value.args[0]
        assert mqtt_pipeline.send_message.call_count == 0

    @pytest.mark.skipif(
        sys.version_info >= (3, 12),
        reason="Python 3.12 appears to have an issue. Investigate further.",
    )
    @pytest.mark.it("Does not raises error when message data size is equal to 256 KB")
    async def test_raises_error_when_message_data_equal_to_256(self, client, mqtt_pipeline):
        data_input = "a" * 262095
        message = Message(data_input)
        # This check was put as message class may undergo the default content type encoding change
        # and the above calculation will change.
        if message.get_size() != device_constant.TELEMETRY_MESSAGE_SIZE_LIMIT:
            assert False

        await client.send_message(message)

        assert mqtt_pipeline.send_message.call_count == 1
        sent_message = mqtt_pipeline.send_message.call_args[0][0]
        assert isinstance(sent_message, Message)
        assert sent_message.data == data_input


class SharedClientReceiveMethodRequestTests(object):
    @pytest.mark.it("Implicitly enables methods feature if not already enabled")
    @pytest.mark.parametrize(
        "method_name",
        [pytest.param(None, id="Generic Method"), pytest.param("method_x", id="Named Method")],
    )
    async def test_enables_methods_only_if_not_already_enabled(
        self, mocker, client, mqtt_pipeline, method_name
    ):
        # patch this so receive_method_request won't block
        mocker.patch.object(
            AsyncClientInbox, "get", return_value=(await create_completed_future(None))
        )

        # Verify Input Messaging enabled if not enabled
        mqtt_pipeline.feature_enabled.__getitem__.return_value = (
            False  # Method Requests will appear disabled
        )
        await client.receive_method_request(method_name)
        assert mqtt_pipeline.enable_feature.call_count == 1
        assert mqtt_pipeline.enable_feature.call_args[0][0] == pipeline_constant.METHODS

        mqtt_pipeline.enable_feature.reset_mock()

        # Verify Input Messaging not enabled if already enabled
        mqtt_pipeline.feature_enabled.__getitem__.return_value = (
            True  # Input Messages will appear enabled
        )
        await client.receive_method_request(method_name)
        assert mqtt_pipeline.enable_feature.call_count == 0

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

    @pytest.mark.it("Locks the client to API Receive Mode if the receive mode has not yet been set")
    @pytest.mark.parametrize(
        "method_name",
        [pytest.param(None, id="Generic Method"), pytest.param("method_x", id="Named Method")],
    )
    async def test_receive_mode_not_set(self, mocker, client, method_name):
        # patch this so receive_method_request won't block
        mocker.patch.object(
            AsyncClientInbox, "get", return_value=(await create_completed_future(None))
        )

        assert client._receive_type is RECEIVE_TYPE_NONE_SET
        await client.receive_method_request(method_name)
        assert client._receive_type is RECEIVE_TYPE_API

    @pytest.mark.it(
        "Does not modify the client receive mode if it has already been set to API Receive Mode"
    )
    @pytest.mark.parametrize(
        "method_name",
        [pytest.param(None, id="Generic Method"), pytest.param("method_x", id="Named Method")],
    )
    async def test_receive_mode_set_api(self, mocker, client, method_name):
        # patch this so receive_method_request won't block
        mocker.patch.object(
            AsyncClientInbox, "get", return_value=(await create_completed_future(None))
        )

        client._receive_type = RECEIVE_TYPE_API
        await client.receive_method_request(method_name)
        assert client._receive_type is RECEIVE_TYPE_API

    @pytest.mark.it(
        "Raises a ClientError and does nothing else if the client receive mode has been set to Handler Receive Mode"
    )
    @pytest.mark.parametrize(
        "method_name",
        [pytest.param(None, id="Generic Method"), pytest.param("method_x", id="Named Method")],
    )
    async def test_receive_mode_set_handler(self, mocker, client, method_name, mqtt_pipeline):
        # patch this so receive_method_request won't block
        inbox_get_mock = mocker.patch.object(
            AsyncClientInbox, "get", return_value=(await create_completed_future(None))
        )
        # patch this so we can make sure feature enabled isn't modified
        mqtt_pipeline.feature_enabled.__getitem__.return_value = False

        client._receive_type = RECEIVE_TYPE_HANDLER
        # Error was raised
        with pytest.raises(client_exceptions.ClientError):
            await client.receive_method_request(method_name)
        # Feature was not enabled
        assert mqtt_pipeline.enable_feature.call_count == 0
        # Inbox get was not called
        assert inbox_get_mock.call_count == 0


class SharedClientSendMethodResponseTests(object):
    @pytest.mark.it("Begins a 'send_method_response' pipeline operation")
    async def test_send_method_response_calls_pipeline(
        self, client, mqtt_pipeline, method_response
    ):
        await client.send_method_response(method_response)
        assert mqtt_pipeline.send_method_response.call_count == 1
        assert mqtt_pipeline.send_method_response.call_args[0][0] is method_response

    @pytest.mark.it(
        "Waits for the completion of the 'send_method_response' pipeline operation before returning"
    )
    async def test_waits_for_pipeline_op_completion(
        self, mocker, client, mqtt_pipeline, method_response
    ):
        cb_mock = mocker.patch.object(async_adapter, "AwaitableCallback").return_value
        cb_mock.completion.return_value = await create_completed_future(None)

        await client.send_method_response(method_response)

        # Assert callback is sent to pipeline
        assert mqtt_pipeline.send_method_response.call_args[1]["callback"] is cb_mock
        # Assert callback completion is waited upon
        assert cb_mock.completion.call_count == 1

    @pytest.mark.it(
        "Raises a client error if the `send_method_response` pipeline operation calls back with a pipeline error"
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
                pipeline_exceptions.NoConnectionError,
                client_exceptions.NoConnectionError,
                id="NoConnectionError->NoConnectionError",
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
            pytest.param(
                pipeline_exceptions.OperationCancelled,
                client_exceptions.OperationCancelled,
                id="OperationCancelled -> OperationCancelled",
            ),
            pytest.param(
                pipeline_exceptions.OperationTimeout,
                client_exceptions.OperationTimeout,
                id="OperationTimeout -> OperationTimeout",
            ),
            pytest.param(Exception, client_exceptions.ClientError, id="Exception->ClientError"),
        ],
    )
    async def test_raises_error_on_pipeline_op_error(
        self, mocker, client, mqtt_pipeline, method_response, pipeline_error, client_error
    ):
        my_pipeline_error = pipeline_error()

        def fail_send_method_response(response, callback):
            callback(error=my_pipeline_error)

        mqtt_pipeline.send_method_response = mocker.MagicMock(side_effect=fail_send_method_response)
        with pytest.raises(client_error) as e_info:
            await client.send_method_response(method_response)
        assert e_info.value.__cause__ is my_pipeline_error
        assert mqtt_pipeline.send_method_response.call_count == 1


class SharedClientGetTwinTests(object):
    @pytest.mark.it("Implicitly enables twin messaging feature if not already enabled")
    async def test_enables_twin_only_if_not_already_enabled(
        self, mocker, client, mqtt_pipeline, fake_twin
    ):
        # patch this so get_twin won't block
        def immediate_callback(callback):
            callback(twin=fake_twin)

        mocker.patch.object(mqtt_pipeline, "get_twin", side_effect=immediate_callback)

        # Verify twin enabled if not enabled
        mqtt_pipeline.feature_enabled.__getitem__.return_value = False  # twin will appear disabled
        await client.get_twin()
        assert mqtt_pipeline.enable_feature.call_count == 1
        assert mqtt_pipeline.enable_feature.call_args[0][0] == pipeline_constant.TWIN

        mqtt_pipeline.enable_feature.reset_mock()

        # Verify twin not enabled if already enabled
        mqtt_pipeline.feature_enabled.__getitem__.return_value = True  # twin will appear enabled
        await client.get_twin()
        assert mqtt_pipeline.enable_feature.call_count == 0

    @pytest.mark.it("Begins a 'get_twin' pipeline operation")
    async def test_get_twin_calls_pipeline(self, client, mqtt_pipeline, mocker, fake_twin):
        def immediate_callback(callback):
            callback(twin=fake_twin)

        mocker.patch.object(mqtt_pipeline, "get_twin", side_effect=immediate_callback)
        await client.get_twin()
        assert mqtt_pipeline.get_twin.call_count == 1

    @pytest.mark.it(
        "Waits for the completion of the 'get_twin' pipeline operation before returning"
    )
    async def test_waits_for_pipeline_op_completion(self, mocker, client, mqtt_pipeline):
        cb_mock = mocker.patch.object(async_adapter, "AwaitableCallback").return_value
        cb_mock.completion.return_value = await create_completed_future(None)
        mqtt_pipeline.feature_enabled.__getitem__.return_value = True  # twin will appear enabled

        await client.get_twin()

        # Assert callback is sent to pipeline
        mqtt_pipeline.get_twin.call_args[1]["callback"] is cb_mock
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
                pipeline_exceptions.NoConnectionError,
                client_exceptions.NoConnectionError,
                id="NoConnectionError->NoConnectionError",
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
            pytest.param(
                pipeline_exceptions.OperationCancelled,
                client_exceptions.OperationCancelled,
                id="OperationCancelled -> OperationCancelled",
            ),
            pytest.param(
                pipeline_exceptions.OperationTimeout,
                client_exceptions.OperationTimeout,
                id="OperationTimeout -> OperationTimeout",
            ),
            pytest.param(Exception, client_exceptions.ClientError, id="Exception->ClientError"),
        ],
    )
    async def test_raises_error_on_pipeline_op_error(
        self, mocker, client, mqtt_pipeline, pipeline_error, client_error
    ):
        my_pipeline_error = pipeline_error()

        def fail_get_twin(callback):
            callback(error=my_pipeline_error)

        mqtt_pipeline.get_twin = mocker.MagicMock(side_effect=fail_get_twin)
        with pytest.raises(client_error) as e_info:
            await client.get_twin()
        assert e_info.value.__cause__ is my_pipeline_error
        assert mqtt_pipeline.get_twin.call_count == 1

    @pytest.mark.it("Returns the twin that the pipeline returned")
    async def test_verifies_twin_returned(self, mocker, client, mqtt_pipeline, fake_twin):

        # make the pipeline the twin
        def immediate_callback(callback):
            callback(twin=fake_twin)

        mocker.patch.object(mqtt_pipeline, "get_twin", side_effect=immediate_callback)

        returned_twin = await client.get_twin()
        assert returned_twin == fake_twin


class SharedClientPatchTwinReportedPropertiesTests(object):
    @pytest.mark.it("Implicitly enables twin messaging feature if not already enabled")
    async def test_enables_twin_only_if_not_already_enabled(
        self, mocker, client, mqtt_pipeline, twin_patch_reported
    ):
        # patch this so x_get_twin won't block
        def immediate_callback(patch, callback):
            callback()

        mocker.patch.object(
            mqtt_pipeline, "patch_twin_reported_properties", side_effect=immediate_callback
        )

        # Verify twin enabled if not enabled
        mqtt_pipeline.feature_enabled.__getitem__.return_value = False  # twin will appear disabled
        await client.patch_twin_reported_properties(twin_patch_reported)
        assert mqtt_pipeline.enable_feature.call_count == 1
        assert mqtt_pipeline.enable_feature.call_args[0][0] == pipeline_constant.TWIN

        mqtt_pipeline.enable_feature.reset_mock()

        # Verify twin not enabled if already enabled
        mqtt_pipeline.feature_enabled.__getitem__.return_value = True  # twin will appear enabled
        await client.patch_twin_reported_properties(twin_patch_reported)
        assert mqtt_pipeline.enable_feature.call_count == 0

    @pytest.mark.it("Begins a 'patch_twin_reported_properties' pipeline operation")
    async def test_patch_twin_reported_properties_calls_pipeline(
        self, client, mqtt_pipeline, twin_patch_reported
    ):
        await client.patch_twin_reported_properties(twin_patch_reported)
        assert mqtt_pipeline.patch_twin_reported_properties.call_count == 1
        assert (
            mqtt_pipeline.patch_twin_reported_properties.call_args[1]["patch"]
            is twin_patch_reported
        )

    @pytest.mark.it(
        "Waits for the completion of the 'patch_twin_reported_properties' pipeline operation before returning"
    )
    async def test_waits_for_pipeline_op_completion(
        self, mocker, client, mqtt_pipeline, twin_patch_reported
    ):
        cb_mock = mocker.patch.object(async_adapter, "AwaitableCallback").return_value
        cb_mock.completion.return_value = await create_completed_future(None)
        mqtt_pipeline.feature_enabled.__getitem__.return_value = True  # twin will appear enabled

        await client.patch_twin_reported_properties(twin_patch_reported)

        # Assert callback is sent to pipeline
        assert mqtt_pipeline.patch_twin_reported_properties.call_args[1]["callback"] is cb_mock
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
                pipeline_exceptions.NoConnectionError,
                client_exceptions.NoConnectionError,
                id="NoConnectionError->NoConnectionError",
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
            pytest.param(
                pipeline_exceptions.OperationCancelled,
                client_exceptions.OperationCancelled,
                id="OperationCancelled -> OperationCancelled",
            ),
            pytest.param(
                pipeline_exceptions.OperationTimeout,
                client_exceptions.OperationTimeout,
                id="OperationTimeout -> OperationTimeout",
            ),
            pytest.param(Exception, client_exceptions.ClientError, id="Exception->ClientError"),
        ],
    )
    async def test_raises_error_on_pipeline_op_error(
        self, mocker, client, mqtt_pipeline, twin_patch_reported, pipeline_error, client_error
    ):
        my_pipeline_error = pipeline_error()

        def fail_patch_twin_reported_properties(patch, callback):
            callback(error=my_pipeline_error)

        mqtt_pipeline.patch_twin_reported_properties = mocker.MagicMock(
            side_effect=fail_patch_twin_reported_properties
        )
        with pytest.raises(client_error) as e_info:
            await client.patch_twin_reported_properties(twin_patch_reported)
        assert e_info.value.__cause__ is my_pipeline_error
        assert mqtt_pipeline.patch_twin_reported_properties.call_count == 1


class SharedClientReceiveTwinDesiredPropertiesPatchTests(object):
    @pytest.mark.it("Implicitly enables twin patch messaging feature if not already enabled")
    async def test_enables_c2d_messaging_only_if_not_already_enabled(
        self, mocker, client, mqtt_pipeline
    ):
        # patch this receive_twin_desired_properties_patch won't block
        mocker.patch.object(
            AsyncClientInbox, "get", return_value=(await create_completed_future(None))
        )

        # Verify twin patches are enabled if not enabled
        mqtt_pipeline.feature_enabled.__getitem__.return_value = (
            False  # twin patches will appear disabled
        )
        await client.receive_twin_desired_properties_patch()
        assert mqtt_pipeline.enable_feature.call_count == 1
        assert mqtt_pipeline.enable_feature.call_args[0][0] == pipeline_constant.TWIN_PATCHES

        mqtt_pipeline.enable_feature.reset_mock()

        # Verify twin patches are not enabled if already enabled
        mqtt_pipeline.feature_enabled.__getitem__.return_value = (
            True  # twin patches will appear enabled
        )
        await client.receive_twin_desired_properties_patch()
        assert mqtt_pipeline.enable_feature.call_count == 0

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

    @pytest.mark.it("Locks the client to API Receive Mode if the receive mode has not yet been set")
    async def test_receive_mode_not_set(self, mocker, client):
        # patch this so API won't block
        mocker.patch.object(
            AsyncClientInbox, "get", return_value=(await create_completed_future(None))
        )

        assert client._receive_type is RECEIVE_TYPE_NONE_SET
        await client.receive_twin_desired_properties_patch()
        assert client._receive_type is RECEIVE_TYPE_API

    @pytest.mark.it(
        "Does not modify the client receive mode if it has already been set to API Receive Mode"
    )
    async def test_receive_mode_set_api(self, mocker, client):
        # patch this so API won't block
        mocker.patch.object(
            AsyncClientInbox, "get", return_value=(await create_completed_future(None))
        )

        client._receive_type = RECEIVE_TYPE_API
        await client.receive_twin_desired_properties_patch()
        assert client._receive_type is RECEIVE_TYPE_API

    @pytest.mark.it(
        "Raises a ClientError and does nothing else if the client receive mode has been set to Handler Receive Mode"
    )
    async def test_receive_mode_set_handler(self, mocker, client, mqtt_pipeline):
        # patch this so API won't block
        inbox_get_mock = mocker.patch.object(
            AsyncClientInbox, "get", return_value=(await create_completed_future(None))
        )
        # patch this so we can make sure feature enabled isn't modified
        mqtt_pipeline.feature_enabled.__getitem__.return_value = False

        client._receive_type = RECEIVE_TYPE_HANDLER
        # Error was raised
        with pytest.raises(client_exceptions.ClientError):
            await client.receive_twin_desired_properties_patch()
        # Feature was not enabled
        assert mqtt_pipeline.enable_feature.call_count == 0
        # Inbox get was not called
        assert inbox_get_mock.call_count == 0


# ################
# # DEVICE TESTS #
# ################
class IoTHubDeviceClientTestsConfig(object):
    @pytest.fixture
    def client_class(self):
        return IoTHubDeviceClient

    @pytest.fixture
    async def client(self, mqtt_pipeline, http_pipeline):
        """This client automatically resolves callbacks sent to the pipeline.
        It should be used for the majority of tests.
        """
        client = IoTHubDeviceClient(mqtt_pipeline, http_pipeline)
        yield client
        await client.shutdown()

    @pytest.fixture
    def connection_string(self, device_connection_string):
        """This fixture is parametrized to prove all valid device connection strings.
        See client_fixtures.py
        """
        return device_connection_string

    @pytest.fixture
    def sas_token_string(self, device_sas_token_string):
        return device_sas_token_string


@pytest.mark.describe("IoTHubDeviceClient (Asynchronous) - Instantiation")
class TestIoTHubDeviceClientInstantiation(
    IoTHubDeviceClientTestsConfig, SharedIoTHubClientInstantiationTests
):
    @pytest.mark.it("Sets on_c2d_message_received handler in the MQTTPipeline")
    async def test_sets_on_c2d_message_received_handler_in_pipeline(
        self, client_class, mqtt_pipeline, http_pipeline
    ):
        client = client_class(mqtt_pipeline, http_pipeline)

        assert client._mqtt_pipeline.on_c2d_message_received is not None
        assert (
            client._mqtt_pipeline.on_c2d_message_received == client._inbox_manager.route_c2d_message
        )


@pytest.mark.describe("IoTHubDeviceClient (Asynchronous) - .create_from_connection_string()")
class TestIoTHubDeviceClientCreateFromConnectionString(
    IoTHubDeviceClientTestsConfig, SharedIoTHubClientCreateFromConnectionStringTests
):
    pass


@pytest.mark.describe("IoTHubDeviceClient (Synchronous) - .create_from_sastoken()")
class TestIoTHubDeviceClientCreateFromSastoken(
    IoTHubDeviceClientTestsConfig, SharedIoTHubDeviceClientCreateFromSastokenTests
):
    pass


@pytest.mark.describe("IoTHubDeviceClient (Asynchronous) - .create_from_symmetric_key()")
class TestConfigurationCreateIoTHubDeviceClientFromSymmetricKey(
    IoTHubDeviceClientTestsConfig, SharedIoTHubDeviceClientCreateFromSymmetricKeyTests
):
    pass


@pytest.mark.describe("IoTHubDeviceClient (Asynchronous) - .create_from_x509_certificate()")
class TestIoTHubDeviceClientCreateFromX509Certificate(
    IoTHubDeviceClientTestsConfig, SharedIoTHubDeviceClientCreateFromX509CertificateTests
):
    pass


@pytest.mark.describe("IoTHubDeviceClient (Asynchronous) - .shutdown()")
class TestIoTHubDeviceClientShutdown(IoTHubDeviceClientTestsConfig, SharedClientShutdownTests):
    @pytest.fixture
    def client(self, mqtt_pipeline, http_pipeline):
        """Override the client so that it doesn't shutdown during cleanup.
        Shutdown can only be done once, and it is under test, so shutting down again during cleanup
        will fail.
        """
        return IoTHubDeviceClient(mqtt_pipeline, http_pipeline)


@pytest.mark.describe("IoTHubDeviceClient (Asynchronous) - .update_sastoken()")
class TestIoTHubDeviceClientUpdateSasToken(
    IoTHubDeviceClientTestsConfig, SharedClientUpdateSasTokenTests
):
    @pytest.fixture
    def sas_config(self, sas_token_string):
        """PipelineConfig set up as if using user-provided, non-renewable SAS auth"""
        sastoken = st.NonRenewableSasToken(sas_token_string)
        token_uri_pieces = sastoken.resource_uri.split("/")
        hostname = token_uri_pieces[0]
        device_id = token_uri_pieces[2]
        sas_config = IoTHubPipelineConfig(hostname=hostname, device_id=device_id, sastoken=sastoken)
        return sas_config

    @pytest.fixture
    def uri(self, hostname, device_id):
        return "{hostname}/devices/{device_id}".format(hostname=hostname, device_id=device_id)

    @pytest.fixture(params=["Nonmatching Device ID", "Nonmatching Hostname"])
    def nonmatching_uri(self, request, device_id, hostname):
        # NOTE: It would be preferable to have this as a parametrization on a test rather than a
        # fixture, however, we need to use the device_id and hostname fixtures in order to ensure
        # tests don't break when other fixtures change, and you can't include fixtures in a
        # parametrization, so this also has to be a fixture
        uri_format = "{hostname}/devices/{device_id}"
        if request.param == "Nonmatching Device ID":
            return uri_format.format(hostname=hostname, device_id="nonmatching_device")
        else:
            return uri_format.format(hostname="nonmatching_hostname", device_id=device_id)

    @pytest.fixture(
        params=["Too short", "Too long", "Incorrectly formatted device notation", "Module URI"]
    )
    def invalid_uri(self, request, device_id, hostname):
        # NOTE: As in the nonmatching_uri fixture above, this is a workaround for parametrization
        # that allows the usage of other fixtures in the parametrized value. Weird pattern, but
        # necessary to ensure stability of the tests over time.
        if request.param == "Too short":
            # Doesn't have device ID
            return hostname + "/devices"
        elif request.param == "Too long":
            # Extraneous value at the end
            return "{}/devices/{}/somethingElse".format(hostname, device_id)
        elif request.param == "Incorrectly formatted device notation":
            # Doesn't have '/devices/'
            return "{}/not-devices/{}".format(hostname, device_id)
        else:
            # Valid... for a Module... but this is a Device
            return "{}/devices/{}/modules/my_module".format(hostname, device_id)


@pytest.mark.describe("IoTHubDeviceClient (Asynchronous) - .connect()")
class TestIoTHubDeviceClientConnect(IoTHubDeviceClientTestsConfig, SharedClientConnectTests):
    pass


@pytest.mark.describe("IoTHubDeviceClient (Asynchronous) - .disconnect()")
class TestIoTHubDeviceClientDisconnect(IoTHubDeviceClientTestsConfig, SharedClientDisconnectTests):
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
        self, mocker, client, mqtt_pipeline
    ):
        # patch this receive_message won't block
        mocker.patch.object(
            AsyncClientInbox, "get", return_value=(await create_completed_future(None))
        )

        # Verify C2D Messaging enabled if not enabled
        mqtt_pipeline.feature_enabled.__getitem__.return_value = False  # C2D will appear disabled
        await client.receive_message()
        assert mqtt_pipeline.enable_feature.call_count == 1
        assert mqtt_pipeline.enable_feature.call_args[0][0] == pipeline_constant.C2D_MSG

        mqtt_pipeline.enable_feature.reset_mock()

        # Verify C2D Messaging not enabled if already enabled
        mqtt_pipeline.feature_enabled.__getitem__.return_value = True  # C2D will appear enabled
        await client.receive_message()
        assert mqtt_pipeline.enable_feature.call_count == 0

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

    @pytest.mark.it("Locks the client to API Receive Mode if the receive mode has not yet been set")
    async def test_receive_mode_not_set(self, mocker, client):
        # patch this so API won't block
        mocker.patch.object(
            AsyncClientInbox, "get", return_value=(await create_completed_future(None))
        )

        assert client._receive_type is RECEIVE_TYPE_NONE_SET
        await client.receive_message()
        assert client._receive_type is RECEIVE_TYPE_API

    @pytest.mark.it(
        "Does not modify the client receive mode if it has already been set to API Receive Mode"
    )
    async def test_receive_mode_set_api(self, mocker, client):
        # patch this so API won't block
        mocker.patch.object(
            AsyncClientInbox, "get", return_value=(await create_completed_future(None))
        )

        client._receive_type = RECEIVE_TYPE_API
        await client.receive_message()
        assert client._receive_type is RECEIVE_TYPE_API

    @pytest.mark.it(
        "Raises a ClientError and does nothing else if the client receive mode has been set to Handler Receive Mode"
    )
    async def test_receive_mode_set_handler(self, mocker, client, mqtt_pipeline):
        # patch this so API won't block
        inbox_get_mock = mocker.patch.object(
            AsyncClientInbox, "get", return_value=(await create_completed_future(None))
        )
        # patch this so we can make sure feature enabled isn't modified
        mqtt_pipeline.feature_enabled.__getitem__.return_value = False

        client._receive_type = RECEIVE_TYPE_HANDLER
        # Error was raised
        with pytest.raises(client_exceptions.ClientError):
            await client.receive_message()
        # Feature was not enabled
        assert mqtt_pipeline.enable_feature.call_count == 0
        # Inbox get was not called
        assert inbox_get_mock.call_count == 0


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


@pytest.mark.describe("IoTHubDeviceClient (Asynchronous) - .get_storage_info_for_blob()")
class TestIoTHubDeviceClientGetStorageInfo(IoTHubDeviceClientTestsConfig):
    @pytest.mark.it("Begins a 'get_storage_info_for_blob' HTTPPipeline operation")
    async def test_calls_pipeline_get_storage_info_for_blob(self, client, http_pipeline):
        fake_blob_name = "__fake_blob_name__"
        await client.get_storage_info_for_blob(fake_blob_name)
        assert http_pipeline.get_storage_info_for_blob.call_count == 1
        assert http_pipeline.get_storage_info_for_blob.call_args[1]["blob_name"] is fake_blob_name

    @pytest.mark.it(
        "Waits for the completion of the 'get_storage_info_for_blob' pipeline operation before returning"
    )
    async def test_waits_for_pipeline_op_completion(self, mocker, client, http_pipeline):
        fake_blob_name = "__fake_blob_name__"
        cb_mock = mocker.patch.object(async_adapter, "AwaitableCallback").return_value
        cb_mock.completion.return_value = await create_completed_future(None)

        await client.get_storage_info_for_blob(fake_blob_name)

        # Assert callback is sent to pipeline
        assert http_pipeline.get_storage_info_for_blob.call_args[1]["callback"] is cb_mock
        # Assert callback completion is waited upon
        assert cb_mock.completion.call_count == 1

    @pytest.mark.it(
        "Raises a client error if the `get_storage_info_for_blob` pipeline operation calls back with a pipeline error"
    )
    @pytest.mark.parametrize(
        "pipeline_error,client_error",
        [
            pytest.param(
                pipeline_exceptions.ProtocolClientError,
                client_exceptions.ClientError,
                id="ProtocolClientError->ClientError",
            ),
            pytest.param(
                pipeline_exceptions.OperationCancelled,
                client_exceptions.OperationCancelled,
                id="OperationCancelled -> OperationCancelled",
            ),
            pytest.param(Exception, client_exceptions.ClientError, id="Exception->ClientError"),
        ],
    )
    async def test_raises_error_on_pipeline_op_error(
        self, mocker, client, http_pipeline, pipeline_error, client_error
    ):
        fake_blob_name = "__fake_blob_name__"

        my_pipeline_error = pipeline_error()

        def fail_get_storage_info_for_blob(blob_name, callback):
            callback(error=my_pipeline_error)

        http_pipeline.get_storage_info_for_blob = mocker.MagicMock(
            side_effect=fail_get_storage_info_for_blob
        )

        with pytest.raises(client_error) as e_info:
            await client.get_storage_info_for_blob(fake_blob_name)
        assert e_info.value.__cause__ is my_pipeline_error

    @pytest.mark.it("Returns a storage_info object upon successful completion")
    async def test_returns_storage_info(self, mocker, client, http_pipeline):
        fake_blob_name = "__fake_blob_name__"
        fake_storage_info = "__fake_storage_info__"
        received_storage_info = await client.get_storage_info_for_blob(fake_blob_name)
        assert http_pipeline.get_storage_info_for_blob.call_count == 1
        assert http_pipeline.get_storage_info_for_blob.call_args[1]["blob_name"] is fake_blob_name

        assert (
            received_storage_info is fake_storage_info
        )  # Note: the return value this is checking for is defined in client_fixtures.py


@pytest.mark.describe("IoTHubDeviceClient (Asynchronous) -.notify_blob_upload_status()")
class TestIoTHubDeviceClientNotifyBlobUploadStatus(IoTHubDeviceClientTestsConfig):
    @pytest.mark.it("Begins a 'notify_blob_upload_status' HTTPPipeline operation")
    async def test_calls_pipeline_notify_blob_upload_status(self, client, http_pipeline):
        correlation_id = "__fake_correlation_id__"
        is_success = "__fake_is_success__"
        status_code = "__fake_status_code__"
        status_description = "__fake_status_description__"
        await client.notify_blob_upload_status(
            correlation_id, is_success, status_code, status_description
        )
        kwargs = http_pipeline.notify_blob_upload_status.call_args[1]
        assert http_pipeline.notify_blob_upload_status.call_count == 1
        assert kwargs["correlation_id"] is correlation_id
        assert kwargs["is_success"] is is_success
        assert kwargs["status_code"] is status_code
        assert kwargs["status_description"] is status_description

    @pytest.mark.it(
        "Waits for the completion of the 'notify_blob_upload_status' pipeline operation before returning"
    )
    async def test_waits_for_pipeline_op_completion(self, mocker, client, http_pipeline):
        correlation_id = "__fake_correlation_id__"
        is_success = "__fake_is_success__"
        status_code = "__fake_status_code__"
        status_description = "__fake_status_description__"
        cb_mock = mocker.patch.object(async_adapter, "AwaitableCallback").return_value
        cb_mock.completion.return_value = await create_completed_future(None)
        await client.notify_blob_upload_status(
            correlation_id, is_success, status_code, status_description
        )

        # Assert callback is sent to pipeline
        assert http_pipeline.notify_blob_upload_status.call_args[1]["callback"] is cb_mock
        # Assert callback completion is waited upon
        assert cb_mock.completion.call_count == 1

    @pytest.mark.it(
        "Raises a client error if the `notify_blob_upload_status` pipeline operation calls back with a pipeline error"
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
        self, mocker, client, http_pipeline, pipeline_error, client_error
    ):
        correlation_id = "__fake_correlation_id__"
        is_success = "__fake_is_success__"
        status_code = "__fake_status_code__"
        status_description = "__fake_status_description__"
        my_pipeline_error = pipeline_error()

        def fail_notify_blob_upload_status(
            correlation_id, is_success, status_code, status_description, callback
        ):
            callback(error=my_pipeline_error)

        http_pipeline.notify_blob_upload_status = mocker.MagicMock(
            side_effect=fail_notify_blob_upload_status
        )

        with pytest.raises(client_error) as e_info:
            await client.notify_blob_upload_status(
                correlation_id, is_success, status_code, status_description
            )
            assert e_info.value.__cause__ is my_pipeline_error


@pytest.mark.describe("IoTHubDeviceClient (Asynchronous) - PROPERTY .on_message_received")
class TestIoTHubDeviceClientPROPERTYOnMessageReceivedHandler(
    IoTHubDeviceClientTestsConfig, SharedIoTHubClientPROPERTYReceiverHandlerTests
):
    @pytest.fixture
    def handler_name(self):
        return "on_message_received"

    @pytest.fixture
    def feature_name(self):
        return pipeline_constant.C2D_MSG


@pytest.mark.describe("IoTHubDeviceClient (Asynchronous) - PROPERTY .on_method_request_received")
class TestIoTHubDeviceClientPROPERTYOnMethodRequestReceivedHandler(
    IoTHubDeviceClientTestsConfig, SharedIoTHubClientPROPERTYReceiverHandlerTests
):
    @pytest.fixture
    def handler_name(self):
        return "on_method_request_received"

    @pytest.fixture
    def feature_name(self):
        return pipeline_constant.METHODS


@pytest.mark.describe(
    "IoTHubDeviceClient (Asynchronous) - PROPERTY .on_twin_desired_properties_patch_received"
)
class TestIoTHubDeviceClientPROPERTYOnTwinDesiredPropertiesPatchReceivedHandler(
    IoTHubDeviceClientTestsConfig, SharedIoTHubClientPROPERTYReceiverHandlerTests
):
    @pytest.fixture
    def handler_name(self):
        return "on_twin_desired_properties_patch_received"

    @pytest.fixture
    def feature_name(self):
        return pipeline_constant.TWIN_PATCHES


@pytest.mark.describe("IoTHubDeviceClient (Asynchronous) - PROPERTY .on_connection_state_change")
class TestIoTHubDeviceClientPROPERTYOnConnectionStateChangeHandler(
    IoTHubDeviceClientTestsConfig, SharedIoTHubClientPROPERTYHandlerTests
):
    @pytest.fixture
    def handler_name(self):
        return "on_connection_state_change"


@pytest.mark.describe("IoTHubDeviceClient (Asynchronous) - PROPERTY .on_new_sastoken_required")
class TestIoTHubDeviceClientPROPERTYOnNewSastokenRequiredHandler(
    IoTHubDeviceClientTestsConfig, SharedIoTHubClientPROPERTYHandlerTests
):
    @pytest.fixture
    def handler_name(self):
        return "on_new_sastoken_required"


@pytest.mark.describe("IoTHubDeviceClient (Asynchronous) - PROPERTY .on_background_exception")
class TestIoTHubDeviceClientPROPERTYOnBackgroundExceptionHandler(
    IoTHubDeviceClientTestsConfig, SharedIoTHubClientPROPERTYHandlerTests
):
    @pytest.fixture
    def handler_name(self):
        return "on_background_exception"


@pytest.mark.describe("IoTHubDeviceClient (Asynchronous) - PROPERTY .connected")
class TestIoTHubDeviceClientPROPERTYConnected(
    IoTHubDeviceClientTestsConfig, SharedIoTHubClientPROPERTYConnectedTests
):
    pass


@pytest.mark.describe("IoTHubDeviceClient (Asynchronous) - OCCURRENCE: Connect")
class TestIoTHubDeviceClientOCCURRENCEConnect(
    IoTHubDeviceClientTestsConfig, SharedIoTHubClientOCCURRENCEConnectTests
):
    pass


@pytest.mark.describe("IoTHubDeviceClient (Asynchronous) - OCCURRENCE: Disconnect")
class TestIoTHubDeviceClientOCCURRENCEDisconnect(
    IoTHubDeviceClientTestsConfig, SharedIoTHubClientOCCURRENCEDisconnectTests
):
    pass


@pytest.mark.describe("IoTHubDeviceClient (Synchronous) - OCCURRENCE: New Sastoken Required")
class TestIoTHubDeviceClientOCCURRENCENewSastokenRequired(
    IoTHubDeviceClientTestsConfig, SharedIoTHubClientOCCURRENCENewSastokenRequired
):
    pass


@pytest.mark.describe("IoTHubDeviceClient (Asynchronous) - OCCURRENCE: Background Exception")
class TestIoTHubDeviceClientOCCURRENCEBackgroundException(
    IoTHubDeviceClientTestsConfig, SharedIoTHubClientOCCURRENCEBackgroundException
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
    async def client(self, mqtt_pipeline, http_pipeline):
        """This client automatically resolves callbacks sent to the pipeline.
        It should be used for the majority of tests.
        """
        client = IoTHubModuleClient(mqtt_pipeline, http_pipeline)
        yield client
        await client.shutdown()

    @pytest.fixture
    def connection_string(self, module_connection_string):
        """This fixture is parametrized to prove all valid device connection strings.
        See client_fixtures.py
        """
        return module_connection_string

    @pytest.fixture
    def sas_token_string(self, module_sas_token_string):
        return module_sas_token_string


@pytest.mark.describe("IoTHubModuleClient (Asynchronous) - Instantiation")
class TestIoTHubModuleClientInstantiation(
    IoTHubModuleClientTestsConfig, SharedIoTHubClientInstantiationTests
):
    @pytest.mark.it("Sets on_input_message_received handler in the MQTTPipeline")
    async def test_sets_on_input_message_received_handler_in_pipeline(
        self, client_class, mqtt_pipeline, http_pipeline
    ):
        client = client_class(mqtt_pipeline, http_pipeline)

        assert client._mqtt_pipeline.on_input_message_received is not None
        assert (
            client._mqtt_pipeline.on_input_message_received
            == client._inbox_manager.route_input_message
        )


@pytest.mark.describe("IoTHubModuleClient (Asynchronous) - .create_from_connection_string()")
class TestIoTHubModuleClientCreateFromConnectionString(
    IoTHubModuleClientTestsConfig, SharedIoTHubClientCreateFromConnectionStringTests
):
    pass


@pytest.mark.describe("IoTHubModuleClient (Asynchronous) - .create_from_sastoken()")
class TestIoTHubModuleClientCreateFromSastoken(
    IoTHubModuleClientTestsConfig, SharedIoTHubModuleClientCreateFromSastokenTests
):
    pass


@pytest.mark.describe(
    "IoTHubModuleClient (Asynchronous) - .create_from_edge_environment() -- Edge Container Environment"
)
class TestIoTHubModuleClientCreateFromEdgeEnvironmentWithContainerEnv(
    IoTHubModuleClientTestsConfig,
    SharedIoTHubModuleClientCreateFromEdgeEnvironmentWithContainerEnvTests,
):
    pass


@pytest.mark.describe(
    "IoTHubModuleClient (Asynchronous) - .create_from_edge_environment() -- Edge Local Debug Environment"
)
class TestIoTHubModuleClientCreateFromEdgeEnvironmentWithDebugEnv(
    IoTHubModuleClientTestsConfig,
    SharedIoTHubModuleClientCreateFromEdgeEnvironmentWithDebugEnvTests,
):
    pass


@pytest.mark.describe("IoTHubModuleClient (Asynchronous) - .create_from_x509_certificate()")
class TestIoTHubModuleClientCreateFromX509Certificate(
    IoTHubModuleClientTestsConfig, SharedIoTHubModuleClientCreateFromX509CertificateTests
):
    pass


@pytest.mark.describe("IoTHubModuleClient (Asynchronous) - .shutdown()")
class TestIoTHubModuleClientShutdown(IoTHubModuleClientTestsConfig, SharedClientShutdownTests):
    @pytest.fixture
    def client(self, mqtt_pipeline, http_pipeline):
        """Override the client so that it doesn't shutdown during cleanup.
        Shutdown can only be done once, and it is under test, so shutting down again during cleanup
        will fail.
        """
        return IoTHubModuleClient(mqtt_pipeline, http_pipeline)


@pytest.mark.describe("IoTHubModuleClient (Asynchronous) - .update_sastoken()")
class TestIoTHubModuleClientUpdateSasToken(
    IoTHubModuleClientTestsConfig, SharedClientUpdateSasTokenTests
):
    @pytest.fixture
    def module_id(self, sas_token_string):
        # NOTE: This is kind of unconventional, but this is the easiest way to extract the
        # module id from a sastoken string
        sastoken = st.NonRenewableSasToken(sas_token_string)
        token_uri_pieces = sastoken.resource_uri.split("/")
        module_id = token_uri_pieces[4]
        return module_id

    @pytest.fixture
    def uri(self, hostname, device_id, module_id):
        return "{hostname}/devices/{device_id}/modules/{module_id}".format(
            hostname=hostname, device_id=device_id, module_id=module_id
        )

    @pytest.fixture(
        params=["Nonmatching Device ID", "Nonmatching Module ID", "Nonmatching Hostname"]
    )
    def nonmatching_uri(self, request, device_id, module_id, hostname):
        # NOTE: It would be preferable to have this as a parametrization on a test rather than a
        # fixture, however, we need to use the device_id and hostname fixtures in order to ensure
        # tests don't break when other fixtures change, and you can't include fixtures in a
        # parametrization, so this also has to be a fixture
        uri_format = "{hostname}/devices/{device_id}/modules/{module_id}"
        if request.param == "Nonmatching Device ID":
            return uri_format.format(
                hostname=hostname, device_id="nonmatching_device", module_id=module_id
            )
        elif request.param == "Nonmatching Module ID":
            return uri_format.format(
                hostname=hostname, device_id=device_id, module_id="nonmatching_module"
            )
        else:
            return uri_format.format(
                hostname="nonmatching_hostname", device_id=device_id, module_id=module_id
            )

    @pytest.fixture(
        params=[
            "Too short",
            "Too long",
            "Incorrectly formatted device notation",
            "Incorrectly formatted module notation",
            "Device URI",
        ]
    )
    def invalid_uri(self, request, device_id, module_id, hostname):
        # NOTE: As in the nonmatching_uri fixture above, this is a workaround for parametrization
        # that allows the usage of other fixtures in the parametrized value. Weird pattern, but
        # necessary to ensure stability of the tests over time.
        if request.param == "Too short":
            # Doesn't have module ID
            return "{}/devices/{}/modules".format(hostname, device_id)
        elif request.param == "Too long":
            # Extraneous value at the end
            return "{}/devices/{}/modules/{}/somethingElse".format(hostname, device_id, module_id)
        elif request.param == "Incorrectly formatted device notation":
            # Doesn't have '/devices/'
            return "{}/not-devices/{}/modules/{}".format(hostname, device_id, module_id)
        elif request.param == "Incorrectly formatted module notation":
            # Doesn't have '/modules/'
            return "{}/devices/{}/not-modules/{}".format(hostname, device_id, module_id)
        else:
            # Valid... for a Device... but this is a Module
            return "{}/devices/{}/".format(hostname, device_id)

    @pytest.fixture
    def sas_config(self, sas_token_string):
        """PipelineConfig set up as if using user-provided, non-renewable SAS auth"""
        sastoken = st.NonRenewableSasToken(sas_token_string)
        token_uri_pieces = sastoken.resource_uri.split("/")
        hostname = token_uri_pieces[0]
        device_id = token_uri_pieces[2]
        module_id = token_uri_pieces[4]
        sas_config = IoTHubPipelineConfig(
            hostname=hostname, device_id=device_id, module_id=module_id, sastoken=sastoken
        )
        return sas_config


@pytest.mark.describe("IoTHubModuleClient (Asynchronous) - .connect()")
class TestIoTHubModuleClientConnect(IoTHubModuleClientTestsConfig, SharedClientConnectTests):
    pass


@pytest.mark.describe("IoTHubModuleClient (Asynchronous) - .disconnect()")
class TestIoTHubModuleClientDisconnect(IoTHubModuleClientTestsConfig, SharedClientDisconnectTests):
    pass


@pytest.mark.describe("IoTHubModuleClient (Asynchronous) - .send_message()")
class TestIoTHubNModuleClientSendD2CMessage(
    IoTHubModuleClientTestsConfig, SharedClientSendD2CMessageTests
):
    pass


@pytest.mark.describe("IoTHubModuleClient (Asynchronous) - .send_message_to_output()")
class TestIoTHubModuleClientSendToOutput(IoTHubModuleClientTestsConfig):
    @pytest.mark.it("Begins a 'send_output_message' pipeline operation")
    async def test_calls_pipeline_send_message_to_output(self, client, mqtt_pipeline, message):
        output_name = "some_output"
        await client.send_message_to_output(message, output_name)
        assert mqtt_pipeline.send_output_message.call_count == 1
        assert mqtt_pipeline.send_output_message.call_args[0][0] is message
        assert message.output_name == output_name

    @pytest.mark.it(
        "Waits for the completion of the 'send_output_message' pipeline operation before returning"
    )
    async def test_waits_for_pipeline_op_completion(self, mocker, client, mqtt_pipeline, message):
        cb_mock = mocker.patch.object(async_adapter, "AwaitableCallback").return_value
        cb_mock.completion.return_value = await create_completed_future(None)

        output_name = "some_output"
        await client.send_message_to_output(message, output_name)

        # Assert callback is sent to pipeline
        assert mqtt_pipeline.send_output_message.call_args[1]["callback"] is cb_mock
        # Assert callback completion is waited upon
        assert cb_mock.completion.call_count == 1

    @pytest.mark.it(
        "Raises a client error if the `send_output_message` pipeline operation calls back with a pipeline error"
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
                pipeline_exceptions.NoConnectionError,
                client_exceptions.NoConnectionError,
                id="NoConnectionError->NoConnectionError",
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
            pytest.param(
                pipeline_exceptions.OperationCancelled,
                client_exceptions.OperationCancelled,
                id="OperationCancelled -> OperationCancelled",
            ),
            pytest.param(
                pipeline_exceptions.OperationTimeout,
                client_exceptions.OperationTimeout,
                id="OperationTimeout -> OperationTimeout",
            ),
            pytest.param(Exception, client_exceptions.ClientError, id="Exception->ClientError"),
        ],
    )
    async def test_raises_error_on_pipeline_op_error(
        self, mocker, client, mqtt_pipeline, message, pipeline_error, client_error
    ):
        my_pipeline_error = pipeline_error()

        def fail_send_output_message(message, callback):
            callback(error=my_pipeline_error)

        mqtt_pipeline.send_output_message = mocker.MagicMock(side_effect=fail_send_output_message)
        with pytest.raises(client_error) as e_info:
            output_name = "some_output"
            await client.send_message_to_output(message, output_name)
        assert e_info.value.__cause__ is my_pipeline_error
        assert mqtt_pipeline.send_output_message.call_count == 1

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
        self, client, mqtt_pipeline, message_input
    ):
        output_name = "some_output"
        await client.send_message_to_output(message_input, output_name)
        assert mqtt_pipeline.send_output_message.call_count == 1
        sent_message = mqtt_pipeline.send_output_message.call_args[0][0]
        assert isinstance(sent_message, Message)
        assert sent_message.data == message_input

    @pytest.mark.it("Raises error when message data size is greater than 256 KB")
    async def test_raises_error_when_message_to_output_data_greater_than_256(
        self, client, mqtt_pipeline
    ):
        output_name = "some_output"
        data_input = "serpensortia" * 256000
        message = Message(data_input)
        with pytest.raises(ValueError) as e_info:
            await client.send_message_to_output(message, output_name)
        assert "256 KB" in e_info.value.args[0]
        assert mqtt_pipeline.send_output_message.call_count == 0

    @pytest.mark.it("Raises error when message size is greater than 256 KB")
    async def test_raises_error_when_message_to_output_size_greater_than_256(
        self, client, mqtt_pipeline
    ):
        output_name = "some_output"
        data_input = "serpensortia"
        message = Message(data_input)
        message.custom_properties["spell"] = data_input * 256000
        with pytest.raises(ValueError) as e_info:
            await client.send_message_to_output(message, output_name)
        assert "256 KB" in e_info.value.args[0]
        assert mqtt_pipeline.send_output_message.call_count == 0

    @pytest.mark.skipif(
        sys.version_info >= (3, 12),
        reason="Python 3.12 appears to have an issue. Investigate further.",
    )
    @pytest.mark.it("Does not raises error when message data size is equal to 256 KB")
    async def test_raises_error_when_message_to_output_data_equal_to_256(
        self, client, mqtt_pipeline
    ):
        output_name = "some_output"
        data_input = "a" * 262095
        message = Message(data_input)
        # This check was put as message class may undergo the default content type encoding change
        # and the above calculation will change.
        if message.get_size() != device_constant.TELEMETRY_MESSAGE_SIZE_LIMIT:
            assert False

        await client.send_message_to_output(message, output_name)

        assert mqtt_pipeline.send_output_message.call_count == 1
        sent_message = mqtt_pipeline.send_output_message.call_args[0][0]
        assert isinstance(sent_message, Message)
        assert sent_message.data == data_input


@pytest.mark.describe("IoTHubModuleClient (Asynchronous) - .receive_message_on_input()")
class TestIoTHubModuleClientReceiveInputMessage(IoTHubModuleClientTestsConfig):
    @pytest.mark.it("Implicitly enables input messaging feature if not already enabled")
    async def test_enables_input_messaging_only_if_not_already_enabled(
        self, mocker, client, mqtt_pipeline
    ):
        # patch this receive_message_on_input won't block
        mocker.patch.object(
            AsyncClientInbox, "get", return_value=(await create_completed_future(None))
        )
        input_name = "some_input"

        # Verify Input Messaging enabled if not enabled
        mqtt_pipeline.feature_enabled.__getitem__.return_value = (
            False  # Input Messages will appear disabled
        )
        await client.receive_message_on_input(input_name)
        assert mqtt_pipeline.enable_feature.call_count == 1
        assert mqtt_pipeline.enable_feature.call_args[0][0] == pipeline_constant.INPUT_MSG

        mqtt_pipeline.enable_feature.reset_mock()

        # Verify Input Messaging not enabled if already enabled
        mqtt_pipeline.feature_enabled.__getitem__.return_value = (
            True  # Input Messages will appear enabled
        )
        await client.receive_message_on_input(input_name)
        assert mqtt_pipeline.enable_feature.call_count == 0

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

    @pytest.mark.it("Locks the client to API Receive Mode if the receive mode has not yet been set")
    async def test_receive_mode_not_set(self, mocker, client):
        # patch this so API won't block
        mocker.patch.object(
            AsyncClientInbox, "get", return_value=(await create_completed_future(None))
        )

        assert client._receive_type is RECEIVE_TYPE_NONE_SET
        await client.receive_message_on_input("some_input")
        assert client._receive_type is RECEIVE_TYPE_API

    @pytest.mark.it(
        "Does not modify the client receive mode if it has already been set to API Receive Mode"
    )
    async def test_receive_mode_set_api(self, mocker, client):
        # patch this so API won't block
        mocker.patch.object(
            AsyncClientInbox, "get", return_value=(await create_completed_future(None))
        )

        client._receive_type = RECEIVE_TYPE_API
        await client.receive_message_on_input("some_input")
        assert client._receive_type is RECEIVE_TYPE_API

    @pytest.mark.it(
        "Raises a ClientError and does nothing else if the client receive mode has been set to Handler Receive Mode"
    )
    async def test_receive_mode_set_handler(self, mocker, client, mqtt_pipeline):
        # patch this so API won't block
        inbox_get_mock = mocker.patch.object(
            AsyncClientInbox, "get", return_value=(await create_completed_future(None))
        )
        # patch this so we can make sure feature enabled isn't modified
        mqtt_pipeline.feature_enabled.__getitem__.return_value = False

        client._receive_type = RECEIVE_TYPE_HANDLER
        # Error was raised
        with pytest.raises(client_exceptions.ClientError):
            await client.receive_message_on_input("some_input")
        # Feature was not enabled
        assert mqtt_pipeline.enable_feature.call_count == 0
        # Inbox get was not called
        assert inbox_get_mock.call_count == 0


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


@pytest.mark.describe("IoTHubModuleClient (Synchronous) -.invoke_method()")
class TestIoTHubModuleClientInvokeMethod(IoTHubModuleClientTestsConfig):
    @pytest.mark.it("Begins a 'invoke_method' HTTPPipeline operation where the target is a device")
    async def test_calls_pipeline_invoke_method_for_device(self, mocker, client, http_pipeline):
        method_params = {"methodName": "__fake_method_name__"}
        device_id = "__fake_device_id__"
        await client.invoke_method(method_params, device_id)
        assert http_pipeline.invoke_method.call_count == 1
        assert http_pipeline.invoke_method.call_args == mocker.call(
            device_id, method_params, callback=mocker.ANY, module_id=None
        )

    @pytest.mark.it("Begins a 'invoke_method' HTTPPipeline operation where the target is a module")
    async def test_calls_pipeline_invoke_method_for_module(self, mocker, client, http_pipeline):
        method_params = {"methodName": "__fake_method_name__"}
        device_id = "__fake_device_id__"
        module_id = "__fake_module_id__"
        await client.invoke_method(method_params, device_id, module_id=module_id)
        assert http_pipeline.invoke_method.call_count == 1
        # assert http_pipeline.invoke_method.call_args[0][0] is device_id
        # assert http_pipeline.invoke_method.call_args[0][1] is method_params
        assert http_pipeline.invoke_method.call_args == mocker.call(
            device_id, method_params, callback=mocker.ANY, module_id=module_id
        )

    @pytest.mark.it(
        "Waits for the completion of the 'invoke_method' pipeline operation before returning"
    )
    async def test_waits_for_pipeline_op_completion(self, mocker, client, http_pipeline):
        method_params = {"methodName": "__fake_method_name__"}
        device_id = "__fake_device_id__"
        module_id = "__fake_module_id__"
        cb_mock = mocker.patch.object(async_adapter, "AwaitableCallback").return_value
        cb_mock.completion.return_value = await create_completed_future(None)

        await client.invoke_method(method_params, device_id, module_id=module_id)

        # Assert callback is sent to pipeline
        assert http_pipeline.invoke_method.call_args[1]["callback"] is cb_mock
        # Assert callback completion is waited upon
        assert cb_mock.completion.call_count == 1

    @pytest.mark.it(
        "Raises a client error if the `invoke_method` pipeline operation calls back with a pipeline error"
    )
    @pytest.mark.parametrize(
        "pipeline_error,client_error",
        [
            pytest.param(
                pipeline_exceptions.ProtocolClientError,
                client_exceptions.ClientError,
                id="ProtocolClientError->ClientError",
            ),
            pytest.param(
                pipeline_exceptions.OperationCancelled,
                client_exceptions.OperationCancelled,
                id="OperationCancelled -> OperationCancelled",
            ),
            pytest.param(Exception, client_exceptions.ClientError, id="Exception->ClientError"),
        ],
    )
    async def test_raises_error_on_pipeline_op_error(
        self, mocker, client, http_pipeline, pipeline_error, client_error
    ):
        method_params = {"methodName": "__fake_method_name__"}
        device_id = "__fake_device_id__"
        module_id = "__fake_module_id__"
        my_pipeline_error = pipeline_error()

        def fail_invoke_method(method_params, device_id, callback, module_id=None):
            return callback(error=my_pipeline_error)

        http_pipeline.invoke_method = mocker.MagicMock(side_effect=fail_invoke_method)

        with pytest.raises(client_error) as e_info:
            await client.invoke_method(method_params, device_id, module_id=module_id)

        assert e_info.value.__cause__ is my_pipeline_error


@pytest.mark.describe("IoTHubModuleClient (Asynchronous) - PROPERTY .on_message_received")
class TestIoTHubModuleClientPROPERTYOnMessageReceivedHandler(
    IoTHubModuleClientTestsConfig, SharedIoTHubClientPROPERTYReceiverHandlerTests
):
    @pytest.fixture
    def handler_name(self):
        return "on_message_received"

    @pytest.fixture
    def feature_name(self):
        return pipeline_constant.INPUT_MSG


@pytest.mark.describe("IoTHubModuleClient (Asynchronous) - PROPERTY .on_method_request_received")
class TestIoTHubModuleClientPROPERTYOnMethodRequestReceivedHandler(
    IoTHubModuleClientTestsConfig, SharedIoTHubClientPROPERTYReceiverHandlerTests
):
    @pytest.fixture
    def handler_name(self):
        return "on_method_request_received"

    @pytest.fixture
    def feature_name(self):
        return pipeline_constant.METHODS


@pytest.mark.describe(
    "IoTHubModuleClient (Asynchronous) - PROPERTY .on_twin_desired_properties_patch_received"
)
class TestIoTHubModuleClientPROPERTYOnTwinDesiredPropertiesPatchReceivedHandler(
    IoTHubModuleClientTestsConfig, SharedIoTHubClientPROPERTYReceiverHandlerTests
):
    @pytest.fixture
    def handler_name(self):
        return "on_twin_desired_properties_patch_received"

    @pytest.fixture
    def feature_name(self):
        return pipeline_constant.TWIN_PATCHES


@pytest.mark.describe("IoTHubModuleClient (Asynchronous) - PROPERTY .on_connection_state_change")
class TestIoTHubModuleClientPROPERTYOnConnectionStateChangeHandler(
    IoTHubModuleClientTestsConfig, SharedIoTHubClientPROPERTYHandlerTests
):
    @pytest.fixture
    def handler_name(self):
        return "on_connection_state_change"


@pytest.mark.describe("IoTHubModuleClient (Asynchronous) - PROPERTY .on_new_sastoken_required")
class TestIoTHubModuleClientPROPERTYOnNewSastokenRequiredHandler(
    IoTHubModuleClientTestsConfig, SharedIoTHubClientPROPERTYHandlerTests
):
    @pytest.fixture
    def handler_name(self):
        return "on_new_sastoken_required"


@pytest.mark.describe("IoTHubModuleClient (Asynchronous) - PROPERTY .on_background_exception")
class TestIoTHubModuleClientPROPERTYOnBackgroundExceptionHandler(
    IoTHubModuleClientTestsConfig, SharedIoTHubClientPROPERTYHandlerTests
):
    @pytest.fixture
    def handler_name(self):
        return "on_background_exception"


@pytest.mark.describe("IoTHubModule (Asynchronous) - PROPERTY .connected")
class TestIoTHubModuleClientPROPERTYConnected(
    IoTHubModuleClientTestsConfig, SharedIoTHubClientPROPERTYConnectedTests
):
    pass


@pytest.mark.describe("IoTHubModuleClient (Asynchronous) - OCCURRENCE: Connect")
class TestIoTHubModuleClientOCCURRENCEConnect(
    IoTHubModuleClientTestsConfig, SharedIoTHubClientOCCURRENCEConnectTests
):
    pass


@pytest.mark.describe("IoTHubModuleClient (Asynchronous) - OCCURRENCE: Disconnect")
class TestIoTHubModuleClientOCCURRENCEDisconnect(
    IoTHubModuleClientTestsConfig, SharedIoTHubClientOCCURRENCEDisconnectTests
):
    pass


@pytest.mark.describe("IoTHubModuleClient (Asynchronous) - OCCURRENCE: New Sastoken Required")
class TestIoTHubModuleClientOCCURRENCENewSastokenRequired(
    IoTHubModuleClientTestsConfig, SharedIoTHubClientOCCURRENCENewSastokenRequired
):
    pass


@pytest.mark.describe("IoTHubModuleClient (Asynchronous) - OCCURRENCE: Background Exception")
class TestIoTHubModuleClientOCCURRENCEBackgroundException(
    IoTHubModuleClientTestsConfig, SharedIoTHubClientOCCURRENCEBackgroundException
):
    pass
