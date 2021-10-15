# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import pytest
import logging
import json
import time
import uuid
from azure.iot.device.exceptions import OperationCancelled

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)


@pytest.mark.describe("ServiceHelper object")
class TestServiceHelper(object):
    @pytest.mark.it("returns None when wait_for_event_arrival times out")
    def test_send_message(self, client, random_message, service_helper):

        event = service_helper.wait_for_eventhub_arrival(uuid.uuid4(), timeout=2)
        assert event is None


@pytest.mark.describe("Client send_message method")
class TestSendMessage(object):
    @pytest.mark.it("Can send a simple message")
    def test_send_message(self, client, random_message, service_helper):

        client.send_message(random_message)

        event = service_helper.wait_for_eventhub_arrival(random_message.message_id)
        assert json.dumps(event.message_body) == random_message.data

    @pytest.mark.it("Connects the transport if necessary")
    def test_connect_if_necessary(self, client, random_message, service_helper):

        client.disconnect()
        assert not client.connected

        client.send_message(random_message)
        assert client.connected

        event = service_helper.wait_for_eventhub_arrival(random_message.message_id)
        assert json.dumps(event.message_body) == random_message.data


@pytest.mark.dropped_connection
@pytest.mark.describe("Client send_message method with dropped connections")
class TestSendMessageDroppedConnection(object):
    @pytest.fixture(scope="class")
    def extra_client_kwargs(self):
        return {"keep_alive": 5}

    @pytest.mark.it("Sends if connection drops before sending")
    @pytest.mark.uses_iptables
    def test_sends_if_drop_before_sending(
        self, client, random_message, dropper, service_helper, executor
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

        event = service_helper.wait_for_eventhub_arrival(random_message.message_id)
        assert json.dumps(event.message_body) == random_message.data

    @pytest.mark.it("Sends if connection rejects send")
    @pytest.mark.uses_iptables
    def test_sends_if_reject_before_sending(
        self, client, random_message, dropper, service_helper, executor
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

        event = service_helper.wait_for_eventhub_arrival(random_message.message_id)
        assert json.dumps(event.message_body) == random_message.data


@pytest.mark.describe("Client send_message with reconnect disabled")
@pytest.mark.dont_run_this_if_you_want_your_tests_to_go_fast
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
    def test_send_message(self, client, random_message, service_helper):
        client.send_message(random_message)

        event = service_helper.wait_for_eventhub_arrival(random_message.message_id)
        assert json.dumps(event.message_body) == random_message.data

    @pytest.mark.it("Automatically connects if transport manually disconnected before sending")
    def test_connect_if_necessary(self, client, random_message, service_helper):

        client.disconnect()
        assert not client.connected

        client.send_message(random_message)
        assert client.connected

        event = service_helper.wait_for_eventhub_arrival(random_message.message_id)
        assert json.dumps(event.message_body) == random_message.data

    @pytest.mark.it("Automatically connects if transport automatically disconnected before sending")
    @pytest.mark.uses_iptables
    def test_connects_after_automatic_disconnect(
        self, client, random_message, dropper, service_helper
    ):

        assert client.connected

        dropper.drop_outgoing()
        while client.connected:
            time.sleep(1)

        assert not client.connected
        dropper.restore_all()
        client.send_message(random_message)
        assert client.connected

        event = service_helper.wait_for_eventhub_arrival(random_message.message_id)
        assert json.dumps(event.message_body) == random_message.data

    @pytest.mark.it("Fails if connection disconnects before sending")
    @pytest.mark.uses_iptables
    def test_fails_if_disconnect_before_sending(self, client, random_message, dropper, executor):

        assert client.connected

        dropper.drop_outgoing()
        send_task = executor.submit(client.send_message, random_message)

        while client.connected:
            time.sleep(1)

        with pytest.raises(OperationCancelled):
            send_task.result()

    @pytest.mark.it("Fails if connection drops before sending")
    @pytest.mark.uses_iptables
    def test_fails_if_drop_before_sending(self, client, random_message, dropper):

        assert client.connected

        dropper.drop_outgoing()
        with pytest.raises(OperationCancelled):
            client.send_message(random_message)

        assert not client.connected
