# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging
import six
import traceback
import threading
import weakref
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

# Maximum amount of time we wait for ConnectOperation to complete
WATCHDOG_INTERVAL = 10


class MQTTTransportStage(PipelineStage):
    """
    PipelineStage object which is responsible for interfacing with the MQTT protocol wrapper object.
    This stage handles all MQTT operations and any other operations (such as ConnectOperation) which
    is not in the MQTT group of operations, but can only be run at the protocol level.
    """

    def __init__(self):
        super(MQTTTransportStage, self).__init__()

        # The transport will be instantiated when Connection Args are received
        self.transport = None

        self._pending_connection_op = None

    @pipeline_thread.runs_on_pipeline_thread
    def _cancel_pending_connection_op(self, error=None):
        """
        Cancel any running connect, disconnect or reauthorize_connection op. Since our ability to "cancel" is fairly limited,
        all this does (for now) is to fail the operation
        """

        op = self._pending_connection_op
        if op:
            # NOTE: This code path should NOT execute in normal flow. There should never already be a pending
            # connection op when another is added, due to the SerializeConnectOps stage.
            # If this block does execute, there is a bug in the codebase.
            if not error:
                error = pipeline_exceptions.OperationCancelled(
                    "Cancelling because new ConnectOperation, DisconnectOperation, or ReauthorizeConnectionOperation was issued"
                )
            self._cancel_connection_watchdog(op)
            op.complete(error=error)
            self._pending_connection_op = None

    @pipeline_thread.runs_on_pipeline_thread
    def _start_connection_watchdog(self, connection_op):
        logger.debug("{}({}): Starting watchdog".format(self.name, connection_op.name))

        self_weakref = weakref.ref(self)
        op_weakref = weakref.ref(connection_op)

        @pipeline_thread.invoke_on_pipeline_thread
        def watchdog_function():
            this = self_weakref()
            op = op_weakref()
            if this and op and this._pending_connection_op is op:
                logger.info(
                    "{}({}): Connection watchdog expired.  Cancelling op".format(this.name, op.name)
                )
                this.transport.disconnect()
                if this.pipeline_root.connected:
                    logger.info(
                        "{}({}): Pipeline is still connected on watchdog expiration.  Sending DisconnectedEvent".format(
                            this.name, op.name
                        )
                    )
                    this.send_event_up(pipeline_events_base.DisconnectedEvent())
                this._cancel_pending_connection_op(
                    error=pipeline_exceptions.OperationCancelled(
                        "Transport timeout on connection operation"
                    )
                )

        connection_op.watchdog_timer = threading.Timer(WATCHDOG_INTERVAL, watchdog_function)
        connection_op.watchdog_timer.daemon = True
        connection_op.watchdog_timer.start()

    @pipeline_thread.runs_on_pipeline_thread
    def _cancel_connection_watchdog(self, op):
        try:
            if op.watchdog_timer:
                logger.debug("{}({}): cancelling watchdog".format(self.name, op.name))
                op.watchdog_timer.cancel()
                op.watchdog_timer = None
        except AttributeError:
            pass

    @pipeline_thread.runs_on_pipeline_thread
    def _run_op(self, op):
        if isinstance(op, pipeline_ops_base.InitializePipelineOperation):

            # If there is a gateway hostname, use that as the hostname for connection,
            # rather than the hostname itself
            if self.pipeline_root.pipeline_configuration.gateway_hostname:
                logger.debug(
                    "Gateway Hostname Present. Setting Hostname to: {}".format(
                        self.pipeline_root.pipeline_configuration.gateway_hostname
                    )
                )
                hostname = self.pipeline_root.pipeline_configuration.gateway_hostname
            else:
                logger.debug(
                    "Gateway Hostname not present. Setting Hostname to: {}".format(
                        self.pipeline_root.pipeline_configuration.hostname
                    )
                )
                hostname = self.pipeline_root.pipeline_configuration.hostname

            # Create the Transport object, set it's handlers
            logger.debug("{}({}): got connection args".format(self.name, op.name))
            self.transport = MQTTTransport(
                client_id=op.client_id,
                hostname=hostname,
                username=op.username,
                server_verification_cert=self.pipeline_root.pipeline_configuration.server_verification_cert,
                x509_cert=self.pipeline_root.pipeline_configuration.x509,
                websockets=self.pipeline_root.pipeline_configuration.websockets,
                cipher=self.pipeline_root.pipeline_configuration.cipher,
                proxy_options=self.pipeline_root.pipeline_configuration.proxy_options,
                keep_alive=self.pipeline_root.pipeline_configuration.keep_alive,
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

        elif isinstance(op, pipeline_ops_base.ConnectOperation):
            logger.debug("{}({}): connecting".format(self.name, op.name))

            self._cancel_pending_connection_op()
            self._pending_connection_op = op
            self._start_connection_watchdog(op)
            # Use SasToken as password if present. If not present (e.g. using X509),
            # then no password is required because auth is handled via other means.
            if self.pipeline_root.pipeline_configuration.sastoken:
                password = str(self.pipeline_root.pipeline_configuration.sastoken)
            else:
                password = None
            try:
                self.transport.connect(password=password)
            except Exception as e:
                logger.info("transport.connect raised error")
                logger.info(traceback.format_exc())
                self._cancel_connection_watchdog(op)
                self._pending_connection_op = None
                op.complete(error=e)

        elif isinstance(op, pipeline_ops_base.DisconnectOperation) or isinstance(
            op, pipeline_ops_base.ReauthorizeConnectionOperation
        ):
            logger.debug("{}({}): disconnecting or reauthorizing".format(self.name, op.name))

            self._cancel_pending_connection_op()
            self._pending_connection_op = op
            # We don't need a watchdog on disconnect because there's no callback to wait for
            # and we respond to a watchdog timeout by calling disconnect, which is what we're
            # already doing.

            try:
                self.transport.disconnect()
            except Exception as e:
                logger.info("transport.disconnect raised error")
                logger.info(traceback.format_exc())
                self._pending_connection_op = None
                op.complete(error=e)

        elif isinstance(op, pipeline_ops_mqtt.MQTTPublishOperation):
            logger.debug("{}({}): publishing on {}".format(self.name, op.name, op.topic))

            @pipeline_thread.invoke_on_pipeline_thread_nowait
            def on_published():
                logger.debug("{}({}): PUBACK received. completing op.".format(self.name, op.name))
                op.complete()

            try:
                self.transport.publish(topic=op.topic, payload=op.payload, callback=on_published)
            except transport_exceptions.ConnectionDroppedError:
                self.send_event_up(pipeline_events_base.DisconnectedEvent())
                raise

        elif isinstance(op, pipeline_ops_mqtt.MQTTSubscribeOperation):
            logger.debug("{}({}): subscribing to {}".format(self.name, op.name, op.topic))

            @pipeline_thread.invoke_on_pipeline_thread_nowait
            def on_subscribed():
                logger.debug("{}({}): SUBACK received. completing op.".format(self.name, op.name))
                op.complete()

            try:
                self.transport.subscribe(topic=op.topic, callback=on_subscribed)
            except transport_exceptions.ConnectionDroppedError:
                self.send_event_up(pipeline_events_base.DisconnectedEvent())
                raise

        elif isinstance(op, pipeline_ops_mqtt.MQTTUnsubscribeOperation):
            logger.debug("{}({}): unsubscribing from {}".format(self.name, op.name, op.topic))

            @pipeline_thread.invoke_on_pipeline_thread_nowait
            def on_unsubscribed():
                logger.debug(
                    "{}({}): UNSUBACK received.  completing op.".format(self.name, op.name)
                )
                op.complete()

            try:
                self.transport.unsubscribe(topic=op.topic, callback=on_unsubscribed)
            except transport_exceptions.ConnectionDroppedError:
                self.send_event_up(pipeline_events_base.DisconnectedEvent())
                raise

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
        logger.debug("{}: message received on topic {}".format(self.name, topic))
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

        if isinstance(self._pending_connection_op, pipeline_ops_base.ConnectOperation):
            logger.debug("completing connect op")
            op = self._pending_connection_op
            self._cancel_connection_watchdog(op)
            self._pending_connection_op = None
            op.complete()
        else:
            # This should indicate something odd is going on.
            # If this occurs, either a connect was completed while there was no pending op,
            # OR that a connect was completed while a disconnect op was pending
            logger.info("Connection was unexpected")

    @pipeline_thread.invoke_on_pipeline_thread_nowait
    def _on_mqtt_connection_failure(self, cause):
        """
        Handler that gets called by the transport when a connection fails.

        :param Exception cause: The Exception that caused the connection failure.
        """

        logger.info("{}: _on_mqtt_connection_failure called: {}".format(self.name, cause))

        if isinstance(self._pending_connection_op, pipeline_ops_base.ConnectOperation):
            logger.debug("{}: failing connect op".format(self.name))
            op = self._pending_connection_op
            self._cancel_connection_watchdog(op)
            self._pending_connection_op = None
            op.complete(error=cause)
        else:
            logger.info("{}: Connection failure was unexpected".format(self.name))
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
            self._cancel_connection_watchdog(op)
            self._pending_connection_op = None

            if isinstance(op, pipeline_ops_base.DisconnectOperation) or isinstance(
                op, pipeline_ops_base.ReauthorizeConnectionOperation
            ):
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
            logger.info("{}: disconnection was unexpected".format(self.name))
            # Regardless of cause, it is now a ConnectionDroppedError.  log it and swallow it.
            # Higher layers will see that we're disconencted and reconnect as necessary.
            e = transport_exceptions.ConnectionDroppedError(cause=cause)
            handle_exceptions.swallow_unraised_exception(
                e,
                log_msg="Unexpected disconnection.  Safe to ignore since other stages will reconnect.",
                log_lvl="info",
            )
