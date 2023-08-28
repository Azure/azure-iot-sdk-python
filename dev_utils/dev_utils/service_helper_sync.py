# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.
import logging
import threading
from six.moves import queue
import copy
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from azure.iot.hub import IoTHubRegistryManager
from azure.iot.hub.protocol.models import Twin, TwinProperties, CloudToDeviceMethod
from azure.eventhub import EventHubConsumerClient

logger = logging.getLogger("e2e.{}".format(__name__))


def convert_binary_dict_to_string_dict(src):
    def binary_to_string(x):
        if isinstance(x, bytes):
            return x.decode("utf-8")
        else:
            return x

    if src:
        dest = {}
        for key, value in src.items():
            dest[binary_to_string(key)] = binary_to_string(value)
        return dest
    else:
        return src


def get_device_id_from_event(event):
    """
    Helper function to get the device_id from an EventHub message
    """
    return event.message.annotations["iothub-connection-device-id".encode()].decode()


def get_module_id_from_event(event):
    """
    Helper function to get the module_id from an EventHub message
    """
    if "iothub-connection-module_id" in event.message.annotations:
        return event.message.annotations["iothub-connection-module-id".encode()].decode()
    else:
        return None


def get_message_source_from_event(event):
    """
    Helper function to get the message source from an EventHub message
    """
    return event.message.annotations["iothub-message-source".encode()].decode()


class EventhubEvent(object):
    def __init__(self):
        self.device_id = None
        self.module_id = None
        self.message_body = None
        self.content_type = None
        self.system_properties = None
        self.properties = None

    @property
    def message_id(self):
        # if message_id is missing, make one with a random guid. Do this because incoming_eventhub_events
        # is a dict indexed on message_id
        return self.system_properties.get("message-id", "no-message-id-{}".format(uuid.uuid4()))


class ServiceHelperSync(object):
    def __init__(
        self,
        iothub_connection_string,
        eventhub_connection_string,
        eventhub_consumer_group,
    ):
        self._executor = ThreadPoolExecutor()

        self._registry_manager = IoTHubRegistryManager(iothub_connection_string)

        logger.info(
            "Creating EventHubConsumerClient with consumer_group = {}".format(
                eventhub_consumer_group
            )
        )

        self._eventhub_consumer_client = EventHubConsumerClient.from_connection_string(
            eventhub_connection_string, consumer_group=eventhub_consumer_group
        )

        self._eventhub_future = self._executor.submit(self._eventhub_thread)
        self.device_id = None
        self.module_id = None
        self.incoming_patch_queue = queue.Queue()
        self.cv = threading.Condition()
        self.incoming_eventhub_events = {}

    def set_identity(self, device_id, module_id):
        if device_id != self.device_id or module_id != self.module_id:
            self.device_id = device_id
            self.module_id = module_id
            self.incoming_patch_queue = queue.Queue()
            with self.cv:
                if self.incoming_eventhub_events:
                    logger.warning(
                        "Abandoning incoming events with IDs {}".format(
                            str(list(self.incoming_eventhub_events.keys()))
                        )
                    )
                self.incoming_eventhub_events = {}

    def set_desired_properties(self, desired_props):
        if self.module_id:
            self._registry_manager.update_module_twin(
                self.device_id,
                self.module_id,
                Twin(properties=TwinProperties(desired=desired_props)),
                "*",
            )
        else:
            self._registry_manager.update_twin(
                self.device_id, Twin(properties=TwinProperties(desired=desired_props)), "*"
            )

    def invoke_method(
        self,
        method_name,
        payload,
        connect_timeout_in_seconds=30,
        response_timeout_in_seconds=None,
    ):
        request = CloudToDeviceMethod(
            method_name=method_name,
            payload=payload,
            response_timeout_in_seconds=response_timeout_in_seconds,
            connect_timeout_in_seconds=connect_timeout_in_seconds,
        )

        if self.module_id:
            response = self._registry_manager.invoke_device_module_method(
                self.device_id, self.module_id, request
            )

        else:
            response = self._registry_manager.invoke_device_method(self.device_id, request)

        return response

    def send_c2d(self, payload, properties):
        if self.module_id:
            raise TypeError("sending C2D to modules is not supported")
        self._registry_manager.send_c2d_message(self.device_id, payload, properties)

    def wait_for_eventhub_arrival(self, message_id, timeout=900):
        def get_event(inner_message_id):
            with self.cv:
                arrivals = self.incoming_eventhub_events

                # if message_id is not set, return any message
                if not inner_message_id and len(arrivals):
                    id = list(arrivals.keys())[0]
                    logger.info("wait_for_eventhub_arrival(None) returning msgid={}".format(id))
                else:
                    id = inner_message_id

                if id and (id in arrivals):
                    value = arrivals[id]
                    del arrivals[id]
                    return value
                else:
                    return None

        if timeout:
            end_time = time.time() + timeout
        else:
            end_time = None
        with self.cv:
            while True:
                ev = get_event(message_id)
                if ev:
                    return ev
                elif time.time() >= end_time:
                    logger.warning("timeout waiting for message with msgid={}".format(message_id))
                    return None
                elif end_time:
                    self.cv.wait(timeout=end_time - time.time())
                else:
                    self.cv.wait()

    def get_next_reported_patch_arrival(self, block=True, timeout=240):
        try:
            return self.incoming_patch_queue.get(block=block, timeout=timeout)
        except queue.Empty:
            raise Exception("reported patch did not arrive within {} seconds".format(timeout))

    def shutdown(self):
        if self._eventhub_consumer_client:
            self._eventhub_consumer_client.close()

    def _convert_incoming_event(self, event):
        try:
            event_body = event.body_as_json()
        except TypeError:
            event_body = event.body_as_str()
        device_id = get_device_id_from_event(event)
        module_id = get_module_id_from_event(event)

        if get_message_source_from_event(event) == "twinChangeEvents":
            return copy.deepcopy(event_body.get("properties", {}))

        else:
            message = EventhubEvent()
            message.device_id = device_id
            message.module_id = module_id
            message.message_body = event_body
            if event.message.properties:
                message.properties = convert_binary_dict_to_string_dict(event.properties)
                message.content_type = event.message.properties.content_type.decode("utf-8")
            message.system_properties = convert_binary_dict_to_string_dict(event.system_properties)
            return message

    def _store_eventhub_arrival(self, converted_event):
        message_id = converted_event.message_id
        if message_id:
            with self.cv:
                self.incoming_eventhub_events[message_id] = converted_event
                self.cv.notify_all()

    def _store_patch_arrival(self, converted_event):
        self.incoming_patch_queue.put(converted_event)

    def _eventhub_thread(self):
        def on_error(partition_context, error):
            logger.error("EventHub on_error: {}".format(str(error) or type(error)))

        def on_partition_initialize(partition_context):
            logger.warning("EventHub on_partition_initialize")

        def on_partition_close(partition_context, reason):
            logger.warning("EventHub on_partition_close: {}".format(reason))

        def on_event_batch(partition_context, events):
            try:
                for event in events:
                    device_id = get_device_id_from_event(event)
                    module_id = get_module_id_from_event(event)

                    if device_id == self.device_id and module_id == self.module_id:

                        converted_event = self._convert_incoming_event(event)
                        if isinstance(converted_event, EventhubEvent):
                            if "message-id" in converted_event.system_properties:
                                logger.info(
                                    "Received event with msgid={}".format(
                                        converted_event.system_properties["message-id"]
                                    )
                                )
                            else:
                                logger.info("Received event with no message id")

                        else:
                            logger.info(
                                "Received {} for device {}, module {}".format(
                                    get_message_source_from_event(event),
                                    device_id,
                                    module_id,
                                )
                            )

                        if isinstance(converted_event, EventhubEvent):
                            self._store_eventhub_arrival(converted_event)
                        else:
                            self._store_patch_arrival(converted_event)
            except Exception:
                logger.error("Error on on_event_batch", exc_info=True)
                raise

        try:
            with self._eventhub_consumer_client:
                logger.info("Starting EventHub receive")
                self._eventhub_consumer_client.receive_batch(
                    max_wait_time=2,
                    on_event_batch=on_event_batch,
                    on_error=on_error,
                    on_partition_initialize=on_partition_initialize,
                    on_partition_close=on_partition_close,
                )
        except Exception:
            logger.error("_eventhub_thread exception", exc_info=True)
            raise
