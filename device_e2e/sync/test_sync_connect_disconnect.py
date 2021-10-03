# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import pytest
import logging
import time

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)


@pytest.mark.describe("Device Client")
class TestConnectDisconnect(object):
    @pytest.mark.it("Can disconnect and reconnect")
    def test_connect_disconnect(self, client):
        assert client
        client.connect()
        assert client.connected

        client.disconnect()
        assert not client.connected

        client.connect()
        assert client.connected


@pytest.mark.dropped_connection
@pytest.mark.describe("Device Client with dropped connection")
class TestConnectDisconnectDroppedConnection(object):
    @pytest.fixture(scope="class")
    def client_kwargs(self):
        return {"keep_alive": 5}

    @pytest.mark.it("disconnects when network drops all outgoing packets")
    def test_disconnect_on_drop_outgoing(self, client, dropper):

        client.connect()
        assert client.connected
        dropper.drop_outgoing()

        while client.connected:
            time.sleep(1)

    @pytest.mark.it("disconnects when network rejects all outgoing packets")
    def test_disconnect_on_reject_outgoing(self, client, dropper):

        client.connect()
        assert client.connected
        dropper.reject_outgoing()

        while client.connected:
            time.sleep(1)
