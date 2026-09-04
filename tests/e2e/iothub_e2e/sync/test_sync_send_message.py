# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import pytest
import logging
import json
import dev_utils
import const
import wait_helpers
from azure.iot.device.exceptions import OperationCancelled, ClientError

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)


@pytest.mark.describe("Client send_message method")
class TestSendMessage(object):
    @pytest.mark.it("Can send a simple message")
    @pytest.mark.quicktest_suite
    def test_sync_send_message_simple(self, client, random_message, service_helper, leak_tracker):

        client.send_message(random_message)

        event = service_helper.wait_for_eventhub_arrival(random_message.message_id)
        assert json.dumps(event.message_body) == random_message.data

    @pytest.mark.it("Connects the transport if necessary")
    @pytest.mark.quicktest_suite
    def test_sync_connect_if_necessary(self, client, random_message, service_helper, leak_tracker):

        client.disconnect()
        assert not client.connected

        client.send_message(random_message)
        assert client.connected

        event = service_helper.wait_for_eventhub_arrival(random_message.message_id)
        assert json.dumps(event.message_body) == random_message.data

    @pytest.mark.it("Raises correct exception for un-serializable payload")
    def test_sync_bad_payload_raises(self, client, leak_tracker):

        # There's no way to serialize a function.
        def thing_that_cant_serialize():
            pass

        with pytest.raises(ClientError) as e_info:
            client.send_message(thing_that_cant_serialize)
        assert isinstance(e_info.value.__cause__, TypeError)

    @pytest.mark.it("Can send a JSON-formatted string that isn't wrapped in a Message object")
    def test_sync_sends_json_string(self, client, service_helper, leak_tracker):

        message = json.dumps(dev_utils.get_random_dict())

        client.send_message(message)

        expected_body = json.loads(message)
        event = service_helper.wait_for_eventhub_arrival(
            None, event_filter=lambda event: event.message_body == expected_body
        )
        assert json.dumps(event.message_body) == message

    @pytest.mark.it("Can send a random string that isn't wrapped in a Message object")
    def test_sync_sends_random_string(self, client, service_helper, leak_tracker):

        message = dev_utils.get_random_string(16)

        client.send_message(message)

        event = service_helper.wait_for_eventhub_arrival(
            None, event_filter=lambda event: event.message_body == message
        )
        assert event.message_body == message


@pytest.mark.dropped_connection
@pytest.mark.describe("Client send_message method with dropped connections")
@pytest.mark.keep_alive(5)
class TestSendMessageDroppedConnection(object):
    @pytest.mark.it("Sends if connection drops before sending")
    @pytest.mark.uses_iptables
    def test_sync_sends_if_drop_before_sending(
        self,
        client,
        random_message,
        dropper,
        service_helper,
        run_in_daemon_thread,
        leak_tracker,
    ):

        assert client.connected

        dropper.drop_outgoing()
        send_task = run_in_daemon_thread(client.send_message, random_message)

        wait_helpers.wait_for_condition(lambda: not client.connected, timeout=const.E2E_TIMEOUT)

        assert not send_task.done()

        dropper.restore_all()
        wait_helpers.wait_for_condition(lambda: client.connected, timeout=const.E2E_TIMEOUT)

        send_task.result(timeout=const.E2E_TIMEOUT)

        event = service_helper.wait_for_eventhub_arrival(random_message.message_id)
        assert json.dumps(event.message_body) == random_message.data

    @pytest.mark.it("Sends if connection rejects send")
    @pytest.mark.uses_iptables
    def test_sync_sends_if_reject_before_sending(
        self,
        client,
        random_message,
        dropper,
        service_helper,
        run_in_daemon_thread,
        leak_tracker,
    ):

        assert client.connected

        dropper.reject_outgoing()
        send_task = run_in_daemon_thread(client.send_message, random_message)

        wait_helpers.wait_for_condition(lambda: not client.connected, timeout=const.E2E_TIMEOUT)

        assert not send_task.done()

        dropper.restore_all()
        wait_helpers.wait_for_condition(lambda: client.connected, timeout=const.E2E_TIMEOUT)

        send_task.result(timeout=const.E2E_TIMEOUT)

        event = service_helper.wait_for_eventhub_arrival(random_message.message_id)
        assert json.dumps(event.message_body) == random_message.data


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

        client.send_message(random_message)

        event = service_helper.wait_for_eventhub_arrival(random_message.message_id)
        assert json.dumps(event.message_body) == random_message.data

    @pytest.mark.it("Automatically connects if transport manually disconnected before sending")
    def test_sync_connect_if_necessary_with_retry_disabled(
        self, client, random_message, service_helper, leak_tracker
    ):

        client.disconnect()
        assert not client.connected

        client.send_message(random_message)
        assert client.connected

        event = service_helper.wait_for_eventhub_arrival(random_message.message_id)
        assert json.dumps(event.message_body) == random_message.data

    @pytest.mark.it("Automatically connects if transport automatically disconnected before sending")
    @pytest.mark.uses_iptables
    def test_sync_connects_after_automatic_disconnect_with_retry_disabled(
        self, client, random_message, dropper, service_helper, leak_tracker
    ):

        assert client.connected

        dropper.drop_outgoing()
        wait_helpers.wait_for_condition(lambda: not client.connected, timeout=const.E2E_TIMEOUT)

        assert not client.connected
        dropper.restore_all()
        client.send_message(random_message)
        assert client.connected

        event = service_helper.wait_for_eventhub_arrival(random_message.message_id)
        assert json.dumps(event.message_body) == random_message.data

    @pytest.mark.it("Fails if connection disconnects before sending")
    @pytest.mark.uses_iptables
    def test_sync_fails_if_disconnect_before_sending_with_retry_disabled(
        self,
        client,
        random_message,
        dropper,
        run_in_daemon_thread,
        service_helper,
        leak_tracker,
    ):

        assert client.connected

        dropper.drop_outgoing()
        send_task = run_in_daemon_thread(client.send_message, random_message)

        wait_helpers.wait_for_condition(lambda: not client.connected, timeout=const.E2E_TIMEOUT)

        with pytest.raises(OperationCancelled):
            send_task.result(timeout=const.E2E_TIMEOUT)

        # -----------------------------------------------------------------------------------------
        # The SDK operation is cancelled, but Paho still owns the accepted QoS publish. Reconnect
        # and let the MQTT exchange finish so the normal leak check sees no active session state.
        dropper.restore_all()
        client.connect()
        event = service_helper.wait_for_eventhub_arrival(random_message.message_id)
        assert json.dumps(event.message_body) == random_message.data

    @pytest.mark.it("Fails if connection drops before sending")
    @pytest.mark.uses_iptables
    def test_sync_fails_if_drop_before_sending_with_retry_disabled(
        self, client, random_message, dropper, service_helper, leak_tracker
    ):

        assert client.connected

        dropper.drop_outgoing()
        with pytest.raises(OperationCancelled):
            client.send_message(random_message)

        assert not client.connected

        # -----------------------------------------------------------------------------------------
        # The SDK operation is cancelled, but Paho still owns the accepted QoS publish. Reconnect
        # and let the MQTT exchange finish so the normal leak check sees no active session state.
        dropper.restore_all()
        client.connect()
        event = service_helper.wait_for_eventhub_arrival(random_message.message_id)
        assert json.dumps(event.message_body) == random_message.data
