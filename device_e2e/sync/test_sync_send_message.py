# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import pytest
import logging
import json
import time

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)


@pytest.mark.describe("Device Client send_message method")
class TestSendMessage(object):
    @pytest.mark.it("Can send a simple message")
    def test_send_message(self, client, random_message, get_next_eventhub_arrival):

        client.send_message(random_message)

        event = get_next_eventhub_arrival()
        assert json.dumps(event.message_body) == random_message.data

    @pytest.mark.it("Connects the transport if necessary")
    def test_connect_if_necessary(self, client, random_message, get_next_eventhub_arrival):

        client.disconnect()
        assert not client.connected

        client.send_message(random_message)
        assert client.connected

        event = get_next_eventhub_arrival()
        assert json.dumps(event.message_body) == random_message.data


@pytest.mark.dropped_connection
@pytest.mark.describe("Device Client send_message method with dropped connections")
class TestSendMessageDroppedConnection(object):
    @pytest.fixture(scope="class")
    def extra_client_kwargs(self):
        return {"keep_alive": 5}

    @pytest.mark.it("Sends if connection drops before sending")
    def test_sends_if_drop_before_sending(
        self, client, random_message, dropper, get_next_eventhub_arrival, executor
    ):

        assert client.connected

        dropper.drop_outgoing()
        send_task = executor.submit(client.send_message, random_message)

        while client.connected:
            time.sleep(1)

        assert not send_task.done()

        dropper.restore_all()
        while not client.connected:
            time.sleep(1)

        send_task.result()

        event = get_next_eventhub_arrival()
        assert json.dumps(event.message_body) == random_message.data

    @pytest.mark.it("Sends if connection rejects send")
    def test_sends_if_reject_before_sending(
        self, client, random_message, dropper, get_next_eventhub_arrival, executor
    ):

        assert client.connected

        dropper.reject_outgoing()
        send_task = executor.submit(client.send_message, random_message)

        while client.connected:
            time.sleep(1)

        assert not send_task.done()

        dropper.restore_all()
        while not client.connected:
            time.sleep(1)

        send_task.result()

        event = get_next_eventhub_arrival()
        assert json.dumps(event.message_body) == random_message.data
