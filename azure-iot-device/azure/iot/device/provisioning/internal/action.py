# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------


class Action(object):
    """
    Base class representing various actions that can be taken
    when the state_based_provider is connected.  When the PipelineAdapter user
    calls a function that requires the state_based_provider to be connected,
    a StateBasedProviderAction object is created and added to the action
    queue.  Then, when the state_based_provider is actually connected, it
    loops through the objects in the action queue and executes them
    one by one.
    """

    def __init__(self, callback):
        self.callback = callback


class PublishAction(Action):
    """
    StateBasedProviderAction object used to publish
    """

    def __init__(self, publish_topic, message, callback):
        super(PublishAction, self).__init__(callback)
        self.publish_topic = publish_topic
        self.message = message


class SubscribeAction(Action):
    """
    StateBasedProviderAction object used to subscribe
    """

    def __init__(self, subscribe_topic, qos, callback):
        super(SubscribeAction, self).__init__(callback)
        self.subscribe_topic = subscribe_topic
        self.qos = qos


class UnsubscribeAction(Action):
    """
    StateBasedProviderAction object used to unsubscribe from a specific MQTT topic
    """

    def __init__(self, topic, callback):
        super(UnsubscribeAction, self).__init__(callback)
        self.unsubscribe_topic = topic
