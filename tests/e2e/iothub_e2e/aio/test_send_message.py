# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import asyncio
import pytest
import logging
import json
import dev_utils

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)


PACKET_DROP = "Packet Drop"
PACKET_REJECT = "Packet Reject"


@pytest.fixture(params=[PACKET_DROP, PACKET_REJECT])
def failure_type(request):
    return request.param


@pytest.mark.describe("Client send_message method")
class TestSendMessage(object):
    @pytest.mark.it("Can send a simple message")
    @pytest.mark.quicktest_suite
    async def test_send_message_simple(
        self, leak_tracker, session_object, random_message, service_helper
    ):
        leak_tracker.set_initial_object_list()

        async with session_object:
            await session_object.send_message(random_message)

        event = await service_helper.wait_for_eventhub_arrival(random_message.message_id)
        # TODO: This behavior changed from v2->v3. Which is correct?
        # assert json.dumps(event.message_body) == random_message.payload
        assert event.message_body == random_message.payload

        leak_tracker.check_for_leaks()

    @pytest.mark.it("Raises correct exception for un-serializable payload")
    @pytest.mark.skip("send_message doesn't raise")
    async def test_bad_payload_raises(self, leak_tracker, session_object):
        leak_tracker.set_initial_object_list()

        # There's no way to serialize a function.
        def thing_that_cant_serialize():
            pass

        async with session_object:
            # TODO: what is the right error here?
            with pytest.raises(asyncio.CancelledError) as e_info:
                await session_object.send_message(thing_that_cant_serialize)
            assert isinstance(e_info.value.__cause__, TypeError)

        del e_info
        leak_tracker.check_for_leaks()

    @pytest.mark.it("Can send a JSON-formatted string that isn't wrapped in a Message object")
    async def test_sends_json_string(self, leak_tracker, session_object, service_helper):
        leak_tracker.set_initial_object_list()

        message = json.dumps(dev_utils.get_random_dict())

        async with session_object:
            await session_object.send_message(message)

        event = await service_helper.wait_for_eventhub_arrival(None)
        assert json.dumps(event.message_body) == message

        leak_tracker.check_for_leaks()

    @pytest.mark.it("Can send a random string that isn't wrapped in a Message object")
    async def test_sends_random_string(self, leak_tracker, session_object, service_helper):
        leak_tracker.set_initial_object_list()

        message = dev_utils.get_random_string(16)

        async with session_object:
            await session_object.send_message(message)

        event = await service_helper.wait_for_eventhub_arrival(None)
        assert event.message_body == message

        leak_tracker.check_for_leaks()

    # TODO: "Succeeds once network is restored and client automatically reconnects after having disconnected due to network failure"
    # TODO: "Succeeds if network failure resolves before client can disconnect"
    # TODO: "Client send_message method with network failure (Connection Retry disabled)"
    # TODO: "Succeeds if network failure resolves before client can disconnect"
