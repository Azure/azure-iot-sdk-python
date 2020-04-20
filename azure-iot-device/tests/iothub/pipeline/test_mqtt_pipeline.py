# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
import logging
import six.moves.urllib as urllib
from azure.iot.device.common import handle_exceptions
from azure.iot.device.common.pipeline import (
    pipeline_stages_base,
    pipeline_stages_mqtt,
    pipeline_ops_base,
)
from azure.iot.device.iothub.pipeline import (
    pipeline_stages_iothub,
    pipeline_stages_iothub_mqtt,
    pipeline_ops_iothub,
    pipeline_events_iothub,
)
from azure.iot.device.iothub import Message
from azure.iot.device.iothub.pipeline import MQTTPipeline, constant
from azure.iot.device.iothub.auth import (
    SymmetricKeyAuthenticationProvider,
    X509AuthenticationProvider,
)

logging.basicConfig(level=logging.DEBUG)
pytestmark = pytest.mark.usefixtures("fake_pipeline_thread")

# Update this list with features as they are added to the SDK
all_features = [
    constant.C2D_MSG,
    constant.INPUT_MSG,
    constant.METHODS,
    constant.TWIN,
    constant.TWIN_PATCHES,
]


@pytest.fixture
def auth_provider(mocker):
    auth = mocker.MagicMock()
    # Add values so that it doesn't break down the pipeline.
    # This will no longer be needed after auth revisions.
    auth.device_id = "fake_device"
    auth.module_id = None
    return auth


@pytest.fixture
def pipeline_configuration(mocker):
    return mocker.MagicMock()


@pytest.fixture
def pipeline(mocker, auth_provider, pipeline_configuration):
    pipeline = MQTTPipeline(auth_provider, pipeline_configuration)
    mocker.patch.object(pipeline._pipeline, "run_op")
    return pipeline


@pytest.fixture
def twin_patch():
    return {"key": "value"}


# automatically mock the transport for all tests in this file.
@pytest.fixture(autouse=True)
def mock_transport(mocker):
    print("mocking transport")
    mocker.patch(
        "azure.iot.device.common.pipeline.pipeline_stages_mqtt.MQTTTransport", autospec=True
    )


@pytest.mark.describe("MQTTPipeline - Instantiation")
class TestMQTTPipelineInstantiation(object):
    @pytest.mark.it("Begins tracking the enabled/disabled status of features")
    @pytest.mark.parametrize("feature", all_features)
    def test_features(self, auth_provider, pipeline_configuration, feature):
        pipeline = MQTTPipeline(auth_provider, pipeline_configuration)
        pipeline.feature_enabled[feature]
        # No assertion required - if this doesn't raise a KeyError, it is a success

    @pytest.mark.it("Marks all features as disabled")
    def test_features_disabled(self, auth_provider, pipeline_configuration):
        pipeline = MQTTPipeline(auth_provider, pipeline_configuration)
        for key in pipeline.feature_enabled:
            assert not pipeline.feature_enabled[key]

    @pytest.mark.it("Sets all handlers to an initial value of None")
    def test_handlers_set_to_none(self, auth_provider, pipeline_configuration):
        pipeline = MQTTPipeline(auth_provider, pipeline_configuration)
        assert pipeline.on_connected is None
        assert pipeline.on_disconnected is None
        assert pipeline.on_c2d_message_received is None
        assert pipeline.on_input_message_received is None
        assert pipeline.on_method_request_received is None
        assert pipeline.on_twin_patch_received is None

    @pytest.mark.it("Configures the pipeline to trigger handlers in response to external events")
    def test_handlers_configured(self, auth_provider, pipeline_configuration):
        pipeline = MQTTPipeline(auth_provider, pipeline_configuration)
        assert pipeline._pipeline.on_pipeline_event_handler is not None
        assert pipeline._pipeline.on_connected_handler is not None
        assert pipeline._pipeline.on_disconnected_handler is not None

    @pytest.mark.it("Configures the pipeline with a series of PipelineStages")
    def test_pipeline_configuration(self, auth_provider, pipeline_configuration):
        pipeline = MQTTPipeline(auth_provider, pipeline_configuration)
        curr_stage = pipeline._pipeline

        expected_stage_order = [
            pipeline_stages_base.PipelineRootStage,
            pipeline_stages_iothub.UseAuthProviderStage,
            pipeline_stages_iothub.EnsureDesiredPropertiesStage,
            pipeline_stages_iothub.TwinRequestResponseStage,
            pipeline_stages_base.CoordinateRequestAndResponseStage,
            pipeline_stages_iothub_mqtt.IoTHubMQTTTranslationStage,
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

    # TODO: revist these tests after auth revision
    # They are too tied to auth types (and there's too much variance in auths to effectively test)
    # Ideally MQTTPipeline is entirely insulated from any auth differential logic (and module/device distinctions)
    # In the meantime, we are using a device auth with connection string to stand in for generic SAS auth
    # and device auth with X509 certs to stand in for generic X509 auth
    @pytest.mark.it(
        "Runs a SetAuthProviderOperation with the provided AuthenticationProvider on the pipeline, if using SAS based authentication"
    )
    def test_sas_auth(self, mocker, device_connection_string, pipeline_configuration):
        mocker.spy(pipeline_stages_base.PipelineRootStage, "run_op")
        auth_provider = SymmetricKeyAuthenticationProvider.parse(device_connection_string)
        pipeline = MQTTPipeline(auth_provider, pipeline_configuration)
        op = pipeline._pipeline.run_op.call_args[0][1]
        assert pipeline._pipeline.run_op.call_count == 1
        assert isinstance(op, pipeline_ops_iothub.SetAuthProviderOperation)
        assert op.auth_provider is auth_provider

    @pytest.mark.it(
        "Raises exceptions that occurred in execution upon unsuccessful completion of the SetAuthProviderOperation"
    )
    def test_sas_auth_op_fail(
        self, mocker, device_connection_string, arbitrary_exception, pipeline_configuration
    ):
        old_run_op = pipeline_stages_base.PipelineRootStage._run_op

        def fail_set_auth_provider(self, op):
            if isinstance(op, pipeline_ops_iothub.SetAuthProviderOperation):
                op.complete(error=arbitrary_exception)
            else:
                old_run_op(self, op)

        mocker.patch.object(
            pipeline_stages_base.PipelineRootStage,
            "_run_op",
            side_effect=fail_set_auth_provider,
            autospec=True,
        )

        auth_provider = SymmetricKeyAuthenticationProvider.parse(device_connection_string)
        with pytest.raises(arbitrary_exception.__class__) as e_info:
            MQTTPipeline(auth_provider, pipeline_configuration)
        assert e_info.value is arbitrary_exception

    @pytest.mark.it(
        "Runs a SetX509AuthProviderOperation with the provided AuthenticationProvider on the pipeline, if using SAS based authentication"
    )
    def test_cert_auth(self, mocker, x509, pipeline_configuration):
        mocker.spy(pipeline_stages_base.PipelineRootStage, "run_op")
        auth_provider = X509AuthenticationProvider(
            hostname="somehostname", device_id="somedevice", x509=x509
        )
        pipeline = MQTTPipeline(auth_provider, pipeline_configuration)
        op = pipeline._pipeline.run_op.call_args[0][1]
        assert pipeline._pipeline.run_op.call_count == 1
        assert isinstance(op, pipeline_ops_iothub.SetX509AuthProviderOperation)
        assert op.auth_provider is auth_provider

    @pytest.mark.it(
        "Raises exceptions that occurred in execution upon unsuccessful completion of the SetX509AuthProviderOperation"
    )
    def test_cert_auth_op_fail(self, mocker, x509, arbitrary_exception, pipeline_configuration):
        old_run_op = pipeline_stages_base.PipelineRootStage._run_op

        def fail_set_auth_provider(self, op):
            if isinstance(op, pipeline_ops_iothub.SetX509AuthProviderOperation):
                op.complete(error=arbitrary_exception)
            else:
                old_run_op(self, op)

        mocker.patch.object(
            pipeline_stages_base.PipelineRootStage,
            "_run_op",
            side_effect=fail_set_auth_provider,
            autospec=True,
        )

        auth_provider = X509AuthenticationProvider(
            hostname="somehostname", device_id="somedevice", x509=x509
        )
        with pytest.raises(arbitrary_exception.__class__):
            MQTTPipeline(auth_provider, pipeline_configuration)


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


@pytest.mark.describe("MQTTPipeline - .send_message()")
class TestMQTTPipelineSendD2CMessage(object):
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


@pytest.mark.describe("MQTTPipeline - .send_output_event()")
class TestMQTTPipelineSendOutputEvent(object):
    @pytest.fixture
    def message(self, message):
        """Modify message fixture to have an output"""
        message.output_name = "some output"
        return message

    @pytest.mark.it("Runs a SendOutputEventOperation with the provided Message on the pipeline")
    def test_runs_op(self, pipeline, message, mocker):
        pipeline.send_output_event(message, callback=mocker.MagicMock())
        op = pipeline._pipeline.run_op.call_args[0][0]

        assert pipeline._pipeline.run_op.call_count == 1
        assert isinstance(op, pipeline_ops_iothub.SendOutputEventOperation)
        assert op.message == message

    @pytest.mark.it(
        "Triggers the callback upon successful completion of the SendOutputEventOperation"
    )
    def test_op_success_with_callback(self, mocker, pipeline, message):
        cb = mocker.MagicMock()

        # Begin operation
        pipeline.send_output_event(message, callback=cb)
        assert cb.call_count == 0

        # Trigger op completion callback
        op = pipeline._pipeline.run_op.call_args[0][0]
        op.complete(error=None)

        assert cb.call_count == 1
        assert cb.call_args == mocker.call(error=None)

    @pytest.mark.it(
        "Calls the callback with the error upon unsuccessful completion of the SendOutputEventOperation"
    )
    def test_op_fail(self, mocker, pipeline, message, arbitrary_exception):
        cb = mocker.MagicMock()
        pipeline.send_output_event(message, callback=cb)

        op = pipeline._pipeline.run_op.call_args[0][0]
        op.complete(error=arbitrary_exception)

        assert cb.call_count == 1
        assert cb.call_args == mocker.call(error=arbitrary_exception)


@pytest.mark.describe("MQTTPipeline - .send_method_response()")
class TestMQTTPipelineSendMethodResponse(object):
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
    @pytest.mark.it("Marks the feature as disabled")
    @pytest.mark.parametrize("feature", all_features)
    def test_mark_feature_disabled(self, pipeline, feature, mocker):
        # enable feature first
        pipeline.feature_enabled[feature] = True
        assert pipeline.feature_enabled[feature]
        pipeline.disable_feature(feature, callback=mocker.MagicMock())
        assert not pipeline.feature_enabled[feature]

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


@pytest.mark.describe("MQTTPipeline - OCCURANCE: Connected")
class TestMQTTPipelineEVENTConnect(object):
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


@pytest.mark.describe("MQTTPipeline - OCCURANCE: Disconnected")
class TestMQTTPipelineEVENTDisconnect(object):
    @pytest.mark.it("Triggers the 'on_disconnected' handler")
    def test_with_handler(self, mocker, pipeline):
        # Set the handler
        mock_handler = mocker.MagicMock()
        pipeline.on_disconnected = mock_handler
        assert mock_handler.call_count == 0

        # Trigger the connect
        pipeline._pipeline.on_disconnected_handler()

        assert mock_handler.call_count == 1
        assert mock_handler.call_args == mocker.call()

    @pytest.mark.it("Does nothing if the 'on_disconnected' handler is not set")
    def test_without_handler(self, pipeline):
        pipeline._pipeline.on_disconnected_handler()

        # No assertions required - not throwing an exception means the test passed


@pytest.mark.describe("MQTTPipeline - OCCURANCE: C2D Message Received")
class TestMQTTPipelineEVENTRecieveC2DMessage(object):
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


@pytest.mark.describe("MQTTPipeline - OCCURANCE: Input Message Received")
class TestMQTTPipelineEVENTReceiveInputMessage(object):
    @pytest.mark.it(
        "Triggers the 'on_input_message_received' handler, passing the received message and input name as arguments"
    )
    def test_with_handler(self, mocker, pipeline, message):
        # Set the handler
        mock_handler = mocker.MagicMock()
        pipeline.on_input_message_received = mock_handler
        assert mock_handler.call_count == 0

        # Create the event
        input_name = "some_input"
        input_message_event = pipeline_events_iothub.InputMessageEvent(input_name, message)

        # Trigger the event
        pipeline._pipeline.on_pipeline_event_handler(input_message_event)

        assert mock_handler.call_count == 1
        assert mock_handler.call_args == mocker.call(input_name, message)

    @pytest.mark.it("Drops the message if the 'on_input_message_received' handler is not set")
    def test_no_handler(self, pipeline, message):
        input_name = "some_input"
        input_message_event = pipeline_events_iothub.InputMessageEvent(input_name, message)
        pipeline._pipeline.on_pipeline_event_handler(input_message_event)

        # No assertions required - not throwing an exception means the test passed


@pytest.mark.describe("MQTTPipeline - OCCURANCE: Method Request Received")
class TestMQTTPipelineEVENTReceiveMethodRequest(object):
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


@pytest.mark.describe("MQTTPipeline - OCCURANCE: Twin Desired Properties Patch Received")
class TestMQTTPipelineEVENTReceiveDesiredPropertiesPatch(object):
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


@pytest.mark.describe("MQTTPipeline - PROPERTY .connected")
class TestMQTTPipelinePROPERTYConnected(object):
    @pytest.mark.it("Cannot be changed")
    def test_read_only(self, pipeline):
        with pytest.raises(AttributeError):
            pipeline.connected = not pipeline.connected

    @pytest.mark.it("Reflects the value of the root stage property of the same name")
    def test_reflects_pipeline_property(self, pipeline):
        pipeline._pipeline.connected = True
        assert pipeline.connected
        pipeline._pipeline.connected = False
        assert not pipeline.connected
