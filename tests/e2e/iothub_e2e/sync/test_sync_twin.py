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
    OperationTimeout,
    OperationCancelled,
    NoConnectionError,
)

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)
logging.basicConfig(level=logging.ERROR)

# TODO: tests with drop_incoming and reject_incoming

reset_reported_props = {const.TEST_CONTENT: None}


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

    @pytest.mark.it("Raises NoConnectionError if there is no connection")
    @pytest.mark.parametrize(
        "twin_enabled",
        [
            pytest.param(False, id="Twin not yet enabled"),
            pytest.param(True, id="Twin already enabled"),
        ],
    )
    @pytest.mark.quicktest_suite
    def test_sync_get_twin_fails_if_no_connection(
        self, client, flush_outgoing, twin_enabled, leak_tracker
    ):
        leak_tracker.set_initial_object_list()

        if twin_enabled:
            client._enable_feature("twin")

        client.disconnect()
        assert not client.connected

        with pytest.raises(NoConnectionError):
            client.get_twin()
        assert not client.connected

        flush_outgoing()
        leak_tracker.check_for_leaks()


@pytest.mark.describe(
    "Client Get Twin with dropped connection (Connection Retry enabled, Twin not yet enabled)"
)
@pytest.mark.dropped_connection
@pytest.mark.keep_alive(4)
# Because the timeout for a subscribe is 10 seconds, and a connection drop can take up to
# 2x keepalive, we need a keepalive < 5 in order to effectively test what happens if a
# connection drops and comes back
class TestGetTwinDroppedConnectionRetryEnabledTwinPatchNotEnabled(object):
    @pytest.mark.it(
        "Raises OperationTimeout if connection is not restored after dropping outgoing packets"
    )
    def test_sync_raises_op_timeout_if_drop_without_restore(
        self, client, flush_outgoing, dropper, executor, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Drop outgoing packets
        dropper.drop_outgoing()

        # Attempt to get a twin (implicitly enabling twin first)
        get_task = executor.submit(client.get_twin)
        # Wait for client disconnect
        while client.connected:
            time.sleep(0.5)
        # Getting the twin has not yet failed
        assert not get_task.done()

        # Failure due to timeout of subscribe (enable feature)
        with pytest.raises(OperationTimeout):
            get_task.result()

        dropper.restore_all()

        del get_task
        flush_outgoing()
        leak_tracker.check_for_leaks()

    @pytest.mark.it(
        "Raises OperationTimeout even if connection is restored after dropping outgoing packets"
    )
    def test_sync_raises_op_timeout_if_drop_and_restore(
        self, client, flush_outgoing, dropper, executor, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Drop outgoing packets
        dropper.drop_outgoing()

        # Attempt to get a twin (implicitly enabling twin first)
        get_task = executor.submit(client.get_twin)
        # Wait for client disconnect
        while client.connected:
            time.sleep(0.5)
        # Getting the twin has not yet failed
        assert not get_task.done()

        # Restore outgoing packet functionality and manually reconnect.
        # We need to manually reconnect to make sure the connection happens before any timeouts.
        dropper.restore_all()
        client.connect()
        # Getting the twin still has not yet failed
        assert not get_task.done()

        # Failure due to timeout of subscribe (enable feature)
        with pytest.raises(OperationTimeout):
            get_task.result()

        del get_task
        flush_outgoing()
        leak_tracker.check_for_leaks()

    @pytest.mark.it(
        "Raises OperationTimeout if connection is not restored after rejecting outgoing packets"
    )
    def test_sync_raises_op_timeout_if_reject_without_restore(
        self, client, flush_outgoing, dropper, executor, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Reject outgoing packets
        dropper.reject_outgoing()

        # Attempt to get the twin (implicitly enabling twin first)
        get_task = executor.submit(client.get_twin)
        # Wait for client disconnect
        while client.connected:
            time.sleep(0.5)
        # Getting the twin has not yet failed
        assert not get_task.done()

        # Failure due to failure of subscribe (enable feature)
        with pytest.raises(OperationTimeout):
            get_task.result()

        dropper.restore_all()

        del get_task
        flush_outgoing()
        leak_tracker.check_for_leaks()

    @pytest.mark.it(
        "Raises OperationTimeout even if connection is restored after rejecting outgoing packets"
    )
    def test_sync_raises_op_timeout_if_reject_and_restore(
        self, client, flush_outgoing, dropper, executor, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Reject outgoing packets
        dropper.reject_outgoing()

        # Attempt to get the twin (implicitly enabling twin first)
        get_task = executor.submit(client.get_twin)
        while client.connected:
            time.sleep(0.5)
        # Getting the twin has not yet failed
        assert not get_task.done()

        # Restore outgoing packet functionality and manually reconnect.
        # We need to manually reconnect to make sure the connection happens before any timeouts.
        dropper.restore_all()
        client.connect()
        # Getting the twin still has not yet failed
        assert not get_task.done()

        # Failure due to timeout of subscribe (enable feature)
        with pytest.raises(OperationTimeout):
            get_task.result()

        del get_task
        flush_outgoing()
        leak_tracker.check_for_leaks()


@pytest.mark.dropped_connection
@pytest.mark.describe(
    "Client Get Twin with dropped connection (Connection Retry disabled, Twin not yet enabled)"
)
@pytest.mark.keep_alive(4)
@pytest.mark.connection_retry(False)
# Because the timeout for a subscribe is 10 seconds, and a connection drop can take up to
# 2x keepalive, we need a keepalive < 5 in order to effectively test what happens if a
# connection drops
class TestGetTwinDroppedConnectionRetryDisabledTwinPatchNotEnabled(object):
    @pytest.mark.it("Raises OperationCancelled after dropping outgoing packets")
    def test_sync_raises_op_cancelled_if_drop(
        self, client, flush_outgoing, dropper, executor, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Drop outgoing packets
        dropper.drop_outgoing()

        # Attempt to get the twin (implicitly enabling twin first)
        get_task = executor.submit(client.get_twin)

        while client.connected:
            assert not get_task.done()
            time.sleep(0.5)
        # (Almost) Immediately upon connection drop, the task is cancelled
        time.sleep(0.1)
        assert get_task.done()
        with pytest.raises(OperationCancelled):
            get_task.result()

        dropper.restore_all()

        del get_task
        flush_outgoing()
        leak_tracker.check_for_leaks()

    @pytest.mark.it("Raises OperationCancelled after rejecting outgoing packets")
    def test_sync_raises_op_cancelled_if_reject(
        self, client, flush_outgoing, dropper, executor, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Drop outgoing packets
        dropper.reject_outgoing()

        # Attempt to get the twin (implicitly enabling twin first)
        get_task = executor.submit(client.get_twin)

        while client.connected:
            assert not get_task.done()
            time.sleep(0.5)
        # (Almost) Immediately upon connection drop, the task is cancelled
        time.sleep(0.1)
        assert get_task.done()
        with pytest.raises(OperationCancelled):
            get_task.result()

        dropper.restore_all()

        del get_task
        flush_outgoing()
        leak_tracker.check_for_leaks()


@pytest.mark.dropped_connection
@pytest.mark.describe(
    "Client Get Twin with dropped connection (Connection Retry enabled, Twin already enabled)"
)
@pytest.mark.keep_alive(4)
class TestGetTwinDroppedConnectionRetryEnabledTwinPatchAlreadyEnabled(object):
    @pytest.mark.it("Returns the twin once connection is restored after dropping outgoing packets")
    def test_sync_gets_twin_if_drop_and_restore(
        self, client, dropper, service_helper, executor, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Enable twins first, then drop outgoing packets
        client._enable_feature("twin")
        dropper.drop_outgoing()

        # Attempt to get the twin
        get_task = executor.submit(client.get_twin)
        # Wait for client to realize connection has dropped (due to keepalive)
        while client.connected:
            time.sleep(0.5)
        # Even though the connection has dropped, the get twin request has not returned
        assert not get_task.done()

        # Restore outgoing packet functionality and wait for client to reconnect
        dropper.restore_all()
        while not client.connected:
            time.sleep(0.5)
        # Wait for the request task to complete now that the client has reconnected
        twin1 = get_task.result()

        # Get the twin from the service to compare
        twin2 = service_helper.get_twin()
        # NOTE: It would be nice to compare the full properties, but the service client one
        # has metadata the client does not have. Look into this further to expand testing.
        assert twin1["desired"]["$version"] == twin2.properties.desired["$version"]
        assert twin1["reported"]["$version"] == twin2.properties.reported["$version"]

        leak_tracker.check_for_leaks()

    @pytest.mark.it("Returns the twin once connection is restored after rejecting outgoing packets")
    def test_sync_gets_twin_if_reject_and_restore(
        self, client, dropper, service_helper, executor, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Enable twins first, then reject packets
        client._enable_feature("twin")
        dropper.reject_outgoing()

        # Attempt to get the twin
        get_task = executor.submit(client.get_twin)
        # Wait for client to realize connection has dropped (due to keepalive)
        while client.connected:
            time.sleep(0.5)
        # Even though the connection has dropped, the get twin request has not returned
        assert not get_task.done()

        # Restore outgoing packet functionality and wait for client to reconnect
        dropper.restore_all()
        while not client.connected:
            time.sleep(0.5)
        # Wait for the request task to complete now that the client has reconnected
        twin1 = get_task.result()

        # Get the twin from the service to compare
        twin2 = service_helper.get_twin()
        # NOTE: It would be nice to compare the full properties, but the service client one
        # has metadata the client does not have. Look into this further to expand testing.
        assert twin1["desired"]["$version"] == twin2.properties.desired["$version"]
        assert twin1["reported"]["$version"] == twin2.properties.reported["$version"]

        leak_tracker.check_for_leaks()


@pytest.mark.dropped_connection
@pytest.mark.describe(
    "Client Get Twin with dropped connection (Connection Retry disabled, Twin already enabled)"
)
@pytest.mark.keep_alive(4)
@pytest.mark.connection_retry(False)
class TestGetTwinDroppedConnectionRetryDisabledTwinPatchAlreadyEnabled(object):
    @pytest.mark.it("Raises OperationCancelled after dropping outgoing packets")
    def test_sync_raises_op_cancelled_if_drop(
        self, client, flush_outgoing, dropper, executor, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Enable twins first, then drop outgoing packets
        client._enable_feature("twin")
        dropper.drop_outgoing()

        # Attempt to get the twin
        get_task = executor.submit(client.get_twin)

        while client.connected:
            assert not get_task.done()
            time.sleep(0.5)
        # (Almost) Immediately upon connection drop, the task is cancelled
        time.sleep(0.1)
        assert get_task.done()
        with pytest.raises(OperationCancelled):
            get_task.result()

        dropper.restore_all()

        del get_task
        flush_outgoing()
        leak_tracker.check_for_leaks()

    @pytest.mark.it("Raises OperationCancelled after rejecting outgoing packets")
    def test_sync_raises_op_cancelled_if_reject(
        self, client, flush_outgoing, dropper, executor, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Enable twins first, then reject outgoing packets
        client._enable_feature("twin")
        dropper.reject_outgoing()

        # Attempt to get the twin
        get_task = executor.submit(client.get_twin)

        while client.connected:
            assert not get_task.done()
            time.sleep(0.5)
        # (Almost) Immediately upon connection drop, the task is cancelled
        time.sleep(0.1)
        get_task.done()
        with pytest.raises(OperationCancelled):
            get_task.result()

        dropper.restore_all()

        del get_task
        flush_outgoing()
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
    def test_sync_bad_reported_patch_raises(
        self, client, flush_outgoing, twin_enabled, leak_tracker
    ):
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
        flush_outgoing()
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

    @pytest.mark.it("Raises NoConnectionError if there is no connection")
    @pytest.mark.parametrize(
        "twin_enabled",
        [
            pytest.param(False, id="Twin not yet enabled"),
            pytest.param(True, id="Twin already enabled"),
        ],
    )
    @pytest.mark.quicktest_suite
    def test_sync_patch_reported_fails_if_no_connection(
        self, client, flush_outgoing, twin_enabled, random_reported_props, leak_tracker
    ):
        leak_tracker.set_initial_object_list()

        if twin_enabled:
            client._enable_feature("twin")

        client.disconnect()
        assert not client.connected

        with pytest.raises(NoConnectionError):
            client.patch_twin_reported_properties(random_reported_props)
        assert not client.connected

        flush_outgoing()
        leak_tracker.check_for_leaks()


@pytest.mark.dropped_connection
@pytest.mark.describe(
    "Client Reported Properties with dropped connection (Connection Retry enabled, Twin not yet enabled)"
)
@pytest.mark.keep_alive(4)
# Because the timeout for a subscribe is 10 seconds, and a connection drop can take up to
# 2x keepalive, we need a keepalive < 5 in order to effectively test what happens if a
# connection drops and comes back
class TestReportedPropertiesDroppedConnectionWRetryEnabledTwinPatchNotEnabled(object):
    @pytest.mark.it(
        "Raises OperationTimeout if connection is not restored after dropping outgoing packets"
    )
    def test_sync_raises_op_timeout_if_drop_without_restore(
        self, client, flush_outgoing, random_reported_props, dropper, executor, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Drop outgoing packets
        dropper.drop_outgoing()

        # Attempt to send a twin patch (implicitly enabling twin first)
        send_task = executor.submit(client.patch_twin_reported_properties, random_reported_props)
        # Wait for client to disconnect
        while client.connected:
            time.sleep(0.5)
        # Sending twin patch has not yet failed
        assert not send_task.done()

        # Failure due to timeout of subscribe (enable feature)
        with pytest.raises(OperationTimeout):
            send_task.result()

        dropper.restore_all()

        del send_task
        flush_outgoing()
        leak_tracker.check_for_leaks()

    @pytest.mark.it(
        "Raises OperationTimeout even if connection is restored after dropping outgoing packets"
    )
    def test_sync_raises_op_timeout_if_drop_and_restore(
        self, client, flush_outgoing, random_reported_props, dropper, executor, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Drop outgoing packets
        dropper.drop_outgoing()

        # Attempt to send a twin patch (implicitly enabling twin first)
        send_task = executor.submit(client.patch_twin_reported_properties, random_reported_props)
        # Wait for client to disconnect
        while client.connected:
            time.sleep(0.5)
        # Sending twin patch has not yet failed
        assert not send_task.done()

        # Restore outgoing packet functionality and manually reconnect.
        # We need to manually reconnect to make sure the connection happens before any timeouts.
        dropper.restore_all()
        client.connect()
        # Sending twin patch still has not yet failed
        assert not send_task.done()

        # Failure due to timeout of subscribe (enable feature)
        with pytest.raises(OperationTimeout):
            send_task.result()

        del send_task
        flush_outgoing()
        leak_tracker.check_for_leaks()

    @pytest.mark.it(
        "Raises OperationTimeout if connection is not restored after rejecting outgoing packets"
    )
    def test_sync_raises_op_timeout_if_reject_without_restore(
        self, client, flush_outgoing, random_reported_props, dropper, executor, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Reject outgoing packets
        dropper.reject_outgoing()

        # Attempt to send a twin patch (implicitly enabling twin first)
        send_task = executor.submit(client.patch_twin_reported_properties, random_reported_props)
        # Wait for client to disconnect
        while client.connected:
            time.sleep(0.5)
        # Sending twin patch has not yet failed
        assert not send_task.done()

        # Failure due to failure of subscribe (enable feature)
        with pytest.raises(OperationTimeout):
            send_task.result()

        dropper.restore_all()

        del send_task
        flush_outgoing()
        leak_tracker.check_for_leaks()

    @pytest.mark.it(
        "Raises OperationTimeout even if connection is restored after rejecting outgoing packets"
    )
    def test_sync_raises_op_timeout_if_reject_and_restore(
        self, client, flush_outgoing, random_reported_props, dropper, executor, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Reject outgoing packets
        dropper.reject_outgoing()

        # Attempt to send a twin patch (implicitly enabling twin first)
        send_task = executor.submit(client.patch_twin_reported_properties, random_reported_props)
        # Wait for the client to disconnect
        while client.connected:
            time.sleep(0.5)
        # Sending twin patch has not yet failed
        assert not send_task.done()

        # Restore outgoing packet functionality and manually reconnect.
        # We need to manually reconnect to make sure the connection happens before any timeouts.
        dropper.restore_all()
        client.connect()
        # Sending twin patch still has not yet failed
        assert not send_task.done()

        # Failure due to timeout of subscribe (enable feature)
        with pytest.raises(OperationTimeout):
            send_task.result()

        del send_task
        flush_outgoing()
        leak_tracker.check_for_leaks()


@pytest.mark.dropped_connection
@pytest.mark.describe(
    "Client Reported Properties with dropped connection (Connection Retry disabled, Twin not yet enabled)"
)
@pytest.mark.keep_alive(4)
@pytest.mark.connection_retry(False)
# Because the timeout for a subscribe is 10 seconds, and a connection drop can take up to
# 2x keepalive, we need a keepalive < 5 in order to effectively test what happens if a
# connection drops
class TestReportedPropertiesDroppedConnectionRetryDisabledTwinPatchNotEnabled(object):
    @pytest.mark.it("Raises OperationCancelled after dropping outgoing packets")
    def test_sync_raises_op_cancelled_if_drop(
        self, client, flush_outgoing, random_reported_props, dropper, executor, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Drop outgoing packets
        dropper.drop_outgoing()

        # Attempt to send a twin patch (implicitly enabling twin first)
        send_task = executor.submit(client.patch_twin_reported_properties, random_reported_props)

        while client.connected:
            assert not send_task.done()
            time.sleep(0.5)
        # (Almost) Immediately upon connection drop, the task is cancelled
        time.sleep(0.1)
        assert send_task.done()
        with pytest.raises(OperationCancelled):
            send_task.result()

        dropper.restore_all()

        del send_task
        flush_outgoing()
        leak_tracker.check_for_leaks()

    @pytest.mark.it("Raises OperationCancelled after rejecting outgoing packets")
    def test_sync_raises_op_cancelled_if_reject(
        self, client, flush_outgoing, random_reported_props, dropper, executor, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Drop outgoing packets
        dropper.reject_outgoing()

        # Attempt to send a twin patch (implicitly enabling twin first)
        send_task = executor.submit(client.patch_twin_reported_properties, random_reported_props)

        while client.connected:
            assert not send_task.done()
            time.sleep(0.5)
        # (Almost) Immediately upon connection drop, the task is cancelled
        time.sleep(0.1)
        assert send_task.done()
        with pytest.raises(OperationCancelled):
            send_task.result()

        dropper.restore_all()

        del send_task
        flush_outgoing()
        leak_tracker.check_for_leaks()


@pytest.mark.dropped_connection
@pytest.mark.describe(
    "Client Reported Properties with dropped connection (Connection Retry enabled, Twin already enabled)"
)
@pytest.mark.keep_alive(4)
class TestReportedPropertiesDroppedConnectionRetryEnabledTwinPatchAlreadyEnabled(object):
    @pytest.mark.it(
        "Updates reported properties once connection is restored after dropping outgoing packets"
    )
    def test_sync_updates_reported_if_drop_and_restore(
        self, client, random_reported_props, dropper, service_helper, executor, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Enable twins first, then drop outgoing packets
        client._enable_feature("twin")
        dropper.drop_outgoing()

        # Attempt to send a twin patch
        send_task = executor.submit(client.patch_twin_reported_properties, random_reported_props)
        # Wait for client to realize connection has dropped (due to keepalive)
        while client.connected:
            time.sleep(0.5)
        # Even though the connection has dropped, the twin patch send has not returned
        assert not send_task.done()

        # Restore outgoing packet functionality and wait for client to reconnect
        dropper.restore_all()
        while not client.connected:
            time.sleep(0.5)
        # Wait for the send task to complete now that the client has reconnected
        send_task.result()

        # Ensure the sent patch was received by the service
        received_patch = service_helper.get_next_reported_patch_arrival()
        assert (
            received_patch[const.REPORTED][const.TEST_CONTENT]
            == random_reported_props[const.TEST_CONTENT]
        )

        leak_tracker.check_for_leaks()

    @pytest.mark.it(
        "Updates reported properties once connection is restored after rejecting outgoing packets"
    )
    def test_sync_updates_reported_if_reject_and_restore(
        self, client, random_reported_props, dropper, service_helper, executor, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Enable twins first, then reject packets
        client._enable_feature("twin")
        dropper.reject_outgoing()

        # Attempt to send a twin patch
        send_task = executor.submit(client.patch_twin_reported_properties, random_reported_props)
        # Wait for client to realize connection has dropped (due to keepalive)
        while client.connected:
            time.sleep(0.5)
        # Even though the connection has dropped, the twin patch send has not returned
        assert not send_task.done()

        # Restore outgoing packet functionality and wait for client to reconnect
        dropper.restore_all()
        while not client.connected:
            time.sleep(0.5)
        # Wait for the send task to complete now that the client has reconnected
        send_task.result()

        # Ensure the sent patch was received by the service
        received_patch = service_helper.get_next_reported_patch_arrival()
        assert (
            received_patch[const.REPORTED][const.TEST_CONTENT]
            == random_reported_props[const.TEST_CONTENT]
        )

        leak_tracker.check_for_leaks()


@pytest.mark.dropped_connection
@pytest.mark.describe(
    "Client Reported Properties with dropped connection (Connection Retry disabled, Twin already enabled)"
)
@pytest.mark.keep_alive(4)
@pytest.mark.connection_retry(False)
# Because the timeout for a subscribe is 10 seconds, and a connection drop can take up to
# 2x keepalive, we need a keepalive < 5 in order to effectively test what happens if a
# connection drops
class TestReportedPropertiesDroppedConnectionRetryDisabledTwinPatchAlreadyEnabled(object):
    @pytest.mark.it("Raises OperationCancelled after dropping outgoing packets")
    def test_sync_raises_op_cancelled_if_drop(
        self, client, flush_outgoing, random_reported_props, dropper, executor, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Enable twins first, then drop outgoing packets
        client._enable_feature("twin")
        dropper.drop_outgoing()

        # Attempt to send a twin patch
        send_task = executor.submit(client.patch_twin_reported_properties, random_reported_props)

        while client.connected:
            assert not send_task.done()
            time.sleep(0.5)
        # (Almost) Immediately upon connection drop, the task is cancelled
        time.sleep(0.1)
        assert send_task.done()
        with pytest.raises(OperationCancelled):
            send_task.result()

        dropper.restore_all()

        del send_task
        flush_outgoing()
        leak_tracker.check_for_leaks()

    @pytest.mark.it("Raises OperationCancelled after rejecting outgoing packets")
    def test_sync_raises_op_cancelled_if_reject(
        self, client, flush_outgoing, random_reported_props, dropper, executor, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Enable twins first, then reject outgoing packets
        client._enable_feature("twin")
        dropper.reject_outgoing()

        # Attempt to send a twin patch
        send_task = executor.submit(client.patch_twin_reported_properties, random_reported_props)

        while client.connected:
            assert not send_task.done()
            time.sleep(0.5)
        # (Almost) Immediately upon connection drop, the task is cancelled
        time.sleep(0.1)
        assert send_task.done()
        with pytest.raises(OperationCancelled):
            send_task.result()

        dropper.restore_all()

        del send_task
        flush_outgoing()
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
