# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import asyncio
import pytest
import logging

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)


@pytest.mark.describe("Session object")
class TestConnectDisconnect(object):
    @pytest.mark.it("Can connect and disconnect")
    @pytest.mark.quicktest_suite
    async def test_connect_disconnect(self, session, leak_tracker):
        leak_tracker.set_initial_object_list()

        assert session.connected is False
        async with session:
            assert session.connected is True
        assert session.connected is False


@pytest.mark.dropped_connection
@pytest.mark.describe("Client with dropped connection")
@pytest.mark.keep_alive(5)
class TestConnectDisconnectDroppedConnection(object):
    @pytest.mark.skip("dropped connection doesn't break out of context manager")
    @pytest.mark.it("disconnects when network drops all outgoing packets")
    async def test_disconnect_on_drop_outgoing(self, dropper, session, leak_tracker):
        """
        This test verifies that the client will disconnect (eventually) if the network starts
        dropping packets
        """
        leak_tracker.set_initial_object_list()

        # with pytest.raises(foo)
        async with session:
            assert session.connected is True
            dropper.drop_outgoing()
            await asyncio.sleep(30)
        assert session.disconnected is False

        leak_tracker.check_for_leaks()

    @pytest.mark.skip("dropped connection doesn't break out of context manager")
    @pytest.mark.it("disconnects when network rejects all outgoing packets")
    @pytest.mark.keep_alive(5)
    async def test_disconnect_on_reject_outgoing(self, dropper, session, leak_tracker):
        """
        This test verifies that the client will disconnect (eventually) if the network starts
        rejecting packets
        """
        leak_tracker.set_initial_object_list()

        # with pytest.raises(foo)
        async with session:
            assert session.connected is True
            dropper.reject_outgoing()
            await asyncio.sleep(30)
        assert session.disconnected is False

        leak_tracker.check_for_leaks()
