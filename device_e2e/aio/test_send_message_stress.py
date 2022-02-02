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
PEAK_RESIDENT_MEMORY_MB_FAILURE_TRIGGER = 512
PEAK_TELEMETRY_ARRIVAL_TIME_FAILURE_TRIGGER = 180
PEAK_RECONNECT_TIME_FAILURE_TRIGGER = 30

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

# Settings that apply to fault injection telemetry test
SEND_TELEMETRY_FAULT_INJECTION_TEST_DURATION = 5 * 60
SEND_TELEMETRY_FAULT_INJECTION_MESSAGES_PER_SECOND = 20
SEND_TELEMETRY_FAULT_INJECTION_FAULT_INTERVAL = 10


@pytest.mark.stress
@pytest.mark.describe("Client Stress")
class TestSendMessageStress(object):
    async def send_and_verify_single_telemetry_message(
        self, client, service_helper, stress_measurements
    ):
        """
        Send a single message and verify that it gets received by EventHub
        """

        random_message = get_random_message(TELEMETRY_PAYLOAD_SIZE)

        # We keep track of outstanding messages by message_id.  This is useful when reading
        # logs on failure because it lets us know _which_ messages didn't finish.
        self.outstanding_message_ids.add(random_message.message_id)

        sent = False
        attempt = 1
        start_time = time.time()

        with stress_measurements.lock:
            stress_measurements.telemetry_messages_in_queue += 1
            stress_measurements.peak_telemetry_messages_in_queue = max(
                stress_measurements.peak_telemetry_messages_in_queue,
                stress_measurements.telemetry_messages_in_queue,
            )

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

        with stress_measurements.lock:
            stress_measurements.telemetry_messages_in_queue -= 1

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

        arrival_time = time.time() - start_time
        with stress_measurements.lock:
            stress_measurements.peak_telemetry_arrival_time = max(
                stress_measurements.peak_telemetry_arrival_time, arrival_time
            )
            logger.info(
                "Arrival time = {}, new peak = {}".format(
                    arrival_time, stress_measurements.peak_telemetry_arrival_time
                )
            )

    async def send_and_verify_continous_telemetry(
        self,
        client,
        service_helper,
        messages_per_second,
        test_length_in_seconds,
        stress_measurements,
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

        # go until time runs out and our list of futures is empty.
        while not done_sending or len(futures) > 0:

            # When time runs out, stop sending, and slow down out loop so we call
            # asyncio.gather much less often.
            if time.time() >= test_end:
                done_sending = True
                sleep_interval = 5

            # if the test is still running, send another message
            if not done_sending:
                futures.append(
                    asyncio.ensure_future(
                        self.send_and_verify_single_telemetry_message(
                            client=client,
                            service_helper=service_helper,
                            stress_measurements=stress_measurements,
                        )
                    )
                )

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

    async def send_and_verify_many_telemetry_messages(
        self, client, service_helper, message_count, stress_measurements
    ):
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
                    stress_measurements=stress_measurements,
                )
            )
            for _ in range(message_count)
        ]

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

    async def inject_periodic_faults(self, client, test_length_in_seconds, fault_interval):
        """
        Inject periodic faults using IoTHub fault-injection packets.  This coroutine cycles
        through available faults and injects a fault every `fault_interval` seconds.  It runs
        for `test_length_in_seconds` seconds.
        """
        test_end = time.time() + test_length_in_seconds
        loop_index = 0
        fault_types = list(fault_injection_types.keys())

        while time.time() < test_end:
            await asyncio.sleep(min(fault_interval, test_end - time.time()))

            if time.time() >= test_end:
                return

            fault_type = fault_types[loop_index % len(fault_types)]
            loop_index += 1

            logger.warning("Injecting fault: {}".format(fault_type))

            fault_message = get_fault_injection_message(fault_type)

            await client.send_message(fault_message)

    async def record_stress_measurements(self, client, stop_event, stress_measurements):
        """
        Coroutine to record certain test measurement throughout the legnth of
        a test.  It completes after stop_event is set.  This way, the invoker can control how
        long this code runs.

        This test records:
            peak_reconnect_time
            peak_resident_memory_mb
        """

        process = psutil.Process(os.getpid())
        was_connected = True
        disconnect_time = 0

        def handle_on_connection_state_change():
            nonlocal was_connected, disconnect_time

            if client.connected:
                if not was_connected:
                    reconnect_time = time.time() - disconnect_time
                    with stress_measurements.lock:
                        stress_measurements.peak_reconnect_time = max(
                            stress_measurements.peak_reconnect_time, reconnect_time
                        )
                        logger.info(
                            "Reconnect time = {}, new peak = {}".format(
                                reconnect_time, stress_measurements.peak_reconnect_time
                            )
                        )
            else:  # not client.connected and
                if was_connected:
                    disconnect_time = time.time()
            was_connected = client.connected

        assert not client.on_connection_state_change, "on_connection_state_change already set"
        client.on_connection_state_change = handle_on_connection_state_change

        while not stop_event.is_set():
            current_resident_memory_mb = process.memory_info().rss / 1024 / 1024
            with stress_measurements.lock:
                stress_measurements.peak_resident_memory_mb = max(
                    stress_measurements.peak_resident_memory_mb, current_resident_memory_mb
                )
                logger.info(
                    "memory use = {}, new peak = {}".format(
                        current_resident_memory_mb,
                        stress_measurements.peak_resident_memory_mb,
                    )
                )

            await asyncio.sleep(5)

        client.on_connection_state_change = None

    @pytest.mark.it(
        "regular message delivery {} messages per second for {} seconds".format(
            CONTINUOUS_TELEMETRY_MESSAGES_PER_SECOND, CONTINUOUS_TELEMETRY_TEST_DURATION
        )
    )
    @pytest.mark.timeout(CONTINUOUS_TELEMETRY_TEST_DURATION * 2)
    async def test_stress_send_continuous_telemetry(
        self,
        client,
        service_helper,
        stress_measurements,
        messages_per_second=CONTINUOUS_TELEMETRY_MESSAGES_PER_SECOND,
        test_length_in_seconds=CONTINUOUS_TELEMETRY_TEST_DURATION,
    ):
        """
        This tests send_message at a regular interval.
        We do this to test very basic functionality first before we start pushing the
        limits of the code
        """

        stop_recorder_event = asyncio.Event()
        recorder = asyncio.ensure_future(
            self.record_stress_measurements(client, stop_recorder_event, stress_measurements)
        )

        try:
            await self.send_and_verify_continous_telemetry(
                client=client,
                service_helper=service_helper,
                messages_per_second=messages_per_second,
                test_length_in_seconds=test_length_in_seconds,
                stress_measurements=stress_measurements,
            )
        finally:
            stop_recorder_event.set()
            await recorder

        assert (
            stress_measurements.peak_reconnect_time <= PEAK_RECONNECT_TIME_FAILURE_TRIGGER
        ), "Reconnect took too long"
        assert (
            stress_measurements.peak_resident_memory_mb <= PEAK_RESIDENT_MEMORY_MB_FAILURE_TRIGGER
        ), "Resident memory overflow"
        assert (
            stress_measurements.peak_telemetry_arrival_time
            <= PEAK_TELEMETRY_ARRIVAL_TIME_FAILURE_TRIGGER
        ), "Telemetry message took too long to arrive"

    @pytest.mark.it("send {} messages all at once".format(ALL_AT_ONCE_MESSAGE_COUNT))
    @pytest.mark.timeout(ALL_AT_ONCE_TOTAL_ELAPSED_TIME_FAILURE_TRIGGER)
    async def test_stress_send_message_all_at_once(
        self,
        client,
        service_helper,
        stress_measurements,
        message_count=ALL_AT_ONCE_MESSAGE_COUNT,
    ):
        """
        This tests send_message with a large quantity of messages, all at once, with no faults
        injected.  We do this to test the limits of our message queueing to make sure we can
        handle large volumes of outstanding messages.
        """
        stop_recorder_event = asyncio.Event()
        recorder = asyncio.ensure_future(
            self.record_stress_measurements(client, stop_recorder_event, stress_measurements)
        )

        try:
            await self.send_and_verify_many_telemetry_messages(
                client=client,
                service_helper=service_helper,
                message_count=message_count,
                stress_measurements=stress_measurements,
            )
        finally:
            stop_recorder_event.set()
            await recorder

        assert (
            stress_measurements.peak_reconnect_time <= PEAK_RECONNECT_TIME_FAILURE_TRIGGER
        ), "Reconnect took too long"
        assert (
            stress_measurements.peak_resident_memory_mb <= PEAK_RESIDENT_MEMORY_MB_FAILURE_TRIGGER
        ), "Resident memory overflow"
        assert (
            stress_measurements.peak_telemetry_arrival_time
            <= PEAK_TELEMETRY_ARRIVAL_TIME_FAILURE_TRIGGER
        ), "Telemetry message took too long to arrive"

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
        stress_measurements,
        messages_per_second=SEND_TELEMETRY_FLAKY_NETWORK_MESSAGES_PER_SECOND,
        test_length_in_seconds=SEND_TELEMETRY_FLAKY_NETWORK_TEST_DURATION,
    ):
        """
        This test calls send_message continuously and alternately disconnects and reconnects
        the network.  We do this to verify that we can call send_message regardless of the
        current connection state, and the code will queue the messages as necessary and verify
        that they always arrive.
        """

        stop_recorder_event = asyncio.Event()
        recorder = asyncio.ensure_future(
            self.record_stress_measurements(client, stop_recorder_event, stress_measurements)
        )

        try:
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
                    stress_measurements=stress_measurements,
                ),
            )
        finally:
            stop_recorder_event.set()
            await recorder

        assert (
            stress_measurements.peak_reconnect_time <= PEAK_RECONNECT_TIME_FAILURE_TRIGGER
        ), "Reconnect took too long"
        assert (
            stress_measurements.peak_resident_memory_mb <= PEAK_RESIDENT_MEMORY_MB_FAILURE_TRIGGER
        ), "Resident memory overflow"
        assert (
            stress_measurements.peak_telemetry_arrival_time
            <= PEAK_TELEMETRY_ARRIVAL_TIME_FAILURE_TRIGGER
        ), "Telemetry message took too long to arrive"

    # skipping becuase:
    # 1. IoTHub appears to ignore AzIoTHub_FaultOperationDelayInSecs and instead fault immediately.
    # 2. A packet which forces a disconnect will get re-sent again as soon as the client reconnects. (bug 12512080)
    @pytest.mark.skip()
    @pytest.mark.it(
        "regular message delivery with fault injection {} messages per second for {} seconds".format(
            SEND_TELEMETRY_FAULT_INJECTION_MESSAGES_PER_SECOND,
            SEND_TELEMETRY_FAULT_INJECTION_TEST_DURATION,
        )
    )
    @pytest.mark.timeout(SEND_TELEMETRY_FAULT_INJECTION_TEST_DURATION * 2)
    async def test_stress_send_message_with_fault_injection(
        self,
        client,
        service_helper,
        stress_measurements,
        messages_per_second=SEND_TELEMETRY_FAULT_INJECTION_MESSAGES_PER_SECOND,
        test_length_in_seconds=SEND_TELEMETRY_FAULT_INJECTION_TEST_DURATION,
    ):
        """
        This test calls send_message continuously and injects faults at regular intervals
        We do this to verify that we can call send_message regardless of the
        current connection state, and the code will queue the messages as necessary and verify
        that they always arrive.
        """

        stop_recorder_event = asyncio.Event()
        recorder = asyncio.ensure_future(
            self.record_stress_measurements(client, stop_recorder_event, stress_measurements)
        )

        try:
            await asyncio.gather(
                self.inject_periodic_faults(
                    client=client,
                    test_length_in_seconds=test_length_in_seconds,
                    fault_interval=SEND_TELEMETRY_FAULT_INJECTION_FAULT_INTERVAL,
                ),
                self.send_and_verify_continous_telemetry(
                    client=client,
                    service_helper=service_helper,
                    messages_per_second=messages_per_second,
                    test_length_in_seconds=test_length_in_seconds,
                    stress_measurements=stress_measurements,
                ),
            )

        finally:
            stop_recorder_event.set()
            await recorder

        assert (
            stress_measurements.peak_reconnect_time <= PEAK_RECONNECT_TIME_FAILURE_TRIGGER
        ), "Reconnect took too long"
        assert (
            stress_measurements.peak_resident_memory_mb <= PEAK_RESIDENT_MEMORY_MB_FAILURE_TRIGGER
        ), "Resident memory overflow"
        assert (
            stress_measurements.peak_telemetry_arrival_time
            <= PEAK_TELEMETRY_ARRIVAL_TIME_FAILURE_TRIGGER
        ), "Telemetry message took too long to arrive"
