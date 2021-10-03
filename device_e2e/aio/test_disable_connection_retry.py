# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import asyncio
import pytest
import json
import logging
from azure.iot.device.exceptions import OperationCancelled

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)

pytestmark = pytest.mark.asyncio


@pytest.mark.describe("Device Client send_message with reconnect disabled")
class TestSendMessageRetryDisabled(object):
    @pytest.fixture(scope="class")
    def client_kwargs(self):
        return {"keep_alive": 5, "connection_retry": False}

    @pytest.fixture(scope="function", autouse=True)
    async def reconnect_after_test(self, dropper, client):
        yield
        dropper.restore_all()
        await client.connect()
        assert client.connected

    @pytest.mark.it("Can send a simple message")
    async def test_send_message(self, client, test_message, get_next_eventhub_arrival):
        await client.send_message(test_message)

        event = await get_next_eventhub_arrival()
        assert json.dumps(event.message_body) == test_message.data

    @pytest.mark.it("Automatically connects if transport manually disconnected before sending")
    async def test_connect_if_necessary(self, client, test_message, get_next_eventhub_arrival):

        await client.disconnect()
        assert not client.connected

        await client.send_message(test_message)
        assert client.connected

        event = await get_next_eventhub_arrival()
        assert json.dumps(event.message_body) == test_message.data

    @pytest.mark.it("Automatically connects if transport automatically disconnected before sending")
    async def test_connects_after_automatic_disconnect(
        self, client, test_message, dropper, get_next_eventhub_arrival
    ):

        assert client.connected

        dropper.drop_outgoing()
        while client.connected:
            await asyncio.sleep(1)

        assert not client.connected
        dropper.restore_all()
        await client.send_message(test_message)
        assert client.connected

        event = await get_next_eventhub_arrival()
        assert json.dumps(event.message_body) == test_message.data

    @pytest.mark.it("Fails if connection disconnects before sending")
    async def test_fails_if_disconnect_before_sending(self, client, test_message, dropper):

        assert client.connected

        dropper.drop_outgoing()
        send_task = asyncio.create_task(client.send_message(test_message))

        while client.connected:
            await asyncio.sleep(1)

        with pytest.raises(OperationCancelled):
            await send_task

    @pytest.mark.it("Fails if connection drops before sending")
    async def test_fails_if_drop_before_sending(self, client, test_message, dropper):

        assert client.connected

        dropper.drop_outgoing()
        with pytest.raises(OperationCancelled):
            await client.send_message(test_message)

        assert not client.connected
