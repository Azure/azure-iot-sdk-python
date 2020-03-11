# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging
import sys
from azure.iot.device.common.evented_callback import EventedCallback
from azure.iot.device.common.pipeline import (
    pipeline_stages_base,
    pipeline_ops_base,
    pipeline_stages_mqtt,
)
from . import (
    constant,
    pipeline_stages_iothub,
    pipeline_events_iothub,
    pipeline_ops_iothub,
    pipeline_stages_iothub_mqtt,
)
from azure.iot.device.iothub.auth.x509_authentication_provider import X509AuthenticationProvider

logger = logging.getLogger(__name__)


class MQTTPipeline(object):
    def __init__(self, auth_provider, pipeline_configuration):
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

        # Event Handlers - Will be set by Client after instantiation of this object
        self.on_connected = None
        self.on_disconnected = None
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
            pipeline_stages_base.PipelineRootStage(pipeline_configuration=pipeline_configuration)
            #
            # UseAuthProviderStage comes near the root by default because it doesn't need to be after
            # anything, but it does need to be before IoTHubMQTTTranslationStage.
            #
            .append_stage(pipeline_stages_iothub.UseAuthProviderStage())
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
            # and this is the first place in the pipeline wherer we can guaranetee that all network
            # ops are MQTT ops.
            #
            .append_stage(pipeline_stages_base.AutoConnectStage())
            #
            # ReconnectStage needs to be after AutoConnectStage because ReconnectStage sets/clears
            # the virtually_conencted flag and we want an automatic connection op to set this flag so
            # we can reconnect autoconnect operations.  This is important, for example, if a
            # send_message causes the transport to automatically connect, but that connection fails.
            # When that happens, the ReconenctState will hold onto the ConnectOperation until it
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

        def _on_pipeline_event(event):
            if isinstance(event, pipeline_events_iothub.C2DMessageEvent):
                if self.on_c2d_message_received:
                    self.on_c2d_message_received(event.message)
                else:
                    logger.warning("C2D message event received with no handler.  dropping.")

            elif isinstance(event, pipeline_events_iothub.InputMessageEvent):
                if self.on_input_message_received:
                    self.on_input_message_received(event.input_name, event.message)
                else:
                    logger.warning("input message event received with no handler.  dropping.")

            elif isinstance(event, pipeline_events_iothub.MethodRequestEvent):
                if self.on_method_request_received:
                    self.on_method_request_received(event.method_request)
                else:
                    logger.warning("Method request event received with no handler. Dropping.")

            elif isinstance(event, pipeline_events_iothub.TwinDesiredPropertiesPatchEvent):
                if self.on_twin_patch_received:
                    self.on_twin_patch_received(event.patch)
                else:
                    logger.warning("Twin patch event received with no handler. Dropping.")

            else:
                logger.warning("Dropping unknown pipeline event {}".format(event.name))

        def _on_connected():
            if self.on_connected:
                self.on_connected()

        def _on_disconnected():
            if self.on_disconnected:
                self.on_disconnected()

        self._pipeline.on_pipeline_event_handler = _on_pipeline_event
        self._pipeline.on_connected_handler = _on_connected
        self._pipeline.on_disconnected_handler = _on_disconnected

        callback = EventedCallback()

        if isinstance(auth_provider, X509AuthenticationProvider):
            op = pipeline_ops_iothub.SetX509AuthProviderOperation(
                auth_provider=auth_provider, callback=callback
            )
        else:  # Currently everything else goes via this block.
            op = pipeline_ops_iothub.SetAuthProviderOperation(
                auth_provider=auth_provider, callback=callback
            )

        self._pipeline.run_op(op)
        callback.wait_for_completion()

    def connect(self, callback):
        """
        Connect to the service.

        :param callback: callback which is called when the connection to the service is complete.

        The following exceptions are not "raised", but rather returned via the "error" parameter
        when invoking "callback":

        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.ConnectionFailedError`
        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.ConnectionDroppedError`
        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.UnauthorizedError`
        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.ProtocolClientError`
        """
        logger.debug("Starting ConnectOperation on the pipeline")

        def on_complete(op, error):
            callback(error=error)

        self._pipeline.run_op(pipeline_ops_base.ConnectOperation(callback=on_complete))

    def disconnect(self, callback):
        """
        Disconnect from the service.

        :param callback: callback which is called when the connection to the service has been disconnected

        The following exceptions are not "raised", but rather returned via the "error" parameter
        when invoking "callback":

        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.ProtocolClientError`
        """
        logger.debug("Starting DisconnectOperation on the pipeline")

        def on_complete(op, error):
            callback(error=error)

        self._pipeline.run_op(pipeline_ops_base.DisconnectOperation(callback=on_complete))

    def send_message(self, message, callback):
        """
        Send a telemetry message to the service.

        :param message: message to send.
        :param callback: callback which is called when the message publish has been acknowledged by the service.

        The following exceptions are not "raised", but rather returned via the "error" parameter
        when invoking "callback":

        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.ConnectionFailedError`
        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.ConnectionDroppedError`
        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.UnauthorizedError`
        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.ProtocolClientError`
        """

        def on_complete(op, error):
            callback(error=error)

        self._pipeline.run_op(
            pipeline_ops_iothub.SendD2CMessageOperation(message=message, callback=on_complete)
        )

    def send_output_event(self, message, callback):
        """
        Send an output message to the service.

        :param message: message to send.
        :param callback: callback which is called when the message publish has been acknowledged by the service.

        The following exceptions are not "raised", but rather returned via the "error" parameter
        when invoking "callback":

        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.ConnectionFailedError`
        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.ConnectionDroppedError`
        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.UnauthorizedError`
        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.ProtocolClientError`
        """

        def on_complete(op, error):
            callback(error=error)

        self._pipeline.run_op(
            pipeline_ops_iothub.SendOutputEventOperation(message=message, callback=on_complete)
        )

    def send_method_response(self, method_response, callback):
        """
        Send a method response to the service.

        :param method_response: the method response to send
        :param callback: callback which is called when response has been acknowledged by the service

        The following exceptions are not "raised", but rather returned via the "error" parameter
        when invoking "callback":

        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.ConnectionFailedError`
        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.ConnectionDroppedError`
        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.UnauthorizedError`
        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.ProtocolClientError`
        """
        logger.debug("MQTTPipeline send_method_response called")

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

        :param callback: callback which is called when request has been acknowledged by the service.
        This callback should have two parameters.  On success, this callback is called with the
        requested twin and error=None.  On failure, this callback is called with None for the requested
        twin and error set to the cause of the failure.

        The following exceptions are not "raised", but rather returned via the "error" parameter
        when invoking "callback":

        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.ConnectionFailedError`
        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.ConnectionDroppedError`
        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.UnauthorizedError`
        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.ProtocolClientError`
        """

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
        :param callback: callback which is called when request has been acknowledged by the service.

        The following exceptions are not "raised", but rather returned via the "error" parameter
        when invoking "callback":

        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.ConnectionFailedError`
        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.ConnectionDroppedError`
        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.UnauthorizedError`
        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.ProtocolClientError`
        """

        def on_complete(op, error):
            callback(error=error)

        self._pipeline.run_op(
            pipeline_ops_iothub.PatchTwinReportedPropertiesOperation(
                patch=patch, callback=on_complete
            )
        )

    def enable_feature(self, feature_name, callback):
        """
        Enable the given feature by subscribing to the appropriate topics.

        :param feature_name: one of the feature name constants from constant.py
        :param callback: callback which is called when the feature is enabled

        :raises: ValueError if feature_name is invalid
        """
        logger.debug("enable_feature {} called".format(feature_name))
        if feature_name not in self.feature_enabled:
            raise ValueError("Invalid feature_name")
        self.feature_enabled[feature_name] = True

        def on_complete(op, error):
            callback(error=error)

        self._pipeline.run_op(
            pipeline_ops_base.EnableFeatureOperation(
                feature_name=feature_name, callback=on_complete
            )
        )

    def disable_feature(self, feature_name, callback):
        """
        Disable the given feature by subscribing to the appropriate topics.
        :param callback: callback which is called when the feature is disabled

        :param feature_name: one of the feature name constants from constant.py

        :raises: ValueError if feature_name is invalid
        """
        logger.debug("disable_feature {} called".format(feature_name))
        if feature_name not in self.feature_enabled:
            raise ValueError("Invalid feature_name")
        self.feature_enabled[feature_name] = False

        def on_complete(op, error):
            callback(error=error)

        self._pipeline.run_op(
            pipeline_ops_base.DisableFeatureOperation(
                feature_name=feature_name, callback=on_complete
            )
        )

    @property
    def connected(self):
        """
        Read-only property to indicate if the transport is connected or not.
        """
        return self._pipeline.connected
