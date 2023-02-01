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
import traceback

# The interval at which to check for registrations
MONITOR_TIME_BETWEEN_SUCCESS_ASSIGNMENTS = 1800
# The interval at which to send telemetry
TELEMETRY_INTERVAL = 10
# Interval in seconds between to check if device was provisioned to some hub
SLEEP_TIME_BETWEEN_CHECKING_REGISTRATION = 10
# Initial interval in seconds between consecutive connection attempts in case of error
INITIAL_SLEEP_TIME_BETWEEN_CONNECTION_ATTEMPTS = 3
# Threshold for retrying connection attempts after which the app will error
THRESHOLD_FOR_RETRY_CONNECTION = 81
# Interval for rotating logs, in seconds
LOG_ROTATION_INTERVAL = 3600
# How many logs to keep before recycling
LOG_BACKUP_COUNT = 6
# Directory for storing log files
LOG_DIRECTORY = "./logs/dpsfailover"
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
        self.iothub_assignment_fail_event = asyncio.Event()
        self.iothub_assignment_sucess_event = asyncio.Event()
        # Baseline that device has not been assigned
        self.iothub_assignment_fail_event.set()
        # Baseline that device has not been connected
        self.disconnected_event.set()

        self.provisioning_host = None
        self.id_scope = None
        self.symmetric_key = None
        self.registration_id = None
        self.registration_result = None

        # self.message_queue = asyncio.Queue()
        self.iothub_client = None
        self.provisioning_client = None
        # self.symmetric_key = None
        self.first_connect = True
        # Power factor for increasing interval between consecutive connection attempts.
        # This will increase with iteration
        self.retry_increase_factor = 1
        # The nth number for attempting connection
        self.sleep_time_between_conns = INITIAL_SLEEP_TIME_BETWEEN_CONNECTION_ATTEMPTS
        self.try_number = 1

    async def create_dps_client(self):
        self.log_info_and_print("Will create provisioning device client to provision device...")
        self.provisioning_client = ProvisioningDeviceClient.create_from_symmetric_key(
            provisioning_host=self.provisioning_host,
            registration_id=self.registration_id,
            id_scope=self.id_scope,
            symmetric_key=self.symmetric_key,
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

            # Reset the power factor, sleep time and the try number to what it was originally
            # on every successful connection.
            self.retry_increase_factor = 1
            self.sleep_time_between_conns = INITIAL_SLEEP_TIME_BETWEEN_CONNECTION_ATTEMPTS
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

    def print_stacktrace(self, exc):
        self.log_error_and_print("".join(traceback.format_stack()))
        if hasattr(exc, "message"):
            self.log_error_and_print(exc.message)

    async def register_loop(self):
        while True:
            if self.iothub_assignment_sucess_event.is_set():
                self.log_info_and_print("Device has been successfully provisioned already...")
                await asyncio.sleep(MONITOR_TIME_BETWEEN_SUCCESS_ASSIGNMENTS)
            elif self.iothub_assignment_fail_event.is_set():
                try:
                    self.log_info_and_print("Registering the device...")
                    self.registration_result = await self.provisioning_client.register()
                    print("The complete registration result is")
                    print(self.registration_result.registration_state)
                    if self.registration_result.status == "assigned":
                        self.log_info_and_print(
                            "Will create hub client to send telemetry from the provisioned device"
                        )
                        await self.create_hub_client(self.registration_result)
                        # await self.iothub_client.connect()
                        self.iothub_assignment_sucess_event.set()
                        self.iothub_assignment_fail_event.clear()
                    else:
                        self.log_error_and_print(
                            "Registration was done but device was not assigned correctly to an "
                            "IoTHub via the registration process.Will try registration "
                            "again after some time..."
                        )
                        await asyncio.sleep(SLEEP_TIME_BETWEEN_CHECKING_REGISTRATION)
                        self.iothub_assignment_fail_event.set()
                        self.iothub_assignment_sucess_event.clear()
                except Exception as e:
                    self.log_error_and_print(
                        "Registration process failed because of error {}".format(get_type_name(e))
                    )
                    self.print_stacktrace(e)
                    raise Exception(
                        "Caught an unrecoverable error that needs to be "
                        "fixed from user end while registering. Will exit application..."
                    )

                    # if self.is_assignment_failure(e):
                    #     self.log_error_and_print("Registration had error out and device was not assigned correctly to "
                    #                              "an IoTHub via the registration process.Will try registration "
                    #                              "again after some time...")
                    #     self.iothub_assignment_fail_event.set()
                    #     await asyncio.sleep(SLEEP_TIME_BETWEEN_CHECKING_REGISTRATION)
                    # else:
                    #     self.log_error_and_print("Caught an unrecoverable error that needs to be "
                    #                              "fixed from user end while registering. Will exit application...")
                    #     raise Exception(
                    #         "Caught an unrecoverable error that needs to be "
                    #                              "fixed from user end while registering. Will exit application..."
                    #     )
            if self.exit_app_event.is_set():
                return

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

    # async def create_hub_device_client(self):
    #     while True:
    #         if self.iothub_assignment_fail_event.is_set():
    #             self.log_info_and_print("waiting for assignment to IoTHub ...")
    #             await self.iothub_assignment_sucess_event.wait()
    #             try:
    #                 self.iothub_client = IoTHubDeviceClient.create_from_symmetric_key(
    #                     symmetric_key=self.symmetric_key,
    #                     hostname=self.registration_result.registration_state.assigned_hub,
    #                     device_id=self.registration_result.registration_state.device_id,
    #                 )
    #                 # Attach the connection state handler
    #                 self.iothub_client.on_connection_state_change = self.handle_on_connection_state_change
    #             except Exception as e:
    #                 self.log_error_and_print(
    #                     "Caught exception while trying to attach handler : {}".format(get_type_name(e))
    #                 )
    #                 raise Exception(
    #                     "Caught exception while trying to attach handler. Will exit application..."
    #                 )
    #         if self.exit_app_event.is_set():
    #             return

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
            if not self.iothub_client:
                # Time to check if device has been provisioned
                self.log_info_and_print(
                    "IoTHub client is still nonexistent for establishing connection."
                    "Will check after {} secs...".format(SLEEP_TIME_BETWEEN_CHECKING_REGISTRATION)
                )
                await asyncio.sleep(SLEEP_TIME_BETWEEN_CHECKING_REGISTRATION)
            elif not self.iothub_client.connected:
                try:
                    self.log_info_and_print(
                        "Attempting to connect the device client try number {}....".format(
                            self.try_number
                        )
                    )
                    await self.iothub_client.connect()
                    if self.first_connect:
                        self.first_connect = False
                    self.log_info_and_print("Successfully connected the device client...")
                except Exception as e:
                    # if self.is_assignment_failure(e):
                    #     self.iothub_assignment_fail_event.set()
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
                    self.print_stacktrace(e)
                    self.retry_increase_factor += 1
                    self.try_number += 1
                    await asyncio.sleep(sleep_time)

    async def wait_for_connect_and_send_telemetry(self):
        message_id = 0
        while True:
            if not self.iothub_client:
                # Time to check if device has been provisioned
                self.log_info_and_print(
                    "IoTHub client is still nonexistent for telemetry. "
                    "Will check after {} secs...".format(SLEEP_TIME_BETWEEN_CHECKING_REGISTRATION)
                )
                await asyncio.sleep(SLEEP_TIME_BETWEEN_CHECKING_REGISTRATION)
            elif not self.iothub_client.connected:
                self.log_info_and_print("IoTHub client is existent. But waiting for connection ...")
                await self.connected_event.wait()
            else:
                try:
                    message_id += 1
                    msg = Message("current wind speed ")
                    msg.message_id = message_id
                    msg.content_type = "application/json"
                    self.log_info_and_print("Created a message with id {}...".format(message_id))
                    await self.iothub_client.send_message(msg)
                    self.log_info_and_print("sent message")
                    await asyncio.sleep(TELEMETRY_INTERVAL)
                except Exception as e:
                    self.log_error_and_print(
                        "Caught exception while trying to send message: {}".format(get_type_name(e))
                    )
                    self.print_stacktrace(e)

            if self.exit_app_event.is_set():
                return

    def is_assignment_failure(self, e):
        """
        Errors where device does not get assigned to IoT Hub. Could mean IoTHub has been deleted or a
        load balancer has decided to kick the device out.
        """
        if (
            "Unreachable IoT Hub endpoint"
            or "Expired security token"
            or "Device disabled in IoT Hub" in e.message
        ):
            return True
        return False

    async def main(self):
        await self.initiate()

        self.provisioning_host = os.getenv("PROVISIONING_HOST")
        self.id_scope = os.getenv("PROVISIONING_IDSCOPE")
        self.registration_id = os.getenv("PROVISIONING_REGISTRATION_ID")
        self.symmetric_key = os.getenv("PROVISIONING_SYMMETRIC_KEY")

        await self.create_dps_client()

        tasks = [
            asyncio.create_task(self.register_loop()),
            asyncio.create_task(self.if_disconnected_then_connect_with_retry()),
            asyncio.create_task(self.wait_for_connect_and_send_telemetry()),
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
