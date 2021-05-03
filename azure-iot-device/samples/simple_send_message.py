# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import os
import asyncio
from azure.iot.device.aio import IoTHubDeviceClient
import logging

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("paho").setLevel(level=logging.DEBUG)

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)


class FakeSocket:
    def send(self, *args, **kwargs):
        logger.error("send raising an exception!")
        raise Exception("send exception")

    def close(self, *args, **kwargs):
        logger.error("close raising an exception!")
        raise Exception("close exception!")


async def main():
    # Fetch the connection string from an enviornment variable
    conn_str = os.getenv("IOTHUB_DEVICE_CONNECTION_STRING")

    # Create instance of the device client using the connection string
    device_client = IoTHubDeviceClient.create_from_connection_string(conn_str, keep_alive=10)

    # Connect the device client.
    await device_client.connect()

    # Send a single message
    logger.info("Sending message...")
    await device_client.send_message("This is a message that is being sent")
    logger.info("Message successfully sent!")

    # Kill the connection
    stage = device_client._mqtt_pipeline._pipeline.next
    while not hasattr(stage, "transport"):
        stage = stage.next
    paho = stage.transport._mqtt_client
    paho._sockpairW = FakeSocket()
    logger.info("failure inserted")

    t = 40
    logger.info("sleeping for {} seconds".format(t))
    await asyncio.sleep(t)
    logger.info("done sleeping")

    try:
        logger.info("Sending another message...")
        await device_client.send_message("This is a message that is being sent")
        logger.info("Message successfully sent!")
    except Exception as e:
        logger.error("send Error: {}".format(str(e) or type(e)))

    # Finally, shut down the client
    logger.info("Disconnecting")
    await device_client.disconnect()
    logger.info("Done disconnecting")

    logger.info("cleanup complete")


if __name__ == "__main__":
    asyncio.run(main())

    # If using Python 3.6 or below, use the following code instead of asyncio.run(main()):
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(main())
    # loop.close()
