# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import asyncio
import pytest
import logging
import json
import dev_utils
from azure.iot.device.exceptions import OperationCancelled, ClientError

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

    @pytest.mark.it("Connects the transport if necessary")
    @pytest.mark.quicktest_suite
    async def test_connect_if_necessary(self, client, random_message, service_helper, leak_tracker):

        leak_tracker.set_initial_object_list()

        await client.disconnect()
        assert not client.connected

        await client.send_message(random_message)
        assert client.connected

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

        # TODO: investigate leak
        # leak_tracker.check_for_leaks()

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


@pytest.mark.dropped_connection
@pytest.mark.describe("Client send_message method with dropped connections")
@pytest.mark.keep_alive(5)
class TestSendMessageDroppedConnection(object):
    @pytest.mark.it("Sends if connection drops before sending")
    @pytest.mark.uses_iptables
    async def test_sends_if_drop_before_sending(
        self, client, random_message, dropper, service_helper, leak_tracker
    ):
        leak_tracker.set_initial_object_list()

        assert client.connected

        dropper.drop_outgoing()
        send_task = asyncio.ensure_future(client.send_message(random_message))

        while client.connected:
            await asyncio.sleep(1)

        assert not send_task.done()

        dropper.restore_all()
        while not client.connected:
            await asyncio.sleep(1)

        await send_task

        event = await service_helper.wait_for_eventhub_arrival(random_message.message_id)

        logger.info("sent from device= {}".format(random_message.data))
        logger.info("received at eventhub = {}".format(event.message_body))

        assert json.dumps(event.message_body) == random_message.data

        logger.info("Success")

        leak_tracker.check_for_leaks()

    @pytest.mark.it("Sends if connection rejects send")
    @pytest.mark.uses_iptables
    async def test_sends_if_reject_before_sending(
        self, client, random_message, dropper, service_helper, leak_tracker
    ):
        leak_tracker.set_initial_object_list()

        assert client.connected

        dropper.reject_outgoing()
        send_task = asyncio.ensure_future(client.send_message(random_message))

        while client.connected:
            await asyncio.sleep(1)

        assert not send_task.done()

        dropper.restore_all()
        while not client.connected:
            await asyncio.sleep(1)

        await send_task

        event = await service_helper.wait_for_eventhub_arrival(random_message.message_id)

        logger.info("sent from device= {}".format(random_message.data))
        logger.info("received at eventhub = {}".format(event.message_body))

        assert json.dumps(event.message_body) == random_message.data

        logger.info("Success")

        leak_tracker.check_for_leaks()


@pytest.mark.describe("Client send_message with reconnect disabled")
@pytest.mark.keep_alive(5)
@pytest.mark.connection_retry(False)
class TestSendMessageRetryDisabled(object):
    @pytest.fixture(scope="function", autouse=True)
    async def reconnect_after_test(self, dropper, client):
        yield
        dropper.restore_all()
        await client.connect()
        assert client.connected

    @pytest.mark.it("Can send a simple message")
    async def test_send_message_retry_disabled(
        self, client, random_message, service_helper, leak_tracker
    ):
        leak_tracker.set_initial_object_list()

        await client.send_message(random_message)

        event = await service_helper.wait_for_eventhub_arrival(random_message.message_id)
        assert json.dumps(event.message_body) == random_message.data

        leak_tracker.check_for_leaks()

    @pytest.mark.it("Automatically connects if transport manually disconnected before sending")
    async def test_connect_if_necessary_retry_disabled(
        self, client, random_message, service_helper, leak_tracker
    ):
        leak_tracker.set_initial_object_list()

        await client.disconnect()
        assert not client.connected

        await client.send_message(random_message)
        assert client.connected

        event = await service_helper.wait_for_eventhub_arrival(random_message.message_id)
        assert json.dumps(event.message_body) == random_message.data

        leak_tracker.check_for_leaks()

    @pytest.mark.it("Automatically connects if transport automatically disconnected before sending")
    @pytest.mark.uses_iptables
    async def test_connects_after_automatic_disconnect_retry_disabled(
        self, client, random_message, dropper, service_helper, leak_tracker
    ):
        leak_tracker.set_initial_object_list()

        assert client.connected

        dropper.drop_outgoing()
        while client.connected:
            await asyncio.sleep(1)

        assert not client.connected
        dropper.restore_all()
        await client.send_message(random_message)
        assert client.connected

        event = await service_helper.wait_for_eventhub_arrival(random_message.message_id)
        assert json.dumps(event.message_body) == random_message.data

        leak_tracker.check_for_leaks()

    @pytest.mark.it("Fails if connection disconnects before sending")
    @pytest.mark.uses_iptables
    async def test_fails_if_disconnect_before_sending(
        self, client, random_message, dropper, leak_tracker
    ):
        leak_tracker.set_initial_object_list()

        assert client.connected

        dropper.drop_outgoing()
        send_task = asyncio.ensure_future(client.send_message(random_message))

        while client.connected:
            await asyncio.sleep(1)

        with pytest.raises(OperationCancelled):
            await send_task

        random_message = None  # so this doesn't get tagged as a leak
        # TODO: investigate leak
        # leak_tracker.check_for_leaks()

    @pytest.mark.it("Fails if connection drops before sending")
    @pytest.mark.uses_iptables
    async def test_fails_if_drop_before_sending_retry_disabled(
        self, client, random_message, dropper, leak_tracker
    ):
        leak_tracker.set_initial_object_list()

        assert client.connected

        dropper.drop_outgoing()
        with pytest.raises(OperationCancelled):
            await client.send_message(random_message)

        assert not client.connected

        random_message = None  # so this doesn't get tagged as a leak
        # TODO: investigate leak
        # leak_tracker.check_for_leaks()
