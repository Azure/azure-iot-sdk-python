# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This sample demonstrates a more complex scenario for use of the IoTHubSession.
This application both sends and receives data, and can be controlled via direct methods.
If the connection drops, it will try to establish one again until the user exits.
"""

import asyncio
import os
from azure.iot.device import (
    IoTHubSession,
    DirectMethodResponse,
    MQTTError,
    MQTTConnectionFailedError,
)


CONNECTION_STRING = os.getenv("IOTHUB_DEVICE_CONNECTION_STRING")
TOTAL_MESSAGES_SENT = 0
TOTAL_MESSAGES_RECEIVED = 0


def do_foo():
    print("FOO!")
    return True


def do_bar():
    print("BAR!")
    return True


async def send_telemetry(session):
    global TOTAL_MESSAGES_SENT
    while True:
        TOTAL_MESSAGES_SENT += 1
        print("Sending Message #{}.".format(TOTAL_MESSAGES_SENT))
        await session.send_message("Message #{}".format(TOTAL_MESSAGES_SENT))
        print("Send complete")
        await asyncio.sleep(5)


async def receive_c2d_messages(session):
    global TOTAL_MESSAGES_RECEIVED
    async with session.messages() as messages:
        print("Waiting to receive messages...")
        async for message in messages:
            TOTAL_MESSAGES_RECEIVED += 1
            print("Message received with payload: {}".format(message.payload))


async def receive_direct_method_requests(session):
    async with session.direct_method_requests() as method_requests:
        async for method_request in method_requests:
            if method_request.name == "foo":
                print("Direct Method request received for 'foo'. Invoking.")
                result = do_foo()
                payload = {"result": result}
                status = 200
                print("'foo' was completed with result: {}".format(result))
            elif method_request.name == "bar":
                print("Direct Method request received for 'bar'. Invoking.")
                result = do_bar()
                payload = {"result": result}
                status = 204
                print("'bar' was completed with result: {}".format(result))
            else:
                payload = {}
                status = 400
                print("Unknown Direct Method request received: {}".format(method_request.name))
            method_response = DirectMethodResponse.create_from_method_request(
                method_request, status, payload
            )
            await session.send_direct_method_response(method_response)


async def main():
    print("Starting multi-feature sample")
    print("Press Ctrl-C to exit")
    while True:
        try:
            print("Connecting to IoT Hub...")
            async with IoTHubSession.from_connection_string(CONNECTION_STRING) as session:
                print("Connected to IoT Hub")
                await asyncio.gather(
                    send_telemetry(session),
                    receive_c2d_messages(session),
                    receive_direct_method_requests(session),
                )

        except MQTTError:
            # Connection has been lost. Reconnect on next pass of loop.
            print("Dropped connection. Reconnecting in 1 second")
            await asyncio.sleep(1)
        except MQTTConnectionFailedError:
            # Connection failed to be established. Retry on next pass of loop.
            print("Could not connect. Retrying in 10 seconds")
            await asyncio.sleep(10)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Exit application because user indicated they wish to exit.
        # This will have cancelled `main()` implicitly.
        print("User initiated exit. Exiting.")
    finally:
        print("Sent {} messages in total.".format(TOTAL_MESSAGES_SENT))
        print("Received {} messages in total.".format(TOTAL_MESSAGES_RECEIVED))
