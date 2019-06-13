# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import logging
import pytest
from azure.iot.device.common.pipeline import (
    pipeline_ops_base,
    pipeline_stages_base,
    pipeline_ops_mqtt,
    pipeline_events_mqtt,
    pipeline_stages_mqtt,
)
from tests.common.pipeline.helpers import (
    assert_default_stage_attributes,
    assert_callback_failed,
    assert_callback_succeeded,
    all_common_ops,
    all_common_events,
    all_except,
    UnhandledException,
)
from tests.iothub.pipeline.helpers import all_iothub_ops, all_iothub_events

logging.basicConfig(level=logging.INFO)

fake_client_id = "__fake_client_id__"
fake_hostname = "__fake_hostname__"
fake_username = "__fake_username__"
fake_ca_cert = "__fake_ca_cert__"
fake_sas_token = "__fake_sas_token__"
fake_topic = "__fake_topic__"
fake_payload = "__fake_payload__"
fake_certificate = "__fake_certificate__"

ops_handled_by_this_stage = [
    pipeline_ops_base.SetSasToken,
    pipeline_ops_base.Connect,
    pipeline_ops_base.Disconnect,
    pipeline_ops_base.Reconnect,
    pipeline_ops_mqtt.SetConnectionArgs,
    pipeline_ops_mqtt.Publish,
    pipeline_ops_mqtt.Subscribe,
    pipeline_ops_mqtt.Unsubscribe,
]

unknown_ops = all_except(
    all_items=(all_common_ops + all_iothub_ops), items_to_exclude=ops_handled_by_this_stage
)

events_handled_by_this_stage = []

unknown_events = all_except(
    all_items=all_common_events + all_iothub_events, items_to_exclude=events_handled_by_this_stage
)


@pytest.fixture
def stage(mocker):
    stage = pipeline_stages_mqtt.Provider()
    root = pipeline_stages_base.PipelineRoot()

    stage.previous = root
    root.next = stage
    stage.pipeline_root = root

    mocker.spy(root, "handle_pipeline_event")
    mocker.spy(stage, "on_connected")
    mocker.spy(stage, "on_disconnected")

    return stage


@pytest.mark.describe("MQTT Provider pipeline stage initializer")
class TestMQTTProviderInitializer(object):
    @pytest.mark.it("Sets name attribute on instantiation")
    @pytest.mark.it("Sets next attribute to None on instantiation")
    @pytest.mark.it("Sets previous attribute to None on instantiation")
    @pytest.mark.it("Sets pipeline_root attribute to None on instantiation")
    def test_initializer(self):
        obj = pipeline_stages_mqtt.Provider()
        assert_default_stage_attributes(obj)


@pytest.mark.describe("MQTT Provider pipeline stage _runOp function with unhandled operations")
class TestMQTTProviderRunOpWithUnknownOperations(object):
    @pytest.mark.parametrize(
        "op_class,init_args", unknown_ops, ids=[x[0].__name__ for x in unknown_ops]
    )
    @pytest.mark.it("fails all unknown operations")
    def test_fails_unknown_op(self, mocker, callback, stage, op_class, init_args):
        op = op_class(*init_args, callback=callback)
        stage.run_op(op)
        assert callback.call_count == 1
        callback_arg = callback.call_args[0][0]
        assert callback_arg == op
        assert isinstance(op.error, NotImplementedError)


@pytest.mark.describe("MQTT Provider pipeline stage _handle_pipeline_event")
class TestMQTTProviderHandlePipelineEvent(object):
    @pytest.mark.parametrize(
        "event_class,event_init_args", unknown_events, ids=[x[0].__name__ for x in unknown_events]
    )
    @pytest.mark.it("passes all events up to the previous stage")
    def test_all_events_get_passed_up(self, stage, mocker, event_class, event_init_args):
        event = event_class(*event_init_args)
        stage.handle_pipeline_event(event)
        assert stage.previous.handle_pipeline_event.call_count == 1
        assert stage.previous.handle_pipeline_event.call_args == mocker.call(event)


@pytest.fixture
def provider(mocker):
    mocker.patch(
        "azure.iot.device.common.pipeline.pipeline_stages_mqtt.MQTTProvider", autospec=True
    )
    return pipeline_stages_mqtt.MQTTProvider


@pytest.fixture
def op_set_connection_args(callback):
    return pipeline_ops_mqtt.SetConnectionArgs(
        client_id=fake_client_id,
        hostname=fake_hostname,
        username=fake_username,
        ca_cert=fake_ca_cert,
        callback=callback,
    )


@pytest.mark.describe(
    "MQTT Provider pipeline stage _runOp function with SetConnectionArgs operations"
)
class TestMQTTProviderRunOpWithSetConnectionArgs(object):
    @pytest.mark.it("Creates an MQTTProvider object")
    def test_creates_provider(self, stage, provider, op_set_connection_args):
        stage.run_op(op_set_connection_args)
        assert provider.call_count == 1

    @pytest.mark.it(
        "initializes the MQTTProvier object with the passed client_id, hostname, username, and ca_cert"
    )
    def test_passes_right_params(self, stage, provider, mocker, op_set_connection_args):
        stage.run_op(op_set_connection_args)
        assert provider.call_args == mocker.call(
            client_id=fake_client_id,
            hostname=fake_hostname,
            username=fake_username,
            ca_cert=fake_ca_cert,
        )

    @pytest.mark.it(
        "sets on_mqtt_connected, on_mqtt_disconnected, and on_mqtt_messsage_received on the transport"
    )
    def test_sets_parameters(self, stage, provider, mocker, op_set_connection_args):
        stage.run_op(op_set_connection_args)
        assert provider.return_value.on_mqtt_disconnected == stage.on_disconnected
        assert provider.return_value.on_mqtt_connected == stage.on_connected
        assert provider.return_value.on_mqtt_message_received == stage._on_message_received

    @pytest.mark.it("sets the provider attribute on the root of the pipeline")
    def test_sets_provider_attribute_on_root(self, stage, provider, op_set_connection_args):
        stage.run_op(op_set_connection_args)
        assert stage.previous.provider == provider.return_value

    @pytest.mark.it("Completes with success if no exception")
    def test_succeeds(self, stage, provider, op_set_connection_args):
        stage.run_op(op_set_connection_args)
        assert_callback_succeeded(op=op_set_connection_args)

    @pytest.mark.it("Completes with failure on exception")
    def test_fails_on_exception(self, stage, provider, op_set_connection_args, mocker):
        provider.return_value = None
        stage.run_op(op_set_connection_args)
        assert_callback_failed(op=op_set_connection_args)


@pytest.fixture
def op_set_sas_token(callback):
    return pipeline_ops_base.SetSasToken(sas_token=fake_sas_token, callback=callback)


@pytest.fixture
def op_set_client_certificate(callback):
    return pipeline_ops_base.SetClientAuthenticationCertificate(certificate=fake_certificate)


@pytest.mark.describe("MQTT Provider pipeline stage _runOp function with SetSasToken operations")
class TestMQTTProviderRunOpWithSetSasToken(object):
    @pytest.mark.it("saves the sas token")
    def test_saves_sas_token(self, stage, op_set_sas_token):
        stage.run_op(op_set_sas_token)
        assert stage.sas_token == fake_sas_token

    @pytest.mark.it("completes with success")
    def test_succeeds(self, stage, op_set_sas_token):
        stage.run_op(op_set_sas_token)
        assert_callback_succeeded(op=op_set_sas_token)


@pytest.fixture
def create_provider(
    stage, provider, op_set_connection_args, op_set_sas_token, op_set_client_certificate
):
    stage.run_op(op_set_connection_args)
    stage.run_op(op_set_sas_token)
    stage.run_op(op_set_client_certificate)


connection_ops = [
    pytest.param(
        {
            "op_class": pipeline_ops_base.Connect,
            "op_init_kwargs": {},
            "provider_function": "connect",
            "provider_kwargs": {},
            "provider_handler": "on_mqtt_connected",
        },
        id="Connect",
    ),
    pytest.param(
        {
            "op_class": pipeline_ops_base.Disconnect,
            "op_init_kwargs": {},
            "provider_function": "disconnect",
            "provider_kwargs": {},
            "provider_handler": "on_mqtt_disconnected",
        },
        id="Disconnect",
    ),
    pytest.param(
        {
            "op_class": pipeline_ops_base.Reconnect,
            "op_init_kwargs": {},
            "provider_function": "reconnect",
            "provider_kwargs": {},
            "provider_handler": "on_mqtt_connected",
        },
        id="Reconnect",
    ),
]

pubsub_ops = [
    pytest.param(
        {
            "op_class": pipeline_ops_mqtt.Publish,
            "op_init_kwargs": {"topic": fake_topic, "payload": fake_payload},
            "provider_function": "publish",
            "provider_kwargs": {"topic": fake_topic, "payload": fake_payload},
        },
        id="Publish",
    ),
    pytest.param(
        {
            "op_class": pipeline_ops_mqtt.Subscribe,
            "op_init_kwargs": {"topic": fake_topic},
            "provider_function": "subscribe",
            "provider_kwargs": {"topic": fake_topic},
        },
        id="Subscribe",
    ),
    pytest.param(
        {
            "op_class": pipeline_ops_mqtt.Unsubscribe,
            "op_init_kwargs": {"topic": fake_topic},
            "provider_function": "unsubscribe",
            "provider_kwargs": {"topic": fake_topic},
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
def provider_function_succeeds(params, stage):
    def fake_provider_function(*args, **kwargs):
        if "callback" in kwargs:
            kwargs["callback"]()
        elif "provider_handler" in params:
            getattr(stage.provider, params["provider_handler"])()
        else:
            assert False

    setattr(stage.provider, params["provider_function"], fake_provider_function)


@pytest.fixture
def provider_function_throws_exception(params, stage, mocker, fake_exception):
    setattr(stage.provider, params["provider_function"], mocker.Mock(side_effect=fake_exception))


@pytest.fixture
def provider_function_throws_base_exception(params, stage, mocker, fake_base_exception):
    setattr(
        stage.provider, params["provider_function"], mocker.Mock(side_effect=fake_base_exception)
    )


@pytest.mark.parametrize("params", connection_ops + pubsub_ops)
@pytest.mark.describe(
    "MQTT Provider pipeline stage _run_op with ops that map directly to provider libraray calls"
)
class TestMQTTProviderBasicFunctionality(object):
    @pytest.mark.it("calls the appropriate function on the provider library")
    def test_calls_provider_function(self, stage, create_provider, params, op):
        stage.run_op(op)
        assert getattr(stage.provider, params["provider_function"]).call_count == 1

    @pytest.mark.it("passes the correct args to the provider function")
    def test_passes_correct_args_to_provider_function(self, stage, create_provider, params, op):
        stage.run_op(op)
        args = getattr(stage.provider, params["provider_function"]).call_args
        for name in params["provider_kwargs"]:
            assert args[1][name] == params["provider_kwargs"][name]

    @pytest.mark.it("returns success after the provider completes the operation")
    def test_succeeds(self, stage, create_provider, params, op, provider_function_succeeds):
        op.callback.reset_mock()
        stage.run_op(op)
        assert_callback_succeeded(op=op)

    @pytest.mark.it("returns failure if there is an Exception in the provider function")
    def test_provider_function_throws_exception(
        self, stage, create_provider, params, fake_exception, op, provider_function_throws_exception
    ):
        op.callback.reset_mock()
        stage.run_op(op)
        assert_callback_failed(op=op, error=fake_exception)

    @pytest.mark.it("Allows any BaseException raised by the provider function to propagate")
    def test_provider_function_throws_base_exception(
        self, stage, create_provider, params, op, provider_function_throws_base_exception
    ):
        op.callback.reset_mock()
        with pytest.raises(UnhandledException):
            stage.run_op(op)


@pytest.mark.parametrize("params", connection_ops)
@pytest.mark.describe("MQTT Provider pipeline stage _runOp function with Connect operations")
class TestMQTTProviderRunOpWithConnect(object):
    @pytest.mark.it("calls connected/disconnected event handler after provider function succeeds")
    def test_calls_handler_on_success(
        self, params, stage, create_provider, op, provider_function_succeeds
    ):
        stage.run_op(op)
        assert getattr(stage.provider, params["provider_handler"]).call_count == 1

    @pytest.mark.it("restores provider handler after provider function succeeds")
    def test_restores_handler_on_success(
        self, params, stage, create_provider, op, provider_function_succeeds
    ):
        handler_before = getattr(stage.provider, params["provider_handler"])
        stage.run_op(op)
        handler_after = getattr(stage.provider, params["provider_handler"])
        assert handler_before == handler_after

    @pytest.mark.it(
        "does not call connected/disconnected handler if there is an Exception in the provider function"
    )
    def test_provider_function_throws_exception(
        self,
        params,
        stage,
        create_provider,
        op,
        mocker,
        fake_exception,
        provider_function_throws_exception,
    ):
        stage.run_op(op)
        assert getattr(stage.provider, params["provider_handler"]).call_count == 0

    @pytest.mark.it("restores provider handler if there is an Exception in the provider function")
    def test_provider_function_throws_exception_2(
        self,
        params,
        stage,
        create_provider,
        op,
        mocker,
        fake_exception,
        provider_function_throws_exception,
    ):
        handler_before = getattr(stage.provider, params["provider_handler"])
        stage.run_op(op)
        handler_after = getattr(stage.provider, params["provider_handler"])
        assert handler_before == handler_after


@pytest.mark.describe("MQTT Provider pipeline stage events from transport library")
class TestMQTTProviderTransportEvents(object):
    @pytest.mark.it("fires an IncomingMessage event for each mqtt message received")
    def test_incoming_message_handler(self, stage, create_provider, mocker):
        stage.provider.on_mqtt_message_received(topic=fake_topic, payload=fake_payload)
        assert stage.previous.handle_pipeline_event.call_count == 1
        call_arg = stage.previous.handle_pipeline_event.call_args[0][0]
        assert isinstance(call_arg, pipeline_events_mqtt.IncomingMessage)

    @pytest.mark.it("passes topic and payload as part of the IncomingMessage event")
    def test_verify_incoming_message_attributes(self, stage, create_provider, mocker):
        stage.provider.on_mqtt_message_received(topic=fake_topic, payload=fake_payload)
        call_arg = stage.previous.handle_pipeline_event.call_args[0][0]
        assert call_arg.payload == fake_payload
        assert call_arg.topic == fake_topic

    @pytest.mark.it(
        "calls self.on_connected and passes it up when the transport connected event fires"
    )
    def test_connected_handler(self, stage, create_provider, mocker):
        mocker.spy(stage.previous, "on_connected")
        assert stage.previous.on_connected.call_count == 0
        stage.provider.on_mqtt_connected()
        assert stage.previous.on_connected.call_count == 1

    @pytest.mark.it(
        "calls self.on_disconnected and passes it up when the transport disconnected event fires"
    )
    def test_disconnected_hanlder(self, stage, create_provider, mocker):
        mocker.spy(stage.previous, "on_disconnected")
        assert stage.previous.on_disconnected.call_count == 0
        stage.provider.on_mqtt_disconnected()
        assert stage.previous.on_disconnected.call_count == 1
