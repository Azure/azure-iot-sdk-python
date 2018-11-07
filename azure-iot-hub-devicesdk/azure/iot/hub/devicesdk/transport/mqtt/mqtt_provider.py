# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

import paho.mqtt.client as mqtt
import logging
import types
import os
import ssl
from transitions import Machine

logger = logging.getLogger(__name__)

class MQTTProvider(object):
    """
    A wrapper over the actual implementation of mqtt message broker which will eventually connect to an mqtt broker
    to publish/subscribe messages.
    """

    def __init__(self, client_id, hostname, username, password):
        """
        Constructor to instantiate a mqtt provider.
        :param client_id: The id of the client connecting to the broker.
        :param hostname: hostname or IP address of the remote broker.
        :param password:  The password to authenticate with.
        """
        states = ["disconnected", "connecting", "connected", "disconnecting"]
        transitions = [
            {"trigger": "trig_connect", "source": "disconnected", "dest": "connecting"},
            {"trigger": "trig_on_connect", "source": "connecting", "dest": "connected"},
            {"trigger": "trig_disconnect", "source": "connected", "dest": "disconnecting"},
            {"trigger": "trig_on_disconnect", "source": "disconnecting", "dest": "disconnected"},
        ]

        self._state_machine = Machine(
            states=states, transitions=transitions, initial="disconnected"
        )
        self._state_machine.on_enter_connecting(self._on_enter_connecting)
        self._state_machine.on_enter_disconnecting(self._on_enter_disconnecting)
        self._state_machine.on_enter_connected(self._emit_connection_status)
        self._state_machine.on_enter_disconnected(self._emit_connection_status)

        self._client_id = client_id
        self._hostname = hostname
        self._username = username
        self._password = password
        self._mqtt_client = None

        self.on_mqtt_connected = types.FunctionType

    def _on_enter_connecting(self):
        """
        The state machine internal enters this method on transitioning to the state of connecting.
        In this method the mqtt provider is created and necessary callbacks are assigned.
        The mqtt provider is also connected to a remote broker and is ready to receive messages.
        """
        self._emit_connection_status()
        self._mqtt_client = mqtt.Client(self._client_id, False, protocol=mqtt.MQTTv311)

        def _on_connect_callback(client, userdata, flags, result_code):
            logger.info("connected with result code: %s", str(result_code))
            self._state_machine.trig_on_connect()

        def on_disconnect_callback(client, userdata, result_code):
            logger.info("disconnected with result code: %s", str(result_code))

        def on_publish_callback(client, userdata, mid):
            logger.info("payload published")

        self._mqtt_client.on_connect = _on_connect_callback
        self._mqtt_client.on_disconnect = on_disconnect_callback
        self._mqtt_client.on_publish = on_publish_callback
        logger.info("Created MQTT provider, assigned callbacks")

        self._mqtt_client.tls_set(
            ca_certs=os.environ.get("IOTHUB_ROOT_CA_CERT"),
            certfile=None,
            keyfile=None,
            cert_reqs=ssl.CERT_REQUIRED,
            tls_version=ssl.PROTOCOL_TLSv1_2,
            ciphers=None,
        )
        self._mqtt_client.username_pw_set(username=self._username, password=self._password)

        self._mqtt_client.connect(host=self._hostname, port=8883)
        self._mqtt_client.loop_start()

    def _on_enter_disconnecting(self):
        self._emit_connection_status()

    def _emit_connection_status(self):
        """
        The connection status is emitted whenever the state machine gets connected or disconnected.
        """
        logger.info("emit_connection_status: %s", self._state_machine.state)
        if self._state_machine.state == "connected":
            self.on_mqtt_connected(self._state_machine.state)

    def connect(self):
        """
        This method connects the upper transport layer to the mqtt provider.
        It internally triggers the state machine to transition into "connecting" state.
        This method should be called as an entry point before sending any telemetry.
        """
        logger.info("creating mqtt client and connecting to mqtt broker")
        self._state_machine.trig_connect()

    def disconnect(self):
        """
        This method disconnects the mqtt provider. This should be called from the upper transport
        when it wants to disconnect from the mqtt provider.
        """
        logger.info("disconnecting transport")
        self._mqtt_client.loop_stop()

    def publish(self, topic, message_payload):
        """
        This method enables the transport to send a message to the message broker
        :param topic: topic: The topic that the message should be published on.
        :param message_payload: The actual message to send.
        """
        logger.info("sending")
        self._mqtt_client.publish(topic=topic, payload=message_payload, qos=1)
