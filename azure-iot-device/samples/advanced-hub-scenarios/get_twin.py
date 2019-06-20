# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import os
import asyncio
import logging
from azure.iot.device.aio import IoTHubDeviceClient
from azure.iot.device import auth

# logging.basicConfig(level=logging.DEBUG)


async def main():
    conn_str = os.getenv("IOTHUB_DEVICE_CONNECTION_STRING")
    device_client = IoTHubDeviceClient.create_from_connection_string(conn_str)

    # connect the client.
    await device_client.connect()

    # get the twin
    twin = await device_client.get_twin()
    print("Reported temperature is {}".format(twin["reported"]["temperature"]))

    # Finally, disconnect
    await device_client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())

    # If using Python 3.6 or below, use the following code instead of asyncio.run(main()):
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(main())
    # loop.close()
