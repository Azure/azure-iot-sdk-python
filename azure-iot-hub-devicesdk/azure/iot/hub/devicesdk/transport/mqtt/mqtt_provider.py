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
    A wrapper over the actual implementation of mqtt message broker which will eventually connect to an mqtt broker
    to publish/subscribe messages.
    """

    def __init__(self, client_id, hostname, username, ca_cert=None):
        """
        Constructor to instantiate a mqtt provider.
        :param client_id: The id of the client connecting to the broker.
        :param hostname: hostname or IP address of the remote broker.
        :param ca_cert: Certificate which can be used to validate a server-side TLS connection.
        """
        self._client_id = client_id
        self._hostname = hostname
        self._username = username
        self._mqtt_client = None
        self._ca_cert = ca_cert

        self.on_mqtt_connected = None
        self.on_mqtt_disconnected = None
        self.on_mqtt_published = None
        self.on_mqtt_subscribed = None
        self.on_mqtt_unsubscribed = None

        self._create_mqtt_client()

    def _create_mqtt_client(self):
        """
        Create the MQTT client object and assign all necessary callbacks.
        """
        logger.info("creating mqtt client")

        self._mqtt_client = mqtt.Client(self._client_id, False, protocol=mqtt.MQTTv311)

        def on_connect_callback(client, userdata, flags, result_code):
            logger.info("connected with result code: %s", str(result_code))
            # TODO: how to do failed connection?
            try:
                self.on_mqtt_connected()
            except:  # noqa: E722 do not use bare 'except'
                logger.error("Unexpected error calling on_mqtt_connected")
                logger.error(traceback.format_exc())

        def on_disconnect_callback(client, userdata, result_code):
            logger.info("disconnected with result code: %s", str(result_code))
            try:
                self.on_mqtt_disconnected()
            except:  # noqa: E722 do not use bare 'except'
                logger.error("Unexpected error calling on_mqtt_disconnected")
                logger.error(traceback.format_exc())

        def on_publish_callback(client, userdata, mid):
            logger.info("payload published for %s", str(mid))
            # TODO: how to do failed publish
            try:
                self.on_mqtt_published(mid)
            except:  # noqa: E722 do not use bare 'except'
                logger.error("Unexpected error calling on_mqtt_published")
                logger.error(traceback.format_exc())

        def on_subscribe_callback(client, userdata, mid, granted_qos):
            logger.info("suback received for %s", str(mid))
            # TODO: how to do failure?
            try:
                self.on_mqtt_subscribed(mid)
            except:  # noqa: E722 do not use bare 'except'
                logger.error("Unexpected error calling on_mqtt_subscribed")
                logger.error(traceback.format_exc())

        def on_message_callback(client, userdata, mqtt_message):
            logger.info("message received")
            try:
                self.on_mqtt_message_received(mqtt_message._topic, mqtt_message.payload)
            except:  # noqa: E722 do not use bare 'except'
                logger.error("Unexpected error calling on_mqtt_message_received")
                logger.error(traceback.format_exc())

        def on_unsubscribe_callback(client, userdata, mid):
            logger.info("UNSUBACK received for %s", str(mid))
            # TODO: how to do failure?
            try:
                self.on_mqtt_unsubscribed(mid)
            except:  # noqa: E722 do not use bare 'except'
                logger.error("Unexpected error calling on_mqtt_unsubscribed")
                logger.error(traceback.format_exc())

        self._mqtt_client.on_connect = on_connect_callback
        self._mqtt_client.on_disconnect = on_disconnect_callback
        self._mqtt_client.on_publish = on_publish_callback
        self._mqtt_client.on_subscribe = on_subscribe_callback
        self._mqtt_client.on_message = on_message_callback
        self._mqtt_client.on_unsubscribe = on_unsubscribe_callback

        logger.info("Created MQTT provider, assigned callbacks")

    def connect(self, password):
        """
        This method connects the upper transport layer to the mqtt broker.
        This method should be called as an entry point before sending any telemetry.
        """
        logger.info("connecting to mqtt broker")

        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        if self._ca_cert:
            ssl_context.load_verify_locations(cadata=self._ca_cert)
        else:
            ssl_context.load_default_certs()
        ssl_context.verify_mode = ssl.CERT_REQUIRED
        ssl_context.check_hostname = True
        self._mqtt_client.tls_set_context(ssl_context)
        self._mqtt_client.tls_insecure_set(False)
        self._mqtt_client.username_pw_set(username=self._username, password=password)

        self._mqtt_client.connect(host=self._hostname, port=8883)
        self._mqtt_client.loop_start()

    def reconnect(self, password):
        """
        This method reconnects the mqtt broker, possibly because of a password (sas) change
        Connect should have previously been called.
        """
        logger.info("reconnecting transport")
        self._mqtt_client.username_pw_set(username=self._username, password=password)
        self._mqtt_client.reconnect()

    def disconnect(self):
        """
        This method disconnects the mqtt provider. This should be called from the upper transport
        when it wants to disconnect from the mqtt provider.
        """
        logger.info("disconnecting transport")
        self._mqtt_client.disconnect()

    def publish(self, topic, message_payload):
        """
        This method enables the transport to send a message to the message broker.
        By default the the quality of service level to use is set to 1.
        :param topic: topic: The topic that the message should be published on.
        :param message_payload: The actual message to send.
        :return message ID for the publish request.
        """
        logger.info("sending")
        message_info = self._mqtt_client.publish(topic=topic, payload=message_payload, qos=1)
        return message_info.mid

    def subscribe(self, topic, qos=0):
        """
        This method subscribes the client to one topic.
        :param topic: a single string specifying the subscription topic to subscribe to
        :param qos: the desired quality of service level for the subscription. Defaults to 0.
        :return: message ID for the subscribe request
        Raises a ValueError if qos is not 0, 1 or 2, or if topic is None or has zero string length,
        """
        logger.info("subscribing")
        (result, mid) = self._mqtt_client.subscribe(topic, qos)
        return mid

    def unsubscribe(self, topic):
        """
        Unsubscribe the client from one topic.
        :param topic: a single string which is the subscription topic to unsubscribe from.
        :return: mid the message ID for the unsubscribe request.
        Raises a ValueError if topic is None or has zero string length, or is not a string.
        """
        logger.info("unsubscribing")
        (result, mid) = self._mqtt_client.unsubscribe(topic)
        return mid
