# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import logging
import pytest
import sys
from azure.iot.device.common.pipeline import (
    pipeline_ops_base,
    pipeline_stages_base,
    pipeline_ops_mqtt,
    pipeline_events_mqtt,
    pipeline_stages_mqtt,
)
from tests.common.pipeline.helpers import (
    assert_callback_failed,
    assert_callback_succeeded,
    all_common_ops,
    all_common_events,
    all_except,
    UnhandledException,
)
from tests.common.pipeline import pipeline_stage_test

logging.basicConfig(level=logging.INFO)


# This fixture makes it look like all test in this file  tests are running
# inside the pipeline thread.  Because this is an autouse fixture, we
# manually add it to the individual test.py files that need it.  If,
# instead, we had added it to some conftest.py, it would be applied to
# every tests in every file and we don't want that.
@pytest.fixture(autouse=True)
def apply_fake_pipeline_thread(fake_pipeline_thread):
    pass


this_module = sys.modules[__name__]

fake_client_id = "__fake_client_id__"
fake_hostname = "__fake_hostname__"
fake_username = "__fake_username__"
fake_ca_cert = "__fake_ca_cert__"
fake_sas_token = "__fake_sas_token__"
fake_topic = "__fake_topic__"
fake_payload = "__fake_payload__"
fake_certificate = "__fake_certificate__"

ops_handled_by_this_stage = [
    pipeline_ops_base.ConnectOperation,
    pipeline_ops_base.DisconnectOperation,
    pipeline_ops_base.ReconnectOperation,
    pipeline_ops_mqtt.SetMQTTConnectionArgsOperation,
    pipeline_ops_mqtt.MQTTPublishOperation,
    pipeline_ops_mqtt.MQTTSubscribeOperation,
    pipeline_ops_mqtt.MQTTUnsubscribeOperation,
]

events_handled_by_this_stage = []


pipeline_stage_test.add_base_pipeline_stage_tests(
    cls=pipeline_stages_mqtt.MQTTTransportStage,
    module=this_module,
    all_ops=all_common_ops,
    handled_ops=ops_handled_by_this_stage,
    all_events=all_common_events,
    handled_events=events_handled_by_this_stage,
    methods_that_enter_pipeline_thread=["_on_message_received", "on_connected", "on_disconnected"],
)


@pytest.fixture
def stage(mocker):
    stage = pipeline_stages_mqtt.MQTTTransportStage()
    root = pipeline_stages_base.PipelineRootStage()

    stage.previous = root
    root.next = stage
    stage.pipeline_root = root

    mocker.spy(root, "handle_pipeline_event")
    mocker.spy(stage, "on_connected")
    mocker.spy(stage, "on_disconnected")

    return stage


@pytest.fixture
def transport(mocker):
    mocker.patch(
        "azure.iot.device.common.pipeline.pipeline_stages_mqtt.MQTTTransport", autospec=True
    )
    return pipeline_stages_mqtt.MQTTTransport


@pytest.fixture
def op_set_connection_args(callback):
    return pipeline_ops_mqtt.SetMQTTConnectionArgsOperation(
        client_id=fake_client_id,
        hostname=fake_hostname,
        username=fake_username,
        ca_cert=fake_ca_cert,
        callback=callback,
    )


@pytest.mark.describe(
    "MQTTTransportStage - .run_op() -- called with pipeline_ops_mqtt.SetMQTTConnectionArgsOperation"
)
class TestMQTTProviderRunOpWithSetConnectionArgs(object):
    @pytest.mark.it("Creates an MQTTTransport object")
    def test_creates_transport(self, stage, transport, op_set_connection_args):
        stage.run_op(op_set_connection_args)
        assert transport.call_count == 1

    # TODO: add client_cert and sas_token tests here
    @pytest.mark.it(
        "Initializes the MQTTProvier object with the passed client_id, hostname, username, and ca_cert"
    )
    def test_passes_right_params(self, stage, transport, mocker, op_set_connection_args):
        stage.run_op(op_set_connection_args)
        assert transport.call_args == mocker.call(
            client_id=fake_client_id,
            hostname=fake_hostname,
            username=fake_username,
            ca_cert=fake_ca_cert,
        )

    @pytest.mark.it(
        "Sets on_mqtt_connected, on_mqtt_disconnected, and on_mqtt_messsage_received on the protocol client library"
    )
    def test_sets_parameters(self, stage, transport, mocker, op_set_connection_args):
        stage.run_op(op_set_connection_args)
        assert transport.return_value.on_mqtt_disconnected == stage.on_disconnected
        assert transport.return_value.on_mqtt_connected == stage.on_connected
        assert transport.return_value.on_mqtt_message_received == stage._on_message_received

    @pytest.mark.it("Sets the transport attribute on the root of the pipeline")
    def test_sets_transport_attribute_on_root(self, stage, transport, op_set_connection_args):
        stage.run_op(op_set_connection_args)
        assert stage.previous.transport == transport.return_value

    @pytest.mark.it("Completes with success if no exception")
    def test_succeeds(self, stage, transport, op_set_connection_args):
        stage.run_op(op_set_connection_args)
        assert_callback_succeeded(op=op_set_connection_args)

    @pytest.mark.it("Completes with failure on exception")
    def test_fails_on_exception(self, stage, transport, op_set_connection_args, mocker):
        transport.return_value = None
        stage.run_op(op_set_connection_args)
        assert_callback_failed(op=op_set_connection_args)


@pytest.fixture
def create_transport(stage, transport, op_set_connection_args):
    stage.run_op(op_set_connection_args)


connection_ops = [
    pytest.param(
        {
            "op_class": pipeline_ops_base.ConnectOperation,
            "op_init_kwargs": {},
            "transport_function": "connect",
            "transport_kwargs": {},
            "transport_handler": "on_mqtt_connected",
        },
        id="ConnectOperation",
    ),
    pytest.param(
        {
            "op_class": pipeline_ops_base.DisconnectOperation,
            "op_init_kwargs": {},
            "transport_function": "disconnect",
            "transport_kwargs": {},
            "transport_handler": "on_mqtt_disconnected",
        },
        id="Disconnect",
    ),
    pytest.param(
        {
            "op_class": pipeline_ops_base.ReconnectOperation,
            "op_init_kwargs": {},
            "transport_function": "reconnect",
            "transport_kwargs": {},
            "transport_handler": "on_mqtt_connected",
        },
        id="Reconnect",
    ),
]

pubsub_ops = [
    pytest.param(
        {
            "op_class": pipeline_ops_mqtt.MQTTPublishOperation,
            "op_init_kwargs": {"topic": fake_topic, "payload": fake_payload},
            "transport_function": "publish",
            "transport_kwargs": {"topic": fake_topic, "payload": fake_payload},
        },
        id="Publish",
    ),
    pytest.param(
        {
            "op_class": pipeline_ops_mqtt.MQTTSubscribeOperation,
            "op_init_kwargs": {"topic": fake_topic},
            "transport_function": "subscribe",
            "transport_kwargs": {"topic": fake_topic},
        },
        id="Subscribe",
    ),
    pytest.param(
        {
            "op_class": pipeline_ops_mqtt.MQTTUnsubscribeOperation,
            "op_init_kwargs": {"topic": fake_topic},
            "transport_function": "unsubscribe",
            "transport_kwargs": {"topic": fake_topic},
        },
        id="Unsubscribe",
    ),
]


@pytest.fixture
def op(params, callback):
    op = params["op_class"](**params["op_init_kwargs"])
    op.callback = callback
    return op


@pytest.fixture
def transport_function_succeeds(params, stage):
    def fake_transport_function(*args, **kwargs):
        if "callback" in kwargs:
            kwargs["callback"]()
        elif "transport_handler" in params:
            getattr(stage.transport, params["transport_handler"])()
        else:
            assert False

    setattr(stage.transport, params["transport_function"], fake_transport_function)


@pytest.fixture
def transport_function_throws_exception(params, stage, mocker, fake_exception):
    setattr(stage.transport, params["transport_function"], mocker.Mock(side_effect=fake_exception))


@pytest.fixture
def transport_function_throws_base_exception(params, stage, mocker, fake_base_exception):
    setattr(
        stage.transport, params["transport_function"], mocker.Mock(side_effect=fake_base_exception)
    )


@pytest.mark.parametrize("params", connection_ops + pubsub_ops)
@pytest.mark.describe(
    "MQTTTransportStage - .run_op() -- called with op that maps directly to protocol client library calls"
)
class TestMQTTProviderBasicFunctionality(object):
    @pytest.mark.it("Calls the appropriate function on the protocol client library")
    def test_calls_transport_function(self, stage, create_transport, params, op):
        stage.run_op(op)
        assert getattr(stage.transport, params["transport_function"]).call_count == 1

    @pytest.mark.it("Passes the correct args to the protocol client library function")
    def test_passes_correct_args_to_transport_function(self, stage, create_transport, params, op):
        stage.run_op(op)
        args = getattr(stage.transport, params["transport_function"]).call_args
        for name in params["transport_kwargs"]:
            assert args[1][name] == params["transport_kwargs"][name]

    @pytest.mark.it("Returns success after the protocol client library completes the operation")
    def test_succeeds(self, stage, create_transport, params, op, transport_function_succeeds):
        op.callback.reset_mock()
        stage.run_op(op)
        assert_callback_succeeded(op=op)

    @pytest.mark.it(
        "Returns failure if there is an Exception in the protocol client library function"
    )
    def test_transport_function_throws_exception(
        self,
        stage,
        create_transport,
        params,
        fake_exception,
        op,
        transport_function_throws_exception,
    ):
        op.callback.reset_mock()
        stage.run_op(op)
        assert_callback_failed(op=op, error=fake_exception)

    @pytest.mark.it(
        "Allows any BaseException raised by the protocol client library function to propagate"
    )
    def test_transport_function_throws_base_exception(
        self, stage, create_transport, params, op, transport_function_throws_base_exception
    ):
        op.callback.reset_mock()
        with pytest.raises(UnhandledException):
            stage.run_op(op)


@pytest.mark.parametrize("params", connection_ops)
@pytest.mark.describe(
    "MQTTTransportStage - .run_op() -- called with op that connects, disconnects, or reconnects"
)
class TestMQTTProviderRunOpWithConnect(object):
    @pytest.mark.it(
        "Calls connected/disconnected event handler after the protocol client library function succeeds"
    )
    def test_calls_handler_on_success(
        self, params, stage, create_transport, op, transport_function_succeeds
    ):
        stage.run_op(op)
        assert getattr(stage.transport, params["transport_handler"]).call_count == 1

    @pytest.mark.it("Restores transport handler after protocol client library function succeeds")
    def test_restores_handler_on_success(
        self, params, stage, create_transport, op, transport_function_succeeds
    ):
        handler_before = getattr(stage.transport, params["transport_handler"])
        stage.run_op(op)
        handler_after = getattr(stage.transport, params["transport_handler"])
        assert handler_before == handler_after

    @pytest.mark.it(
        "Does not call connected/disconnected handler if there is an Exception in the protocol client library function"
    )
    def test_transport_function_throws_exception(
        self,
        params,
        stage,
        create_transport,
        op,
        mocker,
        fake_exception,
        transport_function_throws_exception,
    ):
        stage.run_op(op)
        assert getattr(stage.transport, params["transport_handler"]).call_count == 0

    @pytest.mark.it(
        "Restores transport handler if there is an Exception in the protocol client library function"
    )
    def test_transport_function_throws_exception_2(
        self,
        params,
        stage,
        create_transport,
        op,
        mocker,
        fake_exception,
        transport_function_throws_exception,
    ):
        handler_before = getattr(stage.transport, params["transport_handler"])
        stage.run_op(op)
        handler_after = getattr(stage.transport, params["transport_handler"])
        assert handler_before == handler_after


@pytest.mark.describe("MQTTTransportStage - EVENT: MQTT message received")
class TestMQTTProviderProtocolClientEvents(object):
    @pytest.mark.it("Fires an IncomingMQTTMessageEvent event for each MQTT message received")
    def test_incoming_message_handler(self, stage, create_transport, mocker):
        stage.transport.on_mqtt_message_received(topic=fake_topic, payload=fake_payload)
        assert stage.previous.handle_pipeline_event.call_count == 1
        call_arg = stage.previous.handle_pipeline_event.call_args[0][0]
        assert isinstance(call_arg, pipeline_events_mqtt.IncomingMQTTMessageEvent)

    @pytest.mark.it("Passes topic and payload as part of the IncomingMQTTMessageEvent event")
    def test_verify_incoming_message_attributes(self, stage, create_transport, mocker):
        stage.transport.on_mqtt_message_received(topic=fake_topic, payload=fake_payload)
        call_arg = stage.previous.handle_pipeline_event.call_args[0][0]
        assert call_arg.payload == fake_payload
        assert call_arg.topic == fake_topic


@pytest.mark.describe("MQTTTransportStage - EVENT: MQTT connected")
class TestMQTTProviderOnConnected(object):
    @pytest.mark.it(
        "Calls self.on_connected and passes it up when the client library connected event fires"
    )
    def test_connected_handler(self, stage, create_transport, mocker):
        mocker.spy(stage.previous, "on_connected")
        assert stage.previous.on_connected.call_count == 0
        stage.transport.on_mqtt_connected()
        assert stage.previous.on_connected.call_count == 1


@pytest.mark.describe("MQTTTransportStage - EVENT: MQTT disconencted")
class TestMQTTProviderOnDisconnected(object):
    @pytest.mark.it(
        "Calls self.on_disconnected and passes it up when the client library disconnected event fires"
    )
    def test_disconnected_handler(self, stage, create_transport, mocker):
        mocker.spy(stage.previous, "on_disconnected")
        assert stage.previous.on_disconnected.call_count == 0
        stage.transport.on_mqtt_disconnected()
        assert stage.previous.on_disconnected.call_count == 1
