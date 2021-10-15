# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import asyncio
import pytest
import json
import logging
import test_config

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)

pytestmark = pytest.mark.asyncio


@pytest.mark.skipif(
    test_config.config.auth not in test_config.AUTH_WITH_RENEWING_TOKEN,
    reason="{} auth does not support token renewal".format(test_config.config.auth),
)
@pytest.mark.describe("Client sas renewal code")
@pytest.mark.dont_run_this_if_you_want_your_tests_to_go_fast
class TestSasRenewal(object):
    @pytest.fixture(scope="class")
    def extra_client_kwargs(self):
        # should renew after 10 seconds
        return {"sastoken_ttl": 130}

    @pytest.mark.it("Renews and reconnects before expiry")
    @pytest.mark.parametrize(*test_config.connection_retry_disabled_and_enabled)
    @pytest.mark.parametrize(*test_config.auto_connect_off_and_on)
    async def test_sas_renews(self, client, event_loop, service_helper, random_message):

        connected_event = asyncio.Event()
        disconnected_event = asyncio.Event()
        token_at_connect_time = None

        logger.info("connected and ready")

        token_object = client._mqtt_pipeline._pipeline.pipeline_configuration.sastoken

        async def handle_on_connection_state_change():
            nonlocal token_at_connect_time
            logger.info("handle_on_connection_state_change: {}".format(client.connected))
            if client.connected:
                token_at_connect_time = str(token_object)
                logger.info("saving token: {}".format(token_at_connect_time))

                event_loop.call_soon_threadsafe(connected_event.set)
            else:
                event_loop.call_soon_threadsafe(disconnected_event.set)

        client.on_connection_state_change = handle_on_connection_state_change

        # setting on_connection_state_change seems to have the side effect of
        # calling handle_on_connection_state_change once with the initial value.
        # Wait for one disconnect/reconnect cycle so we can get past it.
        await connected_event.wait()

        # OK, we're ready to test.  wait for the renewal
        token_before_connect = str(token_object)

        disconnected_event.clear()
        connected_event.clear()

        logger.info("Waiting for client to disconnect")
        await disconnected_event.wait()
        logger.info("Waiting for client to reconnect")
        await connected_event.wait()
        logger.info("Client reconnected")

        # Finally verify that our token changed.
        logger.info("token now = {}".format(str(token_object)))
        logger.info("token at_connect = {}".format(str(token_at_connect_time)))
        logger.info("token before_connect = {}".format(str(token_before_connect)))

        assert str(token_object) == token_at_connect_time
        assert not token_before_connect == token_at_connect_time

        # and verify that we can send
        await client.send_message(random_message)

        # and verify that the message arrived at the service
        # TODO incoming_event_queue.get should check thread future
        event = await service_helper.wait_for_eventhub_arrival(random_message.message_id)
        assert json.dumps(event.message_body) == random_message.data
