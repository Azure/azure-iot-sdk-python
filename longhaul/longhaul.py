# st -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import os
import sys
import asyncio
import logging
import logging.handlers
import functools
import json
import random
import dataclasses
import time
import datetime
import gc
import collections
import glob
from blessings import Terminal
from azure.iot.device.aio import IoTHubDeviceClient
from azure.iot.device import Message, X509

DEVICE_ID = os.environ["IOTHUB_DEVICE_ID"]

USE_WEBSOCKETS = True if os.environ.get("IOTHUB_WEBSOCKETS", False) else False

# Maximum number of seconds between reconnect retries
MAX_WAIT_TIME_BETWEEN_RECONNECT_ATTEMPTS = 20

# How long to sleep between telemetry sends
MESSAGE_SEND_SLEEP_TIME = 1

# How often do we start taking heap snapshots, in seconds
HEAP_HISTORY_STARTING_INTERVAL = 10

# How many heap counts do we keep in the history?
HEAP_HISTORY_LENGTH = 4

# Interval, in seconds, for updating the display
DISPLAY_INTERVAL = 1

# Interval for rotating logs, in seconds
LOG_ROTATION_INTERVAL = 3600

# How many logs to keep before recycling
LOG_BACKUP_COUNT = 6

# Directory for storing log files
LOG_DIRECTORY = "./logs/{}".format(DEVICE_ID)

# Prepare the log directory
os.makedirs(LOG_DIRECTORY, exist_ok=True)
for filename in glob.glob("{}/*.log".format(LOG_DIRECTORY)):
    os.remove(filename)


log_formatter = logging.Formatter(
    "%(asctime)s %(levelname)-5s (%(threadName)s) %(filename)s:%(funcName)s():%(message)s"
)

paho_log_handler = logging.handlers.TimedRotatingFileHandler(
    filename="{}/paho.log".format(LOG_DIRECTORY),
    when="S",
    interval=LOG_ROTATION_INTERVAL,
    backupCount=LOG_BACKUP_COUNT,
)
paho_log_handler.setLevel(level=logging.DEBUG)
paho_log_handler.setFormatter(log_formatter)

info_log_handler = logging.handlers.TimedRotatingFileHandler(
    filename="{}/info.log".format(LOG_DIRECTORY),
    when="S",
    interval=LOG_ROTATION_INTERVAL,
    backupCount=LOG_BACKUP_COUNT,
)
info_log_handler.setLevel(level=logging.INFO)
info_log_handler.setFormatter(log_formatter)

debug_log_handler = logging.handlers.TimedRotatingFileHandler(
    filename="{}/debug.log".format(LOG_DIRECTORY),
    when="S",
    interval=LOG_ROTATION_INTERVAL,
    backupCount=LOG_BACKUP_COUNT,
)
debug_log_handler.setLevel(level=logging.DEBUG)
debug_log_handler.setFormatter(log_formatter)

longhaul_log_handler = logging.FileHandler(filename="{}/longhaul.log".format(LOG_DIRECTORY))
longhaul_log_handler.setLevel(level=logging.DEBUG)
longhaul_log_handler.setFormatter(log_formatter)

root_logger = logging.getLogger()
root_logger.setLevel(level=logging.DEBUG)
root_logger.addHandler(info_log_handler)
root_logger.addHandler(debug_log_handler)

paho_logger = logging.getLogger("paho")
paho_logger.addHandler(paho_log_handler)


logger = logging.getLogger(__name__)
logger.addHandler(longhaul_log_handler)

term = Terminal()

try:
    # Copy Paho so time deltas work
    time_func = time.monotonic
except AttributeError:
    time_func = time.time


@dataclasses.dataclass
class HeapHistoryItem(object):
    time: str
    object_count: int


@dataclasses.dataclass(order=True)
class HeapHistoryStatus(object):
    snapshot_interval: int
    next_heap_snapshot: int
    history: list

    def __init__(self):
        super(HeapHistoryStatus, self).__init__()
        self.snapshot_interval = HEAP_HISTORY_STARTING_INTERVAL
        self.next_heap_snapshot = time_func() + self.snapshot_interval
        self.history = []


@dataclasses.dataclass(order=True)
class ReconnectStatus(object):
    connect_loop_status: str = "new"
    pipeline_connection_status: str = ""

    connect_count: int = 0
    disconnect_count: int = 0
    max_disconencted_time: int = 0

    last_connect_time: int = 0
    last_disconnect_time: int = 0
    time_since_last_connect: str = ""
    time_since_last_disconnect: str = ""


@dataclasses.dataclass(order=True)
class ExceptionStatus(object):
    connect_exceptions: dict = dataclasses.field(default_factory=dict)
    send_exceptions: dict = dataclasses.field(default_factory=dict)


@dataclasses.dataclass(order=True)
class PahoStatus(object):
    time_since_last_paho_traffic_in: str = ""
    time_since_last_paho_traffic_out: str = ""
    client_object_id: int = 0
    thread_name: str = ""
    thread_is_alive: bool = False
    len_out_mesage_queue: int = 0
    len_in_message_queue: int = 0
    len_out_pakcet_queue: int = 0
    thread_terminate: bool = False
    connection_state: int = 0

    def to_dict(self):
        return dataclasses.asdict(self)


@dataclasses.dataclass(order=True)
class PahoConfig(object):
    transport: str = ""
    protocol: str = ""
    keepalive: int = 0
    connect_timeout: int = 0
    reconnect_on_failure: bool = False
    reconnect_delay_min: int = 0
    reconnect_delay_max: int = 0
    host: str = ""
    port: int = 0
    proxy_args: dict = dataclasses.field(default_factory=dict)
    socket_class: str = ""
    socket_name: str = ""

    def to_dict(self):
        return dataclasses.asdict(self)


@dataclasses.dataclass(order=True)
class IoTHubClientConfig(object):
    client_class: str = ""
    server_verification_cert: bool = False
    gateway_hostname: str = ""
    websockets: bool = False
    cipher: str = ""
    product_info: str = ""
    proxy_options: dict = dataclasses.field(default_factory=dict)
    sastoken_ttl: int = 0
    keep_alive: int = 0
    connection_retry: bool = False
    connection_retry_interval: int = 0
    device_id: str = ""
    module_id: str = ""
    x509: bool = False
    sastoken_class: str = ""
    sastoken_signing_mechanism_class: str = ""


@dataclasses.dataclass(order=True)
class IoTHubClientStatus(object):
    connection_state: str = ""


@dataclasses.dataclass(order=True)
class SendMessageStatus(object):
    messages_sent: int = 0
    messages_queued: int = 0

    last_message_sent_time: int = 0
    time_since_last_message_sent: str = ""


@dataclasses.dataclass(order=True)
class ClientStatus(object):
    reconnect: ReconnectStatus
    exception: ExceptionStatus
    paho_status: PahoStatus
    paho_config: PahoConfig
    iothub_client_status: IoTHubClientStatus
    iothub_client_config: IoTHubClientConfig
    send_message: SendMessageStatus
    heap_history: HeapHistoryStatus

    start_time: int = 0
    time_since_start: str = ""
    device_id: str = DEVICE_ID
    websockets: bool = USE_WEBSOCKETS

    def __init__(self):
        super(ClientStatus, self).__init__()
        self.reconnect = ReconnectStatus()
        self.exception = ExceptionStatus()
        self.paho_status = PahoStatus()
        self.paho_config = PahoConfig()
        self.iothub_client_status = IoTHubClientStatus()
        self.iothub_client_config = IoTHubClientConfig()
        self.send_message = SendMessageStatus()
        self.heap_history = HeapHistoryStatus()


def wrap_in_try_catch(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(
                "Exception in {}: {}".format(func.__name__, get_type_name(e)), exc_info=True
            )
            raise e

    return wrapper


def get_type_name(e):
    return type(e).__name__


def get_paho_from_device_client(device_client):
    pipeline_root = device_client._mqtt_pipeline._pipeline
    stage = pipeline_root
    while stage.next:
        stage = stage.next
    return stage.transport._mqtt_client


def get_paho_config(paho_client):
    config = PahoConfig()
    config.transport = paho_client._transport
    config.protocol = str(paho_client._protocol)
    config.keepalive = paho_client._keepalive
    config.connect_timeout = paho_client._connect_timeout
    config.reconnect_on_failure = paho_client._reconnect_on_failure
    config.reconnect_delay_min = paho_client._reconnect_min_delay
    config.reconnect_delay_max = paho_client._reconnect_max_delay
    config.host = paho_client._host
    config.port = paho_client._port
    config.proxy_args = paho_client._proxy
    config.socket_class = str(type(paho_client.socket()))
    config.socket_name = (
        str(paho_client.socket().getsockname()) if paho_client.socket() else "No socket"
    )
    return config


def format_time_delta(s):
    if s:
        return str(datetime.timedelta(seconds=time_func() - s))
    else:
        return "infinity"


def get_paho_status(paho_client):
    status = PahoStatus()

    status.time_since_last_paho_traffic_in = format_time_delta(paho_client._last_msg_in)
    status.time_since_last_paho_traffic_out = format_time_delta(paho_client._last_msg_out)

    status.client_object_id = id(paho_client)
    status.thread_name = paho_client._thread.name if paho_client._thread else "None"
    status.thread_is_alive = (
        str(paho_client._thread.is_alive()) if paho_client._thread else "No thread"
    )
    status.len_out_mesage_queue = len(paho_client._out_messages)
    status.len_in_message_queue = len(paho_client._in_messages)
    status.len_out_pakcet_queue = len(paho_client._out_packet)
    status.thread_terminate = paho_client._thread_terminate
    status.connection_state = paho_client._state

    return status


def get_iothub_client_config(iothub_client):
    internal_config_object = iothub_client._mqtt_pipeline._nucleus.pipeline_configuration
    config = IoTHubClientConfig()

    config.client_class = str(type(iothub_client))
    config.server_verification_cert = (
        True if internal_config_object.server_verification_cert else False
    )
    config.gateway_hostname = internal_config_object.gateway_hostname
    config.websockets = internal_config_object.websockets
    config.cipher = str(internal_config_object.cipher)
    config.product_info = internal_config_object.product_info
    config.proxy_options = internal_config_object.proxy_options
    config.keep_alive = internal_config_object.keep_alive
    config.connection_retry = internal_config_object.connection_retry
    config.connection_retry_interval = internal_config_object.connection_retry_interval
    config.device_id = internal_config_object.device_id
    config.module_id = internal_config_object.module_id
    config.x509 = True if internal_config_object.x509 else False
    sastoken = internal_config_object.sastoken
    config.sastoken_ttl = sastoken.ttl if sastoken else 0
    config.sastoken_class = str(type(sastoken)) if sastoken else None
    config.sastoken_signing_mechanism_class = (
        str(type(sastoken._signing_mechanism)) if sastoken and sastoken._signing_mechanism else None
    )

    return config


def get_iothub_client_status(iothub_client):
    status = IoTHubClientStatus()
    nucleus = iothub_client._mqtt_pipeline._nucleus
    status.connection_state = str(nucleus.connection_state)
    return status


class Client(object):
    async def init(self):
        self.device_client = None

        self.outgoing_message_queue = asyncio.Queue()

        self.disconnected_event = asyncio.Event()
        self.connected_event = asyncio.Event()
        self.exit_app_event = asyncio.Event()

        self.disconnected_event.set()
        self.status = ClientStatus()

        self.first_connect = True

    @wrap_in_try_catch
    async def send_message_loop(self):

        while True:
            await self.connected_event.wait()
            next_message = await self.outgoing_message_queue.get()
            self.status.send_message.messages_queued = self.outgoing_message_queue.qsize()
            try:
                await self.device_client.send_message(next_message)
                self.status.send_message.last_message_sent_time = time_func()
            except Exception as e:
                t = get_type_name(e)
                self.status.exception.send_exceptions[t] = (
                    self.status.exception.send_exceptions.get(t, 0) + 1
                )
                await self.outgoing_message_queue.put(next_message)
            else:
                self.status.send_message.messages_sent += 1
            # TODO: queue here

    @wrap_in_try_catch
    async def queue_message_loop(self):
        messageId = 0
        while True:
            messageId += 1
            message = Message(
                json.dumps(
                    {"messageId": messageId, "message": "This is message #{}".format(messageId)}
                )
            )
            await self.outgoing_message_queue.put(message)
            self.status.send_message.messages_queued = self.outgoing_message_queue.qsize()
            await asyncio.sleep(MESSAGE_SEND_SLEEP_TIME)
            if self.exit_app_event.is_set():
                return

    @wrap_in_try_catch
    async def reconnect_loop(self):
        while True:
            done, pending = await asyncio.wait(
                [
                    self.disconnected_event.wait(),
                    self.exit_app_event.wait(),
                ],
                return_when=asyncio.FIRST_COMPLETED,
            )
            await asyncio.gather(*done)
            [x.cancel() for x in pending]

            if self.exit_app_event.is_set():
                self.status.reconnect.connect_loop_status = "exiting while connected"
                return

            if self.first_connect:
                sleep_time = 0
                self.first_connect = False
            else:
                sleep_time = random.random() * MAX_WAIT_TIME_BETWEEN_RECONNECT_ATTEMPTS

            self.status.reconnect.connect_loop_status = (
                "disconencted. waiting for {} seconds".format(round(sleep_time, 2))
            )

            done, pending = await asyncio.wait(
                [
                    self.connected_event.wait(),
                    self.exit_app_event.wait(),
                    asyncio.sleep(sleep_time),
                ],
                return_when=asyncio.FIRST_COMPLETED,
            )
            await asyncio.gather(*done)
            [x.cancel() for x in pending]

            if self.exit_app_event.is_set():
                self.status.reconnect.connect_loop_status = "exiting while disconnected"
                return

            if self.device_client.connected:
                self.status.reconnect.connect_loop_status = "connected"
            else:
                try:
                    self.status.reconnect.connect_loop_status = "connecting"
                    await self.device_client.connect()
                    self.status.reconnect.connect_loop_status = "connected"
                except Exception as e:
                    t = get_type_name(e)
                    self.status.reconnect.connect_loop_status = "connect exception {}".format(t)
                    self.status.exception.connect_exceptions[t] = (
                        self.status.exception.connect_exceptions.get(t, 0) + 1
                    )

    @property
    def paho(self):
        return get_paho_from_device_client(self.device_client)

    @wrap_in_try_catch
    async def display_loop(self):
        last_heap_counts = collections.Counter({})

        while True:

            self.status.time_since_start = format_time_delta(self.status.start_time)

            self.status.paho_config = get_paho_config(self.paho)
            self.status.paho_status = get_paho_status(self.paho)
            self.status.iothub_client_config = get_iothub_client_config(self.device_client)
            self.status.iothub_client_status = get_iothub_client_status(self.device_client)

            self.status.reconnect.time_since_last_connect = format_time_delta(
                self.status.reconnect.last_connect_time
            )
            self.status.reconnect.time_since_last_disconnect = format_time_delta(
                self.status.reconnect.last_disconnect_time
            )
            self.status.send_message.time_since_last_message_sent = format_time_delta(
                self.status.send_message.last_message_sent_time
            )

            if time_func() >= self.status.heap_history.next_heap_snapshot:
                gc.collect(2)

                self.status.heap_history.snapshot_interval *= 2
                self.status.heap_history.next_heap_snapshot = (
                    time_func() + self.status.heap_history.snapshot_interval
                )
                self.status.heap_history.history.append(
                    HeapHistoryItem(
                        time=str(datetime.datetime.now()),
                        object_count=len(gc.get_objects()),
                    )
                )
                self.status.heap_history.history = self.status.heap_history.history[
                    -HEAP_HISTORY_LENGTH:
                ]

                logger.info(
                    "Current Status: {}".format(
                        json.dumps(dataclasses.asdict(self.status), indent=2)
                    )
                )

                heap_counts = collections.Counter([type(x).__name__ for x in gc.get_objects()])
                delta = collections.Counter(heap_counts)
                delta.subtract(last_heap_counts)

                for key in list(delta.keys()):
                    if delta[key] == 0:
                        del delta[key]

                logger.info("Heap Delta: {}".format(json.dumps(delta, indent=2)))
                last_heap_counts = heap_counts

            print(term.clear())
            if time_func() - self.status.start_time > 50:
                self.status.paho_config = None
                self.status.iothub_client_config = None

            print(json.dumps(dataclasses.asdict(self.status), indent=2))

            done, pending = await asyncio.wait(
                [
                    self.exit_app_event.wait(),
                    asyncio.sleep(DISPLAY_INTERVAL),
                ],
                return_when=asyncio.FIRST_COMPLETED,
            )
            await asyncio.gather(*done)
            [x.cancel() for x in pending]

            if self.exit_app_event.is_set():
                return

    @wrap_in_try_catch
    async def handle_connection_state_change(self):
        if self.device_client.connected:
            self.status.reconnect.connect_count += 1
            self.status.reconnect.last_connect_time = time_func()
            self.status.reconnect.pipeline_connection_status = "connected"
            self.disconnected_event.clear()
            self.connected_event.set()
        else:
            self.status.reconnect.disconnect_count += 1
            self.status.reconnect.last_disconnect_time = time_func()
            self.status.reconnect.pipeline_connection_status = "disconnected"
            self.disconnected_event.set()
            self.connected_event.clear()

    async def main(self):
        # Make sure this was run with `python -X dev longhaul.py`.
        if not sys.flags.dev_mode:
            print("please re-run with -X dev command line arguments")
            sys.exit(1)

        await self.init()

        self.status.start_time = time_func()

        if "IOTHUB_DEVICE_CERT" in os.environ:
            self.device_client = IoTHubDeviceClient.create_from_x509_certificate(
                device_id=os.environ["IOTHUB_DEVICE_ID"],
                hostname=os.environ["IOTHUB_HOSTNAME"],
                x509=X509(
                    cert_file=os.environ["IOTHUB_DEVICE_CERT"],
                    key_file=os.environ["IOTHUB_DEVICE_KEY"],
                ),
                websockets=USE_WEBSOCKETS,
            )
        else:
            conn_str = os.getenv("IOTHUB_DEVICE_CONNECTION_STRING")
            self.device_client = IoTHubDeviceClient.create_from_connection_string(
                conn_str, websockets=USE_WEBSOCKETS
            )
        self.device_client.on_connection_state_change = self.handle_connection_state_change

        tasks = [
            self.send_message_loop(),
            self.queue_message_loop(),
            self.reconnect_loop(),
            self.display_loop(),
        ]

        try:
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
            await asyncio.gather(*done)
        except Exception as e:
            logger.error("Exception in main loop: {}".format(get_type_name(e)))
        finally:
            logger.warning("Exiting app")
            self.exit_app_event.set()
            logger.info("Waiting for all coroutines to exit")
            await asyncio.wait_for(
                asyncio.wait(pending, return_when=asyncio.ALL_COMPLETED), timeout=5
            )
            await self.device_client.shutdown()


if __name__ == "__main__":
    asyncio.run(Client().main())
