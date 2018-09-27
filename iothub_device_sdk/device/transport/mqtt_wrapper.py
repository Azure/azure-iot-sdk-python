# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

import paho.mqtt.client as mqtt
import logging
import os
import ssl


class MQTTWrapper:
    def __init__(self, client_id, hostname, state_machine):
        if client_id and hostname and state_machine:
            pass
        else:
            raise ValueError("Can not instantiate MQTT broker. Incomplete values.")
        self._client_id = client_id
        self._hostname = hostname
        self._mqtt_client = mqtt.Client(client_id, False, protocol=mqtt.MQTTv311)
        self._state_machine = state_machine

    @staticmethod
    def create_mqtt_client_wrapper(client_id, hostname, state_machine):
        return MQTTWrapper(client_id, hostname, state_machine)

    def assign_callbacks(self):
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
        self._mqtt_client.tls_set(ca_certs=os.environ.get("IOTHUB_ROOT_CA_CERT"), certfile=None, keyfile=None,
                                  cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1, ciphers=None)
        self._mqtt_client.tls_insecure_set(False)

    def set_credentials(self, username, password):
        self._mqtt_client.username_pw_set(username=username, password=password)

    def connect_and_start(self, hostname):
        logging.info("connecting to mqtt broker")
        self._mqtt_client.connect(host=hostname, port=8883)
        self._mqtt_client.loop_start()

    def publish(self, topic, message_payload):
        logging.info('sending')
        self._mqtt_client.publish(topic=topic, payload=message_payload, qos=1)

    def disconnect_and_stop(self):
        logging.info('disconnecting from mqtt broker')
        self._mqtt_client.loop_stop()
