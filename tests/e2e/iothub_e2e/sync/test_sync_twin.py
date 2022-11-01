# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import pytest
import logging
import time
import const
import queue
from dev_utils import get_random_dict
from azure.iot.device.exceptions import ClientError, OperationTimeout

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)
logging.basicConfig(level=logging.ERROR)

# TODO: tests with drop_incoming and reject_incoming

reset_reported_props = {const.TEST_CONTENT: None}


@pytest.mark.describe("Client Reported Properties")
class TestReportedProperties(object):
    @pytest.mark.it("Can set a simple reported property")
    @pytest.mark.quicktest_suite
    def test_sync_sends_simple_reported_patch(
        self, client, random_reported_props, service_helper, leak_tracker
    ):
        leak_tracker.set_initial_object_list()

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

    @pytest.mark.it("Raises correct exception for un-serializable patch")
    def test_sync_bad_reported_patch_raises(self, client, leak_tracker):
        leak_tracker.set_initial_object_list()

        # There's no way to serialize a function.
        def thing_that_cant_serialize():
            pass

        with pytest.raises(ClientError) as e_info:
            client.patch_twin_reported_properties(thing_that_cant_serialize)
        assert isinstance(e_info.value.__cause__, TypeError)

    @pytest.mark.it("Can clear a reported property")
    @pytest.mark.quicktest_suite
    def test_sync_clear_property(self, client, random_reported_props, service_helper, leak_tracker):
        leak_tracker.set_initial_object_list()

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

    @pytest.mark.it("Fails if there is no connection")
    @pytest.mark.quicktest_suite
    def test_sync_patch_reported_fails_if_no_connection(
        self, client, random_reported_props, leak_tracker
    ):
        leak_tracker.set_initial_object_list()

        client.disconnect()
        assert not client.connected

        with pytest.raises(NoConnectionError):
            client.patch_twin_reported_properties(random_reported_props)
        assert not client.connected

        leak_tracker.check_for_leaks()


@pytest.mark.dropped_connection
@pytest.mark.describe(
    "Client Reported Properties with dropped connection (Twin patches not yet enabled)"
)
@pytest.mark.keep_alive(4)
# Because the timeout for a subscribe is 10 seconds, and a connection drop can take up to
# 2x keepalive, we need a keepalive < 5 in order to effectively test what happens if a
# connection drops and comes back
class TestReportedPropertiesDroppedConnectionTwinPatchNotEnabled(object):
    @pytest.mark.it(
        "Raises OperationTimeout if connection is not restored after dropping outgoing packets"
    )
    def test_sync_raises_op_timeout_if_drop_without_restore(
        self, client, random_reported_props, dropper, executor, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Drop outgoing packets
        dropper.drop_outgoing()

        # Attempt to send a twin patch (implicitly enabling twin patches first)
        send_task = executor.submit(client.patch_twin_reported_properties, random_reported_props)

        # Failure due to timeout of subscribe (enable feature)
        with pytest.raises(OperationTimeout):
            send_task.result()

        dropper.restore_all()

        # TODO: investigate leak
        # leak_tracker.check_for_leaks()

    @pytest.mark.it(
        "Raises OperationTimeout even if connection is restored after dropping outgoing packets"
    )
    def test_sync_raises_op_timeout_if_drop_and_restore(
        self, client, random_reported_props, dropper, executor, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Drop outgoing packets
        dropper.drop_outgoing()

        # Attempt to send a twin patch (implicitly enabling twin patches first)
        send_task = executor.submit(client.patch_twin_reported_properties, random_reported_props)
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

        # TODO: investigate leak
        # leak_tracker.check_for_leaks()

    @pytest.mark.it(
        "Raises OperationTimeout if connection is not restored after rejecting outgoing packets"
    )
    def test_sync_raises_op_timeout_if_reject_without_restore(
        self, client, random_reported_props, dropper, executor, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Reject outgoing packets
        dropper.reject_outgoing()

        # Attempt to send a twin patch (implicitly enabling twin patches first)
        send_task = executor.submit(client.patch_twin_reported_properties, random_reported_props)

        # Failure due to failure of subscribe (enable feature)
        with pytest.raises(OperationTimeout):
            send_task.result()

        dropper.restore_all()

        # TODO: investigate leak
        # leak_tracker.check_for_leaks()

    @pytest.mark.it(
        "Raises OperationTimeout even if connection is restored after rejecting outgoing packets"
    )
    def test_sync_raises_op_timeout_if_reject_and_restore(
        self, client, random_reported_props, dropper, executor, leak_tracker
    ):
        leak_tracker.set_initial_object_list()
        assert client.connected

        # Reject outgoing packets
        dropper.reject_outgoing()

        # Attempt to send a twin patch (implicitly enabling twin patches first)
        send_task = executor.submit(client.patch_twin_reported_properties, random_reported_props)
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

        # TODO: investigate leak
        # leak_tracker.check_for_leaks()


@pytest.mark.dropped_connection
@pytest.mark.describe(
    "Client Reported Properties with dropped connection (Twin patches already enabled)"
)
@pytest.mark.keep_alive(4)
class TestReportedPropertiesDroppedConnectionTwinPatchAlreadyEnabled(object):
    @pytest.mark.it(
        "Updates reported properties once connection is restored after dropping outgoing packets"
    )
    def test_sync_updates_reported_if_drop_before_sending(
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
    def test_sync_updates_reported_if_reject_before_sending(
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
