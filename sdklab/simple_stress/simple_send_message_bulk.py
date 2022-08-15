# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import asyncio
import logging
from azure.iot.device.aio import IoTHubDeviceClient
from dev_utils import test_env, random_content
from dev_utils.service_helper import ServiceHelper

logging.basicConfig(level=logging.WARNING)
logging.getLogger("e2e").setLevel(level=logging.INFO)


async def queue_send_messages(device_client, messages_to_send):
    messages = [random_content.get_random_message() for _ in range(0, messages_to_send)]
    message_ids = [m.message_id for m in messages]

    send_tasks = [asyncio.create_task(device_client.send_message(m)) for m in messages]

    return (send_tasks, message_ids)


async def wait_for_messages(service_helper, message_ids):
    count_received = 0
    while len(message_ids):
        message = await service_helper.wait_for_eventhub_arrival(message_id=None)
        message_ids.remove(message.message_id)
        count_received += 1
        print("received={}, remaining={}".format(count_received, len(message_ids)))


async def main():
    device_client = IoTHubDeviceClient.create_from_connection_string(
        test_env.DEVICE_CONNECTION_STRING
    )
    service_helper = ServiceHelper(
        iothub_connection_string=test_env.IOTHUB_CONNECTION_STRING,
        eventhub_connection_string=test_env.EVENTHUB_CONNECTION_STRING,
        eventhub_consumer_group=test_env.EVENTHUB_CONSUMER_GROUP,
    )
    # logging_hook.hook_device_client(device_client)

    # Connect the device client.
    print("connecting")
    await device_client.connect()

    # TOOD: can we add device_id and module_id attributes on the client?
    service_helper.set_identity(
        device_id=device_client._mqtt_pipeline.pipeline_configuration.device_id,
        module_id=device_client._mqtt_pipeline.pipeline_configuration.module_id,
    )

    print("sleeping to let eventhub consumers spin up correctly")
    await asyncio.sleep(5)

    print("sending 1000 messages")
    (send_tasks, message_ids) = await queue_send_messages(device_client, 1000)
    await asyncio.gather(*send_tasks)
    print("done sending")

    print("waiting")
    await wait_for_messages(service_helper, message_ids)

    print("Shutting down device client")
    await device_client.shutdown()

    print("Shutting down service helper")
    await service_helper.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
