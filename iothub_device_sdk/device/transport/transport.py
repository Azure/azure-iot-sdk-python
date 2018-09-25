# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

from .transport_protocol import TransportProtocol
from .mqtt_wrapper import MQTTWrapper
from .amqp_wrapper import AMQPWrapper


class Transport(object):
    def __init__(self, transport_protocol, source, hostname, state_machine):
        """
        Constructor for transport.
        :param transport_protocol:
        :param source: The id of source (i.e. the client).
        :param hostname: The hostname of the hub to connect to. In case of MQTT it will always connect via port 8883 to the host
        """
        self._transport_protocol = transport_protocol
        self._source = source
        self._hostname = hostname
        self._state_machine = state_machine
        self._mqtt_wrapper = None
        self._amqp_wrapper = None

    def send_event(self, target, event, async=None):
        if self._transport_protocol == TransportProtocol.MQTT:
            self._mqtt_wrapper.publish(target, event)
        else:
            print("Not implemented")
            pass

    def create_message_broker_with_callbacks(self):
        if self._transport_protocol == TransportProtocol.MQTT:
            self._mqtt_wrapper = MQTTWrapper.create_mqtt_client_wrapper(self._source, self._hostname, self._state_machine)
            self._mqtt_wrapper.assign_callbacks()
        else:  # There is no actual code here. Just wanted to flex according to protocol
            self._amqp_wrapper = AMQPWrapper.create_amqp_client_wrapper(self._source, self._hostname)

    def set_options_on_message_broker(self, username, password):
        if self._transport_protocol == TransportProtocol.MQTT:
            self._mqtt_wrapper.set_tls_options()
            self._mqtt_wrapper.set_credentials(username, password)

    def connect_to_message_broker(self):
        if self._transport_protocol == TransportProtocol.MQTT:
            self._mqtt_wrapper.connect_and_start(self._hostname)

    def disconnect_from_message_broker(self):
        if self._transport_protocol == TransportProtocol.MQTT:
            self._mqtt_wrapper.disconnect_and_stop()
