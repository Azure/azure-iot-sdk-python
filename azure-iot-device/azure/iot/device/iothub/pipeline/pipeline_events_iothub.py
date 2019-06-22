# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
from azure.iot.device.common.pipeline import PipelineEvent


class C2DMessageEvent(PipelineEvent):
    """
    A PipelineEvent object which represents an incoming C2D event.  This object is probably
    created by some converter stage based on a protocol-specific event
    """

    def __init__(self, message):
        """
        Initializer for C2DMessageEvent objects.

        :param Message message: The Message object for the message that was received.
        """
        super(C2DMessageEvent, self).__init__()
        self.message = message


class InputMessageEvent(PipelineEvent):
    """
    A PipelineEvent object which represents an incoming input message event.  This object is probably
    created by some converter stage based on a protocol-specific event
    """

    def __init__(self, input_name, message):
        """
        Initializer for InputMessageEvent objects.

        :param str input_name: The name of the input that this message arrived on.  This string is
          also stored in the input_name attribute on the message object
        :param Message message: The Message object for the message that was received.
        """
        super(InputMessageEvent, self).__init__()
        self.input_name = input_name
        self.message = message


class MethodRequestEvent(PipelineEvent):
    """
    A PipelineEvent object which represents an incoming MethodRequest event.
    This object is probably created by some converter stage based on a protocol-specific event.
    """

    def __init__(self, method_request):
        super(MethodRequestEvent, self).__init__()
        self.method_request = method_request


class TwinDesiredPropertiesPatchEvent(PipelineEvent):
    """
    A PipelineEvent object which represents an incoming twin desired properties patch.  This
    object is probably created by some converter stage based on a protocol-specific event.
    """

    def __init__(self, patch):
        super(TwinDesiredPropertiesPatchEvent, self).__init__()
        self.patch = patch
