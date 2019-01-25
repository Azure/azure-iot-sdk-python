import pytest
import inspect
import azure.iot.common.async_adapter as async_adapter

pytestmark = pytest.mark.asyncio


@pytest.fixture
def dummy_value():
    return 123


@pytest.fixture
def mock_function(mocker, dummy_value):
    mock_fn = mocker.MagicMock(return_value=dummy_value)
    mock_fn.__doc__ = "docstring"
    return mock_fn


async def test_emulate_async(mocker, mock_function, dummy_value):
    async_fn = async_adapter.emulate_async(mock_function)
    result = await async_fn(dummy_value)
    assert inspect.iscoroutinefunction(async_fn)
    assert async_fn.__doc__ == mock_function.__doc__  # verify docstring carries over
    assert mock_function.call_count == 1
    assert mock_function.call_args == mocker.call(dummy_value)
    assert result == mock_function.return_value


class TestAwaitableCallback(object):
    async def test_callable_no_args(self, mocker, mock_function):
        callback = async_adapter.AwaitableCallback(mock_function)
        result = callback()
        assert mock_function.call_count == 1
        assert mock_function.call_args == mocker.call()
        assert result == mock_function.return_value

    async def test_callable_with_args(self, mocker, mock_function):
        callback = async_adapter.AwaitableCallback(mock_function)
        result = callback(1, 2, 3)
        assert mock_function.call_count == 1
        assert mock_function.call_args == mocker.call(1, 2, 3)
        assert result == mock_function.return_value

    async def test_callable_with_kwargs(self, mocker, mock_function):
        callback = async_adapter.AwaitableCallback(mock_function)
        result = callback(a=1, b=2, c=3)
        assert mock_function.call_count == 1
        assert mock_function.call_args == mocker.call(a=1, b=2, c=3)
        assert result == mock_function.return_value

    async def test_completion(self, mock_function):
        callback = async_adapter.AwaitableCallback(mock_function)
        callback()
        assert await callback.completion() == mock_function.return_value
        assert callback.future.done()
