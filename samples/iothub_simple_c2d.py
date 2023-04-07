# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This sample demonstrates a simple cloud to device receive using an IoTHubSession."""

import asyncio
import os
from azure.iot.device import IoTHubSession, MQTTError, MQTTConnectionFailedError

CONNECTION_STRING = os.getenv("IOTHUB_DEVICE_CONNECTION_STRING")
TOTAL_MESSAGES_RECEIVED = 0


async def main():
    global TOTAL_MESSAGES_RECEIVED
    print("Starting C2D sample")
    print("Press Ctrl-C to exit")
    try:
        print("Connecting to IoT Hub...")
        async with IoTHubSession.from_connection_string(CONNECTION_STRING) as session:
            print("Connected to IoT Hub")
            async with session.messages() as messages:
                print("Waiting to receive messages...")
                async for message in messages:
                    TOTAL_MESSAGES_RECEIVED += 1
                    print("Message received with payload: {}".format(message.payload))

    except MQTTError:
        # Connection has been lost.
        print("Dropped connection. Exiting")
    except MQTTConnectionFailedError:
        # Connection failed to be established.
        print("Could not connect. Exiting")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Exit application because user indicated they wish to exit.
        # This will have cancelled `main()` implicitly.
        print("User initiated exit. Exiting")
    finally:
        print("Received {} messages in total".format(TOTAL_MESSAGES_RECEIVED))
