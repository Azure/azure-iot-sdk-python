# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import asyncio
import pytest
import json
import logging
from utils import get_random_message

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)

pytestmark = pytest.mark.asyncio


@pytest.mark.describe("Device Client with reconnect enabled")
class TestSasRenewalReconnectEnabled(object):
    @pytest.fixture(scope="class")
    def client_kwargs(self):
        # should renew after 10 seconds
        return {"sastoken_ttl": 130}

    @pytest.mark.it("Renews and reconnects before expiry")
    # TODO: rename incoming_event_queue becaues it conflicts wiht event_loop
    async def test_sas_renews(self, client, event_loop, get_next_eventhub_arrival):
        test_message = get_random_message()

        connected_event = asyncio.Event()
        token_at_connect_time = None

        token_object = client._mqtt_pipeline._pipeline.pipeline_configuration.sastoken

        async def handle_on_connection_state_change():
            nonlocal token_at_connect_time
            logger.info("handle_on_connection_state_change: {}".format(client.connected))
            if client.connected:
                token_at_connect_time = str(token_object)
                event_loop.call_soon_threadsafe(connected_event.set)

        client.on_connection_state_change = handle_on_connection_state_change

        # Since we re-use client objects, we don't know if the token is
        # about to renew.  Since it renews every 10 seconds, let's wait for it to renew
        # once before we test.
        assert client.connected
        connected_event.clear()
        logger.info("Waiting for reconnection to sync up the test")
        await connected_event.wait()
        connected_event.clear()

        # OK, we're ready to test.  wait for the renewal
        token_before_connect = str(token_object)
        logger.info("Waiting for reconnection to verify the change")
        await connected_event.wait()

        # Finally verify that our token changed.
        assert str(token_object) == token_at_connect_time
        assert not token_before_connect == token_at_connect_time

        # and verify that we can send
        await client.send_message(test_message)

        # and verify that the message arrived at the service
        # TODO incoming_event_queue.get should check thread future
        event = await get_next_eventhub_arrival()
        assert json.dumps(event.message_body) == test_message.data


@pytest.mark.describe("Device Client with reconnect disabled")
class TestSasRenewalReconnectDisabled(object):
    @pytest.fixture(scope="class")
    def client_kwargs(self):
        # should renew after 10 seconds
        return {"sastoken_ttl": 130, "connection_retry": False}

    @pytest.mark.it("Renews and reconnects before expiry")
    async def test_sas_renews(self, client, event_loop, get_next_eventhub_arrival):
        test_message = get_random_message()

        connected_event = asyncio.Event()
        token_at_connect_time = None

        token_object = client._mqtt_pipeline._pipeline.pipeline_configuration.sastoken

        async def handle_on_connection_state_change():
            nonlocal token_at_connect_time
            logger.info("handle_on_connection_state_change: {}".format(client.connected))
            if client.connected:
                token_at_connect_time = str(token_object)
                event_loop.call_soon_threadsafe(connected_event.set)

        client.on_connection_state_change = handle_on_connection_state_change

        # Since we re-use client objects, we don't know if the token is
        # about to renew.  Since it renews every 10 seconds, let's wait for it to renew
        # once before we test.
        assert client.connected
        connected_event.clear()
        logger.info("Waiting for reconnection to sync up the test")
        await connected_event.wait()
        connected_event.clear()

        # OK, we're ready to test.  wait for the renewal
        token_before_connect = str(token_object)
        logger.info("Waiting for reconnection to verify the change")
        await connected_event.wait()

        # Finally verify that our token changed.
        assert str(token_object) == token_at_connect_time
        assert not token_before_connect == token_at_connect_time

        # and verify that we can send
        await client.send_message(test_message)

        # and verify that the message arrived at the service
        event = await get_next_eventhub_arrival()
        assert json.dumps(event.message_body) == test_message.data
