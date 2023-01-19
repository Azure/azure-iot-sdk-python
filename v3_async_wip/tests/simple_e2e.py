# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module is not currently run in the gate. It's just a simple local E2E test.
Will be removed once full E2E support implemented"""

import asyncio
import logging
import os
import pytest
from dev_utils import iptables
from v3_async_wip import mqtt_client
from . import transport_helper

logger = logging.getLogger(__name__)

PORT = 8883
TRANSPORT = "tcp"  # websockets
IPTABLES_TRANSPORT = "mqtt"  # mqttws

CONNECTION_STRING = os.getenv("IOTHUB_DEVICE_CONNECTION_STRING")
HOSTNAME = transport_helper.get_hostname(CONNECTION_STRING)


class Dropper(object):
    def __init__(self, transport):
        self.transport = transport

    def disconnect_outgoing(self, disconnect_type):
        iptables.disconnect_output_port(disconnect_type, self.transport, HOSTNAME)

    def drop_outgoing(self):
        iptables.disconnect_output_port("DROP", self.transport, HOSTNAME)

    def reject_outgoing(self):
        iptables.disconnect_output_port("REJECT", self.transport, HOSTNAME)

    def restore_all(self):
        iptables.reconnect_all(self.transport, HOSTNAME)


@pytest.fixture(scope="function")
def dropper():
    dropper = Dropper(IPTABLES_TRANSPORT)
    yield dropper
    logger.info("restoring all")
    dropper.restore_all()


@pytest.fixture
async def client():
    client_id = transport_helper.get_client_id(CONNECTION_STRING)
    username = transport_helper.get_username(CONNECTION_STRING)
    password = transport_helper.get_password(CONNECTION_STRING)
    ssl_context = transport_helper.create_ssl_context()

    client = mqtt_client.MQTTClient(
        client_id=client_id,
        hostname=HOSTNAME,
        port=PORT,
        transport=TRANSPORT,
        keep_alive=5,
        auto_reconnect=False,
        ssl_context=ssl_context,
    )
    client.set_credentials(username, password)
    yield client
    await client.disconnect()


def assert_connected_state(client):
    assert client.is_connected()
    assert client._desire_connection
    assert not client._network_loop.done()


def assert_disconnected_state(client):
    assert not client.is_connected()
    assert not client._desire_connection
    assert client._network_loop is None


def assert_dropped_conn_state(client):
    assert not client.is_connected()
    assert client._desire_connection
    assert client._network_loop.done()


@pytest.mark.it("Connect and disconnect")
async def test_connect_disconnect_twice(client):
    async def conn_disconn():
        # Connect
        await client.connect()
        assert_connected_state(client)
        # Wait
        await asyncio.sleep(1)
        # Disconnect
        await client.disconnect()
        assert_disconnected_state(client)

    # Do it twice to make sure it's repeatable
    await conn_disconn()
    await asyncio.sleep(1)
    await conn_disconn()


@pytest.mark.it("Queued connects and disconnects")
async def test_queued_connects_and_disconnects(client):
    # TODO: this may be unreliable - there's no guarantee that they will resolve in the desired
    # order, and thus, the assertion at the end may end up being incorrect.
    # This test likely ought to be redesigned.
    await asyncio.gather(
        client.connect(),
        client.disconnect(),
        client.disconnect(),
        client.connect(),
        client.connect(),
        client.disconnect(),
    )
    assert_disconnected_state(client)


@pytest.mark.it("Connection drop")
async def test_connection_drop(client, dropper):
    await client.connect()
    assert_connected_state(client)
    # Wait
    await asyncio.sleep(1)
    # Drop network
    dropper.drop_outgoing()
    # Wait for drop
    async with client.disconnected_cond:
        await client.disconnected_cond.wait()
    await asyncio.sleep(0.1)
    assert_dropped_conn_state(client)


@pytest.mark.it("Connect while connected")
async def test_connect_while_connected(client):
    await client.connect()
    assert_connected_state(client)
    await client.connect()
    assert_connected_state(client)


@pytest.mark.it("Disconnect while never connected")
async def test_disconnect_while_never_connected(client):
    await client.disconnect()
    assert_disconnected_state(client)


@pytest.mark.it("Disconnect while disconnected")
async def test_disconnect_while_disconnected(client):
    # Connect first to disconnect to have been at one point connected
    await client.connect()
    assert_connected_state(client)
    await client.disconnect()
    assert_disconnected_state(client)
    await client.disconnect()
    assert_disconnected_state(client)


@pytest.mark.it("Disconnect after drop")
async def test_disconnect_after_drop(client, dropper):
    await client.connect()
    assert_connected_state(client)
    # Wait
    await asyncio.sleep(1)
    # Drop network
    dropper.drop_outgoing()
    # Wait for drop
    async with client.disconnected_cond:
        await client.disconnected_cond.wait()
    await asyncio.sleep(0.1)
    assert_dropped_conn_state(client)
    # Restore and manually disconnect
    dropper.restore_all()
    await client.disconnect()
    assert_disconnected_state(client)


@pytest.mark.it("Connect after drop")
async def test_connect_after_drop(client, dropper):
    await client.connect()
    assert_connected_state(client)
    # Wait
    await asyncio.sleep(1)
    # Drop network
    dropper.drop_outgoing()
    # Wait for drop
    async with client.disconnected_cond:
        await client.disconnected_cond.wait()
    await asyncio.sleep(0.1)
    assert_dropped_conn_state(client)
    # Restore and connect manually
    dropper.restore_all()
    await client.connect()
    assert_connected_state(client)
    # Wait
    await asyncio.sleep(1)
    # Drop network again
    dropper.drop_outgoing()
    # Wait for drop
    async with client.disconnected_cond:
        await client.disconnected_cond.wait()
    await asyncio.sleep(0.1)
    assert_dropped_conn_state(client)
    # Restore and manually disconnect
    dropper.restore_all()
    await client.disconnect()
    assert_disconnected_state(client)


# TODO: auto reconnect
