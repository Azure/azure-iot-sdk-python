# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
from .pipeline_events_base import PipelineEvent


class C2DMessage(PipelineEvent):
    """
    A PipelineEvent object which represents an incoming C2D event.  This object is probably
    created by some converter stage based on a transport-specific event
    """

    def __init__(self, message):
        super(C2DMessage, self).__init__()
        self.message = message


class InputMessage(PipelineEvent):
    """
    A PipelineEvent object which represents an incoming InputMessage event.  This object is probably
    created by some converter stage based on a transport-specific event
    """

    def __init__(self, input_name, message):
        super(InputMessage, self).__init__()
        self.input_name = input_name
        self.message = message
