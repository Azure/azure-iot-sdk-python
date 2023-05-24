# Copyright (c) Microsoft Corporation. All rights teserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import asyncio
import pytest
import logging
import const
import sys
from dev_utils import get_random_dict
from azure.iot.device import MQTTConnectionDroppedError, SessionError
import paho.mqtt.client as paho


logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)


# TODO: tests with drop_incoming and reject_incoming

reset_reported_props = {const.TEST_CONTENT: None}

PACKET_DROP = "Packet Drop"
PACKET_REJECT = "Packet Reject"

twin_enabled_and_disabled = [
    "twin_enabled",
    [
        pytest.param(False, id="Twin not yet enabled"),
        pytest.param(True, id="Twin already enabled"),
    ],
]


@pytest.fixture(params=[PACKET_DROP, PACKET_REJECT])
def failure_type(request):
    return request.param


@pytest.mark.describe("Client Get Twin")
class TestGetTwin(object):
    @pytest.mark.it("Can get the twin")
    @pytest.mark.quicktest_suite
    async def test_simple_get_twin(self, leak_tracker, service_helper, session):
        leak_tracker.set_initial_object_list()

        async with session:
            twin1 = await session.get_twin()
        assert session.connected is False

        twin2 = await service_helper.get_twin()

        # NOTE: It would be nice to compare the full properties, but the service client one
        # has metadata the client does not have. Look into this further to expand testing.
        assert twin1["desired"]["$version"] == twin2.properties.desired["$version"]
        assert twin1["reported"]["$version"] == twin2.properties.reported["$version"]

        leak_tracker.check_for_leaks()

    @pytest.mark.it("Raises SessionError if there is no connection (Twin not yet enabled)")
    @pytest.mark.quicktest_suite
    async def test_no_connection_twin_not_enabled(self, leak_tracker, session):
        leak_tracker.set_initial_object_list()

        assert not session.connected
        assert session._mqtt_client._twin_responses_enabled is False

        with pytest.raises(SessionError):
            await session.get_twin()
        assert session.connected is False

        leak_tracker.check_for_leaks()

    @pytest.mark.it("Raises SessionError if there is no connection (Twin already enabled)")
    @pytest.mark.quicktest_suite
    async def test_no_connection_twin_enabled(self, leak_tracker, session):
        leak_tracker.set_initial_object_list()

        # Get an initial twin (implicitly enabling twin receive)
        async with session:
            t = await session.get_twin()
        assert t is not None

        assert session.connected is False
        assert session._mqtt_client._twin_responses_enabled is True

        # Try to get a twin, this time outside of context manager (i.e. not connected)
        with pytest.raises(SessionError):
            await session.get_twin()
        assert not session.connected

        leak_tracker.check_for_leaks()

    @pytest.mark.it(
        "Raises MQTTConnectionDroppedError on get_twin if network error causes failure enabling twin responses"
    )
    @pytest.mark.keep_alive(5)
    async def test_get_twin_raises_if_network_error_enabling_twin_responses(
        self, dropper, leak_tracker, session, failure_type
    ):
        leak_tracker.set_initial_object_list()

        async with session:
            assert session.connected

            # Disrupt network
            if failure_type == PACKET_DROP:
                dropper.drop_outgoing()
            elif failure_type == PACKET_REJECT:
                dropper.reject_outgoing()

            # Attempt to get twin (implicitly enabling twin first)
            assert session._mqtt_client._twin_responses_enabled is False
            with pytest.raises(MQTTConnectionDroppedError) as e_info:
                await session.get_twin()
            assert e_info.value.rc in [paho.MQTT_ERR_CONN_LOST, paho.MQTT_ERR_KEEPALIVE]
            del e_info
            assert session._mqtt_client._twin_responses_enabled is False

        assert session.connected is False
        leak_tracker.check_for_leaks()

    @pytest.mark.skip("get_twin doesn't time out if no response")
    @pytest.mark.keep_alive(5)
    @pytest.mark.it("Raises Error on get_twin if network error causes request or response to fail")
    async def test_get_twin_raises_if_network_error_on_request_or_response(
        self, dropper, leak_tracker, session, failure_type
    ):
        leak_tracker.set_initial_object_list()

        async with session:
            assert session.connected is True

            assert session._mqtt_client._twin_responses_enabled is False
            await session.get_twin()
            assert session._mqtt_client._twin_responses_enabled is True

            # Disrupt network
            if failure_type == PACKET_DROP:
                dropper.drop_outgoing()
            elif failure_type == PACKET_REJECT:
                dropper.reject_outgoing()

            # TODO: is this the right exception?
            with pytest.raises(asyncio.CancelledError):
                await session.get_twin()

        assert session.connected is False
        leak_tracker.check_for_leaks()

    # TODO "Succeeds if network failure resolves before session can disconnect"


@pytest.mark.describe("Client Reported Properties")
class TestReportedProperties(object):
    @pytest.mark.it("Can set a simple reported property")
    @pytest.mark.parametrize(*twin_enabled_and_disabled)
    @pytest.mark.quicktest_suite
    async def test_sends_simple_reported_patch(
        self, leak_tracker, service_helper, session, twin_enabled, random_reported_props
    ):
        leak_tracker.set_initial_object_list()

        async with session:
            # Enable twin responses if necessary
            assert session._mqtt_client._twin_responses_enabled is False
            if twin_enabled:
                await session.get_twin()
                assert session._mqtt_client._twin_responses_enabled is True

            # patch properties
            await session.update_reported_properties(random_reported_props)

            assert session._mqtt_client._twin_responses_enabled is True

            # wait for patch to arrive at service and verify
            received_patch = await service_helper.get_next_reported_patch_arrival()
            assert (
                received_patch[const.REPORTED][const.TEST_CONTENT]
                == random_reported_props[const.TEST_CONTENT]
            )

            # get twin from the service and verify content
            twin = await session.get_twin()
            assert (
                twin[const.REPORTED][const.TEST_CONTENT]
                == random_reported_props[const.TEST_CONTENT]
            )

        leak_tracker.check_for_leaks()

    @pytest.mark.it("Raises correct exception for un-serializable patch")
    @pytest.mark.parametrize(*twin_enabled_and_disabled)
    async def test_bad_reported_patch_raises(self, leak_tracker, session, twin_enabled):
        leak_tracker.set_initial_object_list()

        async with session:
            # Enable twin responses if necessary
            assert session._mqtt_client._twin_responses_enabled is False
            if twin_enabled:
                await session.get_twin()
                assert session._mqtt_client._twin_responses_enabled is True

            # There's no way to serialize a function.
            def thing_that_cant_serialize():
                pass

            with pytest.raises(TypeError):
                await session.update_reported_properties(thing_that_cant_serialize)

        assert session.connected is False

        leak_tracker.check_for_leaks()

    @pytest.mark.it("Can clear a reported property")
    @pytest.mark.parametrize(*twin_enabled_and_disabled)
    @pytest.mark.quicktest_suite
    async def test_clear_property(
        self, leak_tracker, service_helper, session, twin_enabled, random_reported_props
    ):
        leak_tracker.set_initial_object_list()

        async with session:
            # Enable twin responses if necessary
            assert session._mqtt_client._twin_responses_enabled is False
            if twin_enabled:
                await session.get_twin()
                assert session._mqtt_client._twin_responses_enabled is True

            # patch properties and verify that the service received the patch
            await session.update_reported_properties(random_reported_props)
            received_patch = await service_helper.get_next_reported_patch_arrival()
            assert (
                received_patch[const.REPORTED][const.TEST_CONTENT]
                == random_reported_props[const.TEST_CONTENT]
            )

            # send a patch clearing properties and verify that the service received that patch
            await session.update_reported_properties(reset_reported_props)
            received_patch = await service_helper.get_next_reported_patch_arrival()
            assert (
                received_patch[const.REPORTED][const.TEST_CONTENT]
                == reset_reported_props[const.TEST_CONTENT]
            )

            # get the twin and verify that the properties are no longer part of the twin
            twin = await session.get_twin()
            assert const.TEST_CONTENT not in twin[const.REPORTED]

        assert session.connected is False

        leak_tracker.check_for_leaks()

    @pytest.mark.it("Raises SessionError if there is no connection")
    @pytest.mark.parametrize(*twin_enabled_and_disabled)
    @pytest.mark.quicktest_suite
    async def test_no_connection_raises_error(
        self, leak_tracker, session, random_reported_props, twin_enabled
    ):
        leak_tracker.set_initial_object_list()

        # Enable twin responses if necessary
        assert session._mqtt_client._twin_responses_enabled is False
        if twin_enabled:
            async with session:
                await session.get_twin()

                assert session._mqtt_client._twin_responses_enabled is True
        assert session.connected is False

        with pytest.raises(SessionError):
            await session.update_reported_properties(random_reported_props)
        assert session.connected is False

        leak_tracker.check_for_leaks()


@pytest.mark.describe("Client Desired Properties")
class TestDesiredProperties(object):
    @pytest.mark.it("Receives a patch for a simple desired property")
    @pytest.mark.quicktest_suite
    async def test_receives_simple_desired_patch(
        self, event_loop, leak_tracker, service_helper, session
    ):
        random_dict = get_random_dict()
        leak_tracker.set_initial_object_list()

        # Make a task to pull incoming patches from the generator and pyt
        # them into a queue.
        # In py310, anext can do the same thing, but we need to support older
        # versions.

        queue = asyncio.Queue()
        registered = asyncio.Event()

        async def listener(sess):
            try:
                async with sess.desired_property_updates() as patches:
                    # signal that we're registered
                    registered.set()
                    async for patch in patches:
                        await queue.put(patch)
            except asyncio.CancelledError:
                # this happens during shutdown. no need to log this.
                raise
            except BaseException:
                # Without this line, exceptions get silently ignored until
                # we await the listener task.
                logger.error("Exception", exc_info=True)
                raise

        async with session:
            listener_task = asyncio.create_task(listener(session))
            await registered.wait()

            await service_helper.set_desired_properties(
                {const.TEST_CONTENT: random_dict},
            )

            received_patch = await queue.get()
            assert received_patch[const.TEST_CONTENT] == random_dict

            twin = await session.get_twin()
            assert twin[const.DESIRED][const.TEST_CONTENT] == random_dict

        assert session.connected is False

        # make sure our listener ended with an error when we disconnected.
        logger.info("Waiting for listener_task to complete")
        with pytest.raises(asyncio.CancelledError):
            await listener_task
        logger.info("Done waiting for listener_task")

        leak_tracker.check_for_leaks()

    @pytest.mark.it("Receives a patch for a simple desired property entering session context twice")
    @pytest.mark.quicktest_suite
    async def test_receives_simple_desired_patch_enter_session_twice(
        self, event_loop, leak_tracker, service_helper, session
    ):
        random_dict = get_random_dict()
        leak_tracker.set_initial_object_list()

        # Make a task to pull incoming patches from the generator and pyt
        # them into a queue.
        # In py310, anext can do the same thing, but we need to support older
        # versions.

        queue = asyncio.Queue()
        registered = asyncio.Event()

        async def listener(sess):
            try:
                # This `async with` is the only difference from the previous test.
                async with sess:
                    async with sess.desired_property_updates() as patches:
                        # signal that we're registered
                        registered.set()
                        async for patch in patches:
                            await queue.put(patch)
            except asyncio.CancelledError:
                # this happens during shutdown. no need to log this.
                raise
            except Exception:
                # Without this line, exceptions get silently ignored until
                # we await the listener task.
                logger.error("Exception", exc_info=True)
                raise

        async with session:
            listener_task = asyncio.create_task(listener(session))
            await registered.wait()

            await service_helper.set_desired_properties(
                {const.TEST_CONTENT: random_dict},
            )

            received_patch = await queue.get()
            assert received_patch[const.TEST_CONTENT] == random_dict

            twin = await session.get_twin()
            assert twin[const.DESIRED][const.TEST_CONTENT] == random_dict

        assert session.connected is False

        # make sure our listener ended with an error when we disconnected.
        logger.info("Waiting for listener_task to complete")
        with pytest.raises(asyncio.CancelledError):
            await listener_task
        logger.info("Done waiting for listener_task")

        leak_tracker.check_for_leaks()

    @pytest.mark.skip("leaks")
    @pytest.mark.it("Receives a patch for a simple desired property using anext")
    @pytest.mark.quicktest_suite
    @pytest.mark.skipif(
        sys.version_info.major == 3 and sys.version_info.minor < 10,
        reason="anext was not introduced until 3.10",
    )
    async def test_receives_simple_desired_patch_using_anext(
        self, event_loop, leak_tracker, service_helper, session
    ):
        leak_tracker.set_initial_object_list()
        random_dict = get_random_dict()

        # Python 3.10 makes our lives easier because we can use anext() and treat the generator like a queue

        async with session:
            async with session.desired_property_updates() as patches:
                await service_helper.set_desired_properties(
                    {const.TEST_CONTENT: random_dict},
                )

            received_patch = await anext(patches)  # noqa: F821
            assert received_patch[const.TEST_CONTENT] == random_dict

            twin = await session.get_twin()
            assert twin[const.DESIRED][const.TEST_CONTENT] == random_dict

        assert session.connected is False

        leak_tracker.check_for_leaks()


# TODO: etag tests, version tests
