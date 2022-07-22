# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import asyncio
import logging
import test_env
import paho_fuzz_hook
import random_content
import argparse
from azure.iot.device.aio import IoTHubDeviceClient
from service_helper import ServiceHelper

logging.basicConfig(level=logging.WARNING)
logging.getLogger("e2e").setLevel(level=logging.INFO)


async def queue_send_messages(device_client, messages_to_send=60):
    messages = [random_content.get_random_message() for _ in range(0, messages_to_send)]
    message_ids = [m.message_id for m in messages]

    send_tasks = [asyncio.create_task(device_client.send_message(m)) for m in messages]

    return (send_tasks, message_ids)


async def wait_for_messages(service_helper, message_ids):
    count_received = 0
    while len(message_ids):
        message = await service_helper.wait_for_eventhub_arrival(message_id=None)
        if message.message_id in message_ids:
            message_ids.remove(message.message_id)
        count_received += 1
        print("received={}, remaining={}".format(count_received, len(message_ids)))


drop_outgoing_packets_until_reconnect = 1
drop_individual_outgoing_packets = 2
drop_incoming_packets_until_reconnect = 3
flush_incoming_packet_queue = 4
raise_send_exception = 5
raise_receive_exception = 6

fuzz_type_help = """
drop_outgoing_packets_until_reconnect = 1
drop_individual_outgoing_packets = 2
drop_incoming_packets_until_reconnect = 3
flush_incoming_packet_queue = 4
raise_send_exception = 5
raise_receive_exception = 6
"""


async def main(fuzz_type):
    device_client = IoTHubDeviceClient.create_from_connection_string(
        test_env.DEVICE_CONNECTION_STRING, keep_alive=15
    )
    service_helper = ServiceHelper(
        iothub_connection_string=test_env.IOTHUB_CONNECTION_STRING,
        eventhub_connection_string=test_env.EVENTHUB_CONNECTION_STRING,
        eventhub_consumer_group=test_env.EVENTHUB_CONSUMER_GROUP,
    )

    if fuzz_type == drop_outgoing_packets_until_reconnect:
        paho_fuzz_hook.add_hook_drop_outgoing_until_reconnect(device_client, 0.05)
    elif fuzz_type == drop_individual_outgoing_packets:
        paho_fuzz_hook.add_hook_drop_individual_outgoing(device_client, 0.05)
    elif fuzz_type == drop_incoming_packets_until_reconnect:
        # probability for incoming is calculated on every byte, so it needs to be much lower
        paho_fuzz_hook.add_hook_drop_incoming_until_reconnect(device_client, 0.001)
    elif fuzz_type == flush_incoming_packet_queue:
        paho_fuzz_hook.add_hook_flush_incoming_packet_queue(device_client, 0.05)
    elif fuzz_type == raise_send_exception:
        paho_fuzz_hook.add_hook_raise_send_exception(device_client, 0.05)
    elif fuzz_type == raise_receive_exception:
        paho_fuzz_hook.add_hook_raise_receive_exception(device_client, 0.05)
    else:
        assert False

    paho_fuzz_hook.add_paho_logging_hook(device_client)

    try:

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

        print("sending")
        (send_tasks, message_ids) = await queue_send_messages(device_client)
        await asyncio.gather(*send_tasks)
        print("done sending")

        print("waiting")
        await wait_for_messages(service_helper, message_ids)

    finally:
        print("Shutting down service helper")
        await service_helper.shutdown()

        print("Shutting down device client")
        await device_client.shutdown()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="fuzz_send_message")
    parser.add_argument("fuzz_type", type=int, choices=range(1, 7), help=fuzz_type_help)
    args = parser.parse_args()
    asyncio.run(main(args.fuzz_type))
