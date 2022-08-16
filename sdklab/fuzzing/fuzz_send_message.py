# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import asyncio
import logging
import argparse
import paho_fuzz_hook
from azure.iot.device.aio import IoTHubDeviceClient
from dev_utils import test_env, random_content
from dev_utils.service_helper import ServiceHelper

logging.basicConfig(level=logging.WARNING)
logging.getLogger("e2e").setLevel(level=logging.INFO)

"""
This tool does limited "fuzzing" of the client library by by injecting various
failures into the sockets that Paho uses. The set of failures is limited and are
described in the `fuzz_type_help` string below. Some of these "failures" are
problems that might occur at the network level, such as lost packets and dropped
connections, and other "failures" are exceptions that are raised from lower components.

Calling this "fuzzing" is a misnomer. While this code "injects random failures" into
the transport, that set of random failures are based on scenarios that we except might happen.
The fact that we're guessing the types of failures that might happen limits the scope
of testing, but it still provides value.
"""


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
drop_individual_incoming_packets = 4
raise_send_exception = 5
raise_receive_exception = 6

fuzz_type_help = """
1: drop_outgoing_packets_until_reconnect
   Simulates failures where the transport connection drops all outgoing packets
   until the network socket is closed and re-opened. This simulates a
   "broken output pipe".

2: drop_individual_outgoing_packets
   Simulates loss of individual outgoing packets. This simulates scenarios
   where individual outgoing messages are lost, but the connection isn't
   necessarily "broken".

3: drop_incoming_packets_until_reconnect
   Simulates failures where the transport connection drops all incoming packets
   until the network socket is closed and re-opened. This simulates a
   "broken input pipe".

4: drop_individual_incoming_packets
   Simulates the loss of individual incoming packets. This simulates scenarios
   where individual incoming messages are lost, but the connection isn't necessarily
   "broken"

5: raise_send_exception
   Simulates a failure where the call into the transport socket `send` function raises
   an exception. This simulates low-level socket failures on the outgoing socket.

6: raise_receive_exception
   Simulates a failure where the call into the transport socket `recv` function raises
   an exception. This simulates low-level socket failures on the incoming socket.
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

    paho_fuzz_hook.add_paho_logging_hook(device_client)

    try:

        # Connect the device client.
        print("connecting")
        await device_client.connect()

        # Start fuzzing after the client is connected
        if fuzz_type == drop_outgoing_packets_until_reconnect:
            paho_fuzz_hook.add_hook_drop_outgoing_until_reconnect(device_client, 0.05)
        elif fuzz_type == drop_individual_outgoing_packets:
            paho_fuzz_hook.add_hook_drop_individual_outgoing(device_client, 0.05)
        elif fuzz_type == drop_incoming_packets_until_reconnect:
            # probability for incoming is calculated on every byte, so it needs to be much lower
            paho_fuzz_hook.add_hook_drop_incoming_until_reconnect(device_client, 0.001)
        elif fuzz_type == drop_individual_incoming_packets:
            paho_fuzz_hook.add_hook_drop_individual_incoming(device_client, 0.05)
        elif fuzz_type == raise_send_exception:
            paho_fuzz_hook.add_hook_raise_send_exception(device_client, 0.05)
        elif fuzz_type == raise_receive_exception:
            paho_fuzz_hook.add_hook_raise_receive_exception(device_client, 0.05)
        else:
            assert False

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
