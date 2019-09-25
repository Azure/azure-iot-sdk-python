# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
import asyncio
import logging
from azure.iot.device.iothub.aio.async_inbox import AsyncClientInbox

logging.basicConfig(level=logging.DEBUG)

# Note that some small delays need to be added at the end of async tests due to
# RuntimeWarnings being thrown by the test ending before janus can correctly
# resolve its Futures. This may be a bug in janus.


@pytest.mark.describe("AsyncClientInbox")
class TestAsyncClientInbox(object):
    @pytest.mark.it("Instantiates empty")
    def test_instantiates_empty(self):
        inbox = AsyncClientInbox()
        assert inbox.empty()

    @pytest.mark.it("Can be checked regarding whether or not it contains an item")
    def test_check_item_is_in_inbox(self, mocker):
        inbox = AsyncClientInbox()
        assert inbox.empty()
        item = mocker.MagicMock()
        assert item not in inbox
        inbox._put(item)
        assert item in inbox

    @pytest.mark.it("Can be checked regarding whether or not it is empty")
    @pytest.mark.asyncio
    async def test_can_check_if_empty(self, mocker):
        inbox = AsyncClientInbox()
        assert inbox.empty()
        inbox._put(mocker.MagicMock())
        assert not inbox.empty()
        await inbox.get()
        assert inbox.empty()
        await asyncio.sleep(0.01)  # Do this to prevent RuntimeWarning from janus

    @pytest.mark.it("Operates according to FIFO")
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

        await asyncio.sleep(0.01)  # Do this to prevent RuntimeWarning from janus


@pytest.mark.describe("AsyncClientInbox - ._put()")
class TestAsyncClientInboxPut(object):
    @pytest.mark.it("Adds the given item to the inbox")
    def test_adds_item_to_inbox(self, mocker):
        inbox = AsyncClientInbox()
        assert inbox.empty()
        item = mocker.MagicMock()
        inbox._put(item)
        assert not inbox.empty()
        assert item in inbox


@pytest.mark.describe("AsyncClientInbox - .get()")
@pytest.mark.asyncio
class TestAsyncClientInboxGet(object):
    @pytest.mark.it("Returns and removes the next item from the inbox, if there is one")
    async def test_removes_item_from_inbox_if_already_there(self, mocker):
        inbox = AsyncClientInbox()
        assert inbox.empty()
        item = mocker.MagicMock()
        inbox._put(item)
        assert not inbox.empty()
        retrieved_item = await inbox.get()
        assert retrieved_item is item
        assert inbox.empty()

        await asyncio.sleep(0.01)  # Do this to prevent RuntimeWarning from janus

    @pytest.mark.it(
        "Blocks on an empty inbox until an item is available to remove and return, if using blocking mode"
    )
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


@pytest.mark.describe("AsyncClientInbox - .clear()")
class TestAsyncClientInboxClear(object):
    @pytest.mark.it("Clears all items from the inbox")
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
