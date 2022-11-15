# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import asyncio
import pytest
import logging
import json
import dev_utils
from azure.iot.device.exceptions import OperationCancelled, ClientError, NoConnectionError

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)

pytestmark = pytest.mark.asyncio


@pytest.mark.describe("Client send_message method")
class TestSendMessage(object):
    @pytest.mark.it("Can send a simple message")
    @pytest.mark.quicktest_suite
    async def test_send_simple_message(self, client, random_message, service_helper, leak_tracker):

        leak_tracker.set_initial_object_list()

        await client.send_message(random_message)

        event = await service_helper.wait_for_eventhub_arrival(random_message.message_id)
        assert event.system_properties["message-id"] == random_message.message_id
        assert json.dumps(event.message_body) == random_message.data

        leak_tracker.check_for_leaks()

    @pytest.mark.it("Raises correct exception for un-serializable payload")
    async def test_bad_payload_raises(self, client, flush_messages, leak_tracker):
        leak_tracker.set_initial_object_list()

        # There's no way to serialize a function.
        def thing_that_cant_serialize():
            pass

        with pytest.raises(ClientError) as e_info:
            await client.send_message(thing_that_cant_serialize)
        assert isinstance(e_info.value.__cause__, TypeError)

        del e_info
        await flush_messages()
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

    @pytest.mark.it("Raises NoConnectionError if there is no connection")
    async def test_fails_if_no_connection(
        self, client, random_message, flush_messages, leak_tracker
    ):
        leak_tracker.set_initial_object_list()

        await client.disconnect()
        assert not client.connected

        with pytest.raises(NoConnectionError):
            await client.send_message(random_message)
        assert not client.connected

        await flush_messages()
        leak_tracker.check_for_leaks()


@pytest.mark.dropped_connection
@pytest.mark.describe(
    "Client send_message method with dropped connection (Connection Retry enabled)"
)
@pytest.mark.keep_alive(5)
class TestSendMessageDroppedConnectionRetryEnabled(object):
    @pytest.mark.it("Sends message once connection is restored after dropping outgoing packets")
    @pytest.mark.uses_iptables
    async def test_sends_if_drop_and_restore(
        self, client, random_message, dropper, service_helper, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Drop outgoing packets
        dropper.drop_outgoing()

        # Attempt to send a message
        send_task = asyncio.ensure_future(client.send_message(random_message))

        # Wait for client to realize connection has dropped
        while client.connected:
            await asyncio.sleep(0.5)
        # Even though the connection has dropped, the message send has not completed
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

    @pytest.mark.it("Sends message once connection is restored after rejecting outgoing packets")
    @pytest.mark.uses_iptables
    async def test_sends_if_reject_and_restore(
        self, client, random_message, dropper, service_helper, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Reject outgoing packets
        dropper.reject_outgoing()

        # Attempt to send a message
        send_task = asyncio.ensure_future(client.send_message(random_message))

        # Wait for client to realize connection has dropped
        while client.connected:
            await asyncio.sleep(0.5)
        # Even though the connection has dropped, the message send has not completed
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


@pytest.mark.describe(
    "Client send_message method with dropped connection (Connection Retry disabled)"
)
@pytest.mark.keep_alive(5)
@pytest.mark.connection_retry(False)
class TestSendMessageDroppedConnectionRetryDisabled(object):
    @pytest.mark.it("Raises OperationCancelled after dropping outgoing packets")
    @pytest.mark.uses_iptables
    async def test_raises_op_cancelled_if_drop(
        self, client, random_message, flush_messages, dropper, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Drop outgoing packets
        dropper.drop_outgoing()

        # Attempt to send a message
        send_task = asyncio.ensure_future(client.send_message(random_message))

        # Wait for client to realize connection has dropped
        while client.connected:
            assert not send_task.done()
            await asyncio.sleep(0.5)
        # (Almost) Immediately upon connection drop, the task is cancelled
        await asyncio.sleep(0.1)
        assert send_task.done()
        with pytest.raises(OperationCancelled):
            await send_task

        dropper.restore_all()
        del send_task
        await flush_messages()
        leak_tracker.check_for_leaks()

    @pytest.mark.it("Raises OperationCancelled after rejecting outgoing packets")
    @pytest.mark.uses_iptables
    async def test_raises_op_cancelled_if_reject(
        self, client, random_message, flush_messages, dropper, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Drop outgoing packets
        dropper.reject_outgoing()

        # Attempt to send a message
        send_task = asyncio.ensure_future(client.send_message(random_message))

        # Wait for client to realize connection has dropped
        while client.connected:
            assert not send_task.done()
            await asyncio.sleep(0.5)
        # (Almost) Immediately upon connection drop, the task is cancelled
        await asyncio.sleep(0.1)
        assert send_task.done()
        with pytest.raises(OperationCancelled):
            await send_task

        dropper.restore_all()
        del send_task
        await flush_messages()
        leak_tracker.check_for_leaks()
