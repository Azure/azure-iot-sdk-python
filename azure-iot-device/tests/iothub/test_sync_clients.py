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
from azure.iot.device.iothub.pipeline import constant as pipeline_constant
from azure.iot.device.iothub.pipeline import exceptions as pipeline_exceptions
from azure.iot.device.iothub.models import Message, MethodRequest
from azure.iot.device.iothub.sync_inbox import SyncClientInbox
from azure.iot.device.iothub.abstract_clients import (
    RECEIVE_TYPE_NONE_SET,
    RECEIVE_TYPE_HANDLER,
    RECEIVE_TYPE_API,
)
from azure.iot.device import constant as device_constant
from .shared_client_tests import (
    SharedIoTHubClientInstantiationTests,
    SharedIoTHubClientPROPERTYHandlerTests,
    SharedIoTHubClientPROPERTYConnectedTests,
    SharedIoTHubClientCreateFromConnectionStringTests,
    SharedIoTHubDeviceClientCreateFromSymmetricKeyTests,
    SharedIoTHubDeviceClientCreateFromX509CertificateTests,
    SharedIoTHubModuleClientCreateFromX509CertificateTests,
    SharedIoTHubModuleClientCreateFromEdgeEnvironmentWithContainerEnvTests,
    SharedIoTHubModuleClientCreateFromEdgeEnvironmentWithDebugEnvTests,
)

logging.basicConfig(level=logging.DEBUG)


##################
# INFRASTRUCTURE #
##################
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


##########################
# SHARED CLIENT FIXTURES #
##########################
@pytest.fixture
def handler():
    def _handler_function(arg):
        pass

    return _handler_function


#######################
# SHARED CLIENT TESTS #
#######################
class SharedClientConnectTests(WaitsForEventCompletion):
    @pytest.mark.it("Begins a 'connect' pipeline operation")
    def test_calls_pipeline_connect(self, client, mqtt_pipeline):
        client.connect()
        assert mqtt_pipeline.connect.call_count == 1

    @pytest.mark.it("Waits for the completion of the 'connect' pipeline operation before returning")
    def test_waits_for_pipeline_op_completion(
        self, mocker, client_manual_cb, mqtt_pipeline_manual_cb
    ):
        self.add_event_completion_checks(
            mocker=mocker, pipeline_function=mqtt_pipeline_manual_cb.connect
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
            pytest.param(Exception, client_exceptions.ClientError, id="Exception->ClientError"),
        ],
    )
    def test_raises_error_on_pipeline_op_error(
        self, mocker, client_manual_cb, mqtt_pipeline_manual_cb, pipeline_error, client_error
    ):
        my_pipeline_error = pipeline_error()
        self.add_event_completion_checks(
            mocker=mocker,
            pipeline_function=mqtt_pipeline_manual_cb.connect,
            kwargs={"error": my_pipeline_error},
        )
        with pytest.raises(client_error) as e_info:
            client_manual_cb.connect()
        assert e_info.value.__cause__ is my_pipeline_error


class SharedClientDisconnectTests(WaitsForEventCompletion):
    @pytest.mark.it("Begins a 'disconnect' pipeline operation")
    def test_calls_pipeline_disconnect(self, client, mqtt_pipeline):
        client.disconnect()
        assert mqtt_pipeline.disconnect.call_count == 1

    @pytest.mark.it(
        "Waits for the completion of the 'disconnect' pipeline operation before returning"
    )
    def test_waits_for_pipeline_op_completion(
        self, mocker, client_manual_cb, mqtt_pipeline_manual_cb
    ):
        self.add_event_completion_checks(
            mocker=mocker, pipeline_function=mqtt_pipeline_manual_cb.disconnect
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
        self, mocker, client_manual_cb, mqtt_pipeline_manual_cb, pipeline_error, client_error
    ):
        my_pipeline_error = pipeline_error()
        self.add_event_completion_checks(
            mocker=mocker,
            pipeline_function=mqtt_pipeline_manual_cb.disconnect,
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
    @pytest.mark.it("Begins a 'send_message' MQTTPipeline operation")
    def test_calls_pipeline_send_message(self, client, mqtt_pipeline, message):
        client.send_message(message)
        assert mqtt_pipeline.send_message.call_count == 1
        assert mqtt_pipeline.send_message.call_args[0][0] is message

    @pytest.mark.it(
        "Waits for the completion of the 'send_message' pipeline operation before returning"
    )
    def test_waits_for_pipeline_op_completion(
        self, mocker, client_manual_cb, mqtt_pipeline_manual_cb, message
    ):
        self.add_event_completion_checks(
            mocker=mocker, pipeline_function=mqtt_pipeline_manual_cb.send_message
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
        mqtt_pipeline_manual_cb,
        message,
        pipeline_error,
        client_error,
    ):
        my_pipeline_error = pipeline_error()
        self.add_event_completion_checks(
            mocker=mocker,
            pipeline_function=mqtt_pipeline_manual_cb.send_message,
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
        self, client, mqtt_pipeline, message_input
    ):
        client.send_message(message_input)
        assert mqtt_pipeline.send_message.call_count == 1
        sent_message = mqtt_pipeline.send_message.call_args[0][0]
        assert isinstance(sent_message, Message)
        assert sent_message.data == message_input

    @pytest.mark.it("Raises error when message data size is greater than 256 KB")
    def test_raises_error_when_message_data_greater_than_256(self, client, mqtt_pipeline):
        data_input = "serpensortia" * 25600
        message = Message(data_input)
        with pytest.raises(ValueError) as e_info:
            client.send_message(message)
        assert "256 KB" in e_info.value.args[0]
        assert mqtt_pipeline.send_message.call_count == 0

    @pytest.mark.it("Raises error when message size is greater than 256 KB")
    def test_raises_error_when_message_size_greater_than_256(self, client, mqtt_pipeline):
        data_input = "serpensortia"
        message = Message(data_input)
        message.custom_properties["spell"] = data_input * 25600
        with pytest.raises(ValueError) as e_info:
            client.send_message(message)
        assert "256 KB" in e_info.value.args[0]
        assert mqtt_pipeline.send_message.call_count == 0

    @pytest.mark.it("Does not raises error when message data size is equal to 256 KB")
    def test_raises_error_when_message_data_equal_to_256(self, client, mqtt_pipeline):
        data_input = "a" * 262095
        message = Message(data_input)
        # This check was put as message class may undergo the default content type encoding change
        # and the above calculation will change.
        # Had to do greater than check for python 2. Ideally should be not equal check
        if message.get_size() > device_constant.TELEMETRY_MESSAGE_SIZE_LIMIT:
            assert False

        client.send_message(message)

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
    def test_enables_methods_only_if_not_already_enabled(
        self, mocker, client, mqtt_pipeline, method_name
    ):
        mocker.patch.object(SyncClientInbox, "get")  # patch this receive_method_request won't block

        # Verify Input Messaging enabled if not enabled
        mqtt_pipeline.feature_enabled.__getitem__.return_value = (
            False
        )  # Method Requests will appear disabled
        client.receive_method_request(method_name)
        assert mqtt_pipeline.enable_feature.call_count == 1
        assert mqtt_pipeline.enable_feature.call_args[0][0] == pipeline_constant.METHODS

        mqtt_pipeline.enable_feature.reset_mock()

        # Verify Input Messaging not enabled if already enabled
        mqtt_pipeline.feature_enabled.__getitem__.return_value = (
            True
        )  # Input Messages will appear enabled
        client.receive_method_request(method_name)
        assert mqtt_pipeline.enable_feature.call_count == 0

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

    @pytest.mark.it("Locks the client to API Receive Mode if the receive mode has not yet been set")
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
    def test_receive_mode_not_set(self, mocker, client, method_name, block, timeout):
        inbox_mock = mocker.MagicMock(autospec=SyncClientInbox)
        mocker.patch.object(
            client._inbox_manager, "get_method_request_inbox", return_value=inbox_mock
        )

        assert client._receive_type is RECEIVE_TYPE_NONE_SET
        client.receive_method_request(method_name=method_name, block=block, timeout=timeout)
        assert client._receive_type is RECEIVE_TYPE_API

    @pytest.mark.it(
        "Does not modify the client receive mode if it has already been set to API Receive Mode"
    )
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
    def test_receive_mode_set_api(self, mocker, client, method_name, block, timeout):
        inbox_mock = mocker.MagicMock(autospec=SyncClientInbox)
        mocker.patch.object(
            client._inbox_manager, "get_method_request_inbox", return_value=inbox_mock
        )

        client._receive_type = RECEIVE_TYPE_API
        client.receive_method_request(method_name=method_name, block=block, timeout=timeout)
        assert client._receive_type is RECEIVE_TYPE_API

    @pytest.mark.it(
        "Raises a ClientError and does nothing else if the client receive mode has been set to Handler Receive Mode"
    )
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
    def test_receive_mode_set_handler(
        self, mocker, client, mqtt_pipeline, method_name, block, timeout
    ):
        inbox_mock = mocker.MagicMock(autospec=SyncClientInbox)
        mocker.patch.object(
            client._inbox_manager, "get_method_request_inbox", return_value=inbox_mock
        )
        # patch this so we can make sure feature enabled isn't modified
        mqtt_pipeline.feature_enabled.__getitem__.return_value = False

        client._receive_type = RECEIVE_TYPE_HANDLER
        # Error was raised
        with pytest.raises(client_exceptions.ClientError):
            client.receive_method_request(method_name=method_name, block=block, timeout=timeout)
        # Feature was not enabled
        assert mqtt_pipeline.enable_feature.call_count == 0
        # Inbox get was not called
        assert inbox_mock.get.call_count == 0


class SharedClientSendMethodResponseTests(WaitsForEventCompletion):
    @pytest.mark.it("Begins a 'send_method_response' pipeline operation")
    def test_send_method_response_calls_pipeline(self, client, mqtt_pipeline, method_response):

        client.send_method_response(method_response)
        assert mqtt_pipeline.send_method_response.call_count == 1
        assert mqtt_pipeline.send_method_response.call_args[0][0] is method_response

    @pytest.mark.it(
        "Waits for the completion of the 'send_method_response' pipeline operation before returning"
    )
    def test_waits_for_pipeline_op_completion(
        self, mocker, client_manual_cb, mqtt_pipeline_manual_cb, method_response
    ):
        self.add_event_completion_checks(
            mocker=mocker, pipeline_function=mqtt_pipeline_manual_cb.send_method_response
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
        mqtt_pipeline_manual_cb,
        method_response,
        pipeline_error,
        client_error,
    ):
        my_pipeline_error = pipeline_error()
        self.add_event_completion_checks(
            mocker=mocker,
            pipeline_function=mqtt_pipeline_manual_cb.send_method_response,
            kwargs={"error": my_pipeline_error},
        )
        with pytest.raises(client_error) as e_info:
            client_manual_cb.send_method_response(method_response)
        assert e_info.value.__cause__ is my_pipeline_error


class SharedClientGetTwinTests(WaitsForEventCompletion):
    @pytest.fixture
    def patch_get_twin_to_return_fake_twin(self, fake_twin, mocker, mqtt_pipeline):
        def immediate_callback(callback):
            callback(twin=fake_twin)

        mocker.patch.object(mqtt_pipeline, "get_twin", side_effect=immediate_callback)

    @pytest.mark.it("Implicitly enables twin messaging feature if not already enabled")
    def test_enables_twin_only_if_not_already_enabled(
        self, mocker, client, mqtt_pipeline, patch_get_twin_to_return_fake_twin, fake_twin
    ):
        # Verify twin enabled if not enabled
        mqtt_pipeline.feature_enabled.__getitem__.return_value = False  # twin will appear disabled
        client.get_twin()
        assert mqtt_pipeline.enable_feature.call_count == 1
        assert mqtt_pipeline.enable_feature.call_args[0][0] == pipeline_constant.TWIN

        mqtt_pipeline.enable_feature.reset_mock()

        # Verify twin not enabled if already enabled
        mqtt_pipeline.feature_enabled.__getitem__.return_value = True  # twin will appear enabled
        client.get_twin()
        assert mqtt_pipeline.enable_feature.call_count == 0

    @pytest.mark.it("Begins a 'get_twin' pipeline operation")
    def test_get_twin_calls_pipeline(self, client, mqtt_pipeline):
        client.get_twin()
        assert mqtt_pipeline.get_twin.call_count == 1

    @pytest.mark.it(
        "Waits for the completion of the 'get_twin' pipeline operation before returning"
    )
    def test_waits_for_pipeline_op_completion(
        self, mocker, client_manual_cb, mqtt_pipeline_manual_cb, fake_twin
    ):
        self.add_event_completion_checks(
            mocker=mocker,
            pipeline_function=mqtt_pipeline_manual_cb.get_twin,
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
        self, mocker, client_manual_cb, mqtt_pipeline_manual_cb, pipeline_error, client_error
    ):
        my_pipeline_error = pipeline_error()
        self.add_event_completion_checks(
            mocker=mocker,
            pipeline_function=mqtt_pipeline_manual_cb.get_twin,
            kwargs={"error": my_pipeline_error},
        )
        with pytest.raises(client_error) as e_info:
            client_manual_cb.get_twin()
        assert e_info.value.__cause__ is my_pipeline_error

    @pytest.mark.it("Returns the twin that the pipeline returned")
    def test_verifies_twin_returned(
        self, mocker, client_manual_cb, mqtt_pipeline_manual_cb, fake_twin
    ):
        self.add_event_completion_checks(
            mocker=mocker,
            pipeline_function=mqtt_pipeline_manual_cb.get_twin,
            kwargs={"twin": fake_twin},
        )
        returned_twin = client_manual_cb.get_twin()
        assert returned_twin == fake_twin


class SharedClientPatchTwinReportedPropertiesTests(WaitsForEventCompletion):
    @pytest.mark.it("Implicitly enables twin messaging feature if not already enabled")
    def test_enables_twin_only_if_not_already_enabled(
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
        client.patch_twin_reported_properties(twin_patch_reported)
        assert mqtt_pipeline.enable_feature.call_count == 1
        assert mqtt_pipeline.enable_feature.call_args[0][0] == pipeline_constant.TWIN

        mqtt_pipeline.enable_feature.reset_mock()

        # Verify twin not enabled if already enabled
        mqtt_pipeline.feature_enabled.__getitem__.return_value = True  # twin will appear enabled
        client.patch_twin_reported_properties(twin_patch_reported)
        assert mqtt_pipeline.enable_feature.call_count == 0

    @pytest.mark.it("Begins a 'patch_twin_reported_properties' pipeline operation")
    def test_patch_twin_reported_properties_calls_pipeline(
        self, client, mqtt_pipeline, twin_patch_reported
    ):
        client.patch_twin_reported_properties(twin_patch_reported)
        assert mqtt_pipeline.patch_twin_reported_properties.call_count == 1
        assert (
            mqtt_pipeline.patch_twin_reported_properties.call_args[1]["patch"]
            is twin_patch_reported
        )

    @pytest.mark.it(
        "Waits for the completion of the 'patch_twin_reported_properties' pipeline operation before returning"
    )
    def test_waits_for_pipeline_op_completion(
        self, mocker, client_manual_cb, mqtt_pipeline_manual_cb, twin_patch_reported
    ):
        self.add_event_completion_checks(
            mocker=mocker, pipeline_function=mqtt_pipeline_manual_cb.patch_twin_reported_properties
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
        mqtt_pipeline_manual_cb,
        twin_patch_reported,
        pipeline_error,
        client_error,
    ):
        my_pipeline_error = pipeline_error()
        self.add_event_completion_checks(
            mocker=mocker,
            pipeline_function=mqtt_pipeline_manual_cb.patch_twin_reported_properties,
            kwargs={"error": my_pipeline_error},
        )
        with pytest.raises(client_error) as e_info:
            client_manual_cb.patch_twin_reported_properties(twin_patch_reported)
        assert e_info.value.__cause__ is my_pipeline_error


class SharedClientReceiveTwinDesiredPropertiesPatchTests(object):
    @pytest.mark.it(
        "Implicitly enables Twin desired properties patch feature if not already enabled"
    )
    def test_enables_twin_patches_only_if_not_already_enabled(self, mocker, client, mqtt_pipeline):
        mocker.patch.object(
            SyncClientInbox, "get"
        )  # patch this so receive_twin_desired_properties_patch won't block

        # Verify twin patches enabled if not enabled
        mqtt_pipeline.feature_enabled.__getitem__.return_value = (
            False
        )  # twin patches will appear disabled
        client.receive_twin_desired_properties_patch()
        assert mqtt_pipeline.enable_feature.call_count == 1
        assert mqtt_pipeline.enable_feature.call_args[0][0] == pipeline_constant.TWIN_PATCHES

        mqtt_pipeline.enable_feature.reset_mock()

        # Verify twin patches not enabled if already enabled
        mqtt_pipeline.feature_enabled.__getitem__.return_value = True  # C2D will appear enabled
        client.receive_twin_desired_properties_patch()
        assert mqtt_pipeline.enable_feature.call_count == 0

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

    @pytest.mark.it("Locks the client to API Receive Mode if the receive mode has not yet been set")
    @pytest.mark.parametrize(
        "block,timeout",
        [
            pytest.param(True, None, id="Blocking, no timeout"),
            pytest.param(True, 10, id="Blocking with timeout"),
            pytest.param(False, None, id="Nonblocking"),
        ],
    )
    def test_receive_mode_not_set(self, mocker, client, block, timeout):
        inbox_mock = mocker.MagicMock(autospec=SyncClientInbox)
        mocker.patch.object(client._inbox_manager, "get_twin_patch_inbox", return_value=inbox_mock)

        assert client._receive_type is RECEIVE_TYPE_NONE_SET
        client.receive_twin_desired_properties_patch(block=block, timeout=timeout)
        assert client._receive_type is RECEIVE_TYPE_API

    @pytest.mark.it(
        "Does not modify the client receive mode if it has already been set to API Receive Mode"
    )
    @pytest.mark.parametrize(
        "block,timeout",
        [
            pytest.param(True, None, id="Blocking, no timeout"),
            pytest.param(True, 10, id="Blocking with timeout"),
            pytest.param(False, None, id="Nonblocking"),
        ],
    )
    def test_receive_mode_set_api(self, mocker, client, block, timeout):
        inbox_mock = mocker.MagicMock(autospec=SyncClientInbox)
        mocker.patch.object(client._inbox_manager, "get_twin_patch_inbox", return_value=inbox_mock)

        client._receive_type = RECEIVE_TYPE_API
        client.receive_twin_desired_properties_patch(block=block, timeout=timeout)
        assert client._receive_type is RECEIVE_TYPE_API

    @pytest.mark.it(
        "Raises a ClientError and does nothing else if the client receive mode has been set to Handler Receive Mode"
    )
    @pytest.mark.parametrize(
        "block,timeout",
        [
            pytest.param(True, None, id="Blocking, no timeout"),
            pytest.param(True, 10, id="Blocking with timeout"),
            pytest.param(False, None, id="Nonblocking"),
        ],
    )
    def test_receive_mode_set_handler(self, mocker, client, mqtt_pipeline, block, timeout):
        inbox_mock = mocker.MagicMock(autospec=SyncClientInbox)
        mocker.patch.object(client._inbox_manager, "get_twin_patch_inbox", return_value=inbox_mock)
        # patch this so we can make sure feature enabled isn't modified
        mqtt_pipeline.feature_enabled.__getitem__.return_value = False

        client._receive_type = RECEIVE_TYPE_HANDLER
        # Error was raised
        with pytest.raises(client_exceptions.ClientError):
            client.receive_twin_desired_properties_patch(block=block, timeout=timeout)
        # Feature was not enabled
        assert mqtt_pipeline.enable_feature.call_count == 0
        # Inbox get was not called
        assert inbox_mock.get.call_count == 0


################
# DEVICE TESTS #
################
class IoTHubDeviceClientTestsConfig(object):
    @pytest.fixture
    def client_class(self):
        return IoTHubDeviceClient

    @pytest.fixture
    def client(self, mqtt_pipeline, http_pipeline):
        """This client automatically resolves callbacks sent to the pipeline.
        It should be used for the majority of tests.
        """
        return IoTHubDeviceClient(mqtt_pipeline, http_pipeline)

    @pytest.fixture
    def client_manual_cb(self, mqtt_pipeline_manual_cb, http_pipeline_manual_cb):
        """This client requires manual triggering of the callbacks sent to the pipeline.
        It should only be used for tests where manual control fo a callback is required.
        """
        return IoTHubDeviceClient(mqtt_pipeline_manual_cb, http_pipeline_manual_cb)

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
    IoTHubDeviceClientTestsConfig, SharedIoTHubClientInstantiationTests
):
    @pytest.mark.it("Sets on_c2d_message_received handler in the MQTTPipeline")
    def test_sets_on_c2d_message_received_handler_in_pipeline(
        self, client_class, mqtt_pipeline, http_pipeline
    ):
        client = client_class(mqtt_pipeline, http_pipeline)

        assert client._mqtt_pipeline.on_c2d_message_received is not None
        assert (
            client._mqtt_pipeline.on_c2d_message_received == client._inbox_manager.route_c2d_message
        )


@pytest.mark.describe("IoTHubDeviceClient (Synchronous) - .create_from_connection_string()")
class TestIoTHubDeviceClientCreateFromConnectionString(
    IoTHubDeviceClientTestsConfig, SharedIoTHubClientCreateFromConnectionStringTests
):
    pass


@pytest.mark.describe("IoTHubDeviceClient (Synchronous) - .create_from_symmetric_key()")
class TestIoTHubDeviceClientCreateFromSymmetricKey(
    IoTHubDeviceClientTestsConfig, SharedIoTHubDeviceClientCreateFromSymmetricKeyTests
):
    pass


@pytest.mark.describe("IoTHubDeviceClient (Synchronous) - .create_from_x509_certificate()")
class TestIoTHubDeviceClientCreateFromX509Certificate(
    IoTHubDeviceClientTestsConfig, SharedIoTHubDeviceClientCreateFromX509CertificateTests
):
    pass


@pytest.mark.describe("IoTHubDeviceClient (Synchronous) - .connect()")
class TestIoTHubDeviceClientConnect(IoTHubDeviceClientTestsConfig, SharedClientConnectTests):
    pass


@pytest.mark.describe("IoTHubDeviceClient (Synchronous) - .disconnect()")
class TestIoTHubDeviceClientDisconnect(IoTHubDeviceClientTestsConfig, SharedClientDisconnectTests):
    pass


@pytest.mark.describe("IoTHubDeviceClient (Synchronous) - OCCURANCE: Disconnect")
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
    def test_enables_c2d_messaging_only_if_not_already_enabled(self, mocker, client, mqtt_pipeline):
        mocker.patch.object(SyncClientInbox, "get")  # patch this so receive_message won't block

        # Verify C2D Messaging enabled if not enabled
        mqtt_pipeline.feature_enabled.__getitem__.return_value = False  # C2D will appear disabled
        client.receive_message()
        assert mqtt_pipeline.enable_feature.call_count == 1
        assert mqtt_pipeline.enable_feature.call_args[0][0] == pipeline_constant.C2D_MSG

        mqtt_pipeline.enable_feature.reset_mock()

        # Verify C2D Messaging not enabled if already enabled
        mqtt_pipeline.feature_enabled.__getitem__.return_value = True  # C2D will appear enabled
        client.receive_message()
        assert mqtt_pipeline.enable_feature.call_count == 0

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

    @pytest.mark.it("Locks the client to API Receive Mode if the receive mode has not yet been set")
    @pytest.mark.parametrize(
        "block,timeout",
        [
            pytest.param(True, None, id="Blocking, no timeout"),
            pytest.param(True, 10, id="Blocking with timeout"),
            pytest.param(False, None, id="Nonblocking"),
        ],
    )
    def test_receive_mode_not_set(self, mocker, client, block, timeout):
        inbox_mock = mocker.MagicMock(autospec=SyncClientInbox)
        mocker.patch.object(client._inbox_manager, "get_c2d_message_inbox", return_value=inbox_mock)

        assert client._receive_type is RECEIVE_TYPE_NONE_SET
        client.receive_message(block=block, timeout=timeout)
        assert client._receive_type is RECEIVE_TYPE_API

    @pytest.mark.it(
        "Does not modify the client receive mode if it has already been set to API Receive Mode"
    )
    @pytest.mark.parametrize(
        "block,timeout",
        [
            pytest.param(True, None, id="Blocking, no timeout"),
            pytest.param(True, 10, id="Blocking with timeout"),
            pytest.param(False, None, id="Nonblocking"),
        ],
    )
    def test_receive_mode_set_api(self, mocker, client, block, timeout):
        inbox_mock = mocker.MagicMock(autospec=SyncClientInbox)
        mocker.patch.object(client._inbox_manager, "get_c2d_message_inbox", return_value=inbox_mock)

        client._receive_type = RECEIVE_TYPE_API
        client.receive_message(block=block, timeout=timeout)
        assert client._receive_type is RECEIVE_TYPE_API

    @pytest.mark.it(
        "Raises a ClientError and does nothing else if the client receive mode has been set to Handler Receive Mode"
    )
    @pytest.mark.parametrize(
        "block,timeout",
        [
            pytest.param(True, None, id="Blocking, no timeout"),
            pytest.param(True, 10, id="Blocking with timeout"),
            pytest.param(False, None, id="Nonblocking"),
        ],
    )
    def test_receive_mode_set_handler(self, mocker, client, mqtt_pipeline, block, timeout):
        inbox_mock = mocker.MagicMock(autospec=SyncClientInbox)
        mocker.patch.object(client._inbox_manager, "get_c2d_message_inbox", return_value=inbox_mock)
        # patch this so we can make sure feature enabled isn't modified
        mqtt_pipeline.feature_enabled.__getitem__.return_value = False

        client._receive_type = RECEIVE_TYPE_HANDLER
        # Error was raised
        with pytest.raises(client_exceptions.ClientError):
            client.receive_message(block=block, timeout=timeout)
        # Feature was not enabled
        assert mqtt_pipeline.enable_feature.call_count == 0
        # Inbox get was not called
        assert inbox_mock.get.call_count == 0


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


@pytest.mark.describe("IoTHubDeviceClient (Synchronous) - .get_storage_info_for_blob()")
class TestIoTHubDeviceClientGetStorageInfo(WaitsForEventCompletion, IoTHubDeviceClientTestsConfig):
    @pytest.mark.it("Begins a 'get_storage_info_for_blob' HTTPPipeline operation")
    def test_calls_pipeline_get_storage_info_for_blob(self, mocker, client, http_pipeline):
        fake_blob_name = "__fake_blob_name__"
        client.get_storage_info_for_blob(fake_blob_name)
        assert http_pipeline.get_storage_info_for_blob.call_count == 1
        assert http_pipeline.get_storage_info_for_blob.call_args == mocker.call(
            fake_blob_name, callback=mocker.ANY
        )

    @pytest.mark.it(
        "Waits for the completion of the 'get_storage_info_for_blob' pipeline operation before returning"
    )
    def test_waits_for_pipeline_op_completion(
        self, mocker, client_manual_cb, http_pipeline_manual_cb
    ):
        fake_blob_name = "__fake_blob_name__"

        self.add_event_completion_checks(
            mocker=mocker,
            pipeline_function=http_pipeline_manual_cb.get_storage_info_for_blob,
            kwargs={"storage_info": "__fake_storage_info__"},
        )

        client_manual_cb.get_storage_info_for_blob(fake_blob_name)

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
            pytest.param(Exception, client_exceptions.ClientError, id="Exception->ClientError"),
        ],
    )
    def test_raises_error_on_pipeline_op_error(
        self, mocker, client_manual_cb, http_pipeline_manual_cb, pipeline_error, client_error
    ):
        fake_blob_name = "__fake_blob_name__"
        my_pipeline_error = pipeline_error()
        self.add_event_completion_checks(
            mocker=mocker,
            pipeline_function=http_pipeline_manual_cb.get_storage_info_for_blob,
            kwargs={"error": my_pipeline_error},
        )
        with pytest.raises(client_error) as e_info:
            client_manual_cb.get_storage_info_for_blob(fake_blob_name)
        assert e_info.value.__cause__ is my_pipeline_error

    @pytest.mark.it("Returns a storage_info object upon successful completion")
    def test_returns_storage_info(self, mocker, client, http_pipeline):
        fake_blob_name = "__fake_blob_name__"
        fake_storage_info = "__fake_storage_info__"
        received_storage_info = client.get_storage_info_for_blob(fake_blob_name)
        assert http_pipeline.get_storage_info_for_blob.call_count == 1
        assert http_pipeline.get_storage_info_for_blob.call_args == mocker.call(
            fake_blob_name, callback=mocker.ANY
        )

        assert (
            received_storage_info is fake_storage_info
        )  # Note: the return value this is checkign for is defined in client_fixtures.py


@pytest.mark.describe("IoTHubDeviceClient (Synchronous) - .notify_blob_upload_status()")
class TestIoTHubDeviceClientNotifyBlobUploadStatus(
    WaitsForEventCompletion, IoTHubDeviceClientTestsConfig
):
    @pytest.mark.it("Begins a 'notify_blob_upload_status' HTTPPipeline operation")
    def test_calls_pipeline_notify_blob_upload_status(self, client, http_pipeline):
        correlation_id = "__fake_correlation_id__"
        is_success = "__fake_is_success__"
        status_code = "__fake_status_code__"
        status_description = "__fake_status_description__"
        client.notify_blob_upload_status(
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
    def test_waits_for_pipeline_op_completion(
        self, mocker, client_manual_cb, http_pipeline_manual_cb
    ):
        correlation_id = "__fake_correlation_id__"
        is_success = "__fake_is_success__"
        status_code = "__fake_status_code__"
        status_description = "__fake_status_description__"
        self.add_event_completion_checks(
            mocker=mocker, pipeline_function=http_pipeline_manual_cb.notify_blob_upload_status
        )

        client_manual_cb.notify_blob_upload_status(
            correlation_id, is_success, status_code, status_description
        )

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
    def test_raises_error_on_pipeline_op_error(
        self, mocker, client_manual_cb, http_pipeline_manual_cb, pipeline_error, client_error
    ):
        correlation_id = "__fake_correlation_id__"
        is_success = "__fake_is_success__"
        status_code = "__fake_status_code__"
        status_description = "__fake_status_description__"
        my_pipeline_error = pipeline_error()
        self.add_event_completion_checks(
            mocker=mocker,
            pipeline_function=http_pipeline_manual_cb.notify_blob_upload_status,
            kwargs={"error": my_pipeline_error},
        )
        with pytest.raises(client_error) as e_info:
            client_manual_cb.notify_blob_upload_status(
                correlation_id, is_success, status_code, status_description
            )
            assert e_info.value.__cause__ is my_pipeline_error


@pytest.mark.describe("IoTHubDeviceClient (Synchronous) - PROPERTY .on_message_received")
class TestIoTHubDeviceClientPROPERTYOnMessageReceivedHandler(
    IoTHubDeviceClientTestsConfig, SharedIoTHubClientPROPERTYHandlerTests
):
    @pytest.fixture
    def handler_name(self):
        return "on_message_received"

    @pytest.fixture
    def feature_name(self):
        return pipeline_constant.C2D_MSG


@pytest.mark.describe("IoTHubDeviceClient (Synchronous) - PROPERTY .on_method_request_received")
class TestIoTHubDeviceClientPROPERTYOnMethodRequestReceivedHandler(
    IoTHubDeviceClientTestsConfig, SharedIoTHubClientPROPERTYHandlerTests
):
    @pytest.fixture
    def handler_name(self):
        return "on_method_request_received"

    @pytest.fixture
    def feature_name(self):
        return pipeline_constant.METHODS


@pytest.mark.describe(
    "IoTHubDeviceClient (Synchronous) - PROPERTY .on_twin_desired_properties_patch_received"
)
class TestIoTHubDeviceClientPROPERTYOnTwinDesiredPropertiesPatchReceivedHandler(
    IoTHubDeviceClientTestsConfig, SharedIoTHubClientPROPERTYHandlerTests
):
    @pytest.fixture
    def handler_name(self):
        return "on_twin_desired_properties_patch_received"

    @pytest.fixture
    def feature_name(self):
        return pipeline_constant.TWIN_PATCHES


@pytest.mark.describe("IoTHubDeviceClient (Synchronous) - PROPERTY .connected")
class TestIoTHubDeviceClientPROPERTYConnected(
    IoTHubDeviceClientTestsConfig, SharedIoTHubClientPROPERTYConnectedTests
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
    def client(self, mqtt_pipeline, http_pipeline):
        """This client automatically resolves callbacks sent to the pipeline.
        It should be used for the majority of tests.
        """
        return IoTHubModuleClient(mqtt_pipeline, http_pipeline)

    @pytest.fixture
    def client_manual_cb(self, mqtt_pipeline_manual_cb, http_pipeline_manual_cb):
        """This client requires manual triggering of the callbacks sent to the pipeline.
        It should only be used for tests where manual control fo a callback is required.
        """
        return IoTHubModuleClient(mqtt_pipeline_manual_cb, http_pipeline_manual_cb)

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
    IoTHubModuleClientTestsConfig, SharedIoTHubClientInstantiationTests
):
    @pytest.mark.it("Sets on_input_message_received handler in the MQTTPipeline")
    def test_sets_on_input_message_received_handler_in_pipeline(
        self, client_class, mqtt_pipeline, http_pipeline
    ):
        client = client_class(mqtt_pipeline, http_pipeline)

        assert client._mqtt_pipeline.on_input_message_received is not None
        assert (
            client._mqtt_pipeline.on_input_message_received
            == client._inbox_manager.route_input_message
        )


@pytest.mark.describe("IoTHubModuleClient (Synchronous) - .create_from_connection_string()")
class TestIoTHubModuleClientCreateFromConnectionString(
    IoTHubModuleClientTestsConfig, SharedIoTHubClientCreateFromConnectionStringTests
):
    pass


@pytest.mark.describe(
    "IoTHubModuleClient (Synchronous) - .create_from_edge_environment() -- Edge Container Environment"
)
class TestIoTHubModuleClientCreateFromEdgeEnvironmentWithContainerEnv(
    IoTHubModuleClientTestsConfig,
    SharedIoTHubModuleClientCreateFromEdgeEnvironmentWithContainerEnvTests,
):
    pass


@pytest.mark.describe(
    "IoTHubModuleClient (Synchronous) - .create_from_edge_environment() -- Edge Local Debug Environment"
)
class TestIoTHubModuleClientCreateFromEdgeEnvironmentWithDebugEnv(
    IoTHubModuleClientTestsConfig,
    SharedIoTHubModuleClientCreateFromEdgeEnvironmentWithDebugEnvTests,
):
    pass


@pytest.mark.describe("IoTHubModuleClient (Synchronous) - .create_from_x509_certificate()")
class TestIoTHubModuleClientCreateFromX509Certificate(
    IoTHubModuleClientTestsConfig, SharedIoTHubModuleClientCreateFromX509CertificateTests
):
    pass


@pytest.mark.describe("IoTHubModuleClient (Synchronous) - .connect()")
class TestIoTHubModuleClientConnect(IoTHubModuleClientTestsConfig, SharedClientConnectTests):
    pass


@pytest.mark.describe("IoTHubModuleClient (Synchronous) - .disconnect()")
class TestIoTHubModuleClientDisconnect(IoTHubModuleClientTestsConfig, SharedClientDisconnectTests):
    pass


@pytest.mark.describe("IoTHubModuleClient (Synchronous) - OCCURANCE: Disconnect")
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
    @pytest.mark.it("Begins a 'send_output_message' pipeline operation")
    def test_calls_pipeline_send_message_to_output(self, client, mqtt_pipeline, message):
        output_name = "some_output"
        client.send_message_to_output(message, output_name)
        assert mqtt_pipeline.send_output_message.call_count == 1
        assert mqtt_pipeline.send_output_message.call_args[0][0] is message
        assert message.output_name == output_name

    @pytest.mark.it(
        "Waits for the completion of the 'send_output_message' pipeline operation before returning"
    )
    def test_waits_for_pipeline_op_completion(
        self, mocker, client_manual_cb, mqtt_pipeline_manual_cb, message
    ):
        self.add_event_completion_checks(
            mocker=mocker, pipeline_function=mqtt_pipeline_manual_cb.send_output_message
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
        mqtt_pipeline_manual_cb,
        message,
        pipeline_error,
        client_error,
    ):
        my_pipeline_error = pipeline_error()
        self.add_event_completion_checks(
            mocker=mocker,
            pipeline_function=mqtt_pipeline_manual_cb.send_output_message,
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
        self, client, mqtt_pipeline, message_input
    ):
        output_name = "some_output"
        client.send_message_to_output(message_input, output_name)
        assert mqtt_pipeline.send_output_message.call_count == 1
        sent_message = mqtt_pipeline.send_output_message.call_args[0][0]
        assert isinstance(sent_message, Message)
        assert sent_message.data == message_input

    @pytest.mark.it("Raises error when message data size is greater than 256 KB")
    def test_raises_error_when_message_to_output_data_greater_than_256(self, client, mqtt_pipeline):
        output_name = "some_output"
        data_input = "serpensortia" * 256000
        message = Message(data_input)
        with pytest.raises(ValueError) as e_info:
            client.send_message_to_output(message, output_name)
        assert "256 KB" in e_info.value.args[0]
        assert mqtt_pipeline.send_output_message.call_count == 0

    @pytest.mark.it("Raises error when message size is greater than 256 KB")
    def test_raises_error_when_message_to_output_size_greater_than_256(self, client, mqtt_pipeline):
        output_name = "some_output"
        data_input = "serpensortia"
        message = Message(data_input)
        message.custom_properties["spell"] = data_input * 256000
        with pytest.raises(ValueError) as e_info:
            client.send_message_to_output(message, output_name)
        assert "256 KB" in e_info.value.args[0]
        assert mqtt_pipeline.send_output_message.call_count == 0

    @pytest.mark.it("Does not raises error when message data size is equal to 256 KB")
    def test_raises_error_when_message_to_output_data_equal_to_256(self, client, mqtt_pipeline):
        output_name = "some_output"
        data_input = "a" * 262095
        message = Message(data_input)
        # This check was put as message class may undergo the default content type encoding change
        # and the above calculation will change.
        # Had to do greater than check for python 2. Ideally should be not equal check
        if message.get_size() > device_constant.TELEMETRY_MESSAGE_SIZE_LIMIT:
            assert False

        client.send_message_to_output(message, output_name)

        assert mqtt_pipeline.send_output_message.call_count == 1
        sent_message = mqtt_pipeline.send_output_message.call_args[0][0]
        assert isinstance(sent_message, Message)
        assert sent_message.data == data_input


@pytest.mark.describe("IoTHubModuleClient (Synchronous) - .receive_message_on_input()")
class TestIoTHubModuleClientReceiveInputMessage(IoTHubModuleClientTestsConfig):
    @pytest.mark.it("Implicitly enables input messaging feature if not already enabled")
    def test_enables_input_messaging_only_if_not_already_enabled(
        self, mocker, client, mqtt_pipeline
    ):
        mocker.patch.object(
            SyncClientInbox, "get"
        )  # patch this receive_message_on_input won't block
        input_name = "some_input"

        # Verify Input Messaging enabled if not enabled
        mqtt_pipeline.feature_enabled.__getitem__.return_value = (
            False
        )  # Input Messages will appear disabled
        client.receive_message_on_input(input_name)
        assert mqtt_pipeline.enable_feature.call_count == 1
        assert mqtt_pipeline.enable_feature.call_args[0][0] == pipeline_constant.INPUT_MSG

        mqtt_pipeline.enable_feature.reset_mock()

        # Verify Input Messaging not enabled if already enabled
        mqtt_pipeline.feature_enabled.__getitem__.return_value = (
            True
        )  # Input Messages will appear enabled
        client.receive_message_on_input(input_name)
        assert mqtt_pipeline.enable_feature.call_count == 0

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

    @pytest.mark.it("Locks the client to API Receive Mode if the receive mode has not yet been set")
    @pytest.mark.parametrize(
        "block,timeout",
        [
            pytest.param(True, None, id="Blocking, no timeout"),
            pytest.param(True, 10, id="Blocking with timeout"),
            pytest.param(False, None, id="Nonblocking"),
        ],
    )
    def test_receive_mode_not_set(self, mocker, client, block, timeout):
        inbox_mock = mocker.MagicMock(autospec=SyncClientInbox)
        mocker.patch.object(
            client._inbox_manager, "get_input_message_inbox", return_value=inbox_mock
        )

        assert client._receive_type is RECEIVE_TYPE_NONE_SET
        client.receive_message_on_input(input_name="some_input", block=block, timeout=timeout)
        assert client._receive_type is RECEIVE_TYPE_API

    @pytest.mark.it(
        "Does not modify the client receive mode if it has already been set to API Receive Mode"
    )
    @pytest.mark.parametrize(
        "block,timeout",
        [
            pytest.param(True, None, id="Blocking, no timeout"),
            pytest.param(True, 10, id="Blocking with timeout"),
            pytest.param(False, None, id="Nonblocking"),
        ],
    )
    def test_receive_mode_set_api(self, mocker, client, block, timeout):
        inbox_mock = mocker.MagicMock(autospec=SyncClientInbox)
        mocker.patch.object(
            client._inbox_manager, "get_input_message_inbox", return_value=inbox_mock
        )

        client._receive_type = RECEIVE_TYPE_API
        client.receive_message_on_input(input_name="some_input", block=block, timeout=timeout)
        assert client._receive_type is RECEIVE_TYPE_API

    @pytest.mark.it(
        "Raises a ClientError and does nothing else if the client receive mode has been set to Handler Receive Mode"
    )
    @pytest.mark.parametrize(
        "block,timeout",
        [
            pytest.param(True, None, id="Blocking, no timeout"),
            pytest.param(True, 10, id="Blocking with timeout"),
            pytest.param(False, None, id="Nonblocking"),
        ],
    )
    def test_receive_mode_set_handler(self, mocker, client, mqtt_pipeline, block, timeout):
        inbox_mock = mocker.MagicMock(autospec=SyncClientInbox)
        mocker.patch.object(
            client._inbox_manager, "get_input_message_inbox", return_value=inbox_mock
        )
        # patch this so we can make sure feature enabled isn't modified
        mqtt_pipeline.feature_enabled.__getitem__.return_value = False

        client._receive_type = RECEIVE_TYPE_HANDLER
        # Error was raised
        with pytest.raises(client_exceptions.ClientError):
            client.receive_message_on_input(input_name="some_input", block=block, timeout=timeout)
        # Feature was not enabled
        assert mqtt_pipeline.enable_feature.call_count == 0
        # Inbox get was not called
        assert inbox_mock.get.call_count == 0


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


@pytest.mark.describe("IoTHubModuleClient (Synchronous) - .invoke_method()")
class TestIoTHubModuleClientInvokeMethod(WaitsForEventCompletion, IoTHubModuleClientTestsConfig):
    @pytest.mark.it("Begins a 'invoke_method' HTTPPipeline operation where the target is a device")
    def test_calls_pipeline_invoke_method_for_device(self, client, http_pipeline):
        method_params = {"methodName": "__fake_method_name__"}
        device_id = "__fake_device_id__"
        client.invoke_method(method_params, device_id)
        assert http_pipeline.invoke_method.call_count == 1
        assert http_pipeline.invoke_method.call_args[0][0] is device_id
        assert http_pipeline.invoke_method.call_args[0][1] is method_params

    @pytest.mark.it("Begins a 'invoke_method' HTTPPipeline operation where the target is a module")
    def test_calls_pipeline_invoke_method_for_module(self, client, http_pipeline):
        method_params = {"methodName": "__fake_method_name__"}
        device_id = "__fake_device_id__"
        module_id = "__fake_module_id__"
        client.invoke_method(method_params, device_id, module_id=module_id)
        assert http_pipeline.invoke_method.call_count == 1
        assert http_pipeline.invoke_method.call_args[0][0] is device_id
        assert http_pipeline.invoke_method.call_args[0][1] is method_params
        assert http_pipeline.invoke_method.call_args[1]["module_id"] is module_id

    @pytest.mark.it(
        "Waits for the completion of the 'invoke_method' pipeline operation before returning"
    )
    def test_waits_for_pipeline_op_completion(
        self, mocker, client_manual_cb, http_pipeline_manual_cb
    ):
        method_params = {"methodName": "__fake_method_name__"}
        device_id = "__fake_device_id__"
        module_id = "__fake_module_id__"
        self.add_event_completion_checks(
            mocker=mocker,
            pipeline_function=http_pipeline_manual_cb.invoke_method,
            kwargs={"invoke_method_response": "__fake_invoke_method_response__"},
        )

        client_manual_cb.invoke_method(method_params, device_id, module_id=module_id)

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
            pytest.param(Exception, client_exceptions.ClientError, id="Exception->ClientError"),
        ],
    )
    def test_raises_error_on_pipeline_op_error(
        self, mocker, client_manual_cb, http_pipeline_manual_cb, pipeline_error, client_error
    ):
        method_params = {"methodName": "__fake_method_name__"}
        device_id = "__fake_device_id__"
        module_id = "__fake_module_id__"
        my_pipeline_error = pipeline_error()
        self.add_event_completion_checks(
            mocker=mocker,
            pipeline_function=http_pipeline_manual_cb.invoke_method,
            kwargs={"error": my_pipeline_error},
        )
        with pytest.raises(client_error) as e_info:
            client_manual_cb.invoke_method(method_params, device_id, module_id=module_id)
            assert e_info.value.__cause__ is my_pipeline_error


@pytest.mark.describe("IoTHubModuleClient (Synchronous) - PROPERTY .on_message_received")
class TestIoTHubModuleClientPROPERTYOnMessageReceivedHandler(
    IoTHubModuleClientTestsConfig, SharedIoTHubClientPROPERTYHandlerTests
):
    @pytest.fixture
    def handler_name(self):
        return "on_message_received"

    @pytest.fixture
    def feature_name(self):
        return pipeline_constant.INPUT_MSG


@pytest.mark.describe("IoTHubModuleClient (Synchronous) - PROPERTY .on_method_request_received")
class TestIoTHubModuleClientPROPERTYOnMethodRequestReceivedHandler(
    IoTHubModuleClientTestsConfig, SharedIoTHubClientPROPERTYHandlerTests
):
    @pytest.fixture
    def handler_name(self):
        return "on_method_request_received"

    @pytest.fixture
    def feature_name(self):
        return pipeline_constant.METHODS


@pytest.mark.describe(
    "IoTHubModuleClient (Synchronous) - PROPERTY .on_twin_desired_properties_patch_received"
)
class TestIoTHubModuleClientPROPERTYOnTwinDesiredPropertiesPatchReceivedHandler(
    IoTHubModuleClientTestsConfig, SharedIoTHubClientPROPERTYHandlerTests
):
    @pytest.fixture
    def handler_name(self):
        return "on_twin_desired_properties_patch_received"

    @pytest.fixture
    def feature_name(self):
        return pipeline_constant.TWIN_PATCHES


@pytest.mark.describe("IoTHubModule (Synchronous) - PROPERTY .connected")
class TestIoTHubModuleClientPROPERTYConnected(
    IoTHubModuleClientTestsConfig, SharedIoTHubClientPROPERTYConnectedTests
):
    pass
