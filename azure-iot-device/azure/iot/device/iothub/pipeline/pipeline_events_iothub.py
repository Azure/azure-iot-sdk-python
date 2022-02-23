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
        super().__init__()
        self.message = message


class InputMessageEvent(PipelineEvent):
    """
    A PipelineEvent object which represents an incoming input message event.  This object is probably
    created by some converter stage based on a protocol-specific event
    """

    def __init__(self, message):
        """
        Initializer for InputMessageEvent objects.

        :param Message message: The Message object for the message that was received. This message
            is expected to have had the .input_name attribute set
        """
        super().__init__()
        self.message = message


class MethodRequestEvent(PipelineEvent):
    """
    A PipelineEvent object which represents an incoming MethodRequest event.
    This object is probably created by some converter stage based on a protocol-specific event.
    """

    def __init__(self, method_request):
        super().__init__()
        self.method_request = method_request


class TwinDesiredPropertiesPatchEvent(PipelineEvent):
    """
    A PipelineEvent object which represents an incoming twin desired properties patch.  This
    object is probably created by some converter stage based on a protocol-specific event.
    """

    def __init__(self, patch):
        super().__init__()
        self.patch = patch
