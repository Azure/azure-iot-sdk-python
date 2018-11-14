# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

import types
import logging
import six.moves.queue as queue
from .mqtt_provider import MQTTProvider
#from transitions.extensions import LockedGraphMachine as Machine
from transitions.extensions import LockedMachine as Machine

logger = logging.getLogger(__name__)


class MQTTTransport(Machine):
    def __init__(self, auth_provider):
        """
        Constructor for instantiating a transport
        :param auth_provider: The authentication provider
        """
        self._auth_provider = auth_provider
        self._mqtt_provider = None
        self.on_transport_connected = None
        self._event_queue = queue.LifoQueue()

        states = [
            "disconnected",
            "connecting",
            "connected",
            "sending",
            "disconnecting",
        ]

        transitions = [
            {
                "trigger": "connect",
                "source": "disconnected",
                "dest": "connecting",
                "after": "_after_action_provider_connect",
            },
            {
                "trigger": "connect",
                "source": ["connecting", "connected", "sending"],
                "dest": None,
            },
            {
                "trigger": "_provider_connect_complete",
                "source": "connecting",
                "dest": "connected",
                "after": "_after_action_deliver_next_queued_event",
            },
            {"trigger": "disconnect", "source": "disconnected", "dest": None},
            {
                "trigger": "disconnect",
                "source": "connected",
                "dest": "disconnecting",
                "after": "_after_action_provider_disconnect",
            },
            {
                "trigger": "_provider_disconnect_complete",
                "source": "disconnecting",
                "dest": "disconnected",
            },
            {
                "trigger": "send_event",
                "source": "connected",
                "before": "_before_action_add_event_to_queue",
                "dest": "sending",
                "after": "_after_action_deliver_next_queued_event",
            },
            {
                "trigger": "_provider_publish_complete",
                "source": "sending",
                "dest": None,
                "unless": "_queue_is_empty",
                "after": "_after_action_deliver_next_queued_event",
            },
            {
                "trigger": "_provider_publish_complete",
                "source": "sending",
                "dest": "connected",
                "conditions": "_queue_is_empty"
            },
            {
                "trigger": "send_event",
                "source": ["connecting", "sending"],
                "before": "_before_action_add_event_to_queue",
                "dest": None
            },
            {
                "trigger": "send_event",
                "source": "disconnected",
                "before": "_before_action_add_event_to_queue",
                "dest": "connecting",
                "after": "_after_action_provider_connect",
            },
        ]

        def on_transition_complete(event):
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

        Machine.__init__(
            self,
            states=states,
            transitions=transitions,
            initial="disconnected",
            send_event=True,
            finalize_event=on_transition_complete,
            after_state_change=self._after_state_change
        )
    
        # to render the state machine as a PNG:
        # 1. apt insatll graphviz 
        # 2. pip install pygraphviz
        # 3. change import line at top of this file to import LockedGraphMachine as Machine
        # 4. uncomment the following line
        # 5. run this code
        # self.get_graph().draw('mqtt_transport.png', prog='dot')

        self._create_mqtt_provider()

    def _after_state_change(self, event):
        """
        Callback that happens after all state changes.  Since there are many different 
        ways to get to the connected state, this is where we call our "on_connected" callback.
        (This would be better done inside a handler attached to the _provider_connect_complete event,
        but no such thing exists).
        """
        logger.info("after state change: trigger=%s, dest=%s, error=%s", event.event.name, event.state.name, str(event.error))
        if (not event.error) and (event.event.name == "_provider_connect_complete") and self.on_transport_connected:
            self.on_transport_connected(event.state.name)

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
            pass

    def _create_mqtt_provider(self):
        client_id = self._auth_provider.device_id

        if self._auth_provider.module_id is not None:
            client_id += "/" + self._auth_provider.module_id

        username = (
            self._auth_provider.hostname
            + "/"
            + client_id
            + "/"
            + "?api-version=2018-06-30"
        )

        if hasattr(self._auth_provider, "gateway_hostname"):
            hostname = self._auth_provider.gateway_hostname
        else:
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

        self._mqtt_provider.on_mqtt_connected = self._provider_connect_complete
        self._mqtt_provider.on_mqtt_disconnected = self._provider_disconnect_complete
        self._mqtt_provider.on_mqtt_published = self._provider_publish_complete

    def _get_telemetry_topic(self):
        topic = "devices/" + self._auth_provider.device_id

        if self._auth_provider.module_id is not None:
            topic += "/modules/" + self._auth_provider.module_id

        topic += "/messages/events/"
        return topic
