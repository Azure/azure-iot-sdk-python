# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module contains an Inbox class for use with an asynchronous client"""
import asyncio
import threading
import janus
from azure.iot.device.iothub.sync_inbox import AbstractInbox
from . import loop_management

# IMPLEMENTATION NOTE: The janus Queue exists entirely on the "client internal loop",
# which runs on its own thread. Think of it kind of as a worker loop where async inbox access
# operations are scheduled, with the results returned back to whatever thread/loop scheduled them.
# We do this so that it is safe to use inboxes across different threads, in different places.
# (e.g. customer thread, handler manager thread, callback thread, etc.)


class AsyncClientInbox(AbstractInbox):
    """Holds generic incoming data for an asynchronous client.

    All methods implemented in this class are threadsafe.
    """

    def __init__(self):
        """Initializer for AsyncClientInbox."""

        # The queue must be instantiated on the client internal loop, but there's no way to do
        # that at instantiation from a different loop, so instead we make coroutine to do the
        # task and run it on the client internal loop.
        # It's not pretty, but it works (newer versions of janus have a loop parameter, but
        # not the version we are currently locked at)
        async def make_queue():
            return janus.Queue()

        loop = loop_management.get_client_internal_loop()
        fut = asyncio.run_coroutine_threadsafe(make_queue(), loop)
        self._queue = fut.result()

    def __contains__(self, item):
        """Return True if item is in Inbox, False otherwise"""
        # Note that this function accesses private attributes of janus, thus it is somewhat
        # dangerous. Unfortunately, it is the only way to implement this functionality.
        # However, because this function is only used in tests, I feel it is acceptable.
        with self._queue._sync_mutex:
            return item in self._queue._queue

    def put(self, item):
        """Put an item into the Inbox.

        :param item: The item to be put in the Inbox.
        """
        self._queue.sync_q.put(item)

    async def get(self):
        """Remove and return an item from the Inbox.

        If Inbox is empty, wait until an item is available.

        :returns: An item from the Inbox.
        """
        loop = loop_management.get_client_internal_loop()
        fut = asyncio.run_coroutine_threadsafe(self._queue.async_q.get(), loop)
        return await asyncio.wrap_future(fut)

    def empty(self):
        """Returns True if the inbox is empty, False otherwise

        Note that there is a race condition here, and this may not be accurate. This is because
        the .empty() operation on a janus queue is not threadsafe.

        :returns: Boolean indicating if the inbox is empty
        """
        return self._queue.async_q.empty()

    def clear(self):
        """Remove all items from the inbox."""
        while True:
            try:
                self._queue.sync_q.get_nowait()
            except janus.SyncQueueEmpty:
                break
