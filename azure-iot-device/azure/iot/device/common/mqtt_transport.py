# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import paho.mqtt.client as mqtt
import logging
import ssl
import threading
import traceback
import weakref
import socket
from enum import Enum
from . import transport_exceptions as exceptions
import socks

logger = logging.getLogger(__name__)

CONNECTION_TIMEOUT = 60

# This transport speaks MQTT 3.1.1, but Paho callback API v2 represents callback results
# with MQTT 5 ReasonCode and Properties types. For MQTT 3.1.1, Paho synthesizes these values:
# - CONNACK and SUBACK ReasonCode objects from their MQTT 3.1.1 Return Codes
# - a disconnect ReasonCode from Paho's own MQTTErrorCode
# - a successful ReasonCode for publish completion
# - empty Properties objects, and an empty reason_codes list for UNSUBACK
# These are Paho API values, not fields received in MQTT 3.1.1 Control Packets.
# Maps Paho's synthesized CONNACK reason names to SDK exception types.
paho_connack_reason_name_to_error_type = {
    "Unsupported protocol version": exceptions.ProtocolClientError,
    "Client identifier not valid": exceptions.ProtocolClientError,
    "Server unavailable": exceptions.ConnectionFailedError,
    "Bad user name or password": exceptions.UnauthorizedError,
    "Not authorized": exceptions.UnauthorizedError,
}

# Maps Paho's synthesized disconnect reason names to SDK exception types. MQTT 3.1.1 has no
# server-to-client DISCONNECT packet or disconnect reason field.
paho_disconnect_reason_name_to_error_type = {
    "Unspecified error": exceptions.ConnectionDroppedError,
    "Keep alive timeout": exceptions.ConnectionDroppedError,
}

# Maps Paho library error codes to SDK exception types.
paho_error_code_to_error_type = {
    mqtt.MQTT_ERR_PROTOCOL: exceptions.ProtocolClientError,
    mqtt.MQTT_ERR_INVAL: exceptions.ProtocolClientError,
    mqtt.MQTT_ERR_NO_CONN: exceptions.NoConnectionError,
    mqtt.MQTT_ERR_CONN_REFUSED: exceptions.ConnectionFailedError,
    mqtt.MQTT_ERR_NOT_FOUND: exceptions.ConnectionFailedError,
    mqtt.MQTT_ERR_CONN_LOST: exceptions.ConnectionDroppedError,
    mqtt.MQTT_ERR_TLS: exceptions.UnauthorizedError,
    mqtt.MQTT_ERR_PAYLOAD_SIZE: exceptions.ProtocolClientError,
    mqtt.MQTT_ERR_NOT_SUPPORTED: exceptions.ProtocolClientError,
    mqtt.MQTT_ERR_AUTH: exceptions.UnauthorizedError,
    mqtt.MQTT_ERR_ACL_DENIED: exceptions.UnauthorizedError,
    mqtt.MQTT_ERR_UNKNOWN: exceptions.ProtocolClientError,
    mqtt.MQTT_ERR_ERRNO: exceptions.ProtocolClientError,
    mqtt.MQTT_ERR_QUEUE_SIZE: exceptions.ProtocolClientError,
    mqtt.MQTT_ERR_KEEPALIVE: exceptions.ConnectionDroppedError,
}


def _create_error_from_paho_connack_reason(reason_code):
    """Translate Paho's synthesized CONNACK ReasonCode into an SDK transport exception."""
    paho_reason_name = str(reason_code)
    if paho_reason_name in paho_connack_reason_name_to_error_type:
        return paho_connack_reason_name_to_error_type[paho_reason_name](paho_reason_name)
    else:
        return exceptions.ProtocolClientError("Unknown Paho CONNACK reason={}".format(reason_code))


def _create_error_from_paho_disconnect_reason(reason_code):
    """Translate Paho's synthesized disconnect ReasonCode into an SDK transport exception."""
    paho_reason_name = str(reason_code)
    if paho_reason_name in paho_disconnect_reason_name_to_error_type:
        return paho_disconnect_reason_name_to_error_type[paho_reason_name](paho_reason_name)
    else:
        return exceptions.ProtocolClientError(
            "Unknown Paho disconnect reason={}".format(reason_code)
        )


def _create_error_from_paho_error_code(error_code):
    """Translate a Paho library error code into an SDK transport exception."""
    if error_code in paho_error_code_to_error_type:
        message = mqtt.error_string(error_code)
        return paho_error_code_to_error_type[error_code](message)
    else:
        return exceptions.ProtocolClientError("Unknown Paho error code={}".format(error_code))


class ConnectionState(Enum):
    # No CONNACK or pre-completion disconnection has been processed.
    WAITING_FOR_CONNACK = "WAITING_FOR_CONNACK"
    # A successful CONNACK arrived, but connect() has not yet committed success.
    CONNACK_ACCEPTED = "CONNACK_ACCEPTED"
    # connect() consumed the successful CONNACK and may return to its caller.
    CONNECTED = "CONNECTED"
    # An explicit disconnect began after connect() completed successfully.
    DISCONNECTING = "DISCONNECTING"
    # Network connection closure has been processed.
    DISCONNECTED = "DISCONNECTED"
    # The connection attempt ended unsuccessfully; its stored error is authoritative.
    FAILED = "FAILED"


class ConnectionAttempt(object):
    def __init__(self):
        self._condition = threading.Condition()
        self._state = ConnectionState.WAITING_FOR_CONNACK
        self._error = None

    def accept_connack(self):
        with self._condition:
            if self._state is ConnectionState.WAITING_FOR_CONNACK:
                self._state = ConnectionState.CONNACK_ACCEPTED
                self._condition.notify_all()

    def fail(self, error):
        with self._condition:
            if self._state in (
                ConnectionState.WAITING_FOR_CONNACK,
                ConnectionState.CONNACK_ACCEPTED,
            ):
                self._state = ConnectionState.FAILED
                self._error = error
                self._condition.notify_all()

    def wait_for_connack(self, timeout):
        with self._condition:
            if not self._condition.wait_for(
                lambda: self._state is not ConnectionState.WAITING_FOR_CONNACK,
                timeout=timeout,
            ):
                self._state = ConnectionState.FAILED
                self._error = exceptions.ConnectionTimeoutError(
                    "Timed out waiting for MQTT CONNACK"
                )

            if self._state is ConnectionState.CONNACK_ACCEPTED:
                self._state = ConnectionState.CONNECTED
                return

            raise self._error

    def on_disconnect(self, cause):
        with self._condition:
            if self._state is ConnectionState.WAITING_FOR_CONNACK:
                self._state = ConnectionState.FAILED
                self._error = exceptions.ConnectionFailedError(
                    "Network connection closed before MQTT CONNACK"
                )
                self._condition.notify_all()
                return False
            elif self._state is ConnectionState.CONNACK_ACCEPTED:
                self._state = ConnectionState.FAILED
                self._error = cause or exceptions.ConnectionDroppedError(
                    "Network connection closed during connect"
                )
                self._condition.notify_all()
                return False
            elif self._state is ConnectionState.CONNECTED:
                self._state = ConnectionState.DISCONNECTED
                return True
            elif self._state is ConnectionState.DISCONNECTING:
                self._state = ConnectionState.DISCONNECTED
                return False
            else:
                return False

    def begin_disconnect(self):
        with self._condition:
            if self._state is ConnectionState.CONNECTED:
                self._state = ConnectionState.DISCONNECTING


class MQTTTransport(object):
    """
    A wrapper class that provides an implementation-agnostic MQTT Server interface.
    This transport uses MQTT 3.1.1.

    Calls to connect(), disconnect(), and shutdown() must be serialized by the caller;
    overlapping connection lifecycle calls are not supported. Event handlers can run concurrently
    with the calling thread. Multiple publish, subscribe, and unsubscribe operations can remain
    outstanding and complete out of order; their callback tracking is synchronized internally.

    :ivar on_mqtt_disconnected_handler: Event handler callback, called upon a disconnection.
    :type on_mqtt_disconnected_handler: Function
    :ivar on_mqtt_message_received_handler: Event handler callback, called upon receiving a message.
    :type on_mqtt_message_received_handler: Function
    """

    def __init__(
        self,
        client_id,
        hostname,
        username,
        server_verification_cert=None,
        x509_cert=None,
        websockets=False,
        cipher=None,
        proxy_options=None,
        keep_alive=None,
    ):
        """
        Constructor to instantiate an MQTT protocol wrapper.
        :param str client_id: The Client Identifier used to connect to the MQTT Server.
        :param str hostname: Hostname or IP address of the remote MQTT Server.
        :param str username: User Name for authentication with the MQTT Server.
        :param str server_verification_cert: Certificate which can be used to validate a server-side TLS connection (optional).
        :param x509_cert: Certificate which can be used to authenticate with the MQTT Server in lieu of a password (optional).
        :param bool websockets: Indicates whether or not to enable a websockets connection in the Transport.
        :param str cipher: Cipher string in OpenSSL cipher list format
        :param proxy_options: Options for sending traffic through proxy servers.
        """
        self._client_id = client_id
        self._hostname = hostname
        self._username = username
        self._mqtt_client = None
        self._server_verification_cert = server_verification_cert
        self._x509_cert = x509_cert
        self._websockets = websockets
        self._cipher = cipher
        self._proxy_options = proxy_options
        self._keep_alive = keep_alive
        self._connection_attempt = None

        self.on_mqtt_disconnected_handler = None
        self.on_mqtt_message_received_handler = None

        self._op_manager = OperationManager()

        self._mqtt_client = self._create_mqtt_client()

    def _create_mqtt_client(self):
        """
        Create the MQTT client object and assign all necessary event handler callbacks.
        """
        logger.debug("creating Paho client")

        # Instantiate the client
        if self._websockets:
            logger.info("Creating Paho client for MQTT over websockets")
            mqtt_client = mqtt.Client(
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
                client_id=self._client_id,
                clean_session=False,
                protocol=mqtt.MQTTv311,
                transport="websockets",
                reconnect_on_failure=False,
            )
            mqtt_client.ws_set_options(path="/$iothub/websocket")
        else:
            logger.info("Creating Paho client for MQTT over TCP")
            mqtt_client = mqtt.Client(
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
                client_id=self._client_id,
                clean_session=False,
                protocol=mqtt.MQTTv311,
                reconnect_on_failure=False,
            )

        if self._proxy_options:
            logger.info("Configuring Paho client proxy options")
            mqtt_client.proxy_set(
                proxy_type=self._proxy_options.proxy_type_socks,
                proxy_addr=self._proxy_options.proxy_address,
                proxy_port=self._proxy_options.proxy_port,
                proxy_username=self._proxy_options.proxy_username,
                proxy_password=self._proxy_options.proxy_password,
            )

        mqtt_client.enable_logger(logging.getLogger("paho"))

        # Configure TLS/SSL
        ssl_context = self._create_ssl_context()
        mqtt_client.tls_set_context(context=ssl_context)

        # Set event handlers.  Use weak references back into this object to prevent leaks
        self_weakref = weakref.ref(self)

        def get_transport_from_weakref_or_cleanup_client(client, callback_name):
            """Acquire a strong transport reference for the duration of a Paho callback.

            The transport can be collected before a callback running on Paho's thread resolves
            its weak reference. If it is already gone, disconnect the orphaned client and stop
            its thread; otherwise, the returned reference keeps it alive through callback handling.
            """
            this = self_weakref()
            if this is None:
                logger.info(
                    "Paho callback {} invoked after MQTTTransport was garbage collected; disconnecting Paho Client and stopping network loop".format(
                        callback_name
                    )
                )
                client.on_disconnect = None
                try:
                    client.disconnect()
                finally:
                    # From a Paho callback, this requests the current network thread to exit
                    # without attempting to join itself.
                    client.loop_stop()
            return this

        def on_connect(client, userdata, flags, reason_code, properties):
            # Paho synthesizes this ReasonCode from the MQTT 3.1.1 Connect Return Code.
            logger.info("MQTT CONNACK received; Paho synthesized ReasonCode={}".format(reason_code))
            this = get_transport_from_weakref_or_cleanup_client(client, "on_connect")
            if this is None:
                return

            connection_attempt = this._connection_attempt
            if connection_attempt is None:
                logger.warning("MQTT CONNACK received without an active connection attempt")
                return

            if reason_code.is_failure:
                connection_attempt.fail(_create_error_from_paho_connack_reason(reason_code))
            else:
                connection_attempt.accept_connack()

        def on_disconnect(client, userdata, disconnect_flags, reason_code, properties):
            # Paho synthesizes this ReasonCode from its own disconnection error code.
            logger.info(
                "Paho reported network connection closure; synthesized ReasonCode={}".format(
                    reason_code
                )
            )
            this = get_transport_from_weakref_or_cleanup_client(client, "on_disconnect")
            if this is None:
                return

            cause = None
            if reason_code.is_failure:
                logger.debug("".join(traceback.format_stack()))
                cause = _create_error_from_paho_disconnect_reason(reason_code)

            connection_attempt = this._connection_attempt
            if connection_attempt is None or not connection_attempt.on_disconnect(cause):
                return

            try:
                if this.on_mqtt_disconnected_handler:
                    this.on_mqtt_disconnected_handler(cause)
                else:
                    logger.warning("No on_mqtt_disconnected_handler is configured")
            except Exception:
                logger.warning("Unexpected error calling on_mqtt_disconnected_handler")
                logger.warning(traceback.format_exc())

        def on_subscribe(client, userdata, mid, reason_codes, properties):
            logger.info(
                "MQTT SUBACK received for Packet Identifier {}; Paho synthesized ReasonCodes={}".format(
                    mid, reason_codes
                )
            )
            this = get_transport_from_weakref_or_cleanup_client(client, "on_subscribe")
            if this is None:
                return
            # Paho synthesizes each ReasonCode from an MQTT 3.1.1 SUBACK Return Code.
            # This transport sends one Topic Filter per SUBSCRIBE by design, but handles Paho's
            # general callback shape containing one ReasonCode for each bundled subscription.
            failed_reason_codes = [
                reason_code for reason_code in reason_codes if reason_code.is_failure
            ]
            if failed_reason_codes:
                error = exceptions.ProtocolClientError(
                    "Subscription rejected by MQTT Server: {}".format(
                        ", ".join(str(reason_code) for reason_code in failed_reason_codes)
                    )
                )
                this._op_manager.complete_operation(mid, error=error)
            else:
                this._op_manager.complete_operation(mid)

        def on_unsubscribe(client, userdata, mid, reason_codes, properties):
            logger.info("MQTT UNSUBACK received for Packet Identifier {}".format(mid))
            this = get_transport_from_weakref_or_cleanup_client(client, "on_unsubscribe")
            if this is None:
                return
            # MQTT 3.1.1 UNSUBACK contains only the Packet Identifier, so Paho supplies
            # an empty reason_codes list.
            this._op_manager.complete_operation(mid)

        def on_publish(client, userdata, mid, reason_code, properties):
            logger.info(
                "Paho reported publish completion for MID {}; synthesized ReasonCode={}".format(
                    mid, reason_code
                )
            )
            this = get_transport_from_weakref_or_cleanup_client(client, "on_publish")
            if this is None:
                return
            # MQTT 3.1.1 has no publish-completion reason code or properties, so Paho
            # synthesizes successful values. QoS 0 has no acknowledgment, QoS 1 completes
            # with PUBACK, and QoS 2 with PUBCOMP.
            this._op_manager.complete_operation(mid)

        def on_message(client, userdata, mqtt_message):
            logger.info(
                "MQTT Application Message received on Topic Name {}".format(mqtt_message.topic)
            )
            this = get_transport_from_weakref_or_cleanup_client(client, "on_message")
            if this is None:
                return

            if this.on_mqtt_message_received_handler:
                try:
                    this.on_mqtt_message_received_handler(mqtt_message.topic, mqtt_message.payload)
                except Exception:
                    logger.warning("Unexpected error calling on_mqtt_message_received_handler")
                    logger.warning(traceback.format_exc())
            else:
                logger.debug(
                    "No on_mqtt_message_received_handler is configured; dropping Application Message"
                )

        mqtt_client.on_connect = on_connect
        mqtt_client.on_disconnect = on_disconnect
        mqtt_client.on_subscribe = on_subscribe
        mqtt_client.on_unsubscribe = on_unsubscribe
        mqtt_client.on_publish = on_publish
        mqtt_client.on_message = on_message

        logger.debug("Created Paho client and assigned MQTT callbacks")
        return mqtt_client

    def _disconnect_and_stop_network_loop(self):
        """Disconnect the Paho client, then stop and join its network loop."""

        logger.info("Disconnecting Paho client and stopping network loop")

        try:
            self._mqtt_client.disconnect()
        finally:
            # Always stop and join the network thread, even if disconnect() fails.
            self._mqtt_client.loop_stop()

        logger.debug("Finished disconnecting Paho client and stopping network loop")

    def _cleanup_failed_connect(self):
        """Clean up a failed connection setup without reporting a second lifecycle result.

        connect() reports these failures synchronously by raising an exception. Suppress Paho's
        disconnect callback during teardown so the same attempt is not also reported as a
        disconnection, then restore it for future connection attempts.
        """
        on_disconnect = self._mqtt_client.on_disconnect
        self._mqtt_client.on_disconnect = None
        try:
            self._disconnect_and_stop_network_loop()
        finally:
            self._mqtt_client.on_disconnect = on_disconnect

    def _cleanup_after_network_loop_start_failure(self):
        """Clean up after Paho raises while starting its network thread.

        Paho can retain an unstarted thread if Thread.start() raises, which also causes
        loop_stop() to raise rather than clean up. If normal cleanup encounters that state,
        discard the unusable Paho client without mutating its private thread state.
        """
        failed_client = self._mqtt_client
        try:
            self._cleanup_failed_connect()
        except Exception:
            logger.warning(
                "Paho cleanup failed after network loop startup failure; replacing client"
            )
            logger.warning(traceback.format_exc())

            failed_client.on_disconnect = None
            failed_socket = failed_client.socket()
            if failed_socket is not None:
                try:
                    failed_socket.close()
                except Exception:
                    logger.warning("Unexpected error closing failed Paho client socket")
                    logger.warning(traceback.format_exc())

            try:
                self._mqtt_client = self._create_mqtt_client()
            except Exception:
                logger.warning("Unexpected error replacing failed Paho client")
                logger.warning(traceback.format_exc())

            self._op_manager.complete_all_tracked_operations_as_cancelled()

    def _create_ssl_context(self):
        """
        This method creates the SSLContext object used by Paho to authenticate the connection.
        """
        logger.debug("creating SSL context")
        ssl_context = ssl.SSLContext(protocol=ssl.PROTOCOL_TLS_CLIENT)

        if self._server_verification_cert:
            logger.debug("configuring SSL context with custom server verification certificate")
            ssl_context.load_verify_locations(cadata=self._server_verification_cert)
        else:
            logger.debug("configuring SSL context with default certificates")
            ssl_context.load_default_certs()

        if self._cipher:
            try:
                logger.debug("configuring SSL context with cipher suites")
                ssl_context.set_ciphers(self._cipher)
            except ssl.SSLError as e:
                # TODO: custom error with more detail?
                raise e

        if self._x509_cert is not None:
            logger.debug("configuring SSL context with client certificate and key")
            ssl_context.load_cert_chain(
                self._x509_cert.certificate_file,
                self._x509_cert.key_file,
                self._x509_cert.pass_phrase,
            )

        ssl_context.verify_mode = ssl.CERT_REQUIRED
        ssl_context.check_hostname = True

        return ssl_context

    def shutdown(self):
        """Shut down the transport. This is (currently) irreversible."""
        # Remove the disconnect handler from Paho. We don't want to trigger any events in response
        # to the shutdown and confuse the higher level layers of code. Just end it.
        self._mqtt_client.on_disconnect = None
        try:
            self._disconnect_and_stop_network_loop()
        finally:
            self._op_manager.complete_all_tracked_operations_as_cancelled()

    def connect(self, password=None, timeout=CONNECTION_TIMEOUT):
        """
        Connect to the MQTT Server, using hostname and username set at instantiation.

        This method should be called as an entry point before sending any telemetry.

        The password is not required if the transport was instantiated with an x509 certificate.

        If MQTT connection has been proxied, connection will take a bit longer to allow negotiation
        with the proxy server. Any errors in the proxy connection process will trigger exceptions

        :param str password: The password for connecting with the MQTT Server (Optional).
        :param float timeout: Maximum time to wait for MQTT CONNACK, in seconds.

        :raises: ConnectionFailedError if connection could not be established.
        :raises: ConnectionTimeoutError if MQTT CONNACK was not received before timeout.
        :raises: ConnectionDroppedError if connection is dropped during execution.
        :raises: UnauthorizedError if there is an error authenticating.
        :raises: NoConnectionError in certain failure scenarios where a connection could not be established
        :raises: ProtocolClientError if there is some other client error.
        :raises: TlsExchangeAuthError if there a failure with TLS certificate exchange
        :raises: ProtocolProxyError if there is a proxy-specific error
        """
        logger.debug("connecting to MQTT Server")

        # An unexpected disconnect callback can run just before Paho's network thread exits.
        # loop_stop() blocks until that prior thread exits; before the first connect, its
        # no-thread result is harmless.
        self._mqtt_client.loop_stop()

        connection_attempt = ConnectionAttempt()
        self._connection_attempt = connection_attempt

        self._mqtt_client.username_pw_set(username=self._username, password=password)

        try:
            if self._websockets:
                logger.info("Connecting to MQTT Server over websockets on port 443")
                paho_error_code = self._mqtt_client.connect(
                    host=self._hostname, port=443, keepalive=self._keep_alive
                )
            else:
                logger.info("Connecting to MQTT Server over TCP on port 8883")
                paho_error_code = self._mqtt_client.connect(
                    host=self._hostname, port=8883, keepalive=self._keep_alive
                )
        except socket.error as e:
            self._cleanup_failed_connect()

            # Only this type will raise a special error
            # To stop it from retrying.
            if (
                isinstance(e, ssl.SSLError)
                and e.strerror is not None
                and "CERTIFICATE_VERIFY_FAILED" in e.strerror
            ):
                raise exceptions.TlsExchangeAuthError() from e
            elif isinstance(e, socks.ProxyError):
                if isinstance(e, socks.SOCKS5AuthError):
                    raise exceptions.UnauthorizedError() from e
                # NOTE: add other specialized error handling here as necessary
                else:
                    raise exceptions.ProtocolProxyError() from e
            else:
                # If the socket can't open (e.g. using iptables REJECT), we get a
                # socket.error.  Convert this into ConnectionFailedError so we can retry
                raise exceptions.ConnectionFailedError() from e

        except Exception as e:
            self._cleanup_failed_connect()
            raise exceptions.ProtocolClientError("Unexpected Paho failure during connect") from e

        logger.debug("Paho client.connect() returned MQTTErrorCode={}".format(paho_error_code))
        if paho_error_code:
            self._cleanup_failed_connect()
            raise _create_error_from_paho_error_code(paho_error_code)

        # Start the network loop to process incoming and outgoing MQTT messages
        try:
            paho_error_code = self._mqtt_client.loop_start()
        except Exception as e:
            self._cleanup_after_network_loop_start_failure()
            raise exceptions.ProtocolClientError(
                "Unexpected Paho failure starting network loop"
            ) from e
        logger.debug("Paho client.loop_start() returned MQTTErrorCode={}".format(paho_error_code))
        if paho_error_code:
            self._cleanup_failed_connect()
            raise _create_error_from_paho_error_code(paho_error_code)

        logger.debug("Waiting for MQTT CONNACK")
        try:
            connection_attempt.wait_for_connack(timeout=timeout)
        except Exception:
            try:
                self._cleanup_failed_connect()
            except Exception:
                logger.warning("Unexpected error cleaning up failed MQTT connection")
                logger.warning(traceback.format_exc())
            raise

    def disconnect(self, clear_inflight=False):
        """
        Disconnect from the MQTT Server and wait for the network loop to stop.

        Optionally, clear any inflight operation tracking if clear_inflight is True.

        :raises: ProtocolClientError if there is some client error.
        :raises: ConnectionDroppedError in unexpected cases.
        :raises: UnauthorizedError in unexpected cases.
        :raises: ConnectionFailedError in unexpected cases.
        """
        logger.info("disconnecting from MQTT Server")
        if self._connection_attempt:
            self._connection_attempt.begin_disconnect()
        try:
            paho_error_code = self._mqtt_client.disconnect()
        except Exception as e:
            raise exceptions.ProtocolClientError("Unexpected Paho failure during disconnect") from e
        finally:
            # Always stop and join the network thread, even if disconnect() fails.
            self._mqtt_client.loop_stop()

        logger.debug("Paho client.disconnect() returned MQTTErrorCode={}".format(paho_error_code))
        if paho_error_code:
            # Special case: MQTT_ERR_NO_CONN during disconnect means the socket
            # is already closed. In Paho 2.x, this can happen even after a successful
            # disconnect because the on_disconnect callback fires successfully before
            # disconnect() returns, and Paho's internal cleanup closes the socket.
            # Since we wanted to disconnect and we're disconnected, treat this as success.
            if paho_error_code == mqtt.MQTT_ERR_NO_CONN:
                logger.debug(
                    "Paho client.disconnect() returned MQTT_ERR_NO_CONN; network connection is already closed"
                )
                # Still clear inflight operations since we're effectively disconnected
                if clear_inflight:
                    self._op_manager.complete_all_tracked_operations_as_cancelled()
                else:
                    self._op_manager.stop_tracking_non_publish_operations()
            else:
                # This could result in ConnectionDroppedError or ProtocolClientError
                err = _create_error_from_paho_error_code(paho_error_code)
                raise err
        else:
            # Clear pending ops if instructed, but only if the disconnect was successful.
            # Technically the disconnect could still fail upon response, however that would then
            # stop the network loop via the on_disconnect handler, thus it is safe to clear
            # ops here and now.
            if clear_inflight:
                self._op_manager.complete_all_tracked_operations_as_cancelled()
            else:
                self._op_manager.stop_tracking_non_publish_operations()

    def subscribe(self, topic, qos=1, callback=None):
        """
        Subscribe the Client to one Topic Filter on the MQTT Server.

        :param str topic: A single Topic Filter to subscribe to.
        :param int qos: The maximum QoS requested for the Subscription. Defaults to 1.
        :param callback: A callback to be invoked upon completion (Optional).

        :raises: ValueError if qos is not 0, 1 or 2.
        :raises: ValueError if topic is None or has zero string length.
        :raises: ConnectionDroppedError if connection is dropped during execution.
        :raises: ProtocolClientError if there is some other client error.
        :raises: NoConnectionError if the client is not connected.
        """
        logger.info(
            "sending MQTT SUBSCRIBE for Topic Filter {} with requested maximum QoS {}".format(
                topic, qos
            )
        )
        try:
            paho_error_code, mid = self._mqtt_client.subscribe(topic, qos=qos)
        except ValueError:
            raise
        except Exception as e:
            raise exceptions.ProtocolClientError("Unexpected Paho failure during subscribe") from e
        logger.debug("Paho client.subscribe() returned MQTTErrorCode={}".format(paho_error_code))
        if paho_error_code:
            # This could result in ConnectionDroppedError or ProtocolClientError
            raise _create_error_from_paho_error_code(paho_error_code)
        self._op_manager.register_operation(
            mid=mid, callback=callback, operation_type=OperationType.SUBSCRIBE
        )

    def unsubscribe(self, topic, callback=None):
        """
        Unsubscribe the Client from one Topic Filter on the MQTT Server.

        :param str topic: A single Topic Filter to unsubscribe from.
        :param callback: A callback to be invoked upon completion (Optional).

        :raises: ValueError if topic is None or has zero string length.
        :raises: ConnectionDroppedError if connection is dropped during execution.
        :raises: ProtocolClientError if there is some other client error.
        :raises: NoConnectionError if the client isn't actually connected.
        """
        logger.info("sending MQTT UNSUBSCRIBE for Topic Filter {}".format(topic))
        try:
            paho_error_code, mid = self._mqtt_client.unsubscribe(topic)
        except ValueError:
            raise
        except Exception as e:
            raise exceptions.ProtocolClientError(
                "Unexpected Paho failure during unsubscribe"
            ) from e
        logger.debug("Paho client.unsubscribe() returned MQTTErrorCode={}".format(paho_error_code))
        if paho_error_code:
            # This could result in ConnectionDroppedError or ProtocolClientError
            raise _create_error_from_paho_error_code(paho_error_code)
        self._op_manager.register_operation(
            mid=mid, callback=callback, operation_type=OperationType.UNSUBSCRIBE
        )

    def publish(self, topic, payload, qos=1, callback=None):
        """
        Publish an Application Message to the MQTT Server.

        :param str topic: The Topic Name on which to publish the Application Message.
        :param payload: The Application Message payload.
        :type payload: str, bytes, int, float or None
        :param int qos: The QoS level for delivery of the Application Message. Defaults to 1.
        :param callback: A callback to be invoked upon completion (Optional).

        :raises: ValueError if qos is not 0, 1 or 2
        :raises: ValueError if topic is None or has zero string length
        :raises: ValueError if topic contains a wildcard character ("+" or "#")
        :raises: ValueError if the length of the payload is greater than 268435455 bytes
        :raises: TypeError if payload is not a valid type
        :raises: ConnectionDroppedError if connection is dropped during execution.
        :raises: ProtocolClientError if there is some other client error.
        :raises: NoConnectionError if a QoS 0 message is published while the client is not connected.
        """
        logger.info("sending MQTT PUBLISH on Topic Name {} with QoS {}".format(topic, qos))
        try:
            # NOTE: Paho MQTTMessageInfo allows you to wait upon the completion with
            # `wait_for_publish()`,but that is only supported for PUBLISH.
            # We don't take advantage of it in favor of a general solution (i.e. OperationManager)
            # which can track SUBSCRIBE and UNSUBSCRIBE operations as well.
            # Furthermore, `wait_for_publish()` is buggy when sending a message while disconnected,
            # and does not accurately report the success or failure of the publish operation.
            message_info = self._mqtt_client.publish(topic=topic, payload=payload, qos=qos)
        except ValueError:
            raise
        except TypeError:
            raise
        except Exception as e:
            raise exceptions.ProtocolClientError("Unexpected Paho failure during publish") from e
        paho_error_code = message_info.rc
        mid = message_info.mid
        logger.debug(
            "Paho client.publish() returned MQTTMessageInfo with MQTTErrorCode={}".format(
                paho_error_code
            )
        )
        publish_retained_for_next_connection = paho_error_code == mqtt.MQTT_ERR_NO_CONN and qos > 0
        if paho_error_code and not publish_retained_for_next_connection:
            # This could result in ConnectionDroppedError or ProtocolClientError
            raise _create_error_from_paho_error_code(paho_error_code)
        if publish_retained_for_next_connection:
            logger.debug(
                "Paho retained QoS {} PUBLISH with MID {} for the next connection".format(qos, mid)
            )
        self._op_manager.register_operation(
            mid=mid, callback=callback, operation_type=OperationType.PUBLISH
        )


class OperationType(Enum):
    PUBLISH = "PUBLISH"
    SUBSCRIBE = "SUBSCRIBE"
    UNSUBSCRIBE = "UNSUBSCRIBE"


class PendingOperation(object):
    def __init__(self, operation_type, callback):
        self.operation_type = operation_type
        self.callback = callback


class OperationManager(object):
    """Tracks operation callbacks, unmatched completions, and cancellations by Paho MID."""

    def __init__(self):
        # Maps Paho MID to operations awaiting a response.
        self._pending_operations = {}

        # Maps Paho MIDs with no currently registered operation to optional completion errors.
        # Necessary because sometimes an operation will complete with a response before the
        # Paho call returns.
        self._unknown_operation_completions = {}

        # Tracks cancelled MIDs whose Paho operations may still complete.
        self._cancelled_operation_mids = set()

        self._lock = threading.Lock()

    def register_operation(self, mid, callback, operation_type):
        """Register a pending operation under its Paho MID.

        If a completion has already been recorded for the MID, the callback will be invoked.
        Otherwise, the callback will be invoked when the completion is received.
        """
        invoke_callback = False
        completion_error = None

        with self._lock:
            # If Paho reuses a cancelled MID without completing its previous operation, its next
            # completion belongs to the newly registered operation.
            self._cancelled_operation_mids.discard(mid)

            # Paho can invoke the response callback before its API call returns the MID,
            # thus, the operation might have already completed.
            if mid in self._unknown_operation_completions:

                # Claim the unknown completion now that its operation has been established.
                completion_error = self._unknown_operation_completions.pop(mid)

                # Since a completion was already recorded, indicate callback should be invoked.
                invoke_callback = True

            else:
                self._pending_operations[mid] = PendingOperation(
                    operation_type=operation_type, callback=callback
                )
                logger.debug("Waiting for response on Paho MID {}".format(mid))

        # Invoke the callback only after releasing the lock.
        if invoke_callback:
            logger.debug(
                "Completion for previously unknown Paho MID {} matched registered operation; invoking callback".format(
                    mid
                )
            )
            if callback:
                try:
                    # Not all operation callbacks accept the optional error argument.
                    if completion_error is not None:
                        callback(error=completion_error)
                    else:
                        callback()
                except Exception:
                    logger.debug("Unexpected error calling callback for Paho MID {}".format(mid))
                    logger.debug(traceback.format_exc())
            else:
                # Completion callbacks are optional.
                logger.debug("No callback for Paho MID {}".format(mid))

    def complete_operation(self, mid, error=None):
        """Complete an operation by Paho MID and invoke its callback (if any was set).

        If the MID is unknown, retain its completion in case its operation is registered later.
        """
        callback = None
        invoke_callback = False

        with self._lock:
            if mid in self._cancelled_operation_mids:
                logger.debug("Discarding completion for cancelled Paho MID {}".format(mid))
                self._cancelled_operation_mids.remove(mid)

            # If the Paho MID has a pending operation, invoke its callback.
            elif mid in self._pending_operations:

                # Retrieve the callback, and clear the pending operation now that it has completed.
                callback = self._pending_operations.pop(mid).callback

                # Since the operation is complete, indicate the callback should be invoked.
                invoke_callback = True
            # Otherwise, store the mid as an unknown response
            else:
                logger.debug("Completion received for unknown Paho MID {}; retaining".format(mid))
                self._unknown_operation_completions[mid] = error

        # Invoke the callback only after releasing the lock.
        if invoke_callback:
            logger.debug(
                "Response received for registered Paho MID {}; invoking callback".format(mid)
            )
            if callback:
                try:
                    # Not all operation callbacks accept the optional error argument.
                    if error is not None:
                        callback(error=error)
                    else:
                        callback()
                except Exception:
                    logger.debug("Unexpected error calling callback for Paho MID {}".format(mid))
                    logger.debug(traceback.format_exc())
            else:
                # Completion callbacks are optional.
                logger.debug("No callback set for Paho MID {}".format(mid))

    def stop_tracking_non_publish_operations(self):
        """Stop tracking SUBSCRIBE and UNSUBSCRIBE operations without invoking callbacks.

        Paho does not retain these operations for a later connection. PUBLISH operations remain
        tracked because Paho owns their MQTT 3.1.1 QoS retransmission state.
        """
        with self._lock:
            matching_mids = [
                mid
                for mid, pending_operation in self._pending_operations.items()
                if pending_operation.operation_type
                in (OperationType.SUBSCRIBE, OperationType.UNSUBSCRIBE)
            ]
            for mid in matching_mids:
                del self._pending_operations[mid]
            self._cancelled_operation_mids.update(matching_mids)

    def complete_all_tracked_operations_as_cancelled(self):
        """Complete all tracked SDK operations as cancelled and clear unknown completions.

        This manager owns only local completion tracking: pending callbacks are invoked with
        ``cancelled=True``. Their MIDs remain as tombstones so later Paho completions can be
        discarded. Paho owns MQTT protocol state for accepted operations, including QoS 1 and
        QoS 2 packets retained for redelivery, so those operations may still complete or take
        effect.
        """
        logger.debug("Completing all tracked operations as cancelled")
        with self._lock:
            # Preserve callbacks for invocation after releasing the lock.
            pending_ops = list(self._pending_operations.items())
            self._cancelled_operation_mids.update(self._pending_operations)
            self._pending_operations.clear()
            self._unknown_operation_completions.clear()

        # Invoke pending operation callbacks with cancellation.
        for mid, pending_operation in pending_ops:
            callback = pending_operation.callback
            if callback:
                logger.debug(
                    "Completing tracked operation for Paho MID {} as cancelled; invoking callback".format(
                        mid
                    )
                )
                try:
                    callback(cancelled=True)
                except Exception:
                    logger.debug("Unexpected error calling callback for Paho MID {}".format(mid))
                    logger.debug(traceback.format_exc())
            else:
                logger.debug(
                    "Completing tracked operation for Paho MID {} as cancelled; no callback set".format(
                        mid
                    )
                )


# TODO: Clarify hard-disconnect semantics because cancelling an SDK publish operation does not
# prevent Paho from delivering a retained QoS 1 or QoS 2 message after a later connection.
