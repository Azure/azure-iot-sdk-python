# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import asyncio
import pytest
import logging
import parametrize
import const
import dev_utils
from retry_async import retry_exponential_backoff_with_jitter

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)

pytestmark = pytest.mark.asyncio


@pytest.fixture
def toxic():
    pass


reset_reported_props = {const.TEST_CONTENT: None}

call_with_retry = retry_exponential_backoff_with_jitter


def get_random_property_value():
    return dev_utils.get_random_string(100, True)


def wrap_as_reported_property(value, key=None):
    if key:
        return {const.TEST_CONTENT: {key: value}}
    else:
        return {const.TEST_CONTENT: value}


@pytest.mark.timeout(600)
@pytest.mark.stress
@pytest.mark.describe("Client Stress")
@pytest.mark.parametrize(*parametrize.auto_connect_disabled)
@pytest.mark.parametrize(*parametrize.connection_retry_disabled)
class TestTwinStress(object):
    @pytest.mark.parametrize(
        "iteration_count", [pytest.param(10, id="10 updates"), pytest.param(50, id="50 updates")]
    )
    @pytest.mark.it("Can send continuous reported property updates, one-at-a-time")
    async def test_stress_serial_reported_property_updates(
        self, client, service_helper, toxic, iteration_count, leak_tracker
    ):
        """
        Send reported property updates, one at a time, and verify that each one
        has been received at the service. Do not overlap these calls.
        """
        leak_tracker.set_initial_object_list()

        leak_tracker.set_initial_object_list()

        await call_with_retry(client, client.patch_twin_reported_properties, reset_reported_props)

        for i in range(iteration_count):
            logger.info("Iteration {} of {}".format(i, iteration_count))

            # Update the reported property.
            patch = wrap_as_reported_property(get_random_property_value())
            await call_with_retry(client, client.patch_twin_reported_properties, patch)

            # Wait for that reported property to arrive at the service.
            received = False
            while not received:
                received_patch = await service_helper.get_next_reported_patch_arrival()
                if (
                    const.REPORTED in received_patch
                    and received_patch[const.REPORTED][const.TEST_CONTENT]
                    == patch[const.TEST_CONTENT]
                ):
                    received = True
                else:
                    logger.info(
                        "Wrong patch received. Expecting {}, got {}".format(patch, received_patch)
                    )

        leak_tracker.check_for_leaks()

    @pytest.mark.parametrize(
        "iteration_count, batch_size",
        [
            pytest.param(20, 10, id="20 updates, 10 at a time"),
            pytest.param(250, 25, id="250 updates, 25 at a time"),
        ],
    )
    @pytest.mark.it("Can send continuous overlapped reported property updates")
    async def test_stress_parallel_reported_property_updates(
        self, client, service_helper, toxic, iteration_count, batch_size, leak_tracker
    ):
        """
        Update reported properties with many overlapped calls. Work in batches
        with `batch_size` overlapped calls in a batch. Verify that the updates arrive
        at the service.
        """
        leak_tracker.set_initial_object_list()

        leak_tracker.set_initial_object_list()

        await call_with_retry(client, client.patch_twin_reported_properties, reset_reported_props)

        for _ in range(0, iteration_count, batch_size):
            props = {
                "key_{}".format(k): get_random_property_value() for k in range(0, iteration_count)
            }

            # Do overlapped calls to update `batch_size` properties.
            tasks = [
                call_with_retry(
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

                if isinstance(received_test_content, dict):
                    # We check to make sure received_test_content is a dict because it may be
                    # a string left over from a previous test case.
                    # This can happen if if the tests are running fast and the reported
                    # property updates are being processed slowly.
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

        leak_tracker.check_for_leaks()

    @pytest.mark.parametrize(
        "iteration_count", [pytest.param(10, id="10 updates"), pytest.param(50, id="50 updates")]
    )
    @pytest.mark.it("Can receive continuous desired property updates that were sent one-at-a-time")
    async def test_stress_serial_desired_property_updates(
        self, client, service_helper, toxic, iteration_count, event_loop, leak_tracker
    ):
        """
        Update desired properties, one at a time, and verify that the desired property arrives
        at the client before the next update.
        """
        leak_tracker.set_initial_object_list()

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

            # wait for the property update to arrive at the client
            received_patch = await asyncio.wait_for(patches.get(), 60)
            assert received_patch[const.TEST_CONTENT] == property_value

        leak_tracker.check_for_leaks()

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
    async def test_stress_parallel_desired_property_updates(
        self, client, service_helper, toxic, iteration_count, batch_size, event_loop, leak_tracker
    ):
        """
        Update desired properties in batches. Each batch updates `batch_size` properties,
        with each property being updated in it's own `PATCH`.
        """
        leak_tracker.set_initial_object_list()

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

            # update `batch_size` properties, each with a call to `set_desired_properties`
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

        leak_tracker.check_for_leaks()

    @pytest.mark.parametrize(
        "iteration_count", [pytest.param(10, id="10 updates"), pytest.param(50, id="50 updates")]
    )
    @pytest.mark.it("Can continuously call get_twin and get valid property values")
    async def test_stress_serial_get_twin_calls(
        self, client, service_helper, toxic, iteration_count, leak_tracker
    ):
        """
        Call `get_twin` once-at-a-time to verify that updated properties show up. This test
        calls `get_twin()` `iteration_count` times. Once a reported property shows up in the
        twin, that property is updated to be verified in future `get_twin` calls.
        """
        leak_tracker.set_initial_object_list()

        last_property_value = None
        current_property_value = None

        for i in range(iteration_count):
            logger.info("Iteration {} of {}".format(i, iteration_count))

            # Set a reported property
            if not current_property_value:
                current_property_value = get_random_property_value()
                logger.info("patching to {}".format(current_property_value))
                await call_with_retry(
                    client,
                    client.patch_twin_reported_properties,
                    wrap_as_reported_property(current_property_value),
                )

            # Call get_twin to verify that this property arrived.
            # reported properties aren't immediately reflected in `get_twin` calls,
            # so we have to account for retrieving old property values.
            twin = await call_with_retry(client, client.get_twin)
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

        leak_tracker.check_for_leaks()

        leak_tracker.check_for_leaks()

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
        self, client, service_helper, toxic, iteration_count, batch_size, leak_tracker
    ):
        """
        Call `get_twin` many times, overlapped, to verify that updated properties show up. This test
        calls `get_twin()` `iteration_count` times. Once a reported property shows up in the
        twin, that property is updated to be verified in future `get_twin` calls.
        """
        leak_tracker.set_initial_object_list()

        last_property_value = None
        current_property_value = get_random_property_value()

        await call_with_retry(
            client,
            client.patch_twin_reported_properties,
            wrap_as_reported_property(current_property_value),
        )
        ready_to_test = False

        while not ready_to_test:
            twin = await call_with_retry(client, client.get_twin)
            if twin[const.REPORTED].get(const.TEST_CONTENT, "") == current_property_value:
                logger.info("Initial value set")
                ready_to_test = True
            else:
                logger.info("Waiting for initial value. Sleeping for 5")
                await asyncio.sleep(5)

        for i in range(0, iteration_count, batch_size):
            logger.info("Iteration {} of {}".format(i, iteration_count))

            # Update the property if it's time to update
            if not current_property_value:
                current_property_value = get_random_property_value()
                logger.info("patching to {}".format(current_property_value))
                await call_with_retry(
                    client,
                    client.patch_twin_reported_properties,
                    wrap_as_reported_property(current_property_value),
                )

            # Call `get_twin` many times overlapped and verify that we get either
            # the old property value (if we know it), or the new property value.
            tasks = [call_with_retry(client, client.get_twin) for _ in range(batch_size)]
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
            # it to `None` so the next iteration of the loop can update this value.
            if got_a_match:
                last_property_value = current_property_value
                current_property_value = None

        leak_tracker.check_for_leaks()
