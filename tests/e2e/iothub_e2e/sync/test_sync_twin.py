# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import pytest
import logging
import time
import const
import queue
from dev_utils import get_random_dict
from azure.iot.device.exceptions import ClientError

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)


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

    @pytest.mark.it("Connects the transport if necessary")
    @pytest.mark.quicktest_suite
    def test_sync_patch_reported_connect_if_necessary(
        self, client, random_reported_props, service_helper, leak_tracker
    ):
        leak_tracker.set_initial_object_list()

        client.disconnect()

        assert not client.connected
        client.patch_twin_reported_properties(random_reported_props)
        assert client.connected

        received_patch = service_helper.get_next_reported_patch_arrival()
        assert (
            received_patch[const.REPORTED][const.TEST_CONTENT]
            == random_reported_props[const.TEST_CONTENT]
        )

        twin = client.get_twin()
        assert twin[const.REPORTED][const.TEST_CONTENT] == random_reported_props[const.TEST_CONTENT]

        leak_tracker.check_for_leaks()


@pytest.mark.dropped_connection
@pytest.mark.describe("Client Reported Properties with dropped connection")
@pytest.mark.keep_alive(5)
class TestReportedPropertiesDroppedConnection(object):

    # TODO: split drop tests between first and second patches

    @pytest.mark.it("Updates reported properties if connection drops before sending")
    def test_sync_updates_reported_if_drop_before_sending(
        self, client, random_reported_props, dropper, service_helper, executor, leak_tracker
    ):
        leak_tracker.set_initial_object_list()

        assert client.connected
        dropper.drop_outgoing()

        send_task = executor.submit(client.patch_twin_reported_properties, random_reported_props)
        while client.connected:
            time.sleep(1)

        assert not send_task.done()

        dropper.restore_all()
        while not client.connected:
            time.sleep(1)

        send_task.result()

        received_patch = service_helper.get_next_reported_patch_arrival()
        assert (
            received_patch[const.REPORTED][const.TEST_CONTENT]
            == random_reported_props[const.TEST_CONTENT]
        )

        # TODO: investigate leak
        # leak_tracker.check_for_leaks()

    @pytest.mark.it("Updates reported properties if connection rejects send")
    def test_sync_updates_reported_if_reject_before_sending(
        self, client, random_reported_props, dropper, service_helper, executor, leak_tracker
    ):
        leak_tracker.set_initial_object_list()

        assert client.connected
        dropper.reject_outgoing()

        send_task = executor.submit(client.patch_twin_reported_properties, random_reported_props)
        while client.connected:
            time.sleep(1)

        assert not send_task.done()

        dropper.restore_all()
        while not client.connected:
            time.sleep(1)

        send_task.result()

        received_patch = service_helper.get_next_reported_patch_arrival()
        assert (
            received_patch[const.REPORTED][const.TEST_CONTENT]
            == random_reported_props[const.TEST_CONTENT]
        )

        # TODO: investigate leak
        # leak_tracker.check_for_leaks()


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
