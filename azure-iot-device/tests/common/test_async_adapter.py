# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
import inspect
import asyncio
import azure.iot.device.common.async_adapter as async_adapter

pytestmark = pytest.mark.asyncio


@pytest.fixture
def dummy_value():
    return 123


@pytest.fixture
def mock_function(mocker, dummy_value):
    mock_fn = mocker.MagicMock(return_value=dummy_value)
    mock_fn.__doc__ = "docstring"
    return mock_fn


class TestEmulateAsync(object):
    async def test_returns_coroutine(self, mock_function):
        async_fn = async_adapter.emulate_async(mock_function)
        assert inspect.iscoroutinefunction(async_fn)

    async def test_coroutine_has_input_function_docstring(self, mock_function):
        async_fn = async_adapter.emulate_async(mock_function)
        assert async_fn.__doc__ == mock_function.__doc__

    async def test_coroutine_returns_input_function_result(
        self, mocker, mock_function, dummy_value
    ):
        async_fn = async_adapter.emulate_async(mock_function)
        result = await async_fn(dummy_value)
        assert mock_function.call_count == 1
        assert mock_function.call_args == mocker.call(dummy_value)
        assert result == mock_function.return_value


class TestAwaitableCallback(object):
    async def test_calling_object_calls_input_function_and_returns_result(
        self, mocker, mock_function
    ):
        callback = async_adapter.AwaitableCallback(mock_function)
        result = callback()
        assert mock_function.call_count == 1
        assert mock_function.call_args == mocker.call()
        assert result == mock_function.return_value

    async def test_calling_object_completes_future(self, mock_function):
        callback = async_adapter.AwaitableCallback(mock_function)
        assert not callback.future.done()
        callback()
        await asyncio.sleep(0.1)  # wait to give time to complete the callback
        assert callback.future.done()

    async def test_can_be_called_using_args(self, mocker, mock_function):
        callback = async_adapter.AwaitableCallback(mock_function)
        result = callback(1, 2, 3)
        assert mock_function.call_count == 1
        assert mock_function.call_args == mocker.call(1, 2, 3)
        assert result == mock_function.return_value

    async def test_can_be_called_using_kwargs(self, mocker, mock_function):
        callback = async_adapter.AwaitableCallback(mock_function)
        result = callback(a=1, b=2, c=3)
        assert mock_function.call_count == 1
        assert mock_function.call_args == mocker.call(a=1, b=2, c=3)
        assert result == mock_function.return_value

    async def test_awaiting_completion_of_callback_returns_result(self, mock_function):
        callback = async_adapter.AwaitableCallback(mock_function)
        callback()
        assert await callback.completion() == mock_function.return_value
        assert callback.future.done()
