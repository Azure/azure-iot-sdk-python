# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import logging
import pytest
import sys
import json
import six.moves.urllib as urllib
from azure.iot.device import constant as pkg_constant
from azure.iot.device.common.pipeline import (
    pipeline_ops_base,
    pipeline_stages_base,
    pipeline_ops_mqtt,
    pipeline_events_mqtt,
    pipeline_events_base,
    pipeline_exceptions,
)
from azure.iot.device.provisioning.pipeline import (
    config,
    pipeline_ops_provisioning,
    pipeline_stages_provisioning_mqtt,
)
from azure.iot.device.provisioning.pipeline import constant as pipeline_constant
from azure.iot.device import user_agent
from tests.common.pipeline.helpers import StageRunOpTestBase, StageHandlePipelineEventTestBase
from tests.common.pipeline import pipeline_stage_test

logging.basicConfig(level=logging.DEBUG)
this_module = sys.modules[__name__]
pytestmark = pytest.mark.usefixtures("fake_pipeline_thread")


@pytest.fixture(params=[True, False], ids=["With error", "No error"])
def op_error(request, arbitrary_exception):
    if request.param:
        return arbitrary_exception
    else:
        return None


@pytest.fixture
def mock_mqtt_topic(mocker):
    m = mocker.patch(
        "azure.iot.device.provisioning.pipeline.pipeline_stages_provisioning_mqtt.mqtt_topic_provisioning"
    )
    return m


class ProvisioningMQTTTranslationStageTestConfig(object):
    @pytest.fixture
    def cls_type(self):
        return pipeline_stages_provisioning_mqtt.ProvisioningMQTTTranslationStage

    @pytest.fixture
    def init_kwargs(self):
        return {}

    @pytest.fixture
    def pipeline_config(self, mocker):
        # auth type shouldn't matter for this stage, so just give it a fake sastoken for now.
        cfg = config.ProvisioningPipelineConfig(
            hostname="http://my.hostname",
            registration_id="fake_reg_id",
            id_scope="fake_id_scope",
            sastoken=mocker.MagicMock(),
        )
        return cfg

    @pytest.fixture
    def stage(self, mocker, cls_type, init_kwargs, pipeline_config):
        stage = cls_type(**init_kwargs)
        stage.pipeline_root = pipeline_stages_base.PipelineRootStage(pipeline_config)
        stage.send_op_down = mocker.MagicMock()
        stage.send_event_up = mocker.MagicMock()
        return stage


pipeline_stage_test.add_base_pipeline_stage_tests(
    test_module=this_module,
    stage_class_under_test=pipeline_stages_provisioning_mqtt.ProvisioningMQTTTranslationStage,
    stage_test_config_class=ProvisioningMQTTTranslationStageTestConfig,
)


@pytest.mark.describe(
    "ProvisioningMQTTTranslationStage - .run_op() -- Called with InitializePipelineOperation"
)
class TestProvisioningMQTTTranslationStageRunOpWithInitializePipelineOperation(
    StageRunOpTestBase, ProvisioningMQTTTranslationStageTestConfig
):
    @pytest.fixture
    def op(self, mocker):
        return pipeline_ops_base.InitializePipelineOperation(callback=mocker.MagicMock())

    @pytest.mark.it("Derives the MQTT client id, and sets it on the op")
    def test_client_id(self, stage, op, pipeline_config):
        assert not hasattr(op, "client_id")
        stage.run_op(op)

        assert op.client_id == pipeline_config.registration_id

    @pytest.mark.it("Derives the MQTT username, and sets it on the op")
    def test_username(self, stage, op, pipeline_config):
        assert not hasattr(op, "username")
        stage.run_op(op)

        expected_username = "{id_scope}/registrations/{registration_id}/api-version={api_version}&ClientVersion={user_agent}".format(
            id_scope=pipeline_config.id_scope,
            registration_id=pipeline_config.registration_id,
            api_version=pkg_constant.PROVISIONING_API_VERSION,
            user_agent=urllib.parse.quote(user_agent.get_provisioning_user_agent(), safe=""),
        )
        assert op.username == expected_username

    @pytest.mark.it("Sends the op down the pipeline")
    def test_sends_down(self, mocker, stage, op):
        stage.run_op(op)
        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(op)


@pytest.mark.describe(
    "ProvisioningMQTTTranslationStage - .run_op() -- Called with RequestOperation (Register Request)"
)
class TestProvisioningMQTTTranslationStageRunOpWithRequestOperationRegister(
    StageRunOpTestBase, ProvisioningMQTTTranslationStageTestConfig
):
    @pytest.fixture
    def op(self, mocker):
        return pipeline_ops_base.RequestOperation(
            request_type=pipeline_constant.REGISTER,
            method="PUT",
            resource_location="/",
            request_body='{"json": "payload"}',
            request_id="fake_request_id",
            callback=mocker.MagicMock(),
        )

    @pytest.mark.it("Derives the Provisioning Register Request topic using the op's details")
    def test_register_request_topic(self, mocker, stage, op, mock_mqtt_topic):
        stage.run_op(op)

        assert mock_mqtt_topic.get_register_topic_for_publish.call_count == 1
        assert mock_mqtt_topic.get_register_topic_for_publish.call_args == mocker.call(
            request_id=op.request_id
        )

    @pytest.mark.it(
        "Sends a new MQTTPublishOperation down the pipeline with the original op's request body and the derived topic string"
    )
    def test_sends_mqtt_publish_down(self, mocker, stage, op, mock_mqtt_topic):
        stage.run_op(op)

        assert stage.send_op_down.call_count == 1
        new_op = stage.send_op_down.call_args[0][0]
        assert isinstance(new_op, pipeline_ops_mqtt.MQTTPublishOperation)
        assert new_op.topic == mock_mqtt_topic.get_register_topic_for_publish.return_value
        assert new_op.payload == op.request_body

    @pytest.mark.it("Completes the original op upon completion of the new MQTTPbulishOperation")
    def test_complete_resulting_op(self, stage, op, op_error):
        stage.run_op(op)
        assert not op.completed
        assert op.error is None

        assert stage.send_op_down.call_count == 1
        new_op = stage.send_op_down.call_args[0][0]
        assert isinstance(new_op, pipeline_ops_mqtt.MQTTPublishOperation)

        new_op.complete(error=op_error)

        assert new_op.completed
        assert new_op.error is op_error
        assert op.completed
        assert op.error is op_error


@pytest.mark.describe(
    "ProvisioningMQTTTranslationStage - .run_op() -- Called with RequestOperation (Query Request)"
)
class TestProvisioningMQTTTranslationStageRunOpWithRequestOperationQuery(
    StageRunOpTestBase, ProvisioningMQTTTranslationStageTestConfig
):
    @pytest.fixture
    def op(self, mocker):
        return pipeline_ops_base.RequestOperation(
            request_type=pipeline_constant.QUERY,
            method="GET",
            resource_location="/",
            query_params={"operation_id": "fake_op_id"},
            request_body="some body",
            request_id="fake_request_id",
            callback=mocker.MagicMock(),
        )

    @pytest.mark.it("Derives the Provisioning Query Request topic using the op's details")
    def test_register_request_topic(self, mocker, stage, op, mock_mqtt_topic):
        stage.run_op(op)

        assert mock_mqtt_topic.get_query_topic_for_publish.call_count == 1
        assert mock_mqtt_topic.get_query_topic_for_publish.call_args == mocker.call(
            request_id=op.request_id, operation_id=op.query_params["operation_id"]
        )

    @pytest.mark.it(
        "Sends a new MQTTPublishOperation down the pipeline with the original op's request body and the derived topic string"
    )
    def test_sends_mqtt_publish_down(self, mocker, stage, op, mock_mqtt_topic):
        stage.run_op(op)

        assert stage.send_op_down.call_count == 1
        new_op = stage.send_op_down.call_args[0][0]
        assert isinstance(new_op, pipeline_ops_mqtt.MQTTPublishOperation)
        assert new_op.topic == mock_mqtt_topic.get_query_topic_for_publish.return_value
        assert new_op.payload == op.request_body

    @pytest.mark.it("Completes the original op upon completion of the new MQTTPbulishOperation")
    def test_complete_resulting_op(self, stage, op, op_error):
        stage.run_op(op)
        assert not op.completed
        assert op.error is None

        assert stage.send_op_down.call_count == 1
        new_op = stage.send_op_down.call_args[0][0]
        assert isinstance(new_op, pipeline_ops_mqtt.MQTTPublishOperation)

        new_op.complete(error=op_error)

        assert new_op.completed
        assert new_op.error is op_error
        assert op.completed
        assert op.error is op_error


@pytest.mark.describe(
    "ProvisioningMQTTTranslationStage - .run_op() -- Called with RequestOperation (Unsupported Request Type)"
)
class TestProvisioningMQTTTranslationStageRunOpWithRequestOperationUnsupportedType(
    StageRunOpTestBase, ProvisioningMQTTTranslationStageTestConfig
):
    @pytest.fixture
    def op(self, mocker):
        return pipeline_ops_base.RequestOperation(
            request_type="FAKE_REQUEST_TYPE",
            method="GET",
            resource_location="/",
            request_body="some body",
            request_id="fake_request_id",
            callback=mocker.MagicMock(),
        )

    @pytest.mark.it("Completes the operation with an OperationError failure")
    def test_fail(self, mocker, stage, op):
        assert not op.completed
        assert op.error is None

        stage.run_op(op)

        assert op.completed
        assert isinstance(op.error, pipeline_exceptions.OperationError)


@pytest.mark.describe(
    "ProvisioningMQTTTranslationStage - .run_op() -- Called with EnableFeatureOperation"
)
class TestProvisioningMQTTTranslationStageRunOpWithEnableFeatureOperation(
    StageRunOpTestBase, ProvisioningMQTTTranslationStageTestConfig
):
    @pytest.fixture
    def op(self, mocker):
        return pipeline_ops_base.EnableFeatureOperation(
            feature_name=pipeline_constant.REGISTER, callback=mocker.MagicMock()
        )

    @pytest.mark.it(
        "Sends a new MQTTSubscribeOperation down the pipeline, containing the subscription topic for Register, if Register is the feature being enabled"
    )
    def test_mqtt_subscribe_sent_down(self, mocker, op, stage, mock_mqtt_topic):
        stage.run_op(op)

        # Topic was derived as expected
        assert mock_mqtt_topic.get_register_topic_for_subscribe.call_count == 1
        assert mock_mqtt_topic.get_register_topic_for_subscribe.call_args == mocker.call()

        # New op was sent down
        assert stage.send_op_down.call_count == 1
        new_op = stage.send_op_down.call_args[0][0]
        assert isinstance(new_op, pipeline_ops_mqtt.MQTTSubscribeOperation)

        # New op has the expected topic
        assert new_op.topic == mock_mqtt_topic.get_register_topic_for_subscribe.return_value

    @pytest.mark.it("Completes the original op upon completion of the new MQTTSubscribeOperation")
    def test_complete_resulting_op(self, stage, op, op_error):
        stage.run_op(op)
        assert not op.completed
        assert op.error is None

        assert stage.send_op_down.call_count == 1
        new_op = stage.send_op_down.call_args[0][0]

        new_op.complete(error=op_error)

        assert new_op.completed
        assert new_op.error is op_error
        assert op.completed
        assert op.error is op_error

    @pytest.mark.it(
        "Completes the operation with an OperationError failure if the feature being enabled is of any type other than Register"
    )
    def test_unsupported_feature(self, stage, op):
        op.feature_name = "invalid feature"
        assert not op.completed
        assert op.error is None

        stage.run_op(op)

        assert op.completed
        assert isinstance(op.error, pipeline_exceptions.OperationError)


@pytest.mark.describe(
    "ProvisioningMQTTTranslationStage - .run_op() -- Called with DisableFeatureOperation"
)
class TestProvisioningMQTTTranslationStageRunOpWithDisableFeatureOperation(
    StageRunOpTestBase, ProvisioningMQTTTranslationStageTestConfig
):
    @pytest.fixture
    def op(self, mocker):
        return pipeline_ops_base.DisableFeatureOperation(
            feature_name=pipeline_constant.REGISTER, callback=mocker.MagicMock()
        )

    @pytest.mark.it(
        "Sends a new MQTTUnsubscribeOperation down the pipeline, containing the subscription topic for Register, if Register is the feature being disabled"
    )
    def test_mqtt_unsubscribe_sent_down(self, mocker, op, stage, mock_mqtt_topic):
        stage.run_op(op)

        # Topic was derived as expected
        assert mock_mqtt_topic.get_register_topic_for_subscribe.call_count == 1
        assert mock_mqtt_topic.get_register_topic_for_subscribe.call_args == mocker.call()

        # New op was sent down
        assert stage.send_op_down.call_count == 1
        new_op = stage.send_op_down.call_args[0][0]
        assert isinstance(new_op, pipeline_ops_mqtt.MQTTUnsubscribeOperation)

        # New op has the expected topic
        assert new_op.topic == mock_mqtt_topic.get_register_topic_for_subscribe.return_value

    @pytest.mark.it("Completes the original op upon completion of the new MQTTUnsubscribeOperation")
    def test_complete_resulting_op(self, stage, op, op_error):
        stage.run_op(op)
        assert not op.completed
        assert op.error is None

        assert stage.send_op_down.call_count == 1
        new_op = stage.send_op_down.call_args[0][0]

        new_op.complete(error=op_error)

        assert new_op.completed
        assert new_op.error is op_error
        assert op.completed
        assert op.error is op_error

    @pytest.mark.it(
        "Completes the operation with an OperationError failure if the feature being disabled is of any type other than Register"
    )
    def test_unsupported_feature(self, stage, op):
        op.feature_name = "invalid feature"
        assert not op.completed
        assert op.error is None

        stage.run_op(op)

        assert op.completed
        assert isinstance(op.error, pipeline_exceptions.OperationError)


@pytest.mark.describe(
    "IoTHubMQTTTranslationStage - .run_op() -- Called with other arbitrary operation"
)
class TestProvisioningMQTTTranslationStageRunOpWithArbitraryOperation(
    StageRunOpTestBase, ProvisioningMQTTTranslationStageTestConfig
):
    @pytest.fixture
    def op(self, arbitrary_op):
        return arbitrary_op

    @pytest.mark.it("Sends the operation down the pipeline")
    def test_sends_op_down(self, mocker, stage, op):
        stage.run_op(op)

        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(op)


@pytest.mark.it(
    "IoTHubMQTTTranslationStage - .handle_pipeline_event() -- Called with IncomingMQTTMessageEvent (DPS Response Topic)"
)
class TestProvisioningMQTTTranslationStageHandlePipelineEventWithIncomingMQTTMessageEventDPSResponseTopic(
    StageHandlePipelineEventTestBase, ProvisioningMQTTTranslationStageTestConfig
):
    @pytest.fixture
    def status(self):
        return 200

    @pytest.fixture
    def rid(self):
        return "3226c2f7-3d30-425c-b83b-0c34335f8220"

    @pytest.fixture(params=["With retry-after", "No retry-after"])
    def retry_after(self, request):
        if request.param == "With retry-after":
            return "1234"
        else:
            return None

    @pytest.fixture
    def event(self, status, rid, retry_after):
        topic = "$dps/registrations/res/{status}/?$rid={rid}".format(status=status, rid=rid)
        if retry_after:
            topic = topic + "&retry-after={}".format(retry_after)
        return pipeline_events_mqtt.IncomingMQTTMessageEvent(topic=topic, payload=b"some payload")

    @pytest.mark.it(
        "Sends a ResponseEvent up the pipeline containing the original event's payload and values extracted from the topic string"
    )
    def test_response_event(self, event, stage, status, rid, retry_after):
        stage.handle_pipeline_event(event)

        assert stage.send_event_up.call_count == 1
        new_event = stage.send_event_up.call_args[0][0]
        assert isinstance(new_event, pipeline_events_base.ResponseEvent)
        assert new_event.status_code == status
        assert new_event.request_id == rid
        assert new_event.retry_after == retry_after
        assert new_event.response_body == event.payload


@pytest.mark.describe(
    "ProvisioningMQTTTranslationStage - .handle_pipeline_event() -- Called with IncomingMQTTMessaveEvent (Unrecognized topic string)"
)
class TestProvisioningMQTTTranslationStageHandlePipelineEventWithIncomingMQTTMessageEventUnknownTopicString(
    StageHandlePipelineEventTestBase, ProvisioningMQTTTranslationStageTestConfig
):
    @pytest.fixture
    def event(self):
        topic = "not a real topic"
        return pipeline_events_mqtt.IncomingMQTTMessageEvent(topic=topic, payload=b"some payload")

    @pytest.mark.it("Sends the event up the pipeline")
    def test_sends_up(self, event, stage):
        stage.handle_pipeline_event(event)

        assert stage.send_event_up.call_count == 1
        assert stage.send_event_up.call_args[0][0] == event


@pytest.mark.describe(
    "ProvisioningMQTTTranslationStage - .handle_pipeline_event() -- Called with other arbitrary event"
)
class TestProvisioningMQTTTranslationStageHandlePipelineEventWithArbitraryEvent(
    StageHandlePipelineEventTestBase, ProvisioningMQTTTranslationStageTestConfig
):
    @pytest.fixture
    def event(self, arbitrary_event):
        return arbitrary_event

    @pytest.mark.it("Sends the event up the pipeline")
    def test_sends_up(self, event, stage):
        stage.handle_pipeline_event(event)

        assert stage.send_event_up.call_count == 1
        assert stage.send_event_up.call_args[0][0] == event
