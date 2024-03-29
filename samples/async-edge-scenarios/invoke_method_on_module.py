# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# -------------------------------------------------------------------------

import asyncio
from azure.iot.device.aio import IoTHubModuleClient

messages_to_send = 10


async def main():
    # Inputs/Outputs are only supported in the context of Azure IoT Edge and module client
    # The module client object acts as an Azure IoT Edge module and interacts with an Azure IoT Edge hub
    module_client = IoTHubModuleClient.create_from_edge_environment()

    # Connect the client.
    await module_client.connect()
    fake_method_params = {
        "methodName": "doSomethingInteresting",
        "payload": "foo",
        "responseTimeoutInSeconds": 5,
        "connectTimeoutInSeconds": 2,
    }
    response = await module_client.invoke_method(
        device_id="fakeDeviceId", module_id="fakeModuleId", method_params=fake_method_params
    )
    print("Method Response: {}".format(response))

    # Finally, shut down the client
    await module_client.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
