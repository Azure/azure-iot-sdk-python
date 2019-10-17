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
from azure.iot.device.provisioning.pipeline import pipeline_events_provisioning
from azure.iot.device.provisioning.pipeline import pipeline_ops_provisioning
from azure.iot.device.provisioning.security import SymmetricKeySecurityClient, X509SecurityClient

logger = logging.getLogger(__name__)


class ProvisioningPipeline(object):
    def __init__(self, security_client, pipeline_configuration):
        """
        Constructor for instantiating a pipeline
        :param security_client: The security client which stores credentials
        """
        # Event Handlers - Will be set by Client after instantiation of pipeline
        self.on_connected = None
        self.on_disconnected = None
        self.on_message_received = None

        self._pipeline = (
            pipeline_stages_base.PipelineRootStage(pipeline_configuration=pipeline_configuration)
            .append_stage(pipeline_stages_provisioning.UseSecurityClientStage())
            .append_stage(pipeline_stages_provisioning_mqtt.ProvisioningMQTTConverterStage())
            .append_stage(pipeline_stages_base.EnsureConnectionStage())
            .append_stage(pipeline_stages_base.SerializeConnectOpsStage())
            .append_stage(pipeline_stages_mqtt.MQTTTransportStage())
        )

        def _on_pipeline_event(event):
            if isinstance(event, pipeline_events_provisioning.RegistrationResponseEvent):
                if self.on_message_received:
                    self.on_message_received(
                        event.request_id,
                        event.status_code,
                        event.key_values,
                        event.response_payload,
                    )
                else:
                    logger.warning("Provisioning event received with no handler.  dropping.")

            else:
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
        """
        logger.info("connect called")

        def pipeline_callback(op, error):
            if error:
                # TODO we need error semantics on the client
                exit(1)
            if callback:
                callback()

        self._pipeline.run_op(pipeline_ops_base.ConnectOperation(callback=pipeline_callback))

    def disconnect(self, callback=None):
        """
        Disconnect from the service.

        :param callback: callback which is called when the connection to the service has been disconnected
        """
        logger.info("disconnect called")

        def pipeline_callback(op, error):
            if error:
                # TODO we need error semantics on the client
                exit(1)
            if callback:
                callback()

        self._pipeline.run_op(pipeline_ops_base.DisconnectOperation(callback=pipeline_callback))

    def send_request(self, request_id, request_payload, operation_id=None, callback=None):
        """
        Send a request to the Device Provisioning Service.
        :param request_id: The id of the request
        :param request_payload: The request which is to be sent.
        :param operation_id: The id of the operation.
        :param callback: callback which is called when the message publish has been acknowledged by the service.
        """

        def pipeline_callback(op, error):
            if error:
                # TODO we need error semantics on the client
                exit(1)
            if callback:
                callback()

        op = None
        if operation_id is not None:
            op = pipeline_ops_provisioning.SendQueryRequestOperation(
                request_id=request_id,
                operation_id=operation_id,
                request_payload=request_payload,
                callback=pipeline_callback,
            )
        else:
            op = pipeline_ops_provisioning.SendRegistrationRequestOperation(
                request_id=request_id, request_payload=request_payload, callback=pipeline_callback
            )

        self._pipeline.run_op(op)

    def enable_responses(self, callback=None):
        """
        Disable response from the DPS service by subscribing to the appropriate topics.

        :param callback: callback which is called when the feature is enabled
        """
        logger.debug("enable_responses called")

        def pipeline_callback(op, error):
            if error:
                # TODO we need error semantics on the client
                exit(1)
            if callback:
                callback()

        self._pipeline.run_op(
            pipeline_ops_base.EnableFeatureOperation(feature_name=None, callback=pipeline_callback)
        )

    def disable_responses(self, callback=None):
        """
        Disable response from the DPS service by unsubscribing from the appropriate topics.
        :param callback: callback which is called when the feature is disabled

        """
        logger.debug("disable_responses called")

        def pipeline_callback(op, error):
            if error:
                # TODO we need error semantics on the client
                exit(1)
            if callback:
                callback()

        self._pipeline.run_op(
            pipeline_ops_base.DisableFeatureOperation(feature_name=None, callback=pipeline_callback)
        )
