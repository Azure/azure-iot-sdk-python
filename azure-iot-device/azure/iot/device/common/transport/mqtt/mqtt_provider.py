# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import paho.mqtt.client as mqtt
import logging
import ssl
import traceback

logger = logging.getLogger(__name__)


class MQTTProvider(object):
    """
    A wrapper class that provides an implementation-agnostic MQTT message broker interface.

    :ivar on_mqtt_connected: Event handler callback, called upon establishing a connection.
    :type on_mqtt_connected: Function
    :ivar on_mqtt_disconnected: Event handler callback, called upon a disconnection.
    :type on_mqtt_disconnected: Function
    :ivar on_mqtt_message_received: Event handler callback, called upon receiving a message.
    :type on_mqtt_message_received: Function
    """

    def __init__(self, client_id, hostname, username, ca_cert=None):
        """
        Constructor to instantiate a mqtt provider.
        :param str client_id: The id of the client connecting to the broker.
        :param str hostname: Hostname or IP address of the remote broker.
        :param str username: Username for login to the remote broker.
        :param str ca_cert: Certificate which can be used to validate a server-side TLS connection (optional).
        """
        self._client_id = client_id
        self._hostname = hostname
        self._username = username
        self._mqtt_client = None
        self._ca_cert = ca_cert

        self.on_mqtt_connected = None
        self.on_mqtt_disconnected = None
        self.on_mqtt_message_received = None

        # Maps mid->callback for operations where a control packet has been sent
        # but the reponse has not yet been received
        self._pending_operation_callbacks = {}

        # Maps mid->mid for responses received that are in the _pending_operation_callbacks dict.
        # Necessary because sometimes an operation will complete with a response before the
        # Paho call returns.
        # TODO: make this map mid to something more useful (result code?)
        self._unknown_operation_responses = {}

        self._create_mqtt_client()

    def _create_mqtt_client(self):
        """
        Create the MQTT client object and assign all necessary event handler callbacks.
        """
        logger.info("creating mqtt client")

        self._mqtt_client = mqtt.Client(
            client_id=self._client_id, clean_session=False, protocol=mqtt.MQTTv311
        )

        def on_connect(client, userdata, flags, rc):
            logger.info("connected with result code: {}".format(rc))
            # TODO: how to do failed connection?
            # MUST do LBYL here to avoid confusion with errors thrown in calling callback
            if self.on_mqtt_connected:
                try:
                    self.on_mqtt_connected()
                except:  # noqa: E722 do not use bare 'except'
                    logger.error("Unexpected error calling on_mqtt_connected")
                    logger.error(traceback.format_exc())
            else:
                logger.info("No event handler callback set for on_mqtt_connected")

        def on_disconnect(client, userdata, rc):
            logger.info("disconnected with result code: {}".format(rc))
            # MUST do LBYL here to avoid confusion with errors thrown in calling callback
            if self.on_mqtt_disconnected:
                try:
                    self.on_mqtt_disconnected()
                except:  # noqa: E722 do not use bare 'except'
                    logger.error("Unexpected error calling on_mqtt_disconnected")
                    logger.error(traceback.format_exc())
            else:
                logger.info("No event handler callback set for on_mqtt_disconnected")

        def on_subscribe(client, userdata, mid, granted_qos):
            logger.info("suback received for {}".format(mid))
            # TODO: how to do failure?
            self._resolve_pending_callback(mid)

        def on_unsubscribe(client, userdata, mid):
            logger.info("UNSUBACK received for {}".format(mid))
            # TODO: how to do failure?
            self._resolve_pending_callback(mid)

        def on_publish(client, userdata, mid):
            logger.info("payload published for {}".format(mid))
            # TODO: how to do failed publish
            self._resolve_pending_callback(mid)

        def on_message(client, userdata, mqtt_message):
            logger.info("message received on {}".format(mqtt_message.topic))
            # MUST do LBYL here to avoid confusion with errors thrown in calling callback
            if self.on_mqtt_message_received:
                try:
                    # TODO: Why is this returning _topic instead of topic?
                    self.on_mqtt_message_received(mqtt_message.topic, mqtt_message.payload)
                except:  # noqa: E722 do not use bare 'except'
                    logger.error("Unexpected error calling on_mqtt_message_received")
                    logger.error(traceback.format_exc())
            else:
                logger.warning(
                    "No event handler callback set for on_mqtt_message_received - DROPPING MESSAGE"
                )

        self._mqtt_client.on_connect = on_connect
        self._mqtt_client.on_disconnect = on_disconnect
        self._mqtt_client.on_subscribe = on_subscribe
        self._mqtt_client.on_unsubscribe = on_unsubscribe
        self._mqtt_client.on_publish = on_publish
        self._mqtt_client.on_message = on_message

        logger.info("Created MQTT provider, assigned callbacks")

    def connect(self, password):
        """
        Connect to the MQTT broker, using hostname and username set at instantiation.

        This method should be called as an entry point before sending any telemetry.

        :param str password: The password for connecting with the MQTT broker.
        """
        logger.info("connecting to mqtt broker")

        ssl_context = ssl.SSLContext(protocol=ssl.PROTOCOL_TLSv1_2)
        if self._ca_cert:
            ssl_context.load_verify_locations(cadata=self._ca_cert)
        else:
            ssl_context.load_default_certs()
        ssl_context.verify_mode = ssl.CERT_REQUIRED
        ssl_context.check_hostname = True
        self._mqtt_client.tls_set_context(context=ssl_context)
        self._mqtt_client.tls_insecure_set(False)
        self._mqtt_client.username_pw_set(username=self._username, password=password)

        self._mqtt_client.connect(host=self._hostname, port=8883)
        self._mqtt_client.loop_start()

    def reconnect(self, password):
        """
        Reconnect to the MQTT broker, using username set at instantiation.

        Connect should have previously been called in order to use this function.

        :param str password: The password for reconnecting with the MQTT broker.
        """
        logger.info("reconnecting transport")
        self._mqtt_client.username_pw_set(username=self._username, password=password)
        self._mqtt_client.reconnect()

    def disconnect(self):
        """
        Disconnect from the MQTT broker.
        """
        logger.info("disconnecting transport")
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
        self._set_operation_callback(mid, callback)

    def unsubscribe(self, topic, callback=None):
        """
        Unsubscribe the client from one topic on the MQTT broker.

        :param str topic: a single string which is the subscription topic to unsubscribe from.
        :param callback: A callback to be triggered upon completion (Optional).

        :raises: ValueError if topic is None or has zero string length
        """
        logger.info("unsubscribing from {}".format(topic))
        (result, mid) = self._mqtt_client.unsubscribe(topic)
        self._set_operation_callback(mid, callback)

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
        self._set_operation_callback(message_info.mid, callback)

    def _set_operation_callback(self, mid, callback):
        if mid in self._unknown_operation_responses:
            # If response already came back, trigger the callback
            logger.info("Response for MID: {} was received early - triggering callback".format(mid))
            del self._unknown_operation_responses[mid]
            # MUST do LBYL here to avoid confusion with errors thrown in calling callback
            if callback:
                try:
                    callback()
                except:  # noqa: E722 do not use bare 'except'
                    logger.error("Unexpected error calling callback for MID: {}".format(mid))
                    logger.error(traceback.format_exc())
            else:
                logger.info("No callback for MID: {}".format(mid))
        else:
            # Otherwise, set the callback to use later
            logger.info("Waiting for response on MID: {}".format(mid))
            self._pending_operation_callbacks[mid] = callback

    def _resolve_pending_callback(self, mid):
        if mid in self._pending_operation_callbacks:
            # If mid is known, trigger it's associated callback
            logger.info(
                "Response received for recognized MID: {} - triggering callback".format(mid)
            )
            callback = self._pending_operation_callbacks[mid]
            del self._pending_operation_callbacks[mid]
            # MUST do LBYL here to avoid confusion with errors thrown in calling callback
            if callback:
                try:
                    callback()
                except:  # noqa: E722 do not use bare 'except'
                    logger.error("Unexpected error calling callback for MID: {}".format(mid))
                    logger.error(traceback.format_exc())
            else:
                logger.info("No callback set for MID: {}".format(mid))
        else:
            # Otherwise, store the mid as an unknown response
            logger.warning("Response received for unknown MID: {}".format(mid))
            self._unknown_operation_responses[mid] = mid  # TODO: set something more useful here
