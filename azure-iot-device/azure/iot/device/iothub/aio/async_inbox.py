# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module contains an Inbox class for use with an asynchronous client"""

import janus
from azure.iot.device.iothub.sync_inbox import AbstractInbox


class AsyncClientInbox(AbstractInbox):
    """Holds generic incoming data for an asynchronous client.

    All methods implemented in this class are threadsafe.
    """

    def __init__(self):
        """Initializer for AsyncClientInbox."""
        self._queue = janus.Queue()

    def __contains__(self, item):
        """Return True if item is in Inbox, False otherwise"""
        # Note that this function accesses private attributes of janus, thus it is somewhat
        # dangerous. Unforutnately, it is the only way to implement this functionality.
        # However, because this function is only used in tests, I feel it is acceptable.
        with self._queue._sync_mutex:
            return item in self._queue._queue

    def _put(self, item):
        """Put an item into the Inbox.

        Block if necessary until a free slot is available.
        Only to be used by the InboxManager.

        :param item: The item to be put in the Inbox.
        """
        self._queue.sync_q.put(item)

    async def get(self):
        """Remove and return an item from the Inbox.

        If Inbox is empty, wait until an item is available.

        :returns: An item from the Inbox.
        """
        return await self._queue.async_q.get()

    def empty(self):
        """Returns True if the inbox is empty, False otherwise

        :returns: Boolean indicating if the inbox is empty
        """
        return self._queue.async_q.empty()

    def clear(self):
        """Remove all items from the inbox.
        """
        while True:
            try:
                self._queue.sync_q.get_nowait()
            except janus.SyncQueueEmpty:
                break
