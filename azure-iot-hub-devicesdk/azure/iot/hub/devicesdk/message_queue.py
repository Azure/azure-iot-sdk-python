# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module contains classes related to receiving messages.
"""

from six.moves import queue
import logging
from threading import Event
from azure.iot.hub.devicesdk.transport import constant

logger = logging.getLogger(__name__)


class MessageQueue(
    queue.Queue, object
):  # add object w/ multiple inheritance b/c queue.Queue is old style in Python 2.7 (no inheritance from object)
    """An extension of the Queue class, used to recieve Messages.

    :ivar bool enabled: Indicates whether or not this queue is enabled to receive messages.
    """

    def __init__(self, on_enable, on_disable):
        """Initializer for MessageQueue.

        :param on_enable: handler to be called when a queue is enabled.
        :param on_disable: handler to be called when a queue is disabled.
        """
        super(MessageQueue, self).__init__()
        self._enabled = False
        self._on_enable = on_enable
        self._on_disable = on_disable

    def enable(self):
        """Enable MessageQueue to receive messages if not already enabled."""
        if not self._enabled:
            self._on_enable()  # must do this before changing status!
            self._enabled = True

    def disable(self):
        """Disable MessageQueue from receiving messages if not already disabled."""
        if self._enabled:
            self._enabled = False
            self._on_disable()  # must do this after changing status!

    @property
    def enabled(self):
        """Boolean indicating if the MessageQueue is enabled."""
        return self._enabled

    @enabled.setter
    def enabled(self, value):
        """Set enabled status to True/False.

        :param bool value: The new value to be set.
        """
        if value:
            self.enable()
        else:
            self.disable()


class MessageQueueManager(object):
    """Manages the various MessageQueues for a client.

    :ivar c2d_message_queue: The C2D MessageQueue.
    :ivar input_message_queues: A dictionary mapping input names to Input MessageQueues.
    """

    def __init__(self, enable_feature_fn, disable_feature_fn):
        """Initializer for the MessageQueueManager.

        :param enable_feature_fn: A function that can enable transport features.
        :param disable_feature_fn: A function that can disable transport features.
        """
        self._enable_feature_fn = enable_feature_fn
        self._disable_feature_fn = disable_feature_fn
        self.c2d_message_queue = MessageQueue(
            self._c2d_message_queue_on_enable, self._c2d_message_queue_on_disable
        )  # not yet enabled
        self.input_message_queues = {}

    def _enable_feature(self, feature_name):
        """Trigger feature enable, and wait for it to complete."""
        enable_complete = Event()

        def callback():
            enable_complete.set()

        self._enable_feature_fn(feature_name, callback)
        enable_complete.wait()

    def _disable_feature(self, feature_name):
        """Trigger feature disable, and wait for it to complete."""
        disable_complete = Event()

        def callback():
            disable_complete.set()

        self._disable_feature_fn(feature_name, callback)
        disable_complete.wait()

    def _input_message_queue_on_enable(self):
        """Handler to be called when an Input MessageQueue is enabled."""
        # Enable input messages if no input queues are enabled
        if not any(queue.enabled for queue in self.input_message_queues.values()):
            self._enable_feature(constant.INPUT)

    def _c2d_message_queue_on_enable(self):
        """Handler to be called when a C2D MessageQueue is enabled."""
        self._enable_feature(constant.C2D)

    def _input_message_queue_on_disable(self):
        """Handler to be called when an Input MessageQueue is disabled."""
        # Disable input messages as a feature if all input queues are disabled
        if all(not queue.enabled for queue in self.input_message_queues.values()):
            self._disable_feature(constant.INPUT)

    def _c2d_message_queue_on_disable(self):
        """Handler to be called when a C2D MessageQueue is disabled."""
        self._disable_feature(constant.C2D)

    def get_input_message_queue(self, input_name):
        """Retrieve the MessageQueue for a given input.

        The returned MessageQueue will be automatically enabled.

        :param str input_name: The name of the input for which the associated MessageQueue is desired.
        :returns: An enabled MessageQueue for Input Messages.
        """
        try:
            queue = self.input_message_queues[input_name]
        except KeyError:
            # Create new MessageQueue for input if it does not yet exist
            queue = MessageQueue(
                self._input_message_queue_on_enable, self._input_message_queue_on_disable
            )
            self.input_message_queues[input_name] = queue

        if not queue.enabled:
            queue.enable()
        return queue

    def get_c2d_message_queue(self):
        """Retrieve the MessageQueue for C2D Messages.

        The returned MessageQueue will be automatically enabled.

        :returns: An enabled MessageQueue for C2D Messages.
        """
        queue = self.c2d_message_queue

        if not queue.enabled:
            queue.enable()
        return queue

    def route_input_message(self, input_name, incoming_message):
        """Route an incoming input message to the correct MessageQueue.

        If the MessageQueue is disabled, or the input is unknown, the message will be dropped.

        :param str input_name: The name of the input to route the message to.
        :param incoming_message: The message to be routed.

        :returns: Boolean indicating if the message was successfully routed or not.
        """
        delivered = False
        try:
            queue = self.input_message_queues[input_name]
        except KeyError:
            logger.warning("No input message queue for {} - dropping message".format(input_name))
        else:
            if queue.enabled:
                queue.put(incoming_message)
                delivered = True
                logger.info("Input message sent to {} queue".format(input_name))
            else:
                logger.warning(
                    "Input message queue for {} is disabled - dropping message".format(input_name)
                )
        return delivered

    def route_c2d_message(self, incoming_message):
        """Route an incoming C2D message to the C2D MessageQueue.

        If the MessageQueue is disabled, the message will be dropped.

        :param incoming message: The message to be routed.

        :returns: Boolean indicating if the message was successfully routed or not.
        """
        delivered = False
        if self.c2d_message_queue.enabled:
            self.c2d_message_queue.put(incoming_message)
            delivered = True
            logger.info("C2D message sent to queue")
        else:
            logger.warning("C2D message queue is disabled - dropping message")
        return delivered
