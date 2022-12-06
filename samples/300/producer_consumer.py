# CUSTOMER PERSONA
# A producer application is creating a message and inserting inside a queue uniformly.
# Customer wants to fetch a message from a queue and send message at some interval consistently
# as long as connection remains. In case of disconnection the customer wants to retry the connection
# for errors that are worth retrying.

import asyncio
import logging
from azure.iot.device.iothub.aio import IoTHubDeviceClient
from azure.iot.device import exceptions, Message
import traceback
import os


logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)-5s (%(threadName)s) %(filename)s:%(funcName)s():%(message)s",
    filename="device_60_hours.log",
)


# The interval at which to send telemetry
TELEMETRY_INTERVAL = 10
# Number of times connection attempts will be made.
RETRY_NOS = 50
# Interval between consecutive connection attempts
ATTEMPT_INTERVAL = 5


class Application(object):
    async def initiate(self):

        self.transient_errors = [
            exceptions.OperationCancelled,
            exceptions.OperationTimeout,
            exceptions.ServiceError,
            exceptions.ConnectionFailedError,
            exceptions.ConnectionDroppedError,
            exceptions.NoConnectionError,
            exceptions.ClientError,  # TODO Only TLSEsxhangeError is actually worth retrying
        ]

        self.connected_event = asyncio.Event()
        self.disconnected_event = asyncio.Event()
        # self.exit_app_event = asyncio.Event()
        self.disconnected_event.set()

        self.message_queue = asyncio.Queue()
        self.device_client = None
        self.first_connect = True

    async def create_client(self, conn_str):
        try:
            # Create a Device Client
            self.device_client = IoTHubDeviceClient.create_from_connection_string(conn_str)
            # Attach the connection state handler
            self.device_client.on_connection_state_change = self.handle_on_connection_state_change
        except Exception:
            # Clean up in the connected_event of failure
            print("Caught exception while trying to attach handler....")
            logging.debug(traceback.format_exc())

    async def handle_on_connection_state_change(self):
        print(
            "handle_on_connection_state_change fired. Connected status : {}".format(
                self.device_client.connected
            )
        )
        if self.device_client.connected:
            print("Connected connected_event is set...")
            self.disconnected_event.clear()
            self.connected_event.set()
        else:
            print("Disconnected connected_event is set...")
            self.disconnected_event.set()
            self.connected_event.clear()

    async def enqueue_message(self):
        message_id = 0
        while True:
            msg = Message("current wind speed ")
            msg.message_id = message_id
            msg.content_type = "application/json"
            print("Created a message...")
            self.message_queue.put_nowait(msg)
            await asyncio.sleep(TELEMETRY_INTERVAL)
            message_id += 1

    async def wait_for_connect_and_send_telemetry(self):
        while True:
            if not self.device_client.connected:
                print("waiting for connection ...")
                await self.connected_event.wait()
            else:
                msg = await self.message_queue.get()
                try:
                    print("sending message...")
                    await self.device_client.send_message(msg)
                    print("sent message")
                    self.message_queue.task_done()
                    await asyncio.sleep(TELEMETRY_INTERVAL)
                except Exception:
                    print("Caught exception while trying to send message....")
                    logging.debug(traceback.format_exc())
                    self.message_queue.put_nowait(msg)

    async def if_disconnected_then_connect_with_retry(self, number_of_tries=None):
        i = 0
        while True:
            # for i in range(number_of_tries):
            sleep_time = 0
            await self.disconnected_event.wait()
            if self.first_connect:
                self.first_connect = False
            else:
                sleep_time = ATTEMPT_INTERVAL
            if not self.device_client.connected:
                try:
                    print("Attempting to connect the device client try number {}....".format(i))
                    await self.device_client.connect()
                    print("Successfully connected the device client...")
                    i = 0
                except Exception as e:
                    print("Caught exception while trying to connect...")
                    if type(e) is exceptions.CredentialError:
                        print(
                            "Failed to connect the device client due to incorrect or badly formatted credentials..."
                        )
                        i = 0
                        raise

                    if self.is_retryable(e):
                        print(
                            "Failed to connect the device client due to retryable error.Sleeping and retrying after some time..."
                        )
                        i += 1
                        await asyncio.sleep(sleep_time)
                    else:
                        print("Failed to connect the device client due to not-retryable error....")
                        i = 0
                        raise

    def is_retryable(self, exc):
        if type(exc) in self.transient_errors:
            return True
        else:
            return False

    async def main(self):
        conn_str = os.getenv("IOTHUB_DEVICE_CONNECTION_STRING")
        await self.initiate()
        await self.create_client(conn_str)

        tasks = [
            asyncio.create_task(self.wait_for_connect_and_send_telemetry()),
            asyncio.create_task(self.enqueue_message()),
            asyncio.create_task(self.if_disconnected_then_connect_with_retry(RETRY_NOS)),
        ]

        try:
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
            await asyncio.gather(*done)
        except (KeyboardInterrupt, Exception):
            print("IoTHubClient sample stopped by user")
        except Exception:
            print("Exception in main loop...")
            logging.debug(traceback.format_exc())
        finally:
            print("Shutting down IoTHubClient and exiting Application")
            await self.device_client.shutdown()


if __name__ == "__main__":
    asyncio.run(Application().main())
