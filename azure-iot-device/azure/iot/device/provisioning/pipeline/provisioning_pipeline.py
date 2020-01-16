# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging
from azure.iot.device.common.evented_callback import EventedCallback
from azure.iot.device.common.pipeline import pipeline_stages_base
from azure.iot.device.common.pipeline import pipeline_ops_base
from azure.iot.device.common.pipeline import pipeline_stages_mqtt
from azure.iot.device.provisioning.pipeline import (
    pipeline_stages_provisioning,
    pipeline_stages_provisioning_mqtt,
)
from azure.iot.device.provisioning.pipeline import pipeline_ops_provisioning
from azure.iot.device.provisioning.security import SymmetricKeySecurityClient, X509SecurityClient
from azure.iot.device.provisioning.pipeline import constant as provisioning_constants

logger = logging.getLogger(__name__)


class ProvisioningPipeline(object):
    def __init__(self, security_client, pipeline_configuration):
        """
        Constructor for instantiating a pipeline
        :param security_client: The security client which stores credentials
        """
        self.responses_enabled = {provisioning_constants.REGISTER: False}

        # Event Handlers - Will be set by Client after instantiation of pipeline
        self.on_connected = None
        self.on_disconnected = None
        self.on_message_received = None
        self._registration_id = security_client.registration_id

        self._pipeline = (
            pipeline_stages_base.PipelineRootStage(pipeline_configuration=pipeline_configuration)
            .append_stage(pipeline_stages_provisioning.UseSecurityClientStage())
            .append_stage(pipeline_stages_provisioning.RegistrationStage())
            .append_stage(pipeline_stages_provisioning.PollingStatusStage())
            .append_stage(pipeline_stages_base.CoordinateRequestAndResponseStage())
            # .append_stage(pipeline_stages_provisioning.ProvisioningTimeoutStage())
            .append_stage(pipeline_stages_provisioning_mqtt.ProvisioningMQTTTranslationStage())
            .append_stage(pipeline_stages_base.ReconnectStage())
            .append_stage(pipeline_stages_base.AutoConnectStage())
            .append_stage(pipeline_stages_base.ConnectionLockStage())
            .append_stage(pipeline_stages_base.RetryStage())
            .append_stage(pipeline_stages_base.OpTimeoutStage())
            .append_stage(pipeline_stages_mqtt.MQTTTransportStage())
        )

        def _on_pipeline_event(event):
            logger.warning("Dropping unknown pipeline event {}".format(event.name))

        def _on_connected():
            if self.on_connected:
                self.on_connected("connected")

        def _on_disconnected():
            if self.on_disconnected:
                self.on_disconnected("disconnected")

        self._pipeline.on_pipeline_event_handler = _on_pipeline_event
        self._pipeline.on_connected_handler = _on_connected
        self._pipeline.on_disconnected_handler = _on_disconnected

        callback = EventedCallback()

        if isinstance(security_client, X509SecurityClient):
            op = pipeline_ops_provisioning.SetX509SecurityClientOperation(
                security_client=security_client, callback=callback
            )
        elif isinstance(security_client, SymmetricKeySecurityClient):
            op = pipeline_ops_provisioning.SetSymmetricKeySecurityClientOperation(
                security_client=security_client, callback=callback
            )
        else:
            logger.error("Provisioning not equipped to handle other security client.")

        self._pipeline.run_op(op)
        callback.wait_for_completion()

    def connect(self, callback=None):
        """
        Connect to the service.

        :param callback: callback which is called when the connection to the service is complete.

        The following exceptions are not "raised", but rather returned via the "error" parameter
        when invoking "callback":

        :raises: :class:`azure.iot.device.provisioning.pipeline.exceptions.ConnectionFailedError`
        :raises: :class:`azure.iot.device.provisioning.pipeline.exceptions.ConnectionDroppedError`
        :raises: :class:`azure.iot.device.provisioning.pipeline.exceptions.UnauthorizedError`
        :raises: :class:`azure.iot.device.provisioning.pipeline.exceptions.ProtocolClientError`
        """
        logger.info("connect called")

        def pipeline_callback(op, error):
            callback(error=error)

        self._pipeline.run_op(pipeline_ops_base.ConnectOperation(callback=pipeline_callback))

    def disconnect(self, callback=None):
        """
        Disconnect from the service.

        :param callback: callback which is called when the connection to the service has been disconnected

        The following exceptions are not "raised", but rather returned via the "error" parameter
        when invoking "callback":

        :raises: :class:`azure.iot.device.iothub.pipeline.exceptions.ProtocolClientError`
        """
        logger.info("disconnect called")

        def pipeline_callback(op, error):
            callback(error=error)

        self._pipeline.run_op(pipeline_ops_base.DisconnectOperation(callback=pipeline_callback))

    def enable_responses(self, callback=None):
        """
        Enable response from the DPS service by subscribing to the appropriate topics.

        :param callback: callback which is called when responses are enabled
        """
        logger.debug("enable_responses called")

        self.responses_enabled[provisioning_constants.REGISTER] = True

        def pipeline_callback(op, error):
            callback(error=error)

        self._pipeline.run_op(
            pipeline_ops_base.EnableFeatureOperation(feature_name=None, callback=pipeline_callback)
        )

    def disable_responses(self, callback=None):
        """
        Disable response from the DPS service by unsubscribing from the appropriate topics.
        :param callback: callback which is called when the responses are disabled

        """
        logger.debug("disable_responses called")

        def pipeline_callback(op, error):
            callback(error=error)

        self._pipeline.run_op(
            pipeline_ops_base.DisableFeatureOperation(feature_name=None, callback=pipeline_callback)
        )

    def register(self, payload=None, callback=None):
        """
        Register to the device provisioning service.
        :param payload: Payload that can be sent with the registration request.
        :param callback: callback which is called when the registration is done.

        The following exceptions are not "raised", but rather returned via the "error" parameter
        when invoking "callback":

        :raises: :class:`azure.iot.device.provisioning.pipeline.exceptions.ConnectionFailedError`
        :raises: :class:`azure.iot.device.provisioning.pipeline.exceptions.ConnectionDroppedError`
        :raises: :class:`azure.iot.device.provisioning.pipeline.exceptions.UnauthorizedError`
        :raises: :class:`azure.iot.device.provisioning.pipeline.exceptions.ProtocolClientError`
        """

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
