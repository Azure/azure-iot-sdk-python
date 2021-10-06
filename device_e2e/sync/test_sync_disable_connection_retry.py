# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import pytest
import json
import logging
import time
from azure.iot.device.exceptions import OperationCancelled

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)


@pytest.mark.describe("Device Client send_message with reconnect disabled")
class TestSendMessageRetryDisabled(object):
    @pytest.fixture(scope="class")
    def extra_client_kwargs(self):
        return {"keep_alive": 5, "connection_retry": False}

    @pytest.fixture(scope="function", autouse=True)
    def reconnect_after_test(self, dropper, client):
        yield
        dropper.restore_all()
        client.connect()
        assert client.connected

    @pytest.mark.it("Can send a simple message")
    def test_send_message(self, client, random_message, get_next_eventhub_arrival):
        client.send_message(random_message)

        event = get_next_eventhub_arrival()
        assert json.dumps(event.message_body) == random_message.data

    @pytest.mark.it("Automatically connects if transport manually disconnected before sending")
    def test_connect_if_necessary(self, client, random_message, get_next_eventhub_arrival):

        client.disconnect()
        assert not client.connected

        client.send_message(random_message)
        assert client.connected

        event = get_next_eventhub_arrival()
        assert json.dumps(event.message_body) == random_message.data

    @pytest.mark.it("Automatically connects if transport automatically disconnected before sending")
    def test_connects_after_automatic_disconnect(
        self, client, random_message, dropper, get_next_eventhub_arrival
    ):

        assert client.connected

        dropper.drop_outgoing()
        while client.connected:
            time.sleep(1)

        assert not client.connected
        dropper.restore_all()
        client.send_message(random_message)
        assert client.connected

        event = get_next_eventhub_arrival()
        assert json.dumps(event.message_body) == random_message.data

    @pytest.mark.it("Fails if connection disconnects before sending")
    def test_fails_if_disconnect_before_sending(self, client, random_message, dropper, executor):

        assert client.connected

        dropper.drop_outgoing()
        send_task = executor.submit(client.send_message, random_message)

        while client.connected:
            time.sleep(1)

        with pytest.raises(OperationCancelled):
            send_task.result()

    @pytest.mark.it("Fails if connection drops before sending")
    def test_fails_if_drop_before_sending(self, client, random_message, dropper):

        assert client.connected

        dropper.drop_outgoing()
        with pytest.raises(OperationCancelled):
            client.send_message(random_message)

        assert not client.connected
