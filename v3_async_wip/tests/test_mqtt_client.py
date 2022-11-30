# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

from v3_async_wip.mqtt_client import MQTTClient
from azure.iot.device.common import ProxyOptions
import paho.mqtt.client as mqtt
import pytest
import logging

logging.basicConfig(level=logging.DEBUG)

fake_hostname = "fake.hostname"
fake_ws_path = "/fake/path"
fake_device_id = "MyDevice"
fake_password = "fake_password"
fake_username = fake_hostname + "/" + fake_device_id
new_fake_password = "new fake password"
fake_topic = "fake_topic"
fake_payload = "some payload"
fake_cipher = "DHE-RSA-AES128-SHA"
fake_port = 443
fake_qos = 1
fake_mid = 52
fake_rc = 0
fake_success_rc = 0
fake_failed_rc = mqtt.MQTT_ERR_PROTOCOL
failed_connack_rc = mqtt.CONNACK_REFUSED_IDENTIFIER_REJECTED
fake_keepalive = 1234


# mapping of Paho connack rc codes to Error object classes
connack_return_codes = [
    {
        "name": "CONNACK_REFUSED_PROTOCOL_VERSION",
        "rc": mqtt.CONNACK_REFUSED_PROTOCOL_VERSION,
        # "error": errors.ProtocolClientError,
    },
    {
        "name": "CONNACK_REFUSED_IDENTIFIER_REJECTED",
        "rc": mqtt.CONNACK_REFUSED_IDENTIFIER_REJECTED,
        # "error": errors.ProtocolClientError,
    },
    {
        "name": "CONNACK_REFUSED_SERVER_UNAVAILABLE",
        "rc": mqtt.CONNACK_REFUSED_SERVER_UNAVAILABLE,
        # "error": errors.ConnectionFailedError,
    },
    {
        "name": "CONNACK_REFUSED_BAD_USERNAME_PASSWORD",
        "rc": mqtt.CONNACK_REFUSED_BAD_USERNAME_PASSWORD,
        # "error": errors.UnauthorizedError,
    },
    {
        "name": "CONNACK_REFUSED_NOT_AUTHORIZED",
        "rc": mqtt.CONNACK_REFUSED_NOT_AUTHORIZED,
        # "error": errors.UnauthorizedError,
    },
]


# mapping of Paho rc codes to Error object classes
operation_return_codes = [
    {
        "name": "MQTT_ERR_NOMEM",
        "rc": mqtt.MQTT_ERR_NOMEM,
        # "error": errors.ConnectionDroppedError
    },
    {
        "name": "MQTT_ERR_PROTOCOL",
        "rc": mqtt.MQTT_ERR_PROTOCOL,
        # "error": errors.ProtocolClientError,
    },
    {
        "name": "MQTT_ERR_INVAL",
        "rc": mqtt.MQTT_ERR_INVAL,
        # "error": errors.ProtocolClientError
    },
    {
        "name": "MQTT_ERR_NO_CONN",
        "rc": mqtt.MQTT_ERR_NO_CONN,
        # "error": errors.NoConnectionError
    },
    {
        "name": "MQTT_ERR_CONN_REFUSED",
        "rc": mqtt.MQTT_ERR_CONN_REFUSED,
        # "error": errors.ConnectionFailedError,
    },
    {
        "name": "MQTT_ERR_NOT_FOUND",
        "rc": mqtt.MQTT_ERR_NOT_FOUND,
        # "error": errors.ConnectionFailedError,
    },
    {
        "name": "MQTT_ERR_CONN_LOST",
        "rc": mqtt.MQTT_ERR_CONN_LOST,
        # "error": errors.ConnectionDroppedError,
    },
    {
        "name": "MQTT_ERR_TLS",
        "rc": mqtt.MQTT_ERR_TLS,
        # "error": errors.UnauthorizedError
    },
    {
        "name": "MQTT_ERR_PAYLOAD_SIZE",
        "rc": mqtt.MQTT_ERR_PAYLOAD_SIZE,
        # "error": errors.ProtocolClientError,
    },
    {
        "name": "MQTT_ERR_NOT_SUPPORTED",
        "rc": mqtt.MQTT_ERR_NOT_SUPPORTED,
        # "error": errors.ProtocolClientError,
    },
    {
        "name": "MQTT_ERR_AUTH",
        "rc": mqtt.MQTT_ERR_AUTH,
        # "error": errors.UnauthorizedError
    },
    {
        "name": "MQTT_ERR_ACL_DENIED",
        "rc": mqtt.MQTT_ERR_ACL_DENIED,
        # "error": errors.UnauthorizedError,
    },
    {
        "name": "MQTT_ERR_UNKNOWN",
        "rc": mqtt.MQTT_ERR_UNKNOWN,
        # "error": errors.ProtocolClientError
    },
    {
        "name": "MQTT_ERR_ERRNO",
        "rc": mqtt.MQTT_ERR_ERRNO,
        # "error": errors.ProtocolClientError
    },
    {
        "name": "MQTT_ERR_QUEUE_SIZE",
        "rc": mqtt.MQTT_ERR_QUEUE_SIZE,
        # "error": errors.ProtocolClientError,
    },
    {
        "name": "MQTT_ERR_KEEPALIVE",
        "rc": mqtt.MQTT_ERR_KEEPALIVE,
        # "error": errors.ConnectionDroppedError,
    },
]


@pytest.fixture
def mock_paho(mocker, fake_paho_thread):
    mock = mocker.patch.object(mqtt, "Client")
    mock_paho = mock.return_value
    mock_paho.subscribe = mocker.MagicMock(return_value=(fake_rc, fake_mid))
    mock_paho.unsubscribe = mocker.MagicMock(return_value=(fake_rc, fake_mid))
    mock_paho.publish = mocker.MagicMock(return_value=(fake_rc, fake_mid))

    def connect(*args, **kwargs):
        mock_paho.on_connect(client=mock_paho, userdata=None, flags=None, rc=0)
        return 0

    mock_paho.connect.side_effect = connect
    mock_paho.reconnect.return_value = 0
    mock_paho.disconnect.return_value = 0
    mock_paho._thread = fake_paho_thread
    return mock_paho


@pytest.fixture
async def client(mock_paho):
    # Implicitly imports the mocked Paho MQTT Client from mock_paho
    return MQTTClient(client_id=fake_device_id, hostname=fake_hostname, port=fake_port)


@pytest.mark.describe("MQTTClient - Instantiation")
class TestInstantiation(object):
    @pytest.fixture(
        params=["HTTP - No Auth", "HTTP - Auth", "SOCKS4", "SOCKS5 - No Auth", "SOCKS5 - Auth"]
    )
    def proxy_options(self, request):
        if "HTTP" in request.param:
            proxy_type = "HTTP"
        elif "SOCKS4" in request.param:
            proxy_type = "SOCKS4"
        else:
            proxy_type = "SOCKS5"

        if "No Auth" in request.param:
            proxy = ProxyOptions(proxy_type=proxy_type, proxy_addr="fake.address", proxy_port=1080)
        else:
            proxy = ProxyOptions(
                proxy_type=proxy_type,
                proxy_addr="fake.address",
                proxy_port=1080,
                proxy_username="fake_username",
                proxy_password="fake_password",
            )
        return proxy

    @pytest.fixture(params=["TCP", "WebSockets"])
    def transport(self, request):
        return request.param.lower()

    @pytest.mark.it("Stores the provided hostname value")
    def test_hostname(self, mocker):
        mocker.patch.object(mqtt, "Client")
        client = MQTTClient(client_id=fake_device_id, hostname=fake_hostname, port=fake_port)
        assert client._hostname == fake_hostname

    @pytest.mark.it("Stores the provided port value")
    def test_port(self, mocker):
        mocker.patch.object(mqtt, "Client")
        client = MQTTClient(client_id=fake_device_id, hostname=fake_hostname, port=fake_port)
        assert client._port == fake_port

    @pytest.mark.it("Stores the provided keepalive value (if provided)")
    def test_keepalive(self, mocker):
        mocker.patch.object(mqtt, "Client")
        client = MQTTClient(
            client_id=fake_device_id,
            hostname=fake_hostname,
            port=fake_port,
            keep_alive=fake_keepalive,
        )
        assert client._keep_alive == fake_keepalive

    @pytest.mark.it("Creates and stores an instance of the Paho MQTT Client")
    def test_instantiates_mqtt_client(self, mocker, transport):
        mock_paho_constructor = mocker.patch.object(mqtt, "Client")

        client = MQTTClient(
            client_id=fake_device_id,
            hostname=fake_hostname,
            port=fake_port,
            transport=transport,
        )

        assert mock_paho_constructor.call_count == 1
        assert mock_paho_constructor.call_args == mocker.call(
            client_id=fake_device_id,
            clean_session=False,
            protocol=mqtt.MQTTv311,
            transport=transport,
            reconnect_on_failure=False,
        )
        assert client._mqtt_client is mock_paho_constructor.return_value

    @pytest.mark.it("Uses the provided SSLContext with the Paho MQTT Client")
    def test_ssl_context(self, mocker, transport):
        mock_paho = mocker.patch.object(mqtt, "Client").return_value
        mock_ssl_context = mocker.MagicMock()

        MQTTClient(
            client_id=fake_device_id,
            hostname=fake_hostname,
            port=fake_port,
            transport=transport,
            ssl_context=mock_ssl_context,
        )

        assert mock_paho.tls_set_context.call_count == 1
        assert mock_paho.tls_set_context.call_args == mocker.call(context=mock_ssl_context)

    @pytest.mark.it(
        "Uses a default SSLContext with the Paho MQTT Client if no SSLContext is provided"
    )
    def test_ssl_context_default(self, mocker, transport):
        mock_paho = mocker.patch.object(mqtt, "Client").return_value

        MQTTClient(
            client_id=fake_device_id,
            hostname=fake_hostname,
            port=fake_port,
            transport=transport,
        )

        # NOTE: calling tls_set_context with None == using default context
        assert mock_paho.tls_set_context.call_count == 1
        assert mock_paho.tls_set_context.call_args == mocker.call(context=None)

    @pytest.mark.it("Sets proxy using the provided ProxyOptions with the Paho MQTT Client")
    def test_proxy_options(self, mocker, proxy_options, transport):
        mock_paho = mocker.patch.object(mqtt, "Client").return_value

        MQTTClient(
            client_id=fake_device_id,
            hostname=fake_hostname,
            port=fake_port,
            transport=transport,
            proxy_options=proxy_options,
        )

        # Verify proxy has been set
        assert mock_paho.proxy_set.call_count == 1
        assert mock_paho.proxy_set.call_args == mocker.call(
            proxy_type=proxy_options.proxy_type_socks,
            proxy_addr=proxy_options.proxy_address,
            proxy_port=proxy_options.proxy_port,
            proxy_username=proxy_options.proxy_username,
            proxy_password=proxy_options.proxy_password,
        )

    @pytest.mark.it("Does not set any proxy if no ProxyOptions is provided")
    def test_no_proxy_options(self, mocker, transport):
        mock_paho = mocker.patch.object(mqtt, "Client").return_value

        MQTTClient(
            client_id=fake_device_id,
            hostname=fake_hostname,
            port=fake_port,
            transport=transport,
        )

        # Proxy was not set
        assert mock_paho.proxy_set.call_count == 0

    @pytest.mark.it("Sets the websockets path using the provided value if using websockets")
    def test_ws_path(self, mocker):
        mock_paho = mocker.patch.object(mqtt, "Client").return_value

        MQTTClient(
            client_id=fake_device_id,
            hostname=fake_hostname,
            port=fake_port,
            transport="websockets",
            websockets_path=fake_ws_path,
        )

        # Websockets path was set
        assert mock_paho.ws_set_options.call_count == 1
        assert mock_paho.ws_set_options.call_args == mocker.call(path=fake_ws_path)

    @pytest.mark.it("Does not set the websocket path if it is not provided")
    def test_no_ws_path(self, mocker):
        mock_paho = mocker.patch.object(mqtt, "Client").return_value

        MQTTClient(
            client_id=fake_device_id, hostname=fake_hostname, port=fake_port, transport="websockets"
        )

        # Websockets path was not set
        assert mock_paho.ws_set_options.call_count == 0

    @pytest.mark.it("Does not set the websocket path if not using websockets")
    def test_ws_path_no_ws(self, mocker):
        mock_paho = mocker.patch.object(mqtt, "Client").return_value

        MQTTClient(
            client_id=fake_device_id,
            hostname=fake_hostname,
            port=fake_port,
            transport="tcp",
            websockets_path=fake_ws_path,
        )

        # Websockets path was not set
        assert mock_paho.ws_set_options.call_count == 0

    # TODO: May need public conditions tests (assuming they stay public)


@pytest.mark.describe("MQTTClient - .set_credentials()")
class TestSetCredentials(object):
    @pytest.mark.it("Sets a username only")
    def test_username(self, client, mock_paho, mocker):
        assert mock_paho.username_pw_set.call_count == 0

        client.set_credentials(fake_username)

        assert mock_paho.username_pw_set.call_count == 1
        assert mock_paho.username_pw_set.call_args == mocker.call(
            username=fake_username, password=None
        )

    @pytest.mark.it("Sets a username and password combination")
    def test_username_password(self, client, mock_paho, mocker):
        assert mock_paho.username_pw_set.call_count == 0

        client.set_credentials(fake_username, fake_password)

        assert mock_paho.username_pw_set.call_count == 1
        assert mock_paho.username_pw_set.call_args == mocker.call(
            username=fake_username, password=fake_password
        )


@pytest.mark.describe("MQTTClient - .connect()")
class TestConnect(object):
    @pytest.mark.it(
        "Invokes an MQTT connect via Paho using stored values, if not already connected"
    )
    async def test_not_connected(self, mocker, client, mock_paho):
        assert mock_paho.connect.call_count == 0

        await client.connect()

        assert mock_paho.call_count == 1
        assert mock_paho.call_args == mocker.call(
            host=client._hostname, port=client._port, keepalive=client._keep_alive
        )
