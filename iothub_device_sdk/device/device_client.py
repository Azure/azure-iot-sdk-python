# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

# Temporary path hack (replace once monorepo path solution implemented)
# import os
# import sys
# sys.path.append(os.path.join(os.path.dirname(__file__), "..\..\python_shared_utils"))
# ---------------------------------------------------------------------

import logging
import types
from transitions import Machine
from .transport.transport import Transport
from .authentication_provider import AuthenticationProvider
# from connection_string import ConnectionString, DEVICE_ID, HOST_NAME, SHARED_ACCESS_KEY
# from sastoken import SasToken


class DeviceClient(object):
    """The public facing API that will allow a single physical device to connect
        to an Azure IoT Hub. The Azure IoT Hub supports sending events to and receiving
        messages from an IoT Hub.
    """
    def __init__(self, auth_provider, transport_protocol):
        self._auth_provider = auth_provider
        self._device_id = auth_provider.device_id

        self._transport_protocol = transport_protocol

        states = ["disconnected", "connecting", "connected", "disconnecting"]
        transitions = [
            {"trigger": "trig_connect", "source": "disconnected", "dest": "connecting"},
            {"trigger": "trig_on_connect", "source": "connecting", "dest": "connected"},
            {"trigger": "trig_disconnect", "source": "connected", "dest": "disconnecting"},
            {"trigger": "trig_on_disconnect", "source": "disconnecting", "dest": "disconnected"}
        ]

        self._machine = Machine(states=states, transitions=transitions, initial="disconnected")
        self._machine.on_enter_connecting(self._on_enter_connecting)
        self._machine.on_enter_disconnecting(self._on_enter_disconnecting)
        self._machine.on_enter_connected(self._emit_connection_status)
        self._machine.on_enter_disconnected(self._emit_connection_status)

        self.on_connection_state = types.FunctionType
        self.on_c2d_message = types.FunctionType

    def connect(self):
        """Connects the device to an Azure IoT Hub.
        The device client must call this method as an entry point to getting connected to IoT Hub
        """
        logging.info("creating client")
        self._machine.trig_connect()

    def _on_enter_connecting(self):
        """
        The state machine internal to the device enters this method on transitioning to the state of connecting.
        In this method the transport layer is created and transport connects to the message broker.
        This prepares the device to further send messages to the IoT Hub via the message broker.
        """
        self._emit_connection_status()
        self._transport = Transport(self._transport_protocol, self._auth_provider.device_id,
                                    self._auth_provider.hostname, self._machine)
        self._transport.create_message_broker_with_callbacks()

        username = self._auth_provider.username
        sas_token_str = str(self._auth_provider.sas_token)
        logging.info("username: %s", username)
        logging.info("sas_token: %s", sas_token_str)

        self._transport.set_options_on_message_broker(username, sas_token_str)

        logging.info("connecting")
        self._transport.connect_to_message_broker()
        # self._machine.trig_on_connect()

    def disconnect_from_iot_hub(self):
        """
        Disconnects the device from Azure IoT Hub
        """
        logging.info("disconnecting")
        self._machine.trig_disconnect()

    def _on_enter_disconnecting(self):
        """
        The state machine internal to the device enters this method on transitioning to the state of disconnecting.
        """
        self._emit_connection_status()
        self._transport.disconnect_from_message_broker()

    def send_event(self, payload):
        """
        Sends an actual message/telemetry to the IoT Hub via the message broker.
        The device client must call this method to send messages.
        :param payload: The actual message to send.
        """
        if self._machine.state == "connected":
            topic = "devices/" + self._device_id + "/messages/events/"
            self._transport.send_event(topic, payload)
        else:
            raise ValueError("cannot send if not connected")

    def _emit_connection_status(self):
        """
        The connection status is emitted whenever the state machine internal to the device gets connected or disconnected.
        """
        logging.info("emit_connection_status")
        if self.on_connection_state:
            self.on_connection_state(self._machine.state)

    @staticmethod
    def from_connection_string(connection_string, transport_protocol):
        """Creates a device client with the specified connection string"""
        return DeviceClient(AuthenticationProvider.create_authentication_from_connection_string(connection_string), transport_protocol)
