# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging
import six
from . import (
    pipeline_ops_base,
    PipelineStage,
    pipeline_ops_mqtt,
    pipeline_events_mqtt,
    operation_flow,
    pipeline_thread,
)
from azure.iot.device.common.mqtt_transport import MQTTTransport
from azure.iot.device.common import unhandled_exceptions, errors

logger = logging.getLogger(__name__)


class MQTTTransportStage(PipelineStage):
    """
    PipelineStage object which is responsible for interfacing with the MQTT protocol wrapper object.
    This stage handles all MQTT operations and any other operations (such as ConnectOperation) which
    is not in the MQTT group of operations, but can only be run at the protocol level.
    """

    @pipeline_thread.runs_on_pipeline_thread
    def _cancel_pending_connection_op(self):
        """
        Cancel any running connect, disconnect or reconnect op. Since our ability to "cancel" is fairly limited,
        all this does (for now) is to fail the operation
        """

        op = self._pending_connection_op
        if op:
            # TODO: should this actually run a cancel call on the op?
            op.error = errors.PipelineError(
                "Cancelling because new ConnectOperation, DisconnectOperation, or ReconnectOperation was issued"
            )
            operation_flow.complete_op(stage=self, op=op)
            self._pending_connection_op = None

    @pipeline_thread.runs_on_pipeline_thread
    def _execute_op(self, op):
        if isinstance(op, pipeline_ops_mqtt.SetMQTTConnectionArgsOperation):
            # pipeline_ops_mqtt.SetMQTTConnectionArgsOperation is where we create our MQTTTransport object and set
            # all of its properties.
            logger.info("{}({}): got connection args".format(self.name, op.name))
            self.hostname = op.hostname
            self.username = op.username
            self.client_id = op.client_id
            self.ca_cert = op.ca_cert
            self.sas_token = op.sas_token
            self.client_cert = op.client_cert

            self.transport = MQTTTransport(
                client_id=self.client_id,
                hostname=self.hostname,
                username=self.username,
                ca_cert=self.ca_cert,
                x509_cert=self.client_cert,
            )
            self.transport.on_mqtt_connected_handler = self._on_mqtt_connected
            self.transport.on_mqtt_connection_failure_handler = self._on_mqtt_connection_failure
            self.transport.on_mqtt_disconnected_handler = self._on_mqtt_disconnected
            self.transport.on_mqtt_message_received_handler = self._on_mqtt_message_received

            # There can only be one pending connection operation (Connect, Reconnect, Disconnect)
            # at a time. The existing one must be completed or canceled before a new one is set.

            # Currently, this means that if, say, a connect operation is the pending op and is executed
            # but another connection op is begins by the time the CONACK is received, the original
            # operation will be cancelled, but the CONACK for it will still be received, and complete the
            # NEW operation. This is not desirable, but it is how things currently work.

            # We are however, checking the type, so the CONACK from a cancelled Connect, cannot successfully
            # complete a Disconnect operation.
            self._pending_connection_op = None

            self.pipeline_root.transport = self.transport
            operation_flow.complete_op(self, op)

        elif isinstance(op, pipeline_ops_base.UpdateSasTokenOperation):
            logger.info("{}({}): saving sas token and completing".format(self.name, op.name))
            self.sas_token = op.sas_token
            operation_flow.complete_op(self, op)

        elif isinstance(op, pipeline_ops_base.ConnectOperation):
            logger.info("{}({}): connecting".format(self.name, op.name))

            self._cancel_pending_connection_op()
            self._pending_connection_op = op
            try:
                self.transport.connect(password=self.sas_token)
            except Exception as e:
                logger.error("transport.connect raised error", exc_info=True)
                self._pending_connection_op = None
                op.error = e
                operation_flow.complete_op(self, op)

        elif isinstance(op, pipeline_ops_base.ReconnectOperation):
            logger.info("{}({}): reconnecting".format(self.name, op.name))

            # We set _active_connect_op here because a reconnect is the same as a connect for "active operation" tracking purposes.
            self._cancel_pending_connection_op()
            self._pending_connection_op = op
            try:
                self.transport.reconnect(password=self.sas_token)
            except Exception as e:
                logger.error("transport.reconnect raised error", exc_info=True)
                self._pending_connection_op = None
                op.error = e
                operation_flow.complete_op(self, op)

        elif isinstance(op, pipeline_ops_base.DisconnectOperation):
            logger.info("{}({}): disconnecting".format(self.name, op.name))

            self._cancel_pending_connection_op()
            self._pending_connection_op = op
            try:
                self.transport.disconnect()
            except Exception as e:
                logger.error("transport.disconnect raised error", exc_info=True)
                self._pending_connection_op = None
                op.error = e
                operation_flow.complete_op(self, op)

        elif isinstance(op, pipeline_ops_mqtt.MQTTPublishOperation):
            logger.info("{}({}): publishing on {}".format(self.name, op.name, op.topic))

            @pipeline_thread.invoke_on_pipeline_thread_nowait
            def on_published():
                logger.info("{}({}): PUBACK received. completing op.".format(self.name, op.name))
                operation_flow.complete_op(self, op)

            self.transport.publish(topic=op.topic, payload=op.payload, callback=on_published)

        elif isinstance(op, pipeline_ops_mqtt.MQTTSubscribeOperation):
            logger.info("{}({}): subscribing to {}".format(self.name, op.name, op.topic))

            @pipeline_thread.invoke_on_pipeline_thread_nowait
            def on_subscribed():
                logger.info("{}({}): SUBACK received. completing op.".format(self.name, op.name))
                operation_flow.complete_op(self, op)

            self.transport.subscribe(topic=op.topic, callback=on_subscribed)

        elif isinstance(op, pipeline_ops_mqtt.MQTTUnsubscribeOperation):
            logger.info("{}({}): unsubscribing from {}".format(self.name, op.name, op.topic))

            @pipeline_thread.invoke_on_pipeline_thread_nowait
            def on_unsubscribed():
                logger.info("{}({}): UNSUBACK received.  completing op.".format(self.name, op.name))
                operation_flow.complete_op(self, op)

            self.transport.unsubscribe(topic=op.topic, callback=on_unsubscribed)

        else:
            operation_flow.pass_op_to_next_stage(self, op)

    @pipeline_thread.invoke_on_pipeline_thread_nowait
    def _on_mqtt_message_received(self, topic, payload):
        """
        Handler that gets called by the protocol library when an incoming message arrives.
        Convert that message into a pipeline event and pass it up for someone to handle.
        """
        operation_flow.pass_event_to_previous_stage(
            stage=self,
            event=pipeline_events_mqtt.IncomingMQTTMessageEvent(topic=topic, payload=payload),
        )

    @pipeline_thread.invoke_on_pipeline_thread_nowait
    def _on_mqtt_connected(self):
        """
        Handler that gets called by the transport when it connects.
        """
        logger.info("_on_mqtt_connected called")
        # self.on_connected() tells other pipeline stages that we're connected.  Do this before
        # we do anything else (in case upper stages have any "are we connected" logic.
        self.on_connected()

        if isinstance(
            self._pending_connection_op, pipeline_ops_base.ConnectOperation
        ) or isinstance(self._pending_connection_op, pipeline_ops_base.ReconnectOperation):
            logger.info("completing connect op")
            op = self._pending_connection_op
            self._pending_connection_op = None
            operation_flow.complete_op(stage=self, op=op)
        else:
            # This should indicate something odd is going on.
            # If this occurs, either a connect was completed while there was no pending op,
            # OR that a connect was completed while a disconnect op was pending
            logger.warning("Connection was unexpected")

    @pipeline_thread.invoke_on_pipeline_thread_nowait
    def _on_mqtt_connection_failure(self, cause):
        """
        Handler that gets called by the transport when a connection fails.

        :param Exception cause: The Exception that caused the connection failure.
        """

        logger.error("{}: _on_mqtt_connection_failure called: {}".format(self.name, cause))

        if isinstance(
            self._pending_connection_op, pipeline_ops_base.ConnectOperation
        ) or isinstance(self._pending_connection_op, pipeline_ops_base.ReconnectOperation):
            logger.info("{}: failing connect op".format(self.name))
            op = self._pending_connection_op
            self._pending_connection_op = None
            op.error = cause
            operation_flow.complete_op(stage=self, op=op)
        else:
            logger.warning("{}: Connection failure was unexpected".format(self.name))
            unhandled_exceptions.exception_caught_in_background_thread(cause)

    @pipeline_thread.invoke_on_pipeline_thread_nowait
    def _on_mqtt_disconnected(self, cause=None):
        """
        Handler that gets called by the transport when the transport disconnects.

        :param Exception cause: The Exception that caused the disconnection, if any (optional)
        """
        logger.error("{}: _on_mqtt_disconnect called: {}".format(self.name, cause))

        # self.on_disconnected() tells other pipeilne stages that we're disconnected.  Do this before
        # we do anything else (in case upper stages have any "are we connected" logic.
        self.on_disconnected()

        if isinstance(self._pending_connection_op, pipeline_ops_base.DisconnectOperation):
            logger.info("{}: completing disconnect op".format(self.name))
            op = self._pending_connection_op
            self._pending_connection_op = None

            if cause:
                # Only create a ConnnectionDroppedError if there is a cause,
                # i.e. unexpected disconnect.
                try:
                    six.raise_from(errors.ConnectionDroppedError, cause)
                except errors.ConnectionDroppedError as e:
                    op.error = e
            operation_flow.complete_op(stage=self, op=op)
        else:
            logger.warning("{}: disconnection was unexpected".format(self.name))
            # Regardless of cause, it is now a ConnectionDroppedError
            try:
                six.raise_from(errors.ConnectionDroppedError, cause)
            except errors.ConnectionDroppedError as e:
                unhandled_exceptions.exception_caught_in_background_thread(e)
