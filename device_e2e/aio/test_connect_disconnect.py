# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import asyncio
import pytest
import logging
import test_config

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)

pytestmark = pytest.mark.asyncio


@pytest.mark.describe("Client object")
class TestConnectDisconnect(object):
    @pytest.mark.it("Can disconnect and reconnect")
    @pytest.mark.parametrize(*test_config.connection_retry_disabled_and_enabled)
    @pytest.mark.parametrize(*test_config.auto_connect_off_and_on)
    @pytest.mark.quicktest_suite
    async def test_connect_disconnect(self, brand_new_client):
        client = brand_new_client

        assert client
        logger.info("connecting")
        await client.connect()
        assert client.connected

        await client.disconnect()
        assert not client.connected

        await client.connect()
        assert client.connected

    @pytest.mark.it("calls `on_connection_state_change` when setting the handler (connected case)")
    @pytest.mark.quicktest_suite
    async def test_on_connection_state_change_gets_called_with_current_state_connected(
        self, brand_new_client, event_loop
    ):
        client = brand_new_client

        handler_called = asyncio.Event()

        async def handle_on_connection_state_change():
            nonlocal handler_called
            if client.connected:
                event_loop.call_soon_threadsafe(handler_called.set)

        await client.connect()
        assert client.connected
        client.on_connection_state_change = handle_on_connection_state_change
        await handler_called.wait()

    @pytest.mark.parametrize(
        "previously_connected",
        [
            pytest.param(True, id="previously connected"),
            pytest.param(
                False,
                id="not previously connected",
                marks=pytest.mark.skip(reason="inconssitent behavior"),
            ),
        ],
    )
    @pytest.mark.it(
        "calls `on_connection_state_change` when setting the handler (disconnected case)"
    )
    @pytest.mark.quicktest_suite
    async def test_on_connection_state_change_gets_called_with_current_state_disconnected(
        self, brand_new_client, event_loop, previously_connected
    ):
        client = brand_new_client

        handler_called = asyncio.Event()

        async def handle_on_connection_state_change():
            nonlocal handler_called
            if not client.connected:
                event_loop.call_soon_threadsafe(handler_called.set)

        if previously_connected:
            await client.connect()
            await client.disconnect()
            assert not client.connected

        client.on_connection_state_change = handle_on_connection_state_change
        await handler_called.wait()

    @pytest.mark.it(
        "Can do a manual connect in the `on_connection_state_change` call that if notifying the user about a disconnect."
    )
    @pytest.mark.parametrize(*test_config.connection_retry_disabled_and_enabled)
    @pytest.mark.parametrize(*test_config.auto_connect_off_and_on)
    async def test_connect_in_the_middle_of_disconnect(
        self, brand_new_client, event_loop, service_helper, random_message
    ):
        """
        Explanation: People will call `connect` inside `on_connection_state_change` handlers.
        We have to make sure that we can handle this without getting stuck in a bad state.
        """
        client = brand_new_client
        assert client

        reconnected_event = asyncio.Event()

        async def handle_on_connection_state_change():
            nonlocal reconnected_event
            if client.connected:
                logger.info("connected.  nothing to do")
            else:
                logger.info("disconnected.  reconnecting.")
                await client.connect()
                assert client.connected
                event_loop.call_soon_threadsafe(reconnected_event.set)

        client.on_connection_state_change = handle_on_connection_state_change

        # connect
        await client.connect()
        assert client.connected

        # disconnet.
        reconnected_event.clear()
        await client.disconnect()

        # wait for handle_on_connection_state_change to reconnect
        await reconnected_event.wait()
        assert client.connected

        # sleep a while and make sure that we're still connected.
        await asyncio.sleep(3)
        assert client.connected

        # finally, send a message to makes reu we're _really_ connected
        await client.send_message(random_message)
        event = await service_helper.wait_for_eventhub_arrival(random_message.message_id)
        assert event

    @pytest.mark.it(
        "Can do a manual disconnect in the `on_connection_state_change` call that if notifying the user about a connect."
    )
    @pytest.mark.parametrize(*test_config.connection_retry_disabled_and_enabled)
    @pytest.mark.parametrize(*test_config.auto_connect_off_and_on)
    @pytest.mark.parametrize(
        "first_connect",
        [pytest.param(True, id="First connection"), pytest.param(False, id="Second connection")],
    )
    async def test_disconnect_in_the_middle_of_connect(
        self, brand_new_client, event_loop, service_helper, random_message, first_connect
    ):
        """
        Explanation: This is the inverse of `test_connect_in_the_middle_of_disconnect`.  This is
        less likely to be a user scenario, but it lets us test with unusual-but-specific timing
        on the call to `disconnect`.
        """
        client = brand_new_client
        assert client
        disconnect_on_next_connect_event = False

        disconnected_event = asyncio.Event()

        async def handle_on_connection_state_change():
            nonlocal disconnected_event
            if client.connected:
                if disconnect_on_next_connect_event:
                    logger.info("connected.  disconnecitng now")
                    await client.disconnect()
                    event_loop.call_soon_threadsafe(disconnected_event.set)
                else:
                    logger.info("connected, but nothing to do")
            else:
                logger.info("disconnected.  nothing to do")

        client.on_connection_state_change = handle_on_connection_state_change

        if not first_connect:
            # connect
            await client.connect()
            assert client.connected

            # disconnet.
            await client.disconnect()

        assert not client.connected

        # now, connect (maybe for the second time), and disconnect inside the on_connected handler
        disconnect_on_next_connect_event = True
        disconnected_event.clear()
        await client.connect()

        # and wait for us to disconnect
        await disconnected_event.wait()
        assert not client.connected

        # sleep a while and make sure that we're still disconnected.
        await asyncio.sleep(3)
        assert not client.connected

        # finally, connect and make sure we can send a message
        disconnect_on_next_connect_event = False
        await client.connect()
        assert client.connected

        await client.send_message(random_message)
        event = await service_helper.wait_for_eventhub_arrival(random_message.message_id)
        assert event

    # TODO: Add connect/disconnect stress, multiple times with connect inside disconnect and disconnect inside connect.


@pytest.mark.dropped_connection
@pytest.mark.describe("Client with dropped connection")
class TestConnectDisconnectDroppedConnection(object):
    @pytest.fixture(scope="class")
    def extra_client_kwargs(self):
        return {"keep_alive": 5}

    @pytest.mark.it("disconnects when network drops all outgoing packets")
    async def test_disconnect_on_drop_outgoing(self, client, dropper):

        await client.connect()
        assert client.connected
        dropper.drop_outgoing()

        while client.connected:
            await asyncio.sleep(1)

    @pytest.mark.it("disconnects when network rejects all outgoing packets")
    async def test_disconnect_on_reject_outgoing(self, client, dropper):

        await client.connect()
        assert client.connected
        dropper.reject_outgoing()

        while client.connected:
            await asyncio.sleep(1)
