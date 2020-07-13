# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
import asyncio
import sys
import logging
from azure.iot.device.common import asyncio_compat

logging.basicConfig(level=logging.DEBUG)

pytestmark = pytest.mark.asyncio


@pytest.fixture
def dummy_coroutine():
    async def coro():
        return

    return coro


@pytest.mark.describe("get_running_loop()")
class TestGetRunningLoop(object):
    @pytest.mark.it("Returns the currently running Event Loop in Python 3.7 or higher")
    @pytest.mark.skipif(sys.version_info < (3, 7), reason="Requires Python 3.7+")
    async def test_returns_currently_running_event_loop_(self, mocker, event_loop):
        spy_get_running_loop = mocker.spy(asyncio, "get_running_loop")
        result = asyncio_compat.get_running_loop()
        assert result == event_loop
        assert spy_get_running_loop.call_count == 1
        assert spy_get_running_loop.call_args == mocker.call()

    @pytest.mark.it(
        "Raises a RuntimeError if there is no running Event Loop in Python 3.7 or higher"
    )
    @pytest.mark.skipif(sys.version_info < (3, 7), reason="Requires Python 3.7+")
    async def test_raises_runtime_error_if_no_running_event_loop(self, mocker):
        mocker.patch.object(asyncio, "get_running_loop", side_effect=RuntimeError)
        with pytest.raises(RuntimeError):
            asyncio_compat.get_running_loop()

    @pytest.mark.it("Returns the currently running Event Loop in Python 3.6 or below")
    @pytest.mark.skipif(sys.version_info >= (3, 7), reason="Requires Python 3.6 or below")
    async def test_returns_currently_running_event_loop_py36orless_compat(self, mocker, event_loop):
        spy_get_event_loop = mocker.spy(asyncio, "_get_running_loop")
        result = asyncio_compat.get_running_loop()
        assert result == event_loop
        assert spy_get_event_loop.call_count == 1
        assert spy_get_event_loop.call_args == mocker.call()

    @pytest.mark.it(
        "Raises a RuntimeError if there is no running Event Loop in Python 3.6 or below"
    )
    @pytest.mark.skipif(sys.version_info >= (3, 7), reason="Requires Python 3.6 or below")
    async def test_raises_runtime_error_if_no_running_event_loop_py36orless_compat(self, mocker):
        mocker.patch.object(asyncio, "_get_running_loop", return_value=None)
        with pytest.raises(RuntimeError):
            asyncio_compat.get_running_loop()


@pytest.mark.describe("create_task()")
class TestCreateTask(object):
    @pytest.mark.it(
        "Returns a Task that wraps a given coroutine, and schedules its execution, in Python 3.7 or higher"
    )
    @pytest.mark.skipif(sys.version_info < (3, 7), reason="Requires Python 3.7+")
    async def test_returns_task_wrapping_given_coroutine(self, mocker, dummy_coroutine):
        spy_create_task = mocker.spy(asyncio, "create_task")
        coro_obj = dummy_coroutine()
        result = asyncio_compat.create_task(coro_obj)
        assert isinstance(result, asyncio.Task)
        assert spy_create_task.call_count == 1
        assert spy_create_task.call_args == mocker.call(coro_obj)

    @pytest.mark.it(
        "Returns a Task that wraps a given coroutine, and schedules its execution, in Python 3.6 or below"
    )
    @pytest.mark.skipif(sys.version_info >= (3, 7), reason="Requires Python 3.6 or below")
    async def test_returns_task_wrapping_given_coroutine_py36orless_compat(
        self, mocker, dummy_coroutine
    ):
        spy_ensure_future = mocker.spy(asyncio, "ensure_future")
        coro_obj = dummy_coroutine()
        result = asyncio_compat.create_task(coro_obj)
        assert isinstance(result, asyncio.Task)
        assert spy_ensure_future.call_count == 1
        assert spy_ensure_future.call_args == mocker.call(coro_obj)


@pytest.mark.describe("create_future()")
class TestCreateFuture(object):
    @pytest.mark.it(
        "Returns a new Future object attached to the given Event Loop, in Python 3.5.2 or higher"
    )
    @pytest.mark.skipif(sys.version_info < (3, 5, 2), reason="Requires Python 3.5.2+")
    async def test_create_future_for_given_loop(self, mocker, event_loop):
        spy_create_future = mocker.spy(event_loop, "create_future")
        result = asyncio_compat.create_future(event_loop)
        assert isinstance(result, asyncio.Future)
        assert result._loop == event_loop  # Future.get_loop() only works in Python 3.7+
        assert spy_create_future.call_count == 1
        assert spy_create_future.call_args == mocker.call()

    @pytest.mark.it(
        "Returns a new Future object attached to the given Event Loop, in Python 3.5.1 or below"
    )
    @pytest.mark.skipif(sys.version_info >= (3, 5, 1), reason="Requires Python 3.5.1 or below")
    async def test_create_future_for_given_loop_py351orless_compat(self, mocker, event_loop):
        spy_future = mocker.spy(asyncio, "Future")
        result = asyncio_compat.create_future(event_loop)
        assert isinstance(
            result, spy_future.side_effect
        )  # spy_future.side_effect == asyncio.Future
        assert result._loop == event_loop  # Future.get_loop() only works in Python 3.7+
        assert spy_future.call_count == 1
        assert spy_future.call_args == mocker.call(loop=event_loop)


@pytest.mark.describe("run()")
class TestRun(object):
    @pytest.mark.it("Runs the given coroutine on a new event loop in Python 3.7 or higher")
    @pytest.mark.skipif(sys.version_info < (3, 7), reason="Requires Python 3.7+")
    def test_run_37_or_greater(self, mocker, dummy_coroutine):
        mock_asyncio_run = mocker.patch.object(asyncio, "run")
        coro = dummy_coroutine()
        result = asyncio_compat.run(coro)
        assert mock_asyncio_run.call_count == 1
        assert mock_asyncio_run.call_args == mocker.call(coro)
        assert result == mock_asyncio_run.return_value

    @pytest.mark.it("Runs the given coroutine on a new event loop in Python 3.6 or below")
    @pytest.mark.skipif(sys.version_info >= (3, 7), reason="Requires Python 3.6 or below")
    def test_run_36orless_compat(self, mocker, dummy_coroutine):
        mock_new_event_loop = mocker.patch.object(asyncio, "new_event_loop")
        mock_set_event_loop = mocker.patch.object(asyncio, "set_event_loop")
        mock_loop = mock_new_event_loop.return_value

        coro = dummy_coroutine()
        result = asyncio_compat.run(coro)

        # New event loop was created and set
        assert mock_new_event_loop.call_count == 1
        assert mock_new_event_loop.call_args == mocker.call()
        assert mock_set_event_loop.call_count == 2  # (second time at the end)
        assert mock_set_event_loop.call_args_list[0] == mocker.call(mock_loop)
        # Coroutine was run on the event loop, with the result returned
        assert mock_loop.run_until_complete.call_count == 1
        assert mock_loop.run_until_complete.call_args == mocker.call(coro)
        assert result == mock_loop.run_until_complete.return_value
        # Loop was closed after completion
        assert mock_loop.close.call_count == 1
        assert mock_loop.close.call_args == mocker.call()
        # Event loop was set back to None
        assert mock_set_event_loop.call_args_list[1] == mocker.call(None)

    @pytest.mark.it(
        "Closes the event loop and resets to None, even if an error occurs running the coroutine, in Python 3.6 or below"
    )
    @pytest.mark.skipif(sys.version_info >= (3, 7), reason="Requires Python 3.6 or below")
    def test_error_running_36orless_compat(self, mocker, dummy_coroutine, arbitrary_exception):
        # NOTE: This test is not necessary for 3.7 because asyncio.run() does this for us
        mock_new_event_loop = mocker.patch.object(asyncio, "new_event_loop")
        mock_set_event_loop = mocker.patch.object(asyncio, "set_event_loop")
        mock_loop = mock_new_event_loop.return_value
        mock_loop.run_until_complete.side_effect = arbitrary_exception

        coro = dummy_coroutine()
        with pytest.raises(type(arbitrary_exception)):
            asyncio_compat.run(coro)

        assert mock_loop.close.call_count == 1
        assert mock_set_event_loop.call_count == 2  # Once set, once to unset
        assert mock_set_event_loop.call_args_list[0] == mocker.call(mock_loop)
        assert mock_set_event_loop.call_args_list[1] == mocker.call(None)
