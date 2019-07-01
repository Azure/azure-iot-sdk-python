# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import os
import uuid
from azure.iot.device.iothub.aio import IoTHubDeviceClient
from azure.iot.device.iothub import Message
from azure.iot.device.common import X509
import logging
import asyncio

logging.basicConfig(level=logging.ERROR)


messages_to_send = 10


async def main():
    hostname = os.getenv("HOSTNAME")
    # The device that has been created on the portal using X509 CA signing or Self signing capabilities
    device_id = os.getenv("DEVICE_ID")

    x509 = X509(
        cert_file=os.getenv("X509_CERT_FILE"),
        key_file=os.getenv("X509_KEY_FILE"),
        pass_phrase=os.getenv("PASS_PHRASE"),
    )

    # The client object is used to interact with your Azure IoT hub.
    device_client = IoTHubDeviceClient.create_from_x509_certificate(
        hostname=hostname, device_id=device_id, x509=x509
    )

    # Connect the client.
    await device_client.connect()

    async def send_test_message(i):
        print("sending message #" + str(i))
        msg = Message("test wind speed " + str(i))
        msg.message_id = uuid.uuid4()
        msg.correlation_id = "correlation-1234"
        msg.custom_properties["tornado-warning"] = "yes"
        await device_client.send_d2c_message(msg)
        print("done sending message #" + str(i))

    # send `messages_to_send` messages in parallel
    await asyncio.gather(*[send_test_message(i) for i in range(1, messages_to_send + 1)])

    # finally, disconnect
    await device_client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())

    # If using Python 3.6 or below, use the following code instead of asyncio.run(main()):
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(main())
    # loop.close()
