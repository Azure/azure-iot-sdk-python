# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import asyncio
import time
import uuid
from azure.iot.device.aio import IoTHubModuleClient
from azure.iot.device import Message

messages_to_send = 10


async def main():
    # Inputs/Ouputs are only supported in the context of Azure IoT Edge and module client
    # The module client object acts as an Azure IoT Edge module and interacts with an Azure IoT Edge hub
    module_client = IoTHubModuleClient.create_from_edge_environment()

    # Connect the client.
    await module_client.connect()

    # TODO: ALL OF THIS!!!!

    # finally, disconnect
    module_client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())

    # If using Python 3.6 or below, use the following code instead of asyncio.run(main()):
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(main())
    # loop.close()
