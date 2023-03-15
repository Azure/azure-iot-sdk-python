# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import asyncio
from azure.iot.device.iothub.aio import IoTHubDeviceClient
from azure.iot.device.aio import ProvisioningDeviceClient

import logging.handlers
import glob
import os
import traceback

# Current DPS time out configured in the python SDK is itself 30 secs ,
# so call times need to be configured keeping that in mind.
# The interval at which to check for registrations after a registration has been successful
MONITOR_TIME_BETWEEN_SUCCESS_ASSIGNMENTS = 45
# The interval at which to send telemetry
TELEMETRY_INTERVAL = 10
# Interval in seconds between to check if device was provisioned to some hub
# This is used when registration was underway and other processes are checking if it is completed.
SLEEP_TIME_BETWEEN_CHECKING_REGISTRATION = 10
# Initial interval in seconds between consecutive connection attempts in case of error
INITIAL_SLEEP_TIME_BETWEEN_CONNECTION_ATTEMPTS = 3
# Threshold for retrying connection attempts after which the app will error
THRESHOLD_FOR_RETRY_CONNECTION = 90
# Interval for rotating logs, in seconds
LOG_ROTATION_INTERVAL = 3600
# How many logs to keep before recycling
LOG_BACKUP_COUNT = 6
# Directory for storing log files
LOG_DIRECTORY = "./logs/event_loop_dpsfailover/device-delete-new-client-3"
messages_to_send = 10

# logger = logging.getLogger()
# logger.setLevel(level=logging.DEBUG)

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

        self.iothub_client = None
        self.first_connect = True
        self.registration_attempt_on = True
        # Power factor for increasing interval between consecutive connection attempts.
        # This will increase with iteration
        self.retry_increase_factor = 1
        # The nth number for attempting connection
        self.sleep_time_between_conns = INITIAL_SLEEP_TIME_BETWEEN_CONNECTION_ATTEMPTS
        self.try_number = 1

    async def create_dps_client(self, symmetric_key):
        self.log_info_and_print("Will create provisioning device client to provision device...")
        provisioning_host = os.getenv("PROVISIONING_HOST")
        id_scope = os.getenv("PROVISIONING_IDSCOPE")
        registration_id = os.getenv("PROVISIONING_REGISTRATION_ID")
        provisioning_client = ProvisioningDeviceClient.create_from_symmetric_key(
            provisioning_host=provisioning_host,
            registration_id=registration_id,
            id_scope=id_scope,
            symmetric_key=symmetric_key,
        )
        return provisioning_client

    async def create_hub_client(self, registration_result, symmetric_key):
        try:
            # Create a Device Client
            self.iothub_client = IoTHubDeviceClient.create_from_symmetric_key(
                symmetric_key=symmetric_key,
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
            main_event_loop.call_soon_threadsafe(self.connected_event.set)
            # Reset the power factor, sleep time and the try number to what it was originally
            # on every successful connection.
            self.retry_increase_factor = 1
            self.sleep_time_between_conns = INITIAL_SLEEP_TIME_BETWEEN_CONNECTION_ATTEMPTS
            self.try_number = 1
        else:
            self.log_info_and_print("Disconnected connected_event is set...")
            main_event_loop.call_soon_threadsafe(self.disconnected_event.set)
            self.connected_event.clear()

    async def register_loop(self):
        while True:
            provisioning_client = None
            self.log_info_and_print("Entry register_loop")
            if self.iothub_assignment_sucess_event.is_set():
                self.log_info_and_print("Device has been successfully provisioned already...")
                await asyncio.sleep(MONITOR_TIME_BETWEEN_SUCCESS_ASSIGNMENTS)
            elif self.iothub_assignment_fail_event.is_set():
                try:
                    symmetric_key = os.getenv("PROVISIONING_SYMMETRIC_KEY")
                    provisioning_client = await self.create_dps_client(symmetric_key)
                    self.log_info_and_print("Registering the device...")
                    registration_result = await provisioning_client.register()
                    print("The complete registration result is")
                    print(registration_result.registration_state)
                    if registration_result.status == "assigned":
                        self.log_info_and_print(
                            "Will create hub client to send telemetry from the provisioned device"
                        )
                        await self.create_hub_client(registration_result, symmetric_key)
                        self.iothub_assignment_sucess_event.set()
                        self.iothub_assignment_fail_event.clear()
                        self.log_error_and_print(
                            "Registration was done and device was assigned correctly to an "
                            "IoTHub via the registration process.Will check if all is right "
                            "after some time..."
                        )
                        await asyncio.sleep(MONITOR_TIME_BETWEEN_SUCCESS_ASSIGNMENTS)
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
                    raise Exception(
                        "Caught an unrecoverable error that needs to be "
                        "fixed from user end while registering. Will exit application..."
                    )
                finally:
                    await provisioning_client.shutdown()

            if self.exit_app_event.is_set():
                return

    async def wait_for_connect_and_send_telemetry(self):
        id = 1
        while True:
            if not self.iothub_client:
                # Time to check if device has been provisioned
                self.log_info_and_print(
                    "IoTHub client is not assigned. Telemetry operation failed. "
                    "Will check after {} secs...".format(SLEEP_TIME_BETWEEN_CHECKING_REGISTRATION)
                )
                await asyncio.sleep(SLEEP_TIME_BETWEEN_CHECKING_REGISTRATION)
            elif not self.iothub_client.connected:
                self.log_info_and_print("IoTHub client is existent. But waiting for connection ...")
                await self.connected_event.wait()
            else:
                self.log_info_and_print("sending message with id {}....".format(id))
                await self.iothub_client.send_message("message number {}".format(id))
                id += 1
                self.log_info_and_print("sent message.....")
                self.log_info_and_print("sleeping for {} secs...".format(TELEMETRY_INTERVAL))
                await asyncio.sleep(TELEMETRY_INTERVAL)
            if self.exit_app_event.is_set():
                return

    async def if_disconnected_then_connect_with_retry(self):
        while True:
            self.log_info_and_print("Entry for retry after disconnection")
            done, pending = await asyncio.wait(
                [
                    self.disconnected_event.wait(),
                    self.exit_app_event.wait(),
                ],
                return_when=asyncio.FIRST_COMPLETED,
            )
            self.log_info_and_print("Exit for retry after disconnection")
            await asyncio.gather(*done)
            [x.cancel() for x in pending]
            if self.exit_app_event.is_set():
                self.log_info_and_print("Exiting while connected")
                return
            if not self.iothub_client or self.iothub_assignment_fail_event.is_set():
                self.log_info_and_print(
                    "IoTHub client is invalid, re-provisioning is required to proceed."
                    "Will check after {} secs...".format(SLEEP_TIME_BETWEEN_CHECKING_REGISTRATION)
                )
                await asyncio.sleep(SLEEP_TIME_BETWEEN_CHECKING_REGISTRATION)
            elif not self.iothub_assignment_fail_event.is_set():
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
                    self.log_error_and_print(
                        "Caught exception while trying to connect: {}".format(get_type_name(e))
                    )
                    self.log_error_and_print("Exception details...")
                    self.log_error_and_print(
                        "Detailed exception: {}".format(traceback.format_exception_only(type(e), e))
                    )
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
                            "Retry time is greater than upper limit set. Will be reprovisioning the device again."
                        )
                        self.try_number = 1
                        self.retry_increase_factor = 1
                        self.iothub_assignment_fail_event.set()
                        self.iothub_assignment_sucess_event.clear()
                        sleep_time = SLEEP_TIME_BETWEEN_CHECKING_REGISTRATION
                        self.log_error_and_print(
                            "Will not retry connection as trying re-provisioing again. "
                            "Will try connection again after some time {}...".format(sleep_time)
                        )
                        await asyncio.sleep(sleep_time)
                    else:
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

    async def run_sample(self):
        await self.initiate()

        self.log_error_and_print(
            "asyncio debug is set to {}".format(os.getenv("PYTHONASYNCIODEBUG"))
        )

        tasks = [
            asyncio.create_task(self.register_loop()),
            asyncio.create_task(self.wait_for_connect_and_send_telemetry()),
            asyncio.create_task(self.if_disconnected_then_connect_with_retry()),
        ]

        pending = []

        try:
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
            await asyncio.gather(*done)
        except KeyboardInterrupt:
            self.log_error_and_print("IoTHubClient sample stopped by user")
        except Exception as e:
            self.log_error_and_print("Exception in run sample loop: {}".format(get_type_name(e)))
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

    def main(self):
        global main_event_loop
        print("IoT Hub Sample #1 - Constant Connection With Telemetry")
        print("Press Ctrl-C to exit")

        main_event_loop = asyncio.get_event_loop()

        try:
            main_event_loop.run_until_complete(Application().run_sample())
        except Exception as e:
            self.log_error_and_print(
                "Any other exception in the main calling: {}".format(get_type_name(e))
            )
        except KeyboardInterrupt:
            print("IoTHubClient sample stopped by user")
        finally:
            main_event_loop.close()


if __name__ == "__main__":
    Application().main()
