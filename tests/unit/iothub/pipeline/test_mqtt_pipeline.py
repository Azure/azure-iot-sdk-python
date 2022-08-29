# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
import logging
from azure.iot.device.common.pipeline import (
    pipeline_stages_base,
    pipeline_stages_mqtt,
    pipeline_ops_base,
    pipeline_exceptions,
    pipeline_nucleus,
)
from azure.iot.device.iothub.pipeline import (
    config,
    pipeline_stages_iothub,
    pipeline_stages_iothub_mqtt,
    pipeline_ops_iothub,
    pipeline_events_iothub,
)
from azure.iot.device.iothub.pipeline import MQTTPipeline
from .conftest import all_features

logging.basicConfig(level=logging.DEBUG)
pytestmark = pytest.mark.usefixtures("fake_pipeline_thread")


@pytest.fixture
def pipeline_configuration(mocker):
    # NOTE: Consider parametrizing this to serve as both a device and module configuration.
    # The reason this isn't currently done is that it's not strictly necessary, but it might be
    # more correct and complete to do so. Certainly this must be done if any device/module
    # specific logic is added to the code under test.
    mock_config = config.IoTHubPipelineConfig(
        device_id="my_device", hostname="my.host.name", sastoken=mocker.MagicMock()
    )
    mock_config.sastoken.ttl = 1232  # set for compat
    mock_config.sastoken.expiry_time = 1232131  # set for compat
    return mock_config


@pytest.fixture
def pipeline(mocker, pipeline_configuration):
    pipeline = MQTTPipeline(pipeline_configuration)
    mocker.patch.object(pipeline._pipeline, "run_op")
    return pipeline


@pytest.fixture
def twin_patch():
    return {"key": "value"}


# automatically mock the transport for all tests in this file.
@pytest.fixture(autouse=True)
def mock_transport(mocker):
    return mocker.patch(
        "azure.iot.device.common.pipeline.pipeline_stages_mqtt.MQTTTransport", autospec=True
    )


@pytest.mark.describe("MQTTPipeline - Instantiation")
class TestMQTTPipelineInstantiation(object):
    @pytest.mark.it("Begins tracking the enabled/disabled status of features")
    @pytest.mark.parametrize("feature", all_features)
    def test_features(self, pipeline_configuration, feature):
        pipeline = MQTTPipeline(pipeline_configuration)
        pipeline.feature_enabled[feature]
        # No assertion required - if this doesn't raise a KeyError, it is a success

    @pytest.mark.it("Marks all features as disabled")
    def test_features_disabled(self, pipeline_configuration):
        pipeline = MQTTPipeline(pipeline_configuration)
        for key in pipeline.feature_enabled:
            assert not pipeline.feature_enabled[key]

    @pytest.mark.it("Sets all handlers to an initial value of None")
    def test_handlers_set_to_none(self, pipeline_configuration):
        pipeline = MQTTPipeline(pipeline_configuration)
        assert pipeline.on_connected is None
        assert pipeline.on_disconnected is None
        assert pipeline.on_new_sastoken_required is None
        assert pipeline.on_background_exception is None
        assert pipeline.on_c2d_message_received is None
        assert pipeline.on_input_message_received is None
        assert pipeline.on_method_request_received is None
        assert pipeline.on_twin_patch_received is None

    @pytest.mark.it("Configures the pipeline to trigger handlers in response to external events")
    def test_handlers_configured(self, pipeline_configuration):
        pipeline = MQTTPipeline(pipeline_configuration)
        assert pipeline._pipeline.on_pipeline_event_handler is not None
        assert pipeline._pipeline.on_connected_handler is not None
        assert pipeline._pipeline.on_disconnected_handler is not None

    @pytest.mark.it("Configures the pipeline with a PipelineNucleus")
    def test_pipeline_nucleus(self, pipeline_configuration):
        pipeline = MQTTPipeline(pipeline_configuration)

        assert isinstance(pipeline._nucleus, pipeline_nucleus.PipelineNucleus)
        assert pipeline._nucleus.pipeline_configuration is pipeline_configuration

    @pytest.mark.it("Configures the pipeline with a series of PipelineStages")
    def test_pipeline_stages(self, pipeline_configuration):
        pipeline = MQTTPipeline(pipeline_configuration)
        curr_stage = pipeline._pipeline

        expected_stage_order = [
            pipeline_stages_base.PipelineRootStage,
            pipeline_stages_base.SasTokenStage,
            pipeline_stages_iothub.EnsureDesiredPropertiesStage,
            pipeline_stages_iothub.TwinRequestResponseStage,
            pipeline_stages_base.CoordinateRequestAndResponseStage,
            pipeline_stages_iothub_mqtt.IoTHubMQTTTranslationStage,
            pipeline_stages_base.AutoConnectStage,
            pipeline_stages_base.ConnectionStateStage,
            pipeline_stages_base.RetryStage,
            pipeline_stages_base.OpTimeoutStage,
            pipeline_stages_mqtt.MQTTTransportStage,
        ]

        # Assert that all PipelineStages are there, and they are in the right order
        for i in range(len(expected_stage_order)):
            expected_stage = expected_stage_order[i]
            assert isinstance(curr_stage, expected_stage)
            assert curr_stage.nucleus is pipeline._nucleus
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
        "Sets a flag to indicate the pipeline is 'running' upon successful completion of the InitializePipelineOperation"
    )
    def test_running(self, mocker, pipeline_configuration):
        # Because this is an init test, there isn't really a way to check that it only occurs after
        # the op. The reason is because this is the object's init, the object doesn't actually
        # exist until the entire method has completed, so there's no reference you can check prior
        # to method completion.
        pipeline = MQTTPipeline(pipeline_configuration)
        assert pipeline._running

    @pytest.mark.it(
        "Raises exceptions that occurred in execution upon unsuccessful completion of the InitializePipelineOperation"
    )
    def test_init_pipeline_fail(self, mocker, arbitrary_exception, pipeline_configuration):
        old_run_op = pipeline_stages_base.PipelineRootStage._run_op

        def fail_initialize(self, op):
            if isinstance(op, pipeline_ops_base.InitializePipelineOperation):
                op.complete(error=arbitrary_exception)
            else:
                old_run_op(self, op)

        mocker.patch.object(
            pipeline_stages_base.PipelineRootStage,
            "_run_op",
            side_effect=fail_initialize,
            autospec=True,
        )

        with pytest.raises(arbitrary_exception.__class__) as e_info:
            MQTTPipeline(pipeline_configuration)
        assert e_info.value is arbitrary_exception


@pytest.mark.describe("MQTTPipeline - .shutdown()")
class TestMQTTPipelineShutdown(object):
    @pytest.mark.it(
        "Raises a PipelineNotRunning exception if the pipeline is not running (i.e. already shut down)"
    )
    def test_not_running(self, mocker, pipeline):
        pipeline._running = False

        with pytest.raises(pipeline_exceptions.PipelineNotRunning):
            pipeline.shutdown(callback=mocker.MagicMock())

    @pytest.mark.it("Runs a ShutdownPipelineOperation on the pipeline")
    def test_runs_op(self, pipeline, mocker):
        cb = mocker.MagicMock()
        pipeline.shutdown(callback=cb)
        assert pipeline._pipeline.run_op.call_count == 1
        assert isinstance(
            pipeline._pipeline.run_op.call_args[0][0], pipeline_ops_base.ShutdownPipelineOperation
        )

    @pytest.mark.it(
        "Triggers the callback upon successful completion of the ShutdownPipelineOperation"
    )
    def test_op_success_with_callback(self, mocker, pipeline):
        cb = mocker.MagicMock()

        # Begin operation
        pipeline.shutdown(callback=cb)
        assert cb.call_count == 0

        # Trigger op completion
        op = pipeline._pipeline.run_op.call_args[0][0]
        op.complete(error=None)

        assert cb.call_count == 1
        assert cb.call_args == mocker.call(error=None)

    @pytest.mark.it(
        "Calls the callback with the error upon unsuccessful completion of the ShutdownPipelineOperation"
    )
    def test_op_fail(self, mocker, pipeline, arbitrary_exception):
        cb = mocker.MagicMock()

        pipeline.shutdown(callback=cb)
        op = pipeline._pipeline.run_op.call_args[0][0]

        op.complete(error=arbitrary_exception)
        assert cb.call_count == 1
        assert cb.call_args == mocker.call(error=arbitrary_exception)

    @pytest.mark.it(
        "Sets a flag to indicate the pipeline is no longer running only upon successful completion of the ShutdownPipelineOperation"
    )
    def test_set_not_running(self, mocker, pipeline, arbitrary_exception):
        # Pipeline is running
        assert pipeline._running

        # Begin operation (we will fail this one)
        cb = mocker.MagicMock()
        pipeline.shutdown(callback=cb)
        assert cb.call_count == 0

        # Pipeline is still running
        assert pipeline._running

        # Trigger op completion (failure)
        op = pipeline._pipeline.run_op.call_args[0][0]
        op.complete(error=arbitrary_exception)

        # Pipeline is still running
        assert pipeline._running

        # Try operation again (we will make this one succeed)
        cb.reset_mock()
        pipeline.shutdown(callback=cb)
        assert cb.call_count == 0

        # Trigger op completion (successful)
        op = pipeline._pipeline.run_op.call_args[0][0]
        op.complete(error=None)

        # Pipeline is no longer running
        assert not pipeline._running


@pytest.mark.describe("MQTTPipeline - .connect()")
class TestMQTTPipelineConnect(object):
    @pytest.mark.it(
        "Raises a PipelineNotRunning exception if the pipeline is not running (i.e. already shut down)"
    )
    def test_not_running(self, mocker, pipeline):
        pipeline._running = False

        with pytest.raises(pipeline_exceptions.PipelineNotRunning):
            pipeline.connect(callback=mocker.MagicMock())

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
    @pytest.mark.it(
        "Raises a PipelineNotRunning exception if the pipeline is not running (i.e. already shut down)"
    )
    def test_not_running(self, mocker, pipeline):
        pipeline._running = False

        with pytest.raises(pipeline_exceptions.PipelineNotRunning):
            pipeline.disconnect(callback=mocker.MagicMock())

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


@pytest.mark.describe("MQTTPipeline - .reauthorize_connection()")
class TestMQTTPipelineReauthorizeConnection(object):
    @pytest.mark.it(
        "Raises a PipelineNotRunning exception if the pipeline is not running (i.e. already shut down)"
    )
    def test_not_running(self, mocker, pipeline):
        pipeline._running = False

        with pytest.raises(pipeline_exceptions.PipelineNotRunning):
            pipeline.reauthorize_connection(callback=mocker.MagicMock())

    @pytest.mark.it("Runs a ReauthorizeConnectionOperation on the pipeline")
    def test_runs_op(self, pipeline, mocker):
        pipeline.reauthorize_connection(callback=mocker.MagicMock())
        assert pipeline._pipeline.run_op.call_count == 1
        assert isinstance(
            pipeline._pipeline.run_op.call_args[0][0],
            pipeline_ops_base.ReauthorizeConnectionOperation,
        )

    @pytest.mark.it(
        "Triggers the callback upon successful completion of the ReauthorizeConnectionOperation"
    )
    def test_op_success_with_callback(self, mocker, pipeline):
        cb = mocker.MagicMock()

        # Begin operation
        pipeline.reauthorize_connection(callback=cb)
        assert cb.call_count == 0

        # Trigger oop completion callback
        op = pipeline._pipeline.run_op.call_args[0][0]
        op.complete(error=None)

        assert cb.call_count == 1
        assert cb.call_args == mocker.call(error=None)

    @pytest.mark.it(
        "Calls the callback with the error upon unsuccessful completion of the ReauthorizeConnectionOperation"
    )
    def test_op_fail(self, mocker, pipeline, arbitrary_exception):
        cb = mocker.MagicMock()
        pipeline.reauthorize_connection(callback=cb)

        op = pipeline._pipeline.run_op.call_args[0][0]
        op.complete(error=arbitrary_exception)

        assert cb.call_count == 1
        assert cb.call_args == mocker.call(error=arbitrary_exception)


@pytest.mark.describe("MQTTPipeline - .send_message()")
class TestMQTTPipelineSendD2CMessage(object):
    @pytest.mark.it(
        "Raises a PipelineNotRunning exception if the pipeline is not running (i.e. already shut down)"
    )
    def test_not_running(self, mocker, message, pipeline):
        pipeline._running = False

        with pytest.raises(pipeline_exceptions.PipelineNotRunning):
            pipeline.send_message(message, callback=mocker.MagicMock())

    @pytest.mark.it("Runs a SendD2CMessageOperation with the provided message on the pipeline")
    def test_runs_op(self, pipeline, message, mocker):
        pipeline.send_message(message, callback=mocker.MagicMock())
        op = pipeline._pipeline.run_op.call_args[0][0]

        assert pipeline._pipeline.run_op.call_count == 1
        assert isinstance(op, pipeline_ops_iothub.SendD2CMessageOperation)
        assert op.message == message

    @pytest.mark.it(
        "Triggers the callback upon successful completion of the SendD2CMessageOperation"
    )
    def test_op_success_with_callback(self, mocker, pipeline, message):
        cb = mocker.MagicMock()

        # Begin operation
        pipeline.send_message(message, callback=cb)
        assert cb.call_count == 0

        # Trigger op completion callback
        op = pipeline._pipeline.run_op.call_args[0][0]
        op.complete(error=None)

        assert cb.call_count == 1
        assert cb.call_args == mocker.call(error=None)

    @pytest.mark.it(
        "Calls the callback with the error upon unsuccessful completion of the SendD2CMessageOperation"
    )
    def test_op_fail(self, mocker, pipeline, message, arbitrary_exception):
        cb = mocker.MagicMock()
        pipeline.send_message(message, callback=cb)

        op = pipeline._pipeline.run_op.call_args[0][0]
        op.complete(error=arbitrary_exception)

        assert cb.call_count == 1
        assert cb.call_args == mocker.call(error=arbitrary_exception)


@pytest.mark.describe("MQTTPipeline - .send_output_message()")
class TestMQTTPipelineSendOutputMessage(object):
    @pytest.mark.it(
        "Raises a PipelineNotRunning exception if the pipeline is not running (i.e. already shut down)"
    )
    def test_not_running(self, mocker, message, pipeline):
        pipeline._running = False

        with pytest.raises(pipeline_exceptions.PipelineNotRunning):
            pipeline.send_output_message(message, callback=mocker.MagicMock())

    @pytest.fixture
    def message(self, message):
        """Modify message fixture to have an output"""
        message.output_name = "some output"
        return message

    @pytest.mark.it("Runs a SendOutputMessageOperation with the provided Message on the pipeline")
    def test_runs_op(self, pipeline, message, mocker):
        pipeline.send_output_message(message, callback=mocker.MagicMock())
        op = pipeline._pipeline.run_op.call_args[0][0]

        assert pipeline._pipeline.run_op.call_count == 1
        assert isinstance(op, pipeline_ops_iothub.SendOutputMessageOperation)
        assert op.message == message

    @pytest.mark.it(
        "Triggers the callback upon successful completion of the SendOutputMessageOperation"
    )
    def test_op_success_with_callback(self, mocker, pipeline, message):
        cb = mocker.MagicMock()

        # Begin operation
        pipeline.send_output_message(message, callback=cb)
        assert cb.call_count == 0

        # Trigger op completion callback
        op = pipeline._pipeline.run_op.call_args[0][0]
        op.complete(error=None)

        assert cb.call_count == 1
        assert cb.call_args == mocker.call(error=None)

    @pytest.mark.it(
        "Calls the callback with the error upon unsuccessful completion of the SendOutputMessageOperation"
    )
    def test_op_fail(self, mocker, pipeline, message, arbitrary_exception):
        cb = mocker.MagicMock()
        pipeline.send_output_message(message, callback=cb)

        op = pipeline._pipeline.run_op.call_args[0][0]
        op.complete(error=arbitrary_exception)

        assert cb.call_count == 1
        assert cb.call_args == mocker.call(error=arbitrary_exception)


@pytest.mark.describe("MQTTPipeline - .send_method_response()")
class TestMQTTPipelineSendMethodResponse(object):
    @pytest.mark.it(
        "Raises a PipelineNotRunning exception if the pipeline is not running (i.e. already shut down)"
    )
    def test_not_running(self, mocker, method_response, pipeline):
        pipeline._running = False

        with pytest.raises(pipeline_exceptions.PipelineNotRunning):
            pipeline.send_method_response(method_response, callback=mocker.MagicMock())

    @pytest.mark.it(
        "Runs a SendMethodResponseOperation with the provided MethodResponse on the pipeline"
    )
    def test_runs_op(self, pipeline, method_response, mocker):
        pipeline.send_method_response(method_response, callback=mocker.MagicMock())
        op = pipeline._pipeline.run_op.call_args[0][0]

        assert pipeline._pipeline.run_op.call_count == 1
        assert isinstance(op, pipeline_ops_iothub.SendMethodResponseOperation)
        assert op.method_response == method_response

    @pytest.mark.it(
        "Triggers the callback upon successful completion of the SendMethodResponseOperation"
    )
    def test_op_success_with_callback(self, mocker, pipeline, method_response):
        cb = mocker.MagicMock()

        # Begin operation
        pipeline.send_method_response(method_response, callback=cb)
        assert cb.call_count == 0

        # Trigger op completion callback
        op = pipeline._pipeline.run_op.call_args[0][0]
        op.complete(error=None)

        assert cb.call_count == 1
        assert cb.call_args == mocker.call(error=None)

    @pytest.mark.it(
        "Calls the callback with the error upon unsuccessful completion of the SendMethodResponseOperation"
    )
    def test_op_fail(self, mocker, pipeline, method_response, arbitrary_exception):
        cb = mocker.MagicMock()
        pipeline.send_method_response(method_response, callback=cb)

        op = pipeline._pipeline.run_op.call_args[0][0]
        op.complete(error=arbitrary_exception)

        assert cb.call_count == 1
        assert cb.call_args == mocker.call(error=arbitrary_exception)


@pytest.mark.describe("MQTTPipeline - .get_twin()")
class TestMQTTPipelineGetTwin(object):
    @pytest.mark.it(
        "Raises a PipelineNotRunning exception if the pipeline is not running (i.e. already shut down)"
    )
    def test_not_running(self, mocker, pipeline):
        pipeline._running = False

        with pytest.raises(pipeline_exceptions.PipelineNotRunning):
            pipeline.get_twin(callback=mocker.MagicMock())

    @pytest.mark.it("Runs a GetTwinOperation on the pipeline")
    def test_runs_op(self, mocker, pipeline):
        cb = mocker.MagicMock()
        pipeline.get_twin(callback=cb)
        assert pipeline._pipeline.run_op.call_count == 1
        assert isinstance(
            pipeline._pipeline.run_op.call_args[0][0], pipeline_ops_iothub.GetTwinOperation
        )

    @pytest.mark.it(
        "Triggers the provided callback upon successful completion of the GetTwinOperation"
    )
    def test_op_success_with_callback(self, mocker, pipeline):
        cb = mocker.MagicMock()

        # Begin operation
        pipeline.get_twin(callback=cb)
        assert cb.call_count == 0

        # Trigger op completion callback
        op = pipeline._pipeline.run_op.call_args[0][0]
        op.complete(error=None)

        assert cb.call_count == 1
        assert cb.call_args == mocker.call(twin=None)

    @pytest.mark.it(
        "Calls the callback with the error upon unsuccessful completion of the GetTwinOperation"
    )
    def test_op_fail(self, mocker, pipeline, arbitrary_exception):
        cb = mocker.MagicMock()
        pipeline.get_twin(callback=cb)

        op = pipeline._pipeline.run_op.call_args[0][0]
        op.complete(error=arbitrary_exception)

        assert cb.call_count == 1
        assert cb.call_args == mocker.call(twin=None, error=arbitrary_exception)


@pytest.mark.describe("MQTTPipeline - .patch_twin_reported_properties()")
class TestMQTTPipelinePatchTwinReportedProperties(object):
    @pytest.mark.it(
        "Raises a PipelineNotRunning exception if the pipeline is not running (i.e. already shut down)"
    )
    def test_not_running(self, mocker, twin_patch, pipeline):
        pipeline._running = False

        with pytest.raises(pipeline_exceptions.PipelineNotRunning):
            pipeline.patch_twin_reported_properties(twin_patch, callback=mocker.MagicMock())

    @pytest.mark.it(
        "Runs a PatchTwinReportedPropertiesOperation with the provided twin patch on the pipeline"
    )
    def test_runs_op(self, pipeline, twin_patch, mocker):
        pipeline.patch_twin_reported_properties(twin_patch, callback=mocker.MagicMock())
        op = pipeline._pipeline.run_op.call_args[0][0]

        assert pipeline._pipeline.run_op.call_count == 1
        assert isinstance(op, pipeline_ops_iothub.PatchTwinReportedPropertiesOperation)
        assert op.patch == twin_patch

    @pytest.mark.it(
        "Triggers the callback upon successful completion of the PatchTwinReportedPropertiesOperation"
    )
    def test_op_success_with_callback(self, mocker, pipeline, twin_patch):
        cb = mocker.MagicMock()

        # Begin operation
        pipeline.patch_twin_reported_properties(twin_patch, callback=cb)
        assert cb.call_count == 0

        # Trigger op completion callback
        op = pipeline._pipeline.run_op.call_args[0][0]
        op.complete(error=None)

        assert cb.call_count == 1
        assert cb.call_args == mocker.call(error=None)

    @pytest.mark.it(
        "Calls the callback with the error upon unsuccessful completion of the PatchTwinReportedPropertiesOperation"
    )
    def test_op_fail(self, mocker, pipeline, twin_patch, arbitrary_exception):
        cb = mocker.MagicMock()
        pipeline.patch_twin_reported_properties(twin_patch, callback=cb)

        op = pipeline._pipeline.run_op.call_args[0][0]
        op.complete(error=arbitrary_exception)

        assert cb.call_count == 1
        assert cb.call_args == mocker.call(error=arbitrary_exception)


@pytest.mark.describe("MQTTPipeline - .enable_feature()")
class TestMQTTPipelineEnableFeature(object):
    @pytest.mark.it(
        "Raises a PipelineNotRunning exception if the pipeline is not running (i.e. already shut down)"
    )
    @pytest.mark.parametrize("feature", all_features)
    def test_not_running(self, mocker, feature, pipeline):
        pipeline._running = False

        with pytest.raises(pipeline_exceptions.PipelineNotRunning):
            pipeline.enable_feature(feature, callback=mocker.MagicMock())

    @pytest.mark.it("Raises ValueError if the feature_name is invalid")
    def test_invalid_feature_name(self, pipeline, mocker):
        bad_feature = "not-a-feature-name"
        assert bad_feature not in pipeline.feature_enabled
        with pytest.raises(ValueError):
            pipeline.enable_feature(bad_feature, callback=mocker.MagicMock())
        assert bad_feature not in pipeline.feature_enabled

    # TODO: what about features that are already disabled?

    @pytest.mark.it("Runs a EnableFeatureOperation with the provided feature_name on the pipeline")
    @pytest.mark.parametrize("feature", all_features)
    def test_runs_op(self, pipeline, feature, mocker):
        pipeline.enable_feature(feature, callback=mocker.MagicMock())
        op = pipeline._pipeline.run_op.call_args[0][0]

        assert pipeline._pipeline.run_op.call_count == 1
        assert isinstance(op, pipeline_ops_base.EnableFeatureOperation)
        assert op.feature_name == feature

    @pytest.mark.it("Does not mark the feature as enabled before the callback is complete")
    @pytest.mark.parametrize("feature", all_features)
    def test_mark_feature_not_enabled(self, pipeline, feature, mocker):
        assert not pipeline.feature_enabled[feature]
        callback = mocker.MagicMock()
        pipeline.enable_feature(feature, callback=callback)

        assert callback.call_count == 0
        assert not pipeline.feature_enabled[feature]

    @pytest.mark.it("Does not mark the feature as enabled if the EnableFeatureOperation fails")
    @pytest.mark.parametrize("feature", all_features)
    def test_mark_feature_not_enabled_on_failure(
        self, pipeline, feature, mocker, arbitrary_exception
    ):
        assert not pipeline.feature_enabled[feature]
        callback = mocker.MagicMock()
        pipeline.enable_feature(feature, callback=callback)

        op = pipeline._pipeline.run_op.call_args[0][0]
        assert isinstance(op, pipeline_ops_base.EnableFeatureOperation)
        op.complete(arbitrary_exception)

        assert callback.call_count == 1
        assert not pipeline.feature_enabled[feature]

    @pytest.mark.it("Marks the feature as enabled if the EnableFeatureOperation succeeds")
    @pytest.mark.parametrize("feature", all_features)
    def test_mark_feature_enabled_on_success(self, pipeline, feature, mocker):
        assert not pipeline.feature_enabled[feature]
        callback = mocker.MagicMock()
        pipeline.enable_feature(feature, callback=callback)

        op = pipeline._pipeline.run_op.call_args[0][0]
        assert isinstance(op, pipeline_ops_base.EnableFeatureOperation)
        op.complete()

        assert callback.call_count == 1
        assert pipeline.feature_enabled[feature]

    @pytest.mark.it(
        "Triggers the callback upon successful completion of the EnableFeatureOperation"
    )
    @pytest.mark.parametrize("feature", all_features)
    def test_op_success_with_callback(self, mocker, pipeline, feature):
        cb = mocker.MagicMock()

        # Begin operation
        pipeline.enable_feature(feature, callback=cb)
        assert cb.call_count == 0

        # Trigger op completion callback
        op = pipeline._pipeline.run_op.call_args[0][0]
        op.complete(error=None)

        assert cb.call_count == 1
        assert cb.call_args == mocker.call(error=None)

    @pytest.mark.it(
        "Calls the callback with the error upon unsuccessful completion of the EnableFeatureOperation"
    )
    @pytest.mark.parametrize("feature", all_features)
    def test_op_fail(self, mocker, pipeline, feature, arbitrary_exception):
        cb = mocker.MagicMock()
        pipeline.enable_feature(feature, callback=cb)

        op = pipeline._pipeline.run_op.call_args[0][0]
        op.complete(error=arbitrary_exception)

        assert cb.call_count == 1
        assert cb.call_args == mocker.call(error=arbitrary_exception)


@pytest.mark.describe("MQTTPipeline - .disable_feature()")
class TestMQTTPipelineDisableFeature(object):
    @pytest.mark.it(
        "Raises a PipelineNotRunning exception if the pipeline is not running (i.e. already shut down)"
    )
    @pytest.mark.parametrize("feature", all_features)
    def test_not_running(self, mocker, feature, pipeline):
        pipeline._running = False

        with pytest.raises(pipeline_exceptions.PipelineNotRunning):
            pipeline.disable_feature(feature, callback=mocker.MagicMock())

    @pytest.mark.it("Raises ValueError if the feature_name is invalid")
    def test_invalid_feature_name(self, pipeline, mocker):
        bad_feature = "not-a-feature-name"
        assert bad_feature not in pipeline.feature_enabled
        with pytest.raises(ValueError):
            pipeline.disable_feature(bad_feature, callback=mocker.MagicMock())
        assert bad_feature not in pipeline.feature_enabled

    # TODO: what about features that are already disabled?

    @pytest.mark.it("Runs a DisableFeatureOperation with the provided feature_name on the pipeline")
    @pytest.mark.parametrize("feature", all_features)
    def test_runs_op(self, pipeline, feature, mocker):
        pipeline.disable_feature(feature, callback=mocker.MagicMock())
        op = pipeline._pipeline.run_op.call_args[0][0]

        assert pipeline._pipeline.run_op.call_count == 1
        assert isinstance(op, pipeline_ops_base.DisableFeatureOperation)
        assert op.feature_name == feature

    @pytest.mark.it("Does not mark the feature as disabled before the callback is complete")
    @pytest.mark.parametrize("feature", all_features)
    def test_mark_feature_not_enabled(self, pipeline, feature, mocker):
        # feature is already enabled
        pipeline.feature_enabled[feature] = True
        assert pipeline.feature_enabled[feature]

        # start call to disable feature
        callback = mocker.MagicMock()
        pipeline.disable_feature(feature, callback=callback)

        # feature is still enabled (because callback has not been completed yet)
        assert callback.call_count == 0
        assert pipeline.feature_enabled[feature]

    @pytest.mark.it("Marks the feature as disabled if the DisableFeatureOperation succeeds")
    @pytest.mark.parametrize("feature", all_features)
    def test_mark_feature_enabled_on_success(self, pipeline, feature, mocker):
        # feature is already enabled
        pipeline.feature_enabled[feature] = True
        assert pipeline.feature_enabled[feature]

        # try to disable the feature (and succeed)
        callback = mocker.MagicMock()
        pipeline.disable_feature(feature, callback=callback)
        op = pipeline._pipeline.run_op.call_args[0][0]
        assert isinstance(op, pipeline_ops_base.DisableFeatureOperation)
        op.complete()

        assert callback.call_count == 1
        assert not pipeline.feature_enabled[feature]

    @pytest.mark.it("Marks the feature as disabled even if the DisableFeatureOperation fails")
    @pytest.mark.parametrize("feature", all_features)
    def test_mark_feature_not_enabled_on_failure(
        self, pipeline, feature, mocker, arbitrary_exception
    ):
        # feature is already enabled
        pipeline.feature_enabled[feature] = True
        assert pipeline.feature_enabled[feature]

        # tyr to disable the feature (but fail)
        callback = mocker.MagicMock()
        pipeline.disable_feature(feature, callback=callback)
        op = pipeline._pipeline.run_op.call_args[0][0]
        assert isinstance(op, pipeline_ops_base.DisableFeatureOperation)
        op.complete(arbitrary_exception)

        # Feature was STILL disabled
        assert callback.call_count == 1
        assert not pipeline.feature_enabled[feature]

    @pytest.mark.it(
        "Triggers the callback upon successful completion of the DisableFeatureOperation"
    )
    @pytest.mark.parametrize("feature", all_features)
    def test_op_success_with_callback(self, mocker, pipeline, feature):
        cb = mocker.MagicMock()

        # Begin operation
        pipeline.disable_feature(feature, callback=cb)
        assert cb.call_count == 0

        # Trigger op completion callback
        op = pipeline._pipeline.run_op.call_args[0][0]
        op.complete(error=None)

        assert cb.call_count == 1
        assert cb.call_args == mocker.call(error=None)

    @pytest.mark.it(
        "Calls the callback with the error upon unsuccessful completion of the DisableFeatureOperation"
    )
    @pytest.mark.parametrize("feature", all_features)
    def _est_op_fail(self, mocker, pipeline, feature, arbitrary_exception):
        cb = mocker.MagicMock()
        pipeline.disable_feature(feature, callback=cb)

        op = pipeline._pipeline.run_op.call_args[0][0]
        op.complete(error=arbitrary_exception)

        assert cb.call_count == 1
        assert cb.call_args == mocker.call(error=arbitrary_exception)


@pytest.mark.describe("MQTTPipeline - OCCURRENCE: Connected")
class TestMQTTPipelineOCCURRENCEConnect(object):
    @pytest.mark.it("Triggers the 'on_connected' handler")
    def test_with_handler(self, mocker, pipeline):
        # Set the handler
        mock_handler = mocker.MagicMock()
        pipeline.on_connected = mock_handler
        assert mock_handler.call_count == 0

        # Trigger the connect
        pipeline._pipeline.on_connected_handler()

        assert mock_handler.call_count == 1
        assert mock_handler.call_args == mocker.call()

    @pytest.mark.it("Does nothing if the 'on_connected' handler is not set")
    def test_without_handler(self, pipeline):
        pipeline._pipeline.on_connected_handler()

        # No assertions required - not throwing an exception means the test passed


@pytest.mark.describe("MQTTPipeline - OCCURRENCE: Disconnected")
class TestMQTTPipelineOCCURRENCEDisconnect(object):
    @pytest.mark.it("Triggers the 'on_disconnected' handler")
    def test_with_handler(self, mocker, pipeline):
        # Set the handler
        mock_handler = mocker.MagicMock()
        pipeline.on_disconnected = mock_handler
        assert mock_handler.call_count == 0

        # Trigger the disconnect
        pipeline._pipeline.on_disconnected_handler()

        assert mock_handler.call_count == 1
        assert mock_handler.call_args == mocker.call()

    @pytest.mark.it("Does nothing if the 'on_disconnected' handler is not set")
    def test_without_handler(self, pipeline):
        pipeline._pipeline.on_disconnected_handler()

        # No assertions required - not throwing an exception means the test passed


@pytest.mark.describe("MQTTPipeline - OCCURRENCE: New Sastoken Required")
class TestMQTTPipelineOCCURRENCENewSastokenRequired(object):
    @pytest.mark.it("Triggers the 'on_new_sastoken_required' handler")
    def test_with_handler(self, mocker, pipeline):
        # Set the handler
        mock_handler = mocker.MagicMock()
        pipeline.on_new_sastoken_required = mock_handler
        assert mock_handler.call_count == 0

        # Trigger the event
        pipeline._pipeline.on_new_sastoken_required_handler()

        assert mock_handler.call_count == 1
        assert mock_handler.call_args == mocker.call()

    @pytest.mark.it("Does nothing if the 'on_new_sastoken_required' handler is not set")
    def test_without_handler(self, pipeline):
        pipeline._pipeline.on_new_sastoken_required_handler()

        # No assertions required - not throwing an exception means the test passed


@pytest.mark.describe("MQTTPipeline - OCCURRENCE: Background Exception")
class TestMQTTPipelineOCCURRENCEBackgroundException(object):
    @pytest.mark.it("Triggers the 'on_background_exception' handler")
    def test_with_handler(self, mocker, pipeline, arbitrary_exception):
        # Set the handler
        mock_handler = mocker.MagicMock()
        pipeline.on_background_exception = mock_handler
        assert mock_handler.call_count == 0

        # Trigger the background exception
        pipeline._pipeline.on_background_exception_handler(arbitrary_exception)

        assert mock_handler.call_count == 1
        assert mock_handler.call_args == mocker.call(arbitrary_exception)

    @pytest.mark.it("Does nothing if the 'on_background_exception' handler is not set")
    def test_without_handler(self, pipeline, arbitrary_exception):
        pipeline._pipeline.on_background_exception_handler(arbitrary_exception)

        # No assertions required - not throwing an exception means the test passed


@pytest.mark.describe("MQTTPipeline - OCCURRENCE: C2D Message Received")
class TestMQTTPipelineOCCURRENCEReceiveC2DMessage(object):
    @pytest.mark.it(
        "Triggers the 'on_c2d_message_received' handler, passing the received message as an argument"
    )
    def test_with_handler(self, mocker, pipeline, message):
        # Set the handler
        mock_handler = mocker.MagicMock()
        pipeline.on_c2d_message_received = mock_handler
        assert mock_handler.call_count == 0

        # Create the event
        c2d_event = pipeline_events_iothub.C2DMessageEvent(message)

        # Trigger the event
        pipeline._pipeline.on_pipeline_event_handler(c2d_event)

        assert mock_handler.call_count == 1
        assert mock_handler.call_args == mocker.call(message)

    @pytest.mark.it("Drops the message if the 'on_c2d_message_received' handler is not set")
    def test_no_handler(self, pipeline, message):
        c2d_event = pipeline_events_iothub.C2DMessageEvent(message)
        pipeline._pipeline.on_pipeline_event_handler(c2d_event)

        # No assertions required - not throwing an exception means the test passed


@pytest.mark.describe("MQTTPipeline - OCCURRENCE: Input Message Received")
class TestMQTTPipelineOCCURRENCEReceiveInputMessage(object):
    @pytest.mark.it(
        "Triggers the 'on_input_message_received' handler, passing the received message as an argument"
    )
    def test_with_handler(self, mocker, pipeline, message):
        # Set the handler
        mock_handler = mocker.MagicMock()
        pipeline.on_input_message_received = mock_handler
        assert mock_handler.call_count == 0

        # Create the event
        input_name = "some_input"
        message.input_name = input_name
        input_message_event = pipeline_events_iothub.InputMessageEvent(message)

        # Trigger the event
        pipeline._pipeline.on_pipeline_event_handler(input_message_event)

        assert mock_handler.call_count == 1
        assert mock_handler.call_args == mocker.call(message)

    @pytest.mark.it("Drops the message if the 'on_input_message_received' handler is not set")
    def test_no_handler(self, pipeline, message):
        input_name = "some_input"
        message.input_name = input_name
        input_message_event = pipeline_events_iothub.InputMessageEvent(message)
        pipeline._pipeline.on_pipeline_event_handler(input_message_event)

        # No assertions required - not throwing an exception means the test passed


@pytest.mark.describe("MQTTPipeline - OCCURRENCE: Method Request Received")
class TestMQTTPipelineOCCURRENCEReceiveMethodRequest(object):
    @pytest.mark.it(
        "Triggers the 'on_method_request_received' handler, passing the received method request as an argument"
    )
    def test_with_handler(self, mocker, pipeline, method_request):
        # Set the handler
        mock_handler = mocker.MagicMock()
        pipeline.on_method_request_received = mock_handler
        assert mock_handler.call_count == 0

        # Create the event
        method_request_event = pipeline_events_iothub.MethodRequestEvent(method_request)

        # Trigger the event
        pipeline._pipeline.on_pipeline_event_handler(method_request_event)

        assert mock_handler.call_count == 1
        assert mock_handler.call_args == mocker.call(method_request)

    @pytest.mark.it(
        "Drops the method request if the 'on_method_request_received' handler is not set"
    )
    def test_no_handler(self, pipeline, method_request):
        method_request_event = pipeline_events_iothub.MethodRequestEvent(method_request)
        pipeline._pipeline.on_pipeline_event_handler(method_request_event)

        # No assertions required - not throwing an exception means the test passed


@pytest.mark.describe("MQTTPipeline - OCCURRENCE: Twin Desired Properties Patch Received")
class TestMQTTPipelineOCCURRENCEReceiveDesiredPropertiesPatch(object):
    @pytest.mark.it(
        "Triggers the 'on_twin_patch_received' handler, passing the received twin patch as an argument"
    )
    def test_with_handler(self, mocker, pipeline, twin_patch):
        # Set the handler
        mock_handler = mocker.MagicMock()
        pipeline.on_twin_patch_received = mock_handler
        assert mock_handler.call_count == 0

        # Create the event
        twin_patch_event = pipeline_events_iothub.TwinDesiredPropertiesPatchEvent(twin_patch)

        # Trigger the event
        pipeline._pipeline.on_pipeline_event_handler(twin_patch_event)

        assert mock_handler.call_count == 1
        assert mock_handler.call_args == mocker.call(twin_patch)

    @pytest.mark.it("Drops the twin patch if the 'on_twin_patch_received' handler is not set")
    def test_no_handler(self, pipeline, twin_patch):
        twin_patch_event = pipeline_events_iothub.TwinDesiredPropertiesPatchEvent(twin_patch)
        pipeline._pipeline.on_pipeline_event_handler(twin_patch_event)

        # No assertions required - not throwing an exception means the test passed


@pytest.mark.describe("MQTTPipeline - PROPERTY .pipeline_configuration")
class TestMQTTPipelinePROPERTYPipelineConfiguration(object):
    @pytest.mark.it("Value of the object cannot be changed")
    def test_read_only(self, pipeline):
        with pytest.raises(AttributeError):
            pipeline.pipeline_configuration = 12

    @pytest.mark.it("Values ON the object CAN be changed")
    def test_update_values_on_read_only_object(self, pipeline):
        assert pipeline.pipeline_configuration.sastoken is not None
        pipeline.pipeline_configuration.sastoken = None
        assert pipeline.pipeline_configuration.sastoken is None

    @pytest.mark.it("Reflects the value of the PipelineNucleus attribute of the same name")
    def test_reflects_pipeline_attribute(self, pipeline):
        assert pipeline.pipeline_configuration is pipeline._nucleus.pipeline_configuration


@pytest.mark.describe("MQTTPipeline - PROPERTY .connected")
class TestMQTTPipelinePROPERTYConnected(object):
    @pytest.mark.it("Cannot be changed")
    def test_read_only(self, pipeline):
        with pytest.raises(AttributeError):
            pipeline.connected = not pipeline.connected

    @pytest.mark.it("Reflects the value of the PipelineNucleus attribute of the same name")
    def test_reflects_pipeline_attribute(self, pipeline, pipeline_connected_mock):
        # Need to set indirectly via mock due to nucleus attribute being read-only
        type(pipeline._nucleus).connected = pipeline_connected_mock
        pipeline_connected_mock.return_value = True
        assert pipeline._nucleus.connected
        assert pipeline.connected
        # Again, must be set indirectly
        pipeline_connected_mock.return_value = False
        assert not pipeline._nucleus.connected
        assert not pipeline.connected
