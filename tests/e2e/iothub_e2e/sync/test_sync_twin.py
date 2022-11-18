# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import pytest
import logging
import time
import const
import queue
from dev_utils import get_random_dict
from azure.iot.device.exceptions import (
    ClientError,
    NoConnectionError,
)

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)
logging.basicConfig(level=logging.ERROR)

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
    def test_sync_simple_get_twin(self, client, twin_enabled, service_helper, leak_tracker):
        leak_tracker.set_initial_object_list()

        if twin_enabled:
            client._enable_feature("twin")

        twin1 = client.get_twin()
        twin2 = service_helper.get_twin()

        # NOTE: It would be nice to compare the full properties, but the service client one
        # has metadata the client does not have. Look into this further to expand testing.
        assert twin1["desired"]["$version"] == twin2.properties.desired["$version"]
        assert twin1["reported"]["$version"] == twin2.properties.reported["$version"]

        leak_tracker.check_for_leaks()

    @pytest.mark.it("Raises NoConnectionError if there is no connection (Twin not yet enabled)")
    @pytest.mark.quicktest_suite
    def test_sync_no_connection_twin_not_enabled(self, client, leak_tracker):
        leak_tracker.set_initial_object_list()

        client.disconnect()
        assert not client.connected

        with pytest.raises(NoConnectionError):
            client.get_twin()
        assert not client.connected

        leak_tracker.check_for_leaks()

    @pytest.mark.it(
        "Waits to complete until a connection is established if there is no connection (Twin already enabled)"
    )
    @pytest.mark.quicktest_suite
    def test_sync_no_connection_twin_enabled(self, client, service_helper, executor, leak_tracker):
        leak_tracker.set_initial_object_list()

        client._enable_feature("twin")

        client.disconnect()
        assert not client.connected

        # Attempt to get twin
        get_task = executor.submit(client.get_twin)
        time.sleep(1)
        # Still not done
        assert not get_task.done()
        # Connect
        client.connect()
        time.sleep(0.5)
        # Task is now done
        assert get_task.done()
        twin1 = get_task.result()

        # Validate twin with service
        twin2 = service_helper.get_twin()
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
    def test_sync_network_failure_causes_disconnect(
        self, client, failure_type, dropper, executor, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Disrupt network
        if failure_type == PACKET_DROP:
            dropper.drop_outgoing()
        elif failure_type == PACKET_REJECT:
            dropper.reject_outgoing()

        # Attempt to get twin (implicitly enabling twin first)
        get_task = executor.submit(client.get_twin)
        # Wait for client disconnect
        while client.connected:
            assert not get_task.done()
            time.sleep(0.5)
        # Client has now disconnected
        assert get_task.done()
        with pytest.raises(NoConnectionError):
            get_task.result()

        # Restore and wait so any background operations can resolve before leak checking
        dropper.restore_all()
        time.sleep(1)
        del get_task
        leak_tracker.check_for_leaks()

    @pytest.mark.it("Succeeds if network failure resolves before client can disconnect")
    def test_sync_network_failure_no_disconnect(
        self, client, failure_type, service_helper, dropper, executor, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Disrupt network
        if failure_type == PACKET_DROP:
            dropper.drop_outgoing()
        elif failure_type == PACKET_REJECT:
            dropper.reject_outgoing()

        # Attempt to get twin (implicitly enabling twin first)
        get_task = executor.submit(client.get_twin)

        # Has not been able to succeed due to network failure, but client is still connected
        time.sleep(1)
        assert not get_task.done()
        assert client.connected

        # Restore network, and operation succeeds
        dropper.restore_all()
        time.sleep(1)
        assert get_task.done()
        twin1 = get_task.result()

        # Get the twin from the service to compare
        twin2 = service_helper.get_twin()
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
    def test_sync_network_failure_causes_disconnect(
        self, client, failure_type, dropper, executor, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Disrupt network
        if failure_type == PACKET_DROP:
            dropper.drop_outgoing()
        elif failure_type == PACKET_REJECT:
            dropper.reject_outgoing()

        # Attempt to get twin (implicitly enabling twin first)
        get_task = executor.submit(client.get_twin)
        # Wait for client disconnect
        while client.connected:
            assert not get_task.done()
            time.sleep(0.5)
        # Client has now disconnected
        assert get_task.done()
        with pytest.raises(NoConnectionError):
            get_task.result()

        del get_task
        leak_tracker.check_for_leaks()

    @pytest.mark.it("Succeeds if network failure resolves before client can disconnect")
    def test_sync_network_failure_no_disconnect(
        self, client, failure_type, service_helper, dropper, executor, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Disrupt network
        if failure_type == PACKET_DROP:
            dropper.drop_outgoing()
        elif failure_type == PACKET_REJECT:
            dropper.reject_outgoing()

        # Attempt to get twin (implicitly enabling twin first)
        get_task = executor.submit(client.get_twin)

        # Has not been able to succeed due to network failure, but client is still connected
        time.sleep(1)
        assert not get_task.done()
        assert client.connected

        # Restore network, and operation succeeds
        dropper.restore_all()
        time.sleep(1)
        assert get_task.done()
        twin1 = get_task.result()

        # Get the twin from the service to compare
        twin2 = service_helper.get_twin()
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
    def test_sync_network_failure_causes_disconnect(
        self, client, failure_type, service_helper, dropper, executor, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Enable twins
        client._enable_feature("twin")

        # Disrupt network
        if failure_type == PACKET_DROP:
            dropper.drop_outgoing()
        elif failure_type == PACKET_REJECT:
            dropper.reject_outgoing()

        # Attempt to get twin
        get_task = executor.submit(client.get_twin)

        # Wait for client disconnect
        while client.connected:
            assert not get_task.done()
            time.sleep(0.5)
        # Client has now disconnected and task will not finish until reconnection
        assert not get_task.done()
        dropper.restore_all()
        # Wait for client reconnect
        while not client.connected:
            assert not get_task.done()
            time.sleep(0.5)

        # Once connection is returned, the task will finish
        twin1 = get_task.result()

        # Get the twin from the service to compare
        twin2 = service_helper.get_twin()
        # NOTE: It would be nice to compare the full properties, but the service client one
        # has metadata the client does not have. Look into this further to expand testing.
        assert twin1["desired"]["$version"] == twin2.properties.desired["$version"]
        assert twin1["reported"]["$version"] == twin2.properties.reported["$version"]

        leak_tracker.check_for_leaks()

    @pytest.mark.it("Succeeds if network failure resolves before client can disconnect")
    def test_sync_network_failure_no_disconnect(
        self, client, failure_type, service_helper, dropper, executor, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Enable twins
        client._enable_feature("twin")

        # Disrupt network
        if failure_type == PACKET_DROP:
            dropper.drop_outgoing()
        elif failure_type == PACKET_REJECT:
            dropper.reject_outgoing()

        # Attempt to get twin
        get_task = executor.submit(client.get_twin)

        # Has not been able to succeed due to network failure, but client is still connected
        time.sleep(1)
        assert not get_task.done()
        assert client.connected

        # Restore network, and operation succeeds
        dropper.restore_all()
        time.sleep(1)
        assert get_task.done()
        twin1 = get_task.result()

        # Get the twin from the service to compare
        twin2 = service_helper.get_twin()
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
    def test_sync_network_failure_causes_disconnect(
        self, client, failure_type, service_helper, dropper, executor, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Enable twins
        client._enable_feature("twin")

        # Disrupt network
        if failure_type == PACKET_DROP:
            dropper.drop_outgoing()
        elif failure_type == PACKET_REJECT:
            dropper.reject_outgoing()

        # Attempt to get twin
        get_task = executor.submit(client.get_twin)

        # Wait for client disconnect
        while client.connected:
            assert not get_task.done()
            time.sleep(0.5)
        # Client has now disconnected and task will not finish until reconnection
        assert not get_task.done()
        time.sleep(1)
        assert not get_task.done()
        dropper.restore_all()
        # Manually reconnect
        client.connect()

        # Once connection is returned, the task will finish
        twin1 = get_task.result()

        # Get the twin from the service to compare
        twin2 = service_helper.get_twin()
        # NOTE: It would be nice to compare the full properties, but the service client one
        # has metadata the client does not have. Look into this further to expand testing.
        assert twin1["desired"]["$version"] == twin2.properties.desired["$version"]
        assert twin1["reported"]["$version"] == twin2.properties.reported["$version"]

        leak_tracker.check_for_leaks()

    @pytest.mark.it("Succeeds if network failure resolves before client can disconnect")
    def test_sync_network_failure_no_disconnect(
        self, client, failure_type, service_helper, dropper, executor, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Enable twins
        client._enable_feature("twin")

        # Disrupt network
        if failure_type == PACKET_DROP:
            dropper.drop_outgoing()
        elif failure_type == PACKET_REJECT:
            dropper.reject_outgoing()

        # Attempt to get twin
        get_task = executor.submit(client.get_twin)

        # Has not been able to succeed due to network failure, but client is still connected
        time.sleep(1)
        assert not get_task.done()
        assert client.connected

        # Restore network, and operation succeeds
        dropper.restore_all()
        time.sleep(1)
        assert get_task.done()
        twin1 = get_task.result()

        # Get the twin from the service to compare
        twin2 = service_helper.get_twin()
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
    def test_sync_sends_simple_reported_patch(
        self, client, twin_enabled, random_reported_props, service_helper, leak_tracker
    ):
        leak_tracker.set_initial_object_list()

        if twin_enabled:
            client._enable_feature("twin")

        # patch properties
        client.patch_twin_reported_properties(random_reported_props)

        # wait for patch to arrive at service and verify
        received_patch = service_helper.get_next_reported_patch_arrival()
        assert (
            received_patch[const.REPORTED][const.TEST_CONTENT]
            == random_reported_props[const.TEST_CONTENT]
        )

        # get twin from the service and verify content
        twin = client.get_twin()
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
    def test_sync_bad_reported_patch_raises(self, client, twin_enabled, leak_tracker):
        leak_tracker.set_initial_object_list()

        if twin_enabled:
            client._enable_feature("twin")

        # There's no way to serialize a function.
        def thing_that_cant_serialize():
            pass

        with pytest.raises(ClientError) as e_info:
            client.patch_twin_reported_properties(thing_that_cant_serialize)
        assert isinstance(e_info.value.__cause__, TypeError)

        del e_info
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
    def test_sync_clear_property(
        self, client, twin_enabled, random_reported_props, service_helper, leak_tracker
    ):
        leak_tracker.set_initial_object_list()

        if twin_enabled:
            client._enable_feature("twin")

        # patch properties and verify that the service received the patch
        client.patch_twin_reported_properties(random_reported_props)
        received_patch = service_helper.get_next_reported_patch_arrival()
        assert (
            received_patch[const.REPORTED][const.TEST_CONTENT]
            == random_reported_props[const.TEST_CONTENT]
        )

        # send a patch clearing properties and verify that the service received that patch
        client.patch_twin_reported_properties(reset_reported_props)
        received_patch = service_helper.get_next_reported_patch_arrival()
        assert (
            received_patch[const.REPORTED][const.TEST_CONTENT]
            == reset_reported_props[const.TEST_CONTENT]
        )

        # get the twin and verify that the properties are no longer part of the twin
        twin = client.get_twin()
        assert const.TEST_CONTENT not in twin[const.REPORTED]

        leak_tracker.check_for_leaks()

    @pytest.mark.it("Raises NoConnectionError if there is no connection (Twin not yet enabled)")
    @pytest.mark.quicktest_suite
    def test_sync_no_connection_twin_not_enabled(self, client, random_reported_props, leak_tracker):
        leak_tracker.set_initial_object_list()

        client.disconnect()
        assert not client.connected

        with pytest.raises(NoConnectionError):
            client.patch_twin_reported_properties(random_reported_props)
        assert not client.connected

        leak_tracker.check_for_leaks()

    @pytest.mark.it(
        "Waits to complete until a connection is established if there is no connection (Twin already enabled)"
    )
    @pytest.mark.quicktest_suite
    def test_sync_no_connection_twin_enabled(
        self, client, service_helper, random_reported_props, executor, leak_tracker
    ):
        leak_tracker.set_initial_object_list()

        client._enable_feature("twin")

        client.disconnect()
        assert not client.connected

        # Attempt to patch
        patch_task = executor.submit(client.patch_twin_reported_properties, random_reported_props)
        time.sleep(1)
        # Still not done
        assert not patch_task.done()
        # Connect
        client.connect()
        time.sleep(0.5)
        # Task is now done
        assert patch_task.done()

        # wait for patch to arrive at service and verify
        received_patch = service_helper.get_next_reported_patch_arrival()
        assert (
            received_patch[const.REPORTED][const.TEST_CONTENT]
            == random_reported_props[const.TEST_CONTENT]
        )

        # get twin from the service and verify content
        twin = client.get_twin()
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
    def test_sync_network_failure_causes_disconnect(
        self, client, random_reported_props, failure_type, dropper, executor, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Disrupt network
        if failure_type == PACKET_DROP:
            dropper.drop_outgoing()
        elif failure_type == PACKET_REJECT:
            dropper.reject_outgoing()

        # Attempt to patch twin (implicitly enabling twin first)
        patch_task = executor.submit(client.patch_twin_reported_properties, random_reported_props)
        # Wait for client disconnect
        while client.connected:
            assert not patch_task.done()
            time.sleep(0.5)
        # Client has now disconnected
        assert patch_task.done()
        with pytest.raises(NoConnectionError):
            patch_task.result()

        # Restore and wait so any background operations can resolve before leak checking
        dropper.restore_all()
        time.sleep(1)
        del patch_task
        leak_tracker.check_for_leaks()

    @pytest.mark.it("Succeeds if network failure resolves before client can disconnect")
    def test_sync_network_failure_no_disconnect(
        self,
        client,
        random_reported_props,
        failure_type,
        service_helper,
        dropper,
        executor,
        leak_tracker,
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Disrupt network
        if failure_type == PACKET_DROP:
            dropper.drop_outgoing()
        elif failure_type == PACKET_REJECT:
            dropper.reject_outgoing()

        # Attempt to patch twin (implicitly enabling twin first)
        patch_task = executor.submit(client.patch_twin_reported_properties, random_reported_props)

        # Has not been able to succeed due to network failure, but client is still connected
        time.sleep(1)
        assert not patch_task.done()
        assert client.connected

        # Restore network, and operation succeeds
        dropper.restore_all()
        time.sleep(1)
        assert patch_task.done()

        # wait for patch to arrive at service and verify
        received_patch = service_helper.get_next_reported_patch_arrival()
        assert (
            received_patch[const.REPORTED][const.TEST_CONTENT]
            == random_reported_props[const.TEST_CONTENT]
        )

        # get twin from the service and verify content
        twin = client.get_twin()
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
    def test_sync_network_failure_causes_disconnect(
        self, client, random_reported_props, failure_type, dropper, executor, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Disrupt network
        if failure_type == PACKET_DROP:
            dropper.drop_outgoing()
        elif failure_type == PACKET_REJECT:
            dropper.reject_outgoing()

        # Attempt to patch twin (implicitly enabling twin first)
        patch_task = executor.submit(client.patch_twin_reported_properties, random_reported_props)
        # Wait for client disconnect
        while client.connected:
            assert not patch_task.done()
            time.sleep(0.5)
        # Client has now disconnected
        assert patch_task.done()
        with pytest.raises(NoConnectionError):
            patch_task.result()

        del patch_task
        leak_tracker.check_for_leaks()

    @pytest.mark.it("Succeeds if network failure resolves before client can disconnect")
    def test_sync_network_failure_no_disconnect(
        self,
        client,
        random_reported_props,
        failure_type,
        service_helper,
        dropper,
        executor,
        leak_tracker,
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Disrupt network
        if failure_type == PACKET_DROP:
            dropper.drop_outgoing()
        elif failure_type == PACKET_REJECT:
            dropper.reject_outgoing()

        # Attempt to patch twin (implicitly enabling twin first)
        patch_task = executor.submit(client.patch_twin_reported_properties, random_reported_props)

        # Has not been able to succeed due to network failure, but client is still connected
        time.sleep(1)
        assert not patch_task.done()
        assert client.connected

        # Restore network, and operation succeeds
        dropper.restore_all()
        time.sleep(1)
        assert patch_task.done()

        # wait for patch to arrive at service and verify
        received_patch = service_helper.get_next_reported_patch_arrival()
        assert (
            received_patch[const.REPORTED][const.TEST_CONTENT]
            == random_reported_props[const.TEST_CONTENT]
        )

        # get twin from the service and verify content
        twin = client.get_twin()
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
    def test_sync_network_failure_causes_disconnect(
        self,
        client,
        random_reported_props,
        failure_type,
        service_helper,
        dropper,
        executor,
        leak_tracker,
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Enable twins
        client._enable_feature("twin")

        # Disrupt network
        if failure_type == PACKET_DROP:
            dropper.drop_outgoing()
        elif failure_type == PACKET_REJECT:
            dropper.reject_outgoing()

        # Attempt to patch twin
        patch_task = executor.submit(client.patch_twin_reported_properties, random_reported_props)

        # Wait for client disconnect
        while client.connected:
            assert not patch_task.done()
            time.sleep(0.5)
        # Client has now disconnected and task will not finish until reconnection
        assert not patch_task.done()
        dropper.restore_all()
        # Wait for client reconnect
        while not client.connected:
            assert not patch_task.done()
            time.sleep(0.5)

        # Once connection is returned, the task will finish
        patch_task.result()

        # wait for patch to arrive at service and verify
        received_patch = service_helper.get_next_reported_patch_arrival()
        assert (
            received_patch[const.REPORTED][const.TEST_CONTENT]
            == random_reported_props[const.TEST_CONTENT]
        )

        # get twin from the service and verify content
        twin = client.get_twin()
        assert twin[const.REPORTED][const.TEST_CONTENT] == random_reported_props[const.TEST_CONTENT]

        leak_tracker.check_for_leaks()

    @pytest.mark.it("Succeeds if network failure resolves before client can disconnect")
    def test_sync_network_failure_no_disconnect(
        self,
        client,
        random_reported_props,
        failure_type,
        service_helper,
        dropper,
        executor,
        leak_tracker,
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Enable twins
        client._enable_feature("twin")

        # Disrupt network
        if failure_type == PACKET_DROP:
            dropper.drop_outgoing()
        elif failure_type == PACKET_REJECT:
            dropper.reject_outgoing()

        # Attempt to patch twin
        patch_task = executor.submit(client.patch_twin_reported_properties, random_reported_props)

        # Has not been able to succeed due to network failure, but client is still connected
        time.sleep(1)
        assert not patch_task.done()
        assert client.connected

        # Restore network, and operation succeeds
        dropper.restore_all()
        time.sleep(1)
        assert patch_task.done()

        # wait for patch to arrive at service and verify
        received_patch = service_helper.get_next_reported_patch_arrival()
        assert (
            received_patch[const.REPORTED][const.TEST_CONTENT]
            == random_reported_props[const.TEST_CONTENT]
        )

        # get twin from the service and verify content
        twin = client.get_twin()
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
    def test_sync_network_failure_causes_disconnect(
        self,
        client,
        random_reported_props,
        failure_type,
        service_helper,
        dropper,
        executor,
        leak_tracker,
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Enable twins
        client._enable_feature("twin")

        # Disrupt network
        if failure_type == PACKET_DROP:
            dropper.drop_outgoing()
        elif failure_type == PACKET_REJECT:
            dropper.reject_outgoing()

        # Attempt to patch twin
        patch_task = executor.submit(client.patch_twin_reported_properties, random_reported_props)

        # Wait for client disconnect
        while client.connected:
            assert not patch_task.done()
            time.sleep(0.5)
        # Client has now disconnected and task will not finish until reconnection
        assert not patch_task.done()
        time.sleep(1)
        assert not patch_task.done()
        dropper.restore_all()
        # Manually reconnect
        client.connect()

        # Once connection is returned, the task will finish
        patch_task.result()

        # wait for patch to arrive at service and verify
        received_patch = service_helper.get_next_reported_patch_arrival()
        assert (
            received_patch[const.REPORTED][const.TEST_CONTENT]
            == random_reported_props[const.TEST_CONTENT]
        )

        # get twin from the service and verify content
        twin = client.get_twin()
        assert twin[const.REPORTED][const.TEST_CONTENT] == random_reported_props[const.TEST_CONTENT]

        leak_tracker.check_for_leaks()

    @pytest.mark.it("Succeeds if network failure resolves before client can disconnect")
    def test_sync_network_failure_no_disconnect(
        self,
        client,
        random_reported_props,
        failure_type,
        service_helper,
        dropper,
        executor,
        leak_tracker,
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Enable twins
        client._enable_feature("twin")

        # Disrupt network
        if failure_type == PACKET_DROP:
            dropper.drop_outgoing()
        elif failure_type == PACKET_REJECT:
            dropper.reject_outgoing()

        # Attempt to patch twin
        patch_task = executor.submit(client.patch_twin_reported_properties, random_reported_props)

        # Has not been able to succeed due to network failure, but client is still connected
        time.sleep(1)
        assert not patch_task.done()
        assert client.connected

        # Restore network, and operation succeeds
        dropper.restore_all()
        time.sleep(1)
        assert patch_task.done()

        # wait for patch to arrive at service and verify
        received_patch = service_helper.get_next_reported_patch_arrival()
        assert (
            received_patch[const.REPORTED][const.TEST_CONTENT]
            == random_reported_props[const.TEST_CONTENT]
        )

        # get twin from the service and verify content
        twin = client.get_twin()
        assert twin[const.REPORTED][const.TEST_CONTENT] == random_reported_props[const.TEST_CONTENT]

        leak_tracker.check_for_leaks()


@pytest.mark.describe("Client Desired Properties")
class TestDesiredProperties(object):
    @pytest.mark.it("Receives a patch for a simple desired property")
    @pytest.mark.quicktest_suite
    def test_sync_receives_simple_desired_patch(self, client, service_helper, leak_tracker):
        received_patches = queue.Queue()
        leak_tracker.set_initial_object_list()

        def handle_on_patch_received(patch):
            nonlocal received_patches
            print("received {}".format(patch))
            received_patches.put(patch)

        client.on_twin_desired_properties_patch_received = handle_on_patch_received
        client.enable_twin_desired_properties_patch_receive()

        # erase all old desired properties. Otherwise our random dict will only
        # be part of the twin we get when we call `get_twin` below (because of
        # properties from previous tests).
        service_helper.set_desired_properties(
            {const.TEST_CONTENT: None},
        )

        random_dict = get_random_dict()
        service_helper.set_desired_properties(
            {const.TEST_CONTENT: random_dict},
        )

        while True:
            received_patch = received_patches.get(timeout=60)

            if received_patch[const.TEST_CONTENT] == random_dict:
                twin = client.get_twin()
                assert twin[const.DESIRED][const.TEST_CONTENT] == random_dict
                break

        leak_tracker.check_for_leaks()


# TODO: etag tests, version tests
