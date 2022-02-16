# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module contains an Inbox class for use with a synchronous client."""

import queue
import abc


class InboxEmpty(Exception):
    pass


class AbstractInbox(abc.ABC):
    """Abstract Base Class for Inbox.

    Holds generic incoming data for a client.

    All methods, when implemented, should be threadsafe.
    """

    @abc.abstractmethod
    def put(self, item):
        """Put an item into the Inbox.

        Implementation MUST be a synchronous function.
        Only to be used by the InboxManager.

        :param item: The item to put in the Inbox.
        """
        pass

    @abc.abstractmethod
    def get(self):
        """Remove and return an item from the inbox.

        Implementation should have the capability to block until an item is available.
        Implementation can be a synchronous function or an asynchronous coroutine.

        :returns: An item from the Inbox.
        """
        pass

    @abc.abstractmethod
    def empty(self):
        """Returns True if the inbox is empty, False otherwise

        :returns: Boolean indicating if the inbox is empty
        """
        pass

    @abc.abstractmethod
    def clear(self):
        """Remove all items from the inbox."""
        pass


class SyncClientInbox(AbstractInbox):
    """Holds generic incoming data for a synchronous client.

    All methods implemented in this class are threadsafe.
    """

    def __init__(self):
        """Initializer for SyncClientInbox"""
        self._queue = queue.Queue()

    def __contains__(self, item):
        """Return True if item is in Inbox, False otherwise"""
        with self._queue.mutex:
            return item in self._queue.queue

    def put(self, item):
        """Put an item into the inbox.

        Only to be used by the InboxManager.

        :param item: The item to put in the inbox.
        """
        self._queue.put(item)

    def get(self, block=True, timeout=None):
        """Remove and return an item from the inbox.

        :param bool block: Indicates if the operation should block until an item is available.
        Default True.
        :param int timeout: Optionally provide a number of seconds until blocking times out.

        :raises: InboxEmpty if timeout occurs because the inbox is empty
        :raises: InboxEmpty if inbox is empty in non-blocking mode

        :returns: An item from the Inbox
        """
        try:
            return self._queue.get(block=block, timeout=timeout)
        except queue.Empty:
            raise InboxEmpty("Inbox is empty")

    def empty(self):
        """Returns True if the inbox is empty, False otherwise.

        Note that there is a race condition here, and this may not be accurate as the queue size
        may change while this operation is occurring.

        :returns: Boolean indicating if the inbox is empty
        """
        return self._queue.empty()

    def join(self):
        """Block until all items in the inbox have been gotten and processed.

        Only really used for test code.
        """
        return self._queue.join()

    def clear(self):
        """Remove all items from the inbox."""
        with self._queue.mutex:
            self._queue.queue.clear()
