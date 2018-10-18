# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

from .mqtt_provider import MQTTProvider
import types
from azure.iot.hub.devicesdk.transport.abstract_transport import AbstractTransport


class MQTTTransport(AbstractTransport):
    def __init__(self, auth_provider):
        """
        Constructor for instantiating a transport
        :param auth_provider: The authentication provider
        """
        AbstractTransport.__init__(self, auth_provider)
        self._mqtt_provider = None
        self.on_transport_connected = types.FunctionType

    def connect(self):
        self._mqtt_provider = MQTTProvider(
            self._auth_provider.device_id,
            self._auth_provider.hostname,
            str(self._auth_provider.get_current_sas_token()),
        )
        self._mqtt_provider.on_mqtt_connected = self._get_connected_state_callback
        self._mqtt_provider.connect()

    def send_event(self, event):
        topic = "devices/" + self._auth_provider.device_id + "/messages/events/"
        self._mqtt_provider.publish(topic, event)

    def disconnect(self):
        self._mqtt_provider.disconnect()

    def _get_connected_state_callback(self, machine_state):
        return self.on_transport_connected(machine_state)
