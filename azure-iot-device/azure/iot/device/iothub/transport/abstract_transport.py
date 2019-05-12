# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import abc
import six
from . import constant


@six.add_metaclass(abc.ABCMeta)
class AbstractTransport:
    """
    All specific transport will follow implementations of this abstract class.
    """

    def __init__(self, auth_provider):
        self._auth_provider = auth_provider
        self.feature_enabled = {
            constant.C2D_MSG: False,
            constant.INPUT_MSG: False,
            constant.METHODS: False,
        }

        # Event Handlers - Will be set by Client after instantiation of Transport
        self.on_transport_connected = None
        self.on_transport_disconnected = None
        self.on_transport_c2d_message_received = None
        self.on_transport_input_message_received = None
        self.on_transport_method_request_received = None

    @abc.abstractmethod
    def connect(self, callback):
        """
        Connect to the specific messaging system used by the specific transport protocol
        """
        pass

    @abc.abstractmethod
    def disconnect(self, callback):
        """
        Disconnect from the specific messaging system used by the specific transport protocol
        """
        pass

    @abc.abstractmethod
    def enable_feature(self, feature_name, callback=None):
        """
        Enable a specific feature (c2d, input, etc.)
        """
        pass

    @abc.abstractmethod
    def disable_feature(self, feature_name, callback=None):
        """
        Disable a specific feature (c2d, input, etc.)
        """
        pass

    @abc.abstractmethod
    def send_event(self, event, callback):
        """
        Send some telemetry, event or message.
        """
        pass

    @abc.abstractmethod
    def send_output_event(self, event, callback):
        """
        Send some event or message to a specific output
        """
        pass

    @abc.abstractmethod
    def send_method_response(self, method_response, callback=None):
        """
        Send a method response.
        """
        pass
