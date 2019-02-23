# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------
import abc
import six


@six.add_metaclass(abc.ABCMeta)
class AbstractTransport:
    """
    All specific transport will follow implementations of this abstract class.
    """

    def __init__(self, auth_provider):
        self._auth_provider = auth_provider

    @abc.abstractmethod
    def connect(self, callback):
        """
        Connect to the specific messaging system used by the specific transport protocol
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
    def disconnect(self, callback):
        """
        Disconnect from the specific messaging system used by the specific transport protocol
        """
        pass

    @abc.abstractmethod
    def enable_feature(self, feature_name, callback=None, qos=1):
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
