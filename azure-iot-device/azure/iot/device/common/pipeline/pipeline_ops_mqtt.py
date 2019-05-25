# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
from . import PipelineOperation


class SetConnectionArgs(PipelineOperation):
    """
    A PipelineOperation object which contains arguments used to connect to a server using the MQTT protocol.

    This operation is in the group of MQTT operations because its attributes are very specific to the MQTT protocol.
    """

    def __init__(self, client_id, hostname, username, ca_cert=None, callback=None):
        """
        Initializer for SetConnectionArgs objects.

        :param str client_id: The client identifier to use when connecting to the MQTT server
        :param str hostname: The hostname of the MQTT server we will eventually connect to
        :param str username: The username to use when connecting to the MQTT server
        :param str ca_cert: (Optional) The CA certificate to use if the MQTT server that we're going to
          connect to uses server-side TLS
        :param Function callback: The function that gets called when this operation is complete or has failed.
          The callback function must accept A PipelineOperation object which indicates the specific operation which
          has completed or failed.
        """
        super(SetConnectionArgs, self).__init__(callback=callback)
        self.client_id = client_id
        self.hostname = hostname
        self.username = username
        self.ca_cert = ca_cert

    pass


class Publish(PipelineOperation):
    """
    A PipelineOperation object which contains arguments used to publish a specific payload on a specific topic using the MQTT protocol.

    This operation is in the group of MQTT operations because its attributes are very specific to the MQTT protocol.
    """

    def __init__(self, topic, payload, callback=None):
        """
        Initializer for Publish objects.

        :param str topic: The name of the topic to publish to
        :param str payload: The payload to publish
        :param Function callback: The function that gets called when this operation is complete or has failed.
          The callback function must accept A PipelineOperation object which indicates the specific operation which
          has completed or failed.
        """
        super(Publish, self).__init__(callback=callback)
        self.topic = topic
        self.payload = payload


class Subscribe(PipelineOperation):
    """
    A PipelineOperation object which contains arguments used to subscribe to a specific MQTT topic using the MQTT protocol.

    This operation is in the group of MQTT operations because its attributes are very specific to the MQTT protocol.
    """

    def __init__(self, topic, callback=None):
        """
        Initializer for Subscribe objects.

        :param str topic: The name of the topic to subscribe to
        :param Function callback: The function that gets called when this operation is complete or has failed.
          The callback function must accept A PipelineOperation object which indicates the specific operation which
          has completed or failed.
        """
        super(Subscribe, self).__init__(callback=callback)
        self.topic = topic


class Unsubscribe(PipelineOperation):
    """
    A PipelineOperation object which contains arguments used to unsubscribe from a specific MQTT topic using the MQTT protocol.

    This operation is in the group of MQTT operations because its attributes are very specific to the MQTT protocol.
    """

    def __init__(self, topic, callback=None):
        """
        Initializer for Unsubscribe objects.

        :param str topic: The name of the topic to unsubscribe from
        :param Function callback: The function that gets called when this operation is complete or has failed.
          The callback function must accept A PipelineOperation object which indicates the specific operation which
          has completed or failed.
        """
        super(Unsubscribe, self).__init__(callback=callback)
        self.topic = topic
