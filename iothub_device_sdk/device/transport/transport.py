# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

from .mqtt_wrapper import MQTTWrapper
from .amqp_wrapper import AMQPWrapper
from enum import Enum


class TransportProtocol(Enum):
    MQTT = 0
    AMQP = 1
    HTTPS = 2
    MQTT_WS = 3
    AMQP_WS = 4


class Transport(object):
    def __init__(self, transport_protocol, source, hostname, state_machine):
        """
        Constructor for transport.
        :param transport_protocol:
        :param source: The id of source (i.e. the client).
        :param hostname: The hostname of the hub to connect to. In case of MQTT it will always connect via port 8883 to the host
        """
        if transport_protocol and source and hostname:
            pass
        else:
            raise ValueError("Can not instantiate transport. Incomplete values.")

        self._transport_protocol = transport_protocol
        self._source = source
        self._hostname = hostname
        self._state_machine = state_machine
        self._mqtt_wrapper = None
        self._amqp_wrapper = None

    def send_event(self, target, event, async=None):
        """
        A message to be sent to the message broker
        :param target: The topic that the message should be published on.
        :param event: The actual message to send.
        """
        if self._transport_protocol == TransportProtocol.MQTT:
            self._mqtt_wrapper.publish(target, event)
        else:
            print("Not implemented")
            pass

    def create_message_broker_with_callbacks(self):
        """
        A message broker is created for the specific transport protocol.
        """
        if self._transport_protocol == TransportProtocol.MQTT:
            self._mqtt_wrapper = MQTTWrapper(self._source, self._hostname, self._state_machine)
            self._mqtt_wrapper.assign_callbacks()
        else:  # There is no actual code here. Just wanted to flex according to protocol
            self._amqp_wrapper = AMQPWrapper(self._source, self._hostname)

    def set_options_on_message_broker(self, username, password):
        """
        Set the Transport Layer Security  options and credentials for message broker authentication
        :param username: The username to authenticate with.
        :param password: The password to authenticate with.
        """
        if self._transport_protocol == TransportProtocol.MQTT:
            self._mqtt_wrapper.set_tls_options()
            self._mqtt_wrapper.set_credentials(username, password)

    def connect_to_message_broker(self):
        """
        The message broker wrapper connects and starts to process network traffic.
        """
        if self._transport_protocol == TransportProtocol.MQTT:
            self._mqtt_wrapper.connect_and_start(self._hostname)

    def disconnect_from_message_broker(self):
        """
        The message broker wrapper disconnects.
        """
        if self._transport_protocol == TransportProtocol.MQTT:
            self._mqtt_wrapper.disconnect_and_stop()
