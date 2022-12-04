# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import asyncio
import random
from azure.iot.device.aio import IoTHubModuleClient


async def main():
    # The client object is used to interact with your Azure IoT hub.
    module_client = IoTHubModuleClient.create_from_edge_environment()

    # connect the client.
    await module_client.connect()

    # update the reported properties
    reported_properties = {"temperature": random.randint(320, 800) / 10}
    print("Setting reported temperature to {}".format(reported_properties["temperature"]))
    await module_client.patch_twin_reported_properties(reported_properties)

    # Finally, shut down the client
    await module_client.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
