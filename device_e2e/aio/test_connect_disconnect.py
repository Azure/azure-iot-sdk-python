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


@pytest.mark.dropped_connection
@pytest.mark.describe("Device Client with dropped connection")
class TestConnectDisconnectDroppedConnection(object):
    @pytest.fixture(scope="class")
    def client_kwargs(self):
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
