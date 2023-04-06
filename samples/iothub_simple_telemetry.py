# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This sample demonstrates a simple recurring telemetry using an IoTHubSession"""

import asyncio
import os
from azure.iot.device import IoTHubSession, MQTTError, MQTTConnectionFailedError

CONNECTION_STRING = os.getenv("IOTHUB_DEVICE_CONNECTION_STRING")


async def main():
    try:
        msg_count = 0
        async with IoTHubSession.from_connection_string(CONNECTION_STRING) as session:
            while True:
                msg_count += 1
                print("Sending Message #{}...".format(msg_count))
                await session.send_message("Message #{}".format(msg_count))
                await asyncio.sleep(5)

    except KeyboardInterrupt:
        print("User initiated exit. Exiting.")
    except MQTTError:
        print("Dropped connection. Exiting.")
    except MQTTConnectionFailedError:
        print("Could not connect. Exiting.")
    finally:
        print("Sent {} messages in total.".format(msg_count))


if __name__ == "__main__":
    asyncio.run(main())
