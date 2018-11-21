# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

import logging
import six.moves.queue as queue
from .mqtt_provider import MQTTProvider
from transitions.extensions import LockedMachine as Machine
from azure.iot.hub.devicesdk.transport.abstract_transport import AbstractTransport

"""
The below import is for generating the state machine graph.
"""
# from transitions.extensions import LockedGraphMachine as Machine

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
        self.on_transport_disconnected = None
        self.on_event_sent = None
        self._event_queue = queue.LifoQueue()

        states = ["disconnected", "connecting", "connected", "sending", "disconnecting"]

        transitions = [
            {
                "trigger": "_trig_connect",
                "source": "disconnected",
                "dest": "connecting",
                "after": "_after_action_provider_connect",
            },
            {
                "trigger": "_trig_connect",
                "source": ["connecting", "connected", "sending"],
                "dest": None,
            },
            {
                "trigger": "_trig_provider_connect_complete",
                "source": "connecting",
                "dest": "connected",
                "after": "_trig_check_send_event_queue",
            },
            {"trigger": "_trig_disconnect", "source": "disconnected", "dest": None},
            {
                "trigger": "_trig_disconnect",
                "source": "connected",
                "dest": "disconnecting",
                "after": "_after_action_provider_disconnect",
            },
            {
                "trigger": "_trig_provider_disconnect_complete",
                "source": "disconnecting",
                "dest": "disconnected",
            },
            {
                "trigger": "_trig_send_event",
                "source": "connected",
                "before": "_before_action_add_event_to_queue",
                "dest": "sending",
                "after": "_trig_check_send_event_queue",
            },
            {
                "trigger": "_trig_provider_publish_complete",
                "source": "sending",
                "dest": None,
                "before": "_before_action_notify_publish_complete",
                "after": "_trig_check_send_event_queue",
            },
            {
                "trigger": "_trig_send_event",
                "source": ["connecting", "sending"],
                "before": "_before_action_add_event_to_queue",
                "dest": None,
            },
            {
                "trigger": "_trig_send_event",
                "source": "disconnected",
                "before": "_before_action_add_event_to_queue",
                "dest": "connecting",
                "after": "_after_action_provider_connect",
            },
            {
                "trigger": "_trig_check_send_event_queue",
                "source": ["connected", "sending"],
                "dest": "connected",
                "conditions": "_queue_is_empty",
            },
            {
                "trigger": "_trig_check_send_event_queue",
                "source": ["connected", "sending"],
                "dest": "sending",
                "unless": "_queue_is_empty",
                "after": "_after_action_deliver_next_queued_event",
            },
        ]

        def _on_transition_complete(event):
            if not event.transition:
                dest = "[no transition]"
            else:
                dest = event.transition.dest
            logger.info(
                "Transition complete.  Trigger=%s, Source=%s, Dest=%s, result=%s, error=%s",
                event.event.name,
                event.state,
                dest,
                str(event.result),
                str(event.error),
            )

        self._state_machine = Machine(
            model=self,
            states=states,
            transitions=transitions,
            initial="disconnected",
            send_event=True,
            finalize_event=_on_transition_complete,
        )

        # to render the state machine as a PNG:
        # 1. apt insatll graphviz
        # 2. pip install pygraphviz
        # 3. change import line at top of this file to import LockedGraphMachine as Machine
        # 4. uncomment the following line
        # 5. run this code
        # self.get_graph().draw('mqtt_transport.png', prog='dot')

        self._create_mqtt_provider()

    def on_enter_connected(self, event):
        if event.event.name == "_trig_provider_connect_complete":
            self.on_transport_connected("connected")

    def on_enter_disconnected(self, event):
        if event.event.name == "_trig_provider_disconnect_complete":
            self.on_transport_disconnected("disconnected")

    def _before_action_notify_publish_complete(self, event):
        logger.info("publish complete:" + str(event))
        logger.info("publish error:" + str(event.error))
        if not event.error:
            self.on_event_sent()

    def _after_action_provider_connect(self, event):
        """
        Call into the provider to connect the transport.
        This is meant to be called by the state machine as an "after" action
        """
        self._mqtt_provider.connect()

    def _after_action_provider_disconnect(self, event):
        """
        Call into the provider to disconnect the transport.
        This is meant to be called by the state machine as an "after" action
        """
        self._mqtt_provider.disconnect()

    def _before_action_add_event_to_queue(self, event):
        """
        Queue an event for sending later.
        This is meant to be called by the state machine as an "before" action
        """
        # TODO: throw here if event.args[0] is not an event/message
        self._event_queue.put_nowait(event.args[0])

    def _queue_is_empty(self, event):
        """
        Return true if the sending queue is empty.
        This is meant to be called by the state machine as a "conditions" or "unless" check
        """
        return self._event_queue.empty()

    def _after_action_deliver_next_queued_event(self, event):
        """
        Call the provider to deliver the next event
        This is meant to be called by the state machine as an "before" action
        """
        try:
            event_to_send = self._event_queue.get_nowait()
            topic = self._get_telemetry_topic()
            self._mqtt_provider.publish(topic, event_to_send)
        except queue.Empty:
            logger.warning("UNEXPECTED: queue is empty in _after_action_deliver_next_queued_event")

    def _create_mqtt_provider(self):
        client_id = self._auth_provider.device_id

        if self._auth_provider.module_id is not None:
            client_id += "/" + self._auth_provider.module_id

        username = self._auth_provider.hostname + "/" + client_id + "/" + "?api-version=2018-06-30"

        hostname = None
        if hasattr(self._auth_provider, "gateway_hostname"):
            hostname = self._auth_provider.gateway_hostname
        if not hostname or len(hostname) == 0:
            hostname = self._auth_provider.hostname

        if hasattr(self._auth_provider, "ca_cert"):
            ca_cert = self._auth_provider.ca_cert
        else:
            ca_cert = None

        self._mqtt_provider = MQTTProvider(
            client_id,
            hostname,
            username,
            self._auth_provider.get_current_sas_token(),
            ca_cert=ca_cert,
        )

        self._mqtt_provider.on_mqtt_connected = self._trig_provider_connect_complete
        self._mqtt_provider.on_mqtt_disconnected = self._trig_provider_disconnect_complete
        self._mqtt_provider.on_mqtt_published = self._trig_provider_publish_complete

    def _get_telemetry_topic(self):
        topic = "devices/" + self._auth_provider.device_id

        if self._auth_provider.module_id is not None:
            topic += "/modules/" + self._auth_provider.module_id

        topic += "/messages/events/"
        return topic

    def connect(self):
        self._trig_connect()

    def disconnect(self):
        self._trig_disconnect()

    def send_event(self, message):
        self._trig_send_event(message)
