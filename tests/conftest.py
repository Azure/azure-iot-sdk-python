# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import asyncio
import concurrent.futures
import threading
import time

import pytest


@pytest.fixture
def poll_until():
    """Return a helper that polls a condition without exceeding a timeout."""

    def poll_until_condition(condition, *, timeout, interval=0.01):
        deadline = time.monotonic() + timeout
        while not condition():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                pytest.fail("Timed out waiting for condition")
            time.sleep(min(interval, remaining))

    return poll_until_condition


@pytest.fixture
def async_poll_until():
    """Return an async helper that polls a condition without blocking the event loop."""

    async def poll_until_condition(condition, *, timeout, interval=0.01):
        async def poll_condition():
            while not condition():
                await asyncio.sleep(interval)

        try:
            await asyncio.wait_for(poll_condition(), timeout=timeout)
        except asyncio.TimeoutError:
            pytest.fail("Timed out waiting for condition")

    return poll_until_condition


@pytest.fixture
def run_in_daemon_thread():
    """Return a helper that runs a function in a daemon thread and exposes its result."""

    def run(fn, *args, **kwargs):
        future = concurrent.futures.Future()

        def invoke():
            if not future.set_running_or_notify_cancel():
                return
            try:
                result = fn(*args, **kwargs)
            except BaseException as e:
                future.set_exception(e)
            else:
                future.set_result(result)

        threading.Thread(target=invoke, daemon=True).start()
        return future

    return run


@pytest.fixture
def assert_call_blocks(mocker, run_in_daemon_thread):
    """Return a helper that verifies a call blocks until an action releases it."""

    def assert_blocks(fn, *, blocked_on, release, args=(), kwargs=None, timeout=5):
        call_started = threading.Event()

        def tracked_call(*args, **kwargs):
            call_started.set()
            return blocked_on(*args, **kwargs)

        mocker.patch.object(blocked_on.__self__, blocked_on.__name__, side_effect=tracked_call)
        future = run_in_daemon_thread(fn, *args, **(kwargs or {}))
        try:
            assert call_started.wait(timeout=timeout)
            assert not future.done()
        finally:
            release()
        return future.result(timeout=timeout)

    return assert_blocks


"""
NOTE: ALL (yes, ALL) tests need some kind of non-specific, arbitrary exception should use
one of the following fixtures. This is to ensure the tests operate correctly - many tests used to
raise Exception or BaseException directly to test arbitrary exceptions, but the result was
that exception handling was hiding other errors (also caught by an "except: Exception" block).

The solution is to use a subclass of Exception or BaseException that is not defined anywhere else,
thus guaranteeing that it will be unexpected and unhandled except by broad all-encompassing
handling. Furthermore, because the exception in question is derived from either Exception or
BaseException, but is not itself an instance of either, tests checking that the exception in
question is raised will not spuriously pass due to different exceptions being raised.

For consistency, and to prevent confusion, please do this ONLY by using one of the following
fixtures.

You may (and should!) still use exceptions defined elsewhere for specific, non-arbitrary exceptions
(e.g. testing specific exceptions)
"""


@pytest.fixture
def arbitrary_exception():
    class ArbitraryException(Exception):
        pass

    e = ArbitraryException()
    return e


@pytest.fixture
def arbitrary_base_exception():
    class ArbitraryBaseException(BaseException):
        pass

    return ArbitraryBaseException()
