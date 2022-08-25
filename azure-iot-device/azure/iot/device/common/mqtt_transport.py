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

# Mapping of Paho CONNACK rc codes to Error object classes
# Used for connection callbacks
paho_connack_rc_to_error = {
    mqtt.CONNACK_REFUSED_PROTOCOL_VERSION: exceptions.ProtocolClientError,
    mqtt.CONNACK_REFUSED_IDENTIFIER_REJECTED: exceptions.ProtocolClientError,
    mqtt.CONNACK_REFUSED_SERVER_UNAVAILABLE: exceptions.ConnectionFailedError,
    mqtt.CONNACK_REFUSED_BAD_USERNAME_PASSWORD: exceptions.UnauthorizedError,
    mqtt.CONNACK_REFUSED_NOT_AUTHORIZED: exceptions.UnauthorizedError,
}

# Mapping of Paho rc codes to Error object classes
# Used for responses to Paho APIs and non-connection callbacks
paho_rc_to_error = {
    mqtt.MQTT_ERR_NOMEM: exceptions.ProtocolClientError,
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


def _create_error_from_connack_rc_code(rc):
    """
    Given a paho CONNACK rc code, return an Exception that can be raised
    """
    message = mqtt.connack_string(rc)
    if rc in paho_connack_rc_to_error:
        return paho_connack_rc_to_error[rc](message)
    else:
        return exceptions.ProtocolClientError("Unknown CONNACK rc={}".format(rc))


def _create_error_from_rc_code(rc):
    """
    Given a paho rc code, return an Exception that can be raised
    """
    if rc == 1:
        # Paho returns rc=1 to mean "something went wrong.  stop".  We manually translate this to a ConnectionDroppedError.
        return exceptions.ConnectionDroppedError("Paho returned rc==1")
    elif rc in paho_rc_to_error:
        message = mqtt.error_string(rc)
        return paho_rc_to_error[rc](message)
    else:
        return exceptions.ProtocolClientError("Unknown rc=={}".format(rc))


class MQTTTransport(object):
    """
    A wrapper class that provides an implementation-agnostic MQTT message broker interface.

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
        :param str client_id: The id of the client connecting to the broker.
        :param str hostname: Hostname or IP address of the remote broker.
        :param str username: Username for login to the remote broker.
        :param str server_verification_cert: Certificate which can be used to validate a server-side TLS connection (optional).
        :param x509_cert: Certificate which can be used to authenticate connection to a server in lieu of a password (optional).
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
                client_id=self._client_id,
                clean_session=False,
                protocol=mqtt.MQTTv311,
                transport="websockets",
            )
            mqtt_client.ws_set_options(path="/$iothub/websocket")
        else:
            logger.info("Creating client for connecting using MQTT over TCP")
            mqtt_client = mqtt.Client(
                client_id=self._client_id, clean_session=False, protocol=mqtt.MQTTv311
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

        def on_connect(client, userdata, flags, rc):
            this = self_weakref()
            logger.info("connected with result code: {}".format(rc))

            if rc:  # i.e. if there is an error
                if this.on_mqtt_connection_failure_handler:
                    try:
                        this.on_mqtt_connection_failure_handler(
                            _create_error_from_connack_rc_code(rc)
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

        def on_disconnect(client, userdata, rc):
            this = self_weakref()
            logger.info("disconnected with result code: {}".format(rc))

            cause = None
            if rc:  # i.e. if there is an error
                logger.debug("".join(traceback.format_stack()))
                cause = _create_error_from_rc_code(rc)
                if this:
                    this._force_transport_disconnect_and_cleanup()

            if not this:
                # Paho will sometimes call this after we've been garbage collected,  If so, we have to
                # stop the loop to make sure the Paho thread shuts down.
                logger.info(
                    "on_disconnect called with transport==None. Transport must have been garbage collected. stopping loop"
                )
                client.loop_stop()
            else:
                if this.on_mqtt_disconnected_handler:
                    try:
                        this.on_mqtt_disconnected_handler(cause)
                    except Exception:
                        logger.warning("Unexpected error calling on_mqtt_disconnected_handler")
                        logger.warning(traceback.format_exc())
                else:
                    logger.warning("No event handler callback set for on_mqtt_disconnected_handler")

        def on_subscribe(client, userdata, mid, granted_qos):
            this = self_weakref()
            logger.info("suback received for {}".format(mid))
            # subscribe failures are returned from the subscribe() call.  This is just
            # a notification that a SUBACK was received, so there is no failure case here
            this._op_manager.complete_operation(mid)

        def on_unsubscribe(client, userdata, mid):
            this = self_weakref()
            logger.info("UNSUBACK received for {}".format(mid))
            # unsubscribe failures are returned from the unsubscribe() call.  This is just
            # a notification that a SUBACK was received, so there is no failure case here
            this._op_manager.complete_operation(mid)

        def on_publish(client, userdata, mid):
            this = self_weakref()
            logger.info("payload published for {}".format(mid))
            # publish failures are returned from the publish() call.  This is just
            # a notification that a PUBACK was received, so there is no failure case here
            this._op_manager.complete_operation(mid)

        def on_message(client, userdata, mqtt_message):
            this = self_weakref()
            logger.info("message received on {}".format(mqtt_message.topic))

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

        # Set paho automatic-reconnect delay to 2 hours.  Ideally we would turn
        # paho auto-reconnect off entirely, but this is the best we can do.  Without
        # this, we run the risk of our auto-reconnect code and the paho auto-reconnect
        # code conflicting with each other.
        # The choice of 2 hours is completely arbitrary
        mqtt_client.reconnect_delay_set(120 * 60)

        logger.debug("Created MQTT protocol client, assigned callbacks")
        return mqtt_client

    def _force_transport_disconnect_and_cleanup(self):
        """
        After disconnecting because of an error, Paho was designed to keep the loop running and
        to try reconnecting after the reconnect interval. We don't want Paho to reconnect because
        we want to control the timing of the reconnect, so we force the loop to stop.

        We are relying on intimate knowledge of Paho behavior here.  If this becomes a problem,
        it may be necessary to write our own Paho thread and stop using thread_start()/thread_stop().
        This is certainly supported by Paho, but the thread that Paho provides works well enough
        (so far) and making our own would be more complex than is currently justified.
        """

        logger.info("Forcing paho disconnect to prevent it from automatically reconnecting")

        # Note: We are calling this inside our on_disconnect() handler, so we might be inside the
        # Paho thread at this point. This is perfectly valid.  Comments in Paho's client.py
        # loop_forever() function re-comment calling disconnect() from a callback to exit the
        # Paho thread/loop.

        self._mqtt_client.disconnect()

        # Calling disconnect() isn't enough.  We also need to call loop_stop to make sure
        # Paho is as clean as possible.  Our call to disconnect() above is enough to stop the
        # loop and exit the tread, but the call to loop_stop() is necessary to complete the cleanup.

        self._mqtt_client.loop_stop()

        # Finally, because of a bug in Paho, we need to null out the _thread pointer.  This
        # is necessary because the code that sets _thread to None only gets called if you
        # call loop_stop from an external thread (and we're still inside the Paho thread here).
        if threading.current_thread() == self._mqtt_client._thread:
            logger.debug("in paho thread.  nulling _thread")
            self._mqtt_client._thread = None

        logger.debug("Done forcing paho disconnect")

    def _create_ssl_context(self):
        """
        This method creates the SSLContext object used by Paho to authenticate the connection.
        """
        logger.debug("creating a SSL context")
        ssl_context = ssl.SSLContext(protocol=ssl.PROTOCOL_TLSv1_2)

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
        # Now disconnect and do some additional cleanup.
        self._force_transport_disconnect_and_cleanup()
        self._op_manager.cancel_all_operations()

    def connect(self, password=None):
        """
        Connect to the MQTT broker, using hostname and username set at instantiation.

        This method should be called as an entry point before sending any telemetry.

        The password is not required if the transport was instantiated with an x509 certificate.

        If MQTT connection has been proxied, connection will take a bit longer to allow negotiation
        with the proxy server. Any errors in the proxy connection process will trigger exceptions

        :param str password: The password for connecting with the MQTT broker (Optional).

        :raises: ConnectionFailedError if connection could not be established.
        :raises: ConnectionDroppedError if connection is dropped during execution.
        :raises: UnauthorizedError if there is an error authenticating.
        :raises: NoConnectionError in certain failure scenarios where a connection could not be established
        :raises: ProtocolClientError if there is some other client error.
        :raises: TlsExchangeAuthError if there a failure with TLS certificate exchange
        :raises: ProtocolProxyError if there is a proxy-specific error
        """
        logger.debug("connecting to mqtt broker")

        self._mqtt_client.username_pw_set(username=self._username, password=password)

        try:
            if self._websockets:
                logger.info("Connect using port 443 (websockets)")
                rc = self._mqtt_client.connect(
                    host=self._hostname, port=443, keepalive=self._keep_alive
                )
            else:
                logger.info("Connect using port 8883 (TCP)")
                rc = self._mqtt_client.connect(
                    host=self._hostname, port=8883, keepalive=self._keep_alive
                )
        except socket.error as e:
            self._force_transport_disconnect_and_cleanup()

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
            self._force_transport_disconnect_and_cleanup()

            raise exceptions.ProtocolClientError("Unexpected Paho failure during connect") from e

        logger.debug("_mqtt_client.connect returned rc={}".format(rc))
        if rc:
            raise _create_error_from_rc_code(rc)
        self._mqtt_client.loop_start()

    def disconnect(self, clear_inflight=False):
        """
        Disconnect from the MQTT broker.

        :raises: ProtocolClientError if there is some client error.
        :raises: ConnectionDroppedError in unexpected cases.
        :raises: UnauthorizedError in unexpected cases.
        :raises: ConnectionFailedError in unexpected cases.
        :raises: NoConnectionError if the client isn't actually connected.
        """
        logger.info("disconnecting MQTT client")
        try:
            rc = self._mqtt_client.disconnect()
        except Exception as e:
            raise exceptions.ProtocolClientError("Unexpected Paho failure during disconnect") from e
        finally:
            self._mqtt_client.loop_stop()

            if threading.current_thread() == self._mqtt_client._thread:
                logger.debug("in paho thread.  nulling _thread")
                self._mqtt_client._thread = None

        logger.debug("_mqtt_client.disconnect returned rc={}".format(rc))
        if rc:
            # This could result in ConnectionDroppedError or ProtocolClientError
            # No matter what, we always raise here to give upper layers a chance to respond
            # to this error.
            err = _create_error_from_rc_code(rc)
            raise err
        else:
            # Clear pending ops if instructed, but only if the disconnect was successful.
            # Technically the disconnect could still fail upon response, however that would then
            # cause a force disconnect via the on_disconnect handler, thus it is safe to clear
            # ops here and now.
            if clear_inflight:
                self._op_manager.cancel_all_operations()

    def subscribe(self, topic, qos=1, callback=None):
        """
        This method subscribes the client to one topic from the MQTT broker.

        :param str topic: a single string specifying the subscription topic to subscribe to
        :param int qos: the desired quality of service level for the subscription. Defaults to 1.
        :param callback: A callback to be triggered upon completion (Optional).

        :raises: ValueError if qos is not 0, 1 or 2.
        :raises: ValueError if topic is None or has zero string length.
        :raises: ConnectionDroppedError if connection is dropped during execution.
        :raises: ProtocolClientError if there is some other client error.
        :raises: NoConnectionError if the client isn't actually connected.
        """
        logger.info("subscribing to {} with qos {}".format(topic, qos))
        try:
            (rc, mid) = self._mqtt_client.subscribe(topic, qos=qos)
        except ValueError:
            raise
        except Exception as e:
            raise exceptions.ProtocolClientError("Unexpected Paho failure during subscribe") from e
        logger.debug("_mqtt_client.subscribe returned rc={}".format(rc))
        if rc:
            # This could result in ConnectionDroppedError or ProtocolClientError
            raise _create_error_from_rc_code(rc)
        self._op_manager.establish_operation(mid, callback)

    def unsubscribe(self, topic, callback=None):
        """
        Unsubscribe the client from one topic on the MQTT broker.

        :param str topic: a single string which is the subscription topic to unsubscribe from.
        :param callback: A callback to be triggered upon completion (Optional).

        :raises: ValueError if topic is None or has zero string length.
        :raises: ConnectionDroppedError if connection is dropped during execution.
        :raises: ProtocolClientError if there is some other client error.
        :raises: NoConnectionError if the client isn't actually connected.
        """
        logger.info("unsubscribing from {}".format(topic))
        try:
            (rc, mid) = self._mqtt_client.unsubscribe(topic)
        except ValueError:
            raise
        except Exception as e:
            raise exceptions.ProtocolClientError(
                "Unexpected Paho failure during unsubscribe"
            ) from e
        logger.debug("_mqtt_client.unsubscribe returned rc={}".format(rc))
        if rc:
            # This could result in ConnectionDroppedError or ProtocolClientError
            raise _create_error_from_rc_code(rc)
        self._op_manager.establish_operation(mid, callback)

    def publish(self, topic, payload, qos=1, callback=None):
        """
        Send a message via the MQTT broker.

        :param str topic: topic: The topic that the message should be published on.
        :param payload: The actual message to send.
        :type payload: str, bytes, int, float or None
        :param int qos: the desired quality of service level for the subscription. Defaults to 1.
        :param callback: A callback to be triggered upon completion (Optional).

        :raises: ValueError if qos is not 0, 1 or 2
        :raises: ValueError if topic is None or has zero string length
        :raises: ValueError if topic contains a wildcard ("+")
        :raises: ValueError if the length of the payload is greater than 268435455 bytes
        :raises: TypeError if payload is not a valid type
        :raises: ConnectionDroppedError if connection is dropped during execution.
        :raises: ProtocolClientError if there is some other client error.
        :raises: NoConnectionError if the client isn't actually connected.
        """
        logger.info("publishing on {}".format(topic))
        try:
            (rc, mid) = self._mqtt_client.publish(topic=topic, payload=payload, qos=qos)
        except ValueError:
            raise
        except TypeError:
            raise
        except Exception as e:
            raise exceptions.ProtocolClientError("Unexpected Paho failure during publish") from e
        logger.debug("_mqtt_client.publish returned rc={}".format(rc))
        if rc:
            # This could result in ConnectionDroppedError or ProtocolClientError
            raise _create_error_from_rc_code(rc)
        self._op_manager.establish_operation(mid, callback)


class OperationManager(object):
    """Tracks pending operations and their associated callbacks until completion."""

    def __init__(self):
        # Maps mid->callback for operations where a request has been sent
        # but the response has not yet been received
        self._pending_operation_callbacks = {}

        # Maps mid->mid for responses received that are NOT established in the _pending_operation_callbacks dict.
        # Necessary because sometimes an operation will complete with a response before the
        # Paho call returns.
        # TODO: make this map mid to something more useful (result code?)
        self._unknown_operation_completions = {}

        self._lock = threading.Lock()

    def establish_operation(self, mid, callback=None):
        """Establish a pending operation identified by MID, and store its completion callback.

        If the operation has already been completed, the callback will be triggered.
        """
        trigger_callback = False

        with self._lock:
            # Check to see if a response was already received for this MID before this method was
            # able to be called due to threading shenanigans
            if mid in self._unknown_operation_completions:

                # Clear the recorded unknown response now that it has been resolved
                del self._unknown_operation_completions[mid]

                # Since the operation has already completed, indicate callback should trigger
                trigger_callback = True

            else:
                # Store the operation as pending, along with callback
                self._pending_operation_callbacks[mid] = callback
                logger.debug("Waiting for response on MID: {}".format(mid))

        # Now that the lock has been released, if the callback should be triggered,
        # go ahead and trigger it now.
        if trigger_callback:
            logger.debug(
                "Response for MID: {} was received early - triggering callback".format(mid)
            )
            if callback:
                try:
                    callback()
                except Exception:
                    logger.debug("Unexpected error calling callback for MID: {}".format(mid))
                    logger.debug(traceback.format_exc())
            else:
                # Not entirely unexpected because of QOS=1
                logger.debug("No callback for MID: {}".format(mid))

    def complete_operation(self, mid):
        """Complete an operation identified by MID and trigger the associated completion callback.

        If the operation MID is unknown, the completion status will be stored until
        the operation is established.
        """
        callback = None
        trigger_callback = False

        with self._lock:
            # If the mid is associated with an established pending operation, trigger the associated callback
            if mid in self._pending_operation_callbacks:

                # Retrieve the callback, and clear the pending operation now that it has been completed
                callback = self._pending_operation_callbacks[mid]
                del self._pending_operation_callbacks[mid]

                # Since the operation is complete, indicate the callback should be triggered
                trigger_callback = True

            else:
                # Otherwise, store the mid as an unknown response
                logger.debug("Response received for unknown MID: {}".format(mid))
                self._unknown_operation_completions[
                    mid
                ] = mid  # TODO: set something more useful here

        # Now that the lock has been released, if the callback should be triggered,
        # go ahead and trigger it now.
        if trigger_callback:
            logger.debug(
                "Response received for recognized MID: {} - triggering callback".format(mid)
            )
            if callback:
                try:
                    callback()
                except Exception:
                    logger.debug("Unexpected error calling callback for MID: {}".format(mid))
                    logger.debug(traceback.format_exc())
            else:
                # fully expected.  QOS=1 means we might get 2 PUBACKs
                logger.debug("No callback set for MID: {}".format(mid))

    def cancel_all_operations(self):
        """Complete all pending operations with cancellation, removing MID tracking"""
        logger.debug("Cancelling all pending operations")
        with self._lock:
            # Clear pending operations
            pending_ops = list(self._pending_operation_callbacks.items())
            for pending_op in pending_ops:
                mid = pending_op[0]
                del self._pending_operation_callbacks[mid]

            # Clear unknown responses
            unknown_mids = [mid for mid in self._unknown_operation_completions]
            for mid in unknown_mids:
                del self._unknown_operation_completions[mid]

        # Trigger cancel in pending operation callbacks
        for pending_op in pending_ops:
            mid = pending_op[0]
            callback = pending_op[1]
            if callback:
                logger.debug("Cancelling {} - Triggering callback".format(mid))
                try:
                    callback(cancelled=True)
                except Exception:
                    logger.debug("Unexpected error calling callback for MID: {}".format(mid))
                    logger.debug(traceback.format_exc())
            else:
                logger.debug("Cancelling {} - No callback set for MID".format(mid))
