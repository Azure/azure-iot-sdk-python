# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

# Temporary path hack (replace once monorepo path solution implemented)
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..\..\python_shared_utils"))
# ---------------------------------------------------------------------

import logging
import types
from transitions import Machine
from iothub_device_sdk.device.transport.transport_protocol import TransportProtocol
from .transport.transport import Transport
from connection_string import ConnectionString, DEVICE_ID, HOST_NAME, SHARED_ACCESS_KEY
from sastoken import SasToken


class DeviceClient(object):
    """Client used to connect a device to an Azure IoT Hub instance"""

    def __init__(self, connection_string, transport_protocol):
        self._connection_string = connection_string
        self._device_id = connection_string[DEVICE_ID]
        self._hostname = connection_string[HOST_NAME]
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
        # self.on_message_broker_connect = types.FunctionType

    # def on_message_broker_connect(self):
    #     self._machine.trig_on_connect()

    def connect_to_iot_hub(self):
        """Connects the client to an Azure IoT Hub instance"""
        logging.info("creating client")
        self._machine.trig_connect()

    def _on_enter_connecting(self):
        self._emit_connection_status()
        self._transport = Transport(self._transport_protocol, self._device_id, self._hostname, self._machine)
        self._transport.create_message_broker_with_callbacks()

        username = self._hostname + "/" + self._device_id
        uri = self._hostname + "/devices/" + self._device_id
        sas_token = SasToken(uri, self._connection_string[SHARED_ACCESS_KEY])

        logging.info("username: %s", username)
        logging.info("sas_token: %s", str(sas_token))

        self._transport.set_options_on_message_broker(username, str(sas_token))

        logging.info("connecting")
        self._transport.connect_to_message_broker()
        # self._machine.trig_on_connect()

    def disconnect_from_iot_hub(self):
        logging.info("disconnecting")
        self._machine.trig_disconnect()

    def _on_enter_disconnecting(self):
        self._emit_connection_status()
        self._transport.disconnect_from_message_broker()

    def send_event(self, payload):
        if self._machine.state == "connected":
            topic = "devices/" + self._device_id + "/messages/events/"
            self._transport.send_event(topic, payload)
        else:
            raise ValueError("cannot send if not connected")

    def _emit_connection_status(self):
        logging.info("emit_connection_status")
        if self.on_connection_state:
            self.on_connection_state(self._machine.state)

    @staticmethod
    def from_connection_string(connection_string):
        """Creates a device client with the specified connection string"""
        return DeviceClient(ConnectionString(connection_string), TransportProtocol.MQTT)
