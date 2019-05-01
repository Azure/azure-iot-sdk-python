# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
from .pipeline_events_base import PipelineEvent


class IncomingMessage(PipelineEvent):
    """
    A PipelineEvent object which represents an incoming Mqtt message on some Mqtt topic
    """

    def __init__(self, topic, payload):
        super(IncomingMessage, self).__init__()
        self.topic = topic
        self.payload = payload
