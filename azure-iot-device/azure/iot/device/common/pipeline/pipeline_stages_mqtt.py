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

# Maximum amount of time we wait for ConnectOperation to complete
# TODO: This whole logic of timeout should probably be handled in the TimeoutStage
WATCHDOG_INTERVAL = 60


class MQTTTransportStage(PipelineStage):
    """
    PipelineStage object which is responsible for interfacing with the MQTT protocol wrapper object.
    This stage handles all MQTT operations and any other operations (such as ConnectOperation) which
    is not in the MQTT group of operations, but can only be run at the protocol level.
    """

    def __init__(self):
        super().__init__()

        # The transport will be instantiated upon receiving the InitializePipelineOperation
        self.transport = None
        # The current in-progress op that affects connection state (Connect, Disconnect, Reauthorize)
        self._pending_connection_op = None

    @pipeline_thread.runs_on_pipeline_thread
    def _cancel_pending_connection_op(self, error=None):
        """
        Cancel any running connect, disconnect or reauthorize connection op. Since our ability to "cancel" is fairly limited,
        all this does (for now) is to fail the operation
        """

        op = self._pending_connection_op
        if op:
            # NOTE: This code path should NOT execute in normal flow. There should never already be a pending
            # connection op when another is added, due to the ConnectionLock stage.
            # If this block does execute, there is a bug in the codebase.
            if not error:
                error = pipeline_exceptions.OperationCancelled(
                    "Cancelling because new ConnectOperation or DisconnectOperation was issued"
                )
            self._cancel_connection_watchdog(op)
            self._pending_connection_op = None
            op.complete(error=error)

    @pipeline_thread.runs_on_pipeline_thread
    def _start_connection_watchdog(self, connection_op):
        """
        Start a watchdog on the connection operation. This protects against cases where transport.connect()
        succeeds but the CONNACK never arrives. This is like a timeout, but it is handled at this level
        because specific cleanup needs to take place on timeout (see below), and this cleanup doesn't
        belong anywhere else since it is very specific to this stage.
        """
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
                try:
                    this.transport.disconnect()
                except Exception:
                    # If we don't catch this, the pending connection op might not ever be cancelled.
                    # Most likely, the transport isn't actually connected, but other failures are theoretically
                    # possible. Either way, if disconnect fails, we should assume that we're disconnected.
                    logger.info(
                        "transport.disconnect raised error while disconnecting in watchdog.  Safe to ignore."
                    )
                    logger.info(traceback.format_exc())

                if this.nucleus.connected:

                    logger.info(
                        "{}({}): Pipeline is still connected on watchdog expiration.  Sending DisconnectedEvent".format(
                            this.name, op.name
                        )
                    )
                    this.send_event_up(pipeline_events_base.DisconnectedEvent())
                this._cancel_pending_connection_op(
                    error=pipeline_exceptions.OperationTimeout(
                        "Transport timeout on connection operation"
                    )
                )
            else:
                logger.debug("Connection watchdog expired, but pending op is not the same op")

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

            # Create the Transport object, set it's handlers
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

            # There can only be one pending connection operation (Connect, Disconnect)
            # at a time. The existing one must be completed or canceled before a new one is set.

            # Currently, this means that if, say, a connect operation is the pending op and is executed
            # but another connection op is begins by the time the CONNACK is received, the original
            # operation will be cancelled, but the CONNACK for it will still be received, and complete the
            # NEW operation. This is not desirable, but it is how things currently work.

            # We are however, checking the type, so the CONNACK from a cancelled Connect, cannot successfully
            # complete a Disconnect operation.

            # Note that a ReauthorizeConnectionOperation will never be pending because it will
            # instead spawn separate Connect and Disconnect operations.
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

            self._cancel_pending_connection_op()
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

            self._cancel_pending_connection_op()
            self._pending_connection_op = op
            # We don't need a watchdog on disconnect because there's no callback to wait for
            # and we respond to a watchdog timeout by calling disconnect, which is what we're
            # already doing.

            try:
                # The connect after the disconnect will be triggered upon completion of the
                # disconnect in the on_disconnected handler
                self.transport.disconnect(clear_inflight=op.hard)
            except Exception as e:
                logger.info("transport.disconnect raised error while disconnecting")
                logger.info(traceback.format_exc())
                self._pending_connection_op = None
                op.complete(error=e)

        elif isinstance(op, pipeline_ops_base.ReauthorizeConnectionOperation):
            logger.debug(
                "{}({}): reauthorizing. Will issue disconnect and then a connect".format(
                    self.name, op.name
                )
            )
            self_weakref = weakref.ref(self)
            reauth_op = op  # rename for clarity

            def on_disconnect_complete(op, error):
                this = self_weakref()
                if error:
                    # Failing a disconnect should still get us disconnected, so can proceed anyway
                    logger.debug(
                        "Disconnect failed during reauthorization, continuing with connect"
                    )
                connect_op = reauth_op.spawn_worker_op(pipeline_ops_base.ConnectOperation)

                # NOTE: this relies on the fact that before the disconnect is completed it is
                # unset as the pending connection op. Otherwise there would be issues here.
                this.run_op(connect_op)

            disconnect_op = pipeline_ops_base.DisconnectOperation(callback=on_disconnect_complete)
            disconnect_op.hard = False

            self.run_op(disconnect_op)

        elif isinstance(op, pipeline_ops_mqtt.MQTTPublishOperation):
            logger.debug("{}({}): publishing on {}".format(self.name, op.name, op.topic))

            @pipeline_thread.invoke_on_pipeline_thread_nowait
            def on_complete(cancelled=False):
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
                self.transport.publish(topic=op.topic, payload=op.payload, callback=on_complete)
            except Exception as e:
                op.complete(error=e)

        elif isinstance(op, pipeline_ops_mqtt.MQTTSubscribeOperation):
            logger.debug("{}({}): subscribing to {}".format(self.name, op.name, op.topic))

            @pipeline_thread.invoke_on_pipeline_thread_nowait
            def on_complete(cancelled=False):
                if cancelled:
                    op.complete(
                        error=pipeline_exceptions.OperationCancelled(
                            "Operation cancelled before SUBACK received"
                        )
                    )
                else:
                    logger.debug(
                        "{}({}): SUBACK received. completing op.".format(self.name, op.name)
                    )
                    op.complete()

            try:
                self.transport.subscribe(topic=op.topic, callback=on_complete)
            except Exception as e:
                op.complete(error=e)

        elif isinstance(op, pipeline_ops_mqtt.MQTTUnsubscribeOperation):
            logger.debug("{}({}): unsubscribing from {}".format(self.name, op.name, op.topic))

            @pipeline_thread.invoke_on_pipeline_thread_nowait
            def on_complete(cancelled=False):
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
                self.transport.unsubscribe(topic=op.topic, callback=on_complete)
            except Exception as e:
                op.complete(error=e)

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
            logger.debug("{}: Connection failure was unexpected".format(self.name))
            handle_exceptions.swallow_unraised_exception(
                cause,
                log_msg="Unexpected connection failure (no pending operation). Safe to ignore.",
                log_lvl="info",
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

        # Send an event to tell other pipeline stages that we're disconnected. Do this before
        # we do anything else (in case upper stages have any "are we connected" logic.)
        # NOTE: Other stages rely on the fact that this occurs before any op that may be in
        # progress is completed. Be careful with changing the order things occur here.
        self.send_event_up(pipeline_events_base.DisconnectedEvent())

        if self._pending_connection_op:

            op = self._pending_connection_op

            if isinstance(op, pipeline_ops_base.DisconnectOperation):
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
                op.complete()

            else:
                logger.debug(
                    "{}: Unexpected disconnect - completing pending {} operation".format(
                        self.name, op.name
                    )
                )
                # Cancel any potential connection watchdog, and clear the pending op
                self._cancel_connection_watchdog(op)
                self._pending_connection_op = None
                # Complete
                if cause:
                    op.complete(error=cause)
                else:
                    op.complete(
                        error=transport_exceptions.ConnectionDroppedError("transport disconnected")
                    )
        else:
            logger.info("{}: Unexpected disconnect (no pending connection op)".format(self.name))

            # If there is no connection retry, cancel any transport operations waiting on response
            # so that they do not get stuck there.
            if not self.nucleus.pipeline_configuration.connection_retry:
                logger.debug(
                    "{}: Connection Retry disabled - cancelling in-flight operations".format(
                        self.name
                    )
                )
                # TODO: Remove private access to the op manager (this layer shouldn't know about it)
                # This is a stopgap. I didn't want to invest too much infrastructure into a cancel flow
                # given that future development of individual operation cancels might affect the
                # approach to cancelling inflight ops waiting in the transport.
                self.transport._op_manager.cancel_all_operations()

            # Regardless of cause, it is now a ConnectionDroppedError. Log it and swallow it.
            # Higher layers will see that we're disconnected and may reconnect as necessary.
            e = transport_exceptions.ConnectionDroppedError("Unexpected disconnection")
            e.__cause__ = cause
            self.report_background_exception(e)
