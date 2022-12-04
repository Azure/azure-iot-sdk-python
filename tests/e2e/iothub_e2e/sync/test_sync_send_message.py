# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import pytest
import logging
import json
import time
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
    def test_sync_send_message_simple(self, leak_tracker, client, random_message, service_helper):
        leak_tracker.set_initial_object_list()

        client.send_message(random_message)

        event = service_helper.wait_for_eventhub_arrival(random_message.message_id)
        assert json.dumps(event.message_body) == random_message.data

        leak_tracker.check_for_leaks()

    @pytest.mark.it("Raises correct exception for un-serializable payload")
    def test_sync_bad_payload_raises(self, leak_tracker, client):
        leak_tracker.set_initial_object_list()

        # There's no way to serialize a function.
        def thing_that_cant_serialize():
            pass

        with pytest.raises(ClientError) as e_info:
            client.send_message(thing_that_cant_serialize)
        assert isinstance(e_info.value.__cause__, TypeError)

        del e_info
        leak_tracker.check_for_leaks()

    @pytest.mark.it("Can send a JSON-formatted string that isn't wrapped in a Message object")
    def test_sync_sends_json_string(self, leak_tracker, client, service_helper):
        leak_tracker.set_initial_object_list()

        message = json.dumps(dev_utils.get_random_dict())

        client.send_message(message)

        event = service_helper.wait_for_eventhub_arrival(None)
        assert json.dumps(event.message_body) == message

        leak_tracker.check_for_leaks()

    @pytest.mark.it("Can send a random string that isn't wrapped in a Message object")
    def test_sync_sends_random_string(self, leak_tracker, client, service_helper):
        leak_tracker.set_initial_object_list()

        message = dev_utils.get_random_string(16)

        client.send_message(message)

        event = service_helper.wait_for_eventhub_arrival(None)
        assert event.message_body == message

        leak_tracker.check_for_leaks()

    @pytest.mark.it("Waits until a connection is established to send if there is no connection")
    def test_sync_fails_if_no_connection(
        self, leak_tracker, executor, client, random_message, service_helper
    ):
        leak_tracker.set_initial_object_list()

        client.disconnect()
        assert not client.connected

        # Attempt to send a message
        send_task = executor.submit(client.send_message, random_message)
        time.sleep(1)
        # Still not done
        assert not send_task.done()
        # Connect
        client.connect()
        time.sleep(0.5)
        # Task is now done
        assert send_task.done()

        event = service_helper.wait_for_eventhub_arrival(random_message.message_id)
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
    def test_sync_network_failure_causes_disconnect(
        self, dropper, leak_tracker, executor, client, random_message, failure_type, service_helper
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Disrupt network
        if failure_type == PACKET_DROP:
            dropper.drop_outgoing()
        elif failure_type == PACKET_REJECT:
            dropper.reject_outgoing()

        # Attempt to send a message
        send_task = executor.submit(client.send_message, random_message)

        # Wait for client to disconnect
        while client.connected:
            assert not send_task.done()
            time.sleep(0.5)
        # Client has now disconnected and task will not finish until reconnection
        assert not send_task.done()

        # Restore outgoing packet functionality and wait for client to reconnect
        dropper.restore_all()
        while not client.connected:
            assert not send_task.done()
            time.sleep(0.5)
        # Wait for the send task to complete now that the client has reconnected
        send_task.result()

        # Ensure the sent message was received by the service
        event = service_helper.wait_for_eventhub_arrival(random_message.message_id)
        assert json.dumps(event.message_body) == random_message.data

        leak_tracker.check_for_leaks()

    @pytest.mark.it("Succeeds if network failure resolves before client can disconnect")
    def test_sync_network_failure_no_disconnect(
        self, dropper, leak_tracker, executor, client, random_message, failure_type, service_helper
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Disrupt network
        if failure_type == PACKET_DROP:
            dropper.drop_outgoing()
        elif failure_type == PACKET_REJECT:
            dropper.reject_outgoing()

        # Attempt to send a message
        send_task = executor.submit(client.send_message, random_message)

        # Has not been able to succeed due to network failure, but client is still connected
        time.sleep(1)
        assert not send_task.done()
        assert client.connected

        # Restore network, and operation succeeds
        dropper.restore_all()
        send_task.result()

        # Ensure the sent message was received by the service
        event = service_helper.wait_for_eventhub_arrival(random_message.message_id)
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
    def test_sync_network_failure_causes_disconnect(
        self, dropper, executor, leak_tracker, client, random_message, failure_type, service_helper
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Disrupt network
        if failure_type == PACKET_DROP:
            dropper.drop_outgoing()
        elif failure_type == PACKET_REJECT:
            dropper.reject_outgoing()

        # Attempt to send a message
        send_task = executor.submit(client.send_message, random_message)

        # Wait for client disconnect
        while client.connected:
            assert not send_task.done()
            time.sleep(0.5)
        # Client has now disconnected and task will not finish until reconnection
        assert not send_task.done()
        time.sleep(1)
        assert not send_task.done()

        # Restore network and manually connect
        dropper.restore_all()
        client.connect()

        send_task.result()

        # Ensure the sent message was received by the service
        event = service_helper.wait_for_eventhub_arrival(random_message.message_id)
        assert json.dumps(event.message_body) == random_message.data

        leak_tracker.check_for_leaks()

    @pytest.mark.it("Succeeds if network failure resolves before client can disconnect")
    def test_sync_network_failure_no_disconnect(
        self, dropper, executor, leak_tracker, client, random_message, failure_type, service_helper
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Disrupt network
        if failure_type == PACKET_DROP:
            dropper.drop_outgoing()
        elif failure_type == PACKET_REJECT:
            dropper.reject_outgoing()

        # Attempt to send a message
        send_task = executor.submit(client.send_message, random_message)

        # Has not been able to succeed due to network failure, but client is still connected
        time.sleep(1)
        assert not send_task.done()
        assert client.connected

        # Restore network, and operation succeeds
        dropper.restore_all()
        send_task.result()

        # Ensure the sent message was received by the service
        event = service_helper.wait_for_eventhub_arrival(random_message.message_id)
        assert json.dumps(event.message_body) == random_message.data

        leak_tracker.check_for_leaks()
