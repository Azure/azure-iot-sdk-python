# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
import threading
import time
from azure.iot.hub.devicesdk.sync_inbox import SyncClientInbox, InboxEmpty


class TestSyncClientInbox(object):
    def test_instantiates_empty(self):
        inbox = SyncClientInbox()
        assert inbox.empty()

    def test__put_adds_item_to_inbox(self, mocker):
        inbox = SyncClientInbox()
        assert inbox.empty()
        item = mocker.MagicMock()
        inbox._put(item)
        assert not inbox.empty()

    def test_get_removes_item_from_inbox_if_already_there(self, mocker):
        inbox = SyncClientInbox()
        assert inbox.empty()
        item = mocker.MagicMock()
        inbox._put(item)
        assert not inbox.empty()
        retrieved_item = inbox.get()
        assert retrieved_item is item
        assert inbox.empty()

    def test_get_waits_for_item_to_be_added_if_inbox_empty_in_blocking_mode(self, mocker):
        inbox = SyncClientInbox()
        assert inbox.empty()
        item = mocker.MagicMock()

        def insert_item():
            time.sleep(1)  # wait before inserting
            inbox._put(item)

        insertion_thread = threading.Thread(target=insert_item)
        insertion_thread.start()

        retrieved_item = inbox.get(block=True)
        assert retrieved_item is item
        assert inbox.empty()

    def test_get_times_out_while_blocking_if_timeout_specified(self, mocker):
        inbox = SyncClientInbox()
        assert inbox.empty()
        with pytest.raises(InboxEmpty):
            inbox.get(block=True, timeout=1)

    def test_get_raises_empty_if_inbox_empty_in_non_blocking_mode(self):
        inbox = SyncClientInbox()
        assert inbox.empty()
        with pytest.raises(InboxEmpty):
            inbox.get(block=False)

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

    def test_can_check_if_empty(self, mocker):
        inbox = SyncClientInbox()
        assert inbox.empty()
        item = mocker.MagicMock()
        inbox._put(item)
        assert not inbox.empty()
        inbox.get()
        assert inbox.empty()
