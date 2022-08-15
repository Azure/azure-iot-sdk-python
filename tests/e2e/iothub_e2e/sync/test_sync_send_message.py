# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import pytest
import logging
import json
import time
import dev_utils
from azure.iot.device.exceptions import OperationCancelled, ClientError

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)


@pytest.mark.describe("Client send_message method")
class TestSendMessage(object):
    @pytest.mark.it("Can send a simple message")
    @pytest.mark.quicktest_suite
    def test_sync_send_message_simple(self, client, random_message, service_helper, leak_tracker):
        leak_tracker.set_initial_object_list()

        client.send_message(random_message)

        event = service_helper.wait_for_eventhub_arrival(random_message.message_id)
        assert json.dumps(event.message_body) == random_message.data

        leak_tracker.check_for_leaks()

    @pytest.mark.it("Connects the transport if necessary")
    @pytest.mark.quicktest_suite
    def test_sync_connect_if_necessary(self, client, random_message, service_helper, leak_tracker):
        leak_tracker.set_initial_object_list()

        client.disconnect()
        assert not client.connected

        client.send_message(random_message)
        assert client.connected

        event = service_helper.wait_for_eventhub_arrival(random_message.message_id)
        assert json.dumps(event.message_body) == random_message.data

        leak_tracker.check_for_leaks()

    @pytest.mark.it("Raises correct exception for un-serializable payload")
    def test_sync_bad_payload_raises(self, client, leak_tracker):
        leak_tracker.set_initial_object_list()

        # There's no way to serialize a function.
        def thing_that_cant_serialize():
            pass

        with pytest.raises(ClientError) as e_info:
            client.send_message(thing_that_cant_serialize)
        assert isinstance(e_info.value.__cause__, TypeError)

        # TODO; investigate this leak
        # leak_tracker.check_for_leaks()

    @pytest.mark.it("Can send a JSON-formatted string that isn't wrapped in a Message object")
    def test_sync_sends_json_string(self, client, service_helper, leak_tracker):
        leak_tracker.set_initial_object_list()

        message = json.dumps(dev_utils.get_random_dict())

        client.send_message(message)

        event = service_helper.wait_for_eventhub_arrival(None)
        assert json.dumps(event.message_body) == message

        leak_tracker.check_for_leaks()

    @pytest.mark.it("Can send a random string that isn't wrapped in a Message object")
    def test_sync_sends_random_string(self, client, service_helper, leak_tracker):
        leak_tracker.set_initial_object_list()

        message = dev_utils.get_random_string(16)

        client.send_message(message)

        event = service_helper.wait_for_eventhub_arrival(None)
        assert event.message_body == message

        leak_tracker.check_for_leaks()


@pytest.mark.dropped_connection
@pytest.mark.describe("Client send_message method with dropped connections")
@pytest.mark.keep_alive(5)
class TestSendMessageDroppedConnection(object):
    @pytest.mark.it("Sends if connection drops before sending")
    @pytest.mark.uses_iptables
    def test_sync_sends_if_drop_before_sending(
        self, client, random_message, dropper, service_helper, executor, leak_tracker
    ):
        leak_tracker.set_initial_object_list()

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

        random_message = None  # so this doesn't get tagged as a leak
        leak_tracker.check_for_leaks()

    @pytest.mark.it("Sends if connection rejects send")
    @pytest.mark.uses_iptables
    def test_sync_sends_if_reject_before_sending(
        self, client, random_message, dropper, service_helper, executor, leak_tracker
    ):
        leak_tracker.set_initial_object_list()

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

        random_message = None  # so this doesn't get tagged as a leak
        leak_tracker.check_for_leaks()


@pytest.mark.describe("Client send_message with reconnect disabled")
@pytest.mark.keep_alive(5)
@pytest.mark.connection_retry(False)
class TestSendMessageRetryDisabled(object):
    @pytest.fixture(scope="function", autouse=True)
    def reconnect_after_test(self, dropper, client):
        yield
        dropper.restore_all()
        client.connect()
        assert client.connected

    @pytest.mark.it("Can send a simple message")
    def test_sync_send_message_simple_with_retry_disabled(
        self, client, random_message, service_helper, leak_tracker
    ):
        leak_tracker.set_initial_object_list()

        client.send_message(random_message)

        event = service_helper.wait_for_eventhub_arrival(random_message.message_id)
        assert json.dumps(event.message_body) == random_message.data

        leak_tracker.check_for_leaks()

    @pytest.mark.it("Automatically connects if transport manually disconnected before sending")
    def test_sync_connect_if_necessary_with_retry_disabled(
        self, client, random_message, service_helper, leak_tracker
    ):
        leak_tracker.set_initial_object_list()

        client.disconnect()
        assert not client.connected

        client.send_message(random_message)
        assert client.connected

        event = service_helper.wait_for_eventhub_arrival(random_message.message_id)
        assert json.dumps(event.message_body) == random_message.data

        leak_tracker.check_for_leaks()

    @pytest.mark.it("Automatically connects if transport automatically disconnected before sending")
    @pytest.mark.uses_iptables
    def test_sync_connects_after_automatic_disconnect_with_retry_disabled(
        self, client, random_message, dropper, service_helper, leak_tracker
    ):
        leak_tracker.set_initial_object_list()

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

        leak_tracker.check_for_leaks()

    @pytest.mark.it("Fails if connection disconnects before sending")
    @pytest.mark.uses_iptables
    def test_sync_fails_if_disconnect_before_sending_with_retry_disabled(
        self, client, random_message, dropper, executor, leak_tracker
    ):
        leak_tracker.set_initial_object_list()

        assert client.connected

        dropper.drop_outgoing()
        send_task = executor.submit(client.send_message, random_message)

        while client.connected:
            time.sleep(1)

        with pytest.raises(OperationCancelled):
            send_task.result()

        random_message = None  # So this doesn't get tagged as a leak
        # TODO: investigate this leak
        # leak_tracker.check_for_leaks()

    @pytest.mark.it("Fails if connection drops before sending")
    @pytest.mark.uses_iptables
    def test_sync_fails_if_drop_before_sending_with_retry_disabled(
        self, client, random_message, dropper, leak_tracker
    ):
        leak_tracker.set_initial_object_list()

        assert client.connected

        dropper.drop_outgoing()
        with pytest.raises(OperationCancelled):
            client.send_message(random_message)

        assert not client.connected

        random_message = None  # So this doesn't get tagged as a leak
        # TODO: investigate this leak
        # leak_tracker.check_for_leaks()
