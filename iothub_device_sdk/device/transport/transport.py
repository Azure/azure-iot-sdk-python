# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

from .mqtt_provider import MQTTProvider
from enum import Enum
import types


class TransportProtocol(Enum):
    MQTT = 0
    AMQP = 1
    HTTPS = 2
    MQTT_WS = 3
    AMQP_WS = 4


class Transport(object):

    def __init__(self, auth_provider, transport_protocol):
        """
        Constructor for instantiating a transport
        :param auth_provider: The authentication provider
        :param transport_protocol: The transport protocol
        """
        self._transport_protocol = transport_protocol
        self._auth_provider = auth_provider
        self._mqtt_wrapper = None

        self.on_transport_connected = types.FunctionType

    def connect_to_message_broker(self):
        if self._transport_protocol == TransportProtocol.MQTT:
            self._mqtt_wrapper = MQTTProvider(self._auth_provider.device_id, self._auth_provider.hostname,
                                              str(self._auth_provider.shared_access_signature_token))
            self._mqtt_wrapper.on_mqtt_connected = self._get_mqtt_connected_state_callback
            self._mqtt_wrapper.connect()

    def send_event(self, event):
        if self._transport_protocol == TransportProtocol.MQTT:
            topic = "devices/" + self._auth_provider.device_id + "/messages/events/"
            self._mqtt_wrapper.publish(topic, event)

    def disconnect_from_message_broker(self):
        if self._transport_protocol == TransportProtocol.MQTT:
            self._mqtt_wrapper.disconnect_simple()

    def _get_mqtt_connected_state_callback(self, machine_state):
        return self.on_transport_connected(machine_state)