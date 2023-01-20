# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------


import random
import asyncio

from azure.iot.device.aio import IoTHubDeviceClient
from azure.iot.device import exceptions
import logging
import traceback
import os
import glob

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


# The device connection string to authenticate the device with your IoT hub.
# Using the Azure CLI:
# az iot hub device-identity show-connection-string --hub-name {YourIoTHubName} --device-id MyNodeDevice --output table
CONNECTION_STRING = os.getenv("IOTHUB_DEVICE_CONNECTION_STRING")


# The interval at which to send telemetry
TELEMETRY_INTERVAL = 5
# Number of times connection attempts will be made.
RETRY_NOS = 50
# Interval between consecutive connection attempts
ATTEMPT_INTERVAL = 5
connected_event = None
disconnected_event = None
main_event_loop = None

# TODO We might have to expand our error list to be more detailed
# And possibly have status codes that reflect what sort of a service error
# To have a more detailed experience
transient_errors = [
    exceptions.OperationCancelled,
    exceptions.OperationTimeout,
    exceptions.ServiceError,
    exceptions.ConnectionFailedError,
    exceptions.ConnectionDroppedError,
    exceptions.NoConnectionError,
    exceptions.ClientError,  # TODO Only TLSEsxhangeError is actually worth retrying
]


def is_retryable(exc):
    if type(exc) in transient_errors:
        return True
    else:
        return False


def create_client():
    global connected_event
    global disconnected_event

    # Create a Device Client
    device_client = IoTHubDeviceClient.create_from_connection_string(CONNECTION_STRING)

    connected_event = asyncio.Event()
    disconnected_event = asyncio.Event()

    # Define a connection state change handler
    async def handle_on_connection_state_change():
        global main_event_loop
        print(
            "handle_on_connection_state_change fired. Connected status : {}".format(
                device_client.connected
            )
        )
        if device_client.connected:
            print("Connected connected_event is set...")
            main_event_loop.call_soon_threadsafe(connected_event.set)
        else:
            print("Disconnected connected_event is set...")
            main_event_loop.call_soon_threadsafe(disconnected_event.set)

    try:
        # Attach the connection state handler
        device_client.on_connection_state_change = handle_on_connection_state_change
    except Exception:
        # Clean up in the connected_event of failure
        device_client.shutdown()
        raise

    return device_client


async def connect_with_retry(device_client, number_of_tries=None):
    if device_client.connected:
        print("Client is already connected...")
        return True
    for i in range(number_of_tries):
        try:
            print("Attempting to connect the device client try number {}....".format(i))
            await device_client.connect()
            print("Successfully connected the device client...")
            return True
        except Exception as e:
            print("Caught exception while trying to connect...")
            if type(e) is exceptions.CredentialError:
                print(
                    "Failed to connect the device client due to incorrect or badly formatted credentials..."
                )
                return False

            if is_retryable(e):
                print(
                    "Failed to connect the device client due to retryable error.Sleeping and retrying after some time..."
                )
                await asyncio.sleep(ATTEMPT_INTERVAL)
            else:
                print("Failed to connect the device client due to not-retryable error....")
                return False


async def run_sample(device_client):
    encountered_no_error = await connect_with_retry(device_client, RETRY_NOS)
    if not encountered_no_error:
        print("Fatal error encountered. Will exit the application...")
        raise Exception

    while True:
        global connected_event
        print("Client is connected {}".format(device_client.connected))
        if not device_client.connected:
            print("Waiting for connection ...")
            await connected_event.wait()

        item = random.Random()
        print("Sending message...")
        try:
            await device_client.send_message(str(item))
            print("Message sent...")
            await asyncio.sleep(TELEMETRY_INTERVAL)
        except Exception:
            print("Caught exception while trying to send message....")
            logging.debug(traceback.format_exc())


def main():
    global main_event_loop
    print("IoT Hub Sample #1 - Constant Connection With Telemetry")
    print("Press Ctrl-C to exit")

    # Instantiate the client. Use the same instance of the client for the duration of
    # your application
    device_client = create_client()

    main_event_loop = asyncio.get_event_loop()
    print("IoT Hub device sending periodic messages")

    try:
        main_event_loop.run_until_complete(run_sample(device_client))
    except KeyboardInterrupt:
        print("IoTHubClient sample stopped by user")
    finally:
        print("Shutting down IoTHubClient")
        main_event_loop.run_until_complete(device_client.shutdown())
        main_event_loop.close()


if __name__ == "__main__":
    main()
