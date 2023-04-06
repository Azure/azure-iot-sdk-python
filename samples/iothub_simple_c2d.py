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


async def main():
    try:
        msg_count = 0
        async with IoTHubSession.from_connection_string(CONNECTION_STRING) as session:
            async with session.messages() as messages:
                async for message in messages:
                    msg_count += 1
                    print("Message received with payload: {}".format(message.payload))

    except KeyboardInterrupt:
        print("User initiated exit. Exiting.")
    except MQTTError:
        print("Dropped connection. Exiting.")
    except MQTTConnectionFailedError:
        print("Could not connect. Exiting.")
    finally:
        print("Received {} messages in total.".format(msg_count))


if __name__ == "__main__":
    asyncio.run(main())
