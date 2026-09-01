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
from . import transport_exceptions as exceptions
import socks

logger = logging.getLogger(__name__)

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


class MQTTTransport(object):
    """
    A wrapper class that provides an implementation-agnostic MQTT Server interface.
    This transport uses MQTT 3.1.1.

    :ivar on_mqtt_connected_handler: Event handler callback, called upon establishing a connection.
    :type on_mqtt_connected_handler: Function
    :ivar on_mqtt_disconnected_handler: Event handler callback, called upon a disconnection.
    :type on_mqtt_disconnected_handler: Function
    :ivar on_mqtt_message_received_handler: Event handler callback, called upon receiving a message.
    :type on_mqtt_message_received_handler: Function
    :ivar on_mqtt_connection_failure_handler: Event handler callback, called upon a connection failure.
    :type on_mqtt_connection_failure_handler: Function
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

        self.on_mqtt_connected_handler = None
        self.on_mqtt_disconnected_handler = None
        self.on_mqtt_message_received_handler = None
        self.on_mqtt_connection_failure_handler = None

        self._op_manager = OperationManager()

        self._mqtt_client = self._create_mqtt_client()

    def _create_mqtt_client(self):
        """
        Create the MQTT client object and assign all necessary event handler callbacks.
        """
        logger.debug("creating mqtt client")

        # Instantiate the client
        if self._websockets:
            logger.info("Creating client for connecting using MQTT over websockets")
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
            logger.info("Creating client for connecting using MQTT over TCP")
            mqtt_client = mqtt.Client(
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
                client_id=self._client_id,
                clean_session=False,
                protocol=mqtt.MQTTv311,
                reconnect_on_failure=False,
            )

        if self._proxy_options:
            logger.info("Setting custom proxy options on mqtt client")
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

        def get_transport_from_weakref_or_stop_loop(client, callback_name):
            this = self_weakref()
            if this is None:
                logger.info(
                    "{} called after MQTTTransport was garbage collected; stopping Paho network loop".format(
                        callback_name
                    )
                )
                client.loop_stop()
            return this

        def on_connect(client, userdata, flags, reason_code, properties):
            # Paho synthesizes this ReasonCode from the MQTT 3.1.1 Connect Return Code.
            logger.info("CONNACK received: {}".format(reason_code))
            this = get_transport_from_weakref_or_stop_loop(client, "on_connect")
            if this is None:
                return

            if reason_code != 0:  # i.e. if there is an error
                if this.on_mqtt_connection_failure_handler:
                    try:
                        this.on_mqtt_connection_failure_handler(
                            _create_error_from_paho_connack_reason(reason_code)
                        )
                    except Exception:
                        logger.warning(
                            "Unexpected error calling on_mqtt_connection_failure_handler"
                        )
                        logger.warning(traceback.format_exc())
                else:
                    logger.warning(
                        "connection failed, but no on_mqtt_connection_failure_handler handler callback provided"
                    )
            elif this.on_mqtt_connected_handler:
                try:
                    this.on_mqtt_connected_handler()
                except Exception:
                    logger.warning("Unexpected error calling on_mqtt_connected_handler")
                    logger.warning(traceback.format_exc())
            else:
                logger.debug("No event handler callback set for on_mqtt_connected_handler")

        def on_disconnect(client, userdata, disconnect_flags, reason_code, properties):
            # Paho synthesizes this ReasonCode from its own disconnection error code.
            logger.info("Paho reported disconnection: {}".format(reason_code))
            this = get_transport_from_weakref_or_stop_loop(client, "on_disconnect")
            if this is None:
                return

            cause = None
            if reason_code != 0:  # i.e. if there is an error
                logger.debug("".join(traceback.format_stack()))
                cause = _create_error_from_paho_disconnect_reason(reason_code)
                this._disconnect_and_stop_network_loop()

            if this.on_mqtt_disconnected_handler:
                try:
                    this.on_mqtt_disconnected_handler(cause)
                except Exception:
                    logger.warning("Unexpected error calling on_mqtt_disconnected_handler")
                    logger.warning(traceback.format_exc())
            else:
                logger.warning("No event handler callback set for on_mqtt_disconnected_handler")

        def on_subscribe(client, userdata, mid, reason_codes, properties):
            logger.info("SUBACK received for Packet Identifier {}".format(mid))
            this = get_transport_from_weakref_or_stop_loop(client, "on_subscribe")
            if this is None:
                return
            # Paho synthesizes each ReasonCode from an MQTT 3.1.1 SUBACK Return Code.
            failed_suback_return_codes = [
                return_code for return_code in reason_codes if return_code >= 0x80
            ]
            if failed_suback_return_codes:
                error = exceptions.ProtocolClientError(
                    "Subscription rejected by MQTT Server: {}".format(
                        ", ".join(str(return_code) for return_code in failed_suback_return_codes)
                    )
                )
                this._op_manager.complete_operation(mid, error=error)
            else:
                this._op_manager.complete_operation(mid)

        def on_unsubscribe(client, userdata, mid, reason_codes, properties):
            logger.info("UNSUBACK received for Packet Identifier {}".format(mid))
            this = get_transport_from_weakref_or_stop_loop(client, "on_unsubscribe")
            if this is None:
                return
            # MQTT 3.1.1 UNSUBACK contains only the Packet Identifier, so Paho supplies
            # an empty reason_codes list.
            this._op_manager.complete_operation(mid)

        def on_publish(client, userdata, mid, reason_code, properties):
            logger.info("PUBLISH completed for Paho message ID {}".format(mid))
            this = get_transport_from_weakref_or_stop_loop(client, "on_publish")
            if this is None:
                return
            # MQTT 3.1.1 has no publish-completion reason code or properties, so Paho
            # synthesizes successful values. QoS 0 has no acknowledgment, QoS 1 completes
            # with PUBACK, and QoS 2 with PUBCOMP.
            this._op_manager.complete_operation(mid)

        def on_message(client, userdata, mqtt_message):
            logger.info("Application Message received on Topic Name {}".format(mqtt_message.topic))
            this = get_transport_from_weakref_or_stop_loop(client, "on_message")
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
                    "No event handler callback set for on_mqtt_message_received_handler - DROPPING MESSAGE"
                )

        mqtt_client.on_connect = on_connect
        mqtt_client.on_disconnect = on_disconnect
        mqtt_client.on_subscribe = on_subscribe
        mqtt_client.on_unsubscribe = on_unsubscribe
        mqtt_client.on_publish = on_publish
        mqtt_client.on_message = on_message

        logger.debug("Created MQTT protocol client, assigned callbacks")
        return mqtt_client

    def _disconnect_and_stop_network_loop(self):
        """Disconnect the Paho client and stop its network loop."""

        logger.info("Disconnecting Paho client and stopping network loop")

        self._mqtt_client.disconnect()
        self._mqtt_client.loop_stop()

        logger.debug("Done disconnecting Paho client and stopping network loop")

    def _create_ssl_context(self):
        """
        This method creates the SSLContext object used by Paho to authenticate the connection.
        """
        logger.debug("creating a SSL context")
        ssl_context = ssl.SSLContext(protocol=ssl.PROTOCOL_TLS_CLIENT)

        if self._server_verification_cert:
            logger.debug("configuring SSL context with custom server verification cert")
            ssl_context.load_verify_locations(cadata=self._server_verification_cert)
        else:
            logger.debug("configuring SSL context with default certs")
            ssl_context.load_default_certs()

        if self._cipher:
            try:
                logger.debug("configuring SSL context with cipher suites")
                ssl_context.set_ciphers(self._cipher)
            except ssl.SSLError as e:
                # TODO: custom error with more detail?
                raise e

        if self._x509_cert is not None:
            logger.debug("configuring SSL context with client-side certificate and key")
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
        # Now disconnect and stop the network loop.
        self._disconnect_and_stop_network_loop()
        self._op_manager.cancel_all_operations()

    def connect(self, password=None):
        """
        Connect to the MQTT Server, using hostname and username set at instantiation.

        This method should be called as an entry point before sending any telemetry.

        The password is not required if the transport was instantiated with an x509 certificate.

        If MQTT connection has been proxied, connection will take a bit longer to allow negotiation
        with the proxy server. Any errors in the proxy connection process will trigger exceptions

        :param str password: The password for connecting with the MQTT Server (Optional).

        :raises: ConnectionFailedError if connection could not be established.
        :raises: ConnectionDroppedError if connection is dropped during execution.
        :raises: UnauthorizedError if there is an error authenticating.
        :raises: NoConnectionError in certain failure scenarios where a connection could not be established
        :raises: ProtocolClientError if there is some other client error.
        :raises: TlsExchangeAuthError if there a failure with TLS certificate exchange
        :raises: ProtocolProxyError if there is a proxy-specific error
        """
        logger.debug("connecting to MQTT Server")

        self._mqtt_client.username_pw_set(username=self._username, password=password)

        try:
            if self._websockets:
                logger.info("Connect using port 443 (websockets)")
                paho_error_code = self._mqtt_client.connect(
                    host=self._hostname, port=443, keepalive=self._keep_alive
                )
            else:
                logger.info("Connect using port 8883 (TCP)")
                paho_error_code = self._mqtt_client.connect(
                    host=self._hostname, port=8883, keepalive=self._keep_alive
                )
        except socket.error as e:
            self._disconnect_and_stop_network_loop()

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
                    # TODO This is the only I felt like specializing
                    raise exceptions.UnauthorizedError() from e
                else:
                    raise exceptions.ProtocolProxyError() from e
            else:
                # If the socket can't open (e.g. using iptables REJECT), we get a
                # socket.error.  Convert this into ConnectionFailedError so we can retry
                raise exceptions.ConnectionFailedError() from e

        except Exception as e:
            self._disconnect_and_stop_network_loop()

            raise exceptions.ProtocolClientError("Unexpected Paho failure during connect") from e

        logger.debug("Paho connect returned error code={}".format(paho_error_code))
        if paho_error_code:
            raise _create_error_from_paho_error_code(paho_error_code)
        self._mqtt_client.loop_start()

    def disconnect(self, clear_inflight=False):
        """
        Disconnect from the MQTT Server.

        :raises: ProtocolClientError if there is some client error.
        :raises: ConnectionDroppedError in unexpected cases.
        :raises: UnauthorizedError in unexpected cases.
        :raises: ConnectionFailedError in unexpected cases.
        """
        logger.info("disconnecting MQTT client")
        try:
            paho_error_code = self._mqtt_client.disconnect()
        except Exception as e:
            raise exceptions.ProtocolClientError("Unexpected Paho failure during disconnect") from e
        finally:
            self._mqtt_client.loop_stop()

        logger.debug("Paho disconnect returned error code={}".format(paho_error_code))
        if paho_error_code:
            # Special case: MQTT_ERR_NO_CONN during disconnect means the socket
            # is already closed. In Paho 2.x, this can happen even after a successful
            # disconnect because the on_disconnect callback fires successfully before
            # disconnect() returns, and Paho's internal cleanup closes the socket.
            # Since we wanted to disconnect and we're disconnected, treat this as success.
            if paho_error_code == mqtt.MQTT_ERR_NO_CONN:
                logger.debug(
                    "disconnect returned MQTT_ERR_NO_CONN - socket already closed, treating as success"
                )
                # Still clear inflight operations since we're effectively disconnected
                if clear_inflight:
                    self._op_manager.cancel_all_operations()
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
                self._op_manager.cancel_all_operations()

    def subscribe(self, topic, qos=1, callback=None):
        """
        Subscribe the Client to one Topic Filter on the MQTT Server.

        :param str topic: A single Topic Filter to subscribe to.
        :param int qos: The maximum QoS requested for the Subscription. Defaults to 1.
        :param callback: A callback to be triggered upon completion (Optional).

        :raises: ValueError if qos is not 0, 1 or 2.
        :raises: ValueError if topic is None or has zero string length.
        :raises: ConnectionDroppedError if connection is dropped during execution.
        :raises: ProtocolClientError if there is some other client error.
        :raises: NoConnectionError if the client isn't actually connected.
        """
        logger.info("subscribing to Topic Filter {} with QoS {}".format(topic, qos))
        try:
            paho_error_code, mid = self._mqtt_client.subscribe(topic, qos=qos)
        except ValueError:
            raise
        except Exception as e:
            raise exceptions.ProtocolClientError("Unexpected Paho failure during subscribe") from e
        logger.debug("Paho subscribe returned error code={}".format(paho_error_code))
        if paho_error_code:
            # This could result in ConnectionDroppedError or ProtocolClientError
            raise _create_error_from_paho_error_code(paho_error_code)
        self._op_manager.establish_operation(mid, callback)

    def unsubscribe(self, topic, callback=None):
        """
        Unsubscribe the Client from one Topic Filter on the MQTT Server.

        :param str topic: A single Topic Filter to unsubscribe from.
        :param callback: A callback to be triggered upon completion (Optional).

        :raises: ValueError if topic is None or has zero string length.
        :raises: ConnectionDroppedError if connection is dropped during execution.
        :raises: ProtocolClientError if there is some other client error.
        :raises: NoConnectionError if the client isn't actually connected.
        """
        logger.info("unsubscribing from Topic Filter {}".format(topic))
        try:
            paho_error_code, mid = self._mqtt_client.unsubscribe(topic)
        except ValueError:
            raise
        except Exception as e:
            raise exceptions.ProtocolClientError(
                "Unexpected Paho failure during unsubscribe"
            ) from e
        logger.debug("Paho unsubscribe returned error code={}".format(paho_error_code))
        if paho_error_code:
            # This could result in ConnectionDroppedError or ProtocolClientError
            raise _create_error_from_paho_error_code(paho_error_code)
        self._op_manager.establish_operation(mid, callback)

    def publish(self, topic, payload, qos=1, callback=None):
        """
        Publish an Application Message to the MQTT Server.

        :param str topic: The Topic Name on which to publish the Application Message.
        :param payload: The Application Message payload.
        :type payload: str, bytes, int, float or None
        :param int qos: The QoS level for delivery of the Application Message. Defaults to 1.
        :param callback: A callback to be triggered upon completion (Optional).

        :raises: ValueError if qos is not 0, 1 or 2
        :raises: ValueError if topic is None or has zero string length
        :raises: ValueError if the Topic Name contains a wildcard character ("+" or "#")
        :raises: ValueError if the length of the payload is greater than 268435455 bytes
        :raises: TypeError if payload is not a valid type
        :raises: ConnectionDroppedError if connection is dropped during execution.
        :raises: ProtocolClientError if there is some other client error.
        :raises: NoConnectionError if the client isn't actually connected.
        """
        logger.info("publishing on Topic Name {}".format(topic))
        try:
            paho_error_code, mid = self._mqtt_client.publish(topic=topic, payload=payload, qos=qos)
        except ValueError:
            raise
        except TypeError:
            raise
        except Exception as e:
            raise exceptions.ProtocolClientError("Unexpected Paho failure during publish") from e
        logger.debug("Paho publish returned error code={}".format(paho_error_code))
        if paho_error_code:
            # This could result in ConnectionDroppedError or ProtocolClientError
            raise _create_error_from_paho_error_code(paho_error_code)
        self._op_manager.establish_operation(mid, callback)


class OperationManager(object):
    """Tracks callbacks by Paho message ID, including responses received before registration."""

    def __init__(self):
        # Maps Paho message ID to callback for operations awaiting a response.
        self._pending_operation_callbacks = {}

        # Maps Paho message ID to an optional error when a response arrives before registration.
        self._early_operation_completions = {}

        self._lock = threading.Lock()

    def establish_operation(self, mid, callback=None):
        """Register a pending operation and callback under its Paho message ID.

        If the operation has already been completed, the callback will be triggered.
        """
        trigger_callback = False
        completion_error = None

        with self._lock:
            # Paho can invoke the response callback before its API call returns the message ID.
            if mid in self._early_operation_completions:

                # Clear the early response now that its operation has been established.
                completion_error = self._early_operation_completions.pop(mid)

                # Since the operation has already completed, indicate callback should trigger
                trigger_callback = True

            else:
                # Store the operation as pending, along with callback
                self._pending_operation_callbacks[mid] = callback
                logger.debug("Waiting for response on Paho message ID: {}".format(mid))

        # Now that the lock has been released, if the callback should be triggered,
        # go ahead and trigger it now.
        if trigger_callback:
            logger.debug(
                "Response for Paho message ID: {} was received early - triggering callback".format(
                    mid
                )
            )
            if callback:
                try:
                    if completion_error is not None:
                        callback(error=completion_error)
                    else:
                        callback()
                except Exception:
                    logger.debug(
                        "Unexpected error calling callback for Paho message ID: {}".format(mid)
                    )
                    logger.debug(traceback.format_exc())
            else:
                # Completion callbacks are optional.
                logger.debug("No callback for Paho message ID: {}".format(mid))

    def complete_operation(self, mid, error=None):
        """Complete an operation by Paho message ID and trigger its callback.

        If the operation has not been established yet, retain its completion error until it is.
        """
        callback = None
        trigger_callback = False

        with self._lock:
            # If the Paho message ID has a pending operation, trigger its callback.
            if mid in self._pending_operation_callbacks:

                # Retrieve the callback, and clear the pending operation now that it has been completed
                callback = self._pending_operation_callbacks[mid]
                del self._pending_operation_callbacks[mid]

                # Since the operation is complete, indicate the callback should be triggered
                trigger_callback = True

            else:
                logger.debug(
                    "Response received before Paho message ID was registered: {}".format(mid)
                )
                self._early_operation_completions[mid] = error

        # Now that the lock has been released, if the callback should be triggered,
        # go ahead and trigger it now.
        if trigger_callback:
            logger.debug(
                "Response received for registered Paho message ID: {} - triggering callback".format(
                    mid
                )
            )
            if callback:
                try:
                    if error is not None:
                        callback(error=error)
                    else:
                        callback()
                except Exception:
                    logger.debug(
                        "Unexpected error calling callback for Paho message ID: {}".format(mid)
                    )
                    logger.debug(traceback.format_exc())
            else:
                # Completion callbacks are optional.
                logger.debug("No callback set for Paho message ID: {}".format(mid))

    def cancel_all_operations(self):
        """Cancel pending operations and clear all Paho message ID tracking."""
        logger.debug("Cancelling all pending operations")
        with self._lock:
            # Clear pending operations
            pending_ops = list(self._pending_operation_callbacks.items())
            for pending_op in pending_ops:
                mid = pending_op[0]
                del self._pending_operation_callbacks[mid]

            # Clear responses that arrived before their operations were established.
            early_mids = list(self._early_operation_completions)
            for mid in early_mids:
                del self._early_operation_completions[mid]

        # Trigger cancel in pending operation callbacks
        for pending_op in pending_ops:
            mid = pending_op[0]
            callback = pending_op[1]
            if callback:
                logger.debug("Cancelling Paho message ID {} - triggering callback".format(mid))
                try:
                    callback(cancelled=True)
                except Exception:
                    logger.debug(
                        "Unexpected error calling callback for Paho message ID: {}".format(mid)
                    )
                    logger.debug(traceback.format_exc())
            else:
                logger.debug("Cancelling Paho message ID {} - no callback set".format(mid))
