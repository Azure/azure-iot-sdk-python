# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging
import six
import traceback
from . import (
    pipeline_ops_base,
    PipelineStage,
    pipeline_ops_mqtt,
    pipeline_events_mqtt,
    pipeline_thread,
    pipeline_exceptions,
    pipeline_events_base,
)
from azure.iot.device.common.mqtt_transport import MQTTTransport
from azure.iot.device.common import handle_exceptions, transport_exceptions
from azure.iot.device.common.callable_weak_method import CallableWeakMethod

logger = logging.getLogger(__name__)


class MQTTTransportStage(PipelineStage):
    """
    PipelineStage object which is responsible for interfacing with the MQTT protocol wrapper object.
    This stage handles all MQTT operations and any other operations (such as ConnectOperation) which
    is not in the MQTT group of operations, but can only be run at the protocol level.
    """

    def __init__(self):
        super(MQTTTransportStage, self).__init__()

        # The sas_token will be set when Connetion Args are received
        self.sas_token = None

        # The transport will be instantiated when Connection Args are received
        self.transport = None

        self._pending_connection_op = None

    @pipeline_thread.runs_on_pipeline_thread
    def _cancel_pending_connection_op(self):
        """
        Cancel any running connect, disconnect or reauthorize_connection op. Since our ability to "cancel" is fairly limited,
        all this does (for now) is to fail the operation
        """

        op = self._pending_connection_op
        if op:
            # NOTE: This code path should NOT execute in normal flow. There should never already be a pending
            # connection op when another is added, due to the SerializeConnectOps stage.
            # If this block does execute, there is a bug in the codebase.
            error = pipeline_exceptions.OperationCancelled(
                "Cancelling because new ConnectOperation, DisconnectOperation, or ReauthorizeConnectionOperation was issued"
            )  # TODO: should this actually somehow cancel the operation?
            op.complete(error=error)
            self._pending_connection_op = None

    @pipeline_thread.runs_on_pipeline_thread
    def _run_op(self, op):
        if isinstance(op, pipeline_ops_mqtt.SetMQTTConnectionArgsOperation):
            # pipeline_ops_mqtt.SetMQTTConnectionArgsOperation is where we create our MQTTTransport object and set
            # all of its properties.
            logger.debug("{}({}): got connection args".format(self.name, op.name))
            self.sas_token = op.sas_token
            self.transport = MQTTTransport(
                client_id=op.client_id,
                hostname=op.hostname,
                username=op.username,
                server_verification_cert=op.server_verification_cert,
                x509_cert=op.client_cert,
                websockets=self.pipeline_root.pipeline_configuration.websockets,
                cipher=self.pipeline_root.pipeline_configuration.cipher,
                proxy_options=self.pipeline_root.pipeline_configuration.proxy_options,
            )
            self.transport.on_mqtt_connected_handler = CallableWeakMethod(
                self, "_on_mqtt_connected"
            )
            self.transport.on_mqtt_connection_failure_handler = CallableWeakMethod(
                self, "_on_mqtt_connection_failure"
            )
            self.transport.on_mqtt_disconnected_handler = CallableWeakMethod(
                self, "_on_mqtt_disconnected"
            )
            self.transport.on_mqtt_message_received_handler = CallableWeakMethod(
                self, "_on_mqtt_message_received"
            )

            # There can only be one pending connection operation (Connect, ReauthorizeConnection, Disconnect)
            # at a time. The existing one must be completed or canceled before a new one is set.

            # Currently, this means that if, say, a connect operation is the pending op and is executed
            # but another connection op is begins by the time the CONNACK is received, the original
            # operation will be cancelled, but the CONNACK for it will still be received, and complete the
            # NEW operation. This is not desirable, but it is how things currently work.

            # We are however, checking the type, so the CONNACK from a cancelled Connect, cannot successfully
            # complete a Disconnect operation.
            self._pending_connection_op = None

            op.complete()

        elif isinstance(op, pipeline_ops_base.UpdateSasTokenOperation):
            logger.debug("{}({}): saving sas token and completing".format(self.name, op.name))
            self.sas_token = op.sas_token
            op.complete()

        elif isinstance(op, pipeline_ops_base.ConnectOperation):
            logger.info("{}({}): connecting".format(self.name, op.name))

            self._cancel_pending_connection_op()
            self._pending_connection_op = op
            try:
                self.transport.connect(password=self.sas_token)
            except Exception as e:
                logger.error("transport.connect raised error")
                logger.error(traceback.format_exc())
                self._pending_connection_op = None
                op.complete(error=e)

        elif isinstance(op, pipeline_ops_base.ReauthorizeConnectionOperation):
            logger.info("{}({}): reauthorizing".format(self.name, op.name))

            # We set _active_connect_op here because reauthorizing the connection is the same as a connect for "active operation" tracking purposes.
            self._cancel_pending_connection_op()
            self._pending_connection_op = op
            try:
                self.transport.reauthorize_connection(password=self.sas_token)
            except Exception as e:
                logger.error("transport.reauthorize_connection raised error")
                logger.error(traceback.format_exc())
                self._pending_connection_op = None
                op.complete(error=e)

        elif isinstance(op, pipeline_ops_base.DisconnectOperation):
            logger.info("{}({}): disconnecting".format(self.name, op.name))

            self._cancel_pending_connection_op()
            self._pending_connection_op = op
            try:
                self.transport.disconnect()
            except Exception as e:
                logger.error("transport.disconnect raised error")
                logger.error(traceback.format_exc())
                self._pending_connection_op = None
                op.complete(error=e)

        elif isinstance(op, pipeline_ops_mqtt.MQTTPublishOperation):
            logger.info("{}({}): publishing on {}".format(self.name, op.name, op.topic))

            @pipeline_thread.invoke_on_pipeline_thread_nowait
            def on_published():
                logger.debug("{}({}): PUBACK received. completing op.".format(self.name, op.name))
                op.complete()

            self.transport.publish(topic=op.topic, payload=op.payload, callback=on_published)

        elif isinstance(op, pipeline_ops_mqtt.MQTTSubscribeOperation):
            logger.info("{}({}): subscribing to {}".format(self.name, op.name, op.topic))

            @pipeline_thread.invoke_on_pipeline_thread_nowait
            def on_subscribed():
                logger.debug("{}({}): SUBACK received. completing op.".format(self.name, op.name))
                op.complete()

            self.transport.subscribe(topic=op.topic, callback=on_subscribed)

        elif isinstance(op, pipeline_ops_mqtt.MQTTUnsubscribeOperation):
            logger.info("{}({}): unsubscribing from {}".format(self.name, op.name, op.topic))

            @pipeline_thread.invoke_on_pipeline_thread_nowait
            def on_unsubscribed():
                logger.debug(
                    "{}({}): UNSUBACK received.  completing op.".format(self.name, op.name)
                )
                op.complete()

            self.transport.unsubscribe(topic=op.topic, callback=on_unsubscribed)

        else:
            # This code block should not be reached in correct program flow.
            # This will raise an error when executed.
            self.send_op_down(op)

    @pipeline_thread.invoke_on_pipeline_thread_nowait
    def _on_mqtt_message_received(self, topic, payload):
        """
        Handler that gets called by the protocol library when an incoming message arrives.
        Convert that message into a pipeline event and pass it up for someone to handle.
        """
        self.send_event_up(
            pipeline_events_mqtt.IncomingMQTTMessageEvent(topic=topic, payload=payload)
        )

    @pipeline_thread.invoke_on_pipeline_thread_nowait
    def _on_mqtt_connected(self):
        """
        Handler that gets called by the transport when it connects.
        """
        logger.info("_on_mqtt_connected called")
        # Send an event to tell other pipeline stages that we're connected. Do this before
        # we do anything else (in case upper stages have any "are we connected" logic.
        self.send_event_up(pipeline_events_base.ConnectedEvent())

        if isinstance(
            self._pending_connection_op, pipeline_ops_base.ConnectOperation
        ) or isinstance(
            self._pending_connection_op, pipeline_ops_base.ReauthorizeConnectionOperation
        ):
            logger.debug("completing connect op")
            op = self._pending_connection_op
            self._pending_connection_op = None
            op.complete()
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

        logger.info("{}: _on_mqtt_connection_failure called: {}".format(self.name, cause))

        if isinstance(
            self._pending_connection_op, pipeline_ops_base.ConnectOperation
        ) or isinstance(
            self._pending_connection_op, pipeline_ops_base.ReauthorizeConnectionOperation
        ):
            logger.debug("{}: failing connect op".format(self.name))
            op = self._pending_connection_op
            self._pending_connection_op = None
            op.complete(error=cause)
        else:
            logger.warning("{}: Connection failure was unexpected".format(self.name))
            handle_exceptions.swallow_unraised_exception(
                cause, log_msg="Unexpected connection failure.  Safe to ignore.", log_lvl="info"
            )

    @pipeline_thread.invoke_on_pipeline_thread_nowait
    def _on_mqtt_disconnected(self, cause=None):
        """
        Handler that gets called by the transport when the transport disconnects.

        :param Exception cause: The Exception that caused the disconnection, if any (optional)
        """
        if cause:
            logger.info("{}: _on_mqtt_disconnect called: {}".format(self.name, cause))
        else:
            logger.info("{}: _on_mqtt_disconnect called".format(self.name))

        # Send an event to tell other pipeilne stages that we're disconnected. Do this before
        # we do anything else (in case upper stages have any "are we connected" logic.)
        self.send_event_up(pipeline_events_base.DisconnectedEvent())

        if self._pending_connection_op:
            # on_mqtt_disconnected will cause any pending connect op to complete.  This is how Paho
            # behaves when there is a connection error, and it also makes sense that on_mqtt_disconnected
            # would cause a pending connection op to fail.
            logger.debug(
                "{}: completing pending {} op".format(self.name, self._pending_connection_op.name)
            )
            op = self._pending_connection_op
            self._pending_connection_op = None

            if isinstance(op, pipeline_ops_base.DisconnectOperation):
                # Swallow any errors if we intended to disconnect - even if something went wrong, we
                # got to the state we wanted to be in!
                if cause:
                    handle_exceptions.swallow_unraised_exception(
                        cause,
                        log_msg="Unexpected disconnect with error while disconnecting - swallowing error",
                    )
                op.complete()
            else:
                if cause:
                    op.complete(error=cause)
                else:
                    op.complete(
                        error=transport_exceptions.ConnectionDroppedError("transport disconnected")
                    )
        else:
            logger.warning("{}: disconnection was unexpected".format(self.name))
            # Regardless of cause, it is now a ConnectionDroppedError.  log it and swallow it.
            # Higher layers will see that we're disconencted and reconnect as necessary.
            e = transport_exceptions.ConnectionDroppedError(cause=cause)
            handle_exceptions.swallow_unraised_exception(
                e,
                log_msg="Unexpected disconnection.  Safe to ignore since other stages will reconnect.",
                log_lvl="info",
            )
