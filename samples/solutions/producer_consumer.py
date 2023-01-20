# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import asyncio
from azure.iot.device.iothub.aio import IoTHubDeviceClient
from azure.iot.device import Message
import os
import logging.handlers
import glob

# The interval at which to send telemetry
TELEMETRY_INTERVAL = 10
# Initial interval in seconds between consecutive connection attempts
INITIAL_SLEEP_TIME_BETWEEN_CONNS = 2
# Threshold for retrying connection attempts after which the app will error
THRESHOLD_FOR_RETRY_CONNECTION = 7200
# Interval for rotating logs, in seconds
LOG_ROTATION_INTERVAL = 3600
# How many logs to keep before recycling
LOG_BACKUP_COUNT = 6
# Directory for storing log files
LOG_DIRECTORY = "./logs"

# Prepare the log directory
os.makedirs(LOG_DIRECTORY, exist_ok=True)
for filename in glob.glob("{}/*.log".format(LOG_DIRECTORY)):
    os.remove(filename)

log_formatter = logging.Formatter(
    "%(asctime)s %(levelname)-5s (%(threadName)s) %(filename)s:%(funcName)s():%(message)s"
)

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

root_logger = logging.getLogger()
root_logger.setLevel(level=logging.DEBUG)
root_logger.addHandler(info_log_handler)
root_logger.addHandler(debug_log_handler)

sample_log_handler = logging.FileHandler(filename="{}/sample.log".format(LOG_DIRECTORY))
sample_log_handler.setLevel(level=logging.DEBUG)
sample_log_handler.setFormatter(log_formatter)
logger = logging.getLogger(__name__)
logger.addHandler(sample_log_handler)


def get_type_name(e):
    return type(e).__name__


class Application(object):
    async def initiate(self):
        self.connected_event = asyncio.Event()
        self.disconnected_event = asyncio.Event()
        self.exit_app_event = asyncio.Event()
        self.disconnected_event.set()

        self.message_queue = asyncio.Queue()
        self.device_client = None
        self.first_connect = True
        # Power factor for increasing interval between consecutive connection attempts.
        # This will increase with iteration
        self.retry_increase_factor = 1
        # The nth number for attempting connection
        self.sleep_time_between_conns = INITIAL_SLEEP_TIME_BETWEEN_CONNS
        self.try_number = 1

    async def create_client(self, conn_str):
        try:
            # Create a Device Client
            self.device_client = IoTHubDeviceClient.create_from_connection_string(
                conn_str
            )
            # Attach the connection state handler
            self.device_client.on_connection_state_change = self.handle_on_connection_state_change
        except Exception as e:
            self.log_error_and_print(
                "Caught exception while trying to attach handler : {}".format(get_type_name(e))
            )
            raise Exception(
                "Caught exception while trying to attach handler. Will exit application..."
            )

    async def handle_on_connection_state_change(self):
        self.log_info_and_print(
            "handle_on_connection_state_change fired. Connected status : {}".format(
                self.device_client.connected
            )
        )
        if self.device_client.connected:
            self.log_info_and_print("Connected connected_event is set...")
            self.disconnected_event.clear()
            self.connected_event.set()

            self.retry_increase_factor = 1
            self.sleep_time_between_conns = INITIAL_SLEEP_TIME_BETWEEN_CONNS
            self.try_number = 1
        else:
            self.log_info_and_print("Disconnected connected_event is set...")
            self.disconnected_event.set()
            self.connected_event.clear()

    async def enqueue_message(self):
        message_id = 0
        while True:

            message_id += 1
            msg = Message("current wind speed ")
            msg.message_id = message_id
            msg.content_type = "application/json"
            self.log_info_and_print("Created a message...")
            self.message_queue.put_nowait(msg)
            await asyncio.sleep(TELEMETRY_INTERVAL)
            if self.exit_app_event.is_set():
                return

    async def wait_for_connect_and_send_telemetry(self):
        while True:
            if not self.device_client.connected:
                self.log_info_and_print("waiting for connection ...")
                await self.connected_event.wait()
            else:
                self.log_info_and_print("Retrieving an item from the queue...")
                done, pending = await asyncio.wait(
                    [
                        self.message_queue.get(),
                        self.exit_app_event.wait(),
                    ],
                    return_when=asyncio.FIRST_COMPLETED,
                )
                await asyncio.gather(*done)
                [x.cancel() for x in pending]
                if self.exit_app_event.is_set():
                    self.log_info_and_print("Exiting while waiting for an item")
                    return
                # msg = await self.message_queue.get()
                msg = None
                for task in done:
                    msg = task.result()

                try:
                    self.log_info_and_print('Retrieved "{}"'.format(msg))
                    self.log_info_and_print("sending message...")
                    await self.device_client.send_message(msg)
                    self.log_info_and_print("sent message")
                    self.message_queue.task_done()
                    await asyncio.sleep(TELEMETRY_INTERVAL)
                except Exception as e:
                    self.log_error_and_print(
                        "Caught exception while trying to send message: {}".format(get_type_name(e))
                    )
                    self.message_queue.put_nowait(msg)
            if self.exit_app_event.is_set():
                return

    async def if_disconnected_then_connect_with_retry(self):
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
                self.log_info_and_print("Exiting while connected")
                return
            if not self.device_client.connected:
                try:
                    self.log_info_and_print(
                        "Attempting to connect the device client try number {}....".format(
                            self.try_number
                        )
                    )
                    await self.device_client.connect()
                    if self.first_connect:
                        self.first_connect = False
                    self.log_info_and_print("Successfully connected the device client...")
                except Exception as e:
                    if self.first_connect:
                        self.log_info_and_print(
                            "Very first connection never occurred so will retry immediately..."
                        )
                        self.first_connect = False
                        sleep_time = 0
                    else:
                        self.log_info_and_print(
                            "Retry attempt interval is {} and increase power factor is {}".format(
                                self.sleep_time_between_conns, self.retry_increase_factor
                            )
                        )
                        sleep_time = pow(self.sleep_time_between_conns, self.retry_increase_factor)

                    if sleep_time > THRESHOLD_FOR_RETRY_CONNECTION:
                        self.log_error_and_print(
                            "Failed to connect the device client couple of times."
                            "Retry time is greater than upper limit set. Will be exiting the application."
                        )
                        self.try_number = 0
                        raise

                    self.log_error_and_print("Caught exception while trying to connect...")
                    self.log_error_and_print(
                        "Failed to connect the device client due to error :{}.Sleeping and retrying after {} seconds".format(
                            get_type_name(e), sleep_time
                        )
                    )
                    self.retry_increase_factor += 1
                    self.try_number += 1
                    await asyncio.sleep(sleep_time)

    def log_error_and_print(self, s):
        logger.error(s)
        print(s)

    def log_info_and_print(self, s):
        logger.info(s)
        print(s)

    async def main(self):
        conn_str = os.getenv("IOTHUB_DEVICE_CONNECTION_STRING")
        await self.initiate()
        await self.create_client(conn_str)

        tasks = [
            asyncio.create_task(self.wait_for_connect_and_send_telemetry()),
            asyncio.create_task(self.enqueue_message()),
            asyncio.create_task(self.if_disconnected_then_connect_with_retry()),
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
