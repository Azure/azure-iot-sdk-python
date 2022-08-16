# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import asyncio
import pytest
import logging
import json
import time
import parametrize
import task_cleanup
from dev_utils import get_random_message
from dev_utils.iptables import all_disconnect_types
from retry_async import retry_exponential_backoff_with_jitter

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)

pytestmark = pytest.mark.asyncio

# Settings that apply to all tests in this module
TELEMETRY_PAYLOAD_SIZE = 16 * 1024

# Settings that apply to continuous telemetry test
CONTINUOUS_TELEMETRY_TEST_DURATION = 120
CONTINUOUS_TELEMETRY_MESSAGES_PER_SECOND = 30

# Settings that apply to all-at-once telemetry test
ALL_AT_ONCE_MESSAGE_COUNT = 3000
ALL_AT_ONCE_TOTAL_ELAPSED_TIME_FAILURE_TRIGGER = 10 * 60

# Settings that apply to flaky network telemetry test
SEND_TELEMETRY_FLAKY_NETWORK_TEST_DURATION = 5 * 60
SEND_TELEMETRY_FLAKY_NETWORK_MESSAGES_PER_SECOND = 10
SEND_TELEMETRY_FLAKY_NETWORK_KEEPALIVE_INTERVAL = 10
SEND_TELEMETRY_FLAKY_NETWORK_CONNECTED_INTERVAL = 15
SEND_TELEMETRY_FLAKY_NETWORK_DISCONNECTED_INTERVAL = 15

call_with_retry = retry_exponential_backoff_with_jitter


@pytest.mark.stress
@pytest.mark.describe("Client Stress")
class TestSendMessageStress(object):
    async def send_and_verify_single_telemetry_message(self, client, service_helper):
        """
        Send a single message and verify that it gets received by EventHub
        """

        random_message = get_random_message(TELEMETRY_PAYLOAD_SIZE)

        # We keep track of outstanding messages by message_id.  This is useful when reading
        # logs on failure because it lets us know _which_ messages didn't finish.
        self.outstanding_message_ids.add(random_message.message_id)

        await call_with_retry(client, client.send_message, random_message)

        # Wait for the arrival of the message.
        logger.info("Waiting for arrival of message {}".format(random_message.message_id))
        event = await service_helper.wait_for_eventhub_arrival(random_message.message_id)

        # verify the message
        assert event, "service helper returned falsy event"
        assert (
            event.system_properties["message-id"] == random_message.message_id
        ), "service helper returned event with mismatched message_id"
        assert (
            json.dumps(event.message_body) == random_message.data
        ), "service helper returned event with mismatched body"
        logger.info("Message {} received".format(random_message.message_id))

        self.outstanding_message_ids.remove(random_message.message_id)

    async def send_and_verify_continuous_telemetry(
        self,
        client,
        service_helper,
        messages_per_second,
        test_length_in_seconds,
    ):
        """
        Send continuous telemetry.  This coroutine will queue telemetry at a regular rate
        of `messages_per_second` and verify that they arrive at eventhub.
        """

        # We use `self.outstanding_message_ids` for logging.
        # And we use `futures` to know when all tasks have been completed.
        self.outstanding_message_ids = set()
        test_end = time.time() + test_length_in_seconds
        futures = list()

        done_sending = False
        sleep_interval = 1 / messages_per_second

        try:
            # go until time runs out and our list of futures is empty.
            while not done_sending or len(futures) > 0:

                # When time runs out, stop sending, and slow down out loop so we call
                # asyncio.gather much less often.
                if time.time() >= test_end:
                    done_sending = True
                    sleep_interval = 5

                # if the test is still running, send another message
                if not done_sending:
                    task = asyncio.ensure_future(
                        self.send_and_verify_single_telemetry_message(
                            client=client,
                            service_helper=service_helper,
                        )
                    )
                    futures.append(task)

                # see which tasks are done.
                done, pending = await asyncio.wait(
                    futures, timeout=sleep_interval, return_when=asyncio.ALL_COMPLETED
                )
                logger.info(
                    "From {} futures, {} are done and {} are pending".format(
                        len(futures), len(done), len(pending)
                    )
                )

                # If we're done sending, and nothing finished in this last interval, log which
                # message_ids are outstanding. This can be used to grep logs for outstanding messages.
                if done_sending and len(done) == 0:
                    logger.warning("Not received: {}".format(self.outstanding_message_ids))

                # Use `asyncio.gather` to reraise any exceptions that might have been raised inside our
                # futures.
                await asyncio.gather(*done)

                # And loop again, but we only need to worry about incomplete futures.
                futures = list(pending)

        finally:
            # Clean up any (possibly) running tasks to avoid "Task exception was never retrieved" errors
            if len(futures):
                await task_cleanup.cleanup_tasks(futures)

    async def send_and_verify_many_telemetry_messages(self, client, service_helper, message_count):
        """
        Send a whole bunch of messages all at once and verify that they arrive at eventhub
        """
        sleep_interval = 5
        self.outstanding_message_ids = set()
        futures = [
            asyncio.ensure_future(
                self.send_and_verify_single_telemetry_message(
                    client=client,
                    service_helper=service_helper,
                )
            )
            for _ in range(message_count)
        ]

        try:
            while len(futures):
                # see which tasks are done.
                done, pending = await asyncio.wait(
                    futures, timeout=sleep_interval, return_when=asyncio.ALL_COMPLETED
                )
                logger.info(
                    "From {} futures, {} are done and {} are pending".format(
                        len(futures), len(done), len(pending)
                    )
                )

                # If nothing finished in this last interval, log which
                # message_ids are outstanding. This can be used to grep logs for outstanding messages.
                if len(done) == 0:
                    logger.warning("Not received: {}".format(self.outstanding_message_ids))

                # Use `asyncio.gather` to reraise any exceptions that might have been raised inside our
                # futures.
                await asyncio.gather(*done)

                # And loop again, but we only need to worry about incomplete futures.
                futures = list(pending)

        finally:
            # Clean up any (possibly) running tasks to avoid "Task exception was never retrieved" errors
            if len(futures):
                await task_cleanup.cleanup_tasks(futures)

    async def do_periodic_network_disconnects(
        self,
        client,
        test_length_in_seconds,
        disconnected_interval,
        connected_interval,
        dropper,
    ):
        """
        Periodically disconnect and reconnect the network.  When this coroutine starts, the
        network is connected.  It sleeps for `connected_interval`, then it disconnects the network,
        sleeps for `disconnected_interval`, and reconnects the network.  It finishes after
        `test_length_in_seconds` elapses, and it returns with the network connected again.
        """

        try:
            test_end = time.time() + test_length_in_seconds
            loop_index = 0

            while time.time() < test_end:
                await asyncio.sleep(min(connected_interval, test_end - time.time()))

                if time.time() >= test_end:
                    return

                dropper.disconnect_outgoing(
                    all_disconnect_types[loop_index % len(all_disconnect_types)]
                )
                loop_index += 1

                await asyncio.sleep(min(disconnected_interval, test_end - time.time()))

                dropper.restore_all()
        finally:
            dropper.restore_all()

    @pytest.mark.it(
        "regular message delivery {} messages per second for {} seconds".format(
            CONTINUOUS_TELEMETRY_MESSAGES_PER_SECOND, CONTINUOUS_TELEMETRY_TEST_DURATION
        )
    )
    @pytest.mark.timeout(CONTINUOUS_TELEMETRY_TEST_DURATION * 5)
    async def test_stress_send_continuous_telemetry(
        self,
        client,
        service_helper,
        leak_tracker,
        messages_per_second=CONTINUOUS_TELEMETRY_MESSAGES_PER_SECOND,
        test_length_in_seconds=CONTINUOUS_TELEMETRY_TEST_DURATION,
    ):
        """
        This tests send_message at a regular interval.
        We do this to test very basic functionality first before we start pushing the
        limits of the code
        """

        leak_tracker.set_initial_object_list()

        await self.send_and_verify_continuous_telemetry(
            client=client,
            service_helper=service_helper,
            messages_per_second=messages_per_second,
            test_length_in_seconds=test_length_in_seconds,
        )

        leak_tracker.check_for_leaks()

    @pytest.mark.it("send {} messages all at once".format(ALL_AT_ONCE_MESSAGE_COUNT))
    @pytest.mark.timeout(ALL_AT_ONCE_TOTAL_ELAPSED_TIME_FAILURE_TRIGGER)
    async def test_stress_send_message_all_at_once(
        self,
        client,
        service_helper,
        leak_tracker,
        message_count=ALL_AT_ONCE_MESSAGE_COUNT,
    ):
        """
        This tests send_message with a large quantity of messages, all at once, with no faults
        injected.  We do this to test the limits of our message queueing to make sure we can
        handle large volumes of outstanding messages.
        """

        leak_tracker.set_initial_object_list()

        await self.send_and_verify_many_telemetry_messages(
            client=client,
            service_helper=service_helper,
            message_count=message_count,
        )

        leak_tracker.check_for_leaks()

    @pytest.mark.it(
        "regular message delivery with flaky network {} messages per second for {} seconds".format(
            SEND_TELEMETRY_FLAKY_NETWORK_MESSAGES_PER_SECOND,
            SEND_TELEMETRY_FLAKY_NETWORK_TEST_DURATION,
        )
    )
    @pytest.mark.keep_alive(SEND_TELEMETRY_FLAKY_NETWORK_KEEPALIVE_INTERVAL)
    @pytest.mark.timeout(SEND_TELEMETRY_FLAKY_NETWORK_TEST_DURATION * 2)
    @pytest.mark.dropped_connection
    @pytest.mark.parametrize(*parametrize.connection_retry_disabled_and_enabled)
    @pytest.mark.parametrize(*parametrize.auto_connect_disabled_and_enabled)
    async def test_stress_send_message_with_flaky_network(
        self,
        client,
        service_helper,
        dropper,
        leak_tracker,
        messages_per_second=SEND_TELEMETRY_FLAKY_NETWORK_MESSAGES_PER_SECOND,
        test_length_in_seconds=SEND_TELEMETRY_FLAKY_NETWORK_TEST_DURATION,
    ):
        """
        This test calls send_message continuously and alternately disconnects and reconnects
        the network.  We do this to verify that we can call send_message regardless of the
        current connection state, and the code will queue the messages as necessary and verify
        that they always arrive.
        """

        leak_tracker.set_initial_object_list()

        await asyncio.gather(
            self.do_periodic_network_disconnects(
                client=client,
                test_length_in_seconds=test_length_in_seconds,
                disconnected_interval=SEND_TELEMETRY_FLAKY_NETWORK_DISCONNECTED_INTERVAL,
                connected_interval=SEND_TELEMETRY_FLAKY_NETWORK_CONNECTED_INTERVAL,
                dropper=dropper,
            ),
            self.send_and_verify_continuous_telemetry(
                client=client,
                service_helper=service_helper,
                messages_per_second=messages_per_second,
                test_length_in_seconds=test_length_in_seconds,
            ),
        )

        leak_tracker.check_for_leaks()
