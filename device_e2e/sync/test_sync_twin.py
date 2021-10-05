# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import pytest
import logging
import time
import threading
import const
from utils import get_random_dict

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)


# TODO: tests with drop_incoming and reject_incoming

reset_reported_props = {const.TEST_CONTENT: None}


@pytest.mark.describe("Device Client Reported Properties")
class TestReportedProperties(object):
    @pytest.mark.it("Can set a simple reported property")
    def test_simple_patch(self, client, reported_props, get_next_reported_patch_arrival):

        # patch properties
        client.patch_twin_reported_properties(reported_props)

        # wait for patch to arrive at service and verify
        received_patch = get_next_reported_patch_arrival()
        assert (
            received_patch[const.REPORTED][const.TEST_CONTENT] == reported_props[const.TEST_CONTENT]
        )

        # get twin from the service and verify content
        twin = client.get_twin()
        assert twin[const.REPORTED][const.TEST_CONTENT] == reported_props[const.TEST_CONTENT]

    @pytest.mark.it("Can clear a reported property")
    def test_clear_property(self, client, reported_props, get_next_reported_patch_arrival):

        # patch properties and verify that the service received the patch
        client.patch_twin_reported_properties(reported_props)
        received_patch = get_next_reported_patch_arrival()
        assert (
            received_patch[const.REPORTED][const.TEST_CONTENT] == reported_props[const.TEST_CONTENT]
        )

        # send a patch clearing properties and verify that the service received that patch
        client.patch_twin_reported_properties(reset_reported_props)
        received_patch = get_next_reported_patch_arrival()
        assert (
            received_patch[const.REPORTED][const.TEST_CONTENT]
            == reset_reported_props[const.TEST_CONTENT]
        )

        # get the twin and verify that the properties are no longer part of the twin
        twin = client.get_twin()
        assert const.TEST_CONTENT not in twin[const.REPORTED]

    @pytest.mark.it("Connects the transport if necessary")
    def test_connect_if_necessary(self, client, reported_props, get_next_reported_patch_arrival):

        client.disconnect()

        assert not client.connected
        client.patch_twin_reported_properties(reported_props)
        assert client.connected

        received_patch = get_next_reported_patch_arrival()
        assert (
            received_patch[const.REPORTED][const.TEST_CONTENT] == reported_props[const.TEST_CONTENT]
        )

        twin = client.get_twin()
        assert twin[const.REPORTED][const.TEST_CONTENT] == reported_props[const.TEST_CONTENT]


@pytest.mark.dropped_connection
@pytest.mark.describe("Device Client Reported Properties with dropped connection")
class TestReportedPropertiesDroppedConnection(object):
    @pytest.fixture(scope="class")
    def client_kwargs(self):
        return {"keep_alive": 5}

    # TODO: split drop tests between first and second patches

    @pytest.mark.it("Sends if connection drops before sending")
    def test_sends_if_drop_before_sending(
        self, client, reported_props, dropper, get_next_reported_patch_arrival, executor
    ):

        assert client.connected
        dropper.drop_outgoing()

        send_task = executor.submit(client.patch_twin_reported_properties, reported_props)
        while client.connected:
            time.sleep(1)

        assert not send_task.done()

        dropper.restore_all()
        while not client.connected:
            time.sleep(1)

        send_task.result()

        received_patch = get_next_reported_patch_arrival()
        assert (
            received_patch[const.REPORTED][const.TEST_CONTENT] == reported_props[const.TEST_CONTENT]
        )

    @pytest.mark.it("Sends if connection rejects send")
    def test_sends_if_reject_before_sending(
        self, client, reported_props, dropper, get_next_reported_patch_arrival, executor
    ):

        assert client.connected
        dropper.reject_outgoing()

        send_task = executor.submit(client.patch_twin_reported_properties, reported_props)
        while client.connected:
            time.sleep(1)

        assert not send_task.done()

        dropper.restore_all()
        while not client.connected:
            time.sleep(1)

        send_task.result()

        received_patch = get_next_reported_patch_arrival()
        assert (
            received_patch[const.REPORTED][const.TEST_CONTENT] == reported_props[const.TEST_CONTENT]
        )


@pytest.mark.describe("Device Client Desired Properties")
class TestDesiredProperties(object):
    @pytest.mark.it("Receives a patch for a simple desired property")
    def test_simple_patch(self, client, service_helper, device_id, module_id):

        received = threading.Event()

        # hack needed because there is no `nonlocal` keyword in py27.
        nonlocal_py27_hack = {"received_patch": None, "received": received}

        def handle_on_patch_received(patch):
            print("received {}".format(patch))
            nonlocal_py27_hack["received_patch"] = patch
            nonlocal_py27_hack["received"].set()

        client.on_twin_desired_properties_patch_received = handle_on_patch_received

        random_dict = get_random_dict()
        service_helper.set_desired_properties(
            device_id,
            module_id,
            {const.TEST_CONTENT: random_dict},
        )

        received.wait(timeout=10)
        logger.info("got it")

        assert nonlocal_py27_hack["received_patch"][const.TEST_CONTENT] == random_dict

        twin = client.get_twin()
        assert twin[const.DESIRED][const.TEST_CONTENT] == random_dict


# TODO: etag tests, version tests
