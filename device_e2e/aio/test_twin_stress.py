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
import const
import utils
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


@pytest.fixture
def toxic():
    pass


reset_reported_props = {const.TEST_CONTENT: None}


def get_random_property_value():
    return utils.get_random_string(100, True)


def wrap_as_reported_property(value, key=None):
    if key:
        return {const.TEST_CONTENT: {key: value}}
    else:
        return {const.TEST_CONTENT: value}


async def call_with_connection_retry(client, func, *args, **kwargs):
    """
    wrapper function to call a function with retry.
    """
    attempt = 1
    call_id = str(uuid.uuid4())

    logger.info(
        "retry: call {} started, call = {}({}, {}). Connecting".format(
            call_id, str(func), str(args), str(kwargs)
        )
    )

    # "Poor-man's" retry policy. Retry 5 times with linear backoff
    while True:
        try:
            # If we're not connected, we need to connect.
            if not client.connected:
                logger.info("retry: call {} reconnecting".format(call_id))
                await client.connect()

            logger.info("retry: call {} invoking".format(call_id))
            result = await func(*args, **kwargs)
            logger.info("retry: call {} successful".format(call_id))
            return result

        except (
            ConnectionFailedError,
            ConnectionDroppedError,
            OperationCancelled,
            NoConnectionError,
        ) as e:
            if attempt == 5:
                logger.info(
                    "retry; Call {} retry limit exceeded. Raising {}".format(
                        call_id, str(e) or type(e)
                    )
                )
                raise
            sleep_time = 5 * attempt

            logger.info(
                "retry; Call {} attempt {} raised {}. Sleeping for {} and trying again".format(
                    call_id, attempt, str(e) or type(e), sleep_time
                )
            )

            await asyncio.sleep(sleep_time)
            attempt += 1
        except Exception as e:
            logger.info(
                "retry: Call {} raised non-retriable error {}".format(call_id, str(e) or type(e))
            )
            raise e


@pytest.mark.timeout(600)
@pytest.mark.stress
@pytest.mark.describe("Client Stress")
class TestTwinStress(object):
    @pytest.mark.parametrize(
        "iteration_count", [pytest.param(10, id="10 updates"), pytest.param(50, id="50 updates")]
    )
    @pytest.mark.it("Can send continuous repoted property updates, one-at-a-time")
    async def test_stress_serial_reported_property_updates(
        self, client, service_helper, toxic, iteration_count
    ):
        """
        Send reported property updates, one at a time, and verify that each one
        has been received at the service. Do not overlap these calls.
        """
        await call_with_connection_retry(
            client, client.patch_twin_reported_properties, reset_reported_props
        )

        for i in range(iteration_count):
            logger.info("Iteration {} of {}".format(i, iteration_count))

            # Update the reported property.
            patch = wrap_as_reported_property(get_random_property_value())
            await call_with_connection_retry(client, client.patch_twin_reported_properties, patch)

            # Wait for that reported property to arrive at the service.
            received = False
            while not received:
                received_patch = await service_helper.get_next_reported_patch_arrival()
                if received_patch[const.REPORTED][const.TEST_CONTENT] == patch[const.TEST_CONTENT]:
                    received = True
                else:
                    logger.info(
                        "Wrong patch received. Expecting {}, got {}".format(
                            received_patch[const.REPORTED], patch
                        )
                    )

    @pytest.mark.parametrize(
        "iteration_count, batch_size",
        [
            pytest.param(20, 10, id="20 updates, 10 at a time"),
            pytest.param(250, 25, id="250 updates, 25 at a time"),
        ],
    )
    @pytest.mark.it("Can send continuous overlapped repoted property updates")
    async def test_stress_parallel_reported_property_updates(
        self, client, service_helper, toxic, iteration_count, batch_size
    ):
        """
        Update reported properties with many overlapped calls. Work in batches
        with `batch_size` overlapped calls in a batch. Verify that the updates arrive
        at the service.
        """
        await call_with_connection_retry(
            client, client.patch_twin_reported_properties, reset_reported_props
        )

        for _ in range(0, iteration_count, batch_size):
            props = {
                "key_{}".format(k): get_random_property_value() for k in range(0, iteration_count)
            }

            # Do overlapped calls to update `batch_size` properties.
            tasks = [
                call_with_connection_retry(
                    client,
                    client.patch_twin_reported_properties,
                    wrap_as_reported_property(props[key], key),
                )
                for key in props.keys()
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    raise result

            # wait for these properties to arrive at the service
            count_received = 0
            while count_received < batch_size:
                received_patch = await service_helper.get_next_reported_patch_arrival(timeout=60)
                received_test_content = received_patch[const.REPORTED][const.TEST_CONTENT] or {}
                logger.info("received {}".format(received_test_content))

                for key in received_test_content.keys():
                    logger.info("Received {} = {}".format(key, received_test_content[key]))
                    if key in props:
                        if received_test_content[key] == props[key]:
                            logger.info("Key {} received as expected.".format(key))
                            # Set the value to None so we know that it's been received
                            props[key] = None
                            count_received += 1
                        else:
                            logger.info(
                                "Ignoring unexpected value for key {}. Received = {}, expected = {}".format(
                                    key, received_test_content[key], props[key]
                                )
                            )

    @pytest.mark.parametrize(
        "iteration_count", [pytest.param(10, id="10 updates"), pytest.param(50, id="50 updates")]
    )
    @pytest.mark.it("Can receive continuous desired property updates that were sent one-at-a-time")
    async def test_stress_serial_desired_property_updates(
        self, client, service_helper, toxic, iteration_count, event_loop
    ):
        """
        Update desired properties, one at a time, and verify that the desired property arrives
        at the client before the next update.
        """
        patches = asyncio.Queue()

        async def handle_on_patch_received(patch):
            logger.info("received {}".format(patch))
            # marshal this back into our event loop so we can safely use the asyncio.queue
            asyncio.run_coroutine_threadsafe(patches.put(patch), event_loop)

        client.on_twin_desired_properties_patch_received = handle_on_patch_received

        for i in range(iteration_count):
            logger.info("Iteration {} of {}".format(i, iteration_count))

            # update a single desired property
            property_value = get_random_property_value()
            await service_helper.set_desired_properties(
                {const.TEST_CONTENT: property_value},
            )

            # wait for the property udpate to arrive at the client
            received_patch = await asyncio.wait_for(patches.get(), 60)
            assert received_patch[const.TEST_CONTENT] == property_value

    @pytest.mark.parametrize(
        "iteration_count, batch_size",
        [
            pytest.param(20, 10, id="20 updates, 10 at a time"),
            pytest.param(250, 25, id="250 updates, 25 at a time"),
        ],
    )
    @pytest.mark.it(
        "Can receive continuous desired property updates that may have been sent in parallel"
    )
    async def test_stress_parallel_desired_property_udpates(
        self, client, service_helper, toxic, iteration_count, batch_size, event_loop
    ):
        """
        Update desired properties in batches. Each batch udpates `batch_size` properties,
        with each property being updated in it's own `PATCH`.
        """
        patches = asyncio.Queue()

        async def handle_on_patch_received(patch):
            logger.info("received {}".format(patch))
            # use run_coroutine_threadsafe to marshal this back into our event
            # loop so we can safely use the asyncio.queue
            asyncio.run_coroutine_threadsafe(patches.put(patch), event_loop)

        client.on_twin_desired_properties_patch_received = handle_on_patch_received

        props = {"key_{}".format(k): None for k in range(0, batch_size)}

        await service_helper.set_desired_properties({const.TEST_CONTENT: None})

        for _ in range(0, iteration_count, batch_size):

            # update `batch_size` properties, each with a call to `set_desired_proprties`
            props = {"key_{}".format(k): get_random_property_value() for k in range(0, batch_size)}
            tasks = [
                service_helper.set_desired_properties({const.TEST_CONTENT: {key: props[key]}})
                for key in props.keys()
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    raise result

            # Wait for those properties to arrive at the client
            count_received = 0
            while count_received < batch_size:
                received_patch = await asyncio.wait_for(patches.get(), 60)
                received_test_content = received_patch[const.TEST_CONTENT] or {}

                for key in received_test_content:
                    logger.info("Received {} = {}".format(key, received_test_content[key]))
                    if key in props:
                        if received_test_content[key] == props[key]:
                            logger.info("Key {} received as expected.".format(key))
                            # Set the value to None so we know that it's been received
                            props[key] = None
                            count_received += 1
                        else:
                            logger.info(
                                "Ignoring unexpected value for key {}. Received = {}, expected = {}".format(
                                    key, received_test_content[key], props[key]
                                )
                            )

    @pytest.mark.parametrize(
        "iteration_count", [pytest.param(10, id="10 updates"), pytest.param(50, id="50 updates")]
    )
    @pytest.mark.it("Can continuously call get_twin and get valid property values")
    async def test_stress_serial_get_twin_calls(
        self, client, service_helper, toxic, iteration_count
    ):
        """
        Call `get_twin` once-at-a-time to verify that updated properites show up. This test
        calls `get_twin()` `iteration_count` times. Once a reported property shows up in the
        twin, that property is updated to be verified in future `get_twin` calls.
        """
        last_property_value = None
        current_property_value = None

        for i in range(iteration_count):
            logger.info("Iteration {} of {}".format(i, iteration_count))

            # Set a reported property
            if not current_property_value:
                current_property_value = get_random_property_value()
                logger.info("patching to {}".format(current_property_value))
                await call_with_connection_retry(
                    client,
                    client.patch_twin_reported_properties,
                    wrap_as_reported_property(current_property_value),
                )

            # Call get_twin to verify that this property arrived.
            # repoted properties aren't immediately reflected in `get_twin` calls,
            # so we have to account for retrieving old property values.
            twin = await call_with_connection_retry(client, client.get_twin)
            logger.info("Got {}".format(twin[const.REPORTED][const.TEST_CONTENT]))
            if twin[const.REPORTED][const.TEST_CONTENT] == current_property_value:
                logger.info("it's a match.")
                last_property_value = current_property_value
                current_property_value = None
            elif last_property_value:
                # If it's not the current value, then it _must_ be the last value
                # We can only verify this if we know what the old value was.
                assert twin[const.REPORTED][const.TEST_CONTENT] == last_property_value

        assert last_property_value, "No patches with updated properties were received"

    @pytest.mark.parametrize(
        "iteration_count, batch_size",
        [
            pytest.param(20, 10, id="20 updates, 10 at a time"),
            pytest.param(250, 25, id="250 updates, 25 at a time"),
            pytest.param(1000, 50, id="1000 updates, 50 at a time"),
        ],
    )
    @pytest.mark.it("Can continuously make overlapped get_twin calls and get valid property values")
    async def test_stress_parallel_get_twin_calls(
        self, client, service_helper, toxic, iteration_count, batch_size
    ):
        """
        Call `get_twin` many times, overlapped, to verify that updated properites show up. This test
        calls `get_twin()` `iteration_count` times. Once a reported property shows up in the
        twin, that property is updated to be verified in future `get_twin` calls.
        """
        last_property_value = None
        current_property_value = get_random_property_value()

        await call_with_connection_retry(
            client,
            client.patch_twin_reported_properties,
            wrap_as_reported_property(current_property_value),
        )
        ready_to_test = False

        while not ready_to_test:
            twin = await call_with_connection_retry(client, client.get_twin)
            if twin[const.REPORTED].get(const.TEST_CONTENT, "") == current_property_value:
                logger.info("Initial value set")
                ready_to_test = True
            else:
                logger.info("Waiting for initial value. Sleeping for 5")
                await asyncio.sleep(5)

        for i in range(0, iteration_count, batch_size):
            logger.info("Iteration {} of {}".format(i, iteration_count))

            # Update the property if it's time to udpate
            if not current_property_value:
                current_property_value = get_random_property_value()
                logger.info("patching to {}".format(current_property_value))
                await call_with_connection_retry(
                    client,
                    client.patch_twin_reported_properties,
                    wrap_as_reported_property(current_property_value),
                )

            # Call `get_twin` many times overlapped and verify that we get either
            # the old property value (if we know it), or the new property value.
            tasks = [call_with_connection_retry(client, client.get_twin) for _ in range(batch_size)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            got_a_match = False

            for result in results:
                if isinstance(result, Exception):
                    raise result

                twin = result
                logger.info("Got {}".format(twin[const.REPORTED][const.TEST_CONTENT]))
                if twin[const.REPORTED][const.TEST_CONTENT] == current_property_value:
                    logger.info("it's a match.")
                    got_a_match = True
                elif last_property_value:
                    # if it's not the current value, then it _must_ be the last value
                    assert twin[const.REPORTED][const.TEST_CONTENT] == last_property_value

            # Once we verify that `get_twin` returned the new property value, we set
            # it to `None` so the next ieration of the loop can update this value.
            if got_a_match:
                last_property_value = current_property_value
                current_property_value = None
