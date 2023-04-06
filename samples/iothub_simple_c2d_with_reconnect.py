# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This sample demonstrates a simple cloud to device receive using an IoTHubSession.
If the connection drops, it will try to establish one again until the user exits.
"""

import asyncio
import os
from azure.iot.device import IoTHubSession, MQTTError, MQTTConnectionFailedError

CONNECTION_STRING = os.getenv("IOTHUB_DEVICE_CONNECTION_STRING")


def do_foo():
    return "done"


async def main():
    msg_count = 0
    while True:
        try:
            async with IoTHubSession.from_connection_string(CONNECTION_STRING) as session:
                async with session.messages() as messages:
                    async for message in messages:
                        msg_count += 1
                        print("Message received with payload: {}".format(message.payload))

        except KeyboardInterrupt:
            # Exit application because user indicated they wish to exit.
            print("User initiated exit. Exiting.")
            print("Received {} messages in total.".format(msg_count))
            raise
        except MQTTError:
            # Connection has been lost. Reconnect on next pass of loop.
            print("Dropped connection. Reconnecting in 1 second")
            await asyncio.sleep(1)
        except MQTTConnectionFailedError:
            # Connection failed to be established. Retry on next pass of loop.
            print("Could not connect. Retrying in 10 seconds")
            await asyncio.sleep(10)


if __name__ == "__main__":
    asyncio.run(main())
