# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
import threading
import time
import os
import io
import six
from azure.iot.device.iothub import IoTHubDeviceClient, IoTHubModuleClient
from azure.iot.device.iothub.pipeline import IoTHubPipeline, constant
from azure.iot.device.iothub.models import Message, MethodRequest
from azure.iot.device.iothub.sync_inbox import SyncClientInbox, InboxEmpty
from azure.iot.device.iothub.auth import IoTEdgeError


################
# SHARED TESTS #
################
class SharedClientInstantiationTests(object):
    @pytest.mark.it("Sets on_connected handler in pipeline")
    def test_sets_on_connected_handler_in_pipeline(self, client):
        assert client._pipeline.on_connected is not None
        assert client._pipeline.on_connected == client._on_connected

    @pytest.mark.it("Sets on_disconnected handler in pipeline")
    def test_sets_on_disconnected_handler_in_pipeline(self, client):
        assert client._pipeline.on_disconnected is not None
        assert client._pipeline.on_disconnected == client._on_disconnected

    @pytest.mark.it("Sets on_method_request_received handler in pipeline")
    def test_sets_on_method_request_received_handler_in_pipleline(self, client):
        assert client._pipeline.on_method_request_received is not None
        assert (
            client._pipeline.on_method_request_received
            == client._inbox_manager.route_method_request
        )


class SharedClientFromCreateFromConnectionStringTests(object):
    @pytest.mark.it("Instantiates the client")
    @pytest.mark.parametrize(
        "trusted_cert_chain",
        [
            pytest.param(None, id="No trusted cert chain"),
            pytest.param("some-certificate", id="With trusted cert chain"),
        ],
    )
    def test_instantiates_client(self, client_class, connection_string, trusted_cert_chain):
        args = (connection_string,)
        kwargs = {}
        if trusted_cert_chain:
            kwargs["trusted_certificate_chain"] = trusted_cert_chain
        client = client_class.create_from_connection_string(*args, **kwargs)
        assert isinstance(client, client_class)

    @pytest.mark.it(
        "Uses a SymmetricKeyAuthenticationProvider to create the client's IoTHub pipeline"
    )
    @pytest.mark.parametrize(
        "trusted_cert_chain",
        [
            pytest.param(None, id="No trusted cert chain"),
            pytest.param("some-certificate", id="With trusted cert chain"),
        ],
    )
    def test_auth_provider_and_pipeline(self, mocker, client_class, trusted_cert_chain):
        mock_auth_parse = mocker.patch(
            "azure.iot.device.iothub.auth.SymmetricKeyAuthenticationProvider"
        ).parse
        mock_pipeline_init = mocker.patch("azure.iot.device.iothub.abstract_clients.IoTHubPipeline")

        mock_conn_str = mocker.MagicMock()
        client = client_class.create_from_connection_string(
            mock_conn_str, trusted_certificate_chain=trusted_cert_chain
        )

        assert mock_auth_parse.call_count == 1
        assert mock_auth_parse.call_args == mocker.call(mock_conn_str)
        assert mock_auth_parse.return_value.ca_cert is trusted_cert_chain
        assert mock_pipeline_init.call_count == 1
        assert mock_pipeline_init.call_args == mocker.call(mock_auth_parse.return_value)
        assert client._pipeline == mock_pipeline_init.return_value

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


class SharedClientFromCreateFromSharedAccessSignature(object):
    @pytest.mark.it("Instantiates the client, given a valid SAS token")
    def test_instantiates_client(self, client_class, sas_token_string):
        client = client_class.create_from_shared_access_signature(sas_token_string)
        assert isinstance(client, client_class)

    @pytest.mark.it(
        "Uses a SharedAccessSignatureAuthenticationProvider to create the client's IoTHub pipeline"
    )
    def test_auth_provider_and_pipeline(self, mocker, client_class):
        mock_auth_parse = mocker.patch(
            "azure.iot.device.iothub.auth.SharedAccessSignatureAuthenticationProvider"
        ).parse
        mock_pipeline_init = mocker.patch("azure.iot.device.iothub.abstract_clients.IoTHubPipeline")

        client = client_class.create_from_shared_access_signature(mocker.MagicMock())

        assert mock_auth_parse.call_count == 1
        assert mock_pipeline_init.call_count == 1
        assert mock_pipeline_init.call_args == mocker.call(mock_auth_parse.return_value)
        assert client._pipeline == mock_pipeline_init.return_value

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


class SharedClientFromCreateFromX509Certificate(object):
    @pytest.mark.it("Instantiates the client, given a valid X509 certificate object")
    def test_instantiates_client(self, client_class, x509):
        client = client_class.create_from_x509_certificate(
            hostname="durmstranginstitute.farend", device_id="MySnitch", x509=x509
        )
        assert isinstance(client, client_class)

    @pytest.mark.it("Uses a X509AuthenticationProvider to create the client's IoTHub pipeline")
    def test_auth_provider_and_pipeline(self, mocker, client_class):
        mock_auth = mocker.patch("azure.iot.device.iothub.auth.X509AuthenticationProvider")
        mock_pipeline_init = mocker.patch("azure.iot.device.iothub.abstract_clients.IoTHubPipeline")

        client = client_class.create_from_x509_certificate(
            hostname="durmstranginstitute.farend", device_id="MySnitch", x509=mocker.MagicMock()
        )

        assert mock_auth.call_count == 1
        assert mock_pipeline_init.call_count == 1
        assert mock_pipeline_init.call_args == mocker.call(mock_auth.return_value)
        assert client._pipeline == mock_pipeline_init.return_value


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
    def test_calls_pipeline_connect(self, client, pipeline):
        client.connect()
        assert pipeline.connect.call_count == 1

    @pytest.mark.it("Waits for the completion of the 'connect' pipeline operation before returning")
    def test_waits_for_pipeline_op_completion(self, mocker, client_manual_cb, pipeline_manual_cb):
        self.add_event_completion_checks(
            mocker=mocker, pipeline_function=pipeline_manual_cb.connect
        )
        client_manual_cb.connect()


class SharedClientDisconnectTests(WaitsForEventCompletion):
    @pytest.mark.it("Begins a 'disconnect' pipeline operation")
    def test_calls_pipeline_disconnect(self, client, pipeline):
        client.disconnect()
        assert pipeline.disconnect.call_count == 1

    @pytest.mark.it(
        "Waits for the completion of the 'disconnect' pipeline operation before returning"
    )
    def test_waits_for_pipeline_op_completion(self, mocker, client_manual_cb, pipeline_manual_cb):
        self.add_event_completion_checks(
            mocker=mocker, pipeline_function=pipeline_manual_cb.disconnect
        )
        client_manual_cb.disconnect()


class SharedClientDisconnectEventTests(object):
    @pytest.mark.it("Clears all pending MethodRequests upon disconnect")
    def test_state_change_handler_clears_method_request_inboxes_on_disconnect(self, client, mocker):
        clear_method_request_spy = mocker.spy(client._inbox_manager, "clear_all_method_requests")
        client._on_disconnected()
        assert clear_method_request_spy.call_count == 1


# TODO: rename
class SharedClientSendEventTests(WaitsForEventCompletion):
    @pytest.mark.it("Begins a 'send_d2c_message' pipeline operation")
    def test_calls_pipeline_send_d2c_message(self, client, pipeline, message):
        client.send_d2c_message(message)
        assert pipeline.send_d2c_message.call_count == 1
        assert pipeline.send_d2c_message.call_args[0][0] is message

    @pytest.mark.it(
        "Waits for the completion of the 'send_d2c_message' pipeline operation before returning"
    )
    def test_waits_for_pipeline_op_completion(
        self, mocker, client_manual_cb, pipeline_manual_cb, message
    ):
        self.add_event_completion_checks(
            mocker=mocker, pipeline_function=pipeline_manual_cb.send_d2c_message
        )
        client_manual_cb.send_d2c_message(message)

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
    def test_wraps_data_in_message_and_calls_pipeline_send_d2c_message(
        self, client, pipeline, message_input
    ):
        client.send_d2c_message(message_input)
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
        "Raises InboxEmpty exception after a timeout while blocking, in blocking mode with a specified timeout"
    )
    @pytest.mark.parametrize(
        "method_name",
        [pytest.param(None, id="Generic Method"), pytest.param("method_x", id="Named Method")],
    )
    def test_times_out_waiting_for_message_blocking_mode(self, client, method_name):
        with pytest.raises(InboxEmpty):
            client.receive_method_request(method_name, block=True, timeout=0.01)

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


class SharedClientSendMethodResponseTests(WaitsForEventCompletion):
    @pytest.mark.it("Begins a 'send_method_response' pipeline operation")
    def test_send_method_response_calls_pipeline(self, client, pipeline, method_response):

        client.send_method_response(method_response)
        assert pipeline.send_method_response.call_count == 1
        assert pipeline.send_method_response.call_args[0][0] is method_response

    @pytest.mark.it(
        "Waits for the completion of the 'send_method_response' pipeline operation before returning"
    )
    def test_waits_for_pipeline_op_completion(
        self, mocker, client_manual_cb, pipeline_manual_cb, method_response
    ):
        self.add_event_completion_checks(
            mocker=mocker, pipeline_function=pipeline_manual_cb.send_method_response
        )
        client_manual_cb.send_method_response(method_response)


class SharedClientGetTwinTests(WaitsForEventCompletion):
    @pytest.mark.it("Implicitly enables twin messaging feature if not already enabled")
    def test_enables_twin_only_if_not_already_enabled(self, mocker, client, pipeline):
        # patch this so get_twin won't block
        def immediate_callback(callback):
            callback(None)

        mocker.patch.object(pipeline, "get_twin", side_effect=immediate_callback)

        # Verify twin enabled if not enabled
        pipeline.feature_enabled.__getitem__.return_value = False  # twin will appear disabled
        client.get_twin()
        assert pipeline.enable_feature.call_count == 1
        assert pipeline.enable_feature.call_args[0][0] == constant.TWIN

        pipeline.enable_feature.reset_mock()

        # Verify twin not enabled if already enabled
        pipeline.feature_enabled.__getitem__.return_value = True  # twin will appear enabled
        client.get_twin()
        assert pipeline.enable_feature.call_count == 0

    @pytest.mark.it("Begins a 'get_twin' pipeline operation")
    def test_get_twin_calls_pipeline(self, client, pipeline):
        client.get_twin()
        assert pipeline.get_twin.call_count == 1

    @pytest.mark.it(
        "Waits for the completion of the 'get_twin' pipeline operation before returning"
    )
    def test_waits_for_pipeline_op_completion(self, mocker, client_manual_cb, pipeline_manual_cb):
        self.add_event_completion_checks(
            mocker=mocker, pipeline_function=pipeline_manual_cb.get_twin, args=[None]
        )
        client_manual_cb.get_twin()

    @pytest.mark.it("Returns the twin that the pipeline returned")
    def test_verifies_twin_returned(self, mocker, client_manual_cb, pipeline_manual_cb):
        twin = {"reported": {"foo": "bar"}}
        self.add_event_completion_checks(
            mocker=mocker, pipeline_function=pipeline_manual_cb.get_twin, args=[twin]
        )
        returned_twin = client_manual_cb.get_twin()
        assert returned_twin == twin


class SharedClientPatchTwinReportedPropertiesTests(WaitsForEventCompletion):
    @pytest.mark.it("Implicitly enables twin messaging feature if not already enabled")
    def test_enables_twin_only_if_not_already_enabled(
        self, mocker, client, pipeline, twin_patch_reported
    ):
        # patch this so x_get_twin won't block
        def immediate_callback(patch, callback):
            callback()

        mocker.patch.object(
            pipeline, "patch_twin_reported_properties", side_effect=immediate_callback
        )

        # Verify twin enabled if not enabled
        pipeline.feature_enabled.__getitem__.return_value = False  # twin will appear disabled
        client.patch_twin_reported_properties(twin_patch_reported)
        assert pipeline.enable_feature.call_count == 1
        assert pipeline.enable_feature.call_args[0][0] == constant.TWIN

        pipeline.enable_feature.reset_mock()

        # Verify twin not enabled if already enabled
        pipeline.feature_enabled.__getitem__.return_value = True  # twin will appear enabled
        client.patch_twin_reported_properties(twin_patch_reported)
        assert pipeline.enable_feature.call_count == 0

    @pytest.mark.it("Begins a 'patch_twin_reported_properties' pipeline operation")
    def test_patch_twin_reported_properties_calls_pipeline(
        self, client, pipeline, twin_patch_reported
    ):
        client.patch_twin_reported_properties(twin_patch_reported)
        assert pipeline.patch_twin_reported_properties.call_count == 1
        assert pipeline.patch_twin_reported_properties.call_args[1]["patch"] is twin_patch_reported

    @pytest.mark.it(
        "Waits for the completion of the 'send_method_response' pipeline operation before returning"
    )
    def test_waits_for_pipeline_op_completion(
        self, mocker, client_manual_cb, pipeline_manual_cb, twin_patch_reported
    ):
        self.add_event_completion_checks(
            mocker=mocker, pipeline_function=pipeline_manual_cb.patch_twin_reported_properties
        )
        client_manual_cb.patch_twin_reported_properties(twin_patch_reported)


class SharedClientReceiveTwinDesiredPropertiesPatchTests(object):
    @pytest.mark.it(
        "Implicitly enables Twin desired properties patch feature if not already enabled"
    )
    def test_enables_twin_patches_only_if_not_already_enabled(self, mocker, client, pipeline):
        mocker.patch.object(
            SyncClientInbox, "get"
        )  # patch this so receive_twin_desired_properties_patch won't block

        # Verify twin patches enabled if not enabled
        pipeline.feature_enabled.__getitem__.return_value = (
            False
        )  # twin patches will appear disabled
        client.receive_twin_desired_properties_patch()
        assert pipeline.enable_feature.call_count == 1
        assert pipeline.enable_feature.call_args[0][0] == constant.TWIN_PATCHES

        pipeline.enable_feature.reset_mock()

        # Verify twin patches not enabled if already enabled
        pipeline.feature_enabled.__getitem__.return_value = True  # C2D will appear enabled
        client.receive_twin_desired_properties_patch()
        assert pipeline.enable_feature.call_count == 0

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
        "Raises InboxEmpty exception after a timeout while blocking, in blocking mode with a specified timeout"
    )
    def test_times_out_waiting_for_message_blocking_mode(self, client):
        with pytest.raises(InboxEmpty):
            client.receive_twin_desired_properties_patch(block=True, timeout=0.01)

    @pytest.mark.it(
        "Raises InboxEmpty exception immediately if there are no patches, in nonblocking mode"
    )
    def test_no_message_in_inbox_nonblocking_mode(self, client):
        with pytest.raises(InboxEmpty):
            client.receive_twin_desired_properties_patch(block=False)


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
    def client_manual_cb(self, pipeline_manual_cb):
        """This client requires manual triggering of the callbacks sent to the pipeline.
        It should only be used for tests where manual control fo a callback is required.
        """
        return IoTHubDeviceClient(pipeline_manual_cb)

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
    @pytest.mark.it("Sets on_c2d_message_received handler in pipeline")
    def test_sets_on_c2d_message_received_handler_in_pipeline(self, client):
        assert client._pipeline.on_c2d_message_received is not None
        assert client._pipeline.on_c2d_message_received == client._inbox_manager.route_c2d_message


@pytest.mark.describe("IoTHubDeviceClient (Synchronous) - .create_from_connection_string()")
class TestIoTHubDeviceClientCreateFromConnectionString(
    IoTHubDeviceClientTestsConfig, SharedClientFromCreateFromConnectionStringTests
):
    pass


@pytest.mark.describe("IoTHubDeviceClient (Synchronous) - .create_from_shared_access_signature()")
class TestIoTHubDeviceClientCreateFromSharedAccessSignature(
    IoTHubDeviceClientTestsConfig, SharedClientFromCreateFromSharedAccessSignature
):
    pass


@pytest.mark.describe("IoTHubDeviceClient (Synchronous) - .create_from_x509_certificate()")
class TestIoTHubDeviceClientCreateFromX509Certificate(
    IoTHubDeviceClientTestsConfig, SharedClientFromCreateFromX509Certificate
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


@pytest.mark.describe("IoTHubDeviceClient (Synchronous) - .send_d2c_message()")
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
    def test_returns_message_from_c2d_inbox(self, mocker, client, message):
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
    def test_no_message_in_inbox_blocking_mode(self, client, message):
        c2d_inbox = client._inbox_manager.get_c2d_message_inbox()
        assert c2d_inbox.empty()

        def insert_item_after_delay():
            time.sleep(0.01)
            c2d_inbox._put(message)

        insertion_thread = threading.Thread(target=insert_item_after_delay)
        insertion_thread.start()

        received_message = client.receive_c2d_message(block=True)
        assert received_message is message
        # This proves that the blocking happens because 'received_message' can't be
        # 'message' until after a 10 millisecond delay on the insert. But because the
        # 'received_message' IS 'message', it means that client.receive_c2d_message
        # did not return until after the delay.

    @pytest.mark.it(
        "Raises InboxEmpty exception after a timeout while blocking, in blocking mode with a specified timeout"
    )
    def test_times_out_waiting_for_message_blocking_mode(self, client):
        with pytest.raises(InboxEmpty):
            client.receive_c2d_message(block=True, timeout=0.01)

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
    @pytest.mark.it("Sets on_input_message_received handler in pipeline")
    def test_sets_on_input_message_received_handler_in_pipeline(self, client):
        assert client._pipeline.on_input_message_received is not None
        assert (
            client._pipeline.on_input_message_received == client._inbox_manager.route_input_message
        )


@pytest.mark.describe("IoTHubModuleClient (Synchronous) - .create_from_connection_string()")
class TestIoTHubModuleClientCreateFromConnectionString(
    IoTHubModuleClientTestsConfig, SharedClientFromCreateFromConnectionStringTests
):
    pass


@pytest.mark.describe("IoTHubModuleClient (Synchronous) - .create_from_shared_access_signature()")
class TestIoTHubModuleClientCreateFromSharedAccessSignature(
    IoTHubModuleClientTestsConfig, SharedClientFromCreateFromSharedAccessSignature
):
    pass


@pytest.mark.describe(
    "IoTHubModuleClient (Synchronous) - .create_from_edge_environment() -- Edge Container Environment"
)
class TestIoTHubModuleClientCreateFromEdgeEnvironmentWithContainerEnv(
    IoTHubModuleClientTestsConfig
):
    @pytest.mark.it("Instantiates the client from environment variables")
    def test_instantiates_client(self, mocker, client_class, edge_container_environment):
        mocker.patch.dict(os.environ, edge_container_environment)
        # must patch auth provider because it immediately tries to access Edge HSM
        mocker.patch("azure.iot.device.iothub.auth.IoTEdgeAuthenticationProvider")
        client = client_class.create_from_edge_environment()
        assert isinstance(client, client_class)

    @pytest.mark.it("Uses an IoTEdgeAuthenticationProvider to create the client's IoTHub pipeline")
    def test_auth_provider_and_pipeline(self, mocker, client_class, edge_container_environment):
        mocker.patch.dict(os.environ, edge_container_environment)
        mock_auth_init = mocker.patch("azure.iot.device.iothub.auth.IoTEdgeAuthenticationProvider")
        mock_pipeline_init = mocker.patch("azure.iot.device.iothub.abstract_clients.IoTHubPipeline")

        client = client_class.create_from_edge_environment()

        assert mock_auth_init.call_count == 1
        assert mock_pipeline_init.call_count == 1
        assert mock_pipeline_init.call_args == mocker.call(mock_auth_init.return_value)
        assert client._pipeline == mock_pipeline_init.return_value

    @pytest.mark.it(
        "Ignores any Edge local debug environment variables that may be present, in favor of using Edge container variables"
    )
    def test_auth_provider_and_pipeline_hybrid_env(
        self, mocker, client_class, edge_container_environment, edge_local_debug_environment
    ):
        # This test verifies that with a hybrid environment, the auth provider will always be
        # an IoTEdgeAuthenticationProvider, even if local debug variables are present
        hybrid_environment = merge_dicts(edge_container_environment, edge_local_debug_environment)
        mocker.patch.dict(os.environ, hybrid_environment)
        mock_auth_init = mocker.patch("azure.iot.device.iothub.auth.IoTEdgeAuthenticationProvider")
        mock_pipeline_init = mocker.patch("azure.iot.device.iothub.abstract_clients.IoTHubPipeline")

        client = client_class.create_from_edge_environment()

        assert mock_auth_init.call_count == 1
        assert mock_pipeline_init.call_count == 1
        assert mock_pipeline_init.call_args == mocker.call(mock_auth_init.return_value)
        assert client._pipeline == mock_pipeline_init.return_value

    @pytest.mark.it("Raises IoTEdgeError if the environment is missing required variables")
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

        with pytest.raises(IoTEdgeError):
            client_class.create_from_edge_environment()

    @pytest.mark.it("Raises IoTEdgeError if there is an error using the Edge for authentication")
    def test_bad_edge_auth(self, mocker, client_class, edge_container_environment):
        mocker.patch.dict(os.environ, edge_container_environment)
        mock_auth = mocker.patch("azure.iot.device.iothub.auth.IoTEdgeAuthenticationProvider")
        mock_auth.side_effect = IoTEdgeError

        with pytest.raises(IoTEdgeError):
            client_class.create_from_edge_environment()


@pytest.mark.describe(
    "IoTHubModuleClient (Synchronous) - .create_from_edge_environment() -- Edge Local Debug Environment"
)
class TestIoTHubModuleClientCreateFromEdgeEnvironmentWithDebugEnv(IoTHubModuleClientTestsConfig):
    @pytest.fixture
    def mock_open(self, mocker):
        return mocker.patch.object(io, "open")

    @pytest.mark.it("Instantiates the client from environment variables")
    def test_instantiates_client(
        self, mocker, client_class, edge_local_debug_environment, mock_open
    ):
        mocker.patch.dict(os.environ, edge_local_debug_environment)
        client = client_class.create_from_edge_environment()
        assert isinstance(client, client_class)

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
        "Uses a SymmetricKeyAuthenticationProvider (with CA cert) to create the client's IoTHub pipeline"
    )
    def test_auth_provider_and_pipeline(
        self, mocker, client_class, edge_local_debug_environment, mock_open
    ):
        expected_cert = mock_open.return_value.__enter__.return_value.read.return_value
        mocker.patch.dict(os.environ, edge_local_debug_environment)
        mock_auth_parse = mocker.patch(
            "azure.iot.device.iothub.auth.SymmetricKeyAuthenticationProvider"
        ).parse
        mock_auth = mock_auth_parse.return_value
        mock_pipeline_init = mocker.patch("azure.iot.device.iothub.abstract_clients.IoTHubPipeline")

        client = client_class.create_from_edge_environment()

        assert mock_auth_parse.call_count == 1
        assert mock_auth_parse.call_args == mocker.call(
            edge_local_debug_environment["EdgeHubConnectionString"]
        )
        assert mock_auth.ca_cert == expected_cert
        assert mock_pipeline_init.call_count == 1
        assert mock_pipeline_init.call_args == mocker.call(mock_auth)
        assert client._pipeline == mock_pipeline_init.return_value

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
        mock_auth_init = mocker.patch("azure.iot.device.iothub.auth.IoTEdgeAuthenticationProvider")
        mock_pipeline_init = mocker.patch("azure.iot.device.iothub.abstract_clients.IoTHubPipeline")

        client = client_class.create_from_edge_environment()

        assert mock_auth_init.call_count == 1
        assert mock_pipeline_init.call_count == 1
        assert mock_pipeline_init.call_args == mocker.call(mock_auth_init.return_value)
        assert client._pipeline == mock_pipeline_init.return_value

    @pytest.mark.it("Raises IoTEdgeError if the environment is missing required variables")
    @pytest.mark.parametrize(
        "missing_env_var", ["EdgeHubConnectionString", "EdgeModuleCACertificateFile"]
    )
    def test_bad_environment(
        self, mocker, client_class, edge_local_debug_environment, missing_env_var, mock_open
    ):
        # Remove a variable from the fixture
        del edge_local_debug_environment[missing_env_var]
        mocker.patch.dict(os.environ, edge_local_debug_environment)

        with pytest.raises(IoTEdgeError):
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
        mock_open.side_effect = FileNotFoundError
        with pytest.raises(ValueError):
            client_class.create_from_edge_environment()

    @pytest.mark.it(
        "Raises ValueError if the file referenced by the filepath in the EdgeModuleCACertificateFile environment variable cannot be opened"
    )
    def test_bad_file_io(self, mocker, client_class, edge_local_debug_environment, mock_open):
        # Raise a different error in Python 2 vs 3
        if six.PY2:
            error = IOError
        else:
            error = OSError
        mocker.patch.dict(os.environ, edge_local_debug_environment)
        mock_open.side_effect = error
        with pytest.raises(ValueError):
            client_class.create_from_edge_environment()


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


@pytest.mark.describe("IoTHubModuleClient (Synchronous) - .send_d2c_message()")
class TestIoTHubNModuleClientSendEvent(IoTHubModuleClientTestsConfig, SharedClientSendEventTests):
    pass


@pytest.mark.describe("IoTHubModuleClient (Synchronous) - .send_to_output()")
class TestIoTHubModuleClientSendToOutput(IoTHubModuleClientTestsConfig, WaitsForEventCompletion):
    @pytest.mark.it("Begins a 'send_output_event' pipeline operation")
    def test_calls_pipeline_send_to_output(self, client, pipeline, message):
        output_name = "some_output"
        client.send_to_output(message, output_name)
        assert pipeline.send_output_event.call_count == 1
        assert pipeline.send_output_event.call_args[0][0] is message
        assert message.output_name == output_name

    @pytest.mark.it(
        "Waits for the completion of the 'send_output_event' pipeline operation before returning"
    )
    def test_waits_for_pipeline_op_completion(
        self, mocker, client_manual_cb, pipeline_manual_cb, message
    ):
        self.add_event_completion_checks(
            mocker=mocker, pipeline_function=pipeline_manual_cb.send_output_event
        )
        output_name = "some_output"
        client_manual_cb.send_to_output(message, output_name)

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
    def test_returns_message_from_input_inbox(self, mocker, client, message):
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
    def test_no_message_in_inbox_blocking_mode(self, client, message):
        input_name = "some_input"

        input_inbox = client._inbox_manager.get_input_message_inbox(input_name)
        assert input_inbox.empty()

        def insert_item_after_delay():
            time.sleep(0.01)
            input_inbox._put(message)

        insertion_thread = threading.Thread(target=insert_item_after_delay)
        insertion_thread.start()

        received_message = client.receive_input_message(input_name, block=True)
        assert received_message is message
        # This proves that the blocking happens because 'received_message' can't be
        # 'message' until after a 10 millisecond delay on the insert. But because the
        # 'received_message' IS 'message', it means that client.receive_input_message
        # did not return until after the delay.

    @pytest.mark.it(
        "Raises InboxEmpty exception after a timeout while blocking, in blocking mode with a specified timeout"
    )
    def test_times_out_waiting_for_message_blocking_mode(self, client):
        input_name = "some_input"
        with pytest.raises(InboxEmpty):
            client.receive_input_message(input_name, block=True, timeout=0.01)

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
