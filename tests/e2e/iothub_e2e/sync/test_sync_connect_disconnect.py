# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import pytest
import logging
import time
import threading
import parametrize

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)


@pytest.mark.describe("Client object")
class TestConnectDisconnect(object):
    @pytest.mark.it("Can disconnect and reconnect")
    @pytest.mark.parametrize(*parametrize.connection_retry_disabled_and_enabled)
    @pytest.mark.parametrize(*parametrize.auto_connect_disabled_and_enabled)
    @pytest.mark.quicktest_suite
    def test_sync_connect_disconnect(self, brand_new_client, leak_tracker):
        leak_tracker.set_initial_object_list()

        client = brand_new_client

        client.connect()
        assert client.connected

        client.disconnect()
        assert not client.connected

        client.connect()
        assert client.connected

        leak_tracker.check_for_leaks()

    @pytest.mark.it(
        "Can do a manual connect in the `on_connection_state_change` call that is notifying the user about a disconnect."
    )
    @pytest.mark.parametrize(*parametrize.connection_retry_disabled_and_enabled)
    @pytest.mark.parametrize(*parametrize.auto_connect_disabled_and_enabled)
    # see "This assert fails because of initial and secondary disconnects" below
    @pytest.mark.skip(reason="two stage disconnect causes assertion in test code")
    def test_sync_connect_in_the_middle_of_disconnect(
        self, brand_new_client, service_helper, random_message, leak_tracker
    ):
        """
        Explanation: People will call `connect` inside `on_connection_state_change` handlers.
        We have to make sure that we can handle this without getting stuck in a bad state.
        """
        leak_tracker.set_initial_object_list()

        client = brand_new_client
        assert client

        reconnected_event = threading.Event()

        def handle_on_connection_state_change():
            nonlocal reconnected_event

            if client.connected:
                logger.info("handle_on_connection_state_change connected.  nothing to do")
            else:
                logger.info("handle_on_connection_state_change disconnected.  reconnecting.")
                client.connect()
                assert client.connected
                reconnected_event.set()
                logger.info("reconnect event set")

        client.on_connection_state_change = handle_on_connection_state_change

        # connect
        client.connect()
        assert client.connected

        # disconnect.
        reconnected_event.clear()
        logger.info("Calling client.disconnect.")
        client.disconnect()

        # wait for handle_on_connection_state_change to reconnect
        logger.info("waiting for reconnect_event to be set.")
        reconnected_event.wait()

        logger.info(
            "reconnect_event.wait() returned.  client.connected={}".format(client.connected)
        )
        # This assert fails because of initial and secondary disconnects
        assert client.connected

        # sleep a while and make sure that we're still connected.
        time.sleep(3)
        assert client.connected

        # finally, send a message to makes reu we're _really_ connected
        client.send_message(random_message)
        event = service_helper.wait_for_eventhub_arrival(random_message.message_id)
        assert event

        leak_tracker.check_for_leaks()

    @pytest.mark.it(
        "Can do a manual disconnect in the `on_connection_state_change` call that is notifying the user about a connect."
    )
    @pytest.mark.parametrize(*parametrize.connection_retry_disabled_and_enabled)
    @pytest.mark.parametrize(*parametrize.auto_connect_disabled_and_enabled)
    @pytest.mark.parametrize(
        "first_connect",
        [pytest.param(True, id="First connection"), pytest.param(False, id="Second connection")],
    )
    def test_sync_disconnect_in_the_middle_of_connect(
        self, brand_new_client, service_helper, random_message, first_connect, leak_tracker
    ):
        """
        Explanation: This is the inverse of `test_connect_in_the_middle_of_disconnect`.  This is
        less likely to be a user scenario, but it lets us test with unusual-but-specific timing
        on the call to `disconnect`.
        """
        leak_tracker.set_initial_object_list()

        client = brand_new_client
        assert client
        disconnect_on_next_connect_event = False

        disconnected_event = threading.Event()

        def handle_on_connection_state_change():
            nonlocal disconnected_event

            if client.connected:
                if disconnect_on_next_connect_event:
                    logger.info("connected.  disconnecting now")
                    client.disconnect()
                    disconnected_event.set()
                else:
                    logger.info("connected, but nothing to do")
            else:
                logger.info("disconnected.  nothing to do")

        client.on_connection_state_change = handle_on_connection_state_change

        if not first_connect:
            # connect
            client.connect()
            assert client.connected

            # disconnect.
            client.disconnect()

        assert not client.connected

        # now, connect (maybe for the second time), and disconnect inside the on_connected handler
        disconnect_on_next_connect_event = True
        disconnected_event.clear()
        client.connect()

        # and wait for us to disconnect
        disconnected_event.wait()
        assert not client.connected

        # sleep a while and make sure that we're still disconnected.
        time.sleep(3)
        assert not client.connected

        # finally, connect and make sure we can send a message
        disconnect_on_next_connect_event = False
        client.connect()
        assert client.connected

        client.send_message(random_message)
        event = service_helper.wait_for_eventhub_arrival(random_message.message_id)
        assert event

        leak_tracker.check_for_leaks()


@pytest.mark.dropped_connection
@pytest.mark.describe("Client object with dropped connection")
@pytest.mark.keep_alive(5)
class TestConnectDisconnectDroppedConnection(object):
    @pytest.mark.it("disconnects when network drops all outgoing packets")
    def test_sync_disconnect_on_drop_outgoing(self, client, dropper, leak_tracker):
        """
        This test verifies that the client will disconnect (eventually) if the network starts
        dropping packets
        """
        leak_tracker.set_initial_object_list()

        client.connect()
        assert client.connected
        dropper.drop_outgoing()

        while client.connected:
            time.sleep(1)

        # we've passed the test. Now wait to reconnect before we check for leaks. Otherwise we
        # have a pending ConnectOperation floating around and this would get tagged as a leak.
        dropper.restore_all()
        while not client.connected:
            time.sleep(1)

        leak_tracker.check_for_leaks()

    @pytest.mark.it("disconnects when network rejects all outgoing packets")
    def test_sync_disconnect_on_reject_outgoing(self, client, dropper, leak_tracker):
        """
        This test verifies that the client will disconnect (eventually) if the network starts
        rejecting packets
        """
        leak_tracker.set_initial_object_list()

        client.connect()
        assert client.connected
        dropper.reject_outgoing()

        while client.connected:
            time.sleep(1)

        # we've passed the test. Now wait to reconnect before we check for leaks. Otherwise we
        # have a pending ConnectOperation floating around and this would get tagged as a leak.
        dropper.restore_all()
        while not client.connected:
            time.sleep(1)

        leak_tracker.check_for_leaks()
