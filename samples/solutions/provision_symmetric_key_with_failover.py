# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import asyncio
from azure.iot.device.iothub.aio import IoTHubDeviceClient
from azure.iot.device.aio import ProvisioningDeviceClient
from azure.iot.device import Message
import logging.handlers
import glob
import os
import uuid


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


messages_to_send = 10


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
        self.iothub_fail_event = asyncio.Event()
        self.iothub_fail_event.set()

        self.message_queue = asyncio.Queue()
        self.iothub_client = None
        self.provisioning_client = None
        self.symmetric_key = None
        self.first_connect = True
        # Power factor for increasing interval between consecutive connection attempts.
        # This will increase with iteration
        self.retry_increase_factor = 1
        # The nth number for attempting connection
        self.sleep_time_between_conns = INITIAL_SLEEP_TIME_BETWEEN_CONNS
        self.try_number = 1

    async def create_dps_client(self, provisioning_host, registration_id, id_scope):
        self.provisioning_client = ProvisioningDeviceClient.create_from_symmetric_key(
            provisioning_host=provisioning_host,
            registration_id=registration_id,
            id_scope=id_scope,
            symmetric_key=self.symmetric_key,
        )

    async def create_hub_client(self, registration_result):
        try:
            # Create a Device Client
            self.iothub_client = IoTHubDeviceClient.create_from_symmetric_key(
                symmetric_key=self.symmetric_key,
                hostname=registration_result.registration_state.assigned_hub,
                device_id=registration_result.registration_state.device_id,
            )
            # Attach the connection state handler
            self.iothub_client.on_connection_state_change = self.handle_on_connection_state_change
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
                self.iothub_client.connected
            )
        )
        if self.iothub_client.connected:
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

    def log_error_and_print(self, s):
        logger.error(s)
        print(s)

    def log_info_and_print(self, s):
        logger.info(s)
        print(s)

    async def register(self):
        while True:
            if self.iothub_fail_event.is_set():
                registration_result = await self.provisioning_client.register()
                print("The complete registration result is")
                print(registration_result.registration_state)
                if registration_result.status == "assigned":
                    print("Will send telemetry from the provisioned device")
                    await self.create_hub_client(self.symmetric_key, registration_result)
                    # Connect the client.
                    await self.iothub_client.connect()

                    async def send_test_message(i):
                        print("sending message #" + str(i))
                        msg = Message("test wind speed " + str(i))
                        msg.message_id = uuid.uuid4()
                        await self.iothub_client.send_message(msg)
                        print("done sending message #" + str(i))

                    # send `messages_to_send` messages in parallel
                    await asyncio.gather(
                        *[send_test_message(i) for i in range(1, messages_to_send + 1)]
                    )

                    # finally, disconnect
                    await self.iothub_client.disconnect()
                else:
                    print("Can not send telemetry from the provisioned device")
            if self.exit_app_event.is_set():
                return

    async def main(self):
        await self.initiate()

        provisioning_host = os.getenv("PROVISIONING_HOST")
        id_scope = os.getenv("PROVISIONING_IDSCOPE")
        registration_id = os.getenv("PROVISIONING_REGISTRATION_ID")
        self.symmetric_key = os.getenv("PROVISIONING_SYMMETRIC_KEY")
        await self.create_dps_client(provisioning_host, registration_id, id_scope)

        tasks = [
            asyncio.create_task(self.register()),
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
            if pending:
                await asyncio.wait_for(
                    asyncio.wait(pending, return_when=asyncio.ALL_COMPLETED), timeout=5
                )
            self.log_info_and_print(
                "Shutting down both ProvisioningClient and IoTHubClient and exiting Application"
            )
            await self.iothub_client.shutdown()
            await self.provisioning_client.shutdown()


if __name__ == "__main__":
    asyncio.run(Application().main())
