# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import os
import uuid
from azure.iot.device.aio import IoTHubModuleClient
from azure.iot.device import Message, X509
import asyncio


messages_to_send = 10


async def main():
    hostname = os.getenv("HOSTNAME")

    # The device having a certain module that has been created on the portal
    # using X509 CA signing or Self signing capabilities

    device_id = os.getenv("DEVICE_ID")
    module_id = os.getenv("MODULE_ID")

    x509 = X509(
        cert_file=os.getenv("X509_CERT_FILE"),
        key_file=os.getenv("X509_KEY_FILE"),
        pass_phrase=os.getenv("PASS_PHRASE"),
    )

    module_client = IoTHubModuleClient.create_from_x509_certificate(
        hostname=hostname, x509=x509, device_id=device_id, module_id=module_id
    )

    # Connect the client.
    await module_client.connect()

    async def send_test_message(i):
        print("sending message #" + str(i))
        msg = Message("test wind speed " + str(i))
        msg.message_id = uuid.uuid4()
        msg.correlation_id = "correlation-1234"
        msg.custom_properties["tornado-warning"] = "yes"
        await module_client.send_message(msg)
        print("done sending message #" + str(i))

    await asyncio.gather(*[send_test_message(i) for i in range(1, messages_to_send + 1)])

    # finally, disconnect
    await module_client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())

    # If using Python 3.6 or below, use the following code instead of asyncio.run(main()):
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(main())
    # loop.close()
