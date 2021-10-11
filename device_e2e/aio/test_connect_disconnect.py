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


@pytest.mark.describe("Device Client")
class TestConnectDisconnect(object):
    @pytest.mark.it("Can disconnect and reconnect")
    @pytest.mark.parametrize(*test_config.connection_retry_disabled_and_enabled)
    @pytest.mark.parametrize(*test_config.auto_connect_off_and_on)
    async def test_connect_disconnect(self, brand_new_client):
        client = brand_new_client

        assert client
        await client.connect()
        assert client.connected

        await client.disconnect()
        assert not client.connected

        await client.connect()
        assert client.connected

    @pytest.mark.it("Can reconnect inside on_disconnected")
    @pytest.mark.parametrize(*test_config.connection_retry_disabled_and_enabled)
    @pytest.mark.parametrize(*test_config.auto_connect_off_and_on)
    @pytest.mark.slow
    async def test_reconnect_in_the_middle_of_disconnect(
        self, brand_new_client, event_loop, service_helper, random_message
    ):
        """
        Explanation: People will call connect() inside on_disconnected handlers.  We have
        to make sure that we can handle this without getting stuck in a bad state
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

    @pytest.mark.it("Can disconnect inside on_connected")
    @pytest.mark.parametrize(*test_config.connection_retry_disabled_and_enabled)
    @pytest.mark.parametrize(*test_config.auto_connect_off_and_on)
    @pytest.mark.parametrize(
        "first_connect",
        [pytest.param(True, id="First connection"), pytest.param(False, id="Second connection")],
    )
    @pytest.mark.slow
    async def test_disconnect_in_the_middle_of_connect(
        self, brand_new_client, event_loop, service_helper, random_message, first_connect
    ):
        """
        Explanation: People will call connect() inside on_disconnected handlers.  We have
        to make sure that we can handle this without getting stuck in a bad state
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
@pytest.mark.describe("Device Client with dropped connection")
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
