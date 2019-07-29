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

logger = logging.getLogger(__name__)


class MQTTTransport(object):
    """
    A wrapper class that provides an implementation-agnostic MQTT message broker interface.

    :ivar on_mqtt_connected: Event handler callback, called upon establishing a connection.
    :type on_mqtt_connected: Function
    :ivar on_mqtt_disconnected: Event handler callback, called upon a disconnection.
    :type on_mqtt_disconnected: Function
    :ivar on_mqtt_message_received: Event handler callback, called upon receiving a message.
    :type on_mqtt_message_received: Function
    """

    def __init__(self, client_id, hostname, username, ca_cert=None, x509_cert=None):
        """
        Constructor to instantiate an MQTT protocol wrapper.
        :param str client_id: The id of the client connecting to the broker.
        :param str hostname: Hostname or IP address of the remote broker.
        :param str username: Username for login to the remote broker.
        :param str ca_cert: Certificate which can be used to validate a server-side TLS connection (optional).
        :param x509_cert: Certificate which can be used to authenticate connection to a server in lieu of a password (optional).
        """
        self._client_id = client_id
        self._hostname = hostname
        self._username = username
        self._mqtt_client = None
        self._ca_cert = ca_cert
        self._x509_cert = x509_cert

        self.on_mqtt_connected = None
        self.on_mqtt_disconnected = None
        self.on_mqtt_message_received = None

        self._op_manager = OperationManager()

        self._mqtt_client = self._create_mqtt_client()

    def _create_mqtt_client(self):
        """
        Create the MQTT client object and assign all necessary event handler callbacks.
        """
        logger.info("creating mqtt client")

        # Instantiate client
        mqtt_client = mqtt.Client(
            client_id=self._client_id, clean_session=False, protocol=mqtt.MQTTv311
        )
        mqtt_client.enable_logger(logging.getLogger("paho"))

        # Configure TLS/SSL
        ssl_context = self._create_ssl_context()
        mqtt_client.tls_set_context(context=ssl_context)

        # Set event handlers
        def on_connect(client, userdata, flags, rc):
            logger.info("connected with result code: {}".format(rc))

            # TODO: how to do failed connection?
            if self.on_mqtt_connected:
                try:
                    self.on_mqtt_connected()
                except Exception:
                    logger.error("Unexpected error calling on_mqtt_connected")
                    logger.error(traceback.format_exc())
            else:
                logger.info("No event handler callback set for on_mqtt_connected")

        def on_disconnect(client, userdata, rc):
            logger.info("disconnected with result code: {}".format(rc))

            if self.on_mqtt_disconnected:
                try:
                    self.on_mqtt_disconnected()
                except Exception:
                    logger.error("Unexpected error calling on_mqtt_disconnected")
                    logger.error(traceback.format_exc())
            else:
                logger.info("No event handler callback set for on_mqtt_disconnected")

        def on_subscribe(client, userdata, mid, granted_qos):
            logger.info("suback received for {}".format(mid))
            # TODO: how to do failure?
            self._op_manager.complete_operation(mid)

        def on_unsubscribe(client, userdata, mid):
            logger.info("UNSUBACK received for {}".format(mid))
            # TODO: how to do failure?
            self._op_manager.complete_operation(mid)

        def on_publish(client, userdata, mid):
            logger.info("payload published for {}".format(mid))
            # TODO: how to do failed publish
            self._op_manager.complete_operation(mid)

        def on_message(client, userdata, mqtt_message):
            logger.info("message received on {}".format(mqtt_message.topic))

            if self.on_mqtt_message_received:
                try:
                    self.on_mqtt_message_received(mqtt_message.topic, mqtt_message.payload)
                except Exception:
                    logger.error("Unexpected error calling on_mqtt_message_received")
                    logger.error(traceback.format_exc())
            else:
                logger.warning(
                    "No event handler callback set for on_mqtt_message_received - DROPPING MESSAGE"
                )

        mqtt_client.on_connect = on_connect
        mqtt_client.on_disconnect = on_disconnect
        mqtt_client.on_subscribe = on_subscribe
        mqtt_client.on_unsubscribe = on_unsubscribe
        mqtt_client.on_publish = on_publish
        mqtt_client.on_message = on_message

        logger.info("Created MQTT protocol client, assigned callbacks")
        return mqtt_client

    def _create_ssl_context(self):
        """
        This method creates the SSLContext object used by Paho to authenticate the connection.
        """
        logger.info("creating a SSL context")
        ssl_context = ssl.SSLContext(protocol=ssl.PROTOCOL_TLSv1_2)

        if self._ca_cert:
            ssl_context.load_verify_locations(cadata=self._ca_cert)
        else:
            ssl_context.load_default_certs()
        ssl_context.verify_mode = ssl.CERT_REQUIRED
        ssl_context.check_hostname = True

        if self._x509_cert is not None:
            logger.info("configuring SSL context with client-side certificate and key")
            ssl_context.load_cert_chain(
                self._x509_cert.certificate_file,
                self._x509_cert.key_file,
                self._x509_cert.pass_phrase,
            )

        return ssl_context

    def connect(self, password=None):
        """
        Connect to the MQTT broker, using hostname and username set at instantiation.

        This method should be called as an entry point before sending any telemetry.

        The password is not required if the transport was instantiated with an x509 certificate.

        :param str password: The password for connecting with the MQTT broker (Optional).
        """
        logger.info("connecting to mqtt broker")

        self._mqtt_client.username_pw_set(username=self._username, password=password)

        self._mqtt_client.connect(host=self._hostname, port=8883)
        self._mqtt_client.loop_start()

    def reconnect(self, password=None):
        """
        Reconnect to the MQTT broker, using username set at instantiation.

        Connect should have previously been called in order to use this function.

        The password is not required if the transport was instantiated with an x509 certificate.

        :param str password: The password for reconnecting with the MQTT broker (Optional).
        """
        logger.info("reconnecting MQTT client")
        self._mqtt_client.username_pw_set(username=self._username, password=password)
        self._mqtt_client.reconnect()

    def disconnect(self):
        """
        Disconnect from the MQTT broker.
        """
        logger.info("disconnecting MQTT client")
        self._mqtt_client.disconnect()
        self._mqtt_client.loop_stop()

    def subscribe(self, topic, qos=1, callback=None):
        """
        This method subscribes the client to one topic from the MQTT broker.

        :param str topic: a single string specifying the subscription topic to subscribe to
        :param int qos: the desired quality of service level for the subscription. Defaults to 1.
        :param callback: A callback to be triggered upon completion (Optional).

        :return: message ID for the subscribe request
        :raises: ValueError if qos is not 0, 1 or 2
        :raises: ValueError if topic is None or has zero string length
        """
        logger.info("subscribing to {} with qos {}".format(topic, qos))
        (result, mid) = self._mqtt_client.subscribe(topic, qos=qos)
        self._op_manager.establish_operation(mid, callback)

    def unsubscribe(self, topic, callback=None):
        """
        Unsubscribe the client from one topic on the MQTT broker.

        :param str topic: a single string which is the subscription topic to unsubscribe from.
        :param callback: A callback to be triggered upon completion (Optional).

        :raises: ValueError if topic is None or has zero string length
        """
        logger.info("unsubscribing from {}".format(topic))
        (result, mid) = self._mqtt_client.unsubscribe(topic)
        self._op_manager.establish_operation(mid, callback)

    def publish(self, topic, payload, qos=1, callback=None):
        """
        Send a message via the MQTT broker.

        :param str topic: topic: The topic that the message should be published on.
        :param str payload: The actual message to send.
        :param int qos: the desired quality of service level for the subscription. Defaults to 1.
        :param callback: A callback to be triggered upon completion (Optional).

        :raises: ValueError if qos is not 0, 1 or 2
        :raises: ValueError if topic is None or has zero string length
        :raises: ValueError if topic contains a wildcard ("+")
        :raises: ValueError if the length of the payload is greater than 268435455 bytes
        """
        logger.info("sending")
        message_info = self._mqtt_client.publish(topic=topic, payload=payload, qos=qos)
        self._op_manager.establish_operation(message_info.mid, callback)


class OperationManager(object):
    """Tracks pending operations and thier associated callbacks until completion.
    """

    def __init__(self):
        # Maps mid->callback for operations where a request has been sent
        # but the reponse has not yet been received
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
                logger.info("Waiting for response on MID: {}".format(mid))

        # Now that the lock has been released, if the callback should be triggered,
        # go ahead and trigger it now.
        if trigger_callback:
            logger.info("Response for MID: {} was received early - triggering callback".format(mid))
            if callback:
                try:
                    callback()
                except Exception:
                    logger.error("Unexpected error calling callback for MID: {}".format(mid))
                    logger.error(traceback.format_exc())
            else:
                logger.info("No callback for MID: {}".format(mid))

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
                logger.warning("Response received for unknown MID: {}".format(mid))
                self._unknown_operation_completions[
                    mid
                ] = mid  # TODO: set something more useful here

        # Now that the lock has been released, if the callback should be triggered,
        # go ahead and trigger it now.
        if trigger_callback:
            logger.info(
                "Response received for recognized MID: {} - triggering callback".format(mid)
            )
            if callback:
                try:
                    callback()
                except Exception:
                    logger.error("Unexpected error calling callback for MID: {}".format(mid))
                    logger.error(traceback.format_exc())
            else:
                logger.info("No callback set for MID: {}".format(mid))
