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
def wait_for():
    def wait_for_condition(condition, timeout=5, interval=0.01):
        deadline = time.monotonic() + timeout
        while not condition():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                pytest.fail("Timed out waiting for condition")
            time.sleep(min(interval, remaining))

    return wait_for_condition


@pytest.fixture
def async_wait_for():
    async def wait_for_condition(condition, timeout=5, interval=0.01):
        deadline = time.monotonic() + timeout
        while not condition():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                pytest.fail("Timed out waiting for condition")
            await asyncio.sleep(min(interval, remaining))

    return wait_for_condition


@pytest.fixture
def track_call_started(mocker):
    def track_call(obj, method_name):
        call_started = threading.Event()
        original_method = getattr(obj, method_name)

        def tracked_call(*args, **kwargs):
            call_started.set()
            return original_method(*args, **kwargs)

        mocker.patch.object(obj, method_name, side_effect=tracked_call)
        return call_started

    return track_call


@pytest.fixture
def run_in_daemon_thread():
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
