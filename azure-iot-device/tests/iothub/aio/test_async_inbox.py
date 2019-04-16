# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
import asyncio
from azure.iot.device.iothub.aio.async_inbox import AsyncClientInbox

# Note that the async tests are currently raising runtime warnings for some reason.
# I suspect it is a bug in janus.Queue.
# Will investigate further at a later date.


class TestAsyncClientInbox(object):
    def test_instantiates_empty(self):
        inbox = AsyncClientInbox()
        assert inbox.empty()

    # this test also raises runtime warning if it's asynchronous
    def test__put_adds_item_to_inbox(self, mocker):
        inbox = AsyncClientInbox()
        assert inbox.empty()
        item = mocker.MagicMock()
        inbox._put(item)
        assert not inbox.empty()

    @pytest.mark.asyncio
    async def test_get_removes_item_from_inbox_if_already_there(self, mocker):
        inbox = AsyncClientInbox()
        assert inbox.empty()
        item = mocker.MagicMock()
        inbox._put(item)
        assert not inbox.empty()
        retrieved_item = await inbox.get()
        assert retrieved_item is item
        assert inbox.empty()

    @pytest.mark.asyncio
    async def test_get_waits_for_item_to_be_added_if_inbox_empty(self, mocker):
        inbox = AsyncClientInbox()
        assert inbox.empty()
        item = mocker.MagicMock()

        async def wait_for_item():
            retrieved_item = await inbox.get()
            assert retrieved_item is item

        async def insert_item():
            await asyncio.sleep(1)  # wait before adding item to ensure the above coroutine is first
            inbox._put(item)

        await asyncio.gather(wait_for_item(), insert_item())

    @pytest.mark.asyncio
    async def test_operates_according_to_FIFO(self, mocker):
        inbox = AsyncClientInbox()
        item1 = mocker.MagicMock()
        item2 = mocker.MagicMock()
        item3 = mocker.MagicMock()
        inbox._put(item1)
        inbox._put(item2)
        inbox._put(item3)

        assert await inbox.get() is item1
        assert await inbox.get() is item2
        assert await inbox.get() is item3

    @pytest.mark.asyncio
    async def test_can_check_if_empty(self, mocker):
        inbox = AsyncClientInbox()
        assert inbox.empty()
        inbox._put(mocker.MagicMock())
        assert not inbox.empty()
        await inbox.get()
        assert inbox.empty()

    def test_can_clear_all_items(self, mocker):
        inbox = AsyncClientInbox()
        item1 = mocker.MagicMock()
        item2 = mocker.MagicMock()
        item3 = mocker.MagicMock()
        inbox._put(item1)
        inbox._put(item2)
        inbox._put(item3)
        assert not inbox.empty()

        inbox.clear()
        assert inbox.empty()
