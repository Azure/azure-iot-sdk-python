# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
import logging
from azure.iot.device.common.models import X509
from azure.iot.device.provisioning.pipeline.mqtt_pipeline import MQTTPipeline
from tests.common.pipeline import helpers
import json
from azure.iot.device.provisioning.pipeline import constant as dps_constants
from azure.iot.device.provisioning.pipeline import (
    pipeline_stages_provisioning,
    pipeline_stages_provisioning_mqtt,
    pipeline_ops_provisioning,
)
from azure.iot.device.common.pipeline import (
    pipeline_stages_base,
    pipeline_stages_mqtt,
    pipeline_ops_base,
)

logging.basicConfig(level=logging.DEBUG)
pytestmark = pytest.mark.usefixtures("fake_pipeline_thread")


feature = dps_constants.REGISTER


def mock_x509():
    return X509(
        cert_file="fantastic_beasts", key_file="where_to_find_them", pass_phrase="alohomora"
    )


@pytest.fixture
def pipeline_configuration(mocker):
    mock_config = mocker.MagicMock()
    mock_config.sastoken.ttl = 1232  # set for compat
    mock_config.registration_id = "MyPensieve"
    return mock_config


@pytest.fixture
def pipeline(mocker, pipeline_configuration):
    pipeline = MQTTPipeline(pipeline_configuration)
    mocker.patch.object(pipeline._pipeline, "run_op")
    return pipeline


# automatically mock the transport for all tests in this file.
@pytest.fixture(autouse=True)
def mock_mqtt_transport(mocker):
    return mocker.patch(
        "azure.iot.device.common.pipeline.pipeline_stages_mqtt.MQTTTransport", autospec=True
    )


@pytest.mark.describe("MQTTPipeline - Instantiation")
class TestMQTTPipelineInstantiation(object):
    @pytest.mark.it("Begins tracking the enabled/disabled status of responses")
    def test_features(self, pipeline_configuration):
        pipeline = MQTTPipeline(pipeline_configuration)
        pipeline.responses_enabled[feature]
        # No assertion required - if this doesn't raise a KeyError, it is a success

    @pytest.mark.it("Marks responses as disabled")
    def test_features_disabled(self, pipeline_configuration):
        pipeline = MQTTPipeline(pipeline_configuration)
        assert not pipeline.responses_enabled[feature]

    @pytest.mark.it("Sets all handlers to an initial value of None")
    def test_handlers_set_to_none(self, pipeline_configuration):
        pipeline = MQTTPipeline(pipeline_configuration)
        assert pipeline.on_connected is None
        assert pipeline.on_disconnected is None
        assert pipeline.on_message_received is None

    @pytest.mark.it("Configures the pipeline to trigger handlers in response to external events")
    def test_handlers_configured(self, pipeline_configuration):
        pipeline = MQTTPipeline(pipeline_configuration)
        assert pipeline._pipeline.on_pipeline_event_handler is not None
        assert pipeline._pipeline.on_connected_handler is not None
        assert pipeline._pipeline.on_disconnected_handler is not None

    @pytest.mark.it("Configures the pipeline with a series of PipelineStages")
    def test_pipeline_configuration(self, pipeline_configuration):
        pipeline = MQTTPipeline(pipeline_configuration)
        curr_stage = pipeline._pipeline

        expected_stage_order = [
            pipeline_stages_base.PipelineRootStage,
            pipeline_stages_base.SasTokenRenewalStage,
            pipeline_stages_provisioning.RegistrationStage,
            pipeline_stages_provisioning.PollingStatusStage,
            pipeline_stages_base.CoordinateRequestAndResponseStage,
            pipeline_stages_provisioning_mqtt.ProvisioningMQTTTranslationStage,
            pipeline_stages_base.AutoConnectStage,
            pipeline_stages_base.ReconnectStage,
            pipeline_stages_base.ConnectionLockStage,
            pipeline_stages_base.RetryStage,
            pipeline_stages_base.OpTimeoutStage,
            pipeline_stages_mqtt.MQTTTransportStage,
        ]

        # Assert that all PipelineStages are there, and they are in the right order
        for i in range(len(expected_stage_order)):
            expected_stage = expected_stage_order[i]
            assert isinstance(curr_stage, expected_stage)
            curr_stage = curr_stage.next

        # Assert there are no more additional stages
        assert curr_stage is None

    @pytest.mark.it("Runs an InitializePipelineOperation on the pipeline")
    def test_init_pipeline(self, mocker, pipeline_configuration):
        mocker.spy(pipeline_stages_base.PipelineRootStage, "run_op")

        pipeline = MQTTPipeline(pipeline_configuration)

        op = pipeline._pipeline.run_op.call_args[0][1]
        assert pipeline._pipeline.run_op.call_count == 1
        assert isinstance(op, pipeline_ops_base.InitializePipelineOperation)

    @pytest.mark.it(
        "Raises exceptions that occurred in execution upon unsuccessful completion of the InitializePipelineOperation"
    )
    def test_init_pipeline_failure(self, mocker, arbitrary_exception, pipeline_configuration):
        old_run_op = pipeline_stages_base.PipelineRootStage._run_op

        def fail_set_security_client(self, op):
            if isinstance(op, pipeline_ops_base.InitializePipelineOperation):
                op.complete(error=arbitrary_exception)
            else:
                old_run_op(self, op)

        mocker.patch.object(
            pipeline_stages_base.PipelineRootStage,
            "_run_op",
            side_effect=fail_set_security_client,
            autospec=True,
        )

        with pytest.raises(arbitrary_exception.__class__) as e_info:
            MQTTPipeline(pipeline_configuration)
        assert e_info.value is arbitrary_exception


@pytest.mark.describe("MQTTPipeline - .connect()")
class TestMQTTPipelineConnect(object):
    @pytest.mark.it("Runs a ConnectOperation on the pipeline")
    def test_runs_op(self, pipeline, mocker):
        cb = mocker.MagicMock()
        pipeline.connect(callback=cb)
        assert pipeline._pipeline.run_op.call_count == 1
        assert isinstance(
            pipeline._pipeline.run_op.call_args[0][0], pipeline_ops_base.ConnectOperation
        )

    @pytest.mark.it("Triggers the callback upon successful completion of the ConnectOperation")
    def test_op_success_with_callback(self, mocker, pipeline):
        cb = mocker.MagicMock()

        # Begin operation
        pipeline.connect(callback=cb)
        assert cb.call_count == 0

        # Trigger op completion
        op = pipeline._pipeline.run_op.call_args[0][0]
        op.complete(error=None)

        assert cb.call_count == 1
        assert cb.call_args == mocker.call(error=None)

    @pytest.mark.it(
        "Calls the callback with the error upon unsuccessful completion of the ConnectOperation"
    )
    def test_op_fail(self, mocker, pipeline, arbitrary_exception):
        cb = mocker.MagicMock()

        pipeline.connect(callback=cb)
        op = pipeline._pipeline.run_op.call_args[0][0]

        op.complete(error=arbitrary_exception)
        assert cb.call_count == 1
        assert cb.call_args == mocker.call(error=arbitrary_exception)


@pytest.mark.describe("MQTTPipeline - .disconnect()")
class TestMQTTPipelineDisconnect(object):
    @pytest.mark.it("Runs a DisconnectOperation on the pipeline")
    def test_runs_op(self, pipeline, mocker):
        pipeline.disconnect(callback=mocker.MagicMock())
        assert pipeline._pipeline.run_op.call_count == 1
        assert isinstance(
            pipeline._pipeline.run_op.call_args[0][0], pipeline_ops_base.DisconnectOperation
        )

    @pytest.mark.it("Triggers the callback upon successful completion of the DisconnectOperation")
    def test_op_success_with_callback(self, mocker, pipeline):
        cb = mocker.MagicMock()

        # Begin operation
        pipeline.disconnect(callback=cb)
        assert cb.call_count == 0

        # Trigger op completion callback
        op = pipeline._pipeline.run_op.call_args[0][0]
        op.complete(error=None)

        assert cb.call_count == 1
        assert cb.call_args == mocker.call(error=None)

    @pytest.mark.it(
        "Calls the callback with the error upon unsuccessful completion of the DisconnectOperation"
    )
    def test_op_fail(self, mocker, pipeline, arbitrary_exception):
        cb = mocker.MagicMock()
        pipeline.disconnect(callback=cb)

        op = pipeline._pipeline.run_op.call_args[0][0]
        op.complete(error=arbitrary_exception)

        assert cb.call_count == 1
        assert cb.call_args == mocker.call(error=arbitrary_exception)


@pytest.mark.describe("MQTTPipeline - .register()")
class TestSendRegister(object):
    @pytest.mark.it("Runs a RegisterOperation on the pipeline")
    def test_runs_op(self, pipeline, mocker):
        cb = mocker.MagicMock()
        pipeline.register(callback=cb)
        assert pipeline._pipeline.run_op.call_count == 1
        op = pipeline._pipeline.run_op.call_args[0][0]
        assert isinstance(op, pipeline_ops_provisioning.RegisterOperation)
        assert op.registration_id == pipeline._pipeline.pipeline_configuration.registration_id

    @pytest.mark.it("passes the payload parameter as request_payload on the RegistrationRequest")
    def test_sets_request_payload(self, pipeline, mocker):
        cb = mocker.MagicMock()
        fake_request_payload = "fake_request_payload"
        pipeline.register(payload=fake_request_payload, callback=cb)
        op = pipeline._pipeline.run_op.call_args[0][0]
        assert op.request_payload is fake_request_payload

    @pytest.mark.it(
        "sets request_payload on the RegistrationRequest to None if no payload is provided"
    )
    def test_sets_empty_payload(self, pipeline, mocker):
        cb = mocker.MagicMock()
        pipeline.register(callback=cb)
        op = pipeline._pipeline.run_op.call_args[0][0]
        assert op.request_payload is None

    @pytest.mark.it(
        "Triggers the callback upon successful completion of the RegisterOperation, passing the registration result in the result parameter"
    )
    def test_op_success_with_callback(self, mocker, pipeline):
        cb = mocker.MagicMock()

        # Begin operation
        pipeline.register(callback=cb)
        assert cb.call_count == 0

        # Trigger op completion
        op = pipeline._pipeline.run_op.call_args[0][0]
        fake_registration_result = "fake_result"
        op.registration_result = fake_registration_result
        op.complete(error=None)

        assert cb.call_count == 1
        assert cb.call_args == mocker.call(result=fake_registration_result)

    @pytest.mark.it(
        "Calls the callback with the error upon unsuccessful completion of the RegisterOperation"
    )
    def test_op_fail(self, mocker, pipeline, arbitrary_exception):
        cb = mocker.MagicMock()

        pipeline.register(callback=cb)

        op = pipeline._pipeline.run_op.call_args[0][0]
        fake_registration_result = "fake_result"
        op.registration_result = fake_registration_result
        op.complete(error=arbitrary_exception)

        assert cb.call_count == 1
        assert cb.call_args == mocker.call(error=arbitrary_exception, result=None)


@pytest.mark.describe("MQTTPipeline - .enable_responses()")
class TestEnable(object):
    @pytest.mark.it("Marks the feature as enabled")
    def test_mark_feature_enabled(self, pipeline, mocker):
        assert not pipeline.responses_enabled[feature]
        pipeline.enable_responses(callback=mocker.MagicMock())
        assert pipeline.responses_enabled[feature]

    @pytest.mark.it(
        "Runs a EnableFeatureOperation on the pipeline, passing in the name of the feature"
    )
    def test_runs_op(self, pipeline, mocker):
        pipeline.enable_responses(callback=mocker.MagicMock())
        op = pipeline._pipeline.run_op.call_args[0][0]

        assert pipeline._pipeline.run_op.call_count == 1
        assert isinstance(op, pipeline_ops_base.EnableFeatureOperation)
        assert op.feature_name == dps_constants.REGISTER

    @pytest.mark.it(
        "Triggers the callback upon successful completion of the EnableFeatureOperation"
    )
    def test_op_success_with_callback(self, mocker, pipeline):
        cb = mocker.MagicMock()

        # Begin operation
        pipeline.enable_responses(callback=cb)
        assert cb.call_count == 0

        # Trigger op completion callback
        op = pipeline._pipeline.run_op.call_args[0][0]
        op.complete(error=None)

        assert cb.call_count == 1
        assert cb.call_args == mocker.call(error=None)

    @pytest.mark.it(
        "Calls the callback with the error upon unsuccessful completion of the EnableFeatureOperation"
    )
    def test_op_fail(self, mocker, pipeline, arbitrary_exception):
        cb = mocker.MagicMock()
        pipeline.enable_responses(callback=cb)

        op = pipeline._pipeline.run_op.call_args[0][0]
        op.complete(error=arbitrary_exception)

        assert cb.call_count == 1
        assert cb.call_args == mocker.call(error=arbitrary_exception)
