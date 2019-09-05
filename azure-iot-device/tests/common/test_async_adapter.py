# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
import inspect
import asyncio
import logging
import azure.iot.device.common.async_adapter as async_adapter

logging.basicConfig(level=logging.INFO)
pytestmark = pytest.mark.asyncio


@pytest.fixture
def dummy_value():
    return 123


@pytest.fixture
def mock_function(mocker, dummy_value):
    mock_fn = mocker.MagicMock(return_value=dummy_value)
    mock_fn.__doc__ = "docstring"
    return mock_fn


@pytest.mark.describe("emulate_async()")
class TestEmulateAsync(object):
    @pytest.mark.it("Returns a coroutine function when given a function")
    async def test_returns_coroutine(self, mock_function):
        async_fn = async_adapter.emulate_async(mock_function)
        assert inspect.iscoroutinefunction(async_fn)

    @pytest.mark.it(
        "Returns a coroutine function that returns the result of the input function when called"
    )
    async def test_coroutine_returns_input_function_result(
        self, mocker, mock_function, dummy_value
    ):
        async_fn = async_adapter.emulate_async(mock_function)
        result = await async_fn(dummy_value)
        assert mock_function.call_count == 1
        assert mock_function.call_args == mocker.call(dummy_value)
        assert result == mock_function.return_value

    @pytest.mark.it("Copies the input function docstring to resulting coroutine function")
    async def test_coroutine_has_input_function_docstring(self, mock_function):
        async_fn = async_adapter.emulate_async(mock_function)
        assert async_fn.__doc__ == mock_function.__doc__

    @pytest.mark.it("Can be applied as a decorator")
    async def test_applied_as_decorator(self):

        # Define a function with emulate_async applied as a decorator
        @async_adapter.emulate_async
        def some_function():
            return "foo"

        # Call the function as a coroutine
        result = await some_function()
        assert result == "foo"


@pytest.mark.describe("AwaitableCallback")
class TestAwaitableCallback(object):
    @pytest.mark.it("Can be instantiated with no args")
    async def test_instantiates_without_return_arg_name(self):
        callback = async_adapter.AwaitableCallback()
        assert isinstance(callback, async_adapter.AwaitableCallback)

    @pytest.mark.it("Can be instantiated with a return_arg_name")
    async def test_instantiates_with_return_arg_name(self):
        callback = async_adapter.AwaitableCallback(return_arg_name="arg_name")
        assert isinstance(callback, async_adapter.AwaitableCallback)

    @pytest.mark.it("Raises a TypeError if return_arg_name is not a string")
    async def test_value_error_on_bad_return_arg_name(self):
        with pytest.raises(TypeError):
            async_adapter.AwaitableCallback(return_arg_name=1)

    @pytest.mark.it(
        "Completes the instance Future when a call is invoked on the instance (without return_arg_name)"
    )
    async def test_calling_object_completes_future(self):
        callback = async_adapter.AwaitableCallback()
        assert not callback.future.done()
        callback()
        await asyncio.sleep(0.1)  # wait to give time to complete the callback
        assert callback.future.done()
        assert not callback.future.exception()
        await callback.completion()

    @pytest.mark.it(
        "Completes the instance Future when a call is invoked on the instance (with return_arg_name)"
    )
    async def test_calling_object_completes_future_with_return_arg_name(
        self, fake_return_arg_value
    ):
        callback = async_adapter.AwaitableCallback(return_arg_name="arg_name")
        assert not callback.future.done()
        callback(arg_name=fake_return_arg_value)
        await asyncio.sleep(0.1)  # wait to give time to complete the callback
        assert callback.future.done()
        assert not callback.future.exception()
        assert await callback.completion() == fake_return_arg_value

    @pytest.mark.it(
        "Raises a TypeError when a call is invoked on the instance without the correct return argument (with return_arg_name)"
    )
    async def test_calling_object_raises_exception_if_return_arg_is_missing(
        self, fake_return_arg_value
    ):
        callback = async_adapter.AwaitableCallback(return_arg_name="arg_name")
        with pytest.raises(TypeError):
            callback()

    @pytest.mark.it(
        "Causes an error to be set on the instance Future when an error parameter is passed to the call (without return_arg_name)"
    )
    async def test_raises_error_without_return_arg_name(self, fake_error):
        callback = async_adapter.AwaitableCallback()
        assert not callback.future.done()
        callback(error=fake_error)
        await asyncio.sleep(0.1)  # wait to give time to complete the callback
        assert callback.future.done()
        assert callback.future.exception() == fake_error
        with pytest.raises(fake_error.__class__) as e_info:
            await callback.completion()
        assert e_info.value is fake_error

    @pytest.mark.it(
        "Causes an error to be set on the instance Future when an error parameter is passed to the call (with return_arg_name)"
    )
    async def test_raises_error_with_return_arg_name(self, fake_error):
        callback = async_adapter.AwaitableCallback(return_arg_name="arg_name")
        assert not callback.future.done()
        callback(error=fake_error)
        await asyncio.sleep(0.1)  # wait to give time to complete the callback
        assert callback.future.done()
        assert callback.future.exception() == fake_error
        with pytest.raises(fake_error.__class__) as e_info:
            await callback.completion()
        assert e_info.value is fake_error
