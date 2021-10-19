# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging
import sys
from azure.iot.device.common.evented_callback import EventedCallback
from azure.iot.device.common.pipeline import (
    pipeline_events_base,
    pipeline_stages_base,
    pipeline_ops_base,
    pipeline_stages_mqtt,
    pipeline_exceptions,
)
from . import (
    constant,
    pipeline_stages_iothub,
    pipeline_events_iothub,
    pipeline_ops_iothub,
    pipeline_stages_iothub_mqtt,
)

logger = logging.getLogger(__name__)


class MQTTPipeline(object):
    def __init__(self, pipeline_configuration):
        """
        Constructor for instantiating a pipeline adapter object
        :param auth_provider: The authentication provider
        :param pipeline_configuration: The configuration generated based on user inputs
        """

        self.feature_enabled = {
            constant.C2D_MSG: False,
            constant.INPUT_MSG: False,
            constant.METHODS: False,
            constant.TWIN: False,
            constant.TWIN_PATCHES: False,
        }

        # Handlers - Will be set by Client after instantiation of this object
        self.on_connected = None
        self.on_disconnected = None
        self.on_new_sastoken_required = None
        self.on_background_exception = None

        self.on_c2d_message_received = None
        self.on_input_message_received = None
        self.on_method_request_received = None
        self.on_twin_patch_received = None

        # Currently a single timeout stage and a single retry stage for MQTT retry only.
        # Later, a higher level timeout and a higher level retry stage.
        self._pipeline = (
            #
            # The root is always the root.  By definition, it's the first stage in the pipeline.
            #
            pipeline_stages_base.PipelineRootStage(pipeline_configuration)
            #
            # SasTokenStage comes near the root by default because it should be as close
            # to the top of the pipeline as possible, and does not need to be after anything.
            #
            .append_stage(pipeline_stages_base.SasTokenStage())
            #
            # EnsureDesiredPropertiesStage needs to be above TwinRequestResponseStage because it
            # sends GetTwinOperation ops and that stage handles those ops.
            #
            .append_stage(pipeline_stages_iothub.EnsureDesiredPropertiesStage())
            #
            # TwinRequestResponseStage comes near the root by default because it doesn't need to be
            # after anything
            #
            .append_stage(pipeline_stages_iothub.TwinRequestResponseStage())
            #
            # CoordinateRequestAndResponseStage needs to be after TwinRequestResponseStage because
            # TwinRequestResponseStage creates the request ops that CoordinateRequestAndResponseStage
            # is coordinating.  It needs to be before IoTHubMQTTTranslationStage because that stage
            # operates on ops that CoordinateRequestAndResponseStage produces
            #
            .append_stage(pipeline_stages_base.CoordinateRequestAndResponseStage())
            #
            # IoTHubMQTTTranslationStage comes here because this is the point where we can translate
            # all operations directly into MQTT.  After this stage, only pipeline_stages_base stages
            # are allowed because IoTHubMQTTTranslationStage removes all the IoTHub-ness from the ops
            #
            .append_stage(pipeline_stages_iothub_mqtt.IoTHubMQTTTranslationStage())
            #
            # AutoConnectStage comes here because only MQTT ops have the need_connection flag set
            # and this is the first place in the pipeline where we can guaranetee that all network
            # ops are MQTT ops.
            #
            .append_stage(pipeline_stages_base.AutoConnectStage())
            #
            # ReconnectStage needs to be after AutoConnectStage because ReconnectStage sets/clears
            # the virtually_conencted flag and we want an automatic connection op to set this flag so
            # we can reconnect autoconnect operations.  This is important, for example, if a
            # send_message causes the transport to automatically connect, but that connection fails.
            # When that happens, the ReconnectState will hold onto the ConnectOperation until it
            # succeeds, and only then will return success to the AutoConnectStage which will
            # allow the publish to continue.
            #
            .append_stage(pipeline_stages_base.ReconnectStage())
            #
            # ConnectionLockStage needs to be after ReconnectStage because we want any ops that
            # ReconnectStage creates to go through the ConnectionLockStage gate
            #
            .append_stage(pipeline_stages_base.ConnectionLockStage())
            #
            # RetryStage needs to be near the end because it's retrying low-level MQTT operations.
            #
            .append_stage(pipeline_stages_base.RetryStage())
            #
            # OpTimeoutStage needs to be after RetryStage because OpTimeoutStage returns the timeout
            # errors that RetryStage is watching for.
            #
            .append_stage(pipeline_stages_base.OpTimeoutStage())
            #
            # MQTTTransportStage needs to be at the very end of the pipeline because this is where
            # operations turn into network traffic
            #
            .append_stage(pipeline_stages_mqtt.MQTTTransportStage())
        )

        # Define behavior for domain-specific events
        def _on_pipeline_event(event):
            if isinstance(event, pipeline_events_iothub.C2DMessageEvent):
                if self.on_c2d_message_received:
                    self.on_c2d_message_received(event.message)
                else:
                    logger.error("C2D message event received with no handler.  dropping.")

            elif isinstance(event, pipeline_events_iothub.InputMessageEvent):
                if self.on_input_message_received:
                    self.on_input_message_received(event.message)
                else:
                    logger.error("input message event received with no handler.  dropping.")

            elif isinstance(event, pipeline_events_iothub.MethodRequestEvent):
                if self.on_method_request_received:
                    self.on_method_request_received(event.method_request)
                else:
                    logger.error("Method request event received with no handler. Dropping.")

            elif isinstance(event, pipeline_events_iothub.TwinDesiredPropertiesPatchEvent):
                if self.on_twin_patch_received:
                    self.on_twin_patch_received(event.patch)
                else:
                    logger.error("Twin patch event received with no handler. Dropping.")

            else:
                logger.error("Dropping unknown pipeline event {}".format(event.name))

        def _on_connected():
            if self.on_connected:
                self.on_connected()
            else:
                logger.debug("IoTHub Pipeline was connected, but no handler was set")

        def _on_disconnected():
            if self.on_disconnected:
                self.on_disconnected()
            else:
                logger.debug("IoTHub Pipeline was disconnected, but no handler was set")

        def _on_new_sastoken_required():
            if self.on_new_sastoken_required:
                self.on_new_sastoken_required()
            else:
                logger.debug("IoTHub Pipeline requires new SASToken, but no handler was set")

        def _on_background_exception(e):
            if self.on_background_exception:
                self.on_background_exception(e)
            else:
                logger.debug(
                    "IoTHub Pipeline experienced background exception, but no handler was set"
                )

        # Set internal event handlers
        self._pipeline.on_pipeline_event_handler = _on_pipeline_event
        self._pipeline.on_connected_handler = _on_connected
        self._pipeline.on_disconnected_handler = _on_disconnected
        self._pipeline.on_new_sastoken_required_handler = _on_new_sastoken_required
        self._pipeline.on_background_exception_handler = _on_background_exception

        # Initialize the pipeline
        callback = EventedCallback()
        op = pipeline_ops_base.InitializePipelineOperation(callback=callback)
        self._pipeline.run_op(op)
        callback.wait_for_completion()

        # Set the running flag
        self._running = True

    def _verify_running(self):
        if not self._running:
            raise pipeline_exceptions.PipelineNotRunning(
                "Cannot execute method - Pipeline is not running"
            )

    def shutdown(self, callback):
        """Shut down the pipeline and clean up any resources.

        Once shut down, making any further calls on the pipeline will result in a
        PipelineNotRunning exception being raised.

        There is currently no way to resume pipeline functionality once shutdown has occurred.

        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.PipelineNotRunning` if the
            pipeline has already been shut down

        The shutdown process itself is not expected to fail under any normal condition, but if it
        does, exceptions are not "raised", but rather, returned via the "error" parameter when
        invoking "callback".
        """
        self._verify_running()
        logger.debug("Commencing shutdown of pipeline")

        def on_complete(op, error):
            if not error:
                # Only set the pipeline to not be running if the op was successful
                self._running = False
            callback(error=error)

        # NOTE: While we do run this operation, its functionality is incomplete. Some stages still
        # need a response to this operation implemented. Additionally, there are other pipeline
        # constructs other than Stages (e.g. Operations) which may have timers attached. These are
        # lesser issues, but should be addressed at some point.
        # TODO: Truly complete the shutdown implementation
        self._pipeline.run_op(pipeline_ops_base.ShutdownPipelineOperation(callback=on_complete))

    def connect(self, callback):
        """
        Connect to the service.

        :param callback: callback which is called when the connection attempt is complete.

        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.PipelineNotRunning` if the
            pipeline has previously been shut down

        The following exceptions are not "raised", but rather returned via the "error" parameter
        when invoking "callback":

        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.ConnectionFailedError`
        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.ConnectionDroppedError`
        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.UnauthorizedError`
        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.ProtocolClientError`
        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.OperationTimeout`
        """
        self._verify_running()
        logger.debug("Starting ConnectOperation on the pipeline")

        def on_complete(op, error):
            callback(error=error)

        self._pipeline.run_op(pipeline_ops_base.ConnectOperation(callback=on_complete))

    def disconnect(self, callback):
        """
        Disconnect from the service.

        Note that even if this fails for some reason, the client will be in a disconnected state.

        :param callback: callback which is called when the disconnection is complete.

        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.PipelineNotRunning` if the
            pipeline has previously been shut down

        The following exceptions are not "raised", but rather returned via the "error" parameter
        when invoking "callback":

        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.ProtocolClientError`
        """
        self._verify_running()
        logger.debug("Starting DisconnectOperation on the pipeline")

        def on_complete(op, error):
            callback(error=error)

        self._pipeline.run_op(pipeline_ops_base.DisconnectOperation(callback=on_complete))

    def reauthorize_connection(self, callback):
        """
        Reauthorize connection to the service by disconnecting and then reconnecting using
        fresh credentials.

        This can be called regardless of connection state. If successful, the client will be
        connected. If unsuccessful, the client will be disconnected.

        :param callback: callback which is called when the reauthorization attempt is complete.

        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.PipelineNotRunning` if the
            pipeline has previously been shut down

        The following exceptions are not "raised", but rather returned via the "error" parameter
        when invoking "callback":

        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.ConnectionFailedError`
        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.ConnectionDroppedError`
        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.UnauthorizedError`
        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.ProtocolClientError`
        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.OperationTimeout`
        """
        self._verify_running()
        logger.debug("Starting ReauthorizeConnectionOperation on the pipeline")

        def on_complete(op, error):
            callback(error=error)

        self._pipeline.run_op(
            pipeline_ops_base.ReauthorizeConnectionOperation(callback=on_complete)
        )

    def send_message(self, message, callback):
        """
        Send a telemetry message to the service.

        :param message: message to send.
        :param callback: callback which is called when the message publish attempt is complete.

        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.PipelineNotRunning` if the
            pipeline has previously been shut down

        The following exceptions are not "raised", but rather returned via the "error" parameter
        when invoking "callback":

        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.NoConnectionError`
        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.ProtocolClientError`

        The following exceptions can be returned via the "error" parameter only if auto-connect
        is enabled in the pipeline configuration:

        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.ConnectionFailedError`
        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.ConnectionDroppedError`
        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.UnauthorizedError`
        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.OperationTimeout`
        """
        self._verify_running()
        logger.debug("Starting SendD2CMessageOperation on the pipeline")

        def on_complete(op, error):
            callback(error=error)

        self._pipeline.run_op(
            pipeline_ops_iothub.SendD2CMessageOperation(message=message, callback=on_complete)
        )

    def send_output_message(self, message, callback):
        """
        Send an output message to the service.

        :param message: message to send.
        :param callback: callback which is called when the message publish attempt is complete.

        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.PipelineNotRunning` if the
            pipeline has previously been shut down

        The following exceptions are not "raised", but rather returned via the "error" parameter
        when invoking "callback":

        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.NoConnectionError`
        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.ProtocolClientError`

        The following exceptions can be returned via the "error" parameter only if auto-connect
        is enabled in the pipeline configuration:

        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.ConnectionFailedError`
        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.ConnectionDroppedError`
        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.UnauthorizedError`
        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.OperationTimeout`
        """
        self._verify_running()
        logger.debug("Starting SendOutputMessageOperation on the pipeline")

        def on_complete(op, error):
            callback(error=error)

        self._pipeline.run_op(
            pipeline_ops_iothub.SendOutputMessageOperation(message=message, callback=on_complete)
        )

    def send_method_response(self, method_response, callback):
        """
        Send a method response to the service.

        :param method_response: the method response to send
        :param callback: callback which is called when response publish attempt is complete.

        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.PipelineNotRunning` if the
            pipeline has previously been shut down

        The following exceptions are not "raised", but rather returned via the "error" parameter
        when invoking "callback":

        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.NoConnectionError`
        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.ProtocolClientError`

        The following exceptions can be returned via the "error" parameter only if auto-connect
        is enabled in the pipeline configuration:

        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.ConnectionFailedError`
        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.ConnectionDroppedError`
        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.UnauthorizedError`
        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.OperationTimeout`
        """
        self._verify_running()
        logger.debug("Starting SendMethodResponseOperation on the pipeline")

        def on_complete(op, error):
            callback(error=error)

        self._pipeline.run_op(
            pipeline_ops_iothub.SendMethodResponseOperation(
                method_response=method_response, callback=on_complete
            )
        )

    def get_twin(self, callback):
        """
        Send a request for a full twin to the service.

        :param callback: callback which is called when request attempt is complete.
            This callback should have two parameters.  On success, this callback is called with the
            requested twin and error=None.  On failure, this callback is called with None for the
            requested win and error set to the cause of the failure.

        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.PipelineNotRunning` if the
            pipeline has previously been shut down

        The following exceptions are not "raised", but rather returned via the "error" parameter
        when invoking "callback":

        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.NoConnectionError`
        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.ProtocolClientError`

        The following exceptions can be returned via the "error" parameter only if auto-connect
        is enabled in the pipeline configuration:

        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.ConnectionFailedError`
        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.ConnectionDroppedError`
        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.UnauthorizedError`
        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.OperationTimeout`
        """
        self._verify_running()
        logger.debug("Starting GetTwinOperation on the pipeline")

        def on_complete(op, error):
            if error:
                callback(error=error, twin=None)
            else:
                callback(twin=op.twin)

        self._pipeline.run_op(pipeline_ops_iothub.GetTwinOperation(callback=on_complete))

    def patch_twin_reported_properties(self, patch, callback):
        """
        Send a patch for a twin's reported properties to the service.

        :param patch: the reported properties patch to send
        :param callback: callback which is called when the request attempt is complete.

        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.PipelineNotRunning` if the
            pipeline has previously been shut down

        The following exceptions are not "raised", but rather returned via the "error" parameter
        when invoking "callback":

        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.NoConnectionError`
        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.ProtocolClientError`

        The following exceptions can be returned via the "error" parameter only if auto-connect
        is enabled in the pipeline configuration:

        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.ConnectionFailedError`
        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.ConnectionDroppedError`
        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.UnauthorizedError`
        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.OperationTimeout`
        """
        self._verify_running()
        logger.debug("Starting PatchTwinReportedPropertiesOperation on the pipeline")

        def on_complete(op, error):
            callback(error=error)

        self._pipeline.run_op(
            pipeline_ops_iothub.PatchTwinReportedPropertiesOperation(
                patch=patch, callback=on_complete
            )
        )

    # NOTE: Currently, this operation will retry itself indefinitely in the case of timeout
    def enable_feature(self, feature_name, callback):
        """
        Enable the given feature by subscribing to the appropriate topics.

        :param feature_name: one of the feature name constants from constant.py
        :param callback: callback which is called when the feature is enabled

        :raises: ValueError if feature_name is invalid
        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.PipelineNotRunning` if the
            pipeline has previously been shut down

        The following exceptions are not "raised", but rather returned via the "error" parameter
        when invoking "callback":

        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.NoConnectionError`
        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.ProtocolClientError`

        The following exceptions can be returned via the "error" parameter only if auto-connect
        is enabled in the pipeline configuration:

        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.ConnectionFailedError`
        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.ConnectionDroppedError`
        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.UnauthorizedError`
        """
        self._verify_running()
        logger.debug("enable_feature {} called".format(feature_name))
        if feature_name not in self.feature_enabled:
            raise ValueError("Invalid feature_name")
        # TODO: What about if the feature is already enabled?

        def on_complete(op, error):
            if error:
                logger.error("Subscribe for {} failed.  Not enabling feature".format(feature_name))
            else:
                self.feature_enabled[feature_name] = True
            callback(error=error)

        self._pipeline.run_op(
            pipeline_ops_base.EnableFeatureOperation(
                feature_name=feature_name, callback=on_complete
            )
        )

    # NOTE: Currently, this operation will retry itself indefinitely in the case of timeout
    def disable_feature(self, feature_name, callback):
        """
        Disable the given feature by subscribing to the appropriate topics.
        :param callback: callback which is called when the feature is disabled

        :param feature_name: one of the feature name constants from constant.py

        :raises: ValueError if feature_name is invalid
        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.PipelineNotRunning` if the
            pipeline has previously been shut down

        The following exceptions are not "raised", but rather returned via the "error" parameter
        when invoking "callback":

        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.NoConnectionError`
        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.ProtocolClientError`

        The following exceptions can be returned via the "error" parameter only if auto-connect
        is enabled in the pipeline configuration:

        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.ConnectionFailedError`
        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.ConnectionDroppedError`
        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.UnauthorizedError`
        """
        self._verify_running()
        logger.debug("disable_feature {} called".format(feature_name))
        if feature_name not in self.feature_enabled:
            raise ValueError("Invalid feature_name")
        # TODO: What about if the feature is already disabled?

        def on_complete(op, error):
            if error:
                logger.warning(
                    "Error occurred while disabling feature. Unclear if subscription for {} is still alive or not".format(
                        feature_name
                    )
                )

            # No matter what, mark the feature as disabled, even if there was an error.
            # This is safer than only marking it disabled upon operation success, because an op
            # could fail after successfully doing the network operations to change the subscription
            # state, and then we would be stuck in a bad state.
            self.feature_enabled[feature_name] = False
            callback(error=error)

        self._pipeline.run_op(
            pipeline_ops_base.DisableFeatureOperation(
                feature_name=feature_name, callback=on_complete
            )
        )

    @property
    def pipeline_configuration(self):
        """
        Pipeline Configuration for the pipeline. Note that while a new config object cannot be
        provided (read-only), the values stored in the config object CAN be changed.
        """
        return self._pipeline.pipeline_configuration

    @property
    def connected(self):
        """
        Read-only property to indicate if the transport is connected or not.
        """
        return self._pipeline.connected
