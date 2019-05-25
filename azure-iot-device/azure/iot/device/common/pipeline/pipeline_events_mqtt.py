# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
from . import PipelineEvent


class IncomingMessage(PipelineEvent):
    """
    A PipelineEvent object which represents an incoming Mqtt message on some Mqtt topic
    """

    def __init__(self, topic, payload):
        """
        Initializer for IncomingMessage objects.

        :param str topic: The name of the topic that the incoming message arrived on.
        :param str payload: The payload of the message
        """
        super(IncomingMessage, self).__init__()
        self.topic = topic
        self.payload = payload
