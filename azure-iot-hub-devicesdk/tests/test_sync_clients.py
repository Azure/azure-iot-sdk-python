import pytest
from azure.iot.hub.devicesdk import DeviceClient, ModuleClient
from azure.iot.hub.devicesdk.transport.mqtt import MQTTTransport
from azure.iot.hub.devicesdk.transport.abstract_transport import AbstractTransport
from azure.iot.hub.devicesdk import Message
from azure.iot.hub.devicesdk.message_queue import MessageQueue

# Note that the auth_provider fixture is implicitly imported from tests/conftest.py


class FakeTransport(AbstractTransport):
    def __init__(self):
        pass

    def connect(self, callback):
        callback()

    def send_event(self, event, callback):
        callback()

    def send_output_event(self, event, callback):
        callback()

    def disconnect(self, callback):
        callback()

    def enable_feature(self, feature_name, callback=None, qos=1):
        callback()

    def disable_feature(self, feature_name, callback=None):
        callback()


@pytest.fixture
def transport(mocker):
    return mocker.MagicMock(wraps=FakeTransport())


class ClientSharedTests(object):
    client_class = None  # Will be set in child tests
    xfail_notimplemented = pytest.mark.xfail(raises=NotImplementedError, reason="Unimplemented")

    @pytest.mark.parametrize(
        "protocol,expected_transport",
        [
            pytest.param("mqtt", MQTTTransport, id="mqtt"),
            pytest.param("amqp", None, id="amqp", marks=xfail_notimplemented),
            pytest.param("http", None, id="http", marks=xfail_notimplemented),
        ],
    )
    def test_from_authentication_provider_instantiates_client(
        self, auth_provider, protocol, expected_transport
    ):
        client = self.client_class.from_authentication_provider(auth_provider, protocol)
        assert isinstance(client, self.client_class)
        assert isinstance(client._transport, expected_transport)
        assert client.state == "initial"

    @pytest.mark.parametrize("auth_provider", ["SymmetricKey"], ids=[""], indirect=True)
    @pytest.mark.parametrize(
        "protocol,expected_transport",
        [
            pytest.param("MQTT", MQTTTransport, id="ALL CAPS"),
            pytest.param("MqTt", MQTTTransport, id="mIxEd CaSe"),
        ],
    )
    def test_from_authentication_provider_boundary_case_transport_name(
        self, auth_provider, protocol, expected_transport
    ):
        client = self.client_class.from_authentication_provider(auth_provider, protocol)
        assert isinstance(client, self.client_class)
        assert isinstance(client._transport, expected_transport)

    @pytest.mark.parametrize("auth_provider", ["SymmetricKey"], ids=[""], indirect=True)
    def test_from_authentication_provider_bad_input_raises_error_transport_name(
        self, auth_provider
    ):
        with pytest.raises(ValueError):
            self.client_class.from_authentication_provider(auth_provider, "bad input")

    def test_connect_calls_transport(self, client, transport):
        client.connect()
        assert transport.connect.call_count == 1

    def test_disconnect_calls_transport(self, client, transport):
        client.disconnect()
        assert transport.disconnect.call_count == 1

    def test_send_event_calls_transport(self, client, transport):
        message = Message("this is a message")
        client.send_event(message)
        assert transport.send_event.call_count == 1
        assert transport.send_event.call_args[0][0] == message

    def test_send_event_calls_transport_wraps_data_in_message(self, client, transport):
        naked_string = "this is a message"
        client.send_event(naked_string)
        assert transport.send_event.call_count == 1
        sent_message = transport.send_event.call_args[0][0]
        assert isinstance(sent_message, Message)
        assert sent_message.data == naked_string


class TestModuleClient(ClientSharedTests):
    client_class = ModuleClient

    @pytest.fixture
    def client(self, transport):
        return ModuleClient(transport)

    def test_send_to_output_calls_transport(self, client, transport):
        message = Message("this is a message")
        output_name = "some_output"
        client.send_to_output(message, output_name)
        assert transport.send_output_event.call_count == 1
        assert transport.send_output_event.call_args[0][0] == message
        assert message.output_name == output_name

    def test_send_to_output_calls_transport_wraps_data_in_message(self, client, transport):
        naked_string = "this is a message"
        output_name = "some_output"
        client.send_to_output(naked_string, output_name)
        assert transport.send_output_event.call_count == 1
        sent_message = transport.send_output_event.call_args[0][0]
        assert isinstance(sent_message, Message)
        assert sent_message.data == naked_string

    def test_get_input_message_queue_returns_queue_from_queue_manager(self, client, mocker):
        input_name = "some_input"
        qm_spy = mocker.spy(client._queue_manager, "get_input_message_queue")
        input_queue = client.get_input_message_queue(input_name)
        assert isinstance(input_queue, MessageQueue)
        assert qm_spy.call_count == 1
        assert qm_spy.call_args[0] == (input_name,)


class TestDeviceClient(ClientSharedTests):
    client_class = DeviceClient

    @pytest.fixture
    def client(self, transport):
        return DeviceClient(transport)

    def test_get_c2d_message_queue_returns_queue_from_queue_manager(self, client, mocker):
        qm_spy = mocker.spy(client._queue_manager, "get_c2d_message_queue")
        c2d_queue = client.get_c2d_message_queue()
        assert isinstance(c2d_queue, MessageQueue)
        assert qm_spy.call_count == 1
        assert qm_spy.call_args[0] == ()
