# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
from . import PipelineOperation


class MQTTPublishOperation(PipelineOperation):
    """
    A PipelineOperation object which contains arguments used to publish a specific payload on a specific topic using the MQTT protocol.

    This operation is in the group of MQTT operations because its attributes are very specific to the MQTT protocol.
    """

    def __init__(self, topic, payload, callback):
        """
        Initializer for MQTTPublishOperation objects.

        :param str topic: The name of the topic to publish to
        :param str payload: The payload to publish
        :param Function callback: The function that gets called when this operation is complete or has failed.
          The callback function must accept A PipelineOperation object which indicates the specific operation which
          has completed or failed.
        """
        super().__init__(callback=callback)
        self.topic = topic
        self.payload = payload
        self.needs_connection = True
        self.retry_timer = None


class MQTTSubscribeOperation(PipelineOperation):
    """
    A PipelineOperation object which contains arguments used to subscribe to a specific MQTT topic using the MQTT protocol.

    This operation is in the group of MQTT operations because its attributes are very specific to the MQTT protocol.
    """

    def __init__(self, topic, callback):
        """
        Initializer for MQTTSubscribeOperation objects.

        :param str topic: The name of the topic to subscribe to
        :param Function callback: The function that gets called when this operation is complete or has failed.
          The callback function must accept A PipelineOperation object which indicates the specific operation which
          has completed or failed.
        """
        super().__init__(callback=callback)
        self.topic = topic
        self.needs_connection = True
        self.timeout_timer = None
        self.retry_timer = None


class MQTTUnsubscribeOperation(PipelineOperation):
    """
    A PipelineOperation object which contains arguments used to unsubscribe from a specific MQTT topic using the MQTT protocol.

    This operation is in the group of MQTT operations because its attributes are very specific to the MQTT protocol.
    """

    def __init__(self, topic, callback):
        """
        Initializer for MQTTUnsubscribeOperation objects.

        :param str topic: The name of the topic to unsubscribe from
        :param Function callback: The function that gets called when this operation is complete or has failed.
          The callback function must accept A PipelineOperation object which indicates the specific operation which
          has completed or failed.
        """
        super().__init__(callback=callback)
        self.topic = topic
        self.needs_connection = True
        self.timeout_timer = None
        self.retry_timer = None
