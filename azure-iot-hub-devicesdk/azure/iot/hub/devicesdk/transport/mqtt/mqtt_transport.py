# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

from .mqtt_provider import MQTTProvider
import types
import logging
from azure.iot.hub.devicesdk.transport.abstract_transport import AbstractTransport

logger = logging.getLogger(__name__)

class MQTTTransport(AbstractTransport):
    def __init__(self, auth_provider):
        """
        Constructor for instantiating a transport
        :param auth_provider: The authentication provider
        """
        AbstractTransport.__init__(self, auth_provider)
        self._mqtt_provider = None
        self.on_transport_connected = None

    def connect(self):
        client_id = self._auth_provider.device_id

        if self._auth_provider.module_id is not None:
            client_id += "/" + self._auth_provider.module_id

        username = self._auth_provider.hostname + "/" + client_id + "/" + "?api-version=2018-06-30"

        if hasattr(self._auth_provider, 'gateway_hostname'):
            hostname = self._auth_provider.gateway_hostname
        else:
            hostname = self._auth_provider.hostname

        if hasattr(self._auth_provider, "ca_cert"):
            ca_cert = self._auth_provider.ca_cert
        else:
            ca_cert = None

        self._mqtt_provider = MQTTProvider(client_id, hostname, username,
                                           self._auth_provider.get_current_sas_token(), ca_cert=ca_cert)
        self._mqtt_provider.on_mqtt_connected = self._handle_provider_connected_state
        self._mqtt_provider.connect()

    def send_event(self, event):
        topic = self._get_telemetry_topic()
        self._mqtt_provider.publish(topic, event)

    def disconnect(self):
        self._mqtt_provider.disconnect()

    def _handle_provider_connected_state(self, machine_state):
        logger.info("provider state %s", str(machine_state))
        if self.on_transport_connected:
            return self.on_transport_connected(machine_state)
        else:
            return None

    def _get_telemetry_topic(self):
        topic = "devices/" + self._auth_provider.device_id

        if self._auth_provider.module_id is not None:
            topic += "/modules/" + self._auth_provider.module_id

        topic += "/messages/events/"
        return topic
