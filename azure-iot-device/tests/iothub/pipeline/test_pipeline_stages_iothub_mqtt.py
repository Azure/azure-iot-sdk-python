# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import logging
import pytest
import json
import sys
from azure.iot.device.common.pipeline import (
    pipeline_ops_base,
    pipeline_stages_base,
    pipeline_ops_mqtt,
    pipeline_events_mqtt,
)
from azure.iot.device.iothub.pipeline import (
    constant,
    pipeline_events_iothub,
    pipeline_ops_iothub,
    pipeline_stages_iothub_mqtt,
)
from azure.iot.device.iothub.models.message import Message
from azure.iot.device.iothub.models.methods import MethodRequest, MethodResponse
from tests.common.pipeline.helpers import (
    assert_callback_failed,
    assert_callback_succeeded,
    all_common_ops,
    all_common_events,
    all_except,
    make_mock_stage,
    UnhandledException,
)
from tests.iothub.pipeline.helpers import all_iothub_ops, all_iothub_events
from tests.common.pipeline import pipeline_stage_test

logging.basicConfig(level=logging.INFO)

this_module = sys.modules[__name__]

fake_device_id = "__fake_device_id__"
fake_module_id = "__fake_module_id__"
fake_hostname = "__fake_hostname__"
fake_gateway_hostname = "__fake_gateway_hostname__"
fake_ca_cert = "__fake_ca_cert__"

fake_message_body = "__fake_message_body__"
fake_output_name = "__fake_output_name__"
fake_content_type = "text/json"
fake_content_type_encoded = "%24.ct=text%2Fjson"
fake_message = Message(fake_message_body)

fake_request_id = "__fake_request_id__"
fake_method_name = "__fake_method_name__"
fake_method_payload = "__fake_method_payload__"
fake_method_status = "__fake_method_status__"
fake_method_response = MethodResponse(
    request_id=fake_request_id, status=fake_method_status, payload=fake_method_payload
)

invalid_feature_name = "__invalid_feature_name__"
unmatched_mqtt_topic = "__unmatched_mqtt_topic__"
fake_mqtt_payload = "__fake_mqtt_payload__"

fake_c2d_topic = "devices/{}/messages/devicebound/".format(fake_device_id)
fake_c2d_topic_with_content_type = "{}{}".format(fake_c2d_topic, fake_content_type_encoded)
fake_c2d_topic_for_another_device = "devices/__other_device__/messages/devicebound/"

fake_input_name = "__fake_input_name__"
fake_input_message_topic = "devices/{}/modules/{}/inputs/{}/".format(
    fake_device_id, fake_module_id, fake_input_name
)
fake_input_message_topic_with_content_type = "{}{}".format(
    fake_input_message_topic, fake_content_type_encoded
)
fake_input_message_topic_for_another_module = "devices/{}/modules/__other_module__/messages/devicebound/".format(
    fake_device_id
)
fake_input_message_topic_for_another_device = "devices/__other_device__/modules/{}/messages/devicebound/".format(
    fake_module_id
)

fake_method_request_topic = "$iothub/methods/POST/{}/?$rid={}".format(
    fake_method_name, fake_request_id
)
fake_method_request_payload = "{}".encode("utf-8")


api_version = "2018-06-30"


ops_handled_by_this_stage = [
    pipeline_ops_iothub.SetAuthProviderArgs,
    pipeline_ops_iothub.SendTelemetry,
    pipeline_ops_iothub.SendOutputEvent,
    pipeline_ops_iothub.SendMethodResponse,
    pipeline_ops_base.EnableFeature,
    pipeline_ops_base.DisableFeature,
]

events_handled_by_this_stage = [pipeline_events_mqtt.IncomingMessage]

pipeline_stage_test.add_base_pipeline_stage_tests(
    cls=pipeline_stages_iothub_mqtt.IotHubMQTTConverter,
    module=this_module,
    all_ops=all_common_ops + all_iothub_ops,
    handled_ops=ops_handled_by_this_stage,
    all_events=all_common_events + all_iothub_events,
    handled_events=events_handled_by_this_stage,
)


@pytest.fixture
def stage(mocker):
    return make_mock_stage(mocker, pipeline_stages_iothub_mqtt.IotHubMQTTConverter)


@pytest.fixture
def set_auth_provider_args(callback):
    return pipeline_ops_iothub.SetAuthProviderArgs(
        device_id=fake_device_id, hostname=fake_hostname, callback=callback
    )


@pytest.fixture
def set_auth_provider_args_for_device(set_auth_provider_args):
    return set_auth_provider_args


@pytest.fixture
def set_auth_provider_args_for_module(set_auth_provider_args):
    set_auth_provider_args.module_id = fake_module_id
    return set_auth_provider_args


@pytest.fixture
def stage_configured_for_device(stage, set_auth_provider_args_for_device, mocker):
    set_auth_provider_args_for_device.callback = None
    stage.run_op(set_auth_provider_args_for_device)
    mocker.resetall()


@pytest.fixture
def stage_configured_for_module(stage, set_auth_provider_args_for_module, mocker):
    set_auth_provider_args_for_module.callback = None
    stage.run_op(set_auth_provider_args_for_module)
    mocker.resetall()


@pytest.fixture(params=["device", "module"])
def stages_configured_for_both(request, stage, set_auth_provider_args, mocker):
    set_auth_provider_args.callback = None
    if request.param == "module":
        set_auth_provider_args.module_id = fake_module_id
    stage.run_op(set_auth_provider_args)
    mocker.resetall()


@pytest.mark.describe("IotHubMQTTConverter - .run_op() -- called with SetAuthProviderArgs")
class TestIotHubMQTTConverterWithSetAuthProviderArgs(object):
    @pytest.mark.it("Runs a SetConnectionArgs operation on the next stage")
    def test_runs_set_connection_args(self, stage, set_auth_provider_args):
        stage.run_op(set_auth_provider_args)
        assert stage.next._run_op.call_count == 1
        new_op = stage.next._run_op.call_args[0][0]
        assert isinstance(new_op, pipeline_ops_mqtt.SetConnectionArgs)

    @pytest.mark.it(
        "Sets connection_args.client_id to auth_provider_args.device_id if auth_provider_args.module_id is None"
    )
    def test_sets_client_id_for_devices(self, stage, set_auth_provider_args):
        stage.run_op(set_auth_provider_args)
        new_op = stage.next._run_op.call_args[0][0]
        assert new_op.client_id == fake_device_id

    @pytest.mark.it(
        "Sets connection_args.client_id to auth_provider_args.device_id/auth_provider_args.module_id if auth_provider_args.module_id is not None"
    )
    def test_sets_client_id_for_modules(self, stage, set_auth_provider_args_for_module):
        stage.run_op(set_auth_provider_args_for_module)
        new_op = stage.next._run_op.call_args[0][0]
        assert new_op.client_id == "{}/{}".format(fake_device_id, fake_module_id)

    @pytest.mark.it(
        "Sets connection_args.hostname to auth_provider.hostname if auth_provider.gateway_hostname is None"
    )
    def test_sets_hostname_if_no_gateway(self, stage, set_auth_provider_args):
        stage.run_op(set_auth_provider_args)
        new_op = stage.next._run_op.call_args[0][0]
        assert new_op.hostname == fake_hostname

    @pytest.mark.it(
        "Sets connection_args.hostname to auth_provider.gateway_hostname if auth_provider.gateway_hostname is not None"
    )
    def test_sets_hostname_if_yes_gateway(self, stage, set_auth_provider_args):
        set_auth_provider_args.gateway_hostname = fake_gateway_hostname
        stage.run_op(set_auth_provider_args)
        new_op = stage.next._run_op.call_args[0][0]
        assert new_op.hostname == fake_gateway_hostname

    @pytest.mark.it(
        "Sets connection_args.username to auth_provider.hostname/auth_provider/device_id/?api-version=2018-06-30 if auth_provider_args.gateway_hostname is None and module_id is None"
    )
    def test_sets_device_username_if_no_gateway(self, stage, set_auth_provider_args):
        stage.run_op(set_auth_provider_args)
        new_op = stage.next._run_op.call_args[0][0]
        assert new_op.username == "{}/{}/?api-version={}".format(
            fake_hostname, fake_device_id, api_version
        )

    @pytest.mark.it(
        "Sets connection_args.username to auth_provider.hostname/device_id/?api-version=2018-06-30 if auth_provider_args.gateway_hostname is not None and module_id is None"
    )
    def test_sets_device_username_if_yes_gateway(self, stage, set_auth_provider_args):
        set_auth_provider_args.gateway_hostname = fake_gateway_hostname
        stage.run_op(set_auth_provider_args)
        new_op = stage.next._run_op.call_args[0][0]
        assert new_op.username == "{}/{}/?api-version={}".format(
            fake_hostname, fake_device_id, api_version
        )

    @pytest.mark.it(
        "Sets connection_args.username to auth_provider.hostname/auth_provider/device_id/?api-version=2018-06-30 if auth_provider_args.gateway_hostname is None and module_id is None"
    )
    def test_sets_module_username_if_no_gateway(self, stage, set_auth_provider_args_for_module):
        stage.run_op(set_auth_provider_args_for_module)
        new_op = stage.next._run_op.call_args[0][0]
        assert new_op.username == "{}/{}/{}/?api-version={}".format(
            fake_hostname, fake_device_id, fake_module_id, api_version
        )

    @pytest.mark.it(
        "Sets connection_args.username to auth_provider.hostname/device_id/module_id/?api-version=2018-06-30 if auth_provider_args.gateway_hostname is not None and module_id is None"
    )
    def test_sets_module_username_if_yes_gateway(self, stage, set_auth_provider_args_for_module):
        set_auth_provider_args_for_module.gateway_hostname = fake_gateway_hostname
        stage.run_op(set_auth_provider_args_for_module)
        new_op = stage.next._run_op.call_args[0][0]
        assert new_op.username == "{}/{}/{}/?api-version={}".format(
            fake_hostname, fake_device_id, fake_module_id, api_version
        )

    @pytest.mark.it("Sets connection_args.ca_cert to auth_provider.ca_cert")
    def test_sets_ca_cert(self, stage, set_auth_provider_args):
        set_auth_provider_args.ca_cert = fake_ca_cert
        stage.run_op(set_auth_provider_args)
        new_op = stage.next._run_op.call_args[0][0]
        assert new_op.ca_cert == fake_ca_cert

    @pytest.mark.it(
        "Calls the SetAuthProviderArgs callback with error if the SetConnectionArgs raises an Exception"
    )
    def test_set_connection_args_raises_exception(
        self, stage, mocker, fake_exception, set_auth_provider_args
    ):
        stage.next._run_op = mocker.Mock(side_effect=fake_exception)
        stage.run_op(set_auth_provider_args)
        assert_callback_failed(op=set_auth_provider_args, error=fake_exception)

    @pytest.mark.it(
        "Allows any BaseExceptions raised inside the SetConnectionArgs operation to propagate"
    )
    def test_set_connection_args_raises_base_exception(
        self, stage, mocker, fake_base_exception, set_auth_provider_args
    ):
        stage.next._run_op = mocker.Mock(side_effect=fake_base_exception)
        with pytest.raises(UnhandledException):
            stage.run_op(set_auth_provider_args)

    @pytest.mark.it(
        "Calls the SetAuthProviderArgs callback with no error if the SetConnectionArgs operation succeeds"
    )
    def test_set_connection_args_succeeds(self, stage, mocker, set_auth_provider_args):
        stage.run_op(set_auth_provider_args)
        assert_callback_succeeded(op=set_auth_provider_args)


basic_ops = [
    {
        "op_class": pipeline_ops_iothub.SendTelemetry,
        "op_init_kwargs": {"message": fake_message},
        "new_op_class": pipeline_ops_mqtt.Publish,
    },
    {
        "op_class": pipeline_ops_iothub.SendOutputEvent,
        "op_init_kwargs": {"message": fake_message},
        "new_op_class": pipeline_ops_mqtt.Publish,
    },
    {
        "op_class": pipeline_ops_iothub.SendMethodResponse,
        "op_init_kwargs": {"method_response": fake_method_response},
        "new_op_class": pipeline_ops_mqtt.Publish,
    },
    {
        "op_class": pipeline_ops_base.EnableFeature,
        "op_init_kwargs": {"feature_name": constant.C2D_MSG},
        "new_op_class": pipeline_ops_mqtt.Subscribe,
    },
    {
        "op_class": pipeline_ops_base.DisableFeature,
        "op_init_kwargs": {"feature_name": constant.C2D_MSG},
        "new_op_class": pipeline_ops_mqtt.Unsubscribe,
    },
]


@pytest.fixture
def op(params, callback):
    op = params["op_class"](**params["op_init_kwargs"])
    op.callback = callback
    return op


@pytest.mark.parametrize(
    "params",
    basic_ops,
    ids=["{}->{}".format(x["op_class"].__name__, x["new_op_class"].__name__) for x in basic_ops],
)
@pytest.mark.describe("IotHubMQTTConverter - .run_op() -- called with basic MQTT operations")
class TestIotHubMQTTConverterBasicOperations(object):
    @pytest.mark.it("Runs an operation on the next stage")
    def test_runs_publish(self, params, stage, stages_configured_for_both, op):
        stage.run_op(op)
        new_op = stage.next._run_op.call_args[0][0]
        assert isinstance(new_op, params["new_op_class"])

    @pytest.mark.it("Calls the original op callback with error if the new_op raises an exception")
    def test_operation_raises_exception(
        self, params, mocker, stage, stages_configured_for_both, op, fake_exception
    ):
        stage.next._run_op = mocker.Mock(side_effect=fake_exception)
        stage.run_op(op)
        assert_callback_failed(op=op, error=fake_exception)

    @pytest.mark.it("Allows any any BaseExceptions raised in the new_op to propagate")
    def test_operation_raises_base_exception(
        self, params, mocker, stage, stages_configured_for_both, op, fake_base_exception
    ):
        stage.next._run_op = mocker.Mock(side_effect=fake_base_exception)
        with pytest.raises(UnhandledException):
            stage.run_op(op)

    @pytest.mark.it("Calls the original op callback with no error if the new_op operation succeeds")
    def test_operation_succeeds(self, params, stage, stages_configured_for_both, op):
        stage.run_op(op)
        assert_callback_succeeded(op)


publish_ops = [
    {
        "name": "send telemetry",
        "stage_type": "device",
        "op_class": pipeline_ops_iothub.SendTelemetry,
        "op_init_kwargs": {"message": Message(fake_message_body)},
        "topic": "devices/{}/messages/events/".format(fake_device_id),
        "publish_payload": fake_message_body,
    },
    {
        "name": "send telemetry with properties",
        "stage_type": "device",
        "op_class": pipeline_ops_iothub.SendTelemetry,
        "op_init_kwargs": {"message": Message(fake_message_body, content_type=fake_content_type)},
        "topic": "devices/{}/messages/events/{}".format(fake_device_id, fake_content_type_encoded),
        "publish_payload": fake_message_body,
    },
    {
        "name": "send output",
        "stage_type": "module",
        "op_class": pipeline_ops_iothub.SendOutputEvent,
        "op_init_kwargs": {"message": Message(fake_message_body, output_name=fake_output_name)},
        "topic": "devices/{}/modules/{}/messages/events/%24.on={}".format(
            fake_device_id, fake_module_id, fake_output_name
        ),
        "publish_payload": fake_message_body,
    },
    {
        "name": "send output with properties",
        "stage_type": "module",
        "op_class": pipeline_ops_iothub.SendOutputEvent,
        "op_init_kwargs": {
            "message": Message(
                fake_message_body, output_name=fake_output_name, content_type=fake_content_type
            )
        },
        "topic": "devices/{}/modules/{}/messages/events/%24.on={}&{}".format(
            fake_device_id, fake_module_id, fake_output_name, fake_content_type_encoded
        ),
        "publish_payload": fake_message_body,
    },
    {
        "name": "send method result",
        "stage_type": "both",
        "op_class": pipeline_ops_iothub.SendMethodResponse,
        "op_init_kwargs": {"method_response": fake_method_response},
        "topic": "$iothub/methods/res/__fake_method_status__/?$rid=__fake_request_id__",
        "publish_payload": json.dumps(fake_method_payload),
    },
]


@pytest.mark.parametrize("params", publish_ops, ids=[x["name"] for x in publish_ops])
@pytest.mark.describe("IotHubMQTTConverter - .run_op() -- called with publish operations")
class TestIotHubMQTTConverterForPublishOps(object):
    @pytest.mark.it("Uses the correct topic and encodes message properties string when publishing")
    def test_uses_device_topic_for_devices(self, stage, stages_configured_for_both, params, op):
        if params["stage_type"] == "device" and stage.module_id:
            pytest.skip()
        elif params["stage_type"] == "module" and not stage.module_id:
            pytest.skip()
        stage.run_op(op)
        new_op = stage.next._run_op.call_args[0][0]
        assert new_op.topic == params["topic"]

    @pytest.mark.it("Sends the body in the payload of the MQTT publish operation")
    def test_sends_correct_body(self, stage, stages_configured_for_both, params, op):
        stage.run_op(op)
        new_op = stage.next._run_op.call_args[0][0]
        assert new_op.payload == params["publish_payload"]


feature_name_to_subscribe_topic = [
    {
        "stage_type": "device",
        "feature_name": constant.C2D_MSG,
        "topic": "devices/{}/messages/devicebound/#".format(fake_device_id),
    },
    {
        "stage_type": "module",
        "feature_name": constant.INPUT_MSG,
        "topic": "devices/{}/modules/{}/inputs/#".format(fake_device_id, fake_module_id),
    },
    {"stage_type": "both", "feature_name": constant.METHODS, "topic": "$iothub/methods/POST/#"},
]

sub_unsub_operations = [
    {"op_class": pipeline_ops_base.EnableFeature, "new_op": pipeline_ops_mqtt.Subscribe},
    {"op_class": pipeline_ops_base.DisableFeature, "new_op": pipeline_ops_mqtt.Unsubscribe},
]


@pytest.mark.describe(
    "IotHubMQTTConverter - .run_op() -- called with EnableFeature or DisableFeature"
)
class TestIotHubMQTTConverterWithEnableFeature(object):
    @pytest.mark.parametrize(
        "topic_parameters",
        feature_name_to_subscribe_topic,
        ids=[
            "{} {}".format(x["stage_type"], x["feature_name"])
            for x in feature_name_to_subscribe_topic
        ],
    )
    @pytest.mark.parametrize(
        "op_parameters",
        sub_unsub_operations,
        ids=[x["op_class"].__name__ for x in sub_unsub_operations],
    )
    @pytest.mark.it("Converts the feature_name to the correct topic")
    def test_converts_feature_name_to_topic(
        self, mocker, stage, stages_configured_for_both, topic_parameters, op_parameters
    ):
        if topic_parameters["stage_type"] == "device" and stage.module_id:
            pytest.skip()
        elif topic_parameters["stage_type"] == "module" and not stage.module_id:
            pytest.skip()
        stage.next._run_op = mocker.Mock()
        op = op_parameters["op_class"](feature_name=topic_parameters["feature_name"])
        stage.run_op(op)
        new_op = stage.next._run_op.call_args[0][0]
        assert isinstance(new_op, op_parameters["new_op"])
        assert new_op.topic == topic_parameters["topic"]

    @pytest.mark.it("Fails on an invalid feature_name")
    @pytest.mark.parametrize(
        "op_parameters",
        sub_unsub_operations,
        ids=[x["op_class"].__name__ for x in sub_unsub_operations],
    )
    def test_fails_on_invalid_feature_name(
        self, mocker, stage, stages_configured_for_both, op_parameters, callback
    ):
        op = op_parameters["op_class"](feature_name=invalid_feature_name, callback=callback)
        callback.reset_mock()
        stage.run_op(op)
        assert callback.call_count == 1
        callback_arg = op.callback.call_args[0][0]
        assert callback_arg == op
        assert isinstance(callback_arg.error, KeyError)


@pytest.fixture
def add_pipeline_root(stage, mocker):
    root = pipeline_stages_base.PipelineRoot()
    mocker.spy(root, "handle_pipeline_event")
    stage.previous = root


@pytest.mark.describe(
    "IotHubMQTTConverter - .handle_pipeline_event() -- called with unmatched topic"
)
class TestIotHubMQTTConverterHandlePipelineEvent(object):
    @pytest.mark.it("Passes up any mqtt messages with topics that aren't matched by this stage")
    def test_passes_up_mqtt_message_with_unknown_topic(
        self, stage, stages_configured_for_both, add_pipeline_root, mocker
    ):
        event = pipeline_events_mqtt.IncomingMessage(
            topic=unmatched_mqtt_topic, payload=fake_mqtt_payload
        )
        stage.handle_pipeline_event(event)
        assert stage.previous.handle_pipeline_event.call_count == 1
        assert stage.previous.handle_pipeline_event.call_args == mocker.call(event)


@pytest.fixture
def c2d_event():
    return pipeline_events_mqtt.IncomingMessage(topic=fake_c2d_topic, payload=fake_mqtt_payload)


@pytest.mark.describe("IotHubMQTTConverter - .handle_pipeline_event() -- called with C2D topic")
class TestIotHubMQTTConverterHandlePipelineEventC2D(object):
    @pytest.mark.it(
        "Converts mqtt message with topic devices/device_id/message/devicebound/ to c2d event"
    )
    def test_converts_c2d_topic_to_c2d_events(
        self, mocker, stage, stage_configured_for_device, add_pipeline_root, c2d_event
    ):
        stage.handle_pipeline_event(c2d_event)
        assert stage.previous.handle_pipeline_event.call_count == 1
        new_event = stage.previous.handle_pipeline_event.call_args[0][0]
        assert isinstance(new_event, pipeline_events_iothub.C2DMessageEvent)

    @pytest.mark.it("Convers the mqtt payload of a c2d message into a Message object")
    def test_creates_message_object_for_c2d_event(
        self, mocker, stage, stage_configured_for_device, add_pipeline_root, c2d_event
    ):
        stage.handle_pipeline_event(c2d_event)
        new_event = stage.previous.handle_pipeline_event.call_args[0][0]
        assert isinstance(new_event.message, Message)

    @pytest.mark.it("Extracts message properties from the mqtt topic for c2d messages")
    def test_extracts_c2d_message_properties_from_topic_name(
        self, mocker, stage, stage_configured_for_device, add_pipeline_root
    ):
        event = pipeline_events_mqtt.IncomingMessage(
            topic=fake_c2d_topic_with_content_type, payload=fake_mqtt_payload
        )
        stage.handle_pipeline_event(event)
        new_event = stage.previous.handle_pipeline_event.call_args[0][0]
        assert new_event.message.content_type == fake_content_type

    @pytest.mark.it("Passes up c2d messages destined for another device")
    def test_if_topic_is_c2d_for_another_device(
        self, mocker, stage, stage_configured_for_device, add_pipeline_root
    ):
        event = pipeline_events_mqtt.IncomingMessage(
            topic=fake_c2d_topic_for_another_device, payload=fake_mqtt_payload
        )
        stage.handle_pipeline_event(event)
        assert stage.previous.handle_pipeline_event.call_count == 1
        assert stage.previous.handle_pipeline_event.call_args == mocker.call(event)


@pytest.fixture
def input_message_event():
    return pipeline_events_mqtt.IncomingMessage(
        topic=fake_input_message_topic, payload=fake_mqtt_payload
    )


@pytest.mark.describe(
    "IotHubMQTTConverter - .handle_pipeline_event() -- called with input message topic"
)
class TestIotHubMQTTConverterHandlePipelineEventInputMessages(object):
    @pytest.mark.it(
        "Converts mqtt message with topic devices/device_id/modules/module_id/inputs/input_name/ to input event"
    )
    def test_converts_input_topic_to_input_event(
        self, mocker, stage, stage_configured_for_module, add_pipeline_root, input_message_event
    ):
        stage.handle_pipeline_event(input_message_event)
        assert stage.previous.handle_pipeline_event.call_count == 1
        new_event = stage.previous.handle_pipeline_event.call_args[0][0]
        assert isinstance(new_event, pipeline_events_iothub.InputMessageEvent)

    @pytest.mark.it("Converts the mqtt payload of an input message into a Message object")
    def test_creates_message_object_for_input_event(
        self, mocker, stage, stage_configured_for_module, add_pipeline_root, input_message_event
    ):
        stage.handle_pipeline_event(input_message_event)
        new_event = stage.previous.handle_pipeline_event.call_args[0][0]
        assert isinstance(new_event.message, Message)

    @pytest.mark.it("Extracts the input name of an input message from the mqtt topic")
    def test_extracts_input_name_from_topic(
        self, mocker, stage, stage_configured_for_module, add_pipeline_root, input_message_event
    ):
        stage.handle_pipeline_event(input_message_event)
        new_event = stage.previous.handle_pipeline_event.call_args[0][0]
        assert new_event.input_name == fake_input_name

    @pytest.mark.it("Extracts message properties from the mqtt topic for input messages")
    def test_extracts_input_message_properties_from_topic_name(
        self, mocker, stage, stage_configured_for_module, add_pipeline_root
    ):
        event = pipeline_events_mqtt.IncomingMessage(
            topic=fake_input_message_topic_with_content_type, payload=fake_mqtt_payload
        )
        stage.handle_pipeline_event(event)
        new_event = stage.previous.handle_pipeline_event.call_args[0][0]
        assert new_event.message.content_type == fake_content_type

    @pytest.mark.parametrize(
        "topic",
        [fake_input_message_topic_for_another_device, fake_input_message_topic_for_another_module],
        ids=["different device_id", "same device_id"],
    )
    @pytest.mark.it("Passes up input messages destined for another module")
    def test_if_topic_is_input_message_for_another_module(
        self, mocker, stage, stage_configured_for_module, add_pipeline_root, topic
    ):
        event = pipeline_events_mqtt.IncomingMessage(topic=topic, payload=fake_mqtt_payload)
        stage.handle_pipeline_event(event)
        assert stage.previous.handle_pipeline_event.call_count == 1
        assert stage.previous.handle_pipeline_event.call_args == mocker.call(event)


@pytest.fixture
def method_request_event():
    return pipeline_events_mqtt.IncomingMessage(
        topic=fake_method_request_topic, payload=fake_method_request_payload
    )


@pytest.mark.describe(
    "IotHubMQTTConverter - .handle_pipeline_event() -- called with method request topic"
)
class TestIotHubMQTTConverterHandlePipelineEventMethodRequets(object):
    @pytest.mark.it(
        "Converts mqtt messages with topic $iothub/methods/POST/{method name}/?$rid={request id} to method request events"
    )
    def test_converts_method_request_topic_to_method_request_event(
        self, mocker, stage, stages_configured_for_both, add_pipeline_root, method_request_event
    ):
        stage.handle_pipeline_event(method_request_event)
        assert stage.previous.handle_pipeline_event.call_count == 1
        new_event = stage.previous.handle_pipeline_event.call_args[0][0]
        assert isinstance(new_event, pipeline_events_iothub.MethodRequest)

    @pytest.mark.it("Makes a MethodRequest object to hold the method request details")
    def test_passes_method_request_object_in_method_request_event(
        self, mocker, stage, stages_configured_for_both, add_pipeline_root, method_request_event
    ):
        stage.handle_pipeline_event(method_request_event)
        new_event = stage.previous.handle_pipeline_event.call_args[0][0]
        assert isinstance(new_event.method_request, MethodRequest)

    @pytest.mark.it("Extracts the method name from the mqtt topic")
    def test_extracts_method_name_from_method_request_topic(
        self, mocker, stage, stages_configured_for_both, add_pipeline_root, method_request_event
    ):
        stage.handle_pipeline_event(method_request_event)
        new_event = stage.previous.handle_pipeline_event.call_args[0][0]
        assert new_event.method_request.name == fake_method_name

    @pytest.mark.it("Extracts the request id from the mqtt topic")
    def test_extracts_request_id_from_method_request_topic(
        self, mocker, stage, stages_configured_for_both, add_pipeline_root, method_request_event
    ):
        stage.handle_pipeline_event(method_request_event)
        new_event = stage.previous.handle_pipeline_event.call_args[0][0]
        assert new_event.method_request.request_id == fake_request_id

    @pytest.mark.it(
        "Puts the payload of the mqtt message as the payload of the method requets object"
    )
    def test_puts_mqtt_payload_in_method_request_payload(
        self, mocker, stage, stages_configured_for_both, add_pipeline_root, method_request_event
    ):
        stage.handle_pipeline_event(method_request_event)
        new_event = stage.previous.handle_pipeline_event.call_args[0][0]
        assert new_event.method_request.payload == json.loads(
            fake_method_request_payload.decode("utf-8")
        )
