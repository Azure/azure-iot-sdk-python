from six.moves import queue
import logging
from threading import Event
from azure.iot.hub.devicesdk.transport import constant

logger = logging.getLogger(__name__)


class MessageQueue(
    queue.Queue, object
):  # add object as multiple inheritance b/c Queue is old style (no inheritance from object)
    def __init__(self, on_enable, on_disable):
        super(MessageQueue, self).__init__()
        self._enabled = False
        self._on_enable = on_enable
        self._on_disable = on_disable

    def enable(self):
        if not self._enabled:
            self._on_enable()  # must do this before changing status!
            self._enabled = True

    def disable(self):
        if self._enabled:
            self._enabled = False
            self._on_disable()  # must do this after changing status!

    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, v):
        if v:
            self.enable()
        else:
            self.disable()


class MessageQueueManager(object):
    def __init__(self, enable_feature_fn, disable_feature_fn):
        self._enable_feature_fn = enable_feature_fn
        self._disable_feature_fn = disable_feature_fn
        self.c2d_message_queue = MessageQueue(
            self._c2d_message_queue_on_enable, self._c2d_message_queue_on_disable
        )  # not yet enabled
        self.input_message_queues = {}

    def _enable_feature(self, feature_name):
        enable_complete = Event()

        def callback():
            enable_complete.set()

        self._enable_feature_fn(feature_name, callback)
        enable_complete.wait()

    def _disable_feature(self, feature_name):
        disable_complete = Event()

        def callback():
            disable_complete.set()

        self._disable_feature_fn(feature_name, callback)
        disable_complete.wait()

    def _input_message_queue_on_enable(self):
        # Enable input messages if no input queues are enabled
        if not any(queue.enabled for queue in self.input_message_queues.values()):
            self._enable_feature(constant.INPUT)

    def _c2d_message_queue_on_enable(self):
        self._enable_feature(constant.C2D)

    def _input_message_queue_on_disable(self):
        # Disable input messages as a feature if all input queues are disabled
        if all(not queue.enabled for queue in self.input_message_queues.values()):
            self._disable_feature(constant.INPUT)

    def _c2d_message_queue_on_disable(self):
        self._disable_feature(constant.C2D)

    def get_input_message_queue(self, input_name):
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
        queue = self.c2d_message_queue

        if not queue.enabled:
            queue.enable()
        return queue

    def route_input_message(self, input_name, incoming_message):
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
        delivered = False
        if self.c2d_message_queue.enabled:
            self.c2d_message_queue.put(incoming_message)
            delivered = True
            logger.info("C2D message sent to queue")
        else:
            logger.warning("C2D message queue is disabled - dropping message")
        return delivered
