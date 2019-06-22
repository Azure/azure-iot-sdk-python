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
)
from azure.iot.device.provisioning.pipeline import (
    constant,
    pipeline_events_provisioning,
    pipeline_ops_provisioning,
    pipeline_stages_provisioning_mqtt,
)
from tests.common.pipeline.helpers import (
    assert_callback_failed,
    assert_callback_succeeded,
    all_common_ops,
    all_common_events,
    all_except,
    make_mock_stage,
    UnhandledException,
)
from tests.provisioning.pipeline.helpers import all_provisioning_ops, all_provisioning_events
from tests.common.pipeline import pipeline_stage_test

logging.basicConfig(level=logging.INFO)

this_module = sys.modules[__name__]

fake_device_id = "elder_wand"
fake_registration_id = "registered_remembrall"
fake_provisioning_host = "hogwarts.com"
fake_id_scope = "weasley_wizard_wheezes"
fake_ca_cert = "fake_certificate"
fake_sas_token = "horcrux_token"
fake_security_client = "secure_via_muffliato"
fake_request_id = "fake_request_1234"
fake_mqtt_payload = "hello hogwarts"
fake_operation_id = "fake_operation_9876"

invalid_feature_name = "__invalid_feature_name__"
unmatched_mqtt_topic = "__unmatched_mqtt_topic__"

fake_response_topic = "$dps/registrations/res/200/?$rid={}".format(fake_request_id)

api_version = "2019-03-31"


ops_handled_by_this_stage = [
    pipeline_ops_provisioning.SetSecurityClientArgsOperation,
    pipeline_ops_provisioning.SendRegistrationRequestOperation,
    pipeline_ops_provisioning.SendQueryRequestOperation,
    pipeline_ops_base.EnableFeatureOperation,
    pipeline_ops_base.DisableFeatureOperation,
]

events_handled_by_this_stage = [pipeline_events_mqtt.IncomingMQTTMessageEvent]

pipeline_stage_test.add_base_pipeline_stage_tests(
    cls=pipeline_stages_provisioning_mqtt.ProvisioningMQTTConverterStage,
    module=this_module,
    all_ops=all_common_ops + all_provisioning_ops,
    handled_ops=ops_handled_by_this_stage,
    all_events=all_common_events + all_provisioning_events,
    handled_events=events_handled_by_this_stage,
)


@pytest.fixture(scope="function")
def some_exception():
    return Exception("Alohomora")


@pytest.fixture
def mock_stage(mocker):
    return make_mock_stage(mocker, pipeline_stages_provisioning_mqtt.ProvisioningMQTTConverterStage)


@pytest.fixture
def set_security_client_args(callback):
    op = pipeline_ops_provisioning.SetSecurityClientArgsOperation(
        provisioning_host=fake_provisioning_host,
        registration_id=fake_registration_id,
        id_scope=fake_id_scope,
        callback=callback,
    )
    return op


@pytest.fixture
def stages_configured(mock_stage, set_security_client_args, mocker):
    set_security_client_args.callback = None
    mock_stage.run_op(set_security_client_args)
    mocker.resetall()


@pytest.mark.describe(
    "ProvisioningMQTTConverterStage run_op function with SetSecurityClientArgsOperation"
)
class TestProvisioningMQTTConverterWithSetAuthProviderArgs(object):
    @pytest.mark.it(
        "Runs a pipeline_ops_mqtt.SetMQTTConnectionArgsOperation operation on the next stage"
    )
    def test_runs_set_connection_args(self, mock_stage, set_security_client_args):
        mock_stage.run_op(set_security_client_args)
        assert mock_stage.next._run_op.call_count == 1
        new_op = mock_stage.next._run_op.call_args[0][0]
        assert isinstance(new_op, pipeline_ops_mqtt.SetMQTTConnectionArgsOperation)

    @pytest.mark.it(
        "Sets ConnectionArgs.client_id = SymmetricKeySecurityClientArgs.registration_id"
    )
    def test_sets_client_id(self, mock_stage, set_security_client_args):
        mock_stage.run_op(set_security_client_args)
        new_op = mock_stage.next._run_op.call_args[0][0]
        assert new_op.client_id == fake_registration_id

    @pytest.mark.it(
        "Sets ConnectionArgs.hostname = SymmetricKeySecurityClientArgs.provisioning_host"
    )
    def test_sets_hostname(self, mock_stage, set_security_client_args):
        mock_stage.run_op(set_security_client_args)
        new_op = mock_stage.next._run_op.call_args[0][0]
        assert new_op.hostname == fake_provisioning_host

    @pytest.mark.it(
        "Sets ConnectionArgs.username = SymmetricKeySecurityClientArgs.{id_scope}/registrations/{registration_id}/api-version={api_version}&ClientVersion={client_version}"
    )
    def test_sets_username(self, mock_stage, set_security_client_args):
        mock_stage.run_op(set_security_client_args)
        new_op = mock_stage.next._run_op.call_args[0][0]
        assert (
            new_op.username
            == "{id_scope}/registrations/{registration_id}/api-version={api_version}&ClientVersion={client_version}".format(
                id_scope=fake_id_scope,
                registration_id=fake_registration_id,
                api_version=constant.API_VERSION,
                client_version="azure-iot-provisioning-devicesdk%2F" + "0.0.1",
            )
        )

    @pytest.mark.it(
        "Calls the SetSymmetricKeySecurityClientArgs callback with error if the pipeline_ops_mqtt.SetMQTTConnectionArgsOperation operation raises an Exception"
    )
    def test_set_connection_args_raises_exception(
        self, mock_stage, mocker, some_exception, set_security_client_args
    ):
        mock_stage.next._run_op = mocker.Mock(side_effect=some_exception)
        mock_stage.run_op(set_security_client_args)
        assert_callback_failed(op=set_security_client_args, error=some_exception)

    @pytest.mark.it(
        "Allows any BaseExceptions raised inside the pipeline_ops_mqtt.SetMQTTConnectionArgsOperation operation to propagate"
    )
    def test_set_connection_args_raises_base_exception(
        self, mock_stage, mocker, fake_base_exception, set_security_client_args
    ):
        mock_stage.next._run_op = mocker.Mock(side_effect=fake_base_exception)
        with pytest.raises(UnhandledException):
            mock_stage.run_op(set_security_client_args)

    @pytest.mark.it(
        "Calls the SetSymmetricKeySecurityClientArgs callback with no error if the pipeline_ops_mqtt.SetMQTTConnectionArgsOperation operation succeeds"
    )
    def test_returns_success_if_set_connection_args_succeeds(
        self, mock_stage, mocker, set_security_client_args
    ):
        mock_stage.run_op(set_security_client_args)
        assert_callback_succeeded(op=set_security_client_args)


basic_ops = [
    {
        "op_class": pipeline_ops_provisioning.SendRegistrationRequestOperation,
        "op_init_kwargs": {"request_id": fake_request_id, "request_payload": fake_mqtt_payload},
        "new_op_class": pipeline_ops_mqtt.MQTTPublishOperation,
    },
    {
        "op_class": pipeline_ops_provisioning.SendQueryRequestOperation,
        "op_init_kwargs": {
            "request_id": fake_request_id,
            "operation_id": fake_operation_id,
            "request_payload": fake_mqtt_payload,
        },
        "new_op_class": pipeline_ops_mqtt.MQTTPublishOperation,
    },
    {
        "op_class": pipeline_ops_base.EnableFeatureOperation,
        "op_init_kwargs": {"feature_name": None},
        "new_op_class": pipeline_ops_mqtt.MQTTSubscribeOperation,
    },
    {
        "op_class": pipeline_ops_base.DisableFeatureOperation,
        "op_init_kwargs": {"feature_name": None},
        "new_op_class": pipeline_ops_mqtt.MQTTUnsubscribeOperation,
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
@pytest.mark.describe("ProvisioningMQTTConverterStage basic operation tests")
class TestProvisioningMQTTConverterBasicOperations(object):
    @pytest.mark.it("Runs an operation on the next stage")
    def test_runs_publish(self, params, mock_stage, stages_configured, op):
        mock_stage.run_op(op)
        new_op = mock_stage.next._run_op.call_args[0][0]
        assert isinstance(new_op, params["new_op_class"])

    @pytest.mark.it("Calls the original op callback with error if the new_op raises an Exception")
    def test_new_op_raises_exception(
        self, params, mocker, mock_stage, stages_configured, op, some_exception
    ):
        mock_stage.next._run_op = mocker.Mock(side_effect=some_exception)
        mock_stage.run_op(op)
        assert_callback_failed(op=op, error=some_exception)

    @pytest.mark.it("Allows any BaseExceptions raised from inside new_op to propagate")
    def test_new_op_raises_base_exception(
        self, params, mocker, mock_stage, stages_configured, op, fake_base_exception
    ):
        mock_stage.next._run_op = mocker.Mock(side_effect=fake_base_exception)
        with pytest.raises(UnhandledException):
            mock_stage.run_op(op)

    @pytest.mark.it("Calls the original op callback with no error if the new_op operation succeeds")
    def test_returns_success_if_publish_succeeds(self, params, mock_stage, stages_configured, op):
        mock_stage.run_op(op)
        assert_callback_succeeded(op)


publish_ops = [
    {
        "name": "send register request",
        "op_class": pipeline_ops_provisioning.SendRegistrationRequestOperation,
        "op_init_kwargs": {"request_id": fake_request_id, "request_payload": fake_mqtt_payload},
        "topic": "$dps/registrations/PUT/iotdps-register/?$rid={request_id}".format(
            request_id=fake_request_id
        ),
        "publish_payload": fake_mqtt_payload,
    },
    {
        "name": "send query request",
        "op_class": pipeline_ops_provisioning.SendQueryRequestOperation,
        "op_init_kwargs": {
            "request_id": fake_request_id,
            "operation_id": fake_operation_id,
            "request_payload": fake_mqtt_payload,
        },
        "topic": "$dps/registrations/GET/iotdps-get-operationstatus/?$rid={request_id}&operationId={operation_id}".format(
            request_id=fake_request_id, operation_id=fake_operation_id
        ),
        "publish_payload": fake_mqtt_payload,
    },
]


@pytest.mark.parametrize("params", publish_ops, ids=[x["name"] for x in publish_ops])
@pytest.mark.describe("ProvisioningMQTTConverterStage run_op function for publish operations")
class TestProvisioningMQTTConverterForPublishOps(object):
    @pytest.mark.it("Uses correct registration topic string when publishing")
    def test_uses_topic_for(self, mock_stage, stages_configured, params, op):
        mock_stage.run_op(op)
        new_op = mock_stage.next._run_op.call_args[0][0]
        assert new_op.topic == params["topic"]

    @pytest.mark.it("Sends correct payload when publishing")
    def test_sends_correct_body(self, mock_stage, stages_configured, params, op):
        mock_stage.run_op(op)
        new_op = mock_stage.next._run_op.call_args[0][0]
        assert new_op.payload == params["publish_payload"]


sub_unsub_operations = [
    {
        "op_class": pipeline_ops_base.EnableFeatureOperation,
        "new_op": pipeline_ops_mqtt.MQTTSubscribeOperation,
    },
    {
        "op_class": pipeline_ops_base.DisableFeatureOperation,
        "new_op": pipeline_ops_mqtt.MQTTUnsubscribeOperation,
    },
]


@pytest.mark.describe("ProvisioningMQTTConverterStage run_op function with EnableFeature operation")
class TestProvisioningMQTTConverterWithEnable(object):
    @pytest.mark.parametrize(
        "op_parameters",
        sub_unsub_operations,
        ids=[x["op_class"].__name__ for x in sub_unsub_operations],
    )
    @pytest.mark.it("Gets the correct topic")
    def test_converts_feature_name_to_topic(
        self, mocker, mock_stage, stages_configured, op_parameters
    ):
        topic = "$dps/registrations/res/#"
        mock_stage.next._run_op = mocker.Mock()

        op = op_parameters["op_class"](feature_name=None)
        mock_stage.run_op(op)
        new_op = mock_stage.next._run_op.call_args[0][0]
        assert isinstance(new_op, op_parameters["new_op"])
        assert new_op.topic == topic


@pytest.fixture
def add_pipeline_root(mock_stage, mocker):
    root = pipeline_stages_base.PipelineRootStage()
    mocker.spy(root, "handle_pipeline_event")
    mock_stage.previous = root


@pytest.mark.describe("ProvisioningMQTTConverterStage _handle_pipeline_event")
class TestProvisioningMQTTConverterHandlePipelineEvent(object):
    @pytest.mark.it("Passes up any mqtt messages with topics that aren't matched by this stage")
    def test_passes_up_mqtt_message_with_unknown_topic(
        self, mock_stage, stages_configured, add_pipeline_root, mocker
    ):
        event = pipeline_events_mqtt.IncomingMQTTMessageEvent(
            topic=unmatched_mqtt_topic, payload=fake_mqtt_payload
        )
        mock_stage.handle_pipeline_event(event)
        assert mock_stage.previous.handle_pipeline_event.call_count == 1
        assert mock_stage.previous.handle_pipeline_event.call_args == mocker.call(event)


@pytest.fixture
def dps_response_event():
    return pipeline_events_mqtt.IncomingMQTTMessageEvent(
        topic=fake_response_topic, payload=fake_mqtt_payload.encode("utf-8")
    )


@pytest.mark.describe("ProvisioningMQTTConverterStage _handle_pipeline_event for response")
class TestProvisioningMQTTConverterHandlePipelineEventRegistrationResponse(object):
    @pytest.mark.it(
        "Converts mqtt message with topic $dps/registrations/res/#/ to registration response event"
    )
    def test_converts_response_topic_to_registration_response_event(
        self, mocker, mock_stage, stages_configured, add_pipeline_root, dps_response_event
    ):
        mock_stage.handle_pipeline_event(dps_response_event)
        assert mock_stage.previous.handle_pipeline_event.call_count == 1
        new_event = mock_stage.previous.handle_pipeline_event.call_args[0][0]
        assert isinstance(new_event, pipeline_events_provisioning.RegistrationResponseEvent)

    @pytest.mark.it("Extracts message properties from the mqtt topic for c2d messages")
    def test_extracts_some_properties_from_topic(
        self, mocker, mock_stage, stages_configured, add_pipeline_root, dps_response_event
    ):
        mock_stage.handle_pipeline_event(dps_response_event)
        new_event = mock_stage.previous.handle_pipeline_event.call_args[0][0]
        assert new_event.request_id == fake_request_id
        assert new_event.status_code == "200"

    @pytest.mark.it("Passes up other messages")
    def test_if_topic_is_not_response(
        self, mocker, mock_stage, stages_configured, add_pipeline_root
    ):
        fake_some_other_topic = "devices/{}/messages/devicebound/".format(fake_device_id)
        event = pipeline_events_mqtt.IncomingMQTTMessageEvent(
            topic=fake_some_other_topic, payload=fake_mqtt_payload
        )
        mock_stage.handle_pipeline_event(event)
        assert mock_stage.previous.handle_pipeline_event.call_count == 1
        assert mock_stage.previous.handle_pipeline_event.call_args == mocker.call(event)
