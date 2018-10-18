# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

import logging
import types
from .symmetric_key_authentication_provider import SymmetricKeyAuthenticationProvider


class DeviceClient(object):
    def __init__(self, auth_provider, transport_config):
        """
        Constructor for instantiating a device client
        :param auth_provider: The authentication provider
        :param transport_config: The transport config
        """
        self._auth_provider = auth_provider
        self._transport_config = transport_config

        self._transport = None
        self.state = "initial"

        self.on_connection_state = types.FunctionType

    def connect(self):
        """Connects the device to an Azure IoT Hub.
        The device client must call this method as an entry point to getting connected to IoT Hub
        """
        logging.info("connecting to transport")
        self._transport = self._transport_config.get_specific_transport(self._auth_provider)
        self._transport.on_transport_connected = self._get_transport_connected_state_callback
        self._transport.connect()
        self._emit_connection_status()

    def send_event(self, event):
        """
        Sends an actual message/telemetry to the IoT Hub via the message broker.
        The device client must call this method to send messages.
        :param event: The actual message to send.
        """
        if self.state is "connected":
            self._transport.send_event(event)
        else:
            logging.error("Can not send if not connected")
            # Check if need to define custom exception
            raise ValueError("No connection present to send event.")

    def _emit_connection_status(self):
        """
        The connection status is emitted whenever the device gets connected or disconnected.
        """
        logging.info("emit_connection_status")
        if self.on_connection_state:
            self.on_connection_state(self.state)
        else:
            logging.error("No callback defined for sending state")

    def _get_transport_connected_state_callback(self, new_state):
        self.state = new_state
        self._emit_connection_status()

    @staticmethod
    def create_from_connection_string(connection_string, transport_config):
        """Creates a device client with the specified connection string"""
        return DeviceClient(
            SymmetricKeyAuthenticationProvider.create_authentication_from_connection_string(
                connection_string
            ),
            transport_config,
        )
