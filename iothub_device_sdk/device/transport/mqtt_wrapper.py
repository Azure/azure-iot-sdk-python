# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

import paho.mqtt.client as mqtt
import logging
import os
import ssl


class MQTTWrapper:
    """A wrapper over the actual implementation of mqtt message broker which will eventually connect to an mqtt broker
             to publish/subscribe messages.
    """
    def __init__(self, client_id, hostname, state_machine):
        """A wrapper over the actual implementation of mqtt which will eventually connect to an mqtt client
         to publish/subscribe messages.

        Args:
            client_id: The id of the client connecting to the message broker
            hostname: hostname or IP address of the remote broker.
            state_machine: A finite state machine that will transition between the various states.

        """
        if client_id and hostname and state_machine:
            pass
        else:
            raise ValueError("Can not instantiate MQTT broker. Incomplete values.")
        self._client_id = client_id
        self._hostname = hostname
        self._mqtt_client = mqtt.Client(client_id, False, protocol=mqtt.MQTTv311)
        self._state_machine = state_machine

    def assign_callbacks(self):
        """
        Assign various callbacks to the mqtt message broker.
        The connect callback implementation.
        The disconnect callback implementation
        The published message callback implementation.
        """
        def _on_connect_callback(client, userdata, flags, result_code):
            logging.info("connected with result code: %s", str(result_code))
            self._state_machine.trig_on_connect()

        def on_disconnect_callback(client, userdata, result_code):
            logging.info("disconnected with result code: %s", str(result_code))

        def on_publish_callback(client, userdata, mid):
            logging.info("payload published")

        self._mqtt_client.on_connect = _on_connect_callback
        self._mqtt_client.on_disconnect = on_disconnect_callback
        self._mqtt_client.on_publish = on_publish_callback

    def set_tls_options(self):
        """
        Configure network encryption and authentication options. Enables SSL/TLS support.
        Configure verification of the server hostname in the server certificate.
        """
        self._mqtt_client.tls_set(ca_certs=os.environ.get("IOTHUB_ROOT_CA_CERT"), certfile=None, keyfile=None,
                                  cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1, ciphers=None)
        self._mqtt_client.tls_insecure_set(False)

    def set_credentials(self, username, password):
        """
        Set the credentials for message broker authentication
        :param username: The username to authenticate with.
        :param password: The password to authenticate with.
        """
        self._mqtt_client.username_pw_set(username=username, password=password)

    def connect_and_start(self, hostname):
        """
        mqtt message broker connects and starts to process network traffic.
        :param hostname: hostname or IP address of the remote broker.
        """
        logging.info("connecting to mqtt broker")
        self._mqtt_client.connect(host=hostname, port=8883)
        self._mqtt_client.loop_start()

    def publish(self, topic, message_payload):
        """
        A message to be sent to the message broker
        :param topic: topic: The topic that the message should be published on.
        :param message_payload: The actual message to send.
        """
        logging.info('sending')
        self._mqtt_client.publish(topic=topic, payload=message_payload, qos=1)

    def disconnect_and_stop(self):
        """
        This will stop the thread previously created with loop_start().
        """
        logging.info('disconnecting from mqtt broker')
        self._mqtt_client.loop_stop()
