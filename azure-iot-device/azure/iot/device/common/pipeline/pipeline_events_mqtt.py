# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
from . import PipelineEvent


class IncomingMQTTMessageEvent(PipelineEvent):
    """
    A PipelineEvent object which represents an incoming MQTT message on some MQTT topic
    """

    def __init__(self, topic, payload):
        """
        Initializer for IncomingMQTTMessageEvent objects.

        :param str topic: The name of the topic that the incoming message arrived on.
        :param str payload: The payload of the message
        """
        super(IncomingMQTTMessageEvent, self).__init__()
        self.topic = topic
        self.payload = payload
