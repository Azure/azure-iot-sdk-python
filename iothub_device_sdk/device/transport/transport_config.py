# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------
from enum import Enum
from .mqtt.mqtt_transport import MQTTTransport


class TransportProtocol(Enum):
    """
    Enumeration for different protocols used in the transport layer.
    """

    MQTT = 0
    AMQP = 1
    HTTPS = 2
    MQTT_WS = 3
    AMQP_WS = 4


class TransportConfig(object):
    """
    Information regarding the configuration of a transport class.
    """

    def __init__(self, transport_protocol):
        """
        Constructor for instantiating a transport configuration.
        The device client must create this according to the device's chosen protocol.
        :param transport_protocol: The chose transport protocol
        """
        self._transport_protocol = transport_protocol
        self.device_transport = None

    def get_specific_transport(self, auth_provider):
        """
        Instantiate a specific transport according to the protocol chosen
        :param auth_provider: Authentication provider.
        :return: An instance of a implementation of a specific transport.
        """
        if self._transport_protocol == TransportProtocol.MQTT:
            self.device_transport = MQTTTransport(auth_provider)
        return self.device_transport
