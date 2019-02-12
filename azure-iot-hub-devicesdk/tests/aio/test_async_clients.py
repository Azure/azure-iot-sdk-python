import pytest
import asyncio
import abc
import six
from azure.iot.hub.devicesdk.aio import DeviceClient, ModuleClient
from azure.iot.hub.devicesdk.transport.mqtt import MQTTTransportAsync
from azure.iot.hub.devicesdk.transport.abstract_transport import AbstractTransport
from azure.iot.hub.devicesdk import Message

# Note that the auth_provider fixture is implicitly imported from tests/conftest.py

pytestmark = pytest.mark.asyncio


async def completed_future():
    f = asyncio.Future()
    f.set_result = None
    return f


class FakeAsyncTransport(AbstractTransport):
    def __init__(self):
        pass

    async def connect(self):
        return await completed_future()

    async def send_event(self, event):
        return await completed_future()

    async def send_output_event(self, event):
        return await completed_future()

    async def disconnect(self):
        return await completed_future()


@pytest.fixture()
async def transport(mocker):
    m = mocker.MagicMock(wraps=FakeAsyncTransport())
    return m


class ClientSharedTests(object):
    client_class = None  # Will be set in child classes
    xfail_notimplemented = pytest.mark.xfail(raises=NotImplementedError, reason="Unimplemented")

    @pytest.mark.parametrize(
        "protocol,expected_transport",
        [
            pytest.param("mqtt", MQTTTransportAsync, id="mqtt"),
            pytest.param("amqp", None, id="amqp", marks=xfail_notimplemented),
            pytest.param("http", None, id="http", marks=xfail_notimplemented),
        ],
    )
    async def test_from_authentication_provider_instantiates_client(
        self, auth_provider, protocol, expected_transport
    ):
        client = await self.client_class.from_authentication_provider(auth_provider, protocol)
        assert isinstance(client, self.client_class)
        assert isinstance(client._transport, expected_transport)
        assert client.state == "initial"

    @pytest.mark.parametrize("auth_provider", ["SymmetricKey"], ids=[""], indirect=True)
    @pytest.mark.parametrize(
        "protocol,expected_transport",
        [
            pytest.param("MQTT", MQTTTransportAsync, id="ALL CAPS"),
            pytest.param("MqTt", MQTTTransportAsync, id="mIxEd CaSe"),
        ],
    )
    async def test_from_authentication_provider_boundary_case_transport_name(
        self, auth_provider, protocol, expected_transport
    ):
        client = await self.client_class.from_authentication_provider(auth_provider, protocol)
        assert isinstance(client, self.client_class)
        assert isinstance(client._transport, expected_transport)

    @pytest.mark.parametrize("auth_provider", ["SymmetricKey"], ids=[""], indirect=True)
    async def test_from_authentication_provider_bad_input_raises_error_transport_name(
        self, auth_provider
    ):
        with pytest.raises(ValueError):
            await self.client_class.from_authentication_provider(auth_provider, "bad input")

    async def test_connect_calls_transport(self, client, transport):
        await client.connect()
        assert transport.connect.call_count == 1

    async def test_disconnect_calls_transport(self, client, transport):
        await client.disconnect()
        assert transport.disconnect.call_count == 1

    async def test_send_event_calls_transport(self, client, transport):
        message = Message("this is a message")
        await client.send_event(message)
        assert transport.send_event.call_count == 1
        assert transport.send_event.call_args[0][0] == message

    async def test_send_event_calls_transport_wraps_data_in_message(self, client, transport):
        naked_string = "this is a message"
        await client.send_event(naked_string)
        assert transport.send_event.call_count == 1
        sent_message = transport.send_event.call_args[0][0]
        assert isinstance(sent_message, Message)
        assert sent_message.data == naked_string


class TestModuleClient(ClientSharedTests):
    client_class = ModuleClient

    @pytest.fixture
    def client(self, transport):
        return ModuleClient(transport)

    async def test_send_to_output_calls_transport(self, client, transport):
        message = Message("this is a message")
        output_name = "some_output"
        await client.send_to_output(message, output_name)
        assert transport.send_output_event.call_count == 1
        assert transport.send_output_event.call_args[0][0] == message
        assert message.output_name == output_name

    async def test_send_to_output_calls_transport_wraps_data_in_message(self, client, transport):
        naked_string = "this is a message"
        output_name = "some_output"
        await client.send_to_output(naked_string, output_name)
        assert transport.send_output_event.call_count == 1
        sent_message = transport.send_output_event.call_args[0][0]
        assert isinstance(sent_message, Message)
        assert sent_message.data == naked_string


class TestDeviceClient(ClientSharedTests):
    client_class = DeviceClient

    @pytest.fixture
    async def client(self, transport):
        return DeviceClient(transport)
