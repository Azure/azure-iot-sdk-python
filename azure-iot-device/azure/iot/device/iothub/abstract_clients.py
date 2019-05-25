# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module contains abstract classes for the various clients of the Azure IoT Hub Device SDK
"""

import six
import abc
import logging
from .pipeline import PipelineAdapter

logger = logging.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class AbstractIoTHubClient(object):
    """A superclass representing a generic client. This class needs to be extended for specific clients."""

    def __init__(self, pipeline):
        """Initializer for a generic client.

        :param pipeline: The pipeline that the client will use.
        """
        self._pipeline = pipeline

    @classmethod
    def from_authentication_provider(cls, authentication_provider, transport_name):
        """Creates a client with the specified authentication provider and pipeline.

        When creating the client, you need to pass in an authorization provider and a transport_name.

        The authentication_provider parameter is an object created using the authentication_provider_factory
        module.  It knows where to connect (a network address), how to authenticate with the service
        (a set of credentials), and, if necessary, the protocol gateway to use when communicating
        with the service.

        The transport_name is a string which defines the name of the transport to use when connecting
        with the service or the protocol gateway.

        Currently "mqtt" is the only supported transport.

        :param authentication_provider: The authentication provider.
        :param transport_name: The name of the transport that the client will use.

        :returns: Instance of the client.

        :raises: ValueError if given an invalid transport_name.
        :raises: NotImplementedError if transport_name is "amqp" or "http".
        """
        transport_name = transport_name.lower()
        if transport_name == "mqtt":
            pipeline = PipelineAdapter(authentication_provider)
        elif transport_name == "amqp" or transport_name == "http":
            raise NotImplementedError("This transport has not yet been implemented")
        else:
            raise ValueError("No specific transport can be instantiated based on the choice.")
        return cls(pipeline)

    @abc.abstractmethod
    def connect(self):
        pass

    @abc.abstractmethod
    def disconnect(self):
        pass

    @abc.abstractmethod
    def send_event(self, message):
        pass

    @abc.abstractmethod
    def receive_method_request(self, method_name=None):
        pass

    @abc.abstractmethod
    def send_method_response(self, method_request, payload, status):
        pass


@six.add_metaclass(abc.ABCMeta)
class AbstractIoTHubDeviceClient(AbstractIoTHubClient):
    @abc.abstractmethod
    def receive_c2d_message(self):
        pass


@six.add_metaclass(abc.ABCMeta)
class AbstractIoTHubModuleClient(AbstractIoTHubClient):
    @abc.abstractmethod
    def send_to_output(self, message, output_name):
        pass

    @abc.abstractmethod
    def receive_input_message(self, input_name):
        pass
