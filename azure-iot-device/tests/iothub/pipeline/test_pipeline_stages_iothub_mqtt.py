# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import logging
import pytest
import json
import sys
import six.moves.urllib as urllib
from azure.iot.device.common.pipeline import (
    pipeline_events_base,
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
    config,
    mqtt_topic_iothub,
)
from azure.iot.device.iothub.pipeline.exceptions import OperationError, PipelineError
from azure.iot.device.iothub.models.message import Message
from azure.iot.device.iothub.models.methods import MethodRequest, MethodResponse
from tests.common.pipeline.helpers import StageRunOpTestBase, StageHandlePipelineEventTestBase
from tests.common.pipeline import pipeline_stage_test
from azure.iot.device import constant as pkg_constant, user_agent

logging.basicConfig(level=logging.DEBUG)
this_module = sys.modules[__name__]
pytestmark = pytest.mark.usefixtures("fake_pipeline_thread", "mock_mqtt_topic")


@pytest.fixture
def mock_mqtt_topic(mocker):
    # Don't mock the whole module, just mock what we want to (which is most of it).
    # Mocking out the get_x_topic style functions is useful, but the ones that
    # match patterns and return bools (is_x_topic) making testing annoying if mocked.
    mocker.patch.object(mqtt_topic_iothub, "get_telemetry_topic_for_publish")
    mocker.patch.object(mqtt_topic_iothub, "get_method_topic_for_publish")
    mocker.patch.object(mqtt_topic_iothub, "get_twin_topic_for_publish")
    mocker.patch.object(mqtt_topic_iothub, "get_c2d_topic_for_subscribe")
    mocker.patch.object(mqtt_topic_iothub, "get_input_topic_for_subscribe")
    mocker.patch.object(mqtt_topic_iothub, "get_method_topic_for_subscribe")
    mocker.patch.object(mqtt_topic_iothub, "get_twin_response_topic_for_subscribe")
    mocker.patch.object(mqtt_topic_iothub, "get_twin_patch_topic_for_subscribe")
    mocker.patch.object(mqtt_topic_iothub, "encode_message_properties_in_topic")
    mocker.patch.object(mqtt_topic_iothub, "extract_message_properties_from_topic")
    # It's kind of weird that we return the (unmocked) module, but it's easier this way,
    # and since it's a module, not a function, we'd never treat it like a mock anyway
    # (you don't check the call count of a module)
    return mqtt_topic_iothub


@pytest.fixture(params=[True, False], ids=["With error", "No error"])
def op_error(request, arbitrary_exception):
    if request.param:
        return arbitrary_exception
    else:
        return None


# NOTE: This fixutre is defined out here rather than on a class because it is used for both
# EnableFeatureOperation and DisableFeatureOperation tests
@pytest.fixture
def expected_mqtt_topic_fn(mock_mqtt_topic, iothub_pipeline_feature):
    if iothub_pipeline_feature == constant.C2D_MSG:
        return mock_mqtt_topic.get_c2d_topic_for_subscribe
    elif iothub_pipeline_feature == constant.INPUT_MSG:
        return mock_mqtt_topic.get_input_topic_for_subscribe
    elif iothub_pipeline_feature == constant.METHODS:
        return mock_mqtt_topic.get_method_topic_for_subscribe
    elif iothub_pipeline_feature == constant.TWIN:
        return mock_mqtt_topic.get_twin_response_topic_for_subscribe
    elif iothub_pipeline_feature == constant.TWIN_PATCHES:
        return mock_mqtt_topic.get_twin_patch_topic_for_subscribe
    else:
        # This shouldn't happen
        assert False


# NOTE: This fixutre is defined out here rather than on a class because it is used for both
# EnableFeatureOperation and DisableFeatureOperation tests
@pytest.fixture
def expected_mqtt_topic_fn_call(mocker, iothub_pipeline_feature, stage):
    if iothub_pipeline_feature == constant.C2D_MSG:
        return mocker.call(stage.pipeline_root.pipeline_configuration.device_id)
    elif iothub_pipeline_feature == constant.INPUT_MSG:
        return mocker.call(
            stage.pipeline_root.pipeline_configuration.device_id,
            stage.pipeline_root.pipeline_configuration.module_id,
        )
    else:
        return mocker.call()


class IoTHubMQTTTranslationStageTestConfig(object):
    @pytest.fixture
    def cls_type(self):
        return pipeline_stages_iothub_mqtt.IoTHubMQTTTranslationStage

    @pytest.fixture
    def init_kwargs(self):
        return {}

    @pytest.fixture
    def pipeline_config(self, mocker):
        # auth type shouldn't matter for this stage, so just give it a fake sastoken for now.
        # can manually add extra fields (e.g. module id) as necessary
        cfg = config.IoTHubPipelineConfig(
            hostname="http://my.hostname", device_id="my_device", sastoken=mocker.MagicMock()
        )
        return cfg

    @pytest.fixture
    def stage(self, mocker, cls_type, init_kwargs, pipeline_config):
        stage = cls_type(**init_kwargs)
        stage.pipeline_root = mocker.MagicMock()
        stage.pipeline_root.pipeline_configuration = pipeline_config
        stage.send_op_down = mocker.MagicMock()
        stage.send_event_up = mocker.MagicMock()
        return stage


pipeline_stage_test.add_base_pipeline_stage_tests(
    test_module=this_module,
    stage_class_under_test=pipeline_stages_iothub_mqtt.IoTHubMQTTTranslationStage,
    stage_test_config_class=IoTHubMQTTTranslationStageTestConfig,
)


@pytest.mark.describe(
    "IoTHubMQTTTranslationStage - .run_op() -- Called with InitializePipelineOperation (Pipeline has Device Configuration)"
)
class TestIoTHubMQTTTranslationStageRunOpWithInitializePipelineOperationOnDevice(
    StageRunOpTestBase, IoTHubMQTTTranslationStageTestConfig
):
    @pytest.fixture
    def op(self, mocker):
        return pipeline_ops_base.InitializePipelineOperation(callback=mocker.MagicMock())

    @pytest.mark.it("Derives the MQTT client id, and sets it on the op")
    def test_client_id(self, stage, op, pipeline_config):
        assert not hasattr(op, "client_id")
        stage.run_op(op)

        assert op.client_id == pipeline_config.device_id

    @pytest.mark.it("Derives the MQTT username, and sets it on the op")
    @pytest.mark.parametrize(
        "cust_product_info",
        [
            pytest.param("", id="No custom product info"),
            pytest.param("my-product-info", id="With custom product info"),
            pytest.param("my$product$info", id="With custom product info (URL encoding required)"),
        ],
    )
    def test_username(self, stage, op, pipeline_config, cust_product_info):
        pipeline_config.product_info = cust_product_info
        assert not hasattr(op, "username")
        stage.run_op(op)

        expected_username = "{hostname}/{client_id}/?api-version={api_version}&DeviceClientType={user_agent}{custom_product_info}".format(
            hostname=pipeline_config.hostname,
            client_id=pipeline_config.device_id,
            api_version=pkg_constant.IOTHUB_API_VERSION,
            user_agent=urllib.parse.quote(user_agent.get_iothub_user_agent(), safe=""),
            custom_product_info=urllib.parse.quote(pipeline_config.product_info, safe=""),
        )
        assert op.username == expected_username

    @pytest.mark.it(
        "ALWAYS uses the pipeline configuration's hostname in the MQTT username and NEVER the gateway_hostname"
    )
    def test_hostname_vs_gateway_hostname(self, stage, op, pipeline_config):
        # NOTE: this is a sanity check test. There's no reason it should ever be using
        # gateway hostname rather than hostname, but these are easily confused fields, so
        # this test has been included to catch any possible errors down the road
        pipeline_config.hostname = "http://my.hostname"
        pipeline_config.gateway_hostname = "http://my.gateway.hostname"
        stage.run_op(op)

        assert pipeline_config.hostname in op.username
        assert pipeline_config.gateway_hostname not in op.username

    @pytest.mark.it("Sends the op down the pipeline")
    def test_sends_down(self, mocker, stage, op):
        stage.run_op(op)
        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(op)


@pytest.mark.describe(
    "IoTHubMQTTTranslationStage - .run_op() -- Called with InitializePipelineOperation (Pipeline has Module Configuration)"
)
class TestIoTHubMQTTTranslationStageRunOpWithInitializePipelineOperationOnModule(
    StageRunOpTestBase, IoTHubMQTTTranslationStageTestConfig
):
    @pytest.fixture
    def pipeline_config(self, mocker):
        # auth type shouldn't matter for this stage, so just give it a fake sastoken for now.
        cfg = config.IoTHubPipelineConfig(
            hostname="http://my.hostname",
            device_id="my_device",
            module_id="my_module",
            sastoken=mocker.MagicMock(),
        )
        return cfg

    @pytest.fixture
    def op(self, mocker):
        return pipeline_ops_base.InitializePipelineOperation(callback=mocker.MagicMock())

    @pytest.mark.it("Derives the MQTT client id, and sets it on the op")
    def test_client_id(self, stage, op, pipeline_config):
        stage.run_op(op)

        expected_client_id = "{device_id}/{module_id}".format(
            device_id=pipeline_config.device_id, module_id=pipeline_config.module_id
        )
        assert op.client_id == expected_client_id

    @pytest.mark.it("Derives the MQTT username, and sets it on the op")
    @pytest.mark.parametrize(
        "cust_product_info",
        [
            pytest.param("", id="No custom product info"),
            pytest.param("my-product-info", id="With custom product info"),
            pytest.param("my$product$info", id="With custom product info (URL encoding required)"),
        ],
    )
    def test_username(self, stage, op, pipeline_config, cust_product_info):
        pipeline_config.product_info = cust_product_info
        stage.run_op(op)

        expected_client_id = "{device_id}/{module_id}".format(
            device_id=pipeline_config.device_id, module_id=pipeline_config.module_id
        )
        expected_username = "{hostname}/{client_id}/?api-version={api_version}&DeviceClientType={user_agent}{custom_product_info}".format(
            hostname=pipeline_config.hostname,
            client_id=expected_client_id,
            api_version=pkg_constant.IOTHUB_API_VERSION,
            user_agent=urllib.parse.quote(user_agent.get_iothub_user_agent(), safe=""),
            custom_product_info=urllib.parse.quote(pipeline_config.product_info, safe=""),
        )
        assert op.username == expected_username

    @pytest.mark.it(
        "ALWAYS uses the pipeline configuration's hostname in the MQTT username and NEVER the gateway_hostname"
    )
    def test_hostname_vs_gateway_hostname(self, stage, op, pipeline_config):
        # NOTE: this is a sanity check test. There's no reason it should ever be using
        # gateway hostname rather than hostname, but these are easily confused fields, so
        # this test has been included to catch any possible errors down the road
        pipeline_config.hostname = "http://my.hostname"
        pipeline_config.gateway_hostname = "http://my.gateway.hostname"
        stage.run_op(op)

        assert pipeline_config.hostname in op.username
        assert pipeline_config.gateway_hostname not in op.username

    @pytest.mark.it("Sends the op down the pipeline")
    def test_sends_down(self, mocker, stage, op):
        stage.run_op(op)
        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(op)


# CT-TODO: parametrize all of these run op tests to pivot on device/module configs
@pytest.mark.describe(
    "IoTHubMQTTTranslationStage - .run_op() -- Called with SendD2CMessageOperation"
)
class TestIoTHubMQTTTranslationStageRunOpWithSendD2CMessageOperation(
    StageRunOpTestBase, IoTHubMQTTTranslationStageTestConfig
):
    @pytest.fixture
    def op(self, mocker):
        return pipeline_ops_iothub.SendD2CMessageOperation(
            message=Message("my message"), callback=mocker.MagicMock()
        )

    @pytest.mark.it(
        "Derives the IoTHub telemetry topic from the device/module details, and encodes the op's message's properties in the resulting topic string"
    )
    def test_telemetry_topic(self, mocker, stage, op, pipeline_config, mock_mqtt_topic):
        # Although this requirement refers to message properties, we don't actually have to
        # parametrize the op to have them, because the entire logic of encoding message properties
        # is handled by the mocked out mqtt_topic_iothub library, so whether or not our fixture
        # has message properties on the message or not is irrelevant.
        stage.run_op(op)

        assert mock_mqtt_topic.get_telemetry_topic_for_publish.call_count == 1
        assert mock_mqtt_topic.get_telemetry_topic_for_publish.call_args == mocker.call(
            device_id=pipeline_config.device_id, module_id=pipeline_config.module_id
        )
        assert mock_mqtt_topic.encode_message_properties_in_topic.call_count == 1
        assert mock_mqtt_topic.encode_message_properties_in_topic.call_args == mocker.call(
            op.message, mock_mqtt_topic.get_telemetry_topic_for_publish.return_value
        )

    @pytest.mark.it(
        "Sends a new MQTTPublishOperation down the pipeline with the message data from the original op and the derived topic string"
    )
    def test_sends_mqtt_publish_op_down(self, mocker, stage, op, mock_mqtt_topic):
        stage.run_op(op)

        assert stage.send_op_down.call_count == 1
        new_op = stage.send_op_down.call_args[0][0]
        assert isinstance(new_op, pipeline_ops_mqtt.MQTTPublishOperation)
        assert new_op.topic == mock_mqtt_topic.encode_message_properties_in_topic.return_value
        assert new_op.payload == op.message.data

    @pytest.mark.it("Completes the original op upon completion of the new MQTTPublishOperation")
    def test_complete_resulting_op(self, stage, op, op_error):
        stage.run_op(op)
        assert not op.completed

        assert stage.send_op_down.call_count == 1
        new_op = stage.send_op_down.call_args[0][0]

        new_op.complete(error=op_error)

        assert new_op.completed
        assert new_op.error is op_error
        assert op.completed
        assert op.error is op_error


@pytest.mark.describe(
    "IoTHubMQTTTranslationStage - .run_op() -- Called with SendOutputMessageOperation"
)
class TestIoTHubMQTTTranslationStageRunOpWithSendOutputMessageOperation(
    StageRunOpTestBase, IoTHubMQTTTranslationStageTestConfig
):
    @pytest.fixture
    def op(self, mocker):
        return pipeline_ops_iothub.SendOutputMessageOperation(
            message=Message("my message"), callback=mocker.MagicMock()
        )

    @pytest.mark.it(
        "Derives the IoTHub telemetry topic using the device/module details, and encodes the op's message's properties in the resulting topic string"
    )
    def test_telemetry_topic(self, mocker, stage, op, pipeline_config, mock_mqtt_topic):
        # Although this requirement refers to message properties, we don't actually have to
        # parametrize the op to have them, because the entire logic of encoding message properties
        # is handled by the mocked out mqtt_topic_iothub library, so whether or not our fixture
        # has message properties on the message or not is irrelevant.
        stage.run_op(op)

        assert mock_mqtt_topic.get_telemetry_topic_for_publish.call_count == 1
        assert mock_mqtt_topic.get_telemetry_topic_for_publish.call_args == mocker.call(
            device_id=pipeline_config.device_id, module_id=pipeline_config.module_id
        )
        assert mock_mqtt_topic.encode_message_properties_in_topic.call_count == 1
        assert mock_mqtt_topic.encode_message_properties_in_topic.call_args == mocker.call(
            op.message, mock_mqtt_topic.get_telemetry_topic_for_publish.return_value
        )

    @pytest.mark.it(
        "Sends a new MQTTPublishOperation down the pipeline with the message data from the original op and the derived topic string"
    )
    def test_sends_mqtt_publish_op_down(self, mocker, stage, op, mock_mqtt_topic):
        stage.run_op(op)

        assert stage.send_op_down.call_count == 1
        new_op = stage.send_op_down.call_args[0][0]
        assert isinstance(new_op, pipeline_ops_mqtt.MQTTPublishOperation)
        assert new_op.topic == mock_mqtt_topic.encode_message_properties_in_topic.return_value
        assert new_op.payload == op.message.data

    @pytest.mark.it("Completes the original op upon completion of the new MQTTPublishOperation")
    def test_complete_resulting_op(self, stage, op, op_error):
        stage.run_op(op)
        assert not op.completed

        assert stage.send_op_down.call_count == 1
        new_op = stage.send_op_down.call_args[0][0]

        new_op.complete(error=op_error)

        assert new_op.completed
        assert new_op.error is op_error
        assert op.completed
        assert op.error is op_error


@pytest.mark.describe(
    "IoTHubMQTTTranslationStage - .run_op() -- Called with SendMethodResponseOperation"
)
class TestIoTHubMQTTTranslationStageWithSendMethodResponseOperation(
    StageRunOpTestBase, IoTHubMQTTTranslationStageTestConfig
):
    @pytest.fixture
    def op(self, mocker):
        method_response = MethodResponse(
            request_id="fake_request_id", status=200, payload={"some": "json"}
        )
        return pipeline_ops_iothub.SendMethodResponseOperation(
            method_response=method_response, callback=mocker.MagicMock()
        )

    @pytest.mark.it("Derives the IoTHub telemetry topic using the op's request id and status")
    def test_telemtry_topic(self, mocker, stage, op, mock_mqtt_topic):
        stage.run_op(op)

        assert mock_mqtt_topic.get_method_topic_for_publish.call_count == 1
        assert mock_mqtt_topic.get_method_topic_for_publish.call_args == mocker.call(
            op.method_response.request_id, op.method_response.status
        )

    @pytest.mark.it(
        "Sends a new MQTTPublishOperation down the pipeline with the original op's payload in JSON string format, and the derived topic string"
    )
    @pytest.mark.parametrize(
        "payload, expected_string",
        [
            pytest.param(None, "null", id="No payload"),
            pytest.param({"some": "json"}, '{"some": "json"}', id="Dictionary payload"),
            pytest.param("payload", '"payload"', id="String payload"),
        ],
    )
    def test_sends_mqtt_publish_op_down(
        self, mocker, stage, op, mock_mqtt_topic, payload, expected_string
    ):
        op.method_response.payload = payload
        stage.run_op(op)

        assert stage.send_op_down.call_count == 1
        new_op = stage.send_op_down.call_args[0][0]
        assert isinstance(new_op, pipeline_ops_mqtt.MQTTPublishOperation)
        assert new_op.topic == mock_mqtt_topic.get_method_topic_for_publish.return_value
        assert new_op.payload == expected_string

    @pytest.mark.it("Completes the original op upon completion of the new MQTTPublishOperation")
    def test_complete_resulting_op(self, stage, op, op_error):
        stage.run_op(op)
        assert not op.completed

        assert stage.send_op_down.call_count == 1
        new_op = stage.send_op_down.call_args[0][0]

        new_op.complete(error=op_error)

        assert new_op.completed
        assert new_op.error is op_error
        assert op.completed
        assert op.error is op_error


@pytest.mark.describe(
    "IoTHubMQTTTranslationStage - .run_op() -- Called with EnableFeatureOperation"
)
class TestIoTHubMQTTTranslationStageRunOpWithEnableFeatureOperation(
    StageRunOpTestBase, IoTHubMQTTTranslationStageTestConfig
):
    @pytest.fixture
    def op(self, mocker, iothub_pipeline_feature):
        return pipeline_ops_base.EnableFeatureOperation(
            feature_name=iothub_pipeline_feature, callback=mocker.MagicMock()
        )

    @pytest.mark.it(
        "Sends a new MQTTSubscribeOperation down the pipeline, containing the subscription topic string corresponding to the feature being enabled"
    )
    def test_mqtt_subscribe_sent_down(
        self, op, stage, expected_mqtt_topic_fn, expected_mqtt_topic_fn_call
    ):
        stage.run_op(op)

        # Topic was derived as expected
        assert expected_mqtt_topic_fn.call_count == 1
        assert expected_mqtt_topic_fn.call_args == expected_mqtt_topic_fn_call

        # New op was sent down
        assert stage.send_op_down.call_count == 1
        new_op = stage.send_op_down.call_args[0][0]
        assert isinstance(new_op, pipeline_ops_mqtt.MQTTSubscribeOperation)

        # New op has the expected topic
        assert new_op.topic == expected_mqtt_topic_fn.return_value

    @pytest.mark.it("Completes the original op upon completion of the new MQTTSubscribeOperation")
    def test_complete_resulting_op(self, stage, op, op_error):
        stage.run_op(op)
        assert not op.completed

        assert stage.send_op_down.call_count == 1
        new_op = stage.send_op_down.call_args[0][0]

        new_op.complete(error=op_error)

        assert new_op.completed
        assert new_op.error is op_error
        assert op.completed
        assert op.error is op_error


@pytest.mark.describe(
    "IoTHubMQTTTranslationStage - .run_op() -- Called with DisableFeatureOperation"
)
class TestIoTHubMQTTTranslationStageRunOpWithDisableFeatureOperation(
    StageRunOpTestBase, IoTHubMQTTTranslationStageTestConfig
):
    @pytest.fixture
    def op(self, mocker, iothub_pipeline_feature):
        return pipeline_ops_base.DisableFeatureOperation(
            feature_name=iothub_pipeline_feature, callback=mocker.MagicMock()
        )

    @pytest.mark.it(
        "Sends a new MQTTUnsubscribeOperation down the pipeline, containing the subscription topic string corresponding to the feature being disabled"
    )
    def test_mqtt_unsubscribe_sent_down(
        self, op, stage, expected_mqtt_topic_fn, expected_mqtt_topic_fn_call
    ):
        stage.run_op(op)

        # Topic was derived as expected
        assert expected_mqtt_topic_fn.call_count == 1
        assert expected_mqtt_topic_fn.call_args == expected_mqtt_topic_fn_call

        # New op was sent down
        assert stage.send_op_down.call_count == 1
        new_op = stage.send_op_down.call_args[0][0]
        assert isinstance(new_op, pipeline_ops_mqtt.MQTTUnsubscribeOperation)

        # New op has the expected topic
        assert new_op.topic == expected_mqtt_topic_fn.return_value

    @pytest.mark.it("Completes the original op upon completion of the new MQTTUnsubscribeOperation")
    def test_complete_resulting_op(self, stage, op, op_error):
        stage.run_op(op)
        assert not op.completed

        assert stage.send_op_down.call_count == 1
        new_op = stage.send_op_down.call_args[0][0]

        new_op.complete(error=op_error)

        assert new_op.completed
        assert new_op.error is op_error
        assert op.completed
        assert op.error is op_error


@pytest.mark.describe("IoTHubMQTTTranslationStage - .run_op() -- Called with RequestOperation")
class TestIoTHubMQTTTranslationStageWithRequestOperation(
    StageRunOpTestBase, IoTHubMQTTTranslationStageTestConfig
):
    @pytest.fixture
    def op(self, mocker):
        # Only request operation supported at present by this stage is TWIN. If this changes,
        # logic in this whole test class must become more robust
        return pipeline_ops_base.RequestOperation(
            request_type=constant.TWIN,
            method="GET",
            resource_location="/",
            request_body=" ",
            request_id="fake_request_id",
            callback=mocker.MagicMock(),
        )

    @pytest.mark.it(
        "Derives the IoTHub Twin Request topic using the op's details, if the op is a Twin Request"
    )
    def test_twin_request_topic(self, mocker, stage, op, mock_mqtt_topic):
        stage.run_op(op)

        assert mock_mqtt_topic.get_twin_topic_for_publish.call_count == 1
        assert mock_mqtt_topic.get_twin_topic_for_publish.call_args == mocker.call(
            method=op.method, resource_location=op.resource_location, request_id=op.request_id
        )

    @pytest.mark.it(
        "Completes the operation with an OperationError failure if the op is any type of request other than a Twin Request"
    )
    def test_invalid_op(self, mocker, stage, op):
        # Okay, so technically this does'nt prove it does this if it's ANY other type of request, but that's pretty much
        # impossible to disprove in a black-box test, because there are infinite possibilities in theory
        op.request_type = "Some_other_type"
        stage.run_op(op)
        assert op.completed
        assert isinstance(op.error, OperationError)

    @pytest.mark.it(
        "Sends a new MQTTPublishOperation down the pipeline with the original op's request body and the derived topic string"
    )
    def test_sends_mqtt_publish_op_down(self, mocker, stage, op, mock_mqtt_topic):
        stage.run_op(op)

        assert stage.send_op_down.call_count == 1
        new_op = stage.send_op_down.call_args[0][0]
        assert isinstance(new_op, pipeline_ops_mqtt.MQTTPublishOperation)
        assert new_op.topic == mock_mqtt_topic.get_twin_topic_for_publish.return_value
        assert new_op.payload == op.request_body

    @pytest.mark.it("Completes the original op upon completion of the new MQTTPublishOperation")
    def test_complete_resulting_op(self, stage, op, op_error):
        stage.run_op(op)
        assert not op.completed

        assert stage.send_op_down.call_count == 1
        new_op = stage.send_op_down.call_args[0][0]

        new_op.complete(error=op_error)

        assert new_op.completed
        assert new_op.error is op_error
        assert op.completed
        assert op.error is op_error


@pytest.mark.describe(
    "IoTHubMQTTTranslationStage - .run_op() -- Called with other arbitrary operation"
)
class TestIoTHubMQTTTranslationStageRunOpWithAribtraryOperation(
    StageRunOpTestBase, IoTHubMQTTTranslationStageTestConfig
):
    @pytest.fixture
    def op(self, arbitrary_op):
        return arbitrary_op

    @pytest.mark.it("Sends the operation down the pipeline")
    def test_sends_op_down(self, mocker, stage, op):
        stage.run_op(op)

        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(op)


@pytest.mark.describe(
    "IoTHubMQTTTranslationStage - .handle_pipeline_event() -- Called with IncomingMQTTMessageEvent (C2D topic string)"
)
class TestIoTHubMQTTTranslationStageHandlePipelineEventWithIncomingMQTTMessageEventC2DTopic(
    StageHandlePipelineEventTestBase, IoTHubMQTTTranslationStageTestConfig
):
    @pytest.fixture
    def event(self, pipeline_config):
        # topic device id MATCHES THE PIPELINE CONFIG
        topic = "devices/{device_id}/messages/devicebound/%24.mid=6b822696-f75a-46f5-8b02-0680db65abf5&%24.to=%2Fdevices%2F{device_id}%2Fmessages%2Fdevicebound".format(
            device_id=pipeline_config.device_id
        )
        return pipeline_events_mqtt.IncomingMQTTMessageEvent(topic=topic, payload="some payload")

    @pytest.mark.it(
        "Creates a Message with the event's payload, and applies any message properties included in the topic"
    )
    def test_message(self, event, stage, mock_mqtt_topic):
        stage.handle_pipeline_event(event)

        # Message properties were extracted from the topic
        # NOTE that because this is mocked, we don't need to test various topics with various properties
        assert mock_mqtt_topic.extract_message_properties_from_topic.call_count == 1
        assert mock_mqtt_topic.extract_message_properties_from_topic.call_args[0][0] == event.topic
        message = mock_mqtt_topic.extract_message_properties_from_topic.call_args[0][1]
        assert isinstance(message, Message)
        # The message contains the event's payload
        assert message.data == event.payload

    @pytest.mark.it(
        "Sends a new C2DMessageEvent up the pipeline, containing the newly created Message"
    )
    def test_c2d_message_event(self, event, stage, mock_mqtt_topic):
        stage.handle_pipeline_event(event)

        # C2DMessageEvent was sent up the pipeline
        assert stage.send_event_up.call_count == 1
        new_event = stage.send_event_up.call_args[0][0]
        assert isinstance(new_event, pipeline_events_iothub.C2DMessageEvent)
        # The C2DMessageEvent contains the same Message that was created from the topic details
        assert mock_mqtt_topic.extract_message_properties_from_topic.call_count == 1
        message = mock_mqtt_topic.extract_message_properties_from_topic.call_args[0][1]
        assert new_event.message is message

    @pytest.mark.it(
        "Sends the original event up the pipeline instead, if the device id in the topic string does not match the client details"
    )
    def test_nonmatching_device_id(self, mocker, event, stage):
        stage.pipeline_root.pipeline_configuration.device_id = "different_device_id"
        stage.handle_pipeline_event(event)

        assert stage.send_event_up.call_count == 1
        assert stage.send_event_up.call_args == mocker.call(event)


@pytest.mark.describe(
    "IoTHubMQTTTranslationStage - .handle_pipeline_event() -- Called with IncomingMQTTMessageEvent (Input Message topic string)"
)
class TestIoTHubMQTTTranslationStageHandlePipelineEventWithIncomingMQTTMessageEventInputTopic(
    StageHandlePipelineEventTestBase, IoTHubMQTTTranslationStageTestConfig
):
    @pytest.fixture
    def pipeline_config(self, mocker):
        cfg = config.IoTHubPipelineConfig(
            hostname="fake_hostname",
            device_id="my_device",
            module_id="my_module",
            sastoken=mocker.MagicMock(),
        )
        return cfg

    @pytest.fixture
    def input_name(self):
        return "some_input"

    @pytest.fixture
    def event(self, pipeline_config, input_name):
        # topic device id MATCHES THE PIPELINE CONFIG
        topic = "devices/{device_id}/modules/{module_id}/inputs/{input_name}/%24.mid=6b822696-f75a-46f5-8b02-0680db65abf5&%24.to=%2Fdevices%2F{device_id}%2Fmodules%2F{module_id}%2Finputs%2F{input_name}".format(
            device_id=pipeline_config.device_id,
            module_id=pipeline_config.module_id,
            input_name=input_name,
        )
        return pipeline_events_mqtt.IncomingMQTTMessageEvent(topic=topic, payload="some payload")

    @pytest.mark.it(
        "Creates a Message with the event's payload, and applies any message properties included in the topic"
    )
    def test_message(self, event, stage, mock_mqtt_topic):
        stage.handle_pipeline_event(event)

        # Message properties were extracted from the topic
        # NOTE that because this is mocked, we don't need to test various topics with various properties
        assert mock_mqtt_topic.extract_message_properties_from_topic.call_count == 1
        assert mock_mqtt_topic.extract_message_properties_from_topic.call_args[0][0] == event.topic
        message = mock_mqtt_topic.extract_message_properties_from_topic.call_args[0][1]
        assert isinstance(message, Message)
        # The message contains the event's payload
        assert message.data == event.payload

    @pytest.mark.it(
        "Sends a new InputMessageEvent up the pipeline, containing the newly created Message and the input name extracted from the topic"
    )
    def test_input_message_event(self, event, stage, mock_mqtt_topic, input_name):
        stage.handle_pipeline_event(event)

        # InputMessageEvent was sent up the pipeline
        assert stage.send_event_up.call_count == 1
        new_event = stage.send_event_up.call_args[0][0]
        assert isinstance(new_event, pipeline_events_iothub.InputMessageEvent)
        # The InputMessageEvent contains the same Message that was created from the topic details
        assert mock_mqtt_topic.extract_message_properties_from_topic.call_count == 1
        message = mock_mqtt_topic.extract_message_properties_from_topic.call_args[0][1]
        assert new_event.message is message
        # The InputMessageEvent contains the same input name from the topic
        assert new_event.input_name == input_name

    @pytest.mark.it(
        "Sends the original event up the pipeline instead, if the the topic string does not match the client details"
    )
    @pytest.mark.parametrize(
        "alt_device_id, alt_module_id",
        [
            pytest.param("different_device_id", None, id="Non-matching device id"),
            pytest.param(None, "different_module_id", id="Non-matching module id"),
            pytest.param(
                "different_device_id",
                "different_module_id",
                id="Non-matching device id AND module id",
            ),
        ],
    )
    def test_nonmatching_ids(self, mocker, event, stage, alt_device_id, alt_module_id):
        if alt_device_id:
            stage.pipeline_root.pipeline_configuration.device_id = alt_device_id
        if alt_module_id:
            stage.pipeline_root.pipeline_configuration.module_id = alt_module_id
        stage.handle_pipeline_event(event)

        assert stage.send_event_up.call_count == 1
        assert stage.send_event_up.call_args == mocker.call(event)


@pytest.mark.describe(
    "IoTHubMQTTTranslationStage - .handle_pipeline_event() -- Called with IncomingMQTTMessageEvent (Method topic string)"
)
class TestIoTHubMQTTTranslationStageHandlePipelineEventWithIncomingMQTTMessageEventMethodTopic(
    StageHandlePipelineEventTestBase, IoTHubMQTTTranslationStageTestConfig
):
    @pytest.fixture
    def method_name(self):
        return "some_method"

    @pytest.fixture
    def rid(self):
        return "1"

    @pytest.fixture
    def event(self, method_name, rid):
        topic = "$iothub/methods/POST/{method_name}/?$rid={rid}".format(
            method_name=method_name, rid=rid
        )
        return pipeline_events_mqtt.IncomingMQTTMessageEvent(
            topic=topic, payload=b'{"some": "json"}'
        )

    @pytest.mark.it(
        "Sends a MethodRequestEvent up the pipeline with a MethodRequest containing values extracted from the event's topic"
    )
    def test_method_request(self, event, stage, method_name, rid):
        stage.handle_pipeline_event(event)

        assert stage.send_event_up.call_count == 1
        new_event = stage.send_event_up.call_args[0][0]
        assert isinstance(new_event, pipeline_events_iothub.MethodRequestEvent)
        assert isinstance(new_event.method_request, MethodRequest)
        assert new_event.method_request.name == method_name
        assert new_event.method_request.request_id == rid
        # This is expanded on in in the next test
        assert new_event.method_request.payload == json.loads(event.payload.decode("utf-8"))

    @pytest.mark.it(
        "Derives the MethodRequestEvent's payload by converting the original event's payload from bytes into a JSON object"
    )
    @pytest.mark.parametrize(
        "original_payload, derived_payload",
        [
            pytest.param(b'{"some": "payload"}', {"some": "payload"}, id="Dictionary JSON"),
            pytest.param(b'"payload"', "payload", id="String JSON"),
            pytest.param(b"1234", 1234, id="Int JSON"),
            pytest.param(b"null", None, id="None JSON"),
        ],
    )
    def test_json_payload(self, event, stage, original_payload, derived_payload):
        event.payload = original_payload
        stage.handle_pipeline_event(event)

        assert stage.send_event_up.call_count == 1
        new_event = stage.send_event_up.call_args[0][0]
        assert isinstance(new_event, pipeline_events_iothub.MethodRequestEvent)
        assert isinstance(new_event.method_request, MethodRequest)

        assert new_event.method_request.payload == derived_payload


@pytest.mark.describe(
    "IoTHubMQTTTranslationStage - .handle_pipeline_event() -- Called with IncomingMQTTMessageEvent (Twin Response topic string)"
)
class TestIoTHubMQTTTranslationStageHandlePipelineEventWithIncomingMQTTMessageEventTwinResponseTopic(
    StageHandlePipelineEventTestBase, IoTHubMQTTTranslationStageTestConfig
):
    @pytest.fixture
    def status(self):
        return 200

    @pytest.fixture
    def rid(self):
        return "d9d7ce4d-3be9-498b-abde-913b81b880e5"

    @pytest.fixture
    def event(self, status, rid):
        topic = "$iothub/twin/res/{status}/?$rid={rid}".format(status=status, rid=rid)
        return pipeline_events_mqtt.IncomingMQTTMessageEvent(topic=topic, payload=b"some_payload")

    @pytest.mark.it(
        "Sends a ResponseEvent up the pipeline containing the original event's payload, and values extracted from the topic string"
    )
    def test_response_event(self, event, stage, status, rid):
        stage.handle_pipeline_event(event)

        assert stage.send_event_up.call_count == 1
        new_event = stage.send_event_up.call_args[0][0]
        assert isinstance(new_event, pipeline_events_base.ResponseEvent)
        assert new_event.status_code == status
        assert new_event.request_id == rid
        assert new_event.response_body == event.payload


@pytest.mark.describe(
    "IoTHubMQTTTranslationStage - .handle_pipeline_event() -- Called with IncomingMQTTMessageEvent (Twin Desired Properties Patch topic string)"
)
class TestIoTHubMQTTTranslationStageHandlePipelineEventWithIncomingMQTTMessageEventTwinDesiredPropertiesPatchTopic(
    StageHandlePipelineEventTestBase, IoTHubMQTTTranslationStageTestConfig
):
    @pytest.fixture
    def event(self):
        topic = "$iothub/twin/PATCH/properties/desired/?$version=1"
        # payload will be overwritten in relevant tests
        return pipeline_events_mqtt.IncomingMQTTMessageEvent(
            topic=topic, payload=b'{"some": "payload"}'
        )

    @pytest.mark.it(
        "Sends a TwinDesiredPropertiesPatchEvent up the pipeline, containing the original event's payload formatted as a JSON-object"
    )
    @pytest.mark.parametrize(
        "original_payload, derived_payload",
        [
            pytest.param(b'{"some": "payload"}', {"some": "payload"}, id="Dictionary JSON"),
            pytest.param(b'"payload"', "payload", id="String JSON"),
            pytest.param(b"1234", 1234, id="Int JSON"),
            pytest.param(b"null", None, id="None JSON"),
        ],
    )
    def test_twin_patch_event(self, event, stage, original_payload, derived_payload):
        event.payload = original_payload
        stage.handle_pipeline_event(event)

        assert stage.send_event_up.call_count == 1
        new_event = stage.send_event_up.call_args[0][0]
        assert isinstance(new_event, pipeline_events_iothub.TwinDesiredPropertiesPatchEvent)
        assert new_event.patch == derived_payload


@pytest.mark.describe(
    "IoTHubMQTTTranslationStage - .handle_pipeline_event() -- Called with IncomingMQTTMessageEvent (Unrecognized topic string)"
)
class TestIoTHubMQTTTranslationStageHandlePipelineEventWithIncomingMQTTMessageEventUnknownTopicString(
    StageHandlePipelineEventTestBase, IoTHubMQTTTranslationStageTestConfig
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
    "IoTHubMQTTTranslationStage - .handle_pipeline_event() -- Called with other arbitrary event"
)
class TestIoTHubMQTTTranslationStageHandlePipelineEventWithArbitraryEvent(
    StageHandlePipelineEventTestBase, IoTHubMQTTTranslationStageTestConfig
):
    @pytest.fixture
    def event(self, arbitrary_event):
        return arbitrary_event

    @pytest.mark.it("Sends the event up the pipeline")
    def test_sends_up(self, event, stage):
        stage.handle_pipeline_event(event)

        assert stage.send_event_up.call_count == 1
        assert stage.send_event_up.call_args[0][0] == event
