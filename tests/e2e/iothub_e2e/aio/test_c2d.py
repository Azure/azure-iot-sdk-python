# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import asyncio
import pytest
import logging
import json
import sys
from dev_utils import get_random_dict

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)

# TODO: add tests for various application properties
# TODO: is there a way to call send_c2d so it arrives as an object rather than a JSON string?


@pytest.mark.describe("Client C2d")
class TestReceiveC2d(object):
    @pytest.mark.it("Can receive C2D")
    @pytest.mark.quicktest_suite
    async def test_receive_c2d(self, session_object, service_helper, event_loop, leak_tracker):
        leak_tracker.set_initial_object_list()

        message = json.dumps(get_random_dict())

        queue = asyncio.Queue()

        async def listener(sess):
            try:
                async with sess.messages() as messages:
                    async for message in messages:
                        await queue.put(message)
            except asyncio.CancelledError:
                # this happens during shutdown. no need to log this.
                raise
            except BaseException:
                # Without this line, exceptions get silently ignored until
                # we await the listener task.
                logger.error("Exception", exc_info=True)
                raise

        async with session_object:
            listener_task = asyncio.create_task(listener(session_object))

            await service_helper.send_c2d(message, {})

            received_message = await queue.get()

        assert session_object.connected is False
        with pytest.raises(asyncio.CancelledError):
            await listener_task
        listener_task = None

        assert received_message.payload == message

        del received_message
        leak_tracker.check_for_leaks()

    @pytest.mark.it("Can receive C2D using anext")
    @pytest.mark.quicktest_suite
    @pytest.mark.skipif(
        sys.version_info.major == 3 and sys.version_info.minor < 10,
        reason="anext was not introduced until 3.10",
    )
    async def test_receive_c2d_using_anext(
        self, session_object, service_helper, event_loop, leak_tracker
    ):
        leak_tracker.set_initial_object_list()

        message = json.dumps(get_random_dict())

        async with session_object:
            async with session_object.messages() as messages:
                await service_helper.send_c2d(message, {})
                received_message = await anext(messages)

        assert session_object.connected is False
        assert received_message.payload == message

        del received_message
        leak_tracker.check_for_leaks()
