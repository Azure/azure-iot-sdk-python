# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

import logging
from .transport.mqtt.mqtt_transport import MQTTTransport

logger = logging.getLogger(__name__)


class InternalClient(object):
    """
    A super class representing a generic client. This class needs to be extended for specific clients.
    """

    def __init__(self, auth_provider, transport):
        """
        Constructor for instantiating an internal client
        :param auth_provider: The authentication provider
        :param transport: The transport that the client will use.
        """
        self._auth_provider = auth_provider
        self._transport = transport

        self.state = "initial"

        self.on_connection_state = None
        self.on_event_sent = None

    def connect(self):
        """Connects the client to an Azure IoT Hub.
        The client must call this method as an entry point to getting connected to IoT Hub
        """
        logger.info("connecting to transport")
        self._transport.on_transport_connected = self._handle_transport_connected_state
        self._transport.on_transport_disconnected = self._handle_transport_connected_state
        self._transport.on_event_sent = self._handle_transport_event_sent
        self._transport.connect()

    def disconnect(self):
        """
        Disconnect the client from the Azure IoT Hub or Azure IoT Edge Hub
        """
        logger.info("disconnecting from transport")
        self._transport.disconnect()

    def send_event(self, event):
        """
        Sends a message to the default events endpoint on the Azure IoT Hub or Edge Hub instance via a message broker.
        The client must call this method to send messages.
        :param event: The actual message to send.
        """
        self._transport.send_event(event)

    def _emit_connection_status(self):
        """
        The connection status is emitted whenever the client on the module gets connected or disconnected.
        """
        logger.info("emit_connection_status: {}".format(self.state))
        if self.on_connection_state:
            self.on_connection_state(self.state)
        else:
            logger.warn("No callback defined for sending state")

    def _handle_transport_connected_state(self, new_state):
        self.state = new_state
        self._emit_connection_status()

    def _handle_transport_event_sent(self):
        logger.info("_handle_transport_event_sent: " + str(self.on_event_sent))
        if self.on_event_sent:
            self.on_event_sent()

    @classmethod
    def from_authentication_provider(cls, authentication_provider, transport_name):
        """Creates a device client with the specified authentication provider and transport protocol"""
        if transport_name == "mqtt":
            transport = MQTTTransport(authentication_provider)
        else:
            raise NotImplementedError(
                "No specific transport can be instantiated based on the choice."
            )
        return cls(authentication_provider, transport)
