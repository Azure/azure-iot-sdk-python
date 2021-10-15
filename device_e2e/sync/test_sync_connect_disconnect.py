# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import pytest
import logging
import time
import test_config

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)


@pytest.mark.describe("Client object")
class TestConnectDisconnect(object):
    @pytest.mark.it("Can disconnect and reconnect")
    @pytest.mark.parametrize(*test_config.connection_retry_disabled_and_enabled)
    @pytest.mark.parametrize(*test_config.auto_connect_off_and_on)
    def test_connect_disconnect(self, brand_new_client):
        client = brand_new_client

        client.connect()
        assert client.connected

        client.disconnect()
        assert not client.connected

        client.connect()
        assert client.connected


@pytest.mark.dropped_connection
@pytest.mark.describe("Client object with dropped connection")
class TestConnectDisconnectDroppedConnection(object):
    @pytest.fixture(scope="class")
    def extra_client_kwargs(self):
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
