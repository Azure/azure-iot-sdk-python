# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging
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

logger = logging.getLogger(__name__)

# Maximum time to wait for a ConnectOperation to complete.
# TODO: This whole logic of timeout should probably be handled in the TimeoutStage
CONNECTION_WATCHDOG_TIMEOUT = 60


class MQTTTransportStage(PipelineStage):
    """
    PipelineStage responsible for interfacing with MQTTTransport.

    This stage handles MQTT operations and connection lifecycle operations that must run at the
    transport level.
    """

    def __init__(self):
        super().__init__()

        # The transport will be instantiated upon receiving the InitializePipelineOperation
        self.transport = None
        # The pending ConnectOperation or DisconnectOperation, if any.
        self._pending_connection_op = None

    @pipeline_thread.runs_on_pipeline_thread
    def _fail_pending_connection_op(self, error=None):
        """Complete the pending connection operation with an error.

        If no error is supplied, the operation is superseded by a newer connection operation and
        is completed with OperationCancelled.
        """

        pending_op = self._pending_connection_op
        if pending_op:
            # NOTE: This code path should NOT execute in normal flow. There should never already be a pending
            # connection op when another is added, due to the ConnectionLock stage.
            # If this block does execute, there is a bug in the codebase.
            if error is None:
                error = pipeline_exceptions.OperationCancelled(
                    "Cancelling because new ConnectOperation or DisconnectOperation was issued"
                )
            self._cancel_connection_watchdog(pending_op)
            self._pending_connection_op = None
            pending_op.complete(error=error)

    @pipeline_thread.runs_on_pipeline_thread
    def _start_connection_watchdog(self, connection_op):
        """
        Start a watchdog on the connection operation. This protects against cases where transport.connect()
        succeeds but the CONNACK never arrives. This is like a timeout, but it is handled at this level
        because specific cleanup needs to take place on timeout (see below), and this cleanup doesn't
        belong anywhere else since it is very specific to this stage.
        """
        logger.debug("{}({}): Starting watchdog".format(self.name, connection_op.name))

        stage_weakref = weakref.ref(self)
        connection_op_weakref = weakref.ref(connection_op)

        @pipeline_thread.invoke_on_pipeline_thread
        def on_connection_watchdog_expired():
            stage = stage_weakref()
            connection_op = connection_op_weakref()
            if stage and connection_op and stage._pending_connection_op is connection_op:
                logger.info(
                    "{}({}): Connection watchdog expired. Failing operation".format(
                        stage.name, connection_op.name
                    )
                )
                try:
                    stage.transport.disconnect()
                except Exception:
                    # If we don't catch this, the pending connection op might not be completed.
                    # Most likely, the transport isn't actually connected, but other failures are theoretically
                    # possible. Either way, if disconnect fails, we should assume that we're disconnected.
                    logger.info(
                        "transport.disconnect raised error while disconnecting in watchdog.  Safe to ignore."
                    )
                    logger.info(traceback.format_exc())

                if stage.nucleus.connected:

                    logger.info(
                        "{}({}): Pipeline is still connected on watchdog expiration.  Sending DisconnectedEvent".format(
                            stage.name, connection_op.name
                        )
                    )
                    stage.send_event_up(pipeline_events_base.DisconnectedEvent())
                stage._fail_pending_connection_op(
                    error=pipeline_exceptions.OperationTimeout(
                        "Transport timeout on connection operation"
                    )
                )
            else:
                logger.debug("Connection watchdog expired, but pending op is not the same op")

        connection_op.watchdog_timer = threading.Timer(
            CONNECTION_WATCHDOG_TIMEOUT, on_connection_watchdog_expired
        )
        connection_op.watchdog_timer.daemon = True
        connection_op.watchdog_timer.start()

    @pipeline_thread.runs_on_pipeline_thread
    def _cancel_connection_watchdog(self, connection_op):
        try:
            if connection_op.watchdog_timer:
                logger.debug("{}({}): cancelling watchdog".format(self.name, connection_op.name))
                connection_op.watchdog_timer.cancel()
                connection_op.watchdog_timer = None
        except AttributeError:
            pass

    @pipeline_thread.runs_on_pipeline_thread
    def _run_op(self, op):
        if isinstance(op, pipeline_ops_base.InitializePipelineOperation):

            # If there is a gateway hostname, use that as the hostname for connection,
            # rather than the hostname itself
            if self.nucleus.pipeline_configuration.gateway_hostname:
                logger.debug(
                    "Gateway Hostname Present. Setting Hostname to: {}".format(
                        self.nucleus.pipeline_configuration.gateway_hostname
                    )
                )
                hostname = self.nucleus.pipeline_configuration.gateway_hostname
            else:
                logger.debug(
                    "Gateway Hostname not present. Setting Hostname to: {}".format(
                        self.nucleus.pipeline_configuration.hostname
                    )
                )
                hostname = self.nucleus.pipeline_configuration.hostname

            # Create the transport and set its handlers.
            logger.debug("{}({}): got connection args".format(self.name, op.name))
            self.transport = MQTTTransport(
                client_id=op.client_id,
                hostname=hostname,
                username=op.username,
                server_verification_cert=self.nucleus.pipeline_configuration.server_verification_cert,
                x509_cert=self.nucleus.pipeline_configuration.x509,
                websockets=self.nucleus.pipeline_configuration.websockets,
                cipher=self.nucleus.pipeline_configuration.cipher,
                proxy_options=self.nucleus.pipeline_configuration.proxy_options,
                keep_alive=self.nucleus.pipeline_configuration.keep_alive,
            )
            self.transport.on_mqtt_connected_handler = self._on_mqtt_connected
            self.transport.on_mqtt_connection_failure_handler = self._on_mqtt_connection_failure
            self.transport.on_mqtt_disconnected_handler = self._on_mqtt_disconnected
            self.transport.on_mqtt_message_received_handler = self._on_mqtt_message_received

            # Only one ConnectOperation or DisconnectOperation can be pending. Lifecycle callbacks
            # snapshot its identity before entering the pipeline thread, so stale queued callbacks
            # cannot affect a later operation. Reauthorization sequences worker operations and is
            # never stored here directly.
            self._pending_connection_op = None

            op.complete()

        elif isinstance(op, pipeline_ops_base.ShutdownPipelineOperation):
            try:
                self.transport.shutdown()
            except Exception as e:
                logger.info("transport.shutdown raised error")
                logger.info(traceback.format_exc())
                op.complete(error=e)
            else:
                op.complete()

        elif isinstance(op, pipeline_ops_base.ConnectOperation):
            logger.debug("{}({}): connecting".format(self.name, op.name))

            self._fail_pending_connection_op()
            self._pending_connection_op = op
            self._start_connection_watchdog(op)
            # Use SasToken as password if present. If not present (e.g. using X509),
            # then no password is required because auth is handled via other means.
            if self.nucleus.pipeline_configuration.sastoken:
                password = str(self.nucleus.pipeline_configuration.sastoken)
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

        elif isinstance(op, pipeline_ops_base.DisconnectOperation):
            logger.debug("{}({}): disconnecting".format(self.name, op.name))

            self._fail_pending_connection_op()
            self._pending_connection_op = op
            # No watchdog is needed because MQTTTransport.disconnect() blocks until its network
            # loop stops; this stage does not wait for the queued disconnected callback.

            try:
                # MQTTTransport.disconnect() blocks until the network loop has stopped.
                self.transport.disconnect(clear_inflight=op.hard)
            except Exception as e:
                logger.info("transport.disconnect raised error while disconnecting")
                logger.info(traceback.format_exc())
                self._pending_connection_op = None
                op.complete(error=e)
            else:
                self._handle_disconnected_state()

        elif isinstance(op, pipeline_ops_base.ReauthorizeConnectionOperation):
            logger.debug(
                "{}({}): reauthorizing. Will issue disconnect and then a connect".format(
                    self.name, op.name
                )
            )
            stage_weakref = weakref.ref(self)
            reauthorization_op = op

            def on_reauthorization_disconnect_complete(op, error):
                stage = stage_weakref()
                if error:
                    # Failing a disconnect should still get us disconnected, so can proceed anyway
                    logger.debug(
                        "Disconnect failed during reauthorization, continuing with connect"
                    )
                connect_op = reauthorization_op.spawn_worker_op(pipeline_ops_base.ConnectOperation)

                # NOTE: this relies on the fact that before the disconnect is completed it is
                # unset as the pending connection op. Otherwise there would be issues here.
                stage.run_op(connect_op)

            disconnect_op = pipeline_ops_base.DisconnectOperation(
                callback=on_reauthorization_disconnect_complete
            )
            disconnect_op.hard = False

            self.run_op(disconnect_op)

        elif isinstance(op, pipeline_ops_mqtt.MQTTPublishOperation):
            logger.debug("{}({}): publishing on {}".format(self.name, op.name, op.topic))

            @pipeline_thread.invoke_on_pipeline_thread_nowait
            def on_publish_complete(cancelled=False):
                if cancelled:
                    op.complete(
                        error=pipeline_exceptions.OperationCancelled(
                            "Operation cancelled before PUBACK received"
                        )
                    )
                else:
                    logger.debug(
                        "{}({}): PUBACK received. completing op.".format(self.name, op.name)
                    )
                    op.complete()

            try:
                self.transport.publish(
                    topic=op.topic, payload=op.payload, callback=on_publish_complete
                )
            except Exception as e:
                op.complete(error=e)

        elif isinstance(op, pipeline_ops_mqtt.MQTTSubscribeOperation):
            logger.debug("{}({}): subscribing to {}".format(self.name, op.name, op.topic))

            @pipeline_thread.invoke_on_pipeline_thread_nowait
            def on_subscribe_complete(cancelled=False, error=None):
                if cancelled:
                    op.complete(
                        error=pipeline_exceptions.OperationCancelled(
                            "Operation cancelled before SUBACK received"
                        )
                    )
                elif error is not None:
                    op.complete(error=error)
                else:
                    logger.debug(
                        "{}({}): SUBACK received. completing op.".format(self.name, op.name)
                    )
                    op.complete()

            try:
                self.transport.subscribe(topic=op.topic, callback=on_subscribe_complete)
            except Exception as e:
                op.complete(error=e)

        elif isinstance(op, pipeline_ops_mqtt.MQTTUnsubscribeOperation):
            logger.debug("{}({}): unsubscribing from {}".format(self.name, op.name, op.topic))

            @pipeline_thread.invoke_on_pipeline_thread_nowait
            def on_unsubscribe_complete(cancelled=False):
                if cancelled:
                    op.complete(
                        error=pipeline_exceptions.OperationCancelled(
                            "Operation cancelled before UNSUBACK received"
                        )
                    )
                else:
                    logger.debug(
                        "{}({}): UNSUBACK received.  completing op.".format(self.name, op.name)
                    )
                    op.complete()

            try:
                self.transport.unsubscribe(topic=op.topic, callback=on_unsubscribe_complete)
            except Exception as e:
                op.complete(error=e)

        else:
            # This code block should not be reached in correct program flow.
            # This will raise an error when executed.
            self.send_op_down(op)

    @pipeline_thread.invoke_on_pipeline_thread_nowait
    def _on_mqtt_message_received(self, topic, payload):
        """
        Handler that gets called by the transport when an incoming message arrives.
        Convert that message into a pipeline event and pass it up for someone to handle.
        """
        logger.debug("{}: message received on topic {}".format(self.name, topic))
        self.send_event_up(
            pipeline_events_mqtt.IncomingMQTTMessageEvent(topic=topic, payload=payload)
        )

    # Lifecycle callbacks must snapshot the pending operation before queueing work on the pipeline
    # thread; otherwise, a delayed callback could act on a newer operation. Message callbacks can
    # be queued directly because their topic and payload are already captured in the callback args.
    def _on_mqtt_connected(self):
        """Snapshot the pending operation and queue connected-callback processing."""
        connection_op_snapshot = self._pending_connection_op
        self._process_mqtt_connected_callback(connection_op_snapshot)

    @pipeline_thread.invoke_on_pipeline_thread_nowait
    def _process_mqtt_connected_callback(self, connection_op_snapshot):
        """Process a connected callback on the pipeline thread."""
        if connection_op_snapshot is not self._pending_connection_op:
            logger.info(
                "{}: Ignoring connected callback for a connection operation that is no longer pending".format(
                    self.name
                )
            )
            return

        logger.info("{}: MQTT connected".format(self.name))
        # Send an event to tell other pipeline stages that we're connected. Do this before
        # we do anything else (in case upper stages have any "are we connected" logic.
        self.send_event_up(pipeline_events_base.ConnectedEvent())

        if isinstance(self._pending_connection_op, pipeline_ops_base.ConnectOperation):
            logger.debug("{}: completing connect op".format(self.name))
            op = self._pending_connection_op
            self._cancel_connection_watchdog(op)
            self._pending_connection_op = None
            op.complete()
        else:
            # This should indicate something odd is going on.
            # If this occurs, either a connect was completed while there was no pending op,
            # OR that a connect was completed while a disconnect op was pending
            logger.info(
                "{}: Connection was unexpected (no connection op pending)".format(self.name)
            )

    # Lifecycle callbacks must snapshot the pending operation before queueing work on the pipeline
    # thread; otherwise, a delayed callback could act on a newer operation. Message callbacks can
    # be queued directly because their topic and payload are already captured in the callback args.
    def _on_mqtt_connection_failure(self, cause):
        """Snapshot the pending operation and queue failure-callback processing."""
        connection_op_snapshot = self._pending_connection_op
        self._process_mqtt_connection_failure_callback(connection_op_snapshot, cause)

    @pipeline_thread.invoke_on_pipeline_thread_nowait
    def _process_mqtt_connection_failure_callback(self, connection_op_snapshot, cause):
        """Process a connection-failure callback on the pipeline thread.

        :param Exception cause: The Exception that caused the connection failure.
        """

        if connection_op_snapshot is not self._pending_connection_op:
            logger.info(
                "{}: Ignoring connection failure callback for a connection operation that is no longer pending".format(
                    self.name
                )
            )
            return

        logger.info("{}: MQTT connection failed: {}".format(self.name, cause))

        if isinstance(self._pending_connection_op, pipeline_ops_base.ConnectOperation):
            logger.debug("{}: failing connect op".format(self.name))
            op = self._pending_connection_op
            self._cancel_connection_watchdog(op)
            self._pending_connection_op = None
            op.complete(error=cause)
        else:
            logger.debug("{}: Connection failure was unexpected".format(self.name))
            handle_exceptions.swallow_unraised_exception(
                cause,
                log_msg="Unexpected connection failure (no pending operation). Safe to ignore.",
                log_lvl="info",
            )

    # Lifecycle callbacks must snapshot the pending operation before queueing work on the pipeline
    # thread; otherwise, a delayed callback could act on a newer operation. Message callbacks can
    # be queued directly because their topic and payload are already captured in the callback args.
    def _on_mqtt_disconnected(self, cause=None):
        """Snapshot the pending operation and queue disconnected-callback processing."""
        connection_op_snapshot = self._pending_connection_op
        self._process_mqtt_disconnected_callback(connection_op_snapshot, cause)

    @pipeline_thread.invoke_on_pipeline_thread_nowait
    def _process_mqtt_disconnected_callback(self, connection_op_snapshot, cause=None):
        """Process a disconnected callback on the pipeline thread."""
        if connection_op_snapshot is not self._pending_connection_op:
            logger.info(
                "{}: Ignoring disconnected callback for a connection operation that is no longer pending".format(
                    self.name
                )
            )
            return

        self._handle_disconnected_state(cause)

    @pipeline_thread.runs_on_pipeline_thread
    def _handle_disconnected_state(self, cause=None):
        """Handle disconnected-state effects on the pipeline thread.

        Called after either a transport callback or a successful blocking disconnect.

        :param Exception cause: The Exception that caused the disconnection, if any (optional)
        """
        if cause:
            logger.info("{}: MQTT disconnected: {}".format(self.name, cause))
        else:
            logger.info("{}: MQTT disconnected".format(self.name))

        # Send an event to tell other pipeline stages that we're disconnected. Do this before
        # we do anything else (in case upper stages have any "are we connected" logic.)
        # NOTE: Other stages rely on the fact that this occurs before any op that may be in
        # progress is completed. Be careful with changing the order things occur here.
        self.send_event_up(pipeline_events_base.DisconnectedEvent())

        if self._pending_connection_op:

            connection_op = self._pending_connection_op

            if isinstance(connection_op, pipeline_ops_base.DisconnectOperation):
                logger.debug(
                    "{}: Expected disconnect - completing pending disconnect op".format(self.name)
                )
                # Swallow any errors if we intended to disconnect - even if something went wrong, we
                # got to the state we wanted to be in!
                if cause:
                    handle_exceptions.swallow_unraised_exception(
                        cause,
                        log_msg="Unexpected error while disconnecting - swallowing error",
                    )
                # Disconnect complete, no longer pending
                self._pending_connection_op = None
                connection_op.complete()

            else:
                logger.debug(
                    "{}: Unexpected disconnect - completing pending {} operation".format(
                        self.name, connection_op.name
                    )
                )
                # Cancel any potential connection watchdog, and clear the pending op
                self._cancel_connection_watchdog(connection_op)
                self._pending_connection_op = None
                # Complete
                if cause:
                    connection_op.complete(error=cause)
                else:
                    connection_op.complete(
                        error=transport_exceptions.ConnectionDroppedError("transport disconnected")
                    )
        else:
            logger.info("{}: Unexpected disconnect (no pending connection op)".format(self.name))

            # If there is no connection retry, complete tracked MQTT operations as cancelled so
            # they do not remain pending indefinitely.
            if not self.nucleus.pipeline_configuration.connection_retry:
                logger.debug(
                    "{}: Connection Retry disabled - completing tracked MQTT operations as cancelled".format(
                        self.name
                    )
                )
                # TODO: Remove private access to the op manager (this layer shouldn't know about it)
                # This is a stopgap. I didn't want to invest too much infrastructure into a cancel flow
                # given that future development of individual operation cancels might affect the
                # approach to completing tracked transport operations as cancelled.
                self.transport._op_manager.complete_all_tracked_operations_as_cancelled()
            else:
                logger.debug(
                    "{}: Connection Retry enabled - preserving PUBLISH tracking and stopping SUBSCRIBE and UNSUBSCRIBE tracking".format(
                        self.name
                    )
                )
                self.transport._op_manager.stop_tracking_non_publish_operations()

            # Regardless of cause, it is now a ConnectionDroppedError. Log it and swallow it.
            # Higher layers will see that we're disconnected and may reconnect as necessary.
            e = transport_exceptions.ConnectionDroppedError("Unexpected disconnection")
            e.__cause__ = cause
            self.report_background_exception(e)
