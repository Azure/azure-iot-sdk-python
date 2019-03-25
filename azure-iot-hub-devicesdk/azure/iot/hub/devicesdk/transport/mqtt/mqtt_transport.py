# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging
from datetime import date
import six.moves.urllib as urllib
import six.moves.queue as queue
from .mqtt_provider import MQTTProvider
from transitions import Machine
from azure.iot.hub.devicesdk.transport.abstract_transport import AbstractTransport
from azure.iot.hub.devicesdk.transport import constant
from azure.iot.hub.devicesdk.common import Message


"""
The below import is for generating the state machine graph.
"""
# from transitions.extensions import LockedGraphMachine as Machine

logger = logging.getLogger(__name__)

"""
A note on names, design, and code flow:

This transport is a state machine which is responsible for coordinating
several different things.  (I would like to say that it coordinates several
events, but the word "event" is very overloaded, especially in this context,
so I hesitate to add one more overload).

In particular, it needs to coordinate external things:
    1. Things the caller wants to do, such as "connect", "send message", etc.
    2. Calls into the transport provider
    3. Completion callbacks from the transport provider.
    4. Completion callbacks from this object into the caller.

and also internal things:
    5. The "state" of transport (connected, disconnected, etc).
    6. Transitions between possible states.

Since one caller-initiated action results in many different things happening, this
class uses the following conventions:

1. Actions that the caller can initiate are all named without an underscore at the beginning,
    such as "connect", "send_message", etc.

2. All internal functions are prefixed with an underscore.  This is "the pythonic way", but it bears repeating.
    Internal functions are internal and should be called by external code.

2. Actions will typically trigger a state machine event.  State machine triggers, wihch may
    or may not change state, are all prefixed with _trig_ (_trig_connect, _trig_add_pending_action_to_queue, etc)
    The "_trig" indicates that this is a operation on the state machine.  _trig_* functions are also unusual in
    that they get added to the transport object at runtime when intiializing the Machine object.

3. Functions which call into the provider are prefixed with "_call_provider_", such as _call_provider_connect.
    These are always called as part of state machine transitions.  Calls from the caller should not go directly into the
    provider without going through the state machine.

4. When the provider completes an action or receives an acknowledgement, it will call back into this object using
    functions which are all prefixed with "_on_provider_", such as "_on_provider_connect_complete".  These callback functions
    will, most of the time, trigger additional state machine transitions by calling _trig_ functions.

5. Functions which are called by the state machine as side-effects of state transitions will accept event_data objects
    as the second parameter (after self).  The event_data structure contains information about the trigger or the transition
    which caused the side-effect.

6. Callbacks from this object into caller code, when not passed in as `callback` parameters to function calls, are prefixed with
    on_ (with no underscore), such as "on_transport_connected'.  Because most callbacks are passed in as function parameters,
    there are very few callbacks like this.

"""


TOPIC_POS_DEVICE = 4
TOPIC_POS_MODULE = 6
TOPIC_POS_INPUT_NAME = 5


class TransportAction(object):
    """
    base class representing various actions that can be taken
    when the transport is connected.  When the MqttTransport user
    calls a function that requires the transport to be connected,
    a TransportAction object is created and added to the action
    queue.  Then, when the transport is actually connected, it
    loops through the objects in the action queue and executes them
    one by one.
    """

    def __init__(self, callback):
        self.callback = callback


class SendMessageAction(TransportAction):
    """
    TransportAction object used to send a telemetry message or an
    output message
    """

    def __init__(self, message, callback):
        TransportAction.__init__(self, callback)
        self.message = message


class SubscribeAction(TransportAction):
    """
    TransportAction object used to subscribe to a specific MQTT topic
    """

    def __init__(self, topic, qos, callback):
        TransportAction.__init__(self, callback)
        self.topic = topic
        self.qos = qos


class UnsubscribeAction(TransportAction):
    """
    TransportAction object used to unsubscribe from a specific MQTT topic
    """

    def __init__(self, topic, callback):
        TransportAction.__init__(self, callback)
        self.topic = topic


class MethodReponseAction(TransportAction):
    """
    TransportAction object used to send a method response back to the service.
    """

    def __init__(self, method_response, callback):
        TransportAction.__init__(self, callback)
        self.method_response = method_response


class MQTTTransport(AbstractTransport):
    def __init__(self, auth_provider):
        """
        Constructor for instantiating a transport
        :param auth_provider: The authentication provider
        """
        AbstractTransport.__init__(self, auth_provider)
        self.topic = self._get_telemetry_topic_for_publish()
        self._mqtt_provider = None

        # Queue of actions that will be executed once the transport is connected.
        # Currently, we use a queue, which is FIFO, but the actual order doesn't matter
        # since each action stands on its own.
        self._pending_action_queue = queue.Queue()

        # Object which maps mid->callback for actions which are in flight.  This is
        # used to call back into the caller to indicate that an action is complete.
        self._in_progress_actions = {}

        # Map of responses we receive with a MID that is not in the _in_progress_actions map.
        # We need this because sometimes a SUBSCRIBE or a PUBLISH will complete before the call
        # to subscribe() or publish() returns.
        self._responses_with_unknown_mid = {}

        self._connect_callback = None
        self._disconnect_callback = None

        self._c2d_topic = None
        self._input_topic = None

        states = ["disconnected", "connecting", "connected", "disconnecting"]

        transitions = [
            {
                "trigger": "_trig_connect",
                "source": "disconnected",
                "dest": "connecting",
                "after": "_call_provider_connect",
            },
            {"trigger": "_trig_connect", "source": ["connecting", "connected"], "dest": None},
            {
                "trigger": "_trig_provider_connect_complete",
                "source": "connecting",
                "dest": "connected",
                "after": "_execute_actions_in_queue",
            },
            {
                "trigger": "_trig_disconnect",
                "source": ["disconnected", "disconnecting"],
                "dest": None,
            },
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
                "trigger": "_trig_add_action_to_pending_queue",
                "source": "connected",
                "before": "_add_action_to_queue",
                "dest": None,
                "after": "_execute_actions_in_queue",
            },
            {
                "trigger": "_trig_add_action_to_pending_queue",
                "source": "connecting",
                "before": "_add_action_to_queue",
                "dest": None,
            },
            {
                "trigger": "_trig_add_action_to_pending_queue",
                "source": "disconnected",
                "before": "_add_action_to_queue",
                "dest": "connecting",
                "after": "_call_provider_connect",
            },
            {
                "trigger": "_trig_on_shared_access_string_updated",
                "source": "connected",
                "dest": "connecting",
                "after": "_call_provider_reconnect",
            },
            {
                "trigger": "_trig_on_shared_access_string_updated",
                "source": ["disconnected", "disconnecting"],
                "dest": None,
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

        This is called by the state machine as part of a state transition

        :param EventData event_data:  Object created by the Transitions library with information about the state transition
        """
        logger.info("Calling provider connect")
        password = self._auth_provider.get_current_sas_token()
        self._mqtt_provider.connect(password)

        if hasattr(self._auth_provider, "token_update_callback"):
            self._auth_provider.token_update_callback = self._on_shared_access_string_updated

    def _call_provider_disconnect(self, event_data):
        """
        Call into the provider to disconnect the transport.

        This is called by the state machine as part of a state transition

        :param EventData event_data:  Object created by the Transitions library with information about the state transition
        """
        logger.info("Calling provider disconnect")
        self._mqtt_provider.disconnect()
        self._auth_provider.disconnect()

    def _call_provider_reconnect(self, event_data):
        """
        Call into the provider to reconnect the transport.

        This is called by the state machine as part of a state transition

        :param EventData event_data:  Object created by the Transitions library with information about the state transition
        """
        password = self._auth_provider.get_current_sas_token()
        self._mqtt_provider.reconnect(password)

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
        Callback that is called by the provider when it receives a PUBACK from the service

        :param mid: message id that was returned by the provider when `publish` was called.  This is used to tie the
            PUBLISH to the PUBACK.
        """
        if mid in self._in_progress_actions:
            callback = self._in_progress_actions[mid]
            del self._in_progress_actions[mid]
            callback()
        else:
            logger.warning("PUBACK received with unknown MID: %s", str(mid))
            self._responses_with_unknown_mid[
                mid
            ] = mid  # storing MID for now.  will probably store result code later.

    def _on_provider_subscribe_complete(self, mid):
        """
        Callback that is called by the provider when it receives a SUBACK from the service

        :param mid: message id that was returned by the provider when `subscribe` was called.  This is used to tie the
            SUBSCRIBE to the SUBACK.
        """
        if mid in self._in_progress_actions:
            callback = self._in_progress_actions[mid]
            del self._in_progress_actions[mid]
            callback()
        else:
            logger.warning("SUBACK received with unknown MID: %s", str(mid))
            self._responses_with_unknown_mid[
                mid
            ] = mid  # storing MID for now.  will probably store result code later.

    def _on_provider_message_received_callback(self, topic, payload):
        """
        Callback that is called by the provider when a message is received.  This message can be any MQTT message,
        including, but not limited to, a C2D message, an input message, a TWIN patch, a twin response (/res), and
        a method invocation.  This function needs to decide what kind of message it is based on the topic name and
        take the correct action.

        :param topic: MQTT topic name that the message arrived on
        :param payload: Payload of the message
        """
        logger.info("Message received on topic %s", topic)
        message_received = Message(payload)
        # TODO : Discuss everything in bytes , need to be changed, specially the topic
        topic_str = topic.decode("utf-8")
        topic_parts = topic_str.split("/")

        if _is_input_topic(topic_str):
            input_name = topic_parts[TOPIC_POS_INPUT_NAME]
            message_received.input_name = input_name
            _extract_properties(topic_parts[TOPIC_POS_MODULE], message_received)
            self.on_transport_input_message_received(input_name, message_received)
        elif _is_c2d_topic(topic_str):
            _extract_properties(topic_parts[TOPIC_POS_DEVICE], message_received)
            self.on_transport_c2d_message_received(message_received)
        else:
            pass  # is there any other case

    def _on_provider_unsubscribe_complete(self, mid):
        """
        Callback that is called by the provider when it receives an UNSUBACK from the service

        :param mid: message id that was returned by the provider when `unsubscribe` was called.  This is used to tie the
            UNSUBSCRIBE to the UNSUBACK.
        """
        if mid in self._in_progress_actions:
            callback = self._in_progress_actions[mid]
            del self._in_progress_actions[mid]
            callback()
        else:
            logger.warning("UNSUBACK received with unknown MID: %s", str(mid))
            self._responses_with_unknown_mid[
                mid
            ] = mid  # storing MID for now.  will probably store result code later.

    def _add_action_to_queue(self, event_data):
        """
        Queue an action for running later.  All actions that need to run while connected end up in
        this queue, even if they're going to be run immediately.

        This is called by the state machine as part of a state transition

        :param EventData event_data:  Object created by the Transitions library with information about the state transition
        """
        self._pending_action_queue.put_nowait(event_data.args[0])

    def _execute_action(self, action):
        """
        Execute an action from the action queue.  This is called when the transport is connected and the
        state machine is able to execute individual actions.

        :param TransportAction action: object containing the details of the action to be executed
        """

        if isinstance(action, SendMessageAction):
            logger.info("running SendMessageAction")
            message_to_send = action.message
            encoded_topic = _encode_properties(
                message_to_send, self._get_telemetry_topic_for_publish()
            )
            mid = self._mqtt_provider.publish(encoded_topic, message_to_send.data)
            if mid in self._responses_with_unknown_mid:
                del self._responses_with_unknown_mid[mid]
                action.callback()
            else:
                self._in_progress_actions[mid] = action.callback

        elif isinstance(action, SubscribeAction):
            logger.info("running SubscribeAction topic=%s qos=%s", action.topic, action.qos)
            mid = self._mqtt_provider.subscribe(action.topic, action.qos)
            logger.info("subscribe mid = %s", mid)
            if mid in self._responses_with_unknown_mid:
                del self._responses_with_unknown_mid[mid]
                action.callback()
            else:
                self._in_progress_actions[mid] = action.callback

        elif isinstance(action, UnsubscribeAction):
            logger.info("running UnsubscribeAction")
            mid = self._mqtt_provider.unsubscribe(action.topic)
            if mid in self._responses_with_unknown_mid:
                del self._responses_with_unknown_mid[mid]
                action.callback()
            else:
                self._in_progress_actions[mid] = action.callback

        elif isinstance(action, MethodReponseAction):
            logger.info("running MethodResponseAction")
            topic = "TODO"
            mid = self._mqtt_provider.publish(topic, action.method_response)
            if mid in self._responses_with_unknown_mid:
                del self._responses_with_unknown_mid[mid]
                action.callback()
            else:
                self._in_progress_actions[mid] = action.callback

        else:
            logger.error("Removed unknown action type from queue.")

    def _execute_actions_in_queue(self, event_data):
        """
        Execute any actions that are waiting in the action queue.
        This is called by the state machine as part of a state transition.
        This function actually calls down into the provider to perform the necessary operations.

        :param EventData event_data:  Object created by the Transitions library with information about the state transition
        """
        logger.info("checking _pending_action_queue")
        while True:
            try:
                action = self._pending_action_queue.get_nowait()
            except queue.Empty:
                logger.info("done checking queue")
                return

            self._execute_action(action)

    def _create_mqtt_provider(self):
        """
        Create the provider object which is used by this instance to communicate with the service.
        No network communication can take place without a provider object.
        """
        client_id = self._auth_provider.device_id

        if self._auth_provider.module_id:
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

        self._mqtt_provider = MQTTProvider(client_id, hostname, username, ca_cert=ca_cert)

        self._mqtt_provider.on_mqtt_connected = self._on_provider_connect_complete
        self._mqtt_provider.on_mqtt_disconnected = self._on_provider_disconnect_complete
        self._mqtt_provider.on_mqtt_published = self._on_provider_publish_complete
        self._mqtt_provider.on_mqtt_subscribed = self._on_provider_subscribe_complete
        self._mqtt_provider.on_mqtt_unsubscribed = self._on_provider_unsubscribe_complete
        self._mqtt_provider.on_mqtt_message_received = self._on_provider_message_received_callback

    def _get_topic_base(self):
        """
        return the string that is at the beginning of all topics for this
        device/module
        """

        if self._auth_provider.module_id:
            return (
                "devices/"
                + self._auth_provider.device_id
                + "/modules/"
                + self._auth_provider.module_id
            )
        else:
            return "devices/" + self._auth_provider.device_id

    def _get_telemetry_topic_for_publish(self):
        """
        return the topic string used to publish telemetry
        """
        return self._get_topic_base() + "/messages/events/"

    def _get_c2d_topic_for_subscribe(self):
        """
        :return: The topic for cloud to device messages.It is of the format
        "devices/<deviceid>/messages/devicebound/#"
        """
        return self._get_topic_base() + "/messages/devicebound/#"

    def _get_input_topic_for_subscribe(self):
        """
        :return: The topic for input messages. It is of the format
        "devices/<deviceId>/modules/<moduleId>/messages/inputs/#"
        """
        return self._get_topic_base() + "/inputs/#"

    def connect(self, callback=None):
        """
        Connect to the service.

        :param callback: callback which is called when the connection to the service is complete.
        """
        logger.info("connect called")
        self._connect_callback = callback
        self._trig_connect()

    def disconnect(self, callback=None):
        """
        Disconnect from the service.

        :param callback: callback which is called when the connection to the service has been disconnected
        """
        logger.info("disconnect called")
        self._disconnect_callback = callback
        self._trig_disconnect()

    def send_event(self, message, callback=None):
        """
        Send a telemetry message to the service.

        :param callback: callback which is called when the message publish has been acknowledged by the service.
        """
        action = SendMessageAction(message, callback)
        self._trig_add_action_to_pending_queue(action)

    def send_output_event(self, message, callback=None):
        """
        Send an output message to the service.

        :param callback: callback which is called when the message publish has been acknowledged by the service.
        """
        action = SendMessageAction(message, callback)
        self._trig_add_action_to_pending_queue(action)

    def send_method_response(self, method, payload, status, callback=None):
        raise NotImplementedError

    def _on_shared_access_string_updated(self):
        """
        Callback which is called by the authentication provider when the shared access string has been updated.
        """
        self._trig_on_shared_access_string_updated()

    def enable_feature(self, feature_name, callback=None):
        """
        Enable the given feature by subscribing to the appropriate topics.

        :param feature_name: one of the feature name constants from constant.py
        :param callback: callback which is called when the feature is enabled
        """
        logger.info("enable_feature %s called", feature_name)
        if feature_name == constant.INPUT_MSG:
            self._enable_input_messages(callback)
        elif feature_name == constant.C2D_MSG:
            self._enable_c2d_messages(callback)
        elif feature_name == constant.METHODS:
            self._enable_methods(callback)
        else:
            logger.error("Feature name {} is unknown".format(feature_name))
            raise ValueError("Invalid feature name")

    def disable_feature(self, feature_name, callback=None):
        """
        Disable the given feature by subscribing to the appropriate topics.
        :param callback: callback which is called when the feature is disabled

        :param feature_name: one of the feature name constants from constant.py
        """
        logger.info("disable_feature %s called", feature_name)
        if feature_name == constant.INPUT_MSG:
            self._disable_input_messages(callback)
        elif feature_name == constant.C2D_MSG:
            self._disable_c2d_messages(callback)
        elif feature_name == constant.METHODS:
            self._disable_methods(callback)
        else:
            logger.error("Feature name {} is unknown".format(feature_name))
            raise ValueError("Invalid feature name")

    def _enable_input_messages(self, callback=None):
        """
        Helper function to enable input messages

        :param callback: callback which is called when the feature is enabled
        """
        action = SubscribeAction(
            topic=self._get_input_topic_for_subscribe(), qos=1, callback=callback
        )
        self._trig_add_action_to_pending_queue(action)
        self.feature_enabled[constant.INPUT_MSG] = True

    def _disable_input_messages(self, callback=None):
        """
        Helper function to disable input messages

        :param callback: callback which is called when the feature is disabled
        """
        action = UnsubscribeAction(topic=self._get_input_topic_for_subscribe(), callback=callback)
        self._trig_add_action_to_pending_queue(action)
        self.feature_enabled[constant.INPUT_MSG] = False

    def _enable_c2d_messages(self, callback=None):
        """
        Helper function to enable c2de messages

        :param callback: callback which is called when the feature is enabled
        """
        action = SubscribeAction(
            topic=self._get_c2d_topic_for_subscribe(), qos=1, callback=callback
        )
        self._trig_add_action_to_pending_queue(action)
        self.feature_enabled[constant.C2D_MSG] = True

    def _disable_c2d_messages(self, callback=None):
        """
        Helper function to disabled c2d messages

        :param callback: callback which is called when the feature is disabled
        """
        action = UnsubscribeAction(topic=self._get_c2d_topic_for_subscribe(), callback=callback)
        self._trig_add_action_to_pending_queue(action)
        self.feature_enabled[constant.C2D_MSG] = False

    def _enable_methods(self, callback=None, qos=1):
        """
        Helper function to enable methods

        :param callback: callback which is called when the feature is enabled.
        :param qos: Quality of Serivce level
        """
        action = SubscribeAction(self._get_method_topic_for_subscribe(), qos, callback)
        self._trig_add_action_to_pending_queue(action)
        self.feature_enabled[constant.METHODS] = True

    def _disable_methods(self, callback=None):
        """
        Helper function to disable methods

        :param callback: callback which is called when the feature is disabled
        """
        action = UnsubscribeAction(self._get_method_topic_for_subscribe(), callback)
        self._trig_add_action_to_pending_queue(action)
        self.feature_enabled[constant.METHODS] = False


def _is_c2d_topic(split_topic_str):
    """
    Topics for c2d message are of the following format:
    devices/<deviceId>/messages/devicebound
    :param split_topic_str: The already split received topic string
    """
    if "messages/devicebound" in split_topic_str and len(split_topic_str) > 4:
        return True
    return False


def _is_input_topic(split_topic_str):
    """
    Topics for inputs are of the following format:
    devices/<deviceId>/modules/<moduleId>/messages/inputs/<inputName>
    :param split_topic_str: The already split received topic string
    """
    if "inputs" in split_topic_str and len(split_topic_str) > 6:
        return True
    return False


def _extract_properties(properties, message_received):
    """
    Extract key=value pairs from custom properties and set the properties on the received message.
    :param properties: The properties string which is ampersand(&) delimited key=value pair.
    :param message_received: The message received with the payload in bytes
    """
    key_value_pairs = properties.split("&")

    for entry in key_value_pairs:
        pair = entry.split("=")
        key = urllib.parse.unquote_plus(pair[0])
        value = urllib.parse.unquote_plus(pair[1])

        if key == "$.mid":
            message_received.message_id = value
        elif key == "$.cid":
            message_received.correlation_id = value
        elif key == "$.uid":
            message_received.user_id = value
        elif key == "$.to":
            message_received.to = value
        elif key == "$.ct":
            message_received.content_type = value
        elif key == "$.ce":
            message_received.content_encoding = value
        else:
            message_received.custom_properties[key] = value


def _encode_properties(message_to_send, topic):
    """
    uri-encode the system properties of a message as key-value pairs on the topic with defined keys.
    Additionally if the message has user defined properties, the property keys and values shall be
    uri-encoded and appended at the end of the above topic with the following convention:
    '<key>=<value>&<key2>=<value2>&<key3>=<value3>(...)'
    :param message_to_send: The message to send
    :param topic: The topic which has not been encoded yet. For a device it looks like
    "devices/<deviceId>/messages/events/" and for a module it looks like
    "devices/<deviceId>/modules/<moduleId>/messages/events/
    :return: The topic which has been uri-encoded
    """
    system_properties = {}
    if message_to_send.output_name:
        system_properties["$.on"] = message_to_send.output_name
    if message_to_send.message_id:
        system_properties["$.mid"] = message_to_send.message_id

    if message_to_send.correlation_id:
        system_properties["$.cid"] = message_to_send.correlation_id

    if message_to_send.user_id:
        system_properties["$.uid"] = message_to_send.user_id

    if message_to_send.to:
        system_properties["$.to"] = message_to_send.to

    if message_to_send.content_type:
        system_properties["$.ct"] = message_to_send.content_type

    if message_to_send.content_encoding:
        system_properties["$.ce"] = message_to_send.content_encoding

    if message_to_send.expiry_time_utc:
        system_properties["$.exp"] = (
            message_to_send.expiry_time_utc.isoformat()
            if isinstance(message_to_send.expiry_time_utc, date)
            else message_to_send.expiry_time_utc
        )

    system_properties_encoded = urllib.parse.urlencode(system_properties)
    topic += system_properties_encoded

    if message_to_send.custom_properties and len(message_to_send.custom_properties) > 0:
        topic += "&"
        user_properties_encoded = urllib.parse.urlencode(message_to_send.custom_properties)
        topic += user_properties_encoded

    return topic
