import pytest
import asyncio
from azure.iot.common import async_adapter
from azure.iot.hub.devicesdk.transport.mqtt import MQTTTransportAsync
from azure.iot.hub.devicesdk import Message

pytestmark = pytest.mark.asyncio


def complete_callback(*args):
    callback = args[len(args) - 1]  # callback is always the last argument
    # complete the given callback
    callback()
    # Return a future so the fn is awaitable
    f = asyncio.Future()
    f.set_result(None)
    return f


@pytest.fixture
def emulate_async_mock(mocker):
    m = mocker.patch.object(async_adapter, "emulate_async")
    m.return_value.side_effect = complete_callback
    return m


@pytest.fixture
def callback_mock(mocker):
    m = mocker.patch.object(async_adapter, "AwaitableCallback")
    f = asyncio.Future()
    f.set_result(None)  # Don't return a value from callback
    m.return_value.completion.return_value = f  # Completion is awaitable => returns future
    return m.return_value  # Instance of AwaitableCallback


@pytest.fixture
def transport(mocker):
    mock_auth_provider = mocker.MagicMock()
    return MQTTTransportAsync(mock_auth_provider)


@pytest.fixture
def message():
    return Message("This is a message")


class TestConnect(object):
    async def test_calls_async_emulated_transport_method(
        self, mocker, transport, emulate_async_mock
    ):
        async_call_mock = emulate_async_mock.return_value
        await transport.connect()
        # Assert the superclass connect method is made async
        assert emulate_async_mock.call_count == 1
        assert emulate_async_mock.call_args == mocker.call(
            super(MQTTTransportAsync, transport).connect
        )
        # Assert the async wrapped method is called
        assert async_call_mock.call_count == 1

    async def test_awaits_callback_from_transport(
        self, transport, emulate_async_mock, callback_mock
    ):
        await transport.connect()
        assert callback_mock.completion.call_count == 1


class TestDisconnect(object):
    async def test_calls_async_emulated_transport_method(
        self, mocker, transport, emulate_async_mock
    ):
        async_call_mock = emulate_async_mock.return_value
        await transport.disconnect()
        # Assert the superclass disconnect method is made async
        assert emulate_async_mock.call_count == 1
        assert emulate_async_mock.call_args == mocker.call(
            super(MQTTTransportAsync, transport).disconnect
        )
        # Assert the async wrapped method is called
        assert async_call_mock.call_count == 1

    async def test_awaits_callback_from_transport(
        self, transport, emulate_async_mock, callback_mock
    ):
        await transport.disconnect()
        assert callback_mock.completion.call_count == 1


class TestSendEvent(object):
    async def test_calls_async_emulated_transport_method(
        self, mocker, transport, emulate_async_mock, message
    ):
        async_call_mock = emulate_async_mock.return_value
        await transport.send_event(message)
        # Assert the superclass send event method is made async
        assert emulate_async_mock.call_count == 1
        assert emulate_async_mock.call_args == mocker.call(
            super(MQTTTransportAsync, transport).send_event
        )
        # Assert the async wrapped method is called
        assert async_call_mock.call_count == 1

    async def test_awaits_callback_from_transport(
        self, transport, emulate_async_mock, message, callback_mock
    ):
        await transport.send_event(message)
        assert callback_mock.completion.call_count == 1


class TestSendOutputEvent(object):
    async def test_calls_async_emulated_transport_method(
        self, mocker, transport, emulate_async_mock, message
    ):
        async_call_mock = emulate_async_mock.return_value
        await transport.send_output_event(message)
        # Assert the superclass send event method is made async
        assert emulate_async_mock.call_count == 1
        assert emulate_async_mock.call_args == mocker.call(
            super(MQTTTransportAsync, transport).send_output_event
        )
        # Assert the async wrapped method is called
        assert async_call_mock.call_count == 1

    async def test_awaits_callback_from_transport(
        self, transport, emulate_async_mock, message, callback_mock
    ):
        await transport.send_event(message)
        assert callback_mock.completion.call_count == 1
