# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import pytest
import logging
import json
import time
import dev_utils
from azure.iot.device.exceptions import OperationCancelled, ClientError, NoConnectionError

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

    @pytest.mark.it("Raises correct exception for un-serializable payload")
    def test_sync_bad_payload_raises(self, client, flush_messages, leak_tracker):
        leak_tracker.set_initial_object_list()

        # There's no way to serialize a function.
        def thing_that_cant_serialize():
            pass

        with pytest.raises(ClientError) as e_info:
            client.send_message(thing_that_cant_serialize)
        assert isinstance(e_info.value.__cause__, TypeError)

        del e_info
        flush_messages()
        leak_tracker.check_for_leaks()

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

    @pytest.mark.it("Raises NoConnectionError if there is no connection")
    def test_sync_fails_if_no_connection(
        self, client, flush_messages, random_message, leak_tracker
    ):
        leak_tracker.set_initial_object_list()

        client.disconnect()
        assert not client.connected

        with pytest.raises(NoConnectionError):
            client.send_message(random_message)
        assert not client.connected

        flush_messages()
        leak_tracker.check_for_leaks()


@pytest.mark.dropped_connection
@pytest.mark.describe(
    "Client send_message method with dropped connection (Connection Retry enabled)"
)
@pytest.mark.keep_alive(5)
class TestSendMessageDroppedConnectionRetryEnabled(object):
    @pytest.mark.it("Sends message once connection is restored after dropping outgoing packets")
    @pytest.mark.uses_iptables
    def test_sync_sends_if_drop_and_restore(
        self, client, random_message, dropper, service_helper, executor, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Drop outgoing packets
        dropper.drop_outgoing()

        # Attempt to send a message
        send_task = executor.submit(client.send_message, random_message)

        # Wait for client to realize connection has dropped
        while client.connected:
            time.sleep(0.5)
        # Even though connection has dropped, the message send has not completed
        assert not send_task.done()

        # Restore outgoing packet functionality and wait for client to reconnect
        dropper.restore_all()
        while not client.connected:
            time.sleep(0.5)
        # Wait for the send task to complete now that the client has reconnected
        send_task.result()

        # Ensure the sent message was received by the service
        event = service_helper.wait_for_eventhub_arrival(random_message.message_id)
        assert json.dumps(event.message_body) == random_message.data

        leak_tracker.check_for_leaks()

    @pytest.mark.it("Sends message once connection is restored after rejecting outgoing packets")
    @pytest.mark.uses_iptables
    def test_sync_sends_if_reject_and_restore(
        self, client, random_message, dropper, service_helper, executor, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Reject outgoing packets
        dropper.reject_outgoing()

        # Attempt to send a message
        send_task = executor.submit(client.send_message, random_message)

        # Wait for client to realize connection has dropped
        while client.connected:
            time.sleep(0.5)
        # Even though the connection has dropped, the message send has not completed
        assert not send_task.done()

        # Restore outgoing packet functionality and wait for client to reconnect
        dropper.restore_all()
        while not client.connected:
            time.sleep(0.5)
        # Wait for the send task to complete now that the client has reconnected
        send_task.result()

        # Ensure the sent message was received by the service
        event = service_helper.wait_for_eventhub_arrival(random_message.message_id)
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
    def test_sync_raises_op_cancelled_if_drop(
        self, client, flush_messages, random_message, dropper, executor, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Drop outgoing packets
        dropper.drop_outgoing()

        # Attempt to send a message
        send_task = executor.submit(client.send_message, random_message)

        # Wait for client to realize connection has dropped
        while client.connected:
            assert not send_task.done()
            time.sleep(0.5)
        # (Almost) Immediately upon connection drop, the task is cancelled
        time.sleep(0.1)
        assert send_task.done()
        with pytest.raises(OperationCancelled):
            send_task.result()

        dropper.restore_all()
        del send_task
        flush_messages()
        leak_tracker.check_for_leaks()

    @pytest.mark.it("Raises OperationCancelled after rejecting outgoing packets before sending")
    @pytest.mark.uses_iptables
    def test_sync_raises_op_cancelled_if_reject(
        self, client, flush_messages, random_message, dropper, executor, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Reject outgoing packets
        dropper.reject_outgoing()

        # Attempt to send a message
        send_task = executor.submit(client.send_message, random_message)

        # Wait for client to realize connection has dropped
        while client.connected:
            assert not send_task.done()
            time.sleep(0.5)
        # (Almost) Immediately upon connection drop, the task is cancelled
        time.sleep(0.1)
        assert send_task.done()
        with pytest.raises(OperationCancelled):
            send_task.result()

        dropper.restore_all()
        del send_task
        flush_messages()
        leak_tracker.check_for_leaks()
