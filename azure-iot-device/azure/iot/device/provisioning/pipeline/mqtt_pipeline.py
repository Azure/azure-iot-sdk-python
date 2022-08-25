# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging
from azure.iot.device.common.evented_callback import EventedCallback
from azure.iot.device.common.pipeline import (
    pipeline_stages_base,
    pipeline_ops_base,
    pipeline_stages_mqtt,
    pipeline_exceptions,
    pipeline_nucleus,
)
from azure.iot.device.provisioning.pipeline import (
    pipeline_stages_provisioning,
    pipeline_stages_provisioning_mqtt,
)
from azure.iot.device.provisioning.pipeline import pipeline_ops_provisioning
from azure.iot.device.provisioning.pipeline import constant as provisioning_constants

logger = logging.getLogger(__name__)


class MQTTPipeline(object):
    def __init__(self, pipeline_configuration):
        """
        Constructor for instantiating a pipeline
        :param security_client: The security client which stores credentials
        """
        self.responses_enabled = {provisioning_constants.REGISTER: False}

        # Event Handlers - Will be set by Client after instantiation of pipeline
        self.on_connected = None
        self.on_disconnected = None
        self.on_background_exception = None
        self.on_message_received = None
        self._registration_id = pipeline_configuration.registration_id

        # Contains data and information shared globally within the pipeline
        self._nucleus = pipeline_nucleus.PipelineNucleus(pipeline_configuration)

        self._pipeline = (
            #
            # The root is always the root.  By definition, it's the first stage in the pipeline.
            #
            pipeline_stages_base.PipelineRootStage(self._nucleus)
            #
            # SasTokenStage comes near the root by default because it should be as close
            # to the top of the pipeline as possible, and does not need to be after anything.
            #
            .append_stage(pipeline_stages_base.SasTokenStage())
            #
            # RegistrationStage needs to come early because this is the stage that converts registration
            # or query requests into request and response objects which are used by later stages
            #
            .append_stage(pipeline_stages_provisioning.RegistrationStage())
            #
            # PollingStatusStage needs to come after RegistrationStage because RegistrationStage counts
            # on PollingStatusStage to poll until the registration is complete.
            #
            .append_stage(pipeline_stages_provisioning.PollingStatusStage())
            #
            # CoordinateRequestAndResponseStage needs to be after RegistrationStage and PollingStatusStage
            # because these 2 stages create the request ops that CoordinateRequestAndResponseStage
            # is coordinating.  It needs to be before ProvisioningMQTTTranslationStage because that stage
            # operates on ops that CoordinateRequestAndResponseStage produces
            #
            .append_stage(pipeline_stages_base.CoordinateRequestAndResponseStage())
            #
            # ProvisioningMQTTTranslationStage comes here because this is the point where we can translate
            # all operations directly into MQTT.  After this stage, only pipeline_stages_base stages
            # are allowed because ProvisioningMQTTTranslationStage removes all the provisioning-ness from the ops
            #
            .append_stage(pipeline_stages_provisioning_mqtt.ProvisioningMQTTTranslationStage())
            #
            # AutoConnectStage comes here because only MQTT ops have the need_connection flag set
            # and this is the first place in the pipeline where we can guarantee that all network
            # ops are MQTT ops.
            #
            .append_stage(pipeline_stages_base.AutoConnectStage())
            #
            # ConnectionStateStage needs to be after AutoConnectStage because the AutoConnectStage
            # can create ConnectOperations and we (may) want to queue connection related operations
            # in the ConnectionStateStage
            #
            .append_stage(pipeline_stages_base.ConnectionStateStage())
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

        def _on_pipeline_event(event):
            # error because no events should
            logger.debug("Dropping unknown pipeline event {}".format(event.name))

        def _on_connected():
            if self.on_connected:
                self.on_connected("connected")

        def _on_disconnected():
            if self.on_disconnected:
                self.on_disconnected("disconnected")

        def _on_background_exception():
            if self.on_background_exception:
                self.on_background_exception

        self._pipeline.on_pipeline_event_handler = _on_pipeline_event
        self._pipeline.on_connected_handler = _on_connected
        self._pipeline.on_disconnected_handler = _on_disconnected

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

        :raises: :class:`azure.iot.device.provisioning.pipeline.exceptions.PipelineNotRunning` if the
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

    def connect(self, callback=None):
        """
        Connect to the service.

        :param callback: callback which is called when the connection to the service is complete.

        :raises: :class:`azure.iot.device.provisioning.pipeline.exceptions.PipelineNotRunning` if the
            pipeline has already been shut down

        The following exceptions are not "raised", but rather returned via the "error" parameter
        when invoking "callback":

        :raises: :class:`azure.iot.device.provisioning.pipeline.exceptions.ConnectionFailedError`
        :raises: :class:`azure.iot.device.provisioning.pipeline.exceptions.ConnectionDroppedError`
        :raises: :class:`azure.iot.device.provisioning.pipeline.exceptions.UnauthorizedError`
        :raises: :class:`azure.iot.device.provisioning.pipeline.exceptions.ProtocolClientError`
        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.OperationTimeout`
        """
        self._verify_running()
        logger.debug("connect called")

        def pipeline_callback(op, error):
            callback(error=error)

        self._pipeline.run_op(pipeline_ops_base.ConnectOperation(callback=pipeline_callback))

    def disconnect(self, callback=None):
        """
        Disconnect from the service.

        :param callback: callback which is called when the connection to the service has been disconnected

        :raises: :class:`azure.iot.device.provisioning.pipeline.exceptions.PipelineNotRunning` if the
            pipeline has already been shut down

        The following exceptions are not "raised", but rather returned via the "error" parameter
        when invoking "callback":

        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.ProtocolClientError`
        """
        self._verify_running()
        logger.debug("disconnect called")

        def pipeline_callback(op, error):
            callback(error=error)

        self._pipeline.run_op(pipeline_ops_base.DisconnectOperation(callback=pipeline_callback))

    # NOTE: Currently, this operation will retry itself indefinitely in the case of timeout
    def enable_responses(self, callback=None):
        """
        Enable response from the DPS service by subscribing to the appropriate topics.

        :raises: :class:`azure.iot.device.provisioning.pipeline.exceptions.PipelineNotRunning` if the
            pipeline has already been shut down

        :param callback: callback which is called when responses are enabled
        """
        self._verify_running()
        logger.debug("enable_responses called")

        self.responses_enabled[provisioning_constants.REGISTER] = True

        def pipeline_callback(op, error):
            callback(error=error)

        self._pipeline.run_op(
            pipeline_ops_base.EnableFeatureOperation(
                feature_name=provisioning_constants.REGISTER, callback=pipeline_callback
            )
        )

    def register(self, payload=None, callback=None):
        """
        Register to the device provisioning service.
        :param payload: Payload that can be sent with the registration request.
        :param callback: callback which is called when the registration is done.

        :raises: :class:`azure.iot.device.provisioning.pipeline.exceptions.PipelineNotRunning` if the
            pipeline has already been shut down

        The following exceptions are not "raised", but rather returned via the "error" parameter
        when invoking "callback":

        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.NoConnectionError`
        :raises: :class:`azure.iot.device.provisioning.pipeline.exceptions.ProtocolClientError

        The following exceptions can be returned via the "error" parameter only if auto-connect
        is enabled in the pipeline configuration:

        :raises: :class:`azure.iot.device.provisioning.pipeline.exceptions.ConnectionFailedError`
        :raises: :class:`azure.iot.device.provisioning.pipeline.exceptions.ConnectionDroppedError`
        :raises: :class:`azure.iot.device.provisioning.pipeline.exceptions.UnauthorizedError``
        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.OperationTimeout`
        """
        self._verify_running()

        def on_complete(op, error):
            # TODO : Apparently when its failed we can get result as well as error.
            if error:
                callback(error=error, result=None)
            else:
                callback(result=op.registration_result)

        self._pipeline.run_op(
            pipeline_ops_provisioning.RegisterOperation(
                request_payload=payload, registration_id=self._registration_id, callback=on_complete
            )
        )
