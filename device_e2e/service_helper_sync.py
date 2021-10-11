# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.
import logging
import threading
from six.moves import queue
import copy
import time
from concurrent.futures import ThreadPoolExecutor
from azure.iot.hub import IoTHubRegistryManager, DigitalTwinClient
from azure.iot.hub.protocol.models import Twin, TwinProperties, CloudToDeviceMethod
from azure.eventhub import EventHubConsumerClient
import e2e_settings

logger = logging.getLogger("e2e.{}".format(__name__))

iothub_connection_string = e2e_settings.IOTHUB_CONNECTION_STRING
iothub_name = e2e_settings.IOTHUB_NAME
eventhub_connection_string = e2e_settings.EVENTHUB_CONNECTION_STRING
eventhub_consumer_group = e2e_settings.EVENTHUB_CONSUMER_GROUP

assert iothub_connection_string
assert iothub_name
assert eventhub_connection_string
assert eventhub_consumer_group


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


class PerClientData(object):
    """
    Object that holds data that needs to be stored in a device-by-device basis
    """

    def __init__(self, device_id, module_id):
        self.device_id = device_id
        self.module_id = module_id
        self.incoming_patch_queue = queue.Queue()
        self.cv = threading.Condition()
        self.incoming_eventhub_events = {}


class ClientList(object):
    """
    Thread-safe object for holding a dictionary of PerDeviceData objects.
    """

    def __init__(self):
        self.lock = threading.Lock()
        self.values = {}

    def remove(self, device_id, module_id):
        """
        remove an object from the dict
        """
        key = self.get_key(device_id, module_id)
        with self.lock:
            if key in self.values:
                del self.values[key]

    def try_get(self, device_id, module_id):
        """
        Try to get an object from the dict, returning None if the object doesn't exist
        """
        key = self.get_key(device_id, module_id)
        with self.lock:
            return self.values.get(key, None)

    def get_or_create(self, device_id, module_id):
        key = self.get_key(device_id, module_id)
        with self.lock:
            if key in self.values:
                return self.values.get(key)
            else:
                value = PerClientData(device_id, module_id)
                self.values[key] = value
                return value

    def get_key(self, device_id, module_id):
        return "{}%{}".format(device_id, module_id)


class ServiceHelperSync(object):
    def __init__(self):
        self._client_list = ClientList()
        self._executor = ThreadPoolExecutor()

        self._registry_manager = IoTHubRegistryManager(iothub_connection_string)

        self._digital_twin_client = DigitalTwinClient.from_connection_string(
            iothub_connection_string
        )

        self._eventhub_consumer_client = EventHubConsumerClient.from_connection_string(
            eventhub_connection_string, consumer_group=eventhub_consumer_group
        )

        self._eventhub_future = self._executor.submit(self._eventhub_thread)
        self.default_device_id = None
        self.default_module_id = None

    def start_watching(self, device_id, module_id):
        self.default_device_id = device_id
        self.default_module_id = module_id
        self._client_list.get_or_create(device_id, module_id)

    def stop_watching(self, device_id, module_id):
        if self.default_device_id == device_id and self.default_module_id == module_id:
            self.default_device_id = None
            self.default_module_id = None
        self._client_list.remove(device_id, module_id)

    def set_desired_properties(self, desired_props, device_id=None, module_id=None):
        device_id = device_id or self.default_device_id
        module_id = module_id or self.default_module_id

        if module_id:
            self._registry_manager.update_module_twin(
                device_id, module_id, Twin(properties=TwinProperties(desired=desired_props)), "*"
            )
        else:
            self._registry_manager.update_twin(
                device_id, Twin(properties=TwinProperties(desired=desired_props)), "*"
            )

    def invoke_method(
        self,
        method_name,
        payload,
        device_id=None,
        module_id=None,
        connect_timeout_in_seconds=None,
        response_timeout_in_seconds=None,
    ):
        device_id = device_id or self.default_device_id
        module_id = module_id or self.default_module_id

        request = CloudToDeviceMethod(
            method_name=method_name,
            payload=payload,
            response_timeout_in_seconds=response_timeout_in_seconds,
            connect_timeout_in_seconds=connect_timeout_in_seconds,
        )

        if module_id:
            response = self._registry_manager.invoke_device_module_method(
                device_id, module_id, request
            )

        else:
            response = self._registry_manager.invoke_device_method(device_id, request)

        return response

    def invoke_pnp_command(
        self,
        component_name,
        command_name,
        payload,
        device_id=None,
        module_id=None,
        connect_timeout_in_seconds=None,
        response_timeout_in_seconds=None,
    ):
        device_id = device_id or self.default_device_id
        module_id = module_id or self.default_module_id

        assert not module_id  # TODO
        if component_name:
            return self._digital_twin_client.invoke_component_command(
                device_id,
                component_name,
                command_name,
                payload,
                connect_timeout_in_seconds,
                response_timeout_in_seconds,
            )
        else:
            return self._digital_twin_client.invoke_command(
                device_id,
                command_name,
                payload,
                connect_timeout_in_seconds,
                response_timeout_in_seconds,
            )

    def get_pnp_properties(self, device_id=None, module_id=None):
        device_id = device_id or self.default_device_id
        module_id = module_id or self.default_module_id

        assert not module_id  # TODO
        return self._digital_twin_client.get_digital_twin(device_id)

    def update_pnp_properties(self, properties, device_id=None, module_id=None):
        device_id = device_id or self.default_device_id
        module_id = module_id or self.default_module_id

        assert not module_id  # TODO
        return self._digital_twin_client.update_digital_twin(device_id, properties)

    def send_c2d(self, payload, properties, device_id=None, module_id=None):
        device_id = device_id or self.default_device_id
        module_id = module_id or self.default_module_id

        assert not module_id  # TODO
        self._registry_manager.send_c2d_message(device_id, payload, properties)

    def wait_for_eventhub_arrival(self, message_id, device_id=None, module_id=None, timeout=20):
        device_id = device_id or self.default_device_id
        module_id = module_id or self.default_module_id

        client_data = self._client_list.try_get(device_id, module_id)

        def get_event():
            with client_data.cv:
                arrivals = client_data.incoming_eventhub_events

                # if message_id is not set, return any message
                if not message_id and len(arrivals):
                    id = list(arrivals.keys())[0]
                else:
                    id = message_id

                if id and (id in arrivals):
                    value = arrivals[id]
                    del arrivals[id]
                    return value
                else:
                    return None

        if client_data:
            # this should use return client_data.cv.wait_for(get_event, timeout=timeout)
            # Replace this when we don't support py27 anymore
            if timeout:
                end_time = time.time() + timeout
            else:
                end_time = None
            with client_data.cv:
                while True:
                    ev = get_event()
                    if ev or time.time() >= end_time:
                        return ev

                    if end_time:
                        client_data.cv.wait(timeout=end_time - time.time())
                    else:
                        client_data.cv.wait()

    def get_next_reported_patch_arrival(
        self, device_id=None, module_id=None, block=True, timeout=20
    ):
        device_id = device_id or self.default_device_id
        module_id = module_id or self.default_module_id

        client_data = self._client_list.try_get(device_id, module_id)
        if client_data:
            return client_data.incoming_patch_queue.get(block=block, timeout=timeout)

    def shutdown(self):
        if self._eventhub_consumer_client:
            self._eventhub_consumer_client.close()

    def _convert_incoming_event(self, event):
        event_body = event.body_as_json()
        device_id = get_device_id_from_event(event)
        module_id = None  # TODO: extract module_id

        if get_message_source_from_event(event) == "twinChangeEvents":
            return copy.deepcopy(event_body.get("properties", {}))

        else:
            message = EventhubEvent()
            message.device_id = device_id
            message.module_id = module_id
            message.message_body = event_body
            message.content_type = event.message.properties.content_type.decode("utf-8")
            message.system_properties = convert_binary_dict_to_string_dict(event.system_properties)
            message.properties = convert_binary_dict_to_string_dict(event.properties)
            return message

    def _store_eventhub_arrival(self, client_data, converted_event):
        message_id = converted_event.system_properties["message-id"]
        if message_id:
            with client_data.cv:
                client_data.incoming_eventhub_events[
                    converted_event.system_properties["message-id"]
                ] = converted_event
                client_data.cv.notify_all()

    def _store_patch_arrival(self, client_data, converted_event):
        client_data.incoming_patch_queue.put(converted_event)

    def _eventhub_thread(self):
        def on_error(partition_context, error):
            logger.error("EventHub on_error: {}".format(str(error) or type(error)))

        def on_partition_initialize(partition_context):
            logger.warning("EventHub on_partition_initialize")

        def on_partition_close(partition_context, reason):
            # commented out because it causes ugly warning spew on shutdown
            # logger.warning("EventHub on_partition_close: {}".format(reason))
            pass

        def on_event(partition_context, event):
            if event:
                device_id = get_device_id_from_event(event)
                module_id = None  # TODO: extract module_id

                client_data = self._client_list.try_get(device_id, module_id)
                if client_data:
                    logger.info(
                        "Received {} for device {}, module {}".format(
                            get_message_source_from_event(event),
                            client_data.device_id,
                            client_data.module_id,
                        )
                    )

                    converted_event = self._convert_incoming_event(event)

                    if isinstance(converted_event, EventhubEvent):
                        self._store_eventhub_arrival(client_data, converted_event)
                    else:
                        self._store_patch_arrival(client_data, converted_event)

        try:
            with self._eventhub_consumer_client:
                logger.info("Starting EventHub receive")
                self._eventhub_consumer_client.receive(
                    on_event,
                    on_error=on_error,
                    on_partition_initialize=on_partition_initialize,
                    on_partition_close=on_partition_close,
                    max_wait_time=3600,
                )
        except Exception:
            logger.error("_eventhub_thread exception", exc_info=True)
            raise
