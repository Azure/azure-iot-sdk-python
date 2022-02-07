# Copyright (c) Microsoft Corporation. All rights reserved.

# Licensed under the MIT License. See License.txt in the project root for
# license information.
import asyncio
import pytest
import logging
import json
import uuid
import time
import parametrize
import contextlib
import psutil
import threading
import os
import task_cleanup
from iptables import all_disconnect_types
from utils import get_random_message, fault_injection_types, get_fault_injection_message
from azure.iot.device.exceptions import (
    ConnectionFailedError,
    ConnectionDroppedError,
    OperationCancelled,
    NoConnectionError,
)

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)

pytestmark = pytest.mark.asyncio

"""

We will eventually have three different kinds of stress tests:
    1. Tests which are run frequently (every night).  These are used to provide assurance that
       we do not have any regressions.  They The run relatively quickly and rarely fail. They
       exist to produce statistics which we can compare between libraries and from run to run.
    2. Tests which run less frequently that are used to find bugs.  These stress the library
       much more than the first set of tests.  They run longer than the first set of tests.
       They are expected to fail and/or produce actionable bug reports..  If they don't,
       we're not pushing limits hard enough.
    3. Long haul tests.  These are designed to run for a long time under more realistic
       scenarios.  Their purpose is to behave in a more realistic manner and find bugs that
       might not come up in the artificial conditions we use for the first to sets of tests.

This file contains tests from the first set.

"""


# Settings that apply to all tests in this module
TELEMETRY_PAYLOAD_SIZE = 16 * 1024

# Settings that apply to continuous telemetry test
CONTINUOUS_TELEMETRY_TEST_DURATION = 120
CONTINUOUS_TELEMETRY_MESSAGES_PER_SECOND = 30

# Settings that apply to all-at-once telemetry test
ALL_AT_ONCE_MESSAGE_COUNT = 3000
ALL_AT_ONCE_TOTAL_ELAPSED_TIME_FAILURE_TRIGGER = 5 * 60

# Settings that apply to flaky network telemetry test
SEND_TELEMETRY_FLAKY_NETWORK_TEST_DURATION = 5 * 60
SEND_TELEMETRY_FLAKY_NETWORK_MESSAGES_PER_SECOND = 20
SEND_TELEMETRY_FLAKY_NETWORK_KEEPALIVE_INTERVAL = 10
SEND_TELEMETRY_FLAKY_NETWORK_CONNECTED_INTERVAL = 15
SEND_TELEMETRY_FLAKY_NETWORK_DISCONNECTED_INTERVAL = 15


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

        sent = False
        attempt = 1

        # "Poor-man's" retry policy.  retry 5 times with linear backoff
        while not sent:
            try:
                # If we're not connected, we need to connect.  This could be done better.
                # If we're sending 10 messages per second, this will give us ten calls to
                # client.connect when we really only need one.
                if not client.connected:
                    logger.info("Connecting for  message {}".format(random_message.message_id))
                    await client.connect()

                logger.info("Sending message {}".format(random_message.message_id))
                await client.send_message(random_message)
                logger.info("Done sending message {}".format(random_message.message_id))

                sent = True

            except (
                ConnectionFailedError,
                ConnectionDroppedError,
                OperationCancelled,
                NoConnectionError,
            ) as e:
                # These are the errors that client.connect or client.send_message can raise
                # if we're not connected.  Can we limit this list?  Surely, we don't expect
                # ConnectoinDroppedError if auto_connect==True.  Do we want to fail if we do?
                logger.info(
                    "{} exception for for message {}".format(type(e), random_message.message_id)
                )
                if attempt == 5:
                    raise
                sleep_time = 5 * attempt

                logger.warning(
                    "ConnectionFailedError.  Sleeping for {} before trying again".format(sleep_time)
                )
                await asyncio.sleep(sleep_time)
                attempt += 1
            except Exception as e:
                logger.info("send_message raised {}".format(type(e)))
                raise

        # Wait for the arrival of the message.  We have a relatively short timeout here
        # (set as a default parameter to wait_for_eventhub_arrival), but that's OK because
        # the message has already been sent at this point.
        logger.info("Waiting for arrival of message {}".format(random_message.message_id))
        event = await service_helper.wait_for_eventhub_arrival(random_message.message_id)

        # verify the mesage
        assert event, "service helper returned falsy event"
        assert (
            event.system_properties["message-id"] == random_message.message_id
        ), "service helper returned event with mismatched message_id"
        assert (
            json.dumps(event.message_body) == random_message.data
        ), "service helper returned event with mismatched body"
        logger.info("Message {} received".format(random_message.message_id))

        self.outstanding_message_ids.remove(random_message.message_id)

    async def send_and_verify_continous_telemetry(
        self,
        client,
        service_helper,
        messages_per_second,
        test_length_in_seconds,
    ):
        """
        Send continuous telemetry.  This coroutine will queue telemetry at a regular rate
        of `messages_per_second` and verify that they arive at eventhub.
        """

        # We use `self.outstanding_message_ids` for logging.
        # And we use `futures` to konw when all tasks have been completed.
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
            # Clean up any (possily) running tasks to avoid "Task exception was never retrieved" errors
            if len(futures):
                task_cleanup.cleanup_tasks(futures)

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
            # Clean up any (possily) running tasks to avoid "Task exception was never retrieved" errors
            if len(futures):
                task_cleanup.cleanup_tasks(futures)

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
        messages_per_second=CONTINUOUS_TELEMETRY_MESSAGES_PER_SECOND,
        test_length_in_seconds=CONTINUOUS_TELEMETRY_TEST_DURATION,
    ):
        """
        This tests send_message at a regular interval.
        We do this to test very basic functionality first before we start pushing the
        limits of the code
        """

        await self.send_and_verify_continous_telemetry(
            client=client,
            service_helper=service_helper,
            messages_per_second=messages_per_second,
            test_length_in_seconds=test_length_in_seconds,
        )

    @pytest.mark.it("send {} messages all at once".format(ALL_AT_ONCE_MESSAGE_COUNT))
    @pytest.mark.timeout(ALL_AT_ONCE_TOTAL_ELAPSED_TIME_FAILURE_TRIGGER)
    async def test_stress_send_message_all_at_once(
        self,
        client,
        service_helper,
        message_count=ALL_AT_ONCE_MESSAGE_COUNT,
    ):
        """
        This tests send_message with a large quantity of messages, all at once, with no faults
        injected.  We do this to test the limits of our message queueing to make sure we can
        handle large volumes of outstanding messages.
        """

        await self.send_and_verify_many_telemetry_messages(
            client=client,
            service_helper=service_helper,
            message_count=message_count,
        )

    @pytest.mark.it(
        "regular message delivery with flaky network {} messages per second for {} seconds".format(
            SEND_TELEMETRY_FLAKY_NETWORK_MESSAGES_PER_SECOND,
            SEND_TELEMETRY_FLAKY_NETWORK_TEST_DURATION,
        )
    )
    @pytest.mark.keep_alive(SEND_TELEMETRY_FLAKY_NETWORK_KEEPALIVE_INTERVAL)
    @pytest.mark.timeout(SEND_TELEMETRY_FLAKY_NETWORK_TEST_DURATION * 2)
    @pytest.mark.dropped_connection
    async def test_stress_send_message_with_flaky_network(
        self,
        client,
        service_helper,
        dropper,
        messages_per_second=SEND_TELEMETRY_FLAKY_NETWORK_MESSAGES_PER_SECOND,
        test_length_in_seconds=SEND_TELEMETRY_FLAKY_NETWORK_TEST_DURATION,
    ):
        """
        This test calls send_message continuously and alternately disconnects and reconnects
        the network.  We do this to verify that we can call send_message regardless of the
        current connection state, and the code will queue the messages as necessary and verify
        that they always arrive.
        """

        await asyncio.gather(
            self.do_periodic_network_disconnects(
                client=client,
                test_length_in_seconds=test_length_in_seconds,
                disconnected_interval=SEND_TELEMETRY_FLAKY_NETWORK_DISCONNECTED_INTERVAL,
                connected_interval=SEND_TELEMETRY_FLAKY_NETWORK_CONNECTED_INTERVAL,
                dropper=dropper,
            ),
            self.send_and_verify_continous_telemetry(
                client=client,
                service_helper=service_helper,
                messages_per_second=messages_per_second,
                test_length_in_seconds=test_length_in_seconds,
            ),
        )
