# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

from azure.iot.device.common.mqtt_transport import MQTTTransport, OperationManager, OperationType
from azure.iot.device.common.models.x509 import X509
from azure.iot.device.common import transport_exceptions as errors
from azure.iot.device.common import ProxyOptions
import paho.mqtt.client as mqtt
from paho.mqtt.packettypes import PacketTypes
import ssl
import copy
import pytest
import logging
import socket
import socks
import threading
import gc
import weakref

logging.basicConfig(level=logging.DEBUG)

fake_hostname = "fake.hostname"
fake_device_id = "MyDevice"
fake_password = "fake_password"
fake_username = fake_hostname + "/" + fake_device_id
new_fake_password = "new fake password"
fake_topic = "fake_topic"
fake_payload = "some payload"
fake_cipher = "DHE-RSA-AES128-SHA"
fake_qos = 1
fake_mid = 52
fake_rc = 0
successful_connack_reason_code = mqtt.convert_connack_rc_to_reason_code(mqtt.CONNACK_ACCEPTED)
failed_connack_reason_code = mqtt.convert_connack_rc_to_reason_code(
    mqtt.CONNACK_REFUSED_IDENTIFIER_REJECTED
)
successful_disconnect_reason_code = mqtt.convert_disconnect_error_code_to_reason_code(
    mqtt.MQTT_ERR_SUCCESS
)
failed_disconnect_reason_code = mqtt.convert_disconnect_error_code_to_reason_code(
    mqtt.MQTT_ERR_CONN_LOST
)
keep_alive_disconnect_reason_code = mqtt.convert_disconnect_error_code_to_reason_code(
    mqtt.MQTT_ERR_KEEPALIVE
)
fake_keepalive = 1234


# Paho-normalized CONNACK reasons and their corresponding SDK exception types
paho_connack_reason_error_cases = [
    {
        "reason_code": mqtt.convert_connack_rc_to_reason_code(
            mqtt.CONNACK_REFUSED_PROTOCOL_VERSION
        ),
        "error": errors.ProtocolClientError,
    },
    {
        "reason_code": mqtt.convert_connack_rc_to_reason_code(
            mqtt.CONNACK_REFUSED_IDENTIFIER_REJECTED
        ),
        "error": errors.ProtocolClientError,
    },
    {
        "reason_code": mqtt.convert_connack_rc_to_reason_code(
            mqtt.CONNACK_REFUSED_SERVER_UNAVAILABLE
        ),
        "error": errors.ConnectionFailedError,
    },
    {
        "reason_code": mqtt.convert_connack_rc_to_reason_code(
            mqtt.CONNACK_REFUSED_BAD_USERNAME_PASSWORD
        ),
        "error": errors.UnauthorizedError,
    },
    {
        "reason_code": mqtt.convert_connack_rc_to_reason_code(mqtt.CONNACK_REFUSED_NOT_AUTHORIZED),
        "error": errors.UnauthorizedError,
    },
]

paho_disconnect_reason_error_cases = [
    {
        "reason_code": failed_disconnect_reason_code,
        "error": errors.ConnectionDroppedError,
    },
    {
        "reason_code": keep_alive_disconnect_reason_code,
        "error": errors.ConnectionDroppedError,
    },
]


def trigger_on_connect(mqtt_client, reason_code=successful_connack_reason_code):
    mqtt_client.on_connect(
        client=mqtt_client,
        userdata=None,
        flags=mqtt.ConnectFlags(session_present=False),
        reason_code=reason_code,
        properties=mqtt.Properties(PacketTypes.CONNACK),
    )


def trigger_on_disconnect(mqtt_client, reason_code=successful_disconnect_reason_code):
    mqtt_client.on_disconnect(
        client=mqtt_client,
        userdata=None,
        disconnect_flags=mqtt.DisconnectFlags(is_disconnect_packet_from_server=False),
        reason_code=reason_code,
        properties=mqtt.Properties(PacketTypes.DISCONNECT),
    )


def trigger_on_subscribe(mqtt_client, mid, reason_codes=None):
    if reason_codes is None:
        reason_codes = [mqtt.ReasonCode(PacketTypes.SUBACK, identifier=fake_qos)]
    mqtt_client.on_subscribe(
        client=mqtt_client,
        userdata=None,
        mid=mid,
        reason_codes=reason_codes,
        properties=mqtt.Properties(PacketTypes.SUBACK),
    )


def trigger_on_unsubscribe(mqtt_client, mid):
    mqtt_client.on_unsubscribe(
        client=mqtt_client,
        userdata=None,
        mid=mid,
        reason_codes=[],
        properties=mqtt.Properties(PacketTypes.UNSUBACK),
    )


def register_publish(manager, mid, callback=None):
    manager.register_operation(mid=mid, callback=callback, operation_type=OperationType.PUBLISH)


def trigger_on_publish(mqtt_client, mid):
    mqtt_client.on_publish(
        client=mqtt_client,
        userdata=None,
        mid=mid,
        reason_code=mqtt.ReasonCode(PacketTypes.PUBACK),
        properties=mqtt.Properties(PacketTypes.PUBACK),
    )


# Paho library error codes and their corresponding SDK exception types
paho_error_code_cases = [
    {
        "name": "MQTT_ERR_PROTOCOL",
        "error_code": mqtt.MQTT_ERR_PROTOCOL,
        "error": errors.ProtocolClientError,
    },
    {
        "name": "MQTT_ERR_INVAL",
        "error_code": mqtt.MQTT_ERR_INVAL,
        "error": errors.ProtocolClientError,
    },
    {
        "name": "MQTT_ERR_NO_CONN",
        "error_code": mqtt.MQTT_ERR_NO_CONN,
        "error": errors.NoConnectionError,
    },
    {
        "name": "MQTT_ERR_CONN_REFUSED",
        "error_code": mqtt.MQTT_ERR_CONN_REFUSED,
        "error": errors.ConnectionFailedError,
    },
    {
        "name": "MQTT_ERR_NOT_FOUND",
        "error_code": mqtt.MQTT_ERR_NOT_FOUND,
        "error": errors.ConnectionFailedError,
    },
    {
        "name": "MQTT_ERR_CONN_LOST",
        "error_code": mqtt.MQTT_ERR_CONN_LOST,
        "error": errors.ConnectionDroppedError,
    },
    {"name": "MQTT_ERR_TLS", "error_code": mqtt.MQTT_ERR_TLS, "error": errors.UnauthorizedError},
    {
        "name": "MQTT_ERR_PAYLOAD_SIZE",
        "error_code": mqtt.MQTT_ERR_PAYLOAD_SIZE,
        "error": errors.ProtocolClientError,
    },
    {
        "name": "MQTT_ERR_NOT_SUPPORTED",
        "error_code": mqtt.MQTT_ERR_NOT_SUPPORTED,
        "error": errors.ProtocolClientError,
    },
    {"name": "MQTT_ERR_AUTH", "error_code": mqtt.MQTT_ERR_AUTH, "error": errors.UnauthorizedError},
    {
        "name": "MQTT_ERR_ACL_DENIED",
        "error_code": mqtt.MQTT_ERR_ACL_DENIED,
        "error": errors.UnauthorizedError,
    },
    {
        "name": "MQTT_ERR_UNKNOWN",
        "error_code": mqtt.MQTT_ERR_UNKNOWN,
        "error": errors.ProtocolClientError,
    },
    {
        "name": "MQTT_ERR_ERRNO",
        "error_code": mqtt.MQTT_ERR_ERRNO,
        "error": errors.ProtocolClientError,
    },
    {
        "name": "MQTT_ERR_QUEUE_SIZE",
        "error_code": mqtt.MQTT_ERR_QUEUE_SIZE,
        "error": errors.ProtocolClientError,
    },
    {
        "name": "MQTT_ERR_KEEPALIVE",
        "error_code": mqtt.MQTT_ERR_KEEPALIVE,
        "error": errors.ConnectionDroppedError,
    },
]

# During disconnect, MQTT_ERR_NO_CONN means the socket is already closed and is successful.
disconnect_error_code_cases = [
    case for case in paho_error_code_cases if case["error_code"] != mqtt.MQTT_ERR_NO_CONN
]

# For QoS 1 and QoS 2, Paho retains a publish that returns MQTT_ERR_NO_CONN.
publish_failure_code_cases = [
    case for case in paho_error_code_cases if case["error_code"] != mqtt.MQTT_ERR_NO_CONN
]


@pytest.fixture
def mock_mqtt_client(mocker):
    mock = mocker.patch.object(mqtt, "Client")
    mock_mqtt_client = mock.return_value
    mock_mqtt_client.subscribe = mocker.MagicMock(return_value=(fake_rc, fake_mid))
    mock_mqtt_client.unsubscribe = mocker.MagicMock(return_value=(fake_rc, fake_mid))
    message_info = mqtt.MQTTMessageInfo(fake_mid)
    message_info.rc = fake_rc
    mock_mqtt_client.publish = mocker.MagicMock(return_value=message_info)
    mock_mqtt_client.connect.return_value = 0
    mock_mqtt_client.reconnect.return_value = 0
    mock_mqtt_client.disconnect.return_value = 0
    mock_mqtt_client.loop_start.side_effect = lambda: (
        trigger_on_connect(mock_mqtt_client) or mqtt.MQTT_ERR_SUCCESS
    )
    mock_mqtt_client.loop_stop.return_value = 0
    return mock_mqtt_client


@pytest.fixture
def transport(mock_mqtt_client):
    # Implicitly imports the mocked Paho MQTT Client from mock_mqtt_client
    return MQTTTransport(client_id=fake_device_id, hostname=fake_hostname, username=fake_username)


@pytest.fixture
def collected_transport_weakref(mock_mqtt_client):
    transport = MQTTTransport(
        client_id=fake_device_id, hostname=fake_hostname, username=fake_username
    )
    transport_weakref = weakref.ref(transport)
    transport = None
    gc.collect(2)
    assert transport_weakref() is None
    return transport_weakref


@pytest.mark.describe("MQTTTransport - Instantiation")
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

    @pytest.mark.it("Creates an instance of the Paho MQTT Client")
    def test_instantiates_mqtt_client(self, mocker):
        mock_mqtt_client_constructor = mocker.patch.object(mqtt, "Client")

        MQTTTransport(client_id=fake_device_id, hostname=fake_hostname, username=fake_username)

        assert mock_mqtt_client_constructor.call_count == 1
        assert mock_mqtt_client_constructor.call_args == mocker.call(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=fake_device_id,
            clean_session=False,
            protocol=mqtt.MQTTv311,
            reconnect_on_failure=False,
        )

    @pytest.mark.it(
        "Creates an instance of the Paho MQTT Client using Websockets when websockets parameter is True"
    )
    def test_configures_mqtt_websockets(self, mocker):
        mock_mqtt_client_constructor = mocker.patch.object(mqtt, "Client")
        mock_mqtt_client = mock_mqtt_client_constructor.return_value

        MQTTTransport(
            client_id=fake_device_id,
            hostname=fake_hostname,
            username=fake_username,
            websockets=True,
        )

        assert mock_mqtt_client_constructor.call_count == 1
        assert mock_mqtt_client_constructor.call_args == mocker.call(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=fake_device_id,
            clean_session=False,
            protocol=mqtt.MQTTv311,
            transport="websockets",
            reconnect_on_failure=False,
        )

        # Verify websockets options have been set
        assert mock_mqtt_client.ws_set_options.call_count == 1
        assert mock_mqtt_client.ws_set_options.call_args == mocker.call(path="/$iothub/websocket")

    @pytest.mark.it(
        "Sets the proxy information on the client when the `proxy_options` parameter is provided"
    )
    def test_proxy_config(self, mocker, proxy_options):
        mock_mqtt_client_constructor = mocker.patch.object(mqtt, "Client")
        mock_mqtt_client = mock_mqtt_client_constructor.return_value

        MQTTTransport(
            client_id=fake_device_id,
            hostname=fake_hostname,
            username=fake_username,
            proxy_options=proxy_options,
        )

        # Verify proxy has been set
        assert mock_mqtt_client.proxy_set.call_count == 1
        assert mock_mqtt_client.proxy_set.call_args == mocker.call(
            proxy_type=proxy_options.proxy_type_socks,
            proxy_addr=proxy_options.proxy_address,
            proxy_port=proxy_options.proxy_port,
            proxy_username=proxy_options.proxy_username,
            proxy_password=proxy_options.proxy_password,
        )

    @pytest.mark.it(
        "Configures TLS/SSL context to use TLS 1.2, require certificates and check hostname"
    )
    def test_configures_tls_context(self, mocker):
        mock_mqtt_client = mocker.patch.object(mqtt, "Client").return_value
        mock_ssl_context_constructor = mocker.patch.object(ssl, "SSLContext")
        mock_ssl_context = mock_ssl_context_constructor.return_value

        MQTTTransport(client_id=fake_device_id, hostname=fake_hostname, username=fake_username)

        # Verify correctness of TLS/SSL Context
        assert mock_ssl_context_constructor.call_count == 1
        assert mock_ssl_context_constructor.call_args == mocker.call(
            protocol=ssl.PROTOCOL_TLS_CLIENT
        )
        assert mock_ssl_context.check_hostname is True
        assert mock_ssl_context.verify_mode == ssl.CERT_REQUIRED

        # Verify context has been set
        assert mock_mqtt_client.tls_set_context.call_count == 1
        assert mock_mqtt_client.tls_set_context.call_args == mocker.call(context=mock_ssl_context)

    @pytest.mark.it(
        "Configures TLS/SSL context using default certificates if protocol wrapper not instantiated with a server verification certificate"
    )
    def test_configures_tls_context_with_default_certs(self, mocker, mock_mqtt_client):
        mock_ssl_context_constructor = mocker.patch.object(ssl, "SSLContext")
        mock_ssl_context = mock_ssl_context_constructor.return_value

        MQTTTransport(client_id=fake_device_id, hostname=fake_hostname, username=fake_username)

        assert mock_ssl_context.load_default_certs.call_count == 1
        assert mock_ssl_context.load_default_certs.call_args == mocker.call()

    @pytest.mark.it(
        "Configures TLS/SSL context with provided server verification certificate if protocol wrapper instantiated with a server verification certificate"
    )
    def test_configures_tls_context_with_server_verification_certs(self, mocker, mock_mqtt_client):
        mock_ssl_context_constructor = mocker.patch.object(ssl, "SSLContext")
        mock_ssl_context = mock_ssl_context_constructor.return_value
        server_verification_cert = "dummy_certificate"

        MQTTTransport(
            client_id=fake_device_id,
            hostname=fake_hostname,
            username=fake_username,
            server_verification_cert=server_verification_cert,
        )

        assert mock_ssl_context.load_verify_locations.call_count == 1
        assert mock_ssl_context.load_verify_locations.call_args == mocker.call(
            cadata=server_verification_cert
        )

    @pytest.mark.it(
        "Configures TLS/SSL context with provided cipher if present during instantiation"
    )
    def test_configures_tls_context_with_cipher(self, mocker, mock_mqtt_client):
        mock_ssl_context_constructor = mocker.patch.object(ssl, "SSLContext")
        mock_ssl_context = mock_ssl_context_constructor.return_value

        MQTTTransport(
            client_id=fake_device_id,
            hostname=fake_hostname,
            username=fake_username,
            cipher=fake_cipher,
        )

        assert mock_ssl_context.set_ciphers.call_count == 1
        assert mock_ssl_context.set_ciphers.call_args == mocker.call(fake_cipher)

    @pytest.mark.it("Configures TLS/SSL context with client-provided-certificate-chain like x509")
    def test_configures_tls_context_with_client_provided_certificate_chain(
        self, mocker, mock_mqtt_client
    ):
        mock_ssl_context_constructor = mocker.patch.object(ssl, "SSLContext")
        mock_ssl_context = mock_ssl_context_constructor.return_value
        fake_client_cert = X509("fake_cert_file", "fake_key_file", "fake pass phrase")

        MQTTTransport(
            client_id=fake_device_id,
            hostname=fake_hostname,
            username=fake_username,
            x509_cert=fake_client_cert,
        )

        assert mock_ssl_context.load_default_certs.call_count == 1
        assert mock_ssl_context.load_cert_chain.call_count == 1
        assert mock_ssl_context.load_cert_chain.call_args == mocker.call(
            fake_client_cert.certificate_file,
            fake_client_cert.key_file,
            fake_client_cert.pass_phrase,
        )

    @pytest.mark.it("Sets Paho MQTT Client callbacks")
    def test_sets_paho_callbacks(self, mocker):
        mock_mqtt_client = mocker.patch.object(mqtt, "Client").return_value

        MQTTTransport(client_id=fake_device_id, hostname=fake_hostname, username=fake_username)

        assert callable(mock_mqtt_client.on_connect)
        assert callable(mock_mqtt_client.on_disconnect)
        assert callable(mock_mqtt_client.on_subscribe)
        assert callable(mock_mqtt_client.on_unsubscribe)
        assert callable(mock_mqtt_client.on_publish)
        assert callable(mock_mqtt_client.on_message)

    @pytest.mark.it("Initializes event handlers to 'None'")
    def test_handler_callbacks_set_to_none(self, mocker):
        mocker.patch.object(mqtt, "Client")

        transport = MQTTTransport(
            client_id=fake_device_id, hostname=fake_hostname, username=fake_username
        )

        assert transport.on_mqtt_disconnected_handler is None
        assert transport.on_mqtt_message_received_handler is None

    @pytest.mark.it("Initializes internal operation tracking structures")
    def test_operation_infrastructure_set_up(self, mocker):
        transport = MQTTTransport(
            client_id=fake_device_id, hostname=fake_hostname, username=fake_username
        )
        assert transport._op_manager._pending_operations == {}
        assert transport._op_manager._unknown_operation_completions == {}

    @pytest.mark.it("Does not configure Paho reconnect delay or manual acknowledgements")
    def test_does_not_set_reconnect_interval(self, transport, mock_mqtt_client):
        assert mock_mqtt_client.reconnect_delay_set.call_count == 0
        assert mock_mqtt_client.manual_ack_set.call_count == 0


@pytest.mark.describe("MQTTTransport - .shutdown()")
class TestShutdown(object):
    @pytest.mark.it("Disconnects Paho and stops its network loop")
    def test_disconnects_and_stops_network_loop(self, mocker, mock_mqtt_client, transport):
        transport.shutdown()

        assert mock_mqtt_client.disconnect.call_count == 1
        assert mock_mqtt_client.disconnect.call_args == mocker.call()
        assert mock_mqtt_client.loop_stop.call_count == 1
        assert mock_mqtt_client.loop_stop.call_args == mocker.call()

    @pytest.mark.it("Does NOT trigger the on_disconnect handler upon disconnect")
    def test_does_not_trigger_handler(self, mocker, mock_mqtt_client, transport):
        mock_disconnect_handler = mocker.MagicMock()
        mock_mqtt_client.on_disconnect = mock_disconnect_handler
        transport.shutdown()
        assert mock_mqtt_client.on_disconnect is None
        assert mock_disconnect_handler.call_count == 0

    @pytest.mark.it("Stops the network loop and allows any Exception from disconnect to propagate")
    def test_stops_loop_if_disconnect_raises(
        self, mock_mqtt_client, transport, arbitrary_exception
    ):
        mock_mqtt_client.disconnect.side_effect = arbitrary_exception

        with pytest.raises(type(arbitrary_exception)) as e_info:
            transport.shutdown()

        assert e_info.value is arbitrary_exception
        assert mock_mqtt_client.loop_stop.call_count == 1

    @pytest.mark.it(
        "Completes tracked operations as cancelled and allows any Exception from teardown to propagate"
    )
    def test_completes_tracked_operations_if_teardown_raises(
        self, mocker, mock_mqtt_client, transport, arbitrary_exception
    ):
        callback = mocker.MagicMock()
        transport.subscribe(fake_topic, callback=callback)
        mock_mqtt_client.disconnect.side_effect = arbitrary_exception

        with pytest.raises(type(arbitrary_exception)):
            transport.shutdown()

        assert callback.call_count == 1
        assert callback.call_args == mocker.call(cancelled=True)


class ArbitraryConnectException(Exception):
    pass


@pytest.mark.describe("MQTTTransport - .connect()")
class TestConnect(object):
    @pytest.mark.it("Joins a previously started network loop before connecting")
    def test_joins_prior_network_loop_before_connect(self, mocker, mock_mqtt_client, transport):
        call_order = mocker.MagicMock()
        call_order.attach_mock(mock_mqtt_client.loop_stop, "loop_stop")
        call_order.attach_mock(mock_mqtt_client.connect, "connect")

        transport.connect(fake_password)

        assert call_order.mock_calls[:2] == [
            mocker.call.loop_stop(),
            mocker.call.connect(host=fake_hostname, port=8883, keepalive=None),
        ]

    @pytest.mark.it("Uses the stored username and provided password for Paho credentials")
    def test_use_provided_password(self, mocker, mock_mqtt_client, transport):
        transport.connect(fake_password)

        assert mock_mqtt_client.username_pw_set.call_count == 1
        assert mock_mqtt_client.username_pw_set.call_args == mocker.call(
            username=transport._username, password=fake_password
        )

    @pytest.mark.it(
        "Uses the stored username without a password for Paho credentials, if password is not provided"
    )
    def test_use_no_password(self, mocker, mock_mqtt_client, transport):
        transport.connect()

        assert mock_mqtt_client.username_pw_set.call_count == 1
        assert mock_mqtt_client.username_pw_set.call_args == mocker.call(
            username=transport._username, password=None
        )

    @pytest.mark.it("Initiates MQTT connect via Paho")
    @pytest.mark.parametrize(
        "password",
        [
            pytest.param(fake_password, id="Password provided"),
            pytest.param(None, id="No password provided"),
        ],
    )
    @pytest.mark.parametrize(
        "websockets,port",
        [
            pytest.param(False, 8883, id="Not using websockets"),
            pytest.param(True, 443, id="Using websockets"),
        ],
    )
    def test_calls_paho_connect(
        self, mocker, mock_mqtt_client, transport, password, websockets, port
    ):

        # We don't want to use a special fixture for websockets, so instead we are overriding the attribute below.
        # However, we want to assert that this value is not undefined. For instance, the self._websockets convention private attribute
        # could be changed to self._websockets1, and all our tests would still pass without the below assert statement.
        assert transport._websockets is False

        transport._websockets = websockets
        fake_keepalive = 900
        transport._keep_alive = fake_keepalive

        transport.connect(password)

        assert mock_mqtt_client.connect.call_count == 1
        assert mock_mqtt_client.connect.call_args == mocker.call(
            host=fake_hostname, port=port, keepalive=fake_keepalive
        )

    @pytest.mark.it("Starts MQTT Network Loop")
    @pytest.mark.parametrize(
        "password",
        [
            pytest.param(fake_password, id="Password provided"),
            pytest.param(None, id="No password provided"),
        ],
    )
    def test_calls_loop_start(self, mocker, mock_mqtt_client, transport, password):
        transport.connect(password)

        assert mock_mqtt_client.loop_start.call_count == 1
        assert mock_mqtt_client.loop_start.call_args == mocker.call()

    @pytest.mark.it("Raises a ProtocolClientError if Paho connect raises an unexpected Exception")
    def test_client_raises_unexpected_error(
        self, mocker, mock_mqtt_client, transport, arbitrary_exception
    ):
        mock_mqtt_client.connect.side_effect = arbitrary_exception
        with pytest.raises(errors.ProtocolClientError) as e_info:
            transport.connect(fake_password)
        assert e_info.value.__cause__ is arbitrary_exception

    @pytest.mark.it(
        "Raises a ConnectionFailedError if Paho connect raises a socket.error Exception"
    )
    def test_client_raises_socket_error(
        self, mocker, mock_mqtt_client, transport, arbitrary_exception
    ):
        socket_error = socket.error()
        mock_mqtt_client.connect.side_effect = socket_error
        with pytest.raises(errors.ConnectionFailedError) as e_info:
            transport.connect(fake_password)
        assert e_info.value.__cause__ is socket_error

    @pytest.mark.it(
        "Raises a TlsExchangeAuthError if Paho connect raises a socket.error of type SSLCertVerificationError Exception"
    )
    def test_client_raises_socket_tls_auth_error(
        self, mocker, mock_mqtt_client, transport, arbitrary_exception
    ):
        socket_error = ssl.SSLError("socket error", "CERTIFICATE_VERIFY_FAILED")
        mock_mqtt_client.connect.side_effect = socket_error
        with pytest.raises(errors.TlsExchangeAuthError) as e_info:
            transport.connect(fake_password)
        assert e_info.value.__cause__ is socket_error
        print(e_info.value.__cause__.strerror)

    @pytest.mark.it(
        "Raises a ProtocolProxyError if Paho connect raises a socket error or a ProxyError exception"
    )
    def test_client_raises_socket_error_or_proxy_error_as_proxy_error(
        self, mocker, mock_mqtt_client, transport, arbitrary_exception
    ):
        socks_error = socks.SOCKS5Error(
            "it is a sock 5 error", socket_err="a general SOCKS5Error error"
        )
        mock_mqtt_client.connect.side_effect = socks_error
        with pytest.raises(errors.ProtocolProxyError) as e_info:
            transport.connect(fake_password)
        assert e_info.value.__cause__ is socks_error
        print(e_info.value.__cause__.strerror)

    @pytest.mark.it(
        "Raises a UnauthorizedError if Paho connect raises a socket error or a ProxyError exception"
    )
    def test_client_raises_socket_error_or_proxy_error_as_unauthorized_error(
        self, mocker, mock_mqtt_client, transport, arbitrary_exception
    ):
        socks_error = socks.SOCKS5AuthError(
            "it is a sock 5 auth error", socket_err="an auth SOCKS5Error error"
        )
        mock_mqtt_client.connect.side_effect = socks_error
        with pytest.raises(errors.UnauthorizedError) as e_info:
            transport.connect(fake_password)
        assert e_info.value.__cause__ is socks_error
        print(e_info.value.__cause__.strerror)

    @pytest.mark.it("Allows any BaseExceptions raised in Paho connect to propagate")
    def test_client_raises_base_exception(
        self, mock_mqtt_client, transport, arbitrary_base_exception
    ):
        mock_mqtt_client.connect.side_effect = arbitrary_base_exception
        with pytest.raises(arbitrary_base_exception.__class__) as e_info:
            transport.connect(fake_password)
        assert e_info.value is arbitrary_base_exception

    # NOTE: this test tests all mapped Paho error codes, even ones that shouldn't be
    # possible on a connect operation.
    @pytest.mark.it("Raises a custom Exception if Paho connect returns an error code")
    @pytest.mark.parametrize(
        "error_case",
        paho_error_code_cases,
        ids=[
            "{}->{}".format(case["name"], case["error"].__name__) for case in paho_error_code_cases
        ],
    )
    def test_client_returns_error_code(self, mocker, mock_mqtt_client, transport, error_case):
        mock_mqtt_client.connect.return_value = error_case["error_code"]
        with pytest.raises(error_case["error"]):
            transport.connect(fake_password)
        assert mock_mqtt_client.disconnect.call_count == 1

    @pytest.fixture(
        params=[
            ArbitraryConnectException(),
            socket.error(),
            ssl.SSLError("socket error", "CERTIFICATE_VERIFY_FAILED"),
            socks.SOCKS5Error("it is a sock 5 error", socket_err="a general SOCKS5Error error"),
            socks.SOCKS5AuthError(
                "it is a sock 5 auth error", socket_err="an auth SOCKS5Error error"
            ),
        ],
        ids=[
            "ArbitraryConnectException",
            "socket.error",
            "ssl.SSLError",
            "socks.SOCKS5Error",
            "socks.SOCKS5AuthError",
        ],
    )
    def connect_exception(self, request):
        return request.param

    @pytest.mark.it("Disconnects Paho and stops its network loop if connect raises an Exception")
    def test_cleans_up_on_exception(self, mock_mqtt_client, transport, connect_exception):
        mock_mqtt_client.connect.side_effect = connect_exception
        with pytest.raises(Exception):
            transport.connect(fake_password)
        assert mock_mqtt_client.disconnect.call_count == 1
        assert mock_mqtt_client.loop_stop.call_count == 2

    @pytest.mark.parametrize(
        "connect_failure, expected_error",
        [
            pytest.param("socket error", errors.ConnectionFailedError),
            pytest.param("proxy auth error", errors.UnauthorizedError),
            pytest.param("connect error code", errors.ProtocolClientError),
            pytest.param("loop start error code", errors.ProtocolClientError),
        ],
    )
    @pytest.mark.parametrize(
        "cleanup_failure",
        [pytest.param("disconnect"), pytest.param("loop_stop")],
    )
    @pytest.mark.it("Preserves a connect error if cleanup raises an Exception")
    def test_connect_error_preserved_if_cleanup_raises(
        self,
        mock_mqtt_client,
        transport,
        arbitrary_exception,
        connect_failure,
        expected_error,
        cleanup_failure,
    ):
        if connect_failure == "socket error":
            mock_mqtt_client.connect.side_effect = socket.error()
        elif connect_failure == "proxy auth error":
            mock_mqtt_client.connect.side_effect = socks.SOCKS5AuthError(
                "authentication failed", socket_err="authentication failed"
            )
        elif connect_failure == "connect error code":
            mock_mqtt_client.connect.return_value = mqtt.MQTT_ERR_INVAL
        else:
            mock_mqtt_client.loop_start.side_effect = None
            mock_mqtt_client.loop_start.return_value = mqtt.MQTT_ERR_INVAL

        if cleanup_failure == "disconnect":
            mock_mqtt_client.disconnect.side_effect = arbitrary_exception
        else:
            mock_mqtt_client.loop_stop.side_effect = [None, arbitrary_exception]

        with pytest.raises(expected_error) as e_info:
            transport.connect(fake_password)

        assert type(e_info.value) is expected_error
        assert mock_mqtt_client.on_disconnect is not None

    @pytest.mark.it(
        "Raises a ProtocolClientError and cleans up if Paho loop_start() returns an error code"
    )
    def test_loop_start_returns_error(self, mock_mqtt_client, transport):
        mock_mqtt_client.loop_start.side_effect = None
        mock_mqtt_client.loop_start.return_value = mqtt.MQTT_ERR_INVAL

        with pytest.raises(errors.ProtocolClientError):
            transport.connect(fake_password)

        assert mock_mqtt_client.disconnect.call_count == 1
        assert mock_mqtt_client.loop_stop.call_count == 2

    @pytest.mark.it(
        "Raises a ProtocolClientError and cleans up if Paho loop_start() raises an Exception"
    )
    def test_loop_start_raises(self, mock_mqtt_client, transport, arbitrary_exception):
        mock_mqtt_client.loop_start.side_effect = arbitrary_exception

        with pytest.raises(errors.ProtocolClientError) as e_info:
            transport.connect(fake_password)

        assert e_info.value.__cause__ is arbitrary_exception
        assert mock_mqtt_client.disconnect.call_count == 1
        assert mock_mqtt_client.loop_stop.call_count == 2
        assert mock_mqtt_client.on_disconnect is not None

    @pytest.mark.it(
        "Raises a ProtocolClientError and replaces a Paho client left unusable by a network-thread start failure"
    )
    def test_loop_start_thread_failure_replaces_client(self, mocker):
        transport = MQTTTransport(
            client_id=fake_device_id,
            hostname=fake_hostname,
            username=fake_username,
            keep_alive=fake_keepalive,
        )
        failed_client = transport._mqtt_client
        publish_callback = mocker.MagicMock()
        transport.publish(fake_topic, fake_payload, qos=1, callback=publish_callback)
        failed_client_socket, failed_server_socket = socket.socketpair()
        mocker.patch.object(failed_client, "_create_socket", return_value=failed_client_socket)
        start_error = RuntimeError("cannot start network thread")
        mocker.patch.object(threading.Thread, "start", side_effect=start_error)

        try:
            with pytest.raises(errors.ProtocolClientError) as e_info:
                transport.connect(fake_password)
        finally:
            failed_server_socket.close()

        assert e_info.value.__cause__ is start_error
        assert failed_client_socket.fileno() == -1
        assert transport._mqtt_client is not failed_client
        assert transport._mqtt_client.on_connect is not None
        assert transport._mqtt_client.on_disconnect is not None
        assert publish_callback.call_count == 1
        assert publish_callback.call_args == mocker.call(cancelled=True)
        assert transport._op_manager._pending_operations == {}

    @pytest.mark.it("Waits for CONNACK before returning")
    def test_waits_for_connack(self, mock_mqtt_client, transport, run_in_daemon_thread, poll_until):
        mock_mqtt_client.loop_start.side_effect = None
        mock_mqtt_client.loop_start.return_value = mqtt.MQTT_ERR_SUCCESS

        connect_future = run_in_daemon_thread(transport.connect, fake_password)
        poll_until(lambda: mock_mqtt_client.loop_start.call_count == 1, timeout=1)

        assert not connect_future.done()

        trigger_on_connect(mock_mqtt_client)
        connect_future.result(timeout=1)

    @pytest.mark.it("Raises the mapped error from a failed CONNACK")
    def test_failed_connack_raises(
        self, mock_mqtt_client, transport, run_in_daemon_thread, poll_until
    ):
        mock_mqtt_client.loop_start.side_effect = None
        mock_mqtt_client.loop_start.return_value = mqtt.MQTT_ERR_SUCCESS
        connect_future = run_in_daemon_thread(transport.connect, fake_password)
        poll_until(lambda: mock_mqtt_client.loop_start.call_count == 1, timeout=1)

        trigger_on_connect(mock_mqtt_client, reason_code=failed_connack_reason_code)

        with pytest.raises(errors.ProtocolClientError):
            connect_future.result(timeout=1)

        assert mock_mqtt_client.disconnect.call_count == 1
        assert mock_mqtt_client.loop_stop.call_count == 2

    @pytest.mark.it("Raises ConnectionFailedError if the connection closes before CONNACK")
    def test_disconnect_before_connack_raises(
        self, mocker, mock_mqtt_client, transport, run_in_daemon_thread, poll_until
    ):
        mock_mqtt_client.loop_start.side_effect = None
        mock_mqtt_client.loop_start.return_value = mqtt.MQTT_ERR_SUCCESS
        disconnected_handler = mocker.MagicMock()
        transport.on_mqtt_disconnected_handler = disconnected_handler
        connect_future = run_in_daemon_thread(transport.connect, fake_password)
        poll_until(lambda: mock_mqtt_client.loop_start.call_count == 1, timeout=1)

        trigger_on_disconnect(mock_mqtt_client, reason_code=failed_disconnect_reason_code)

        with pytest.raises(errors.ConnectionFailedError):
            connect_future.result(timeout=1)

        assert disconnected_handler.call_count == 0
        assert mock_mqtt_client.disconnect.call_count == 1
        assert mock_mqtt_client.loop_stop.call_count == 2

    @pytest.mark.it("Raises ConnectionDroppedError if the connection drops before connect returns")
    def test_disconnect_after_connack_before_return_raises(
        self, mocker, mock_mqtt_client, transport
    ):
        disconnected_handler = mocker.MagicMock()
        transport.on_mqtt_disconnected_handler = disconnected_handler

        def connect_then_disconnect():
            trigger_on_connect(mock_mqtt_client)
            trigger_on_disconnect(mock_mqtt_client, reason_code=failed_disconnect_reason_code)
            return mqtt.MQTT_ERR_SUCCESS

        mock_mqtt_client.loop_start.side_effect = connect_then_disconnect

        with pytest.raises(errors.ConnectionDroppedError):
            transport.connect(fake_password)

        assert disconnected_handler.call_count == 0
        assert mock_mqtt_client.disconnect.call_count == 1
        assert mock_mqtt_client.loop_stop.call_count == 2

    @pytest.mark.it("Preserves a rejected CONNACK if disconnection follows before connect returns")
    def test_failed_connack_then_disconnect_preserves_connack_error(
        self, mock_mqtt_client, transport
    ):
        def reject_then_disconnect():
            trigger_on_connect(mock_mqtt_client, reason_code=failed_connack_reason_code)
            trigger_on_disconnect(mock_mqtt_client, reason_code=failed_disconnect_reason_code)
            return mqtt.MQTT_ERR_SUCCESS

        mock_mqtt_client.loop_start.side_effect = reject_then_disconnect

        with pytest.raises(errors.ProtocolClientError):
            transport.connect(fake_password)

    @pytest.mark.parametrize(
        "reason_code",
        [successful_connack_reason_code, failed_connack_reason_code],
        ids=["Accepted CONNACK", "Rejected CONNACK"],
    )
    @pytest.mark.it("Preserves a pre-CONNACK disconnection if CONNACK follows")
    def test_disconnect_then_connack_preserves_connection_failure(
        self, mock_mqtt_client, transport, reason_code
    ):
        def disconnect_then_connack():
            trigger_on_disconnect(mock_mqtt_client, reason_code=failed_disconnect_reason_code)
            trigger_on_connect(mock_mqtt_client, reason_code=reason_code)
            return mqtt.MQTT_ERR_SUCCESS

        mock_mqtt_client.loop_start.side_effect = disconnect_then_connack

        with pytest.raises(errors.ConnectionFailedError) as e_info:
            transport.connect(fake_password)

        assert type(e_info.value) is errors.ConnectionFailedError

    @pytest.mark.parametrize(
        "terminal_outcome, expected_error",
        [
            pytest.param("rejected_connack", errors.ProtocolClientError, id="Rejected CONNACK"),
            pytest.param(
                "disconnect_before_connack",
                errors.ConnectionFailedError,
                id="Disconnect before CONNACK",
            ),
            pytest.param(
                "disconnect_after_connack",
                errors.ConnectionDroppedError,
                id="Disconnect after accepted CONNACK",
            ),
        ],
    )
    @pytest.mark.it("Preserves a terminal connection error if cleanup raises an Exception")
    def test_terminal_error_preserved_if_cleanup_raises(
        self,
        mock_mqtt_client,
        transport,
        arbitrary_exception,
        terminal_outcome,
        expected_error,
    ):
        def fail_during_loop_start():
            if terminal_outcome == "rejected_connack":
                trigger_on_connect(mock_mqtt_client, reason_code=failed_connack_reason_code)
            elif terminal_outcome == "disconnect_before_connack":
                trigger_on_disconnect(mock_mqtt_client, reason_code=failed_disconnect_reason_code)
            else:
                trigger_on_connect(mock_mqtt_client)
                trigger_on_disconnect(mock_mqtt_client, reason_code=failed_disconnect_reason_code)
            return mqtt.MQTT_ERR_SUCCESS

        mock_mqtt_client.loop_start.side_effect = fail_during_loop_start
        mock_mqtt_client.disconnect.side_effect = arbitrary_exception

        with pytest.raises(expected_error) as e_info:
            transport.connect(fake_password)

        assert type(e_info.value) is expected_error

    @pytest.mark.it("Raises ConnectionTimeoutError and cleans up if CONNACK times out")
    def test_connack_timeout(self, mock_mqtt_client, transport):
        mock_mqtt_client.loop_start.side_effect = None
        mock_mqtt_client.loop_start.return_value = mqtt.MQTT_ERR_SUCCESS

        with pytest.raises(errors.ConnectionTimeoutError):
            transport.connect(fake_password, timeout=0.01)

        assert mock_mqtt_client.disconnect.call_count == 1
        assert mock_mqtt_client.loop_stop.call_count == 2

    @pytest.mark.it("Preserves pending publish tracking when a connection attempt times out")
    def test_connack_timeout_preserves_publish_tracking(self, mocker, mock_mqtt_client, transport):
        publish_callback = mocker.MagicMock()
        transport.publish(fake_topic, fake_payload, callback=publish_callback)
        mock_mqtt_client.loop_start.side_effect = None
        mock_mqtt_client.loop_start.return_value = mqtt.MQTT_ERR_SUCCESS

        with pytest.raises(errors.ConnectionTimeoutError):
            transport.connect(fake_password, timeout=0.01)

        assert publish_callback.call_count == 0

        trigger_on_publish(mock_mqtt_client, fake_mid)

        assert publish_callback.call_count == 1
        assert publish_callback.call_args == mocker.call()

    @pytest.mark.it("Times out immediately with a zero timeout if no CONNACK was received")
    def test_zero_timeout_without_connack(self, mock_mqtt_client, transport):
        mock_mqtt_client.loop_start.side_effect = None
        mock_mqtt_client.loop_start.return_value = mqtt.MQTT_ERR_SUCCESS

        with pytest.raises(errors.ConnectionTimeoutError):
            transport.connect(fake_password, timeout=0)

    @pytest.mark.it("Accepts a CONNACK received before a zero timeout is evaluated")
    def test_zero_timeout_with_connack(self, mock_mqtt_client, transport):
        transport.connect(fake_password, timeout=0)

    @pytest.mark.parametrize(
        "reason_code",
        [successful_connack_reason_code, failed_connack_reason_code],
        ids=["Accepted CONNACK", "Rejected CONNACK"],
    )
    @pytest.mark.it("Ignores a CONNACK received after the connection attempt times out")
    def test_connack_after_timeout_is_ignored(
        self, mocker, mock_mqtt_client, transport, reason_code
    ):
        mock_mqtt_client.loop_start.side_effect = None
        mock_mqtt_client.loop_start.return_value = mqtt.MQTT_ERR_SUCCESS
        disconnected_handler = mocker.MagicMock()
        transport.on_mqtt_disconnected_handler = disconnected_handler

        def disconnect_after_timeout():
            trigger_on_connect(mock_mqtt_client, reason_code=reason_code)
            return mqtt.MQTT_ERR_SUCCESS

        mock_mqtt_client.disconnect.side_effect = disconnect_after_timeout

        with pytest.raises(errors.ConnectionTimeoutError) as e_info:
            transport.connect(fake_password, timeout=0.01)

        trigger_on_disconnect(mock_mqtt_client, reason_code=failed_disconnect_reason_code)

        assert transport._connection_attempt._error is e_info.value
        assert disconnected_handler.call_count == 0

    @pytest.mark.it(
        "Suppresses the Paho disconnect callback during timeout cleanup and restores it afterward"
    )
    def test_connack_timeout_suppresses_cleanup_disconnect_callback(
        self, mock_mqtt_client, transport
    ):
        mock_mqtt_client.loop_start.side_effect = None
        mock_mqtt_client.loop_start.return_value = mqtt.MQTT_ERR_SUCCESS
        paho_disconnect_handler = mock_mqtt_client.on_disconnect

        def disconnect_while_checking_handler():
            assert mock_mqtt_client.on_disconnect is None
            return mqtt.MQTT_ERR_SUCCESS

        mock_mqtt_client.disconnect.side_effect = disconnect_while_checking_handler

        with pytest.raises(errors.ConnectionTimeoutError):
            transport.connect(fake_password, timeout=0.01)

        assert mock_mqtt_client.on_disconnect is paho_disconnect_handler

    @pytest.mark.parametrize(
        "cleanup_failure",
        ["disconnect", "loop_stop"],
        ids=["Paho disconnect raises", "Paho loop_stop raises"],
    )
    @pytest.mark.it("Preserves the timeout if timeout cleanup raises an Exception")
    def test_connack_timeout_preserves_error_if_cleanup_raises(
        self,
        mock_mqtt_client,
        transport,
        arbitrary_exception,
        cleanup_failure,
    ):
        mock_mqtt_client.loop_start.side_effect = None
        mock_mqtt_client.loop_start.return_value = mqtt.MQTT_ERR_SUCCESS
        if cleanup_failure == "disconnect":
            mock_mqtt_client.disconnect.side_effect = arbitrary_exception
        else:
            mock_mqtt_client.loop_stop.side_effect = [None, arbitrary_exception]

        with pytest.raises(errors.ConnectionTimeoutError):
            transport.connect(fake_password, timeout=0.01)

        assert mock_mqtt_client.on_disconnect is not None

    @pytest.mark.it("Can connect successfully after a connection attempt times out")
    def test_connect_after_timeout(self, mock_mqtt_client, transport):
        mock_mqtt_client.loop_start.side_effect = None
        mock_mqtt_client.loop_start.return_value = mqtt.MQTT_ERR_SUCCESS

        with pytest.raises(errors.ConnectionTimeoutError):
            transport.connect(fake_password, timeout=0.01)

        mock_mqtt_client.loop_start.side_effect = lambda: (
            trigger_on_connect(mock_mqtt_client) or mqtt.MQTT_ERR_SUCCESS
        )

        transport.connect(fake_password)

        assert mock_mqtt_client.connect.call_count == 2

    @pytest.mark.parametrize(
        "reason_code",
        [successful_connack_reason_code, failed_connack_reason_code],
        ids=["Accepted CONNACK", "Rejected CONNACK"],
    )
    @pytest.mark.it("Does not apply a prior attempt's late CONNACK to a retry")
    def test_prior_connack_during_loop_join_does_not_complete_retry(
        self,
        mock_mqtt_client,
        transport,
        run_in_daemon_thread,
        poll_until,
        reason_code,
    ):
        mock_mqtt_client.loop_start.side_effect = None
        mock_mqtt_client.loop_start.return_value = mqtt.MQTT_ERR_SUCCESS

        with pytest.raises(errors.ConnectionTimeoutError):
            transport.connect(fake_password, timeout=0.01)

        prior_attempt = transport._connection_attempt
        mock_mqtt_client.loop_stop.side_effect = lambda: trigger_on_connect(
            mock_mqtt_client, reason_code=reason_code
        )
        retry_future = run_in_daemon_thread(transport.connect, fake_password, timeout=1)
        poll_until(lambda: mock_mqtt_client.loop_start.call_count == 2, timeout=1)

        assert transport._connection_attempt is not prior_attempt
        assert not retry_future.done()

        trigger_on_connect(mock_mqtt_client)
        retry_future.result(timeout=1)


@pytest.mark.describe("MQTTTransport - OCCURRENCE: CONNACK after transport collection")
class TestConnackAfterTransportCollection(object):
    @pytest.mark.it(
        "Stops Paho's network loop if the MQTTTransport was garbage collected before CONNACK"
    )
    @pytest.mark.parametrize(
        "reason_code",
        [successful_connack_reason_code, failed_connack_reason_code],
        ids=["Successful CONNACK", "Failed CONNACK"],
    )
    def test_stops_loop_after_gc(
        self, mocker, mock_mqtt_client, collected_transport_weakref, reason_code
    ):
        trigger_on_connect(mock_mqtt_client, reason_code=reason_code)

        assert mock_mqtt_client.loop_stop.call_count == 1
        assert mock_mqtt_client.loop_stop.call_args == mocker.call()


@pytest.mark.describe("MQTTTransport - .disconnect()")
class TestDisconnect(object):
    @pytest.mark.it("Initiates MQTT disconnect via Paho")
    def test_calls_paho_disconnect(self, mocker, mock_mqtt_client, transport):
        transport.disconnect()

        assert mock_mqtt_client.disconnect.call_count == 1
        assert mock_mqtt_client.disconnect.call_args == mocker.call()

    @pytest.mark.it(
        "Raises a ProtocolClientError if Paho disconnect raises an unexpected Exception"
    )
    def test_client_raises_unexpected_error(
        self, mocker, mock_mqtt_client, transport, arbitrary_exception
    ):
        mock_mqtt_client.disconnect.side_effect = arbitrary_exception
        with pytest.raises(errors.ProtocolClientError) as e_info:
            transport.disconnect()
        assert e_info.value.__cause__ is arbitrary_exception

    @pytest.mark.it("Allows any BaseExceptions raised in Paho disconnect to propagate")
    def test_client_raises_base_exception(
        self, mock_mqtt_client, transport, arbitrary_base_exception
    ):
        mock_mqtt_client.disconnect.side_effect = arbitrary_base_exception
        with pytest.raises(arbitrary_base_exception.__class__) as e_info:
            transport.disconnect()
        assert e_info.value is arbitrary_base_exception

    @pytest.mark.it("Raises a custom Exception if Paho disconnect returns an error code")
    @pytest.mark.parametrize(
        "error_case",
        disconnect_error_code_cases,
        ids=[
            "{}->{}".format(case["name"], case["error"].__name__)
            for case in disconnect_error_code_cases
        ],
    )
    def test_client_returns_error_code(self, mocker, mock_mqtt_client, transport, error_case):
        mock_mqtt_client.disconnect.return_value = error_case["error_code"]
        with pytest.raises(error_case["error"]):
            transport.disconnect()

    @pytest.mark.it("Treats MQTT_ERR_NO_CONN as a successful disconnect")
    def test_no_connection_error_code(self, mock_mqtt_client, transport):
        mock_mqtt_client.disconnect.return_value = mqtt.MQTT_ERR_NO_CONN

        transport.disconnect()

    @pytest.mark.it(
        "Completes tracked operations as cancelled after an already-completed disconnect"
    )
    def test_no_connection_error_code_clears_inflight(self, mocker, mock_mqtt_client, transport):
        callback = mocker.MagicMock()
        transport.subscribe(topic=fake_topic, qos=fake_qos, callback=callback)
        mock_mqtt_client.disconnect.return_value = mqtt.MQTT_ERR_NO_CONN

        transport.disconnect(clear_inflight=True)

        assert callback.call_count == 1
        assert callback.call_args == mocker.call(cancelled=True)

    @pytest.mark.it(
        "Completes tracked operations as cancelled if the clear_inflight parameter is True"
    )
    def test_clear_inflight_completes_tracked_operations(self, mocker, mock_mqtt_client, transport):
        # Set up a pending publish
        pub_callback = mocker.MagicMock(name="pub cb")
        pub_mid = "1"
        message_info = mqtt.MQTTMessageInfo(pub_mid)
        message_info.rc = fake_rc
        mock_mqtt_client.publish.return_value = message_info
        transport.publish(topic=fake_topic, payload=fake_payload, callback=pub_callback)

        # Set up a pending subscribe
        sub_callback = mocker.MagicMock(name="sub_cb")
        sub_mid = "2"
        mock_mqtt_client.subscribe.return_value = (fake_rc, sub_mid)
        transport.subscribe(topic=fake_topic, qos=fake_qos, callback=sub_callback)

        # Operations are pending
        assert pub_callback.call_count == 0
        assert sub_callback.call_count == 0

        # Disconnect and clear tracked operations
        transport.disconnect(clear_inflight=True)

        # Tracked operations were completed as cancelled
        assert pub_callback.call_count == 1
        assert pub_callback.call_args == mocker.call(cancelled=True)
        assert sub_callback.call_count == 1
        assert sub_callback.call_args == mocker.call(cancelled=True)

    @pytest.mark.it(
        "Preserves publish tracking and stops non-publish tracking if clear_inflight is False"
    )
    def test_clear_inflight_false_preserves_publish_tracking(
        self, mocker, mock_mqtt_client, transport
    ):
        # Set up a pending publish
        pub_callback = mocker.MagicMock(name="pub cb")
        pub_mid = "1"
        message_info = mqtt.MQTTMessageInfo(pub_mid)
        message_info.rc = fake_rc
        mock_mqtt_client.publish.return_value = message_info
        transport.publish(topic=fake_topic, payload=fake_payload, callback=pub_callback)

        # Set up a pending subscribe
        sub_callback = mocker.MagicMock(name="sub_cb")
        sub_mid = "2"
        mock_mqtt_client.subscribe.return_value = (fake_rc, sub_mid)
        transport.subscribe(topic=fake_topic, qos=fake_qos, callback=sub_callback)

        # Operations are pending
        assert pub_callback.call_count == 0
        assert sub_callback.call_count == 0

        # Disconnect
        transport.disconnect(clear_inflight=False)

        # Tracked operations remain pending
        assert pub_callback.call_count == 0
        assert sub_callback.call_count == 0
        assert list(transport._op_manager._pending_operations) == [pub_mid]
        assert transport._op_manager._pending_operations[pub_mid].callback is pub_callback
        assert transport._op_manager._cancelled_operation_mids == {sub_mid}

    @pytest.mark.it("Preserves publish tracking and stops non-publish tracking by default")
    def test_default_preserves_publish_tracking(self, mocker, mock_mqtt_client, transport):
        # Set up a pending publish
        pub_callback = mocker.MagicMock(name="pub cb")
        pub_mid = "1"
        message_info = mqtt.MQTTMessageInfo(pub_mid)
        message_info.rc = fake_rc
        mock_mqtt_client.publish.return_value = message_info
        transport.publish(topic=fake_topic, payload=fake_payload, callback=pub_callback)

        # Set up a pending subscribe
        sub_callback = mocker.MagicMock(name="sub_cb")
        sub_mid = "2"
        mock_mqtt_client.subscribe.return_value = (fake_rc, sub_mid)
        transport.subscribe(topic=fake_topic, qos=fake_qos, callback=sub_callback)

        # Operations are pending
        assert pub_callback.call_count == 0
        assert sub_callback.call_count == 0

        # Disconnect
        transport.disconnect()

        # Tracked operations remain pending
        assert pub_callback.call_count == 0
        assert sub_callback.call_count == 0
        assert list(transport._op_manager._pending_operations) == [pub_mid]
        assert transport._op_manager._pending_operations[pub_mid].callback is pub_callback
        assert transport._op_manager._cancelled_operation_mids == {sub_mid}

    @pytest.mark.it("Stops MQTT Network Loop when disconnect does not raise an exception")
    def test_calls_loop_stop_on_success(self, mocker, mock_mqtt_client, transport):
        transport.disconnect()

        assert mock_mqtt_client.loop_stop.call_count == 1
        assert mock_mqtt_client.loop_stop.call_args == mocker.call()

    @pytest.mark.it("Stops MQTT Network Loop when disconnect raises an exception")
    def test_calls_loop_stop_on_exception(
        self, mocker, mock_mqtt_client, transport, arbitrary_exception
    ):
        mock_mqtt_client.disconnect.side_effect = arbitrary_exception

        with pytest.raises(Exception):
            transport.disconnect()

        assert mock_mqtt_client.loop_stop.call_count == 1
        assert mock_mqtt_client.loop_stop.call_args == mocker.call()


@pytest.mark.describe("MQTTTransport - OCCURRENCE: Disconnect Completed")
class TestEventDisconnectCompleted(object):
    @pytest.fixture(
        params=[successful_disconnect_reason_code, failed_disconnect_reason_code],
        ids=["success reason code", "failed reason code"],
    )
    def reason_code_success_or_failure(self, request):
        return request.param

    @pytest.mark.it(
        "Triggers on_mqtt_disconnected_handler event handler upon disconnect completion"
    )
    def test_calls_event_handler_callback_externally_driven(
        self, mocker, mock_mqtt_client, transport
    ):
        callback = mocker.MagicMock()
        transport.on_mqtt_disconnected_handler = callback

        transport.connect(fake_password)

        # Manually trigger Paho on_disconnect event_handler
        trigger_on_disconnect(mock_mqtt_client)

        # Verify transport.on_mqtt_disconnected_handler was called
        assert callback.call_count == 1
        assert callback.call_args == mocker.call(None)

    @pytest.mark.parametrize(
        "error_case",
        paho_disconnect_reason_error_cases,
        ids=[
            "{}->{}".format(case["reason_code"], case["error"].__name__)
            for case in paho_disconnect_reason_error_cases
        ],
    )
    @pytest.mark.it(
        "Triggers on_mqtt_disconnected_handler with a ConnectionDroppedError for an unexpected MQTT 3.1.1 disconnect"
    )
    def test_calls_event_handler_callback_with_failure(
        self, mocker, mock_mqtt_client, transport, error_case
    ):
        callback = mocker.MagicMock()
        transport.on_mqtt_disconnected_handler = callback

        transport.connect(fake_password)

        trigger_on_disconnect(mock_mqtt_client, reason_code=error_case["reason_code"])

        # Verify transport.on_mqtt_disconnected_handler was called
        assert callback.call_count == 1
        assert isinstance(callback.call_args[0][0], error_case["error"])
        assert str(callback.call_args[0][0]) == str(error_case["reason_code"])

    @pytest.mark.it("Reports one disconnection when Paho invokes on_disconnect more than once")
    def test_reports_one_disconnection_for_duplicate_paho_callbacks(
        self, mocker, mock_mqtt_client, transport
    ):
        callback = mocker.MagicMock()
        transport.on_mqtt_disconnected_handler = callback

        transport.connect(fake_password)
        trigger_on_disconnect(mock_mqtt_client, reason_code=failed_disconnect_reason_code)
        trigger_on_disconnect(mock_mqtt_client, reason_code=failed_disconnect_reason_code)

        assert callback.call_count == 1

        transport.connect(fake_password)
        trigger_on_disconnect(mock_mqtt_client, reason_code=failed_disconnect_reason_code)

        assert callback.call_count == 2

    @pytest.mark.it(
        "Skips on_mqtt_disconnected_handler event handler if set to 'None' upon disconnect completion"
    )
    def test_skips_none_event_handler_callback(self, mocker, mock_mqtt_client, transport):
        assert transport.on_mqtt_disconnected_handler is None

        transport.connect(fake_password)

        trigger_on_disconnect(mock_mqtt_client)

        # No further asserts required - this is a test to show that it skips a callback.
        # Not raising an exception == test passed

    @pytest.mark.it("Recovers from Exception in on_mqtt_disconnected_handler event handler")
    def test_event_handler_callback_raises_exception(
        self, mocker, mock_mqtt_client, transport, arbitrary_exception
    ):
        event_cb = mocker.MagicMock(side_effect=arbitrary_exception)
        transport.on_mqtt_disconnected_handler = event_cb

        transport.connect(fake_password)
        trigger_on_disconnect(mock_mqtt_client)

        # Callback was called, but exception did not propagate
        assert event_cb.call_count == 1

    @pytest.mark.it(
        "Allows any BaseExceptions raised in on_mqtt_disconnected_handler event handler to propagate"
    )
    def test_event_handler_callback_raises_base_exception(
        self, mocker, mock_mqtt_client, transport, arbitrary_base_exception
    ):
        event_cb = mocker.MagicMock(side_effect=arbitrary_base_exception)
        transport.on_mqtt_disconnected_handler = event_cb

        transport.connect(fake_password)
        with pytest.raises(arbitrary_base_exception.__class__) as e_info:
            trigger_on_disconnect(mock_mqtt_client)
        assert e_info.value is arbitrary_base_exception

    @pytest.mark.it("Does not call Paho's disconnect() method if cause is None")
    def test_doesnt_call_disconnect_without_cause(self, mock_mqtt_client, transport):
        transport.connect(fake_password)
        trigger_on_disconnect(mock_mqtt_client)
        assert mock_mqtt_client.disconnect.call_count == 0

    @pytest.mark.it("Does not call Paho's loop_stop() if cause is None")
    def test_does_not_call_loop_stop(self, mock_mqtt_client, transport):
        transport.connect(fake_password)
        mock_mqtt_client.loop_stop.reset_mock()
        trigger_on_disconnect(mock_mqtt_client)
        assert mock_mqtt_client.loop_stop.call_count == 0

    @pytest.mark.it("Does not stop or reconnect Paho after an unexpected disconnection")
    def test_does_not_stop_or_reconnect_paho_after_failure(self, mock_mqtt_client, transport):
        transport.connect(fake_password)
        mock_mqtt_client.loop_stop.reset_mock()
        trigger_on_disconnect(mock_mqtt_client, reason_code=failed_disconnect_reason_code)

        assert mock_mqtt_client.disconnect.call_count == 0
        assert mock_mqtt_client.loop_stop.call_count == 0
        assert mock_mqtt_client.reconnect.call_count == 0

    @pytest.mark.it(
        "Does not raise any exceptions if the MQTTTransport object was garbage collected before the disconnect completed"
    )
    def test_no_exception_after_gc(
        self, mock_mqtt_client, collected_transport_weakref, reason_code_success_or_failure
    ):
        assert mock_mqtt_client.on_disconnect
        trigger_on_disconnect(mock_mqtt_client, reason_code=reason_code_success_or_failure)
        # lack of exception is success

    @pytest.mark.it(
        "Calls Paho's loop_stop() if the MQTTTransport object was garbage collected before the disconnect completed"
    )
    def test_calls_loop_stop_after_gc(
        self,
        collected_transport_weakref,
        mock_mqtt_client,
        reason_code_success_or_failure,
        mocker,
    ):
        assert mock_mqtt_client.loop_stop.call_count == 0
        trigger_on_disconnect(mock_mqtt_client, reason_code=reason_code_success_or_failure)
        assert mock_mqtt_client.loop_stop.call_count == 1
        assert mock_mqtt_client.loop_stop.call_args == mocker.call()

    @pytest.mark.it(
        "Allows any Exception raised by Paho's loop_stop() to propagate if the MQTTTransport object was garbage collected before the disconnect completed"
    )
    def test_raises_exception_after_gc(
        self,
        collected_transport_weakref,
        mock_mqtt_client,
        reason_code_success_or_failure,
        arbitrary_exception,
    ):
        mock_mqtt_client.loop_stop.side_effect = arbitrary_exception
        with pytest.raises(type(arbitrary_exception)):
            trigger_on_disconnect(mock_mqtt_client, reason_code=reason_code_success_or_failure)

    @pytest.mark.it(
        "Allows any BaseException raised by Paho's loop_stop() to propagate if the MQTTTransport object was garbage collected before the disconnect completed"
    )
    def test_raises_base_exception_after_gc(
        self,
        collected_transport_weakref,
        mock_mqtt_client,
        reason_code_success_or_failure,
        arbitrary_base_exception,
    ):
        mock_mqtt_client.loop_stop.side_effect = arbitrary_base_exception
        with pytest.raises(type(arbitrary_base_exception)):
            trigger_on_disconnect(mock_mqtt_client, reason_code=reason_code_success_or_failure)


@pytest.mark.describe("MQTTTransport - .subscribe()")
class TestSubscribe(object):
    @pytest.mark.it("Subscribes with Paho")
    @pytest.mark.parametrize(
        "qos",
        [pytest.param(0, id="QoS 0"), pytest.param(1, id="QoS 1"), pytest.param(2, id="QoS 2")],
    )
    def test_calls_paho_subscribe(self, mocker, mock_mqtt_client, transport, qos):
        transport.subscribe(fake_topic, qos=qos)

        assert mock_mqtt_client.subscribe.call_count == 1
        assert mock_mqtt_client.subscribe.call_args == mocker.call(fake_topic, qos=qos)

    @pytest.mark.it("Tracks the operation as a SUBSCRIBE")
    def test_tracks_subscribe_operation_type(self, mocker, transport):
        callback = mocker.MagicMock()

        transport.subscribe(fake_topic, callback=callback)

        pending_operation = transport._op_manager._pending_operations[fake_mid]
        assert pending_operation.operation_type is OperationType.SUBSCRIBE
        assert pending_operation.callback is callback

    @pytest.mark.it("Raises ValueError on invalid QoS")
    @pytest.mark.parametrize("qos", [pytest.param(-1, id="QoS < 0"), pytest.param(3, id="QoS > 2")])
    def test_raises_value_error_invalid_qos(self, qos):
        # Manually instantiate protocol wrapper, do NOT mock paho client (paho generates this error)
        transport = MQTTTransport(
            client_id=fake_device_id, hostname=fake_hostname, username=fake_username
        )
        with pytest.raises(ValueError):
            transport.subscribe(fake_topic, qos=qos)

    @pytest.mark.it("Raises ValueError on invalid topic string")
    @pytest.mark.parametrize("topic", [pytest.param(None), pytest.param("", id="Empty string")])
    def test_raises_value_error_invalid_topic(self, topic):
        # Manually instantiate protocol wrapper, do NOT mock paho client (paho generates this error)
        transport = MQTTTransport(
            client_id=fake_device_id, hostname=fake_hostname, username=fake_username
        )
        with pytest.raises(ValueError):
            transport.subscribe(topic, qos=fake_qos)

    @pytest.mark.it("Triggers callback upon subscribe completion")
    @pytest.mark.parametrize(
        "suback_return_code",
        [
            pytest.param(0x00, id="Maximum QoS 0"),
            pytest.param(0x01, id="Maximum QoS 1"),
            pytest.param(0x02, id="Maximum QoS 2"),
        ],
    )
    def test_triggers_callback_upon_paho_on_subscribe_event(
        self, mocker, mock_mqtt_client, transport, suback_return_code
    ):
        callback = mocker.MagicMock()
        mock_mqtt_client.subscribe.return_value = (fake_rc, fake_mid)

        # Initiate subscribe
        transport.subscribe(topic=fake_topic, qos=fake_qos, callback=callback)

        # Check callback is not called yet
        assert callback.call_count == 0

        # Manually trigger Paho on_subscribe event handler
        granted_qos = mqtt.ReasonCode(PacketTypes.SUBACK, identifier=suback_return_code)
        trigger_on_subscribe(mock_mqtt_client, mid=fake_mid, reason_codes=[granted_qos])

        # Check callback has now been called
        assert callback.call_count == 1
        assert callback.call_args == mocker.call()

    @pytest.mark.it("Completes a subscription with ProtocolClientError if any reason fails")
    def test_failed_suback(self, mocker, mock_mqtt_client, transport):
        callback = mocker.MagicMock()
        transport.subscribe(topic=fake_topic, qos=fake_qos, callback=callback)
        granted = mqtt.ReasonCode(PacketTypes.SUBACK, identifier=1)
        rejected = mqtt.ReasonCode(PacketTypes.SUBACK, identifier=128)

        trigger_on_subscribe(mock_mqtt_client, mid=fake_mid, reason_codes=[granted, rejected])

        assert callback.call_count == 1
        assert isinstance(callback.call_args.kwargs["error"], errors.ProtocolClientError)

    @pytest.mark.it(
        "Stops Paho's network loop if the MQTTTransport was garbage collected before subscribe completed"
    )
    def test_stops_loop_after_gc(self, mocker, mock_mqtt_client, collected_transport_weakref):
        trigger_on_subscribe(mock_mqtt_client, mid=fake_mid)

        assert mock_mqtt_client.loop_stop.call_count == 1
        assert mock_mqtt_client.loop_stop.call_args == mocker.call()

    @pytest.mark.it(
        "Triggers callback upon subscribe completion when Paho event handler triggered early"
    )
    def test_triggers_callback_when_paho_on_subscribe_event_called_early(
        self, mocker, mock_mqtt_client, transport
    ):
        callback = mocker.MagicMock()

        def trigger_early_on_subscribe(topic, qos):

            # Trigger on_subscribe before returning mid
            trigger_on_subscribe(mock_mqtt_client, mid=fake_mid)

            # Check callback not yet called
            assert callback.call_count == 0

            return (fake_rc, fake_mid)

        mock_mqtt_client.subscribe.side_effect = trigger_early_on_subscribe

        # Initiate subscribe
        transport.subscribe(topic=fake_topic, qos=fake_qos, callback=callback)

        # Check callback has now been called
        assert callback.call_count == 1

    @pytest.mark.it(
        "Completes a rejected subscription when the SUBACK arrives before subscribe returns"
    )
    def test_failed_suback_received_early(self, mocker, mock_mqtt_client, transport):
        callback = mocker.MagicMock()
        rejected = mqtt.ReasonCode(PacketTypes.SUBACK, identifier=128)

        def trigger_early_on_subscribe(topic, qos):
            trigger_on_subscribe(mock_mqtt_client, mid=fake_mid, reason_codes=[rejected])
            assert callback.call_count == 0
            return (fake_rc, fake_mid)

        mock_mqtt_client.subscribe.side_effect = trigger_early_on_subscribe

        transport.subscribe(topic=fake_topic, qos=fake_qos, callback=callback)

        assert callback.call_count == 1
        assert isinstance(callback.call_args.kwargs["error"], errors.ProtocolClientError)

    @pytest.mark.it("Skips callback that is set to 'None' upon subscribe completion")
    def test_none_callback_upon_paho_on_subscribe_event(self, mocker, mock_mqtt_client, transport):
        callback = None
        mock_mqtt_client.subscribe.return_value = (fake_rc, fake_mid)

        # Initiate subscribe
        transport.subscribe(topic=fake_topic, qos=fake_qos, callback=callback)

        # Manually trigger Paho on_subscribe event handler
        trigger_on_subscribe(mock_mqtt_client, mid=fake_mid)

        # No assertions necessary - not raising an exception => success

    @pytest.mark.it(
        "Skips callback that is set to 'None' upon subscribe completion when Paho event handler triggered early"
    )
    def test_none_callback_when_paho_on_subscribe_event_called_early(
        self, mocker, mock_mqtt_client, transport
    ):
        callback = None

        def trigger_early_on_subscribe(topic, qos):

            # Trigger on_subscribe before returning mid
            trigger_on_subscribe(mock_mqtt_client, mid=fake_mid)

            return (fake_rc, fake_mid)

        mock_mqtt_client.subscribe.side_effect = trigger_early_on_subscribe

        # Initiate subscribe
        transport.subscribe(topic=fake_topic, qos=fake_qos, callback=callback)

        # No assertions necessary - not raising an exception => success

    @pytest.mark.it(
        "Handles multiple callbacks from multiple subscribe operations that complete out of order"
    )
    def test_multiple_callbacks(self, mocker, mock_mqtt_client, transport):
        callback1 = mocker.MagicMock()
        callback2 = mocker.MagicMock()
        callback3 = mocker.MagicMock()

        mid1 = 1
        mid2 = 2
        mid3 = 3

        mock_mqtt_client.subscribe.side_effect = [(fake_rc, mid1), (fake_rc, mid2), (fake_rc, mid3)]

        # Initiate subscribe (1 -> 2 -> 3)
        transport.subscribe(topic=fake_topic, qos=fake_qos, callback=callback1)
        transport.subscribe(topic=fake_topic, qos=fake_qos, callback=callback2)
        transport.subscribe(topic=fake_topic, qos=fake_qos, callback=callback3)

        # Check callbacks have not yet been called
        assert callback1.call_count == 0
        assert callback2.call_count == 0
        assert callback3.call_count == 0

        # Manually trigger Paho on_subscribe event handler (2 -> 3 -> 1)
        trigger_on_subscribe(mock_mqtt_client, mid=mid2)
        assert callback1.call_count == 0
        assert callback2.call_count == 1
        assert callback3.call_count == 0

        trigger_on_subscribe(mock_mqtt_client, mid=mid3)
        assert callback1.call_count == 0
        assert callback2.call_count == 1
        assert callback3.call_count == 1

        trigger_on_subscribe(mock_mqtt_client, mid=mid1)
        assert callback1.call_count == 1
        assert callback2.call_count == 1
        assert callback3.call_count == 1

    @pytest.mark.it("Recovers from Exception in callback")
    def test_callback_raises_exception(
        self, mocker, mock_mqtt_client, transport, arbitrary_exception
    ):
        callback = mocker.MagicMock(side_effect=arbitrary_exception)
        mock_mqtt_client.subscribe.return_value = (fake_rc, fake_mid)

        transport.subscribe(topic=fake_topic, qos=fake_qos, callback=callback)
        trigger_on_subscribe(mock_mqtt_client, mid=fake_mid)

        # Callback was called, but exception did not propagate
        assert callback.call_count == 1

    @pytest.mark.it("Allows any BaseExceptions raised in callback to propagate")
    def test_callback_raises_base_exception(
        self, mocker, mock_mqtt_client, transport, arbitrary_base_exception
    ):
        callback = mocker.MagicMock(side_effect=arbitrary_base_exception)
        mock_mqtt_client.subscribe.return_value = (fake_rc, fake_mid)

        transport.subscribe(topic=fake_topic, qos=fake_qos, callback=callback)
        with pytest.raises(arbitrary_base_exception.__class__) as e_info:
            trigger_on_subscribe(mock_mqtt_client, mid=fake_mid)
        assert e_info.value is arbitrary_base_exception

    @pytest.mark.it("Recovers from Exception in callback when Paho event handler triggered early")
    def test_callback_raises_exception_when_paho_on_subscribe_triggered_early(
        self, mocker, mock_mqtt_client, transport, arbitrary_exception
    ):
        callback = mocker.MagicMock(side_effect=arbitrary_exception)

        def trigger_early_on_subscribe(topic, qos):
            trigger_on_subscribe(mock_mqtt_client, mid=fake_mid)

            # Should not have yet called callback
            assert callback.call_count == 0

            return (fake_rc, fake_mid)

        mock_mqtt_client.subscribe.side_effect = trigger_early_on_subscribe

        # Initiate subscribe
        transport.subscribe(topic=fake_topic, qos=fake_qos, callback=callback)

        # Callback was called, but exception did not propagate
        assert callback.call_count == 1

    @pytest.mark.it(
        "Allows any BaseExceptions raised in callback when Paho event handler triggered early to propagate"
    )
    def test_callback_raises_base_exception_when_paho_on_subscribe_triggered_early(
        self, mocker, mock_mqtt_client, transport, arbitrary_base_exception
    ):
        callback = mocker.MagicMock(side_effect=arbitrary_base_exception)

        def trigger_early_on_subscribe(topic, qos):
            trigger_on_subscribe(mock_mqtt_client, mid=fake_mid)

            # Should not have yet called callback
            assert callback.call_count == 0

            return (fake_rc, fake_mid)

        mock_mqtt_client.subscribe.side_effect = trigger_early_on_subscribe

        # Initiate subscribe
        with pytest.raises(arbitrary_base_exception.__class__) as e_info:
            transport.subscribe(topic=fake_topic, qos=fake_qos, callback=callback)
        assert e_info.value is arbitrary_base_exception

    @pytest.mark.it("Raises a ProtocolClientError if Paho subscribe raises an unexpected Exception")
    def test_client_raises_unexpected_error(
        self, mocker, mock_mqtt_client, transport, arbitrary_exception
    ):
        mock_mqtt_client.subscribe.side_effect = arbitrary_exception
        with pytest.raises(errors.ProtocolClientError) as e_info:
            transport.subscribe(topic=fake_topic, qos=fake_qos, callback=None)
        assert e_info.value.__cause__ is arbitrary_exception

    @pytest.mark.it("Allows any BaseExceptions raised in Paho subscribe to propagate")
    def test_client_raises_base_exception(
        self, mock_mqtt_client, transport, arbitrary_base_exception
    ):
        mock_mqtt_client.subscribe.side_effect = arbitrary_base_exception
        with pytest.raises(arbitrary_base_exception.__class__) as e_info:
            transport.subscribe(topic=fake_topic, qos=fake_qos, callback=None)
        assert e_info.value is arbitrary_base_exception

    # NOTE: this test tests all mapped Paho error codes, even ones that shouldn't be
    # possible on a subscribe operation.
    @pytest.mark.it("Raises a custom Exception if Paho subscribe returns an error code")
    @pytest.mark.parametrize(
        "error_case",
        paho_error_code_cases,
        ids=[
            "{}->{}".format(case["name"], case["error"].__name__) for case in paho_error_code_cases
        ],
    )
    def test_client_returns_error_code(self, mocker, mock_mqtt_client, transport, error_case):
        mock_mqtt_client.subscribe.return_value = (error_case["error_code"], 0)
        with pytest.raises(error_case["error"]):
            transport.subscribe(topic=fake_topic, qos=fake_qos, callback=None)


@pytest.mark.describe("MQTTTransport - .unsubscribe()")
class TestUnsubscribe(object):
    @pytest.mark.it("Unsubscribes with Paho")
    def test_calls_paho_unsubscribe(self, mocker, mock_mqtt_client, transport):
        transport.unsubscribe(fake_topic)

        assert mock_mqtt_client.unsubscribe.call_count == 1
        assert mock_mqtt_client.unsubscribe.call_args == mocker.call(fake_topic)

    @pytest.mark.it("Tracks the operation as an UNSUBSCRIBE")
    def test_tracks_unsubscribe_operation_type(self, mocker, transport):
        callback = mocker.MagicMock()

        transport.unsubscribe(fake_topic, callback=callback)

        pending_operation = transport._op_manager._pending_operations[fake_mid]
        assert pending_operation.operation_type is OperationType.UNSUBSCRIBE
        assert pending_operation.callback is callback

    @pytest.mark.it("Raises ValueError on invalid topic string")
    @pytest.mark.parametrize("topic", [pytest.param(None), pytest.param("", id="Empty string")])
    def test_raises_value_error_invalid_topic(self, topic):
        # Manually instantiate protocol wrapper, do NOT mock paho client (paho generates this error)
        transport = MQTTTransport(
            client_id=fake_device_id, hostname=fake_hostname, username=fake_username
        )
        with pytest.raises(ValueError):
            transport.unsubscribe(topic)

    @pytest.mark.it("Triggers callback upon unsubscribe completion")
    def test_triggers_callback_upon_paho_on_unsubscribe_event(
        self, mocker, mock_mqtt_client, transport
    ):
        callback = mocker.MagicMock()
        mock_mqtt_client.unsubscribe.return_value = (fake_rc, fake_mid)

        # Initiate unsubscribe
        transport.unsubscribe(topic=fake_topic, callback=callback)

        # Check callback not called
        assert callback.call_count == 0

        # Manually trigger Paho on_unsubscribe event handler
        trigger_on_unsubscribe(mock_mqtt_client, mid=fake_mid)

        # Check callback has now been called
        assert callback.call_count == 1

    @pytest.mark.it(
        "Stops Paho's network loop if the MQTTTransport was garbage collected before unsubscribe completed"
    )
    def test_stops_loop_after_gc(self, mocker, mock_mqtt_client, collected_transport_weakref):
        trigger_on_unsubscribe(mock_mqtt_client, mid=fake_mid)

        assert mock_mqtt_client.loop_stop.call_count == 1
        assert mock_mqtt_client.loop_stop.call_args == mocker.call()

    @pytest.mark.it(
        "Triggers callback upon unsubscribe completion when Paho event handler triggered early"
    )
    def test_triggers_callback_when_paho_on_unsubscribe_event_called_early(
        self, mocker, mock_mqtt_client, transport
    ):
        callback = mocker.MagicMock()

        def trigger_early_on_unsubscribe(topic):

            # Trigger on_unsubscribe before returning mid
            trigger_on_unsubscribe(mock_mqtt_client, mid=fake_mid)

            # Check callback not yet called
            assert callback.call_count == 0

            return (fake_rc, fake_mid)

        mock_mqtt_client.unsubscribe.side_effect = trigger_early_on_unsubscribe

        # Initiate unsubscribe
        transport.unsubscribe(topic=fake_topic, callback=callback)

        # Check callback has now been called
        assert callback.call_count == 1

    @pytest.mark.it("Skips callback that is set to 'None' upon unsubscribe completion")
    def test_none_callback_upon_paho_on_unsubscribe_event(
        self, mocker, mock_mqtt_client, transport
    ):
        callback = None
        mock_mqtt_client.unsubscribe.return_value = (fake_rc, fake_mid)

        # Initiate unsubscribe
        transport.unsubscribe(topic=fake_topic, callback=callback)

        # Manually trigger Paho on_unsubscribe event handler
        trigger_on_unsubscribe(mock_mqtt_client, mid=fake_mid)

        # No assertions necessary - not raising an exception => success

    @pytest.mark.it(
        "Skips callback that is set to 'None' upon unsubscribe completion when Paho event handler triggered early"
    )
    def test_none_callback_when_paho_on_unsubscribe_event_called_early(
        self, mocker, mock_mqtt_client, transport
    ):
        callback = None

        def trigger_early_on_unsubscribe(topic):

            # Trigger on_unsubscribe before returning mid
            trigger_on_unsubscribe(mock_mqtt_client, mid=fake_mid)

            return (fake_rc, fake_mid)

        mock_mqtt_client.unsubscribe.side_effect = trigger_early_on_unsubscribe

        # Initiate unsubscribe
        transport.unsubscribe(topic=fake_topic, callback=callback)

        # No assertions necessary - not raising an exception => success

    @pytest.mark.it(
        "Handles multiple callbacks from multiple unsubscribe operations that complete out of order"
    )
    def test_multiple_callbacks(self, mocker, mock_mqtt_client, transport):
        callback1 = mocker.MagicMock()
        callback2 = mocker.MagicMock()
        callback3 = mocker.MagicMock()

        mid1 = 1
        mid2 = 2
        mid3 = 3

        mock_mqtt_client.unsubscribe.side_effect = [
            (fake_rc, mid1),
            (fake_rc, mid2),
            (fake_rc, mid3),
        ]

        # Initiate unsubscribe (1 -> 2 -> 3)
        transport.unsubscribe(topic=fake_topic, callback=callback1)
        transport.unsubscribe(topic=fake_topic, callback=callback2)
        transport.unsubscribe(topic=fake_topic, callback=callback3)

        # Check callbacks have not yet been called
        assert callback1.call_count == 0
        assert callback2.call_count == 0
        assert callback3.call_count == 0

        # Manually trigger Paho on_unsubscribe event handler (2 -> 3 -> 1)
        trigger_on_unsubscribe(mock_mqtt_client, mid=mid2)
        assert callback1.call_count == 0
        assert callback2.call_count == 1
        assert callback3.call_count == 0

        trigger_on_unsubscribe(mock_mqtt_client, mid=mid3)
        assert callback1.call_count == 0
        assert callback2.call_count == 1
        assert callback3.call_count == 1

        trigger_on_unsubscribe(mock_mqtt_client, mid=mid1)
        assert callback1.call_count == 1
        assert callback2.call_count == 1
        assert callback3.call_count == 1

    @pytest.mark.it("Recovers from Exception in callback")
    def test_callback_raises_exception(
        self, mocker, mock_mqtt_client, transport, arbitrary_exception
    ):
        callback = mocker.MagicMock(side_effect=arbitrary_exception)
        mock_mqtt_client.unsubscribe.return_value = (fake_rc, fake_mid)

        transport.unsubscribe(topic=fake_topic, callback=callback)
        trigger_on_unsubscribe(mock_mqtt_client, mid=fake_mid)

        # Callback was called, but exception did not propagate
        assert callback.call_count == 1

    @pytest.mark.it("Allows any BaseExceptions raised in callback to propagate")
    def test_callback_raises_base_exception(
        self, mocker, mock_mqtt_client, transport, arbitrary_base_exception
    ):
        callback = mocker.MagicMock(side_effect=arbitrary_base_exception)
        mock_mqtt_client.unsubscribe.return_value = (fake_rc, fake_mid)

        transport.unsubscribe(topic=fake_topic, callback=callback)
        with pytest.raises(arbitrary_base_exception.__class__) as e_info:
            trigger_on_unsubscribe(mock_mqtt_client, mid=fake_mid)
        assert e_info.value is arbitrary_base_exception

    @pytest.mark.it("Recovers from Exception in callback when Paho event handler triggered early")
    def test_callback_raises_exception_when_paho_on_unsubscribe_triggered_early(
        self, mocker, mock_mqtt_client, transport, arbitrary_exception
    ):
        callback = mocker.MagicMock(side_effect=arbitrary_exception)

        def trigger_early_on_unsubscribe(topic):
            trigger_on_unsubscribe(mock_mqtt_client, mid=fake_mid)

            # Should not have yet called callback
            assert callback.call_count == 0

            return (fake_rc, fake_mid)

        mock_mqtt_client.unsubscribe.side_effect = trigger_early_on_unsubscribe

        # Initiate unsubscribe
        transport.unsubscribe(topic=fake_topic, callback=callback)

        # Callback was called, but exception did not propagate
        assert callback.call_count == 1

    @pytest.mark.it(
        "Allows any BaseExceptions raised in callback when Paho event handler triggered early to propagate"
    )
    def test_callback_raises_base_exception_when_paho_on_unsubscribe_triggered_early(
        self, mocker, mock_mqtt_client, transport, arbitrary_base_exception
    ):
        callback = mocker.MagicMock(side_effect=arbitrary_base_exception)

        def trigger_early_on_unsubscribe(topic):
            trigger_on_unsubscribe(mock_mqtt_client, mid=fake_mid)

            # Should not have yet called callback
            assert callback.call_count == 0

            return (fake_rc, fake_mid)

        mock_mqtt_client.unsubscribe.side_effect = trigger_early_on_unsubscribe

        # Initiate unsubscribe
        with pytest.raises(arbitrary_base_exception.__class__) as e_info:
            transport.unsubscribe(topic=fake_topic, callback=callback)
        assert e_info.value is arbitrary_base_exception

    @pytest.mark.it(
        "Raises a ProtocolClientError if Paho unsubscribe raises an unexpected Exception"
    )
    def test_client_raises_unexpected_error(
        self, mocker, mock_mqtt_client, transport, arbitrary_exception
    ):
        mock_mqtt_client.unsubscribe.side_effect = arbitrary_exception
        with pytest.raises(errors.ProtocolClientError) as e_info:
            transport.unsubscribe(topic=fake_topic, callback=None)
        assert e_info.value.__cause__ is arbitrary_exception

    @pytest.mark.it("Allows any BaseExceptions raised in Paho unsubscribe to propagate")
    def test_client_raises_base_exception(
        self, mock_mqtt_client, transport, arbitrary_base_exception
    ):
        mock_mqtt_client.unsubscribe.side_effect = arbitrary_base_exception
        with pytest.raises(arbitrary_base_exception.__class__) as e_info:
            transport.unsubscribe(topic=fake_topic, callback=None)
        assert e_info.value is arbitrary_base_exception

    # NOTE: this test tests all mapped Paho error codes, even ones that shouldn't be
    # possible on an unsubscribe operation.
    @pytest.mark.it("Raises a custom Exception if Paho unsubscribe returns an error code")
    @pytest.mark.parametrize(
        "error_case",
        paho_error_code_cases,
        ids=[
            "{}->{}".format(case["name"], case["error"].__name__) for case in paho_error_code_cases
        ],
    )
    def test_client_returns_error_code(self, mocker, mock_mqtt_client, transport, error_case):
        mock_mqtt_client.unsubscribe.return_value = (error_case["error_code"], 0)
        with pytest.raises(error_case["error"]):
            transport.unsubscribe(topic=fake_topic, callback=None)


@pytest.mark.describe("MQTTTransport - .publish()")
class TestPublish(object):
    @pytest.fixture
    def message_info(self, mocker):
        mi = mqtt.MQTTMessageInfo(fake_mid)
        mi.rc = fake_rc
        return mi

    @pytest.mark.it("Publishes with Paho")
    @pytest.mark.parametrize(
        "qos",
        [pytest.param(0, id="QoS 0"), pytest.param(1, id="QoS 1"), pytest.param(2, id="QoS 2")],
    )
    def test_calls_paho_publish(self, mocker, mock_mqtt_client, transport, qos):
        transport.publish(topic=fake_topic, payload=fake_payload, qos=qos)

        assert mock_mqtt_client.publish.call_count == 1
        assert mock_mqtt_client.publish.call_args == mocker.call(
            topic=fake_topic, payload=fake_payload, qos=qos
        )

    @pytest.mark.it("Tracks the operation as a PUBLISH")
    def test_tracks_publish_operation_type(self, mocker, transport):
        callback = mocker.MagicMock()

        transport.publish(fake_topic, fake_payload, callback=callback)

        pending_operation = transport._op_manager._pending_operations[fake_mid]
        assert pending_operation.operation_type is OperationType.PUBLISH
        assert pending_operation.callback is callback

    @pytest.mark.it("Raises ValueError on invalid QoS")
    @pytest.mark.parametrize("qos", [pytest.param(-1, id="QoS < 0"), pytest.param(3, id="Qos > 2")])
    def test_raises_value_error_invalid_qos(self, qos):
        # Manually instantiate protocol wrapper, do NOT mock paho client (paho generates this error)
        transport = MQTTTransport(
            client_id=fake_device_id, hostname=fake_hostname, username=fake_username
        )
        with pytest.raises(ValueError):
            transport.publish(topic=fake_topic, payload=fake_payload, qos=qos)

    @pytest.mark.it("Raises ValueError on invalid topic string")
    @pytest.mark.parametrize(
        "topic",
        [
            pytest.param(None),
            pytest.param("", id="Empty string"),
            pytest.param("+", id="Contains wildcard (+)"),
        ],
    )
    def test_raises_value_error_invalid_topic(self, topic):
        # Manually instantiate protocol wrapper, do NOT mock paho client (paho generates this error)
        transport = MQTTTransport(
            client_id=fake_device_id, hostname=fake_hostname, username=fake_username
        )
        with pytest.raises(ValueError):
            transport.publish(topic=topic, payload=fake_payload, qos=fake_qos)

    @pytest.mark.it("Raises ValueError on invalid payload value")
    @pytest.mark.parametrize("payload", [str(b"0" * 268435456)], ids=["Payload > 268435455 bytes"])
    def test_raises_value_error_invalid_payload(self, payload):
        # Manually instantiate protocol wrapper, do NOT mock paho client (paho generates this error)
        transport = MQTTTransport(
            client_id=fake_device_id, hostname=fake_hostname, username=fake_username
        )
        with pytest.raises(ValueError):
            transport.publish(topic=fake_topic, payload=payload, qos=fake_qos)

    @pytest.mark.it("Raises TypeError on invalid payload type")
    @pytest.mark.parametrize(
        "payload",
        [
            pytest.param({"a": "b"}, id="Dictionary"),
            pytest.param([1, 2, 3], id="List"),
            pytest.param(object(), id="Object"),
        ],
    )
    def test_raises_type_error_invalid_payload_type(self, payload):
        # Manually instantiate protocol wrapper, do NOT mock paho client (paho generates this error)
        transport = MQTTTransport(
            client_id=fake_device_id, hostname=fake_hostname, username=fake_username
        )
        with pytest.raises(TypeError):
            transport.publish(topic=fake_topic, payload=payload, qos=fake_qos)

    @pytest.mark.it("Triggers callback upon publish completion")
    def test_triggers_callback_upon_paho_on_publish_event(
        self, mocker, mock_mqtt_client, transport, message_info
    ):
        callback = mocker.MagicMock()
        mock_mqtt_client.publish.return_value = message_info

        # Initiate publish
        transport.publish(topic=fake_topic, payload=fake_payload, callback=callback)

        # Check callback is not called
        assert callback.call_count == 0

        # Manually trigger Paho on_publish event handler
        trigger_on_publish(mock_mqtt_client, mid=message_info.mid)

        # Check callback has now been called
        assert callback.call_count == 1

    @pytest.mark.it(
        "Stops Paho's network loop if the MQTTTransport was garbage collected before publish completed"
    )
    def test_stops_loop_after_gc(self, mocker, mock_mqtt_client, collected_transport_weakref):
        trigger_on_publish(mock_mqtt_client, mid=fake_mid)

        assert mock_mqtt_client.loop_stop.call_count == 1
        assert mock_mqtt_client.loop_stop.call_args == mocker.call()

    @pytest.mark.it(
        "Triggers callback upon publish completion when Paho event handler triggered early"
    )
    def test_triggers_callback_when_paho_on_publish_event_called_early(
        self, mocker, mock_mqtt_client, transport, message_info
    ):
        callback = mocker.MagicMock()

        def trigger_early_on_publish(topic, payload, qos):

            # Trigger on_publish before returning message_info
            trigger_on_publish(mock_mqtt_client, mid=message_info.mid)

            # Check callback not yet called
            assert callback.call_count == 0

            return message_info

        mock_mqtt_client.publish.side_effect = trigger_early_on_publish

        # Initiate publish
        transport.publish(topic=fake_topic, payload=fake_payload, callback=callback)

        # Check callback has now been called
        assert callback.call_count == 1

    @pytest.mark.it("Skips callback that is set to 'None' upon publish completion")
    def test_none_callback_upon_paho_on_publish_event(
        self, mocker, mock_mqtt_client, transport, message_info
    ):
        mock_mqtt_client.publish.return_value = message_info
        callback = None

        # Initiate publish
        transport.publish(topic=fake_topic, payload=fake_payload, callback=callback)

        # Manually trigger Paho on_publish event handler
        trigger_on_publish(mock_mqtt_client, mid=message_info.mid)

        # No assertions necessary - not raising an exception => success

    @pytest.mark.it(
        "Skips callback that is set to 'None' upon publish completion when Paho event handler triggered early"
    )
    def test_none_callback_when_paho_on_publish_event_called_early(
        self, mocker, mock_mqtt_client, transport, message_info
    ):
        callback = None

        def trigger_early_on_publish(topic, payload, qos):

            # Trigger on_publish before returning message_info
            trigger_on_publish(mock_mqtt_client, mid=message_info.mid)

            return message_info

        mock_mqtt_client.publish.side_effect = trigger_early_on_publish

        # Initiate publish
        transport.publish(topic=fake_topic, payload=fake_payload, callback=callback)

        # No assertions necessary - not raising an exception => success

    @pytest.mark.it(
        "Handles multiple callbacks from multiple publish operations that complete out of order"
    )
    def test_multiple_callbacks(self, mocker, mock_mqtt_client, transport):
        callback1 = mocker.MagicMock()
        callback2 = mocker.MagicMock()
        callback3 = mocker.MagicMock()

        mid1 = 1
        mid2 = 2
        mid3 = 3

        mock_mqtt_client.publish.side_effect = [
            mqtt.MQTTMessageInfo(mid1),
            mqtt.MQTTMessageInfo(mid2),
            mqtt.MQTTMessageInfo(mid3),
        ]

        # Initiate publish (1 -> 2 -> 3)
        transport.publish(topic=fake_topic, payload=fake_payload, callback=callback1)
        transport.publish(topic=fake_topic, payload=fake_payload, callback=callback2)
        transport.publish(topic=fake_topic, payload=fake_payload, callback=callback3)

        # Check callbacks have not yet been called
        assert callback1.call_count == 0
        assert callback2.call_count == 0
        assert callback3.call_count == 0

        # Manually trigger Paho on_publish event handler (2 -> 3 -> 1)
        trigger_on_publish(mock_mqtt_client, mid=mid2)
        assert callback1.call_count == 0
        assert callback2.call_count == 1
        assert callback3.call_count == 0

        trigger_on_publish(mock_mqtt_client, mid=mid3)
        assert callback1.call_count == 0
        assert callback2.call_count == 1
        assert callback3.call_count == 1

        trigger_on_publish(mock_mqtt_client, mid=mid1)
        assert callback1.call_count == 1
        assert callback2.call_count == 1
        assert callback3.call_count == 1

    @pytest.mark.it("Recovers from Exception in callback")
    def test_callback_raises_exception(
        self, mocker, mock_mqtt_client, transport, message_info, arbitrary_exception
    ):
        callback = mocker.MagicMock(side_effect=arbitrary_exception)
        mock_mqtt_client.publish.return_value = message_info

        transport.publish(topic=fake_topic, payload=fake_payload, callback=callback)
        trigger_on_publish(mock_mqtt_client, mid=message_info.mid)

        # Callback was called, but exception did not propagate
        assert callback.call_count == 1

    @pytest.mark.it("Allows any BaseExceptions raised in callback to propagate")
    def test_callback_raises_base_exception(
        self, mocker, mock_mqtt_client, transport, message_info, arbitrary_base_exception
    ):
        callback = mocker.MagicMock(side_effect=arbitrary_base_exception)
        mock_mqtt_client.publish.return_value = message_info

        transport.publish(topic=fake_topic, payload=fake_payload, callback=callback)
        with pytest.raises(arbitrary_base_exception.__class__) as e_info:
            trigger_on_publish(mock_mqtt_client, mid=message_info.mid)
        assert e_info.value is arbitrary_base_exception

    @pytest.mark.it("Recovers from Exception in callback when Paho event handler triggered early")
    def test_callback_raises_exception_when_paho_on_publish_triggered_early(
        self, mocker, mock_mqtt_client, transport, message_info, arbitrary_exception
    ):
        callback = mocker.MagicMock(side_effect=arbitrary_exception)

        def trigger_early_on_publish(topic, payload, qos):
            trigger_on_publish(mock_mqtt_client, mid=message_info.mid)

            # Should not have yet called callback
            assert callback.call_count == 0

            return message_info

        mock_mqtt_client.publish.side_effect = trigger_early_on_publish

        # Initiate publish
        transport.publish(topic=fake_topic, payload=fake_payload, callback=callback)

        # Callback was called, but exception did not propagate
        assert callback.call_count == 1

    @pytest.mark.it(
        "Allows any BaseExceptions raised in callback when Paho event handler triggered early to propagate"
    )
    def test_callback_raises_base_exception_when_paho_on_publish_triggered_early(
        self, mocker, mock_mqtt_client, transport, message_info, arbitrary_base_exception
    ):
        callback = mocker.MagicMock(side_effect=arbitrary_base_exception)

        def trigger_early_on_publish(topic, payload, qos):
            trigger_on_publish(mock_mqtt_client, mid=message_info.mid)

            # Should not have yet called callback
            assert callback.call_count == 0

            return message_info

        mock_mqtt_client.publish.side_effect = trigger_early_on_publish

        # Initiate publish
        with pytest.raises(arbitrary_base_exception.__class__) as e_info:
            transport.publish(topic=fake_topic, payload=fake_payload, callback=callback)
        assert e_info.value is arbitrary_base_exception

    @pytest.mark.it("Raises a ProtocolClientError if Paho publish raises an unexpected Exception")
    def test_client_raises_unexpected_error(
        self, mocker, mock_mqtt_client, transport, arbitrary_exception
    ):
        mock_mqtt_client.publish.side_effect = arbitrary_exception
        with pytest.raises(errors.ProtocolClientError) as e_info:
            transport.publish(topic=fake_topic, payload=fake_payload, callback=None)
        assert e_info.value.__cause__ is arbitrary_exception

    @pytest.mark.it("Allows any BaseExceptions raised in Paho publish to propagate")
    def test_client_raises_base_exception(
        self, mock_mqtt_client, transport, arbitrary_base_exception
    ):
        mock_mqtt_client.publish.side_effect = arbitrary_base_exception
        with pytest.raises(arbitrary_base_exception.__class__) as e_info:
            transport.publish(topic=fake_topic, payload=fake_payload, callback=None)
        assert e_info.value is arbitrary_base_exception

    @pytest.mark.it("Completes a QoS publish retained after Paho reports no connection")
    @pytest.mark.parametrize("qos", [pytest.param(1, id="QoS 1"), pytest.param(2, id="QoS 2")])
    def test_no_connection_qos_publish_completes_later(
        self, mocker, mock_mqtt_client, transport, qos
    ):
        callback = mocker.MagicMock()
        message_info = mqtt.MQTTMessageInfo(fake_mid)
        message_info.rc = mqtt.MQTT_ERR_NO_CONN
        mock_mqtt_client.publish.return_value = message_info

        transport.publish(fake_topic, fake_payload, qos=qos, callback=callback)

        assert callback.call_count == 0
        trigger_on_publish(mock_mqtt_client, mid=fake_mid)
        assert callback.call_count == 1
        assert callback.call_args == mocker.call()

    @pytest.mark.it("Raises NoConnectionError for a disconnected QoS 0 publish")
    def test_no_connection_qos_zero(self, mock_mqtt_client, transport):
        message_info = mqtt.MQTTMessageInfo(fake_mid)
        message_info.rc = mqtt.MQTT_ERR_NO_CONN
        mock_mqtt_client.publish.return_value = message_info

        with pytest.raises(errors.NoConnectionError):
            transport.publish(fake_topic, fake_payload, qos=0)

    # NOTE: this test tests all mapped Paho error codes, even ones that shouldn't be
    # possible on a publish operation.
    @pytest.mark.it("Raises a custom Exception if MQTTMessageInfo contains a failure code")
    @pytest.mark.parametrize(
        "error_case",
        publish_failure_code_cases,
        ids=[
            "{}->{}".format(case["name"], case["error"].__name__)
            for case in publish_failure_code_cases
        ],
    )
    def test_message_info_contains_failure_code(
        self, mocker, mock_mqtt_client, transport, error_case
    ):
        message_info = mqtt.MQTTMessageInfo(0)
        message_info.rc = error_case["error_code"]
        mock_mqtt_client.publish.return_value = message_info
        with pytest.raises(error_case["error"]):
            transport.publish(topic=fake_topic, payload=fake_payload, callback=None)


@pytest.mark.describe("MQTTTransport - OCCURRENCE: Message Received")
class TestMessageReceived(object):
    @pytest.fixture()
    def message(self):
        message = mqtt.MQTTMessage(mid=fake_mid, topic=fake_topic.encode())
        message.payload = fake_payload
        message.qos = fake_qos
        return message

    @pytest.mark.it(
        "Triggers on_mqtt_message_received_handler event handler upon receiving message"
    )
    def test_calls_event_handler_callback(self, mocker, mock_mqtt_client, transport, message):
        callback = mocker.MagicMock()
        transport.on_mqtt_message_received_handler = callback

        # Manually trigger Paho on_message event_handler
        mock_mqtt_client.on_message(client=mock_mqtt_client, userdata=None, mqtt_message=message)

        # Verify transport.on_mqtt_message_received_handler was called
        assert callback.call_count == 1
        assert callback.call_args == mocker.call(message.topic, message.payload)

    @pytest.mark.it(
        "Stops Paho's network loop if the MQTTTransport was garbage collected before message handling"
    )
    def test_stops_loop_after_gc(
        self, mocker, mock_mqtt_client, collected_transport_weakref, message
    ):
        mock_mqtt_client.on_message(client=mock_mqtt_client, userdata=None, mqtt_message=message)

        assert mock_mqtt_client.loop_stop.call_count == 1
        assert mock_mqtt_client.loop_stop.call_args == mocker.call()

    @pytest.mark.it(
        "Stops Paho's network loop and allows any Exception from disconnect after GC to propagate"
    )
    def test_stops_loop_after_gc_if_disconnect_raises(
        self,
        mock_mqtt_client,
        collected_transport_weakref,
        message,
        arbitrary_exception,
    ):
        mock_mqtt_client.disconnect.side_effect = arbitrary_exception

        with pytest.raises(type(arbitrary_exception)) as e_info:
            mock_mqtt_client.on_message(
                client=mock_mqtt_client, userdata=None, mqtt_message=message
            )

        assert e_info.value is arbitrary_exception
        assert mock_mqtt_client.loop_stop.call_count == 1

    @pytest.mark.it(
        "Skips on_mqtt_message_received_handler event handler if set to 'None' upon receiving message"
    )
    def test_skips_none_event_handler_callback(self, mocker, mock_mqtt_client, transport, message):
        assert transport.on_mqtt_message_received_handler is None

        # Manually trigger Paho on_message event_handler
        mock_mqtt_client.on_message(client=mock_mqtt_client, userdata=None, mqtt_message=message)

        # No further asserts required - this is a test to show that it skips a callback.
        # Not raising an exception == test passed

    @pytest.mark.it("Recovers from Exception in on_mqtt_message_received_handler event handler")
    def test_event_handler_callback_raises_exception(
        self, mocker, mock_mqtt_client, transport, message, arbitrary_exception
    ):
        event_cb = mocker.MagicMock(side_effect=arbitrary_exception)
        transport.on_mqtt_message_received_handler = event_cb

        mock_mqtt_client.on_message(client=mock_mqtt_client, userdata=None, mqtt_message=message)

        # Callback was called, but exception did not propagate
        assert event_cb.call_count == 1

    @pytest.mark.it(
        "Allows any BaseExceptions raised in on_mqtt_message_received_handler event handler to propagate"
    )
    def test_event_handler_callback_raises_base_exception(
        self, mocker, mock_mqtt_client, transport, message, arbitrary_base_exception
    ):
        event_cb = mocker.MagicMock(side_effect=arbitrary_base_exception)
        transport.on_mqtt_message_received_handler = event_cb

        with pytest.raises(arbitrary_base_exception.__class__) as e_info:
            mock_mqtt_client.on_message(
                client=mock_mqtt_client, userdata=None, mqtt_message=message
            )
        assert e_info.value is arbitrary_base_exception


@pytest.mark.describe("MQTTTransport - Misc.")
class TestMisc(object):
    @pytest.mark.it(
        "Handles multiple callbacks from multiple different types of operations that complete out of order"
    )
    def test_multiple_callbacks_multiple_ops(self, mocker, mock_mqtt_client, transport):
        callback1 = mocker.MagicMock()
        callback2 = mocker.MagicMock()
        callback3 = mocker.MagicMock()

        mid1 = 1
        mid2 = 2
        mid3 = 3

        topic1 = "topic1"
        topic2 = "topic2"
        topic3 = "topic3"

        mock_mqtt_client.subscribe.return_value = (fake_rc, mid1)
        mock_mqtt_client.publish.return_value = mqtt.MQTTMessageInfo(mid2)
        mock_mqtt_client.unsubscribe.return_value = (fake_rc, mid3)

        # Initiate operations (1 -> 2 -> 3)
        transport.subscribe(topic=topic1, qos=fake_qos, callback=callback1)
        transport.publish(topic=topic2, payload="payload", qos=fake_qos, callback=callback2)
        transport.unsubscribe(topic=topic3, callback=callback3)

        # Check callbacks have not yet been called
        assert callback1.call_count == 0
        assert callback2.call_count == 0
        assert callback3.call_count == 0

        # Complete the operations out of order (2 -> 3 -> 1)
        trigger_on_publish(mock_mqtt_client, mid=mid2)
        assert callback1.call_count == 0
        assert callback2.call_count == 1
        assert callback3.call_count == 0

        trigger_on_unsubscribe(mock_mqtt_client, mid=mid3)
        assert callback1.call_count == 0
        assert callback2.call_count == 1
        assert callback3.call_count == 1

        trigger_on_subscribe(mock_mqtt_client, mid=mid1)
        assert callback1.call_count == 1
        assert callback2.call_count == 1
        assert callback3.call_count == 1


@pytest.mark.describe("OperationManager")
class TestOperationManager(object):
    @pytest.mark.it("Instantiates with no operation tracking information")
    def test_instantiates_empty(self):
        manager = OperationManager()
        assert len(manager._pending_operations) == 0
        assert len(manager._unknown_operation_completions) == 0
        assert len(manager._cancelled_operation_mids) == 0


@pytest.mark.describe("OperationManager - .register_operation()")
class TestOperationManagerRegisterOperation(object):
    @pytest.fixture(params=[True, False])
    def optional_callback(self, mocker, request):
        if request.param:
            return mocker.MagicMock()
        else:
            return None

    @pytest.mark.it("Begins tracking a pending operation for a new MID")
    @pytest.mark.parametrize(
        "optional_callback",
        [pytest.param(True, id="With callback"), pytest.param(False, id="No callback")],
        indirect=True,
    )
    def test_no_unknown_completion(self, optional_callback):
        manager = OperationManager()
        mid = 1
        register_publish(manager, mid, optional_callback)

        assert len(manager._pending_operations) == 1
        assert manager._pending_operations[mid].operation_type is OperationType.PUBLISH
        assert manager._pending_operations[mid].callback is optional_callback

    @pytest.mark.it("Allows a cancelled MID without a late completion to be reused")
    def test_cancelled_mid_reused_without_late_completion(self, mocker):
        manager = OperationManager()
        mid = 1
        reused_mid_callback = mocker.MagicMock()

        register_publish(manager, mid)
        manager.complete_all_tracked_operations_as_cancelled()
        register_publish(manager, mid, callback=reused_mid_callback)

        assert reused_mid_callback.call_count == 0

        manager.complete_operation(mid)
        assert reused_mid_callback.call_args == mocker.call()

    @pytest.mark.it("Resolves operation tracking when the response arrived before registration")
    def test_early_completion(self):
        manager = OperationManager()
        mid = 1

        # Record a completion before the operation is registered
        manager.complete_operation(mid)
        assert len(manager._unknown_operation_completions) == 1
        assert manager._unknown_operation_completions[mid] is None

        # Register operation that was already completed
        register_publish(manager, mid)

        assert len(manager._unknown_operation_completions) == 0

    @pytest.mark.it(
        "Invokes the callback if provided when the response arrived before registration"
    )
    def test_early_completion_with_callback(self, mocker):
        manager = OperationManager()
        mid = 1
        cb_mock = mocker.MagicMock()

        # Record a completion before the operation is registered
        manager.complete_operation(mid)

        # Register operation that was already completed
        register_publish(manager, mid, cb_mock)

        assert cb_mock.call_count == 1
        assert cb_mock.call_args == mocker.call()

    @pytest.mark.it("Preserves an error when the completion arrives before registration")
    def test_early_completion_with_error(self, mocker):
        manager = OperationManager()
        mid = 1
        callback = mocker.MagicMock()
        error = errors.ProtocolClientError("subscription rejected")

        manager.complete_operation(mid, error=error)
        manager.register_operation(
            mid=mid, callback=callback, operation_type=OperationType.SUBSCRIBE
        )

        assert callback.call_count == 1
        assert callback.call_args == mocker.call(error=error)

    @pytest.mark.it("Recovers from Exception thrown in callback")
    def test_callback_raises_exception(self, mocker, arbitrary_exception):
        manager = OperationManager()
        mid = 1
        cb_mock = mocker.MagicMock(side_effect=arbitrary_exception)

        # Record a completion before the operation is registered
        manager.complete_operation(mid)

        # Register operation that was already completed
        register_publish(manager, mid, cb_mock)

        # Callback was called, but exception did not propagate
        assert cb_mock.call_count == 1

    @pytest.mark.it("Allows any BaseExceptions raised in callback to propagate")
    def test_callback_raises_base_exception(self, mocker, arbitrary_base_exception):
        manager = OperationManager()
        mid = 1
        cb_mock = mocker.MagicMock(side_effect=arbitrary_base_exception)

        # Record a completion before the operation is registered
        manager.complete_operation(mid)

        # Register operation that was already completed
        with pytest.raises(arbitrary_base_exception.__class__) as e_info:
            register_publish(manager, mid, cb_mock)
        assert e_info.value is arbitrary_base_exception

    @pytest.mark.it("Does not invoke the callback until after thread lock has been released")
    def test_callback_called_after_lock_release(self, mocker):
        manager = OperationManager()
        mid = 1
        cb_mock = mocker.MagicMock()

        # Record a completion before the operation is registered
        manager.complete_operation(mid)

        # Set up mock tracking
        lock_spy = mocker.spy(manager, "_lock")
        mock_tracker = mocker.MagicMock()
        calls_during_lock = []

        # When the lock enters, start recording calls to callback
        # When the lock exits, copy the list of calls.

        def track_mocks():
            mock_tracker.attach_mock(cb_mock, "cb")

        def stop_tracking_mocks(*args):
            local_calls_during_lock = calls_during_lock  # do this for python2 compat
            local_calls_during_lock += copy.copy(mock_tracker.mock_calls)
            mock_tracker.reset_mock()

        lock_spy.__enter__.side_effect = track_mocks
        lock_spy.__exit__.side_effect = stop_tracking_mocks

        # Register operation that was already completed
        register_publish(manager, mid, cb_mock)

        # Callback WAS called, but...
        assert cb_mock.call_count == 1

        # Callback WAS NOT called while the lock was held
        assert mocker.call.cb() not in calls_during_lock


@pytest.mark.describe("OperationManager - .complete_operation()")
class TestOperationManagerCompleteOperation(object):
    @pytest.mark.it("Resolves operation tracking when MID corresponds to a pending operation")
    def test_complete_pending_operation(self):
        manager = OperationManager()
        mid = 1

        # Register a pending operation
        register_publish(manager, mid)
        assert len(manager._pending_operations) == 1

        # Complete pending operation
        manager.complete_operation(mid)
        assert len(manager._pending_operations) == 0

    @pytest.mark.it("Invokes callback for a pending operation when resolving")
    def test_complete_pending_operation_callback(self, mocker):
        manager = OperationManager()
        mid = 1
        cb_mock = mocker.MagicMock()

        register_publish(manager, mid, cb_mock)
        assert cb_mock.call_count == 0

        manager.complete_operation(mid)
        assert cb_mock.call_count == 1
        assert cb_mock.call_args == mocker.call()

    @pytest.mark.it("Invokes callback with an error for a failed pending operation")
    def test_complete_pending_operation_callback_with_error(self, mocker):
        manager = OperationManager()
        mid = 1
        callback = mocker.MagicMock()
        error = errors.ProtocolClientError("subscription rejected")

        manager.register_operation(
            mid=mid, callback=callback, operation_type=OperationType.SUBSCRIBE
        )
        manager.complete_operation(mid, error=error)

        assert callback.call_count == 1
        assert callback.call_args == mocker.call(error=error)

    @pytest.mark.it("Recovers from Exception thrown in callback")
    def test_callback_raises_exception(self, mocker, arbitrary_exception):
        manager = OperationManager()
        mid = 1
        cb_mock = mocker.MagicMock(side_effect=arbitrary_exception)

        register_publish(manager, mid, cb_mock)
        assert cb_mock.call_count == 0

        manager.complete_operation(mid)
        # Callback was called but exception did not propagate
        assert cb_mock.call_count == 1

    @pytest.mark.it("Allows any BaseExceptions raised in callback to propagate")
    def test_callback_raises_base_exception(self, mocker, arbitrary_base_exception):
        manager = OperationManager()
        mid = 1
        cb_mock = mocker.MagicMock(side_effect=arbitrary_base_exception)

        register_publish(manager, mid, cb_mock)
        assert cb_mock.call_count == 0

        with pytest.raises(arbitrary_base_exception.__class__) as e_info:
            manager.complete_operation(mid)
        assert e_info.value is arbitrary_base_exception

    @pytest.mark.it("Retains a completion if MID does not correspond to a pending operation")
    def test_unknown_completion(self):
        manager = OperationManager()
        mid = 1

        manager.complete_operation(mid)
        assert len(manager._unknown_operation_completions) == 1
        assert manager._unknown_operation_completions[mid] is None

    @pytest.mark.it("Discards a late completion for a cancelled MID")
    def test_late_completion_for_cancelled_mid(self, mocker):
        manager = OperationManager()
        mid = 1
        cancelled_callback = mocker.MagicMock()
        reused_mid_callback = mocker.MagicMock()

        register_publish(manager, mid, callback=cancelled_callback)
        manager.complete_all_tracked_operations_as_cancelled()
        manager.complete_operation(mid)
        register_publish(manager, mid, callback=reused_mid_callback)

        assert cancelled_callback.call_args == mocker.call(cancelled=True)
        assert reused_mid_callback.call_count == 0

        manager.complete_operation(mid)
        assert reused_mid_callback.call_args == mocker.call()

    @pytest.mark.it("Does not invoke the callback until after thread lock has been released")
    def test_callback_called_after_lock_release(self, mocker):
        manager = OperationManager()
        mid = 1
        cb_mock = mocker.MagicMock()

        # Set up an operation and save the callback
        register_publish(manager, mid, cb_mock)

        # Set up mock tracking
        lock_spy = mocker.spy(manager, "_lock")
        mock_tracker = mocker.MagicMock()
        calls_during_lock = []

        # When the lock enters, start recording calls to callback
        # When the lock exits, copy the list of calls.

        def track_mocks():
            mock_tracker.attach_mock(cb_mock, "cb")

        def stop_tracking_mocks(*args):
            local_calls_during_lock = calls_during_lock  # do this for python2 compat
            local_calls_during_lock += copy.copy(mock_tracker.mock_calls)
            mock_tracker.reset_mock()

        lock_spy.__enter__.side_effect = track_mocks
        lock_spy.__exit__.side_effect = stop_tracking_mocks

        # Complete the operation
        manager.complete_operation(mid)

        # Callback WAS called, but...
        assert cb_mock.call_count == 1
        assert cb_mock.call_args == mocker.call()

        # Callback WAS NOT called while the lock was held
        assert mocker.call.cb() not in calls_during_lock


@pytest.mark.describe("OperationManager - .stop_tracking_non_publish_operations()")
class TestOperationManagerStopTrackingNonPublishOperations(object):
    @pytest.mark.it("Preserves publishes and tombstones subscribe and unsubscribe MIDs")
    def test_stops_non_publish_tracking(self, mocker):
        manager = OperationManager()
        publish_callback = mocker.MagicMock()
        subscribe_callback = mocker.MagicMock()
        unsubscribe_callback = mocker.MagicMock()
        manager.register_operation(
            mid=1, callback=publish_callback, operation_type=OperationType.PUBLISH
        )
        manager.register_operation(
            mid=2, callback=subscribe_callback, operation_type=OperationType.SUBSCRIBE
        )
        manager.register_operation(
            mid=3, callback=unsubscribe_callback, operation_type=OperationType.UNSUBSCRIBE
        )

        manager.stop_tracking_non_publish_operations()

        assert list(manager._pending_operations) == [1]
        assert manager._pending_operations[1].operation_type is OperationType.PUBLISH
        assert manager._pending_operations[1].callback is publish_callback
        assert manager._cancelled_operation_mids == {2, 3}
        assert publish_callback.call_count == 0
        assert subscribe_callback.call_count == 0
        assert unsubscribe_callback.call_count == 0

    @pytest.mark.it("Discards a late completion for a non-publish operation no longer tracked")
    def test_discards_late_completion(self, mocker):
        manager = OperationManager()
        callback = mocker.MagicMock()
        manager.register_operation(mid=1, callback=callback, operation_type=OperationType.SUBSCRIBE)
        manager.stop_tracking_non_publish_operations()

        manager.complete_operation(mid=1)

        assert callback.call_count == 0
        assert manager._cancelled_operation_mids == set()
        assert manager._unknown_operation_completions == {}


@pytest.mark.describe("OperationManager - .complete_all_tracked_operations_as_cancelled()")
class TestOperationManagerCompleteAllTrackedOperationsAsCancelled(object):
    @pytest.mark.it("Removes pending callbacks and retains their MIDs as cancelled")
    def test_cancel_pending_ops(self):
        manager = OperationManager()

        # Register pending operations
        register_publish(manager, mid=1)
        manager.register_operation(mid=2, callback=None, operation_type=OperationType.SUBSCRIBE)
        manager.register_operation(mid=3, callback=None, operation_type=OperationType.UNSUBSCRIBE)
        assert len(manager._pending_operations) == 3

        # Complete tracked operations as cancelled
        manager.complete_all_tracked_operations_as_cancelled()
        assert len(manager._pending_operations) == 0
        assert manager._cancelled_operation_mids == {1, 2, 3}

    @pytest.mark.it("Removes all MID tracking for unknown operation completions")
    def test_remove_unknown_completions(self):
        manager = OperationManager()

        # Add unknown operation completions
        manager.complete_operation(mid=2111)
        manager.complete_operation(mid=30045)
        manager.complete_operation(mid=2345)
        assert len(manager._unknown_operation_completions) == 3

        # Complete tracked operations as cancelled
        manager.complete_all_tracked_operations_as_cancelled()
        assert len(manager._unknown_operation_completions) == 0

    @pytest.mark.it("Invokes callbacks with cancelled=True for each tracked operation")
    def test_op_callback_completion(self, mocker):
        manager = OperationManager()

        # Register pending operations
        cb_mock1 = mocker.MagicMock()
        register_publish(manager, mid=1, callback=cb_mock1)
        cb_mock2 = mocker.MagicMock()
        manager.register_operation(mid=2, callback=cb_mock2, operation_type=OperationType.SUBSCRIBE)
        manager.register_operation(mid=3, callback=None, operation_type=OperationType.UNSUBSCRIBE)
        assert cb_mock1.call_count == 0
        assert cb_mock2.call_count == 0

        # Complete tracked operations as cancelled
        manager.complete_all_tracked_operations_as_cancelled()
        assert cb_mock1.call_count == 1
        assert cb_mock1.call_args == mocker.call(cancelled=True)
        assert cb_mock2.call_count == 1
        assert cb_mock2.call_args == mocker.call(cancelled=True)

    @pytest.mark.it("Recovers from Exception thrown in callback")
    def test_callback_raises_exception(self, mocker, arbitrary_exception):
        manager = OperationManager()

        # Register pending operation
        cb_mock = mocker.MagicMock(side_effect=arbitrary_exception)
        register_publish(manager, mid=1, callback=cb_mock)
        assert cb_mock.call_count == 0

        # Complete tracked operations as cancelled
        manager.complete_all_tracked_operations_as_cancelled()

        # Callback was called but exception did not propagate
        assert cb_mock.call_count == 1

    @pytest.mark.it("Allows any BaseExceptions raised in callback to propagate")
    def test_callback_raises_base_exception(self, mocker, arbitrary_base_exception):
        manager = OperationManager()

        # Register pending operation
        cb_mock = mocker.MagicMock(side_effect=arbitrary_base_exception)
        register_publish(manager, mid=1, callback=cb_mock)
        assert cb_mock.call_count == 0

        # When completing operations, Base Exception propagates
        with pytest.raises(arbitrary_base_exception.__class__) as e_info:
            manager.complete_all_tracked_operations_as_cancelled()
        assert e_info.value is arbitrary_base_exception

    @pytest.mark.it("Does not invoke callbacks until after thread lock has been released")
    def test_callback_called_after_lock_release(self, mocker):
        manager = OperationManager()
        cb_mock1 = mocker.MagicMock()
        cb_mock2 = mocker.MagicMock()

        # Set up operations and save the callback
        register_publish(manager, mid=1, callback=cb_mock1)
        manager.register_operation(mid=2, callback=cb_mock2, operation_type=OperationType.SUBSCRIBE)

        # Set up mock tracking
        lock_spy = mocker.spy(manager, "_lock")
        mock_tracker = mocker.MagicMock()
        calls_during_lock = []

        # When the lock enters, start recording calls to callback
        # When the lock exits, copy the list of calls.

        def track_mocks():
            mock_tracker.attach_mock(cb_mock1, "cb1")
            mock_tracker.attach_mock(cb_mock2, "cb2")

        def stop_tracking_mocks(*args):
            local_calls_during_lock = calls_during_lock  # do this for python2 compat
            local_calls_during_lock += copy.copy(mock_tracker.mock_calls)
            mock_tracker.reset_mock()

        lock_spy.__enter__.side_effect = track_mocks
        lock_spy.__exit__.side_effect = stop_tracking_mocks

        # Complete tracked operations as cancelled
        manager.complete_all_tracked_operations_as_cancelled()

        # Callbacks WERE called, but...
        assert cb_mock1.call_count == 1
        assert cb_mock1.call_args == mocker.call(cancelled=True)
        assert cb_mock2.call_count == 1
        assert cb_mock2.call_args == mocker.call(cancelled=True)

        # Callbacks WERE NOT called while the lock was held
        assert mocker.call.cb1() not in calls_during_lock
        assert mocker.call.cb2() not in calls_during_lock
