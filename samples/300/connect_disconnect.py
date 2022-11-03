# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import asyncio
import logging
import random

# import threading
import os
from azure.iot.device import exceptions

# import queue
from azure.iot.device.iothub.aio import IoTHubDeviceClient
import traceback

# TODO We might have to expand our error list to be more detailed
# And possibly have status codes that reflect what sort of a service error
transient_errors = [
    exceptions.OperationCancelled,
    exceptions.OperationTimeout,
    exceptions.ServiceError,
    exceptions.ConnectionFailedError,
    exceptions.ConnectionDroppedError,
    exceptions.NoConnectionError,
    exceptions.ClientError,  # Only TLSEsxhangeError is worth retrying
]

# logging.basicConfig(level=logging.DEBUG, filename="second.log")
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(thread)s %(funcName)s %(message)s",
    filename="debug.log",
)

# q = queue.Queue()
#
#
# async def produce_work(item):
#     q.put(item)
#     await asyncio.sleep(2)


async def connect_with_retry(client, number_of_tries=None):
    # instead of while true chose to go with number of tries
    if client.connected:
        print("Client is already connected...")
        return True
    for i in range(number_of_tries):
        # while True:
        try:
            print("Attempting to connect the device client try number {}....".format(i))
            await client.connect()
            print("Successfully connected the device client...")
            return True
        except Exception as e:
            print("Caught exception while trying to connect...")
            if type(e) is exceptions.CredentialError:
                print(
                    "Failed to connect the device client due to incorrect or badly formatted credentials..."
                )
                logging.error(
                    "Failed to connect the device client due to incorrect or badly formatted credentials..."
                )
                return False

            if is_retryable(e):
                print(
                    "Failed to connect the device client due to retryable error.Sleeping and retrying after some time..."
                )
                logging.info(
                    "Failed to connect the device client due to retryable error.Sleeping and retrying after some time..."
                )
                await asyncio.sleep(5)
            else:
                print("Failed to connect the device client due to not-retryable error....")
                logging.error("Failed to connect the device client due to not-retryable error....")
                return False


def is_retryable(exc):
    if type(exc) in transient_errors:
        return True
    else:
        return False


async def do_work(device_client, connected_event):
    # while not q.empty():
    # print('Waiting for connection ...')
    # await connected_event.wait()
    # This is ideal to do it ths way but
    print("Client is connected {}".format(device_client.connected))
    if not device_client.connected:
        print("Waiting for connection ...")
        await connected_event.wait()
    item = random.Random()
    print("Sending message...")
    try:
        await device_client.send_message(str(item))
        print("Message sent...")
        await asyncio.sleep(5)
    # except OSError as oe:
    #     print("Caught exception while trying to send message")
    #     logging.debug(traceback.format_exc())
    except Exception as e:
        print("Caught exception while trying to send message")
        # use args[0] for getting "Unexpected failure" out of the client error exception
        print(e.args[0])
        logging.debug(traceback.format_exc())
        # if type(e) is exceptions.ClientError:
        #     await device_client.disconnect()


async def main():
    conn_str = os.getenv("IOTHUB_DEVICE_CONNECTION_STRING")
    device_client = IoTHubDeviceClient.create_from_connection_string(conn_str)

    connected_event = asyncio.Event()
    disconnected_event = asyncio.Event()
    main_event_loop = asyncio.get_running_loop()

    async def handle_on_connection_state_change():
        # main_event_loop = asyncio.get_event_loop()
        print(
            "handle_on_connection_state_change fired. Connected status : {}".format(
                device_client.connected
            )
        )
        logging.info(
            "handle_on_connection_state_change connected: {}".format(device_client.connected)
        )
        if device_client.connected:
            print("Connected event is set...")
            main_event_loop.call_soon_threadsafe(connected_event.set)
        else:
            print("Disconnected event is set...")
            main_event_loop.call_soon_threadsafe(disconnected_event.set)

    device_client.on_connection_state_change = handle_on_connection_state_change
    # waiter_task = asyncio.create_task(do_work(device_client, connected_event))
    while True:
        # await do_work(device_client, connected_event)
        encountered_no_error = await connect_with_retry(device_client, 100)
        if not encountered_no_error:
            print("Fatal error encountered. Will exit the application...")
            logging.error("Fatal error encountered. Will exit the application...")
            break
        await do_work(device_client, connected_event)
        # await waiter_task

    # encountered_no_error = await connect_with_retry(device_client, 1)
    # if not encountered_no_error:
    #     logging.error("Fatal error encountered. Will exit the application...")
    #     exit(-1)
    # await do_work(device_client, connected_event)
    # await waiter_task


if __name__ == "__main__":
    asyncio.run(main(), debug=True)
