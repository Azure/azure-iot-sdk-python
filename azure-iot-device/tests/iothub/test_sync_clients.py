# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
import logging
import threading
import time
import os
import io
import six
from azure.iot.device.iothub import IoTHubDeviceClient, IoTHubModuleClient
from azure.iot.device import exceptions as client_exceptions
from azure.iot.device.iothub.pipeline import IoTHubPipeline, constant
from azure.iot.device.iothub.pipeline import exceptions as pipeline_exceptions
from azure.iot.device.iothub.models import Message, MethodRequest
from azure.iot.device.iothub.sync_inbox import SyncClientInbox
from azure.iot.device.iothub.auth import IoTEdgeError
import azure.iot.device.iothub.sync_clients as sync_clients


logging.basicConfig(level=logging.DEBUG)


# automatically mock the pipeline for all tests in this file.
@pytest.fixture(autouse=True)
def mock_pipeline_init(mocker):
    return mocker.patch("azure.iot.device.iothub.pipeline.IoTHubPipeline")


################
# SHARED TESTS #
################
class SharedClientInstantiationTests(object):
    @pytest.mark.it(
        "Stores the IoTHubPipeline from the 'iothub_pipeline' parameter in the '_iothub_pipeline' attribute"
    )
    def test_iothub_pipeline_attribute(self, client_class, iothub_pipeline):
        client = client_class(iothub_pipeline)

        assert client._iothub_pipeline is iothub_pipeline

    @pytest.mark.it("Sets on_connected handler in the IoTHubPipeline")
    def test_sets_on_connected_handler_in_pipeline(self, client_class, iothub_pipeline):
        client = client_class(iothub_pipeline)

        assert client._iothub_pipeline.on_connected is not None
        assert client._iothub_pipeline.on_connected == client._on_connected

    @pytest.mark.it("Sets on_disconnected handler in the IoTHubPipeline")
    def test_sets_on_disconnected_handler_in_pipeline(self, client_class, iothub_pipeline):
        client = client_class(iothub_pipeline)

        assert client._iothub_pipeline.on_disconnected is not None
        assert client._iothub_pipeline.on_disconnected == client._on_disconnected

    @pytest.mark.it("Sets on_method_request_received handler in the IoTHubPipeline")
    def test_sets_on_method_request_received_handler_in_pipleline(
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
    def test_auth_provider_creation(self, mocker, client_class, connection_string, ca_cert):
        mock_auth_parse = mocker.patch(
            "azure.iot.device.iothub.auth.SymmetricKeyAuthenticationProvider"
        ).parse

        args = (connection_string,)
        kwargs = {}
        if ca_cert:
            kwargs["ca_cert"] = ca_cert
        client_class.create_from_connection_string(*args, **kwargs)

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
    def test_pipeline_creation(
        self, mocker, client_class, connection_string, ca_cert, mock_pipeline_init
    ):
        mock_auth = mocker.patch(
            "azure.iot.device.iothub.auth.SymmetricKeyAuthenticationProvider"
        ).parse.return_value

        args = (connection_string,)
        kwargs = {}
        if ca_cert:
            kwargs["ca_cert"] = ca_cert
        client_class.create_from_connection_string(*args, **kwargs)

        assert mock_pipeline_init.call_count == 1
        assert mock_pipeline_init.call_args == mocker.call(mock_auth)

    @pytest.mark.it("Uses the IoTHubPipeline to instantiate the client")
    @pytest.mark.parametrize(
        "ca_cert",
        [
            pytest.param(None, id="No CA certificate"),
            pytest.param("some-certificate", id="With CA certificate"),
        ],
    )
    def test_client_instantiation(self, mocker, client_class, connection_string, ca_cert):
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
    def test_returns_client(self, client_class, connection_string, ca_cert):
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
    def test_raises_value_error_on_bad_connection_string(self, client_class, bad_cs):
        with pytest.raises(ValueError):
            client_class.create_from_connection_string(bad_cs)


class SharedClientCreateFromSharedAccessSignature(object):
    @pytest.mark.it("Uses the SAS token to create a SharedAccessSignatureAuthenticationProvider")
    def test_auth_provider_creation(self, mocker, client_class, sas_token_string):
        mock_auth_parse = mocker.patch(
            "azure.iot.device.iothub.auth.SharedAccessSignatureAuthenticationProvider"
        ).parse

        client_class.create_from_shared_access_signature(sas_token_string)

        assert mock_auth_parse.call_count == 1
        assert mock_auth_parse.call_args == mocker.call(sas_token_string)

    @pytest.mark.it(
        "Uses the SharedAccessSignatureAuthenticationProvider to create an IoTHubPipeline"
    )
    def test_pipeline_creation(self, mocker, client_class, sas_token_string, mock_pipeline_init):
        mock_auth = mocker.patch(
            "azure.iot.device.iothub.auth.SharedAccessSignatureAuthenticationProvider"
        ).parse.return_value

        client_class.create_from_shared_access_signature(sas_token_string)

        assert mock_pipeline_init.call_count == 1
        assert mock_pipeline_init.call_args == mocker.call(mock_auth)

    @pytest.mark.it("Uses the IoTHubPipeline to instantiate the client")
    def test_client_instantiation(self, mocker, client_class, sas_token_string):
        mock_pipeline = mocker.patch("azure.iot.device.iothub.pipeline.IoTHubPipeline").return_value
        spy_init = mocker.spy(client_class, "__init__")

        client_class.create_from_shared_access_signature(sas_token_string)

        assert spy_init.call_count == 1
        assert spy_init.call_args == mocker.call(mocker.ANY, mock_pipeline)

    @pytest.mark.it("Returns the instantiated client")
    def test_returns_client(self, mocker, client_class, sas_token_string):
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
    def test_raises_value_error_on_bad_sas_token(self, client_class, bad_sas):
        with pytest.raises(ValueError):
            client_class.create_from_shared_access_signature(bad_sas)


class WaitsForEventCompletion(object):
    def add_event_completion_checks(self, mocker, pipeline_function, args=[], kwargs={}):
        event_init_mock = mocker.patch.object(threading, "Event")
        event_mock = event_init_mock.return_value

        def check_callback_completes_event():
            # Assert exactly one Event was instantiated so we know the following asserts
            # are related to the code under test ONLY
            assert event_init_mock.call_count == 1

            # Assert waiting for Event to complete
            assert event_mock.wait.call_count == 1
            assert event_mock.set.call_count == 0

            # Manually trigger callback
            cb = pipeline_function.call_args[1]["callback"]
            cb(*args, **kwargs)

            # Assert Event is now completed
            assert event_mock.set.call_count == 1

        event_mock.wait.side_effect = check_callback_completes_event


class SharedClientConnectTests(WaitsForEventCompletion):
    @pytest.mark.it("Begins a 'connect' pipeline operation")
    def test_calls_pipeline_connect(self, client, iothub_pipeline):
        client.connect()
        assert iothub_pipeline.connect.call_count == 1

    @pytest.mark.it("Waits for the completion of the 'connect' pipeline operation before returning")
    def test_waits_for_pipeline_op_completion(
        self, mocker, client_manual_cb, iothub_pipeline_manual_cb
    ):
        self.add_event_completion_checks(
            mocker=mocker, pipeline_function=iothub_pipeline_manual_cb.connect
        )
        client_manual_cb.connect()

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
    def test_raises_error_on_pipeline_op_error(
        self, mocker, client_manual_cb, iothub_pipeline_manual_cb, pipeline_error, client_error
    ):
        my_pipeline_error = pipeline_error()
        self.add_event_completion_checks(
            mocker=mocker,
            pipeline_function=iothub_pipeline_manual_cb.connect,
            kwargs={"error": my_pipeline_error},
        )
        with pytest.raises(client_error) as e_info:
            client_manual_cb.connect()
        assert e_info.value.__cause__ is my_pipeline_error


class SharedClientDisconnectTests(WaitsForEventCompletion):
    @pytest.mark.it("Begins a 'disconnect' pipeline operation")
    def test_calls_pipeline_disconnect(self, client, iothub_pipeline):
        client.disconnect()
        assert iothub_pipeline.disconnect.call_count == 1

    @pytest.mark.it(
        "Waits for the completion of the 'disconnect' pipeline operation before returning"
    )
    def test_waits_for_pipeline_op_completion(
        self, mocker, client_manual_cb, iothub_pipeline_manual_cb
    ):
        self.add_event_completion_checks(
            mocker=mocker, pipeline_function=iothub_pipeline_manual_cb.disconnect
        )
        client_manual_cb.disconnect()

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
    def test_raises_error_on_pipeline_op_error(
        self, mocker, client_manual_cb, iothub_pipeline_manual_cb, pipeline_error, client_error
    ):
        my_pipeline_error = pipeline_error()
        self.add_event_completion_checks(
            mocker=mocker,
            pipeline_function=iothub_pipeline_manual_cb.disconnect,
            kwargs={"error": my_pipeline_error},
        )
        with pytest.raises(client_error) as e_info:
            client_manual_cb.disconnect()
        assert e_info.value.__cause__ is my_pipeline_error


class SharedClientDisconnectEventTests(object):
    @pytest.mark.it("Clears all pending MethodRequests upon disconnect")
    def test_state_change_handler_clears_method_request_inboxes_on_disconnect(self, client, mocker):
        clear_method_request_spy = mocker.spy(client._inbox_manager, "clear_all_method_requests")
        client._on_disconnected()
        assert clear_method_request_spy.call_count == 1


class SharedClientSendD2CMessageTests(WaitsForEventCompletion):
    @pytest.mark.it("Begins a 'send_message' IoTHubPipeline operation")
    def test_calls_pipeline_send_message(self, client, iothub_pipeline, message):
        client.send_message(message)
        assert iothub_pipeline.send_message.call_count == 1
        assert iothub_pipeline.send_message.call_args[0][0] is message

    @pytest.mark.it(
        "Waits for the completion of the 'send_message' pipeline operation before returning"
    )
    def test_waits_for_pipeline_op_completion(
        self, mocker, client_manual_cb, iothub_pipeline_manual_cb, message
    ):
        self.add_event_completion_checks(
            mocker=mocker, pipeline_function=iothub_pipeline_manual_cb.send_message
        )
        client_manual_cb.send_message(message)

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
    def test_raises_error_on_pipeline_op_error(
        self,
        mocker,
        client_manual_cb,
        iothub_pipeline_manual_cb,
        message,
        pipeline_error,
        client_error,
    ):
        my_pipeline_error = pipeline_error()
        self.add_event_completion_checks(
            mocker=mocker,
            pipeline_function=iothub_pipeline_manual_cb.send_message,
            kwargs={"error": my_pipeline_error},
        )
        with pytest.raises(client_error) as e_info:
            client_manual_cb.send_message(message)
        assert e_info.value.__cause__ is my_pipeline_error

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
    def test_wraps_data_in_message_and_calls_pipeline_send_message(
        self, client, iothub_pipeline, message_input
    ):
        client.send_message(message_input)
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
    def test_enables_methods_only_if_not_already_enabled(
        self, mocker, client, iothub_pipeline, method_name
    ):
        mocker.patch.object(SyncClientInbox, "get")  # patch this receive_method_request won't block

        # Verify Input Messaging enabled if not enabled
        iothub_pipeline.feature_enabled.__getitem__.return_value = (
            False
        )  # Method Requests will appear disabled
        client.receive_method_request(method_name)
        assert iothub_pipeline.enable_feature.call_count == 1
        assert iothub_pipeline.enable_feature.call_args[0][0] == constant.METHODS

        iothub_pipeline.enable_feature.reset_mock()

        # Verify Input Messaging not enabled if already enabled
        iothub_pipeline.feature_enabled.__getitem__.return_value = (
            True
        )  # Input Messages will appear enabled
        client.receive_method_request(method_name)
        assert iothub_pipeline.enable_feature.call_count == 0

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
            time.sleep(0.01)
            inbox._put(request)

        insertion_thread = threading.Thread(target=insert_item_after_delay)
        insertion_thread.start()

        received_request = client.receive_method_request(method_name, block=True)
        assert received_request is request
        # This proves that the blocking happens because 'received_request' can't be
        # 'request' until after a 10 millisecond delay on the insert. But because the
        # 'received_request' IS 'request', it means that client.receive_method_request
        # did not return until after the delay.

    @pytest.mark.it(
        "Returns None after a timeout while blocking, in blocking mode with a specified timeout"
    )
    @pytest.mark.parametrize(
        "method_name",
        [pytest.param(None, id="Generic Method"), pytest.param("method_x", id="Named Method")],
    )
    def test_times_out_waiting_for_message_blocking_mode(self, client, method_name):
        result = client.receive_method_request(method_name, block=True, timeout=0.01)
        assert result is None

    @pytest.mark.it("Returns None immediately if there are no messages, in nonblocking mode")
    @pytest.mark.parametrize(
        "method_name",
        [pytest.param(None, id="Generic Method"), pytest.param("method_x", id="Named Method")],
    )
    def test_no_message_in_inbox_nonblocking_mode(self, client, method_name):
        result = client.receive_method_request(method_name, block=False)
        assert result is None


class SharedClientSendMethodResponseTests(WaitsForEventCompletion):
    @pytest.mark.it("Begins a 'send_method_response' pipeline operation")
    def test_send_method_response_calls_pipeline(self, client, iothub_pipeline, method_response):

        client.send_method_response(method_response)
        assert iothub_pipeline.send_method_response.call_count == 1
        assert iothub_pipeline.send_method_response.call_args[0][0] is method_response

    @pytest.mark.it(
        "Waits for the completion of the 'send_method_response' pipeline operation before returning"
    )
    def test_waits_for_pipeline_op_completion(
        self, mocker, client_manual_cb, iothub_pipeline_manual_cb, method_response
    ):
        self.add_event_completion_checks(
            mocker=mocker, pipeline_function=iothub_pipeline_manual_cb.send_method_response
        )
        client_manual_cb.send_method_response(method_response)

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
    def test_raises_error_on_pipeline_op_error(
        self,
        mocker,
        client_manual_cb,
        iothub_pipeline_manual_cb,
        method_response,
        pipeline_error,
        client_error,
    ):
        my_pipeline_error = pipeline_error()
        self.add_event_completion_checks(
            mocker=mocker,
            pipeline_function=iothub_pipeline_manual_cb.send_method_response,
            kwargs={"error": my_pipeline_error},
        )
        with pytest.raises(client_error) as e_info:
            client_manual_cb.send_method_response(method_response)
        assert e_info.value.__cause__ is my_pipeline_error


class SharedClientGetTwinTests(WaitsForEventCompletion):
    @pytest.fixture
    def patch_get_twin_to_return_fake_twin(self, fake_twin, mocker, iothub_pipeline):
        def immediate_callback(callback):
            callback(twin=fake_twin)

        mocker.patch.object(iothub_pipeline, "get_twin", side_effect=immediate_callback)

    @pytest.mark.it("Implicitly enables twin messaging feature if not already enabled")
    def test_enables_twin_only_if_not_already_enabled(
        self, mocker, client, iothub_pipeline, patch_get_twin_to_return_fake_twin, fake_twin
    ):
        # Verify twin enabled if not enabled
        iothub_pipeline.feature_enabled.__getitem__.return_value = (
            False
        )  # twin will appear disabled
        client.get_twin()
        assert iothub_pipeline.enable_feature.call_count == 1
        assert iothub_pipeline.enable_feature.call_args[0][0] == constant.TWIN

        iothub_pipeline.enable_feature.reset_mock()

        # Verify twin not enabled if already enabled
        iothub_pipeline.feature_enabled.__getitem__.return_value = True  # twin will appear enabled
        client.get_twin()
        assert iothub_pipeline.enable_feature.call_count == 0

    @pytest.mark.it("Begins a 'get_twin' pipeline operation")
    def test_get_twin_calls_pipeline(self, client, iothub_pipeline):
        client.get_twin()
        assert iothub_pipeline.get_twin.call_count == 1

    @pytest.mark.it(
        "Waits for the completion of the 'get_twin' pipeline operation before returning"
    )
    def test_waits_for_pipeline_op_completion(
        self, mocker, client_manual_cb, iothub_pipeline_manual_cb, fake_twin
    ):
        self.add_event_completion_checks(
            mocker=mocker,
            pipeline_function=iothub_pipeline_manual_cb.get_twin,
            kwargs={"twin": fake_twin},
        )
        client_manual_cb.get_twin()

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
    def test_raises_error_on_pipeline_op_error(
        self, mocker, client_manual_cb, iothub_pipeline_manual_cb, pipeline_error, client_error
    ):
        my_pipeline_error = pipeline_error()
        self.add_event_completion_checks(
            mocker=mocker,
            pipeline_function=iothub_pipeline_manual_cb.get_twin,
            kwargs={"error": my_pipeline_error},
        )
        with pytest.raises(client_error) as e_info:
            client_manual_cb.get_twin()
        assert e_info.value.__cause__ is my_pipeline_error

    @pytest.mark.it("Returns the twin that the pipeline returned")
    def test_verifies_twin_returned(
        self, mocker, client_manual_cb, iothub_pipeline_manual_cb, fake_twin
    ):
        self.add_event_completion_checks(
            mocker=mocker,
            pipeline_function=iothub_pipeline_manual_cb.get_twin,
            kwargs={"twin": fake_twin},
        )
        returned_twin = client_manual_cb.get_twin()
        assert returned_twin == fake_twin


class SharedClientPatchTwinReportedPropertiesTests(WaitsForEventCompletion):
    @pytest.mark.it("Implicitly enables twin messaging feature if not already enabled")
    def test_enables_twin_only_if_not_already_enabled(
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
        client.patch_twin_reported_properties(twin_patch_reported)
        assert iothub_pipeline.enable_feature.call_count == 1
        assert iothub_pipeline.enable_feature.call_args[0][0] == constant.TWIN

        iothub_pipeline.enable_feature.reset_mock()

        # Verify twin not enabled if already enabled
        iothub_pipeline.feature_enabled.__getitem__.return_value = True  # twin will appear enabled
        client.patch_twin_reported_properties(twin_patch_reported)
        assert iothub_pipeline.enable_feature.call_count == 0

    @pytest.mark.it("Begins a 'patch_twin_reported_properties' pipeline operation")
    def test_patch_twin_reported_properties_calls_pipeline(
        self, client, iothub_pipeline, twin_patch_reported
    ):
        client.patch_twin_reported_properties(twin_patch_reported)
        assert iothub_pipeline.patch_twin_reported_properties.call_count == 1
        assert (
            iothub_pipeline.patch_twin_reported_properties.call_args[1]["patch"]
            is twin_patch_reported
        )

    @pytest.mark.it(
        "Waits for the completion of the 'patch_twin_reported_properties' pipeline operation before returning"
    )
    def test_waits_for_pipeline_op_completion(
        self, mocker, client_manual_cb, iothub_pipeline_manual_cb, twin_patch_reported
    ):
        self.add_event_completion_checks(
            mocker=mocker,
            pipeline_function=iothub_pipeline_manual_cb.patch_twin_reported_properties,
        )
        client_manual_cb.patch_twin_reported_properties(twin_patch_reported)

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
    def test_raises_error_on_pipeline_op_error(
        self,
        mocker,
        client_manual_cb,
        iothub_pipeline_manual_cb,
        twin_patch_reported,
        pipeline_error,
        client_error,
    ):
        my_pipeline_error = pipeline_error()
        self.add_event_completion_checks(
            mocker=mocker,
            pipeline_function=iothub_pipeline_manual_cb.patch_twin_reported_properties,
            kwargs={"error": my_pipeline_error},
        )
        with pytest.raises(client_error) as e_info:
            client_manual_cb.patch_twin_reported_properties(twin_patch_reported)
        assert e_info.value.__cause__ is my_pipeline_error


class SharedClientReceiveTwinDesiredPropertiesPatchTests(object):
    @pytest.mark.it(
        "Implicitly enables Twin desired properties patch feature if not already enabled"
    )
    def test_enables_twin_patches_only_if_not_already_enabled(
        self, mocker, client, iothub_pipeline
    ):
        mocker.patch.object(
            SyncClientInbox, "get"
        )  # patch this so receive_twin_desired_properties_patch won't block

        # Verify twin patches enabled if not enabled
        iothub_pipeline.feature_enabled.__getitem__.return_value = (
            False
        )  # twin patches will appear disabled
        client.receive_twin_desired_properties_patch()
        assert iothub_pipeline.enable_feature.call_count == 1
        assert iothub_pipeline.enable_feature.call_args[0][0] == constant.TWIN_PATCHES

        iothub_pipeline.enable_feature.reset_mock()

        # Verify twin patches not enabled if already enabled
        iothub_pipeline.feature_enabled.__getitem__.return_value = True  # C2D will appear enabled
        client.receive_twin_desired_properties_patch()
        assert iothub_pipeline.enable_feature.call_count == 0

    @pytest.mark.it("Returns a patch from the twin patch inbox, if available")
    def test_returns_message_from_twin_patch_inbox(self, mocker, client, twin_patch_desired):
        inbox_mock = mocker.MagicMock(autospec=SyncClientInbox)
        inbox_mock.get.return_value = twin_patch_desired
        manager_get_inbox_mock = mocker.patch.object(
            client._inbox_manager, "get_twin_patch_inbox", return_value=inbox_mock
        )

        received_patch = client.receive_twin_desired_properties_patch()
        assert manager_get_inbox_mock.call_count == 1
        assert inbox_mock.get.call_count == 1
        assert received_patch is twin_patch_desired

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
        mocker.patch.object(client._inbox_manager, "get_twin_patch_inbox", return_value=inbox_mock)

        client.receive_twin_desired_properties_patch(block=block, timeout=timeout)
        assert inbox_mock.get.call_count == 1
        assert inbox_mock.get.call_args == mocker.call(block=block, timeout=timeout)

    @pytest.mark.it("Defaults to blocking mode with no timeout")
    def test_default_mode(self, mocker, client):
        inbox_mock = mocker.MagicMock(autospec=SyncClientInbox)
        mocker.patch.object(client._inbox_manager, "get_twin_patch_inbox", return_value=inbox_mock)

        client.receive_twin_desired_properties_patch()
        assert inbox_mock.get.call_count == 1
        assert inbox_mock.get.call_args == mocker.call(block=True, timeout=None)

    @pytest.mark.it("Blocks until a patch is available, in blocking mode")
    def test_no_message_in_inbox_blocking_mode(self, client, twin_patch_desired):

        twin_patch_inbox = client._inbox_manager.get_twin_patch_inbox()
        assert twin_patch_inbox.empty()

        def insert_item_after_delay():
            time.sleep(0.01)
            twin_patch_inbox._put(twin_patch_desired)

        insertion_thread = threading.Thread(target=insert_item_after_delay)
        insertion_thread.start()

        received_patch = client.receive_twin_desired_properties_patch(block=True)
        assert received_patch is twin_patch_desired
        # This proves that the blocking happens because 'received_patch' can't be
        # 'twin_patch_desired' until after a 10 millisecond delay on the insert. But because the
        # 'received_patch' IS 'twin_patch_desired', it means that client.receive_twin_desired_properties_patch
        # did not return until after the delay.

    @pytest.mark.it(
        "Returns None after a timeout while blocking, in blocking mode with a specified timeout"
    )
    def test_times_out_waiting_for_message_blocking_mode(self, client):
        result = client.receive_twin_desired_properties_patch(block=True, timeout=0.01)
        assert result is None

    @pytest.mark.it("Returns None immediately if there are no patches, in nonblocking mode")
    def test_no_message_in_inbox_nonblocking_mode(self, client):
        result = client.receive_twin_desired_properties_patch(block=False)
        assert result is None


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
    def client_manual_cb(self, iothub_pipeline_manual_cb):
        """This client requires manual triggering of the callbacks sent to the pipeline.
        It should only be used for tests where manual control fo a callback is required.
        """
        return IoTHubDeviceClient(iothub_pipeline_manual_cb)

    @pytest.fixture
    def connection_string(self, device_connection_string):
        """This fixture is parametrized to provie all valid device connection strings.
        See client_fixtures.py
        """
        return device_connection_string

    @pytest.fixture
    def sas_token_string(self, device_sas_token_string):
        return device_sas_token_string


@pytest.mark.describe("IoTHubDeviceClient (Synchronous) - Instantiation")
class TestIoTHubDeviceClientInstantiation(
    IoTHubDeviceClientTestsConfig, SharedClientInstantiationTests
):
    @pytest.mark.it("Sets on_c2d_message_received handler in the IoTHubPipeline")
    def test_sets_on_c2d_message_received_handler_in_pipeline(self, client_class, iothub_pipeline):
        client = client_class(iothub_pipeline)

        assert client._iothub_pipeline.on_c2d_message_received is not None
        assert (
            client._iothub_pipeline.on_c2d_message_received
            == client._inbox_manager.route_c2d_message
        )

    @pytest.mark.it("Sets the '_edge_pipeline' attribute to None")
    def test_edge_pipeline_is_none(self, client_class, iothub_pipeline):
        client = client_class(iothub_pipeline)

        assert client._edge_pipeline is None


@pytest.mark.describe("IoTHubDeviceClient (Synchronous) - .create_from_connection_string()")
class TestIoTHubDeviceClientCreateFromConnectionString(
    IoTHubDeviceClientTestsConfig, SharedClientCreateFromConnectionStringTests
):
    pass


@pytest.mark.describe("IoTHubDeviceClient (Synchronous) - .create_from_shared_access_signature()")
class TestIoTHubDeviceClientCreateFromSharedAccessSignature(
    IoTHubDeviceClientTestsConfig, SharedClientCreateFromSharedAccessSignature
):
    pass


@pytest.mark.describe("IoTHubDeviceClient (Synchronous) - .create_from_x509_certificate()")
class TestIoTHubDeviceClientCreateFromX509Certificate(IoTHubDeviceClientTestsConfig):
    hostname = "durmstranginstitute.farend"
    device_id = "MySnitch"

    @pytest.mark.it("Uses the provided arguments to create a X509AuthenticationProvider")
    def test_auth_provider_creation(self, mocker, client_class, x509):
        mock_auth_init = mocker.patch("azure.iot.device.iothub.auth.X509AuthenticationProvider")

        client_class.create_from_x509_certificate(
            x509=x509, hostname=self.hostname, device_id=self.device_id
        )

        assert mock_auth_init.call_count == 1
        assert mock_auth_init.call_args == mocker.call(
            x509=x509, hostname=self.hostname, device_id=self.device_id
        )

    @pytest.mark.it("Uses the X509AuthenticationProvider to create an IoTHubPipeline")
    def test_pipeline_creation(self, mocker, client_class, x509, mock_pipeline_init):
        mock_auth = mocker.patch(
            "azure.iot.device.iothub.auth.X509AuthenticationProvider"
        ).return_value

        client_class.create_from_x509_certificate(
            x509=x509, hostname=self.hostname, device_id=self.device_id
        )

        assert mock_pipeline_init.call_count == 1
        assert mock_pipeline_init.call_args == mocker.call(mock_auth)

    @pytest.mark.it("Uses the IoTHubPipeline to instantiate the client")
    def test_client_instantiation(self, mocker, client_class, x509):
        mock_pipeline = mocker.patch("azure.iot.device.iothub.pipeline.IoTHubPipeline").return_value
        spy_init = mocker.spy(client_class, "__init__")

        client_class.create_from_x509_certificate(
            x509=x509, hostname=self.hostname, device_id=self.device_id
        )

        assert spy_init.call_count == 1
        assert spy_init.call_args == mocker.call(mocker.ANY, mock_pipeline)

    @pytest.mark.it("Returns the instantiated client")
    def test_returns_client(self, mocker, client_class, x509):
        client = client_class.create_from_x509_certificate(
            x509=x509, hostname=self.hostname, device_id=self.device_id
        )

        assert isinstance(client, client_class)


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


@pytest.mark.describe("IoTHubDeviceClient (Synchronous) - .send_message()")
class TestIoTHubDeviceClientSendD2CMessage(
    IoTHubDeviceClientTestsConfig, SharedClientSendD2CMessageTests
):
    pass


@pytest.mark.describe("IoTHubDeviceClient (Synchronous) - .receive_message()")
class TestIoTHubDeviceClientReceiveC2DMessage(IoTHubDeviceClientTestsConfig):
    @pytest.mark.it("Implicitly enables C2D messaging feature if not already enabled")
    def test_enables_c2d_messaging_only_if_not_already_enabled(
        self, mocker, client, iothub_pipeline
    ):
        mocker.patch.object(SyncClientInbox, "get")  # patch this so receive_message won't block

        # Verify C2D Messaging enabled if not enabled
        iothub_pipeline.feature_enabled.__getitem__.return_value = False  # C2D will appear disabled
        client.receive_message()
        assert iothub_pipeline.enable_feature.call_count == 1
        assert iothub_pipeline.enable_feature.call_args[0][0] == constant.C2D_MSG

        iothub_pipeline.enable_feature.reset_mock()

        # Verify C2D Messaging not enabled if already enabled
        iothub_pipeline.feature_enabled.__getitem__.return_value = True  # C2D will appear enabled
        client.receive_message()
        assert iothub_pipeline.enable_feature.call_count == 0

    @pytest.mark.it("Returns a message from the C2D inbox, if available")
    def test_returns_message_from_c2d_inbox(self, mocker, client, message):
        inbox_mock = mocker.MagicMock(autospec=SyncClientInbox)
        inbox_mock.get.return_value = message
        manager_get_inbox_mock = mocker.patch.object(
            client._inbox_manager, "get_c2d_message_inbox", return_value=inbox_mock
        )

        received_message = client.receive_message()
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

        client.receive_message(block=block, timeout=timeout)
        assert inbox_mock.get.call_count == 1
        assert inbox_mock.get.call_args == mocker.call(block=block, timeout=timeout)

    @pytest.mark.it("Defaults to blocking mode with no timeout")
    def test_default_mode(self, mocker, client):
        inbox_mock = mocker.MagicMock(autospec=SyncClientInbox)
        mocker.patch.object(client._inbox_manager, "get_c2d_message_inbox", return_value=inbox_mock)

        client.receive_message()
        assert inbox_mock.get.call_count == 1
        assert inbox_mock.get.call_args == mocker.call(block=True, timeout=None)

    @pytest.mark.it("Blocks until a message is available, in blocking mode")
    def test_no_message_in_inbox_blocking_mode(self, client, message):
        c2d_inbox = client._inbox_manager.get_c2d_message_inbox()
        assert c2d_inbox.empty()

        def insert_item_after_delay():
            time.sleep(0.01)
            c2d_inbox._put(message)

        insertion_thread = threading.Thread(target=insert_item_after_delay)
        insertion_thread.start()

        received_message = client.receive_message(block=True)
        assert received_message is message
        # This proves that the blocking happens because 'received_message' can't be
        # 'message' until after a 10 millisecond delay on the insert. But because the
        # 'received_message' IS 'message', it means that client.receive_message
        # did not return until after the delay.

    @pytest.mark.it(
        "Returns None after a timeout while blocking, in blocking mode with a specified timeout"
    )
    def test_times_out_waiting_for_message_blocking_mode(self, client):
        result = client.receive_message(block=True, timeout=0.01)
        assert result is None

    @pytest.mark.it("Returns None immediately if there are no messages, in nonblocking mode")
    def test_no_message_in_inbox_nonblocking_mode(self, client):
        result = client.receive_message(block=False)
        assert result is None


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


@pytest.mark.describe("IoTHubDeviceClient (Synchronous) - .get_twin()")
class TestIoTHubDeviceClientGetTwin(IoTHubDeviceClientTestsConfig, SharedClientGetTwinTests):
    pass


@pytest.mark.describe("IoTHubDeviceClient (Synchronous) - .patch_twin_reported_properties()")
class TestIoTHubDeviceClientPatchTwinReportedProperties(
    IoTHubDeviceClientTestsConfig, SharedClientPatchTwinReportedPropertiesTests
):
    pass


@pytest.mark.describe("IoTHubDeviceClient (Synchronous) - .receive_twin_desired_properties_patch()")
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
    def client_manual_cb(self, iothub_pipeline_manual_cb):
        """This client requires manual triggering of the callbacks sent to the pipeline.
        It should only be used for tests where manual control fo a callback is required.
        """
        return IoTHubModuleClient(iothub_pipeline_manual_cb)

    @pytest.fixture
    def connection_string(self, module_connection_string):
        """This fixture is parametrized to provie all valid device connection strings.
        See client_fixtures.py
        """
        return module_connection_string

    @pytest.fixture
    def sas_token_string(self, module_sas_token_string):
        return module_sas_token_string


@pytest.mark.describe("IoTHubModuleClient (Synchronous) - Instantiation")
class TestIoTHubModuleClientInstantiation(
    IoTHubModuleClientTestsConfig, SharedClientInstantiationTests
):
    @pytest.mark.it("Sets on_input_message_received handler in the IoTHubPipeline")
    def test_sets_on_input_message_received_handler_in_pipeline(
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
    def test_sets_edge_pipeline_attribute(self, client_class, iothub_pipeline, edge_pipeline):
        client = client_class(iothub_pipeline, edge_pipeline)

        assert client._edge_pipeline is edge_pipeline

    @pytest.mark.it(
        "Sets the '_edge_pipeline' attribute to None, if the 'edge_pipeline' parameter is not provided"
    )
    def test_edge_pipeline_default_none(self, client_class, iothub_pipeline):
        client = client_class(iothub_pipeline)

        assert client._edge_pipeline is None


@pytest.mark.describe("IoTHubModuleClient (Synchronous) - .create_from_connection_string()")
class TestIoTHubModuleClientCreateFromConnectionString(
    IoTHubModuleClientTestsConfig, SharedClientCreateFromConnectionStringTests
):
    pass


@pytest.mark.describe("IoTHubModuleClient (Synchronous) - .create_from_shared_access_signature()")
class TestIoTHubModuleClientCreateFromSharedAccessSignature(
    IoTHubModuleClientTestsConfig, SharedClientCreateFromSharedAccessSignature
):
    pass


@pytest.mark.describe(
    "IoTHubModuleClient (Synchronous) - .create_from_edge_environment() -- Edge Container Environment"
)
class TestIoTHubModuleClientCreateFromEdgeEnvironmentWithContainerEnv(
    IoTHubModuleClientTestsConfig
):
    @pytest.mark.it(
        "Uses Edge container environment variables to create an IoTEdgeAuthenticationProvider"
    )
    def test_auth_provider_creation(self, mocker, client_class, edge_container_environment):
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
    def test_auth_provider_creation_hybrid_env(
        self, mocker, client_class, edge_container_environment, edge_local_debug_environment
    ):
        # This test verifies that with a hybrid environment, the auth provider will always be
        # an IoTEdgeAuthenticationProvider, even if local debug variables are present
        hybrid_environment = merge_dicts(edge_container_environment, edge_local_debug_environment)
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
    def test_pipeline_creation(self, mocker, client_class, edge_container_environment):
        mocker.patch.dict(os.environ, edge_container_environment)
        mock_auth = mocker.patch(
            "azure.iot.device.iothub.auth.IoTEdgeAuthenticationProvider"
        ).return_value
        mock_iothub_pipeline_init = mocker.patch("azure.iot.device.iothub.pipeline.IoTHubPipeline")
        mock_edge_pipeline_init = mocker.patch("azure.iot.device.iothub.pipeline.EdgePipeline")

        client_class.create_from_edge_environment()

        assert mock_iothub_pipeline_init.call_count == 1
        assert mock_iothub_pipeline_init.call_args == mocker.call(mock_auth)
        assert mock_edge_pipeline_init.call_count == 1
        assert mock_edge_pipeline_init.call_args == mocker.call(mock_auth)

    @pytest.mark.it("Uses the IoTHubPipeline and the EdgePipeline to instantiate the client")
    def test_client_instantiation(self, mocker, client_class, edge_container_environment):
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
    def test_returns_client(self, mocker, client_class, edge_container_environment):
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
    def test_bad_environment(
        self, mocker, client_class, edge_container_environment, missing_env_var
    ):
        # Remove a variable from the fixture
        del edge_container_environment[missing_env_var]
        mocker.patch.dict(os.environ, edge_container_environment)

        with pytest.raises(OSError):
            client_class.create_from_edge_environment()

    @pytest.mark.it("Raises OSError if there is an error using the Edge for authentication")
    def test_bad_edge_auth(self, mocker, client_class, edge_container_environment):
        mocker.patch.dict(os.environ, edge_container_environment)
        mock_auth = mocker.patch("azure.iot.device.iothub.auth.IoTEdgeAuthenticationProvider")
        my_edge_error = IoTEdgeError()
        mock_auth.side_effect = my_edge_error

        with pytest.raises(OSError) as e_info:
            client_class.create_from_edge_environment()
        assert e_info.value.__cause__ is my_edge_error


@pytest.mark.describe(
    "IoTHubModuleClient (Synchronous) - .create_from_edge_environment() -- Edge Local Debug Environment"
)
class TestIoTHubModuleClientCreateFromEdgeEnvironmentWithDebugEnv(IoTHubModuleClientTestsConfig):
    @pytest.fixture
    def mock_open(self, mocker):
        return mocker.patch.object(io, "open")

    @pytest.mark.it(
        "Extracts the CA certificate from the file indicated by the EdgeModuleCACertificateFile environment variable"
    )
    def test_read_ca_cert(self, mocker, client_class, edge_local_debug_environment, mock_open):
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
    def test_auth_provider_creation(
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
    def test_auth_provider_and_pipeline_hybrid_env(
        self,
        mocker,
        client_class,
        edge_container_environment,
        edge_local_debug_environment,
        mock_open,
    ):
        # This test verifies that with a hybrid environment, the auth provider will always be
        # an IoTEdgeAuthenticationProvider, even if local debug variables are present
        hybrid_environment = merge_dicts(edge_container_environment, edge_local_debug_environment)
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
    def test_pipeline_creation(self, mocker, client_class, edge_local_debug_environment, mock_open):
        mocker.patch.dict(os.environ, edge_local_debug_environment)
        mock_auth = mocker.patch(
            "azure.iot.device.iothub.auth.SymmetricKeyAuthenticationProvider"
        ).parse.return_value
        mock_iothub_pipeline_init = mocker.patch("azure.iot.device.iothub.pipeline.IoTHubPipeline")
        mock_edge_pipeline_init = mocker.patch("azure.iot.device.iothub.pipeline.EdgePipeline")

        client_class.create_from_edge_environment()

        assert mock_iothub_pipeline_init.call_count == 1
        assert mock_iothub_pipeline_init.call_args == mocker.call(mock_auth)
        assert mock_edge_pipeline_init.call_count == 1
        assert mock_iothub_pipeline_init.call_args == mocker.call(mock_auth)

    @pytest.mark.it("Uses the IoTHubPipeline and the EdgePipeline to instantiate the client")
    def test_client_instantiation(
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
    def test_returns_client(self, mocker, client_class, edge_local_debug_environment, mock_open):
        mocker.patch.dict(os.environ, edge_local_debug_environment)

        client = client_class.create_from_edge_environment()

        assert isinstance(client, client_class)

    @pytest.mark.it("Raises OSError if the environment is missing required variables")
    @pytest.mark.parametrize(
        "missing_env_var", ["EdgeHubConnectionString", "EdgeModuleCACertificateFile"]
    )
    def test_bad_environment(
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
        "Raises ValueError if the connection string in the EdgeHubConnectionString environment variable is invalid"
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
    def test_bad_connection_string(
        self, mocker, client_class, edge_local_debug_environment, bad_cs, mock_open
    ):
        edge_local_debug_environment["EdgeHubConnectionString"] = bad_cs
        mocker.patch.dict(os.environ, edge_local_debug_environment)

        with pytest.raises(ValueError):
            client_class.create_from_edge_environment()

    @pytest.mark.it(
        "Raises ValueError if the filepath in the EdgeModuleCACertificateFile environment variable is invalid"
    )
    def test_bad_filepath(self, mocker, client_class, edge_local_debug_environment, mock_open):
        # To make tests compatible with Python 2 & 3, redfine errors
        try:
            FileNotFoundError  # noqa: F823
        except NameError:
            FileNotFoundError = IOError

        mocker.patch.dict(os.environ, edge_local_debug_environment)
        my_fnf_error = FileNotFoundError()
        mock_open.side_effect = my_fnf_error
        with pytest.raises(ValueError) as e_info:
            client_class.create_from_edge_environment()
        assert e_info.value.__cause__ is my_fnf_error

    @pytest.mark.it(
        "Raises ValueError if the file referenced by the filepath in the EdgeModuleCACertificateFile environment variable cannot be opened"
    )
    def test_bad_file_io(self, mocker, client_class, edge_local_debug_environment, mock_open):
        # Raise a different error in Python 2 vs 3
        if six.PY2:
            error = IOError()
        else:
            error = OSError()
        mocker.patch.dict(os.environ, edge_local_debug_environment)
        mock_open.side_effect = error
        with pytest.raises(ValueError) as e_info:
            client_class.create_from_edge_environment()
        assert e_info.value.__cause__ is error


@pytest.mark.describe("IoTHubModuleClient (Synchronous) - .create_from_x509_certificate()")
class TestIoTHubModuleClientCreateFromX509Certificate(IoTHubModuleClientTestsConfig):
    hostname = "durmstranginstitute.farend"
    device_id = "MySnitch"
    module_id = "Charms"

    @pytest.mark.it("Uses the provided arguments to create a X509AuthenticationProvider")
    def test_auth_provider_creation(self, mocker, client_class, x509):
        mock_auth_init = mocker.patch("azure.iot.device.iothub.auth.X509AuthenticationProvider")

        client_class.create_from_x509_certificate(
            x509=x509, hostname=self.hostname, device_id=self.device_id, module_id=self.module_id
        )

        assert mock_auth_init.call_count == 1
        assert mock_auth_init.call_args == mocker.call(
            x509=x509, hostname=self.hostname, device_id=self.device_id, module_id=self.module_id
        )

    @pytest.mark.it("Uses the X509AuthenticationProvider to create an IoTHubPipeline")
    def test_pipeline_creation(self, mocker, client_class, x509, mock_pipeline_init):
        mock_auth = mocker.patch(
            "azure.iot.device.iothub.auth.X509AuthenticationProvider"
        ).return_value

        client_class.create_from_x509_certificate(
            x509=x509, hostname=self.hostname, device_id=self.device_id, module_id=self.module_id
        )

        assert mock_pipeline_init.call_count == 1
        assert mock_pipeline_init.call_args == mocker.call(mock_auth)

    @pytest.mark.it("Uses the IoTHubPipeline to instantiate the client")
    def test_client_instantiation(self, mocker, client_class, x509):
        mock_pipeline = mocker.patch("azure.iot.device.iothub.pipeline.IoTHubPipeline").return_value
        spy_init = mocker.spy(client_class, "__init__")

        client_class.create_from_x509_certificate(
            x509=x509, hostname=self.hostname, device_id=self.device_id, module_id=self.module_id
        )

        assert spy_init.call_count == 1
        assert spy_init.call_args == mocker.call(mocker.ANY, mock_pipeline)

    @pytest.mark.it("Returns the instantiated client")
    def test_returns_client(self, mocker, client_class, x509):
        client = client_class.create_from_x509_certificate(
            x509=x509, hostname=self.hostname, device_id=self.device_id, module_id=self.module_id
        )

        assert isinstance(client, client_class)


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


@pytest.mark.describe("IoTHubModuleClient (Synchronous) - .send_message()")
class TestIoTHubNModuleClientSendD2CMessage(
    IoTHubModuleClientTestsConfig, SharedClientSendD2CMessageTests
):
    pass


@pytest.mark.describe("IoTHubModuleClient (Synchronous) - .send_message_to_output()")
class TestIoTHubModuleClientSendToOutput(IoTHubModuleClientTestsConfig, WaitsForEventCompletion):
    @pytest.mark.it("Begins a 'send_output_event' pipeline operation")
    def test_calls_pipeline_send_message_to_output(self, client, iothub_pipeline, message):
        output_name = "some_output"
        client.send_message_to_output(message, output_name)
        assert iothub_pipeline.send_output_event.call_count == 1
        assert iothub_pipeline.send_output_event.call_args[0][0] is message
        assert message.output_name == output_name

    @pytest.mark.it(
        "Waits for the completion of the 'send_output_event' pipeline operation before returning"
    )
    def test_waits_for_pipeline_op_completion(
        self, mocker, client_manual_cb, iothub_pipeline_manual_cb, message
    ):
        self.add_event_completion_checks(
            mocker=mocker, pipeline_function=iothub_pipeline_manual_cb.send_output_event
        )
        output_name = "some_output"
        client_manual_cb.send_message_to_output(message, output_name)

    @pytest.mark.it(
        "Raises a client error if the `send_out_event` pipeline operation calls back with a pipeline error"
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
    def test_raises_error_on_pipeline_op_error(
        self,
        mocker,
        client_manual_cb,
        iothub_pipeline_manual_cb,
        message,
        pipeline_error,
        client_error,
    ):
        my_pipeline_error = pipeline_error()
        self.add_event_completion_checks(
            mocker=mocker,
            pipeline_function=iothub_pipeline_manual_cb.send_output_event,
            kwargs={"error": my_pipeline_error},
        )
        output_name = "some_output"
        with pytest.raises(client_error) as e_info:
            client_manual_cb.send_message_to_output(message, output_name)
        assert e_info.value.__cause__ is my_pipeline_error

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
    def test_send_message_to_output_calls_pipeline_wraps_data_in_message(
        self, client, iothub_pipeline, message_input
    ):
        output_name = "some_output"
        client.send_message_to_output(message_input, output_name)
        assert iothub_pipeline.send_output_event.call_count == 1
        sent_message = iothub_pipeline.send_output_event.call_args[0][0]
        assert isinstance(sent_message, Message)
        assert sent_message.data == message_input


@pytest.mark.describe("IoTHubModuleClient (Synchronous) - .receive_message_on_input()")
class TestIoTHubModuleClientReceiveInputMessage(IoTHubModuleClientTestsConfig):
    @pytest.mark.it("Implicitly enables input messaging feature if not already enabled")
    def test_enables_input_messaging_only_if_not_already_enabled(
        self, mocker, client, iothub_pipeline
    ):
        mocker.patch.object(
            SyncClientInbox, "get"
        )  # patch this receive_message_on_input won't block
        input_name = "some_input"

        # Verify Input Messaging enabled if not enabled
        iothub_pipeline.feature_enabled.__getitem__.return_value = (
            False
        )  # Input Messages will appear disabled
        client.receive_message_on_input(input_name)
        assert iothub_pipeline.enable_feature.call_count == 1
        assert iothub_pipeline.enable_feature.call_args[0][0] == constant.INPUT_MSG

        iothub_pipeline.enable_feature.reset_mock()

        # Verify Input Messaging not enabled if already enabled
        iothub_pipeline.feature_enabled.__getitem__.return_value = (
            True
        )  # Input Messages will appear enabled
        client.receive_message_on_input(input_name)
        assert iothub_pipeline.enable_feature.call_count == 0

    @pytest.mark.it("Returns a message from the input inbox, if available")
    def test_returns_message_from_input_inbox(self, mocker, client, message):
        inbox_mock = mocker.MagicMock(autospec=SyncClientInbox)
        inbox_mock.get.return_value = message
        manager_get_inbox_mock = mocker.patch.object(
            client._inbox_manager, "get_input_message_inbox", return_value=inbox_mock
        )

        input_name = "some_input"
        received_message = client.receive_message_on_input(input_name)
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
        client.receive_message_on_input(input_name, block=block, timeout=timeout)
        assert inbox_mock.get.call_count == 1
        assert inbox_mock.get.call_args == mocker.call(block=block, timeout=timeout)

    @pytest.mark.it("Defaults to blocking mode with no timeout")
    def test_default_mode(self, mocker, client):
        inbox_mock = mocker.MagicMock(autospec=SyncClientInbox)
        mocker.patch.object(
            client._inbox_manager, "get_input_message_inbox", return_value=inbox_mock
        )

        input_name = "some_input"
        client.receive_message_on_input(input_name)
        assert inbox_mock.get.call_count == 1
        assert inbox_mock.get.call_args == mocker.call(block=True, timeout=None)

    @pytest.mark.it("Blocks until a message is available, in blocking mode")
    def test_no_message_in_inbox_blocking_mode(self, client, message):
        input_name = "some_input"

        input_inbox = client._inbox_manager.get_input_message_inbox(input_name)
        assert input_inbox.empty()

        def insert_item_after_delay():
            time.sleep(0.01)
            input_inbox._put(message)

        insertion_thread = threading.Thread(target=insert_item_after_delay)
        insertion_thread.start()

        received_message = client.receive_message_on_input(input_name, block=True)
        assert received_message is message
        # This proves that the blocking happens because 'received_message' can't be
        # 'message' until after a 10 millisecond delay on the insert. But because the
        # 'received_message' IS 'message', it means that client.receive_message_on_input
        # did not return until after the delay.

    @pytest.mark.it(
        "Returns None after a timeout while blocking, in blocking mode with a specified timeout"
    )
    def test_times_out_waiting_for_message_blocking_mode(self, client):
        input_name = "some_input"
        result = client.receive_message_on_input(input_name, block=True, timeout=0.01)
        assert result is None

    @pytest.mark.it("Returns None immediately if there are no messages, in nonblocking mode")
    def test_no_message_in_inbox_nonblocking_mode(self, client):
        input_name = "some_input"
        result = client.receive_message_on_input(input_name, block=False)
        assert result is None


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


@pytest.mark.describe("IoTHubModuleClient (Synchronous) - .get_twin()")
class TestIoTHubModuleClientGetTwin(IoTHubModuleClientTestsConfig, SharedClientGetTwinTests):
    pass


@pytest.mark.describe("IoTHubModuleClient (Synchronous) - .patch_twin_reported_properties()")
class TestIoTHubModuleClientPatchTwinReportedProperties(
    IoTHubModuleClientTestsConfig, SharedClientPatchTwinReportedPropertiesTests
):
    pass


@pytest.mark.describe("IoTHubModuleClient (Synchronous) - .receive_twin_desired_properties_patch()")
class TestIoTHubModuleClientReceiveTwinDesiredPropertiesPatch(
    IoTHubModuleClientTestsConfig, SharedClientReceiveTwinDesiredPropertiesPatchTests
):
    pass


####################
# HELPER FUNCTIONS #
####################
def merge_dicts(d1, d2):
    d3 = d1.copy()
    d3.update(d2)
    return d3
