# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

import logging
import six.moves.queue as queue
from pprint import pprint
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
        self._event_callback_map = {}
        self._connect_callback = None
        self._disconnect_callback = None

        states = ["disconnected", "connecting", "connected", "disconnecting"]

        transitions = [
            {
                "trigger": "_trig_connect",
                "source": "disconnected",
                "dest": "connecting",
                "after": "_call_provider_connect",
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
                "after": "_publish_events_in_queue",
            },
            {"trigger": "_trig_disconnect", "source": "disconnected", "dest": None},
            {
                "trigger": "_trig_disconnect",
                "source": "connected",
                "dest": "disconnecting",
                "after": "_call_provider_disconnect",
            },
            {
                "trigger": "_trig_provider_disconnect_complete",
                "source": "disconnecting",
                "dest": "disconnected",
            },
            {
                "trigger": "_trig_send_event",
                "source": "connected",
                "before": "_add_event_to_queue",
                "dest": None,
                "after": "_publish_events_in_queue",
            },
            {
                "trigger": "_trig_send_event",
                "source": "connecting",
                "before": "_add_event_to_queue",
                "dest": None,
            },
            {
                "trigger": "_trig_send_event",
                "source": "disconnected",
                "before": "_add_event_to_queue",
                "dest": "connecting",
                "after": "_call_provider_connect",
            },
        ]

        def _on_transition_complete(event_data):
            if not event_data.transition:
                dest = "[no transition]"
            else:
                dest = event_data.transition.dest
            logger.info(
                "Transition complete.  Trigger=%s, Dest=%s, result=%s, error=%s",
                event_data.event.name,
                dest,
                str(event_data.result),
                str(event_data.error),
            )

        self._state_machine = Machine(
            model=self,
            states=states,
            transitions=transitions,
            initial="disconnected",
            send_event=True,  # This has nothing to do with telemetry events.  This tells the machine use event_data structures to hold transition arguments
            finalize_event=_on_transition_complete,
            queued=True,
        )

        # to render the state machine as a PNG:
        # 1. apt install graphviz
        # 2. pip install pygraphviz
        # 3. change import line at top of this file to import LockedGraphMachine as Machine
        # 4. uncomment the following line
        # 5. run this code
        # self.get_graph().draw('mqtt_transport.png', prog='dot')

        self._create_mqtt_provider()

    def _call_provider_connect(self, event_data):
        """
        Call into the provider to connect the transport.
        This is meant to be called by the state machine as part of a state transition
        """
        logger.info("Calling provider connect")
        self._mqtt_provider.connect()

    def _call_provider_disconnect(self, event_data):
        """
        Call into the provider to disconnect the transport.
        This is meant to be called by the state machine as part of a state transition
        """
        logger.info("Calling provider disconnect")
        self._mqtt_provider.disconnect()

    def _on_provider_connect_complete(self):
        """
        Callback that is called by the provider when the connection has been established
        """
        logger.info("_on_provider_connect_complete")
        self._trig_provider_connect_complete()

        if self.on_transport_connected:
            self.on_transport_connected("connected")
        callback = self._connect_callback
        if callback:
            self._connect_callback = None
            callback()

    def _on_provider_disconnect_complete(self):
        """
        Callback that is called by the provider when the connection has been disconnected
        """
        logger.info("_on_provider_disconnect_complete")
        self._trig_provider_disconnect_complete()

        if self.on_transport_disconnected:
            self.on_transport_disconnected("disconnected")
        callback = self._disconnect_callback
        if callback:
            self._disconnect_callback = None
            callback()

    def _on_provider_publish_complete(self, mid):
        """
        Callback that is called by the provider when a publish operation is complete.
        """
        if self.on_event_sent:
            self.on_event_sent()
        if mid in self._event_callback_map:
            callback = self._event_callback_map[mid]
            del self._event_callback_map[mid]
            callback()

    def _add_event_to_queue(self, event_data):
        """
        Queue an event for sending later.  All events that get sent end up going into
        this queue, even if they're going to be sent immediately.
        """
        logger.info("Adding event to queue for later sending")
        # TODO: throw here if event_data.args[0] is not an event/message
        self._event_queue.put_nowait((event_data.args[0], event_data.args[1]))

    def _publish_events_in_queue(self, event_data):
        """
        Publish any events that are waiting in the event queue.  This function
        actually calls down into the provider to publish the events.  For each
        event that is published, it saves the message id (mid) and the callback
        that needs to be called when the result of the publish operation is i
        available.
        """
        logger.info("checking event queue")
        while True:
            try:
                (event_to_send, callback) = self._event_queue.get_nowait()
            except queue.Empty:
                logger.info("done checking queue")
                return
            logger.info("retrieved event from queue. publishing.")
            topic = self._get_telemetry_topic()
            mid = self._mqtt_provider.publish(topic, event_to_send)
            self._event_callback_map[mid] = callback

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

        self._mqtt_provider.on_mqtt_connected = self._on_provider_connect_complete
        self._mqtt_provider.on_mqtt_disconnected = self._on_provider_disconnect_complete
        self._mqtt_provider.on_mqtt_published = self._on_provider_publish_complete

    def _get_telemetry_topic(self):
        topic = "devices/" + self._auth_provider.device_id

        if self._auth_provider.module_id is not None:
            topic += "/modules/" + self._auth_provider.module_id

        topic += "/messages/events/"
        return topic

    def connect(self, callback=None):
        self._connect_callback = callback
        self._trig_connect()

    def disconnect(self, callback=None):
        self._disconnect_callback = callback
        self._trig_disconnect()

    def send_event(self, message, callback=None):
        self._trig_send_event(message, callback)
