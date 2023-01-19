# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import asyncio
import psutil
from azure.iot.device.iothub.aio import IoTHubDeviceClient
from azure.iot.device import Message
import os
import logging.handlers
import glob
import random
import gc

# Interval in sec between consecutive connection attempts in case of retryable error
INITIAL_SLEEP_TIME_BETWEEN_CONNS = 2
# Lower limit of random range for queueing message
LOWER_LIMIT_OF_ENQUEUEING = 5
# Upper limit of random range for queueing message
UPPER_LIMIT_OF_ENQUEUEING = 15
# Time between connections
TIME_BETWEEN_CONNECTIONS = 120
# The interval after which a memory stats are taken, in seconds
STATISTICS_INTERVAL = 180
# Interval for rotating logs, in seconds
LOG_ROTATION_INTERVAL = 3600
# How many logs to keep before recycling
LOG_BACKUP_COUNT = 6
# Directory for storing log files
LOG_DIRECTORY = "./logs/stingy"
# The number of tries for which connection needs to be retried
NUMBER_OF_TRIES = 8

# Prepare the log directory
os.makedirs(LOG_DIRECTORY, exist_ok=True)
for filename in glob.glob("{}/*.log".format(LOG_DIRECTORY)):
    os.remove(filename)

# Formatter for logging
log_formatter = logging.Formatter(
    "%(asctime)s %(levelname)-5s (%(threadName)s) %(filename)s:%(funcName)s():%(message)s"
)
# INFO Log handler
info_log_handler = logging.handlers.TimedRotatingFileHandler(
    filename="{}/info.log".format(LOG_DIRECTORY),
    when="S",
    interval=LOG_ROTATION_INTERVAL,
    backupCount=LOG_BACKUP_COUNT,
)
info_log_handler.setLevel(level=logging.INFO)
info_log_handler.setFormatter(log_formatter)
# DEBUG log handler
debug_log_handler = logging.handlers.TimedRotatingFileHandler(
    filename="{}/debug.log".format(LOG_DIRECTORY),
    when="S",
    interval=LOG_ROTATION_INTERVAL,
    backupCount=LOG_BACKUP_COUNT,
)
debug_log_handler.setLevel(level=logging.DEBUG)
debug_log_handler.setFormatter(log_formatter)

root_logger = logging.getLogger()
root_logger.setLevel(level=logging.DEBUG)
root_logger.addHandler(info_log_handler)
root_logger.addHandler(debug_log_handler)

# Sample log handler
sample_log_handler = logging.FileHandler(filename="{}/sample.log".format(LOG_DIRECTORY))
sample_log_handler.setLevel(level=logging.DEBUG)
sample_log_handler.setFormatter(log_formatter)
logger = logging.getLogger(__name__)
logger.addHandler(sample_log_handler)


def get_type_name(e):
    return type(e).__name__


def process_memory():
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    return mem_info.rss


# decorator function
def profile(func):
    def wrapper(*args, **kwargs):
        mem_before = process_memory()
        result = func(*args, **kwargs)
        mem_after = process_memory()
        print(
            "{}:consumed memory: {:,}, {}, {}".format(
                func.__name__, mem_before, mem_after, mem_after - mem_before
            )
        )

        return result

    return wrapper


class Application(object):
    async def initiate(self):

        self.message_queue = asyncio.Queue()
        self.device_client = None
        self.exit_app_event = asyncio.Event()

        # Power factor for increasing interval between consecutive connection attempts.
        # This will increase with iteration
        self.retry_increase_factor = 1
        # Initial value to sleep between connections.
        self.sleep_time_between_conns = INITIAL_SLEEP_TIME_BETWEEN_CONNS

    async def create_client(self, conn_str):
        try:
            # Create a Device Client
            self.device_client = IoTHubDeviceClient.create_from_connection_string(conn_str)
            # Attach the connection state handler
            self.device_client.on_connection_state_change = self.handle_on_connection_state_change
        except Exception as e:
            self.log_error_and_print(
                "Caught exception while trying to attach handler : {}".format(get_type_name(e))
            )
            raise Exception(
                "Caught exception while trying to attach handler.Will exit application..."
            )

    async def handle_on_connection_state_change(self):
        self.log_info_and_print(
            "handle_on_connection_state_change fired. Connected status : {}".format(
                self.device_client.connected
            )
        )
        if self.device_client.connected:
            self.log_info_and_print("Connected connected_event is set...")
            self.retry_increase_factor = 1
            self.sleep_time_between_conns = INITIAL_SLEEP_TIME_BETWEEN_CONNS
        else:
            self.log_info_and_print("Disconnected connected_event is set...")

    def log_error_and_print(self, s):
        logger.error(s)
        print(s)

    def log_info_and_print(self, s):
        logger.info(s)
        print(s)

    async def enqueue_message(self):
        message_id = 0
        while True:
            message_id += 1
            msg = Message("current wind speed ")
            msg.message_id = message_id
            msg.content_type = "application/json"
            self.log_info_and_print("Created a message...")
            self.message_queue.put_nowait(msg)
            # time between 10 seconds and less than 30 minutes.
            randint = random.randint(UPPER_LIMIT_OF_ENQUEUEING, UPPER_LIMIT_OF_ENQUEUEING)
            self.log_info_and_print(
                "Will sleep for {} seconds and then enqueue messages".format(randint)
            )
            await asyncio.sleep(randint)
            if self.exit_app_event.is_set():
                return

    async def do_all_tasks_and_disconnect(self):
        task_list = []
        self.log_info_and_print("Current qsize is: {}".format(self.message_queue.qsize()))
        while not self.message_queue.empty():
            msg = await self.message_queue.get()
            task = asyncio.create_task(self.device_client.send_message(msg))
            task_list.append(task)
            self.message_queue.task_done()
        try:
            if self.device_client.connected:
                self.log_info_and_print("sending messages...")
                await asyncio.gather(*task_list)
                self.log_info_and_print("sent all messages...")
        except Exception as e:
            self.log_error_and_print(
                "Caught exception while trying to send message or disconnect: {}".format(
                    get_type_name(e)
                )
            )
        finally:
            # Disconnect even if messages were unable to sent due to some exception.
            # We are losing messages here as we consider connections to be expensive.
            task_list = []
            await self.device_client.disconnect()

    async def connect_with_retry_send_all_and_disconnect(self):
        while True:
            for i in range(1, NUMBER_OF_TRIES):
                if not self.device_client.connected:
                    try:
                        self.log_info_and_print(
                            "Attempting to connect the device client try number {}....".format(i)
                        )
                        await self.device_client.connect()
                        self.log_info_and_print("Successfully connected the device client...")
                        await self.do_all_tasks_and_disconnect()
                        break
                    except Exception as e:
                        sleep_time = pow(self.sleep_time_between_conns, self.retry_increase_factor)
                        self.log_error_and_print("Caught exception while trying to connect...")
                        self.log_error_and_print(
                            "Failed to connect the device client due to error :{}.Sleeping and retrying after {} seconds".format(
                                get_type_name(e), sleep_time
                            )
                        )
                        self.retry_increase_factor += 1
                        await asyncio.sleep(sleep_time)

            # Sleep for 30 minutes and again collect all messages to send
            self.log_info_and_print(
                "Will sleep for {} seconds and then retrieve messages to send....".format(
                    TIME_BETWEEN_CONNECTIONS
                )
            )
            await asyncio.sleep(TIME_BETWEEN_CONNECTIONS)
            if self.exit_app_event.is_set():
                return

    async def memory_stats(self):
        while True:
            gc_counts = gc.get_stats()

            self.log_info_and_print("GC stats are:-")
            for item in gc_counts:
                self.log_info_and_print("collections -> {}".format(item["collections"]))
                self.log_info_and_print("collected -> {}".format(item["collected"]))
                self.log_info_and_print("uncollectable -> {}".format(item["uncollectable"]))

            self.log_info_and_print(
                "Will sleep for {} seconds and then collect memory stats....".format(
                    STATISTICS_INTERVAL
                )
            )
            await asyncio.sleep(STATISTICS_INTERVAL)
            if self.exit_app_event.is_set():
                return

    @profile
    async def main(self):
        conn_str = os.getenv("IOTHUB_DEVICE_CONNECTION_STRING")
        await self.initiate()
        await self.create_client(conn_str)

        tasks = [
            asyncio.create_task(self.connect_with_retry_send_all_and_disconnect()),
            asyncio.create_task(self.enqueue_message()),
            asyncio.create_task(self.memory_stats()),
        ]

        pending = []
        try:
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
            await asyncio.gather(*done)
        except KeyboardInterrupt:
            self.log_error_and_print("IoTHubClient sample stopped by user")
        except Exception as e:
            self.log_error_and_print("Exception in main loop: {}".format(get_type_name(e)))
        finally:
            self.log_info_and_print("Exiting app")
            self.exit_app_event.set()
            self.log_info_and_print("Waiting for all coroutines to exit")
            await asyncio.wait_for(
                asyncio.wait(pending, return_when=asyncio.ALL_COMPLETED), timeout=5
            )
            self.log_info_and_print("Shutting down IoTHubClient and exiting Application")
            await self.device_client.shutdown()


if __name__ == "__main__":
    asyncio.run(Application().main())
