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
def transport(mocker):
    mock_auth_provider = mocker.MagicMock()
    return MQTTTransportAsync(mock_auth_provider)


@pytest.fixture
def message():
    return Message("This is a message")


async def test_connect(mocker, transport, emulate_async_mock):
    async_call_mock = emulate_async_mock.return_value
    await transport.connect()
    # Assert the superclass connect method is made async
    assert emulate_async_mock.call_count == 1
    assert emulate_async_mock.call_args == mocker.call(super(MQTTTransportAsync, transport).connect)
    # Assert the async wrapped method is called
    assert async_call_mock.call_count == 1


async def test_disconnect(mocker, transport, emulate_async_mock):
    async_call_mock = emulate_async_mock.return_value
    await transport.disconnect()
    # Assert the superclass disconnect method is made async
    assert emulate_async_mock.call_count == 1
    assert emulate_async_mock.call_args == mocker.call(
        super(MQTTTransportAsync, transport).disconnect
    )
    # Assert the async wrapped method is called
    assert async_call_mock.call_count == 1


async def test_send_event(mocker, transport, emulate_async_mock, message):
    async_call_mock = emulate_async_mock.return_value
    await transport.send_event(message)
    # Assert the superclass send event method is made async
    assert emulate_async_mock.call_count == 1
    assert emulate_async_mock.call_args == mocker.call(
        super(MQTTTransportAsync, transport).send_event
    )
    # Assert the async wrapped method is called
    assert async_call_mock.call_count == 1
