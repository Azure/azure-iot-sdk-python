# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
import logging
import threading
import time
from azure.iot.device.iothub.sync_inbox import SyncClientInbox, InboxEmpty

logging.basicConfig(level=logging.DEBUG)


@pytest.mark.describe("SyncClientInbox")
class TestSyncClientInbox(object):
    @pytest.mark.it("Instantiates empty")
    def test_instantiates_empty(self):
        inbox = SyncClientInbox()
        assert inbox.empty()

    @pytest.mark.it("Can be checked regarding whether or not it contains an item")
    def test_check_item_is_in_inbox(self, mocker):
        inbox = SyncClientInbox()
        assert inbox.empty()
        item = mocker.MagicMock()
        assert item not in inbox
        inbox._put(item)
        assert item in inbox

    @pytest.mark.it("Can checked regarding whether or not it is empty")
    def test_check_if_empty(self, mocker):
        inbox = SyncClientInbox()
        assert inbox.empty()
        item = mocker.MagicMock()
        inbox._put(item)
        assert not inbox.empty()
        inbox.get()
        assert inbox.empty()

    @pytest.mark.it("Operates according to FIFO")
    def test_operates_according_to_FIFO(self, mocker):
        inbox = SyncClientInbox()
        item1 = mocker.MagicMock()
        item2 = mocker.MagicMock()
        item3 = mocker.MagicMock()
        inbox._put(item1)
        inbox._put(item2)
        inbox._put(item3)

        assert inbox.get() is item1
        assert inbox.get() is item2
        assert inbox.get() is item3


@pytest.mark.describe("SyncClientInbox - ._put()")
class TestSyncClientInboxPut(object):
    @pytest.mark.it("Adds the given item to the inbox")
    def test_adds_item_to_inbox(self, mocker):
        inbox = SyncClientInbox()
        assert inbox.empty()
        item = mocker.MagicMock()
        inbox._put(item)
        assert not inbox.empty()
        assert item in inbox


@pytest.mark.describe("SyncClientInbox - .get()")
class TestSyncClientInboxGet(object):
    @pytest.mark.it("Returns and removes the next item from the inbox, if there is one")
    def test_removes_item_from_inbox_if_already_there(self, mocker):
        inbox = SyncClientInbox()
        assert inbox.empty()
        item = mocker.MagicMock()
        inbox._put(item)
        assert not inbox.empty()
        retrieved_item = inbox.get()
        assert retrieved_item is item
        assert inbox.empty()

    @pytest.mark.it(
        "Blocks on an empty inbox until an item is available to remove and return, if using blocking mode"
    )
    def test_waits_for_item_to_be_added_if_inbox_empty_in_blocking_mode(self, mocker):
        inbox = SyncClientInbox()
        assert inbox.empty()
        item = mocker.MagicMock()

        def insert_item():
            time.sleep(0.01)  # wait before inserting
            inbox._put(item)

        insertion_thread = threading.Thread(target=insert_item)
        insertion_thread.start()

        retrieved_item = inbox.get(block=True)
        assert retrieved_item is item
        assert inbox.empty()

    @pytest.mark.it(
        "Raises InboxEmpty exception after a timeout while blocking on an empty inbox, if a timeout is specified"
    )
    def test_times_out_while_blocking_if_timeout_specified(self, mocker):
        inbox = SyncClientInbox()
        assert inbox.empty()
        with pytest.raises(InboxEmpty):
            inbox.get(block=True, timeout=0.01)

    @pytest.mark.it(
        "Raises InboxEmpty exception if the inbox is empty, when using non-blocking mode"
    )
    def test_get_raises_empty_if_inbox_empty_in_non_blocking_mode(self):
        inbox = SyncClientInbox()
        assert inbox.empty()
        with pytest.raises(InboxEmpty):
            inbox.get(block=False)


@pytest.mark.describe("SyncClientInbox - .clear()")
class TestSyncClientInboxClear(object):
    @pytest.mark.it("Clears all items from the inbox")
    def test_can_clear_all_items(self, mocker):
        inbox = SyncClientInbox()
        item1 = mocker.MagicMock()
        item2 = mocker.MagicMock()
        item3 = mocker.MagicMock()
        inbox._put(item1)
        inbox._put(item2)
        inbox._put(item3)
        assert not inbox.empty()

        inbox.clear()
        assert inbox.empty()
