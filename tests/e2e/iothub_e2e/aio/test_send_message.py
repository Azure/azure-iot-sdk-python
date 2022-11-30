# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import asyncio
import pytest
import logging
import json
import dev_utils
from azure.iot.device.exceptions import ClientError

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)


PACKET_DROP = "Packet Drop"
PACKET_REJECT = "Packet Reject"


@pytest.fixture(params=[PACKET_DROP, PACKET_REJECT])
def failure_type(request):
    return request.param


@pytest.mark.describe("Client send_message method")
class TestSendMessage(object):
    @pytest.mark.it("Can send a simple message")
    @pytest.mark.quicktest_suite
    async def test_send_message_simple(self, client, random_message, service_helper, leak_tracker):
        leak_tracker.set_initial_object_list()

        await client.send_message(random_message)

        event = await service_helper.wait_for_eventhub_arrival(random_message.message_id)
        assert json.dumps(event.message_body) == random_message.data

        leak_tracker.check_for_leaks()

    @pytest.mark.it("Raises correct exception for un-serializable payload")
    async def test_bad_payload_raises(self, client, leak_tracker):
        leak_tracker.set_initial_object_list()

        # There's no way to serialize a function.
        def thing_that_cant_serialize():
            pass

        with pytest.raises(ClientError) as e_info:
            await client.send_message(thing_that_cant_serialize)
        assert isinstance(e_info.value.__cause__, TypeError)

        del e_info
        # TODO: Why does this need a sleep, but the sync test doesn't?
        # There might be something here, investigate further
        await asyncio.sleep(0.1)
        leak_tracker.check_for_leaks()

    @pytest.mark.it("Can send a JSON-formatted string that isn't wrapped in a Message object")
    async def test_sends_json_string(self, client, service_helper, leak_tracker):
        leak_tracker.set_initial_object_list()

        message = json.dumps(dev_utils.get_random_dict())

        await client.send_message(message)

        event = await service_helper.wait_for_eventhub_arrival(None)
        assert json.dumps(event.message_body) == message

        leak_tracker.check_for_leaks()

    @pytest.mark.it("Can send a random string that isn't wrapped in a Message object")
    async def test_sends_random_string(self, client, service_helper, leak_tracker):
        leak_tracker.set_initial_object_list()

        message = dev_utils.get_random_string(16)

        await client.send_message(message)

        event = await service_helper.wait_for_eventhub_arrival(None)
        assert event.message_body == message

        leak_tracker.check_for_leaks()

    @pytest.mark.it("Waits until a connection is established to send if there is no connection")
    async def test_fails_if_no_connection(
        self, client, random_message, service_helper, leak_tracker
    ):
        leak_tracker.set_initial_object_list()

        await client.disconnect()
        assert not client.connected

        # Attempt to send a message
        send_task = asyncio.ensure_future(client.send_message(random_message))
        await asyncio.sleep(1)
        # Still not done
        assert not send_task.done()
        # Connect
        await client.connect()
        await asyncio.sleep(0.5)
        # Task is now done
        assert send_task.done()

        event = await service_helper.wait_for_eventhub_arrival(random_message.message_id)
        assert json.dumps(event.message_body) == random_message.data

        leak_tracker.check_for_leaks()


@pytest.mark.describe("Client send_message method with network failure (Connection Retry enabled)")
@pytest.mark.dropped_connection
@pytest.mark.connection_retry(True)
@pytest.mark.keep_alive(5)
class TestSendMessageNetworkFailureConnectionRetryEnabled(object):
    @pytest.mark.it(
        "Succeeds once network is restored and client automatically reconnects after having disconnected due to network failure"
    )
    @pytest.mark.uses_iptables
    async def test_network_failure_causes_disconnect(
        self, client, random_message, failure_type, dropper, service_helper, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Disrupt network
        if failure_type == PACKET_DROP:
            dropper.drop_outgoing()
        elif failure_type == PACKET_REJECT:
            dropper.reject_outgoing()

        # Attempt to send a message
        send_task = asyncio.ensure_future(client.send_message(random_message))

        # Wait for client to disconnect
        while client.connected:
            assert not send_task.done()
            await asyncio.sleep(0.5)
        # Client has now disconnected and task will not finish until reconnection
        assert not send_task.done()

        # Restore outgoing packet functionality and wait for client to reconnect
        dropper.restore_all()
        while not client.connected:
            await asyncio.sleep(0.5)
        # Wait for the send task to complete now that the client has reconnected
        await send_task

        # Ensure the sent message was received by the service
        event = await service_helper.wait_for_eventhub_arrival(random_message.message_id)
        assert json.dumps(event.message_body) == random_message.data

        leak_tracker.check_for_leaks()

    @pytest.mark.it("Succeeds if network failure resolves before client can disconnect")
    async def test_network_failure_no_disconnect(
        self, client, random_message, failure_type, dropper, service_helper, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Disrupt network
        if failure_type == PACKET_DROP:
            dropper.drop_outgoing()
        elif failure_type == PACKET_REJECT:
            dropper.reject_outgoing()

        # Attempt to send a message
        send_task = asyncio.ensure_future(client.send_message(random_message))

        # Has not been able to succeed due to network failure, but client is still connected
        await asyncio.sleep(1)
        assert not send_task.done()
        assert client.connected

        # Restore network, and operation succeeds
        dropper.restore_all()
        await send_task

        # Ensure the sent message was received by the service
        event = await service_helper.wait_for_eventhub_arrival(random_message.message_id)
        assert json.dumps(event.message_body) == random_message.data

        leak_tracker.check_for_leaks()


@pytest.mark.describe("Client send_message method with network failure (Connection Retry disabled)")
@pytest.mark.dropped_connection
@pytest.mark.connection_retry(False)
@pytest.mark.keep_alive(5)
class TestSendMessageNetworkFailureConnectionRetryDisabled(object):
    @pytest.mark.it(
        "Succeeds once network is restored and client manually reconnects after having disconnected due to network failure"
    )
    async def test_network_failure_causes_disconnect(
        self, client, random_message, failure_type, service_helper, dropper, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Disrupt network
        if failure_type == PACKET_DROP:
            dropper.drop_outgoing()
        elif failure_type == PACKET_REJECT:
            dropper.reject_outgoing()

        # Attempt to send a message
        send_task = asyncio.ensure_future(client.send_message(random_message))

        # Wait for client disconnect
        while client.connected:
            assert not send_task.done()
            await asyncio.sleep(0.5)
        # Client has now disconnected and task will not finish until reconnection
        assert not send_task.done()
        await asyncio.sleep(1)
        assert not send_task.done()

        # Restore network and manually connect
        dropper.restore_all()
        await client.connect()

        await send_task

        # Ensure the sent message was received by the service
        event = await service_helper.wait_for_eventhub_arrival(random_message.message_id)
        assert json.dumps(event.message_body) == random_message.data

        dropper.restore_all()
        leak_tracker.check_for_leaks()

    @pytest.mark.it("Succeeds if network failure resolves before client can disconnect")
    async def test_network_failure_no_disconnect(
        self, client, random_message, failure_type, service_helper, dropper, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Disrupt network
        if failure_type == PACKET_DROP:
            dropper.drop_outgoing()
        elif failure_type == PACKET_REJECT:
            dropper.reject_outgoing()

        # Attempt to send a message
        send_task = asyncio.ensure_future(client.send_message(random_message))

        # Has not been able to succeed due to network failure, but client is still connected
        await asyncio.sleep(1)
        assert not send_task.done()
        assert client.connected

        # Restore network, and operation succeeds
        dropper.restore_all()
        await send_task

        # Ensure the sent message was received by the service
        event = await service_helper.wait_for_eventhub_arrival(random_message.message_id)
        assert json.dumps(event.message_body) == random_message.data

        leak_tracker.check_for_leaks()
