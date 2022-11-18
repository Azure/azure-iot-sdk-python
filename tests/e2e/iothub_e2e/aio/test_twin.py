# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import asyncio
import pytest
import logging
import const
from dev_utils import get_random_dict
from azure.iot.device.exceptions import (
    ClientError,
    NoConnectionError,
)

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)

pytestmark = pytest.mark.asyncio


# TODO: tests with drop_incoming and reject_incoming

reset_reported_props = {const.TEST_CONTENT: None}

PACKET_DROP = "Packet Drop"
PACKET_REJECT = "Packet Reject"


@pytest.fixture(params=[PACKET_DROP, PACKET_REJECT])
def failure_type(request):
    return request.param


@pytest.mark.describe("Client Get Twin")
class TestGetTwin(object):
    @pytest.mark.it("Can get the twin")
    @pytest.mark.parametrize(
        "twin_enabled",
        [
            pytest.param(False, id="Twin not yet enabled"),
            pytest.param(True, id="Twin already enabled"),
        ],
    )
    @pytest.mark.quicktest_suite
    async def test_simple_get_twin(self, client, twin_enabled, service_helper, leak_tracker):
        leak_tracker.set_initial_object_list()

        if twin_enabled:
            await client._enable_feature("twin")

        twin1 = await client.get_twin()
        twin2 = await service_helper.get_twin()

        # NOTE: It would be nice to compare the full properties, but the service client one
        # has metadata the client does not have. Look into this further to expand testing.
        assert twin1["desired"]["$version"] == twin2.properties.desired["$version"]
        assert twin1["reported"]["$version"] == twin2.properties.reported["$version"]

        leak_tracker.check_for_leaks()

    @pytest.mark.it("Raises NoConnectionError if there is no connection (Twin not yet enabled)")
    @pytest.mark.quicktest_suite
    async def test_no_connection_twin_not_enabled(self, client, leak_tracker):
        leak_tracker.set_initial_object_list()

        await client.disconnect()
        assert not client.connected

        with pytest.raises(NoConnectionError):
            await client.get_twin()
        assert not client.connected

        # TODO: Why does this need a sleep, but the sync test doesn't?
        # There might be something here, investigate further
        await asyncio.sleep(0.1)
        leak_tracker.check_for_leaks()

    @pytest.mark.it(
        "Waits to complete until a connection is established if there is no connection (Twin already enabled)"
    )
    @pytest.mark.quicktest_suite
    async def test_no_connection_twin_enabled(self, client, service_helper, leak_tracker):
        leak_tracker.set_initial_object_list()

        await client._enable_feature("twin")

        await client.disconnect()
        assert not client.connected

        # Attempt to get twin
        get_twin_task = asyncio.ensure_future(client.get_twin())
        await asyncio.sleep(1)
        # Still not done
        assert not get_twin_task.done()
        # Connect
        await client.connect()
        await asyncio.sleep(0.5)
        # Task is now done
        assert get_twin_task.done()
        twin1 = await get_twin_task

        # Validate twin with service
        twin2 = await service_helper.get_twin()
        # NOTE: It would be nice to compare the full properties, but the service client one
        # has metadata the client does not have. Look into this further to expand testing.
        assert twin1["desired"]["$version"] == twin2.properties.desired["$version"]
        assert twin1["reported"]["$version"] == twin2.properties.reported["$version"]

        leak_tracker.check_for_leaks()


@pytest.mark.describe(
    "Client Get Twin with network failure (Connection Retry enabled, Twin not yet enabled)"
)
@pytest.mark.dropped_connection
@pytest.mark.connection_retry(True)
@pytest.mark.keep_alive(5)
class TestGetTwinNetworkFailureConnectionRetryEnabledTwinPatchNotEnabled(object):
    @pytest.mark.it("Raises NoConnectionError if client disconnects due to network failure")
    async def test_network_failure_causes_disconnect(
        self, client, failure_type, dropper, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Disrupt network
        if failure_type == PACKET_DROP:
            dropper.drop_outgoing()
        elif failure_type == PACKET_REJECT:
            dropper.reject_outgoing()

        # Attempt to get twin (implicitly enabling twin first)
        get_task = asyncio.ensure_future(client.get_twin())
        # Wait for client disconnect
        while client.connected:
            assert not get_task.done()
            await asyncio.sleep(0.5)
        # Client has now disconnected
        assert get_task.done()
        with pytest.raises(NoConnectionError):
            await get_task

        # Restore and wait so any background operations can resolve before leak checking
        dropper.restore_all()
        await asyncio.sleep(1)
        del get_task
        leak_tracker.check_for_leaks()

    @pytest.mark.it("Succeeds if network failure resolves before client can disconnect")
    async def test_network_failure_no_disconnect(
        self, client, failure_type, service_helper, dropper, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Disrupt network
        if failure_type == PACKET_DROP:
            dropper.drop_outgoing()
        elif failure_type == PACKET_REJECT:
            dropper.reject_outgoing()

        # Attempt to get twin (implicitly enabling twin first)
        get_task = asyncio.ensure_future(client.get_twin())

        # Has not been able to succeed due to network failure, but client is still connected
        await asyncio.sleep(1)
        assert not get_task.done()
        assert client.connected

        # Restore network, and operation succeeds
        dropper.restore_all()
        await asyncio.sleep(1)
        assert get_task.done()
        twin1 = await get_task

        # Get the twin from the service to compare
        twin2 = await service_helper.get_twin()
        # NOTE: It would be nice to compare the full properties, but the service client one
        # has metadata the client does not have. Look into this further to expand testing.
        assert twin1["desired"]["$version"] == twin2.properties.desired["$version"]
        assert twin1["reported"]["$version"] == twin2.properties.reported["$version"]

        leak_tracker.check_for_leaks()


@pytest.mark.describe(
    "Client Get Twin with network failure (Connection Retry disabled, Twin not yet enabled)"
)
@pytest.mark.dropped_connection
@pytest.mark.connection_retry(False)
@pytest.mark.keep_alive(5)
class TestGetTwinNetworkFailureConnectionRetryDisabledTwinPatchNotEnabled(object):
    @pytest.mark.it("Raises NoConnectionError if client disconnects due to network failure")
    async def test_network_failure_causes_disconnect(
        self, client, failure_type, dropper, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Disrupt network
        if failure_type == PACKET_DROP:
            dropper.drop_outgoing()
        elif failure_type == PACKET_REJECT:
            dropper.reject_outgoing()

        # Attempt to get twin (implicitly enabling twin first)
        get_task = asyncio.ensure_future(client.get_twin())
        # Wait for client disconnect
        while client.connected:
            assert not get_task.done()
            await asyncio.sleep(0.5)
        # Client has now disconnected
        assert get_task.done()
        with pytest.raises(NoConnectionError):
            await get_task

        del get_task
        leak_tracker.check_for_leaks()

    @pytest.mark.it("Succeeds if network failure resolves before client can disconnect")
    async def test_network_failure_no_disconnect(
        self, client, failure_type, service_helper, dropper, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Disrupt network
        if failure_type == PACKET_DROP:
            dropper.drop_outgoing()
        elif failure_type == PACKET_REJECT:
            dropper.reject_outgoing()

        # Attempt to get twin (implicitly enabling twin first)
        get_task = asyncio.ensure_future(client.get_twin())

        # Has not been able to succeed due to network failure, but client is still connected
        await asyncio.sleep(1)
        assert not get_task.done()
        assert client.connected

        # Restore network, and operation succeeds
        dropper.restore_all()
        await asyncio.sleep(1)
        assert get_task.done()
        twin1 = await get_task

        # Get the twin from the service to compare
        twin2 = await service_helper.get_twin()
        # NOTE: It would be nice to compare the full properties, but the service client one
        # has metadata the client does not have. Look into this further to expand testing.
        assert twin1["desired"]["$version"] == twin2.properties.desired["$version"]
        assert twin1["reported"]["$version"] == twin2.properties.reported["$version"]

        leak_tracker.check_for_leaks()


@pytest.mark.describe(
    "Client Get Twin with network failure (Connection Retry enabled, Twin already enabled)"
)
@pytest.mark.dropped_connection
@pytest.mark.connection_retry(True)
@pytest.mark.keep_alive(5)
class TestGetTwinNetworkFailureConnectionRetryEnabledTwinPatchAlreadyEnabled(object):
    @pytest.mark.it(
        "Succeeds once network is restored and client automatically reconnects after having disconnected due to network failure"
    )
    async def test_network_failure_causes_disconnect(
        self, client, failure_type, service_helper, dropper, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Enable twins
        await client._enable_feature("twin")

        # Disrupt network
        if failure_type == PACKET_DROP:
            dropper.drop_outgoing()
        elif failure_type == PACKET_REJECT:
            dropper.reject_outgoing()

        # Attempt to get twin
        get_task = asyncio.ensure_future(client.get_twin())
        # Wait for client disconnect
        while client.connected:
            assert not get_task.done()
            await asyncio.sleep(0.5)
        # Client has now disconnected and task will not finish until reconnection
        assert not get_task.done()
        dropper.restore_all()
        # Wait for client reconnect
        while not client.connected:
            assert not get_task.done()
            await asyncio.sleep(0.5)

        # Once connection is returned, the task will finish
        twin1 = await get_task

        # Get the twin from the service to compare
        twin2 = await service_helper.get_twin()
        # NOTE: It would be nice to compare the full properties, but the service client one
        # has metadata the client does not have. Look into this further to expand testing.
        assert twin1["desired"]["$version"] == twin2.properties.desired["$version"]
        assert twin1["reported"]["$version"] == twin2.properties.reported["$version"]

        leak_tracker.check_for_leaks()

    @pytest.mark.it("Succeeds if network failure resolves before client can disconnect")
    async def test_network_failure_no_disconnect(
        self, client, failure_type, service_helper, dropper, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Enable twins
        await client._enable_feature("twin")

        # Disrupt network
        if failure_type == PACKET_DROP:
            dropper.drop_outgoing()
        elif failure_type == PACKET_REJECT:
            dropper.reject_outgoing()

        # Attempt to get twin
        get_task = asyncio.ensure_future(client.get_twin())

        # Has not been able to succeed due to network failure, but client is still connected
        await asyncio.sleep(1)
        assert not get_task.done()
        assert client.connected

        # Restore network, and operation succeeds
        dropper.restore_all()
        await asyncio.sleep(1)
        assert get_task.done()
        twin1 = await get_task

        # Get the twin from the service to compare
        twin2 = await service_helper.get_twin()
        # NOTE: It would be nice to compare the full properties, but the service client one
        # has metadata the client does not have. Look into this further to expand testing.
        assert twin1["desired"]["$version"] == twin2.properties.desired["$version"]
        assert twin1["reported"]["$version"] == twin2.properties.reported["$version"]

        leak_tracker.check_for_leaks()


@pytest.mark.describe(
    "Client Get Twin with network failure (Connection Retry disabled, Twin already enabled)"
)
@pytest.mark.dropped_connection
@pytest.mark.connection_retry(False)
@pytest.mark.keep_alive(5)
class TestGetTwinNetworkFailureConnectionRetryDisabledTwinPatchAlreadyEnabled(object):
    @pytest.mark.it(
        "Succeeds once network is restored and client manually reconnects after having disconnected due to network failure"
    )
    async def test_network_failure_causes_disconnect(
        self, client, failure_type, service_helper, dropper, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Enable twins
        await client._enable_feature("twin")

        # Disrupt network
        if failure_type == PACKET_DROP:
            dropper.drop_outgoing()
        elif failure_type == PACKET_REJECT:
            dropper.reject_outgoing()

        # Attempt to get twin
        get_task = asyncio.ensure_future(client.get_twin())
        # Wait for client disconnect
        while client.connected:
            assert not get_task.done()
            await asyncio.sleep(0.5)
        # Client has now disconnected and task will not finish until reconnection
        assert not get_task.done()
        await asyncio.sleep(1)
        assert not get_task.done()
        dropper.restore_all()
        # Manually reconnect
        await client.connect()

        # Once connection is returned, the task will finish
        twin1 = await get_task

        # Get the twin from the service to compare
        twin2 = await service_helper.get_twin()
        # NOTE: It would be nice to compare the full properties, but the service client one
        # has metadata the client does not have. Look into this further to expand testing.
        assert twin1["desired"]["$version"] == twin2.properties.desired["$version"]
        assert twin1["reported"]["$version"] == twin2.properties.reported["$version"]

        leak_tracker.check_for_leaks()

    @pytest.mark.it("Succeeds if network failure resolves before client can disconnect")
    async def test_network_failure_no_disconnect(
        self, client, failure_type, service_helper, dropper, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Enable twins
        await client._enable_feature("twin")

        # Disrupt network
        if failure_type == PACKET_DROP:
            dropper.drop_outgoing()
        elif failure_type == PACKET_REJECT:
            dropper.reject_outgoing()

        # Attempt to get twin
        get_task = asyncio.ensure_future(client.get_twin())

        # Has not been able to succeed due to network failure, but client is still connected
        await asyncio.sleep(1)
        assert not get_task.done()
        assert client.connected

        # Restore network, and operation succeeds
        dropper.restore_all()
        await asyncio.sleep(1)
        assert get_task.done()
        twin1 = await get_task

        # Get the twin from the service to compare
        twin2 = await service_helper.get_twin()
        # NOTE: It would be nice to compare the full properties, but the service client one
        # has metadata the client does not have. Look into this further to expand testing.
        assert twin1["desired"]["$version"] == twin2.properties.desired["$version"]
        assert twin1["reported"]["$version"] == twin2.properties.reported["$version"]

        leak_tracker.check_for_leaks()


@pytest.mark.describe("Client Reported Properties")
class TestReportedProperties(object):
    @pytest.mark.it("Can set a simple reported property")
    @pytest.mark.parametrize(
        "twin_enabled",
        [
            pytest.param(False, id="Twin not yet enabled"),
            pytest.param(True, id="Twin already enabled"),
        ],
    )
    @pytest.mark.quicktest_suite
    async def test_sends_simple_reported_patch(
        self, client, twin_enabled, random_reported_props, service_helper, leak_tracker
    ):
        leak_tracker.set_initial_object_list()

        if twin_enabled:
            await client._enable_feature("twin")

        # patch properties
        await client.patch_twin_reported_properties(random_reported_props)

        # wait for patch to arrive at service and verify
        received_patch = await service_helper.get_next_reported_patch_arrival()
        assert (
            received_patch[const.REPORTED][const.TEST_CONTENT]
            == random_reported_props[const.TEST_CONTENT]
        )

        # get twin from the service and verify content
        twin = await client.get_twin()
        assert twin[const.REPORTED][const.TEST_CONTENT] == random_reported_props[const.TEST_CONTENT]

        leak_tracker.check_for_leaks()

    @pytest.mark.it("Raises correct exception for un-serializable patch")
    @pytest.mark.parametrize(
        "twin_enabled",
        [
            pytest.param(False, id="Twin not yet enabled"),
            pytest.param(True, id="Twin already enabled"),
        ],
    )
    async def test_bad_reported_patch_raises(self, client, twin_enabled, leak_tracker):
        leak_tracker.set_initial_object_list()

        if twin_enabled:
            await client._enable_feature("twin")

        # There's no way to serialize a function.
        def thing_that_cant_serialize():
            pass

        with pytest.raises(ClientError) as e_info:
            await client.patch_twin_reported_properties(thing_that_cant_serialize)
        assert isinstance(e_info.value.__cause__, TypeError)

        del e_info
        # TODO: Why does this need a sleep, but the sync test doesn't?
        # There might be something here, investigate further
        await asyncio.sleep(0.1)
        leak_tracker.check_for_leaks()

    @pytest.mark.it("Can clear a reported property")
    @pytest.mark.parametrize(
        "twin_enabled",
        [
            pytest.param(False, id="Twin not yet enabled"),
            pytest.param(True, id="Twin already enabled"),
        ],
    )
    @pytest.mark.quicktest_suite
    async def test_clear_property(
        self, client, twin_enabled, random_reported_props, service_helper, leak_tracker
    ):
        leak_tracker.set_initial_object_list()

        if twin_enabled:
            await client._enable_feature("twin")

        # patch properties and verify that the service received the patch
        await client.patch_twin_reported_properties(random_reported_props)
        received_patch = await service_helper.get_next_reported_patch_arrival()
        assert (
            received_patch[const.REPORTED][const.TEST_CONTENT]
            == random_reported_props[const.TEST_CONTENT]
        )

        # send a patch clearing properties and verify that the service received that patch
        await client.patch_twin_reported_properties(reset_reported_props)
        received_patch = await service_helper.get_next_reported_patch_arrival()
        assert (
            received_patch[const.REPORTED][const.TEST_CONTENT]
            == reset_reported_props[const.TEST_CONTENT]
        )

        # get the twin and verify that the properties are no longer part of the twin
        twin = await client.get_twin()
        assert const.TEST_CONTENT not in twin[const.REPORTED]

        leak_tracker.check_for_leaks()

    @pytest.mark.it("Raises NoConnectionError if there is no connection (Twin not yet enabled)")
    @pytest.mark.quicktest_suite
    async def test_no_connection_twin_not_enabled(
        self, client, random_reported_props, leak_tracker
    ):
        leak_tracker.set_initial_object_list()

        await client.disconnect()
        assert not client.connected

        with pytest.raises(NoConnectionError):
            await client.patch_twin_reported_properties(random_reported_props)
        assert not client.connected

        # TODO: Why does this need a sleep, but the sync test doesn't?
        # There might be something here, investigate further
        await asyncio.sleep(0.1)
        leak_tracker.check_for_leaks()

    @pytest.mark.it(
        "Waits to complete until a connection is established if there is no connection (Twin already enabled)"
    )
    @pytest.mark.quicktest_suite
    async def test_no_connection_twin_enabled(
        self, client, service_helper, random_reported_props, leak_tracker
    ):
        leak_tracker.set_initial_object_list()

        await client._enable_feature("twin")

        await client.disconnect()
        assert not client.connected

        # Attempt to patch
        patch_task = asyncio.ensure_future(
            client.patch_twin_reported_properties(random_reported_props)
        )
        await asyncio.sleep(1)
        # Still not done
        assert not patch_task.done()
        # Connect
        await client.connect()
        await asyncio.sleep(0.5)
        # Task is now done
        assert patch_task.done()

        # wait for patch to arrive at service and verify
        received_patch = await service_helper.get_next_reported_patch_arrival()
        assert (
            received_patch[const.REPORTED][const.TEST_CONTENT]
            == random_reported_props[const.TEST_CONTENT]
        )

        # get twin from the service and verify content
        twin = await client.get_twin()
        assert twin[const.REPORTED][const.TEST_CONTENT] == random_reported_props[const.TEST_CONTENT]

        leak_tracker.check_for_leaks()


@pytest.mark.describe(
    "Client Reported Properties with network failure (Connection Retry enabled, Twin not yet enabled)"
)
@pytest.mark.dropped_connection
@pytest.mark.connection_retry(True)
@pytest.mark.keep_alive(5)
class TestReportedPropertiesNetworkFailureConnectionRetryEnabledTwinPatchNotEnabled(object):
    @pytest.mark.it("Raises NoConnectionError if client disconnects due to network failure")
    async def test_network_failure_causes_disconnect(
        self, client, random_reported_props, failure_type, dropper, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Disrupt network
        if failure_type == PACKET_DROP:
            dropper.drop_outgoing()
        elif failure_type == PACKET_REJECT:
            dropper.reject_outgoing()

        # Attempt to patch twin (implicitly enabling twin first)
        patch_task = asyncio.ensure_future(
            client.patch_twin_reported_properties(random_reported_props)
        )
        # Wait for client disconnect
        while client.connected:
            assert not patch_task.done()
            await asyncio.sleep(0.5)
        # Client has now disconnected
        assert patch_task.done()
        with pytest.raises(NoConnectionError):
            await patch_task

        # Restore and wait so any background operations can resolve before leak checking
        dropper.restore_all()
        await asyncio.sleep(1)
        del patch_task
        leak_tracker.check_for_leaks()

    @pytest.mark.it("Succeeds if network failure resolves before client can disconnect")
    async def test_network_failure_no_disconnect(
        self, client, random_reported_props, failure_type, service_helper, dropper, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Disrupt network
        if failure_type == PACKET_DROP:
            dropper.drop_outgoing()
        elif failure_type == PACKET_REJECT:
            dropper.reject_outgoing()

        # Attempt to patch twin (implicitly enabling twin first)
        patch_task = asyncio.ensure_future(
            client.patch_twin_reported_properties(random_reported_props)
        )

        # Has not been able to succeed due to network failure, but client is still connected
        await asyncio.sleep(1)
        assert not patch_task.done()
        assert client.connected

        # Restore network, and operation succeeds
        dropper.restore_all()
        await asyncio.sleep(1)
        assert patch_task.done()

        # wait for patch to arrive at service and verify
        received_patch = await service_helper.get_next_reported_patch_arrival()
        assert (
            received_patch[const.REPORTED][const.TEST_CONTENT]
            == random_reported_props[const.TEST_CONTENT]
        )

        # get twin from the service and verify content
        twin = await client.get_twin()
        assert twin[const.REPORTED][const.TEST_CONTENT] == random_reported_props[const.TEST_CONTENT]

        leak_tracker.check_for_leaks()


@pytest.mark.describe(
    "Client Reported Properties with network failure (Connection Retry disabled, Twin not yet enabled)"
)
@pytest.mark.dropped_connection
@pytest.mark.connection_retry(False)
@pytest.mark.keep_alive(5)
class TestReportedPropertiesNetworkFailureConnectionRetryDisabledTwinPatchNotEnabled(object):
    @pytest.mark.it("Raises NoConnectionError if client disconnects due to network failure")
    async def test_network_failure_causes_disconnect(
        self, client, random_reported_props, failure_type, dropper, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Disrupt network
        if failure_type == PACKET_DROP:
            dropper.drop_outgoing()
        elif failure_type == PACKET_REJECT:
            dropper.reject_outgoing()

        # Attempt to patch twin (implicitly enabling twin first)
        patch_task = asyncio.ensure_future(
            client.patch_twin_reported_properties(random_reported_props)
        )
        # Wait for client disconnect
        while client.connected:
            assert not patch_task.done()
            await asyncio.sleep(0.5)
        # Client has now disconnected
        assert patch_task.done()
        with pytest.raises(NoConnectionError):
            await patch_task

        del patch_task
        leak_tracker.check_for_leaks()

    @pytest.mark.it("Succeeds if network failure resolves before client can disconnect")
    async def test_network_failure_no_disconnect(
        self, client, random_reported_props, failure_type, service_helper, dropper, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Disrupt network
        if failure_type == PACKET_DROP:
            dropper.drop_outgoing()
        elif failure_type == PACKET_REJECT:
            dropper.reject_outgoing()

        # Attempt to patch twin (implicitly enabling twin first)
        patch_task = asyncio.ensure_future(
            client.patch_twin_reported_properties(random_reported_props)
        )

        # Has not been able to succeed due to network failure, but client is still connected
        await asyncio.sleep(1)
        assert not patch_task.done()
        assert client.connected

        # Restore network, and operation succeeds
        dropper.restore_all()
        await asyncio.sleep(1)
        assert patch_task.done()

        # wait for patch to arrive at service and verify
        received_patch = await service_helper.get_next_reported_patch_arrival()
        assert (
            received_patch[const.REPORTED][const.TEST_CONTENT]
            == random_reported_props[const.TEST_CONTENT]
        )

        # get twin from the service and verify content
        twin = await client.get_twin()
        assert twin[const.REPORTED][const.TEST_CONTENT] == random_reported_props[const.TEST_CONTENT]

        leak_tracker.check_for_leaks()


@pytest.mark.describe(
    "Client Reported Properties with network failure (Connection Retry enabled, Twin already enabled)"
)
@pytest.mark.dropped_connection
@pytest.mark.connection_retry(True)
@pytest.mark.keep_alive(5)
class TestReportedPropertiesTwinNetworkFailureConnectionRetryEnabledTwinPatchAlreadyEnabled(object):
    @pytest.mark.it(
        "Succeeds once network is restored and client automatically reconnects after having disconnected due to network failure"
    )
    async def test_network_failure_causes_disconnect(
        self, client, random_reported_props, failure_type, service_helper, dropper, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Enable twins
        await client._enable_feature("twin")

        # Disrupt network
        if failure_type == PACKET_DROP:
            dropper.drop_outgoing()
        elif failure_type == PACKET_REJECT:
            dropper.reject_outgoing()

        # Attempt to patch twin
        patch_task = asyncio.ensure_future(
            client.patch_twin_reported_properties(random_reported_props)
        )

        # Wait for client disconnect
        while client.connected:
            assert not patch_task.done()
            await asyncio.sleep(0.5)
        # Client has now disconnected and task will not finish until reconnection
        assert not patch_task.done()
        dropper.restore_all()
        # Wait for client reconnect
        while not client.connected:
            assert not patch_task.done()
            await asyncio.sleep(0.5)

        # Once connection is returned, the task will finish
        patch_task

        # wait for patch to arrive at service and verify
        received_patch = await service_helper.get_next_reported_patch_arrival()
        assert (
            received_patch[const.REPORTED][const.TEST_CONTENT]
            == random_reported_props[const.TEST_CONTENT]
        )

        # get twin from the service and verify content
        twin = await client.get_twin()
        assert twin[const.REPORTED][const.TEST_CONTENT] == random_reported_props[const.TEST_CONTENT]

        leak_tracker.check_for_leaks()

    @pytest.mark.it("Succeeds if network failure resolves before client can disconnect")
    async def test_network_failure_no_disconnect(
        self, client, random_reported_props, failure_type, service_helper, dropper, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Enable twins
        await client._enable_feature("twin")

        # Disrupt network
        if failure_type == PACKET_DROP:
            dropper.drop_outgoing()
        elif failure_type == PACKET_REJECT:
            dropper.reject_outgoing()

        # Attempt to patch twin
        patch_task = asyncio.ensure_future(
            client.patch_twin_reported_properties(random_reported_props)
        )

        # Has not been able to succeed due to network failure, but client is still connected
        await asyncio.sleep(1)
        assert not patch_task.done()
        assert client.connected

        # Restore network, and operation succeeds
        dropper.restore_all()
        await asyncio.sleep(1)
        assert patch_task.done()

        # wait for patch to arrive at service and verify
        received_patch = await service_helper.get_next_reported_patch_arrival()
        assert (
            received_patch[const.REPORTED][const.TEST_CONTENT]
            == random_reported_props[const.TEST_CONTENT]
        )

        # get twin from the service and verify content
        twin = await client.get_twin()
        assert twin[const.REPORTED][const.TEST_CONTENT] == random_reported_props[const.TEST_CONTENT]

        leak_tracker.check_for_leaks()


@pytest.mark.describe(
    "Client Reported Properties with network failure (Connection Retry disabled, Twin already enabled)"
)
@pytest.mark.dropped_connection
@pytest.mark.connection_retry(False)
@pytest.mark.keep_alive(5)
class TestReportedPropertiesNetworkFailureConnectionRetryDisabledTwinPatchAlreadyEnabled(object):
    @pytest.mark.it(
        "Succeeds once network is restored and client manually reconnects after having disconnected due to network failure"
    )
    async def test_network_failure_causes_disconnect(
        self, client, random_reported_props, failure_type, service_helper, dropper, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Enable twins
        await client._enable_feature("twin")

        # Disrupt network
        if failure_type == PACKET_DROP:
            dropper.drop_outgoing()
        elif failure_type == PACKET_REJECT:
            dropper.reject_outgoing()

        # Attempt to patch twin
        patch_task = asyncio.ensure_future(
            client.patch_twin_reported_properties(random_reported_props)
        )

        # Wait for client disconnect
        while client.connected:
            assert not patch_task.done()
            await asyncio.sleep(0.5)
        # Client has now disconnected and task will not finish until reconnection
        assert not patch_task.done()
        await asyncio.sleep(1)
        assert not patch_task.done()
        dropper.restore_all()
        # Manually reconnect
        await client.connect()

        # Once connection is returned, the task will finish
        patch_task

        # wait for patch to arrive at service and verify
        received_patch = await service_helper.get_next_reported_patch_arrival()
        assert (
            received_patch[const.REPORTED][const.TEST_CONTENT]
            == random_reported_props[const.TEST_CONTENT]
        )

        # get twin from the service and verify content
        twin = await client.get_twin()
        assert twin[const.REPORTED][const.TEST_CONTENT] == random_reported_props[const.TEST_CONTENT]

        leak_tracker.check_for_leaks()

    @pytest.mark.it("Succeeds if network failure resolves before client can disconnect")
    async def test_network_failure_no_disconnect(
        self, client, random_reported_props, failure_type, service_helper, dropper, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Enable twins
        await client._enable_feature("twin")

        # Disrupt network
        if failure_type == PACKET_DROP:
            dropper.drop_outgoing()
        elif failure_type == PACKET_REJECT:
            dropper.reject_outgoing()

        # Attempt to patch twin
        patch_task = asyncio.ensure_future(
            client.patch_twin_reported_properties(random_reported_props)
        )

        # Has not been able to succeed due to network failure, but client is still connected
        await asyncio.sleep(1)
        assert not patch_task.done()
        assert client.connected

        # Restore network, and operation succeeds
        dropper.restore_all()
        await asyncio.sleep(1)
        assert patch_task.done()

        # wait for patch to arrive at service and verify
        received_patch = await service_helper.get_next_reported_patch_arrival()
        assert (
            received_patch[const.REPORTED][const.TEST_CONTENT]
            == random_reported_props[const.TEST_CONTENT]
        )

        # get twin from the service and verify content
        twin = await client.get_twin()
        assert twin[const.REPORTED][const.TEST_CONTENT] == random_reported_props[const.TEST_CONTENT]

        leak_tracker.check_for_leaks()


@pytest.mark.describe("Client Desired Properties")
class TestDesiredProperties(object):
    @pytest.mark.it("Receives a patch for a simple desired property")
    @pytest.mark.quicktest_suite
    async def test_receives_simple_desired_patch(
        self, client, event_loop, service_helper, leak_tracker
    ):
        leak_tracker.set_initial_object_list()

        received_patch = None
        received = asyncio.Event()

        async def handle_on_patch_received(patch):
            nonlocal received_patch, received
            print("received {}".format(patch))
            received_patch = patch
            event_loop.call_soon_threadsafe(received.set)

        client.on_twin_desired_properties_patch_received = handle_on_patch_received
        await client.enable_twin_desired_properties_patch_receive()

        random_dict = get_random_dict()
        await service_helper.set_desired_properties(
            {const.TEST_CONTENT: random_dict},
        )

        await asyncio.wait_for(received.wait(), 60)
        assert received.is_set()

        assert received_patch[const.TEST_CONTENT] == random_dict

        twin = await client.get_twin()
        assert twin[const.DESIRED][const.TEST_CONTENT] == random_dict

        leak_tracker.check_for_leaks()


# TODO: etag tests, version tests
