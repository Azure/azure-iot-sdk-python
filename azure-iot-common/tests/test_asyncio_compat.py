import pytest
import asyncio
import sys
from azure.iot.common import asyncio_compat

pytestmark = pytest.mark.asyncio


@pytest.fixture
def dummy_coroutine():
    async def coro():
        return

    return coro


@pytest.mark.skipif(sys.version_info < (3, 7), reason="Requires Python 3.7+")
async def test_get_running_loop(mocker, event_loop):
    spy_get_running_loop = mocker.spy(asyncio, "get_running_loop")
    result = asyncio_compat.get_running_loop()
    assert result == event_loop
    assert spy_get_running_loop.call_count == 1
    assert spy_get_running_loop.call_args == mocker.call()


@pytest.mark.skipif(sys.version_info < (3, 7), reason="Requires Python 3.7+")
async def test_get_running_loop_no_running_loop(mocker):
    mocker.patch.object(asyncio, "get_running_loop", side_effect=RuntimeError)
    with pytest.raises(RuntimeError):
        asyncio_compat.get_running_loop()


@pytest.mark.skipif(sys.version_info >= (3, 7), reason="Requires Python 3.6 or below")
async def test_get_running_loop_36_compat(mocker, event_loop):
    spy_get_event_loop = mocker.spy(asyncio, "_get_running_loop")
    result = asyncio_compat.get_running_loop()
    assert result == event_loop
    assert spy_get_event_loop.call_count == 1
    assert spy_get_event_loop.call_args == mocker.call()


@pytest.mark.skipif(sys.version_info >= (3, 7), reason="Requires Python 3.6 or below")
async def test_get_running_loop_36_compat_no_running_loop(mocker):
    mocker.patch.object(asyncio, "_get_running_loop", return_value=None)
    with pytest.raises(RuntimeError, message="Expecting Runtime Error"):
        asyncio_compat.get_running_loop()


@pytest.mark.skipif(sys.version_info < (3, 7), reason="Requires Python 3.7+")
async def test_create_task(mocker, dummy_coroutine):
    spy_create_task = mocker.spy(asyncio, "create_task")
    coro_obj = dummy_coroutine()
    result = asyncio_compat.create_task(coro_obj)
    assert isinstance(result, asyncio.Task)
    assert spy_create_task.call_count == 1
    assert spy_create_task.call_args == mocker.call(coro_obj)


@pytest.mark.skipif(sys.version_info >= (3, 7), reason="Requires Python 3.6 or below")
async def test_create_task_36_compat(mocker, dummy_coroutine):
    spy_ensure_future = mocker.spy(asyncio, "ensure_future")
    coro_obj = dummy_coroutine()
    result = asyncio_compat.create_task(coro_obj)
    assert isinstance(result, asyncio.Task)
    assert spy_ensure_future.call_count == 1
    assert spy_ensure_future.call_args == mocker.call(coro_obj)


@pytest.mark.skipif(sys.version_info < (3, 5, 2), reason="Requires Python 3.5.2+")
async def test_create_future(mocker, event_loop):
    spy_create_future = mocker.spy(event_loop, "create_future")
    result = asyncio_compat.create_future(event_loop)
    assert isinstance(result, asyncio.Future)
    assert result._loop == event_loop  # Future.get_loop() only works in Python 3.7+
    assert spy_create_future.call_count == 1
    assert spy_create_future.call_args == mocker.call()


@pytest.mark.skipif(sys.version_info >= (3, 5, 1), reason="Requires Python 3.5.1 or below")
async def test_create_future_351_compat(mocker, event_loop):
    spy_future = mocker.spy(asyncio, "Future")
    result = asyncio_compat.create_future(event_loop)
    assert isinstance(result, spy_future.side_effect)  # spy_future.side_effect == asyncio.Future
    assert result._loop == event_loop  # Future.get_loop() only works in Python 3.7+
    assert spy_future.call_count == 1
    assert spy_future.call_args == mocker.call(loop=event_loop)
