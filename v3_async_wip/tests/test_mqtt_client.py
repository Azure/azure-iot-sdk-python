# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

from v3_async_wip.mqtt_client import MQTTClient, MQTTError, MQTTConnectionFailedError
from v3_async_wip.mqtt_client import (
    expected_connect_rc,
    expected_subscribe_rc,
    expected_unsubscribe_rc,
    expected_publish_rc,
    expected_on_connect_rc,
    expected_on_disconnect_rc,
)
from azure.iot.device.common import ProxyOptions
import paho.mqtt.client as mqtt
import asyncio
import logging
import pytest
import sys
import time
from concurrent.futures import ThreadPoolExecutor

logging.basicConfig(level=logging.DEBUG)


fake_device_id = "MyDevice"
fake_hostname = "fake.hostname"
fake_password = "fake_password"
fake_username = fake_hostname + "/" + fake_device_id
fake_port = 443
fake_keepalive = 1234
fake_ws_path = "/fake/path"
fake_topic = "/some/topic/"
fake_payload = "message content"

PAHO_STATE_NEW = "NEW"
PAHO_STATE_DISCONNECTED = "DISCONNECTED"
PAHO_STATE_CONNECTED = "CONNECTED"
PAHO_STATE_CONNECTION_LOST = "CONNECTION_LOST"

UNEXPECTED_PAHO_RC = 255

ACK_DELAY = 1


@pytest.fixture(scope="module")
def paho_threadpool():
    # Paho has a single thread it invokes handlers on
    tpe = ThreadPoolExecutor(max_workers=1)
    yield tpe
    tpe.shutdown()


# TODO: might want some more advanced network loop checks
@pytest.fixture
def mock_paho(mocker, paho_threadpool):
    """This mock is quite a bit more complicated than your average mock in order to
    capture some of the weirder Paho behaviors"""
    mock_paho = mocker.MagicMock()
    # Define a fake internal connection state for Paho.
    # You should not ever have to touch this manually. Please don't.
    #
    # It is further worth noting that this state is different from the one used in
    # the real implementation, because Paho doesn't store true connection state, just a
    # "desired" connection state (which itself is different from our client's .desire_connection).
    # The true connection state is derived by other means (sockets).
    # For simplicity, I've rolled all the information relevant to mocking behavior into a
    # 4-state value.
    mock_paho._state = PAHO_STATE_NEW
    # Indicates whether or not invocations should automatically trigger callbacks
    mock_paho._manual_mode = False
    # Indicates whether or not invocations should trigger callbacks immediately
    # (i.e. before invocation return)
    # NOTE: While the "normal" behavior we can expect is NOT an early ack, we set early ack
    # as the default for test performance reasons
    mock_paho._early_ack = True
    # Default rc value to return on invocations of method mocks
    # NOTE: There is no _disconnect_rc because disconnect return values are deterministic
    # See the implementation of trigger_on_disconnect and the mock disconnect below.
    mock_paho._connect_rc = mqtt.MQTT_ERR_SUCCESS
    mock_paho._publish_rc = mqtt.MQTT_ERR_SUCCESS
    mock_paho._subscribe_rc = mqtt.MQTT_ERR_SUCCESS
    mock_paho._unsubscribe_rc = mqtt.MQTT_ERR_SUCCESS
    # Last mid that was returned. Will be incremented over time (see _get_next_mid())
    # NOTE: 0 means no mid has been sent yet
    mock_paho._last_mid = 0

    # Utility helpers
    # TODO: this should probably trigger on_disconnect if failed
    def trigger_on_connect(rc=mqtt.CONNACK_ACCEPTED):
        if rc == mqtt.CONNACK_ACCEPTED:
            # State is only set to connected if successfully connecting
            mock_paho._state = PAHO_STATE_CONNECTED
        else:
            # If it fails it ends up in a "new" state.
            mock_paho._state = PAHO_STATE_NEW
        if not mock_paho._early_ack:
            paho_threadpool.submit(time.sleep, ACK_DELAY)
        paho_threadpool.submit(
            mock_paho.on_connect, client=mock_paho, userdata=None, flags=None, rc=rc
        )

    mock_paho.trigger_on_connect = trigger_on_connect

    def trigger_on_disconnect(rc=mqtt.MQTT_ERR_SUCCESS):
        if mock_paho._state == PAHO_STATE_CONNECTED:
            mock_paho._state = PAHO_STATE_CONNECTION_LOST
        if not mock_paho._early_ack:
            paho_threadpool.submit(time.sleep, ACK_DELAY)
        paho_threadpool.submit(mock_paho.on_disconnect, client=mock_paho, userdata=None, rc=rc)

    mock_paho.trigger_on_disconnect = trigger_on_disconnect

    def trigger_on_subscribe(mid=None):
        if not mid:
            mid = mock_paho._last_mid
        if not mock_paho._early_ack:
            paho_threadpool.submit(time.sleep, ACK_DELAY)
        paho_threadpool.submit(
            mock_paho.on_subscribe, client=mock_paho, userdata=None, mid=mid, granted_qos=1
        )

    mock_paho.trigger_on_subscribe = trigger_on_subscribe

    def trigger_on_unsubscribe(mid=None):
        if not mid:
            mid = mock_paho._last_mid
        if not mock_paho._early_ack:
            paho_threadpool.submit(time.sleep, ACK_DELAY)
        paho_threadpool.submit(mock_paho.on_unsubscribe, client=mock_paho, userdata=None, mid=mid)

    mock_paho.trigger_on_unsubscribe = trigger_on_unsubscribe

    def trigger_on_publish(mid):
        if not mid:
            mid = mock_paho._last_mid
        if not mock_paho._early_ack:
            paho_threadpool.submit(time.sleep, ACK_DELAY)
        paho_threadpool.submit(mock_paho.on_publish, client=mock_paho, userdata=None, mid=mid)

    mock_paho.trigger_on_publish = trigger_on_publish

    # NOTE: This should not be necessary to use in any tests themselves.
    def _get_next_mid():
        mock_paho._last_mid += 1
        mid = mock_paho._last_mid
        return mid

    mock_paho._get_next_mid = _get_next_mid

    # Method mocks
    def is_connected(*args, **kwargs):
        """
        NOT TO BE CONFUSED WITH MQTTClient.is_connected()!!!!
        This is Paho's inner state. It returns True even if connection has been lost.
        """
        return mock_paho._state != PAHO_STATE_DISCONNECTED

    def connect(*args, **kwargs):
        # Only trigger completion if not in manual mode
        # Only trigger completion if returning success
        if not mock_paho._manual_mode and mock_paho._connect_rc == mqtt.MQTT_ERR_SUCCESS:
            mock_paho.trigger_on_connect()
        return mock_paho._connect_rc

    def disconnect(*args, **kwargs):
        # NOTE: THERE IS NO WAY TO OVERRIDE THIS RETURN VALUE AS IT IS DETERMINISTIC
        # BASED ON THE PAHO STATE
        if mock_paho._state == PAHO_STATE_CONNECTED:
            mock_paho._state = PAHO_STATE_DISCONNECTED
            if not mock_paho._manual_mode:
                mock_paho.trigger_on_disconnect()
            rc = mqtt.MQTT_ERR_SUCCESS
        else:
            mock_paho._state = PAHO_STATE_DISCONNECTED
            rc = mqtt.MQTT_ERR_NO_CONN
        return rc

    def subscribe(*args, **kwargs):
        if mock_paho._subscribe_rc != mqtt.MQTT_ERR_SUCCESS:
            mid = None
        else:
            mid = mock_paho._get_next_mid()
            if not mock_paho._manual_mode:
                mock_paho.trigger_on_subscribe(mid)
        return (mock_paho._subscribe_rc, mid)

    def unsubscribe(*args, **kwargs):
        if mock_paho._unsubscribe_rc != mqtt.MQTT_ERR_SUCCESS:
            mid = None
        else:
            mid = mock_paho._get_next_mid()
            if not mock_paho._manual_mode:
                mock_paho.trigger_on_unsubscribe(mid)
        return (mock_paho._unsubscribe_rc, mid)

    def publish(*args, **kwargs):
        # Unlike subscribe and unsubscribe, publish still returns a mid in the case of failure
        mid = mock_paho._get_next_mid()
        if not mock_paho._manual_mode:
            mock_paho.trigger_on_publish(mid)
        # Not going to bother mocking out the details of this message info since we just use it
        # for the rc and mid
        msg_info = mqtt.MQTTMessageInfo(mid)
        msg_info.rc = mock_paho._publish_rc
        return msg_info

    mock_paho.is_connected.side_effect = is_connected
    mock_paho.connect.side_effect = connect
    mock_paho.disconnect.side_effect = disconnect
    mock_paho.subscribe.side_effect = subscribe
    mock_paho.unsubscribe.side_effect = unsubscribe
    mock_paho.publish.side_effect = publish

    mocker.patch.object(mqtt, "Client", return_value=mock_paho)

    return mock_paho


@pytest.fixture
async def fresh_client(mock_paho):
    # NOTE: Implicitly imports the mocked Paho MQTT Client due to patch in mock_paho
    client = MQTTClient(
        client_id=fake_device_id, hostname=fake_hostname, port=fake_port, auto_reconnect=False
    )
    assert client._mqtt_client is mock_paho
    yield client

    # Reset any mock paho settings that might affect ability to disconnect
    mock_paho._manual_mode = False
    await client.disconnect()


@pytest.fixture
async def client(fresh_client):
    return fresh_client


# Helper functions for changing client state.
# Always use these to set the state during tests so that the client state and Paho state
# do not get out of sync
def client_set_connected(client):
    """Set the client to a connected state"""
    client._connected = True
    client._desire_connection = True
    client._mqtt_client._state = PAHO_STATE_CONNECTED


def client_set_disconnected(client):
    """Set the client to an (intentionally) disconnected state"""
    client._connected = False
    client._desire_connection = False
    client._mqtt_client._state = PAHO_STATE_DISCONNECTED


def client_set_connection_dropped(client):
    """Set the client to a state representing an unexpected disconnect"""
    client._connected = False
    client._desire_connection = True
    client._mqtt_client._state = PAHO_STATE_CONNECTION_LOST


def client_set_fresh(client):
    """Set a client to a fresh state.
    This could either be a client that has never been connected or a client that has had a
    connection failure (even if it was previously connected). This is because Paho resets its
    state when making a connection attempt.

    FOR ALL INTENTS AND PURPOSES A CLIENT IN THIS STATE SHOULD BEHAVE EXACTLY THE SAME AS
    ONE IN A DISCONNECTED STATE. USE THE SAME TESTS FOR BOTH.
    """
    client._connected = False
    client._desire_connection = False
    client._mqtt_client._state = PAHO_STATE_NEW


# Pytest parametrizations
early_ack_params = [
    pytest.param(False, id="Response after invocation returns"),
    pytest.param(True, id="Response before invocation returns"),
]

# NOTE: disconnect rcs are not necessary as disconnect can't fail and the result is deterministic
# (See mock_paho implementation for more information)
connect_failed_rc_params = [
    pytest.param(UNEXPECTED_PAHO_RC, id="Unexpected Paho result"),
]
subscribe_failed_rc_params = [
    pytest.param(mqtt.MQTT_ERR_NO_CONN, id="MQTT_ERR_NO_CONN"),
    pytest.param(UNEXPECTED_PAHO_RC, id="Unexpected Paho result"),
]
unsubscribe_failed_rc_params = [
    pytest.param(mqtt.MQTT_ERR_NO_CONN, id="MQTT_ERR_NO_CONN"),
    pytest.param(UNEXPECTED_PAHO_RC, id="Unexpected Paho result"),
]
publish_failed_rc_params = [
    # Publish can also return MQTT_ERR_NO_CONN, but it isn't a failure
    pytest.param(mqtt.MQTT_ERR_QUEUE_SIZE, id="MQTT_ERR_QUEUE_SIZE"),
    pytest.param(UNEXPECTED_PAHO_RC, id="Unexpected Paho result"),
]
on_connect_failed_rc_params = [
    pytest.param(mqtt.CONNACK_REFUSED_PROTOCOL_VERSION, id="CONNACK_REFUSED_PROTOCOL_VERSION"),
    pytest.param(
        mqtt.CONNACK_REFUSED_IDENTIFIER_REJECTED, id="CONNACK_REFUSED_IDENTIFIER_REJECTED"
    ),
    pytest.param(mqtt.CONNACK_REFUSED_SERVER_UNAVAILABLE, id="CONNACK_REFUSED_SERVER_UNAVAILABLE"),
    pytest.param(
        mqtt.CONNACK_REFUSED_BAD_USERNAME_PASSWORD, id="CONNACK_REFUSED_BAD_USERNAME_PASSWORD"
    ),
    pytest.param(mqtt.CONNACK_REFUSED_NOT_AUTHORIZED, id="CONNACK_REFUSED_NOT_AUTHORIZED"),
    pytest.param(
        UNEXPECTED_PAHO_RC, id="Unexpected Paho result"
    ),  # Reserved for future use defined by MQTT
]
on_disconnect_failed_rc_params = [
    pytest.param(mqtt.MQTT_ERR_CONN_REFUSED, id="MQTT_ERR_CONN_REFUSED"),
    pytest.param(mqtt.MQTT_ERR_CONN_LOST, id="MQTT_ERR_CONN_LOST"),
    pytest.param(mqtt.MQTT_ERR_KEEPALIVE, id="MQTT_ERR_KEEPALIVE"),
    pytest.param(UNEXPECTED_PAHO_RC, id="Unexpected Paho result"),
]


# Validate the above are correct so failure will occur if tests are out of date.
def validate_rc_params(rc_params, expected_rc, no_fail=[]):
    # Ignore success, and any other failing rcs that don't result in failure
    ignore = [mqtt.MQTT_ERR_SUCCESS, mqtt.CONNACK_ACCEPTED] + no_fail
    # Assert that all expected rcs (other than ignored vals) are in our rc params
    for rc in [v for v in expected_rc if v not in ignore]:
        assert True in [rc in param.values for param in rc_params]
    # Assert that our unexpected rc stand-in is in our rc params
    assert True in [UNEXPECTED_PAHO_RC in param.values for param in rc_params]
    # Assert that there are not more values in our rc params than we would expect
    expected_len = len(expected_rc) - 1  # No success
    expected_len += 1  # We have an additional unexpected value
    expected_len -= len(no_fail)  # No non-fails
    assert len(rc_params) == expected_len


validate_rc_params(connect_failed_rc_params, expected_connect_rc)
validate_rc_params(subscribe_failed_rc_params, expected_subscribe_rc)
validate_rc_params(unsubscribe_failed_rc_params, expected_unsubscribe_rc)
validate_rc_params(publish_failed_rc_params, expected_publish_rc, no_fail=[mqtt.MQTT_ERR_NO_CONN])
validate_rc_params(on_connect_failed_rc_params, expected_on_connect_rc)
validate_rc_params(on_disconnect_failed_rc_params, expected_on_disconnect_rc)


###############################################################################
#                             TESTS START                                     #
###############################################################################


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
    async def test_hostname(self, mocker):
        mocker.patch.object(mqtt, "Client")
        client = MQTTClient(client_id=fake_device_id, hostname=fake_hostname, port=fake_port)
        assert client._hostname == fake_hostname

    @pytest.mark.it("Stores the provided port value")
    async def test_port(self, mocker):
        mocker.patch.object(mqtt, "Client")
        client = MQTTClient(client_id=fake_device_id, hostname=fake_hostname, port=fake_port)
        assert client._port == fake_port

    @pytest.mark.it("Stores the provided keepalive value (if provided)")
    async def test_keepalive(self, mocker):
        mocker.patch.object(mqtt, "Client")
        client = MQTTClient(
            client_id=fake_device_id,
            hostname=fake_hostname,
            port=fake_port,
            keep_alive=fake_keepalive,
        )
        assert client._keep_alive == fake_keepalive

    @pytest.mark.it("Stores the provided auto_reconnect value (if provided)")
    @pytest.mark.parametrize(
        "value", [pytest.param(True, id="Enabled"), pytest.param(False, id="Disabled")]
    )
    async def test_auto_reconnect(self, mocker, value):
        mocker.patch.object(mqtt, "Client")
        client = MQTTClient(
            client_id=fake_device_id, hostname=fake_hostname, port=fake_port, auto_reconnect=value
        )
        assert client._auto_reconnect == value

    @pytest.mark.it("Stores the provided reconnect_interval value (if provided)")
    async def test_reconnect_interval(self, mocker):
        mocker.patch.object(mqtt, "Client")
        my_interval = 5
        client = MQTTClient(
            client_id=fake_device_id,
            hostname=fake_hostname,
            port=fake_port,
            auto_reconnect=True,
            reconnect_interval=my_interval,
        )
        assert client._reconnect_interval == my_interval

    @pytest.mark.it("Creates and stores an instance of the Paho MQTT Client")
    async def test_instantiates_mqtt_client(self, mocker, transport):
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
    async def test_ssl_context(self, mocker, transport):
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
    async def test_ssl_context_default(self, mocker, transport):
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
    async def test_proxy_options(self, mocker, proxy_options, transport):
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

    @pytest.mark.it("Does not set any proxy on the Paho MQTT Client if no ProxyOptions is provided")
    async def test_no_proxy_options(self, mocker, transport):
        mock_paho = mocker.patch.object(mqtt, "Client").return_value

        MQTTClient(
            client_id=fake_device_id,
            hostname=fake_hostname,
            port=fake_port,
            transport=transport,
        )

        # Proxy was not set
        assert mock_paho.proxy_set.call_count == 0

    @pytest.mark.it(
        "Sets the websockets path on the Paho MQTT Client using the provided value if using websockets"
    )
    async def test_ws_path(self, mocker):
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

    @pytest.mark.it("Does not set the websocket path on the Paho MQTT Client if it is not provided")
    async def test_no_ws_path(self, mocker):
        mock_paho = mocker.patch.object(mqtt, "Client").return_value

        MQTTClient(
            client_id=fake_device_id, hostname=fake_hostname, port=fake_port, transport="websockets"
        )

        # Websockets path was not set
        assert mock_paho.ws_set_options.call_count == 0

    @pytest.mark.it(
        "Does not set the websocket path on the Paho MQTT Client if not using websockets"
    )
    async def test_ws_path_no_ws(self, mocker):
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

    @pytest.mark.it("Sets the initial connection state")
    async def test_connection_state(self, mocker):
        mocker.patch.object(mqtt, "Client")
        client = MQTTClient(client_id=fake_device_id, hostname=fake_hostname, port=fake_port)
        assert not client._connected
        assert not client._desire_connection

    @pytest.mark.it("Sets the reconnect daemon to None")
    async def test_reconnect_daemon(self, mocker):
        mocker.patch.object(mqtt, "Client")
        client = MQTTClient(client_id=fake_device_id, hostname=fake_hostname, port=fake_port)
        assert client._reconnect_daemon is None

    @pytest.mark.it("Sets initial operation tracking structures")
    async def test_pending_ops(self, mocker):
        mocker.patch.object(mqtt, "Client")
        client = MQTTClient(client_id=fake_device_id, hostname=fake_hostname, port=fake_port)
        assert client._pending_subs == {}
        assert client._pending_unsubs == {}
        assert client._pending_pubs == {}

    @pytest.mark.it("Creates an incoming message queue")
    async def test_incoming_messages_unfiltered(self, mocker):
        mocker.patch.object(mqtt, "Client")
        client = MQTTClient(client_id=fake_device_id, hostname=fake_hostname, port=fake_port)
        assert isinstance(client._incoming_messages, asyncio.Queue)
        assert client._incoming_messages.empty()

    @pytest.mark.it("Sets initial filtered message queue structures")
    async def test_incoming_messages_filtered(self, mocker):
        mocker.patch.object(mqtt, "Client")
        client = MQTTClient(client_id=fake_device_id, hostname=fake_hostname, port=fake_port)
        assert client._incoming_filtered_messages == {}

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


@pytest.mark.describe("MQTTClient - .is_connected()")
class TestIsConnected(object):
    @pytest.mark.it("Returns a boolean indicating the connection status")
    @pytest.mark.parametrize(
        "connected", [pytest.param(True, id="Connected"), pytest.param(False, id="Disconnected")]
    )
    def test_returns_value(self, client, connected):
        if connected:
            client_set_connected(client)
        else:
            client_set_disconnected(client)
        assert client.is_connected() == connected


@pytest.mark.describe("MQTTClient - .add_incoming_message_filter()")
class TestAddIncomingMessageFilter(object):
    @pytest.mark.it("Adds a new incoming message queue for the given topic")
    def test_adds_queue(self, client):
        assert len(client._incoming_filtered_messages) == 0

        client.add_incoming_message_filter(fake_topic)

        assert len(client._incoming_filtered_messages) == 1
        assert isinstance(client._incoming_filtered_messages[fake_topic], asyncio.Queue)
        assert client._incoming_filtered_messages[fake_topic].empty()

    @pytest.mark.it("Adds a callback for the given topic to the Paho MQTT Client")
    def test_adds_callback(self, mocker, client, mock_paho):
        assert mock_paho.message_callback_add.call_count == 0

        client.add_incoming_message_filter(fake_topic)

        assert mock_paho.message_callback_add.call_count == 1
        assert mock_paho.message_callback_add.call_args == mocker.call(fake_topic, mocker.ANY)

    @pytest.mark.it(
        "Raises a ValueError and does not add an incoming message queue or add a callback to the Paho MQTT Client if the filter already exists"
    )
    def test_filter_exists(self, client, mock_paho):
        client.add_incoming_message_filter(fake_topic)
        assert fake_topic in client._incoming_filtered_messages
        assert len(client._incoming_filtered_messages) == 1
        existing_queue = client._incoming_filtered_messages[fake_topic]
        assert existing_queue.empty()
        assert mock_paho.message_callback_add.call_count == 1

        # Try and add the same topic filter again
        with pytest.raises(ValueError):
            client.add_incoming_message_filter(fake_topic)

        # No additional filter was added, nor were changes made to the existing one
        assert fake_topic in client._incoming_filtered_messages
        assert len(client._incoming_filtered_messages) == 1
        assert client._incoming_filtered_messages[fake_topic] == existing_queue
        assert existing_queue.empty()
        assert mock_paho.message_callback_add.call_count == 1

    # NOTE: To see this filter in action, see the message receive tests


@pytest.mark.describe("MQTTClient - .remove_incoming_message_filter()")
class TestRemoveIncomingMessageFilter(object):
    @pytest.mark.it("Removes the callback for the given topic from the Paho MQTT Client")
    def test_removes_callback(self, mocker, client, mock_paho):
        # Add a filter
        client.add_incoming_message_filter(fake_topic)
        assert mock_paho.message_callback_remove.call_count == 0

        # Remove
        client.remove_incoming_message_filter(fake_topic)

        # Callback was removed
        assert mock_paho.message_callback_remove.call_count == 1
        assert mock_paho.message_callback_remove.call_args == mocker.call(fake_topic)

    @pytest.mark.it("Removes the incoming message queue for the given topic")
    def test_removes_queue(self, client):
        # Add a filter
        client.add_incoming_message_filter(fake_topic)
        assert fake_topic in client._incoming_filtered_messages

        # Remove
        client.remove_incoming_message_filter(fake_topic)

        # Filter queue was removed
        assert fake_topic not in client._incoming_filtered_messages

    @pytest.mark.it(
        "Raises ValueError and does not remove any incoming message queues or remove any callbacks from the Paho MQTT Client if the filter does not exist"
    )
    async def test_filter_does_not_exist(self, mocker, client, mock_paho):
        # Add a different filter
        client.add_incoming_message_filter(fake_topic)
        assert fake_topic in client._incoming_filtered_messages
        assert len(client._incoming_filtered_messages) == 1
        existing_queue = client._incoming_filtered_messages[fake_topic]
        fake_item = mocker.MagicMock()
        await existing_queue.put(fake_item)
        assert existing_queue.qsize() == 1
        assert mock_paho.message_callback_remove.call_count == 0

        # Remove a topic that has not yet been added
        even_faker_topic = "even/faker_topic"
        assert even_faker_topic != fake_topic
        with pytest.raises(ValueError):
            client.remove_incoming_message_filter(even_faker_topic)

        # No filter was removed or modified
        assert fake_topic in client._incoming_filtered_messages
        assert len(client._incoming_filtered_messages) == 1
        existing_queue = client._incoming_filtered_messages[fake_topic]
        assert existing_queue.qsize() == 1
        item = await existing_queue.get()
        assert item is fake_item
        assert mock_paho.message_callback_remove.call_count == 0


# NOTE: Because clients in Disconnected, Connection Dropped, and Fresh states have the same
# behaviors during a connect, define a parent class that can be subclassed so tests don't have
# to be written twice.
class ConnectWithClientNotConnectedTests(object):
    @pytest.mark.it(
        "Starts the reconnect daemon and stores its task if auto_reconnect is enabled and the daemon is not yet running"
    )
    async def test_reconnect_daemon_enabled_not_running(self, client):
        client._auto_reconnect = True
        assert client._reconnect_daemon is None

        await client.connect()

        assert isinstance(client._reconnect_daemon, asyncio.Task)
        assert not client._reconnect_daemon.done()

    @pytest.mark.it("Does not start the reconnect daemon if auto_reconnect is disabled")
    async def test_reconnect_daemon_disabled(self, client):
        assert client._auto_reconnect is False
        assert client._reconnect_daemon is None

        await client.connect()

        assert client._reconnect_daemon is None

    @pytest.mark.it("Does not start the reconnect daemon if it is already running")
    async def test_reconnect_daemon_running(self, mocker, client):
        client._auto_reconnect is True
        mock_task = mocker.MagicMock()
        client._reconnect_daemon = mock_task

        await client.connect()

        assert client._reconnect_daemon is mock_task

    @pytest.mark.it("Invokes an MQTT connect via Paho using stored values")
    async def test_paho_invocation(self, mocker, client, mock_paho):
        assert mock_paho.connect.call_count == 0

        await client.connect()

        assert mock_paho.connect.call_count == 1
        assert mock_paho.connect.call_args == mocker.call(
            host=client._hostname, port=client._port, keepalive=client._keep_alive
        )

    @pytest.mark.it(
        "Raises a MQTTConnectionFailedError if there is a failure invoking Paho's connect"
    )
    async def test_fail_paho_invocation(self, client, mock_paho, arbitrary_exception):
        mock_paho.connect.side_effect = arbitrary_exception

        with pytest.raises(MQTTConnectionFailedError) as e_info:
            await client.connect()
        assert e_info.value.__cause__ is arbitrary_exception
        assert e_info.value.rc is None

    # NOTE: This should be an invalid scenario as connect should not be able to return a failed status
    @pytest.mark.it(
        "Raises a MQTTConnectionFailedError if invoking Paho's connect returns a failed status"
    )
    @pytest.mark.parametrize("failing_rc", connect_failed_rc_params)
    async def test_fail_status(self, client, mock_paho, failing_rc):
        mock_paho._connect_rc = failing_rc

        with pytest.raises(MQTTConnectionFailedError) as e_info:
            await client.connect()
        assert e_info.value.rc is None
        cause = e_info.value.__cause__
        assert isinstance(cause, MQTTError)
        assert cause.rc == failing_rc

    @pytest.mark.it("Starts the Paho network loop if the connect invocation is successful")
    async def test_network_loop_connect_success(self, mocker, client, mock_paho):
        assert mock_paho.loop_start.call_count == 0

        await client.connect()

        assert mock_paho.loop_start.call_count == 1
        assert mock_paho.loop_start.call_args == mocker.call()

    @pytest.mark.it("Does not start the Paho network loop if the connect invocation fails")
    async def test_network_loop_connect_fail_raise(self, client, mock_paho, arbitrary_exception):
        assert mock_paho.loop_start.call_count == 0
        mock_paho.connect.side_effect = arbitrary_exception

        with pytest.raises(MQTTConnectionFailedError):
            await client.connect()

        assert mock_paho.loop_start.call_count == 0

    # NOTE: This should be an invalid scenario as connect should not be able to return a failed status
    @pytest.mark.it("Does not start the Paho network loop if the connect returns a failed status")
    @pytest.mark.parametrize("failing_rc", connect_failed_rc_params)
    async def test_network_loop_connect_fail_status(self, client, mock_paho, failing_rc):
        assert mock_paho.loop_start.call_count == 0
        mock_paho._connect_rc = failing_rc

        with pytest.raises(MQTTConnectionFailedError):
            await client.connect()

        assert mock_paho.loop_start.call_count == 0

    @pytest.mark.it("Stops, then starts the Paho network loop if the loop is already running")
    async def test_network_loop_already_running(self, mocker, client, mock_paho):
        mock_paho.loop_start.side_effect = [3, 0]
        assert mock_paho.loop_start.call_count == 0
        assert mock_paho.loop_stop.call_count == 0

        await client.connect()

        assert mock_paho.loop_start.call_count == 2
        assert mock_paho.loop_stop.call_count == 1

    @pytest.mark.it(
        "Waits to return until Paho receives a success response if the connect invocation succeeded"
    )
    async def test_waits_for_completion(self, client, mock_paho):
        # Require manual completion
        mock_paho._manual_mode = True

        # Start a connect. It won't complete
        connect_task = asyncio.create_task(client.connect())
        await asyncio.sleep(0.5)
        assert not connect_task.done()

        # Trigger connect completion
        mock_paho.trigger_on_connect(rc=mqtt.CONNACK_ACCEPTED)
        await connect_task

    @pytest.mark.it(
        "Raises a MQTTConnectionFailedError if the connect attempt receives a failure response"
    )
    @pytest.mark.parametrize("failing_rc", on_connect_failed_rc_params)
    async def test_fail_response(self, client, mock_paho, failing_rc):
        # Require manual completion
        mock_paho._manual_mode = True

        # Attempt connect
        connect_task = asyncio.create_task(client.connect())
        await asyncio.sleep(0.1)

        # Send failure CONNACK response
        mock_paho.trigger_on_connect(rc=failing_rc)
        # Any CONNACK failure also results in a ERR_CONN_REFUSED to on_disconnect
        mock_paho.trigger_on_disconnect(rc=mqtt.MQTT_ERR_CONN_REFUSED)
        with pytest.raises(MQTTConnectionFailedError) as e_info:
            await connect_task
        assert e_info.value.rc == failing_rc

    @pytest.mark.it("Can handle responses received before or after Paho invocation returns")
    @pytest.mark.parametrize("early_ack", early_ack_params)
    async def test_early_ack(self, client, mock_paho, early_ack):
        mock_paho._early_ack = early_ack
        await client.connect()
        # If this doesn't hang, the test passes

    @pytest.mark.it("Puts the client in a connected state if connection attempt is successful")
    async def test_state_success(self, client):
        assert not client.is_connected()

        await client.connect()

        assert client.is_connected()

    @pytest.mark.it(
        "Leaves the client in a disconnected state if there is a failure invoking Paho's connect"
    )
    async def test_state_fail_raise(self, client, mock_paho, arbitrary_exception):
        # Raise failure from connect
        mock_paho.connect.side_effect = arbitrary_exception
        assert not client.is_connected()

        with pytest.raises(MQTTConnectionFailedError):
            await client.connect()

        assert not client.is_connected()

    # NOTE: This should be an invalid scenario as connect should not be able to return a failed status
    @pytest.mark.it(
        "Leaves the client in a disconnected state if invoking Paho's connect returns a failed status"
    )
    @pytest.mark.parametrize("failing_rc", connect_failed_rc_params)
    async def test_state_fail_status(self, client, mock_paho, failing_rc):
        # Return a fail status
        mock_paho._connect_rc = failing_rc
        assert not client.is_connected()

        with pytest.raises(MQTTConnectionFailedError):
            await client.connect()

        assert not client.is_connected()

    @pytest.mark.it(
        "Leaves the client in a disconnected state if the connect attempt receives a failure response"
    )
    @pytest.mark.parametrize("failing_rc", on_connect_failed_rc_params)
    async def test_state_fail_response(self, client, mock_paho, failing_rc):
        # Require manual completion
        mock_paho._manual_mode = True
        assert not client.is_connected()

        # Attempt connect
        connect_task = asyncio.create_task(client.connect())
        await asyncio.sleep(0.1)
        # Send failure CONNACK response
        mock_paho.trigger_on_connect(rc=failing_rc)
        # Any CONNACK failure also results in an ERR_CONN_REFUSED to on_disconnect
        mock_paho.trigger_on_disconnect(rc=mqtt.MQTT_ERR_CONN_REFUSED)

        with pytest.raises(MQTTConnectionFailedError):
            await connect_task

        assert not client.is_connected()

    @pytest.mark.it(
        "Leaves the reconnect daemon running if there is a failure invoking Paho's connect"
    )
    async def test_reconnect_daemon_fail_raise(self, client, mock_paho, arbitrary_exception):
        client._auto_reconnect = True
        assert client._reconnect_daemon is None
        # Raise failure from connect
        mock_paho.connect.side_effect = arbitrary_exception

        with pytest.raises(MQTTConnectionFailedError):
            await client.connect()

        assert isinstance(client._reconnect_daemon, asyncio.Task)
        assert not client._reconnect_daemon.done()

    # NOTE: This should be an invalid scenario as connect should not be able to return a failed status
    @pytest.mark.it(
        "Leaves the reconnect daemon running if invoking Paho's connect returns a failed status"
    )
    @pytest.mark.parametrize("failing_rc", connect_failed_rc_params)
    async def test_reconnect_daemon_fail_status(self, client, mock_paho, failing_rc):
        # Return a fail status
        mock_paho._connect_rc = failing_rc
        client._auto_reconnect = True
        assert client._reconnect_daemon is None

        with pytest.raises(MQTTConnectionFailedError):
            await client.connect()

        assert isinstance(client._reconnect_daemon, asyncio.Task)
        assert not client._reconnect_daemon.done()

    @pytest.mark.it(
        "Leaves the reconnect daemon running if the connect attempt receives a failure response"
    )
    @pytest.mark.parametrize("failing_rc", on_connect_failed_rc_params)
    async def test_reconnect_daemon_fail_response(self, client, mock_paho, failing_rc):
        # Require manual completion
        mock_paho._manual_mode = True
        client._auto_reconnect = True
        assert client._reconnect_daemon is None

        # Attempt connect
        connect_task = asyncio.create_task(client.connect())
        await asyncio.sleep(0.1)
        # Send failure CONNACK response
        mock_paho.trigger_on_connect(rc=failing_rc)
        # Any CONNACK failure also results in an ERR_CONN_REFUSED to on_disconnect
        mock_paho.trigger_on_disconnect(rc=mqtt.MQTT_ERR_CONN_REFUSED)

        with pytest.raises(MQTTConnectionFailedError):
            await connect_task

        assert isinstance(client._reconnect_daemon, asyncio.Task)
        assert not client._reconnect_daemon.done()
        # Some test cases will need some help cleaning up
        # TODO: is there a cleaner way to make sure this happens smoothly?
        # TODO: the issue is I think that connect is getting called by the task before it can get cleaned
        client._reconnect_daemon.cancel()

    @pytest.mark.it(
        "Stops the Paho network loop if the connect attempt receives a failure response"
    )
    @pytest.mark.parametrize("failing_rc", on_connect_failed_rc_params)
    async def test_network_loop_fail_response(self, mocker, client, mock_paho, failing_rc):
        # Require manual completion
        mock_paho._manual_mode = True
        assert mock_paho.loop_start.call_count == 0
        assert mock_paho.loop_stop.call_count == 0

        # Attempt connect
        connect_task = asyncio.create_task(client.connect())

        # Network loop was started
        await asyncio.sleep(0.1)
        assert mock_paho.loop_start.call_count == 1
        assert mock_paho.loop_start.call_args == mocker.call()
        assert mock_paho.loop_stop.call_count == 0

        # Send failure CONNACK response
        mock_paho.trigger_on_connect(rc=failing_rc)
        # Any CONNACK failure also results in an ERR_CONN_REFUSED
        mock_paho.trigger_on_disconnect(rc=mqtt.MQTT_ERR_CONN_REFUSED)
        with pytest.raises(MQTTConnectionFailedError):
            await connect_task

        # Network loop was stopped
        assert mock_paho.loop_start.call_count == 1
        assert mock_paho.loop_stop.call_count == 1


@pytest.mark.describe("MQTTClient - .connect() -- Client Fresh")
class TestConnectWithClientFresh(ConnectWithClientNotConnectedTests):
    @pytest.fixture
    async def client(self, fresh_client):
        return fresh_client


@pytest.mark.describe("MQTTClient - .connect() -- Client Disconnected")
class TestConnectWithClientDisconnected(ConnectWithClientNotConnectedTests):
    @pytest.fixture
    async def client(self, fresh_client):
        client = fresh_client
        client_set_disconnected(client)
        return client


@pytest.mark.describe("MQTTClient - .connect() -- Client Connection Dropped")
class TestConnectWithClientConnectionDropped(ConnectWithClientNotConnectedTests):
    @pytest.fixture
    async def client(self, fresh_client):
        client = fresh_client
        client_set_connection_dropped(client)
        return client


@pytest.mark.describe("MQTTClient - .connect() -- Client Already Connected")
class TestConnectWithClientConnected(object):
    @pytest.fixture
    async def client(self, fresh_client):
        client = fresh_client
        client_set_connected(client)
        return client

    @pytest.mark.it("Does not invoke an MQTT connect via Paho")
    async def test_paho_invocation(self, client, mock_paho):
        assert mock_paho.connect.call_count == 0

        await client.connect()

        assert mock_paho.connect.call_count == 0

    @pytest.mark.it("Does not start the reconnect daemon")
    async def test_reconnect_daemon(self, client, mock_paho):
        client._auto_reconnect = True
        assert client._reconnect_daemon is None

        await client.connect()

        assert client._reconnect_daemon is None

    @pytest.mark.it("Does not start the Paho network loop")
    async def test_network_loop(self, client, mock_paho):
        assert mock_paho.loop_start.call_count == 0

        await client.connect()

        assert mock_paho.loop_start.call_count == 0

    @pytest.mark.it("Leaves the client in a connected state")
    async def test_state(self, client):
        assert client.is_connected()

        await client.connect()

        assert client.is_connected()

    @pytest.mark.it("Does not wait for a response before returning")
    async def test_return(self, client, mock_paho):
        # Require manual completion
        mock_paho._manual_mode = True
        # Attempt connect
        connect_task = asyncio.create_task(client.connect())
        # No waiting for connect response trigger was required
        await connect_task


# NOTE: Disconnect responses can be either a single or double invocation of Paho's .on_disconnect()
# handler. Both cases are covered. Why does this happen? I don't know. But it does, and the client
# is designed to handle it.
# NOTE: Paho's .disconnect() method will always return success (rc = MQTT_ERR_SUCCESS) when the
# client is connected. As such, we don't have to test rc != MQTT_ERR_SUCCESS here
# (it is covered in other test classes)
@pytest.mark.describe("MQTTClient - .disconnect() -- Client Connected")
class TestDisconnectWithClientConnected(object):
    @pytest.fixture
    async def client(self, fresh_client):
        client = fresh_client
        client_set_connected(client)
        return client

    @pytest.mark.it("Invokes an MQTT disconnect via Paho")
    async def test_paho_invocation(self, mocker, client, mock_paho):
        assert mock_paho.disconnect.call_count == 0

        await client.disconnect()

        assert mock_paho.disconnect.call_count == 1
        assert mock_paho.disconnect.call_args == mocker.call()

    @pytest.mark.it("Waits to return until Paho receives a response")
    @pytest.mark.parametrize(
        "double_response",
        [
            pytest.param(False, id="Single Disconnect Response"),
            pytest.param(True, id="Double Disconnect Response"),
        ],
    )
    async def test_waits_for_completion(self, client, mock_paho, double_response):
        # Require manual completion
        mock_paho._manual_mode = True

        # Start a disconnect. It won't complete
        disconnect_task = asyncio.create_task(client.disconnect())
        await asyncio.sleep(0.5)
        assert not disconnect_task.done()

        # Trigger disconnect completion
        mock_paho.trigger_on_disconnect(rc=mqtt.MQTT_ERR_SUCCESS)
        if double_response:
            mock_paho.trigger_on_disconnect(rc=mqtt.MQTT_ERR_SUCCESS)
        await disconnect_task

    @pytest.mark.it("Can handle responses received before or after Paho invocation returns")
    @pytest.mark.parametrize("early_ack", early_ack_params)
    async def test_early_ack(self, client, mock_paho, early_ack):
        mock_paho._early_ack = early_ack
        await client.disconnect()
        # If this doesn't hang, the test passes

    @pytest.mark.it("Cancels and removes the reconnect daemon task if it is running")
    @pytest.mark.parametrize(
        "double_response",
        [
            pytest.param(False, id="Single Disconnect Response"),
            pytest.param(True, id="Double Disconnect Response"),
        ],
    )
    async def test_reconnect_daemon(self, mocker, client, mock_paho, double_response):
        # Require manual completion
        mock_paho._manual_mode = True
        # Set a fake daemon task
        mock_task = mocker.MagicMock()
        client._reconnect_daemon = mock_task

        # Start a disconnect.
        disconnect_task = asyncio.create_task(client.disconnect())
        await asyncio.sleep(0.1)
        # Trigger disconnect completion
        mock_paho.trigger_on_disconnect(rc=mqtt.MQTT_ERR_SUCCESS)
        if double_response:
            mock_paho.trigger_on_disconnect(rc=mqtt.MQTT_ERR_SUCCESS)
        await disconnect_task

        # Daemon was cancelled
        assert mock_task.cancel.call_count == 1
        assert client._reconnect_daemon is None

    @pytest.mark.it("Stops the Paho network loop")
    @pytest.mark.parametrize(
        "double_response",
        [
            pytest.param(False, id="Single Disconnect Response"),
            pytest.param(True, id="Double Disconnect Response"),
        ],
    )
    async def test_network_loop(self, client, mock_paho, double_response):
        # Require manual completion
        mock_paho._manual_mode = True
        assert mock_paho.loop_stop.call_count == 0

        # Start a disconnect.
        disconnect_task = asyncio.create_task(client.disconnect())
        await asyncio.sleep(0.1)
        # Trigger disconnect completion
        mock_paho.trigger_on_disconnect(rc=mqtt.MQTT_ERR_SUCCESS)
        if double_response:
            mock_paho.trigger_on_disconnect(rc=mqtt.MQTT_ERR_SUCCESS)
        await disconnect_task
        assert mock_paho.loop_stop.call_count == 1

    @pytest.mark.it("Puts the client in a disconnected state")
    @pytest.mark.parametrize(
        "double_response",
        [
            pytest.param(False, id="Single Disconnect Response"),
            pytest.param(True, id="Double Disconnect Response"),
        ],
    )
    async def test_state(self, client, mock_paho, double_response):
        # Require manual completion
        mock_paho._manual_mode = True
        assert client.is_connected()

        # Start a disconnect.
        disconnect_task = asyncio.create_task(client.disconnect())
        await asyncio.sleep(0.1)
        # Trigger disconnect completion
        mock_paho.trigger_on_disconnect(rc=mqtt.MQTT_ERR_SUCCESS)
        if double_response:
            mock_paho.trigger_on_disconnect(rc=mqtt.MQTT_ERR_SUCCESS)
        await disconnect_task

        assert not client.is_connected()

    @pytest.mark.it("Cancels and removes all pending subscribes and unsubscribes")
    @pytest.mark.parametrize(
        "double_response",
        [
            pytest.param(False, id="Single Disconnect Response"),
            pytest.param(True, id="Double Disconnect Response"),
        ],
    )
    async def test_cancel_sub_unsub(self, mocker, client, mock_paho, double_response):
        # Require manual completion
        mock_paho._manual_mode = True
        # Set mocked pending Futures
        mock_subs = [mocker.MagicMock(), mocker.MagicMock(), mocker.MagicMock()]
        mock_unsubs = [mocker.MagicMock(), mocker.MagicMock(), mocker.MagicMock()]
        client._pending_subs[1] = mock_subs[0]
        client._pending_subs[2] = mock_subs[1]
        client._pending_subs[3] = mock_subs[2]
        client._pending_unsubs[4] = mock_unsubs[0]
        client._pending_unsubs[5] = mock_unsubs[1]
        client._pending_unsubs[6] = mock_unsubs[2]

        # Start a disconnect.
        disconnect_task = asyncio.create_task(client.disconnect())
        await asyncio.sleep(0.1)
        # Trigger disconnect completion
        mock_paho.trigger_on_disconnect(rc=mqtt.MQTT_ERR_SUCCESS)
        if double_response:
            mock_paho.trigger_on_disconnect(rc=mqtt.MQTT_ERR_SUCCESS)
        await disconnect_task

        # All were cancelled
        for mock in mock_subs:
            assert mock.cancel.call_count == 1
        for mock in mock_unsubs:
            assert mock.cancel.call_count == 1
        # All were removed
        assert len(client._pending_subs) == 0
        assert len(client._pending_unsubs) == 0

    @pytest.mark.it("Does not cancel or remove any pending publishes")
    @pytest.mark.parametrize(
        "double_response",
        [
            pytest.param(False, id="Single Disconnect Response"),
            pytest.param(True, id="Double Disconnect Response"),
        ],
    )
    async def test_no_cancel_pub(self, mocker, client, mock_paho, double_response):
        # Set mocked pending Futures
        mock_pubs = [mocker.MagicMock(), mocker.MagicMock(), mocker.MagicMock()]
        client._pending_pubs[1] = mock_pubs[0]
        client._pending_pubs[2] = mock_pubs[1]
        client._pending_pubs[3] = mock_pubs[2]

        # Start a disconnect.
        disconnect_task = asyncio.create_task(client.disconnect())
        await asyncio.sleep(0.1)
        # Trigger disconnect completion
        mock_paho.trigger_on_disconnect(rc=mqtt.MQTT_ERR_SUCCESS)
        if double_response:
            mock_paho.trigger_on_disconnect(rc=mqtt.MQTT_ERR_SUCCESS)
        await disconnect_task

        # None were cancelled
        for mock in mock_pubs:
            assert mock.cancel.call_count == 0
        # None were removed
        assert len(client._pending_pubs) == 3


@pytest.mark.describe("MQTTClient - .disconnect() -- Client Connection Dropped")
class TestDisconnectWithClientConnectionDrop(object):
    @pytest.fixture
    async def client(self, fresh_client):
        client = fresh_client
        client_set_connection_dropped(client)
        return client

    @pytest.mark.it("Invokes an MQTT disconnect via Paho")
    async def test_paho_invocation(self, mocker, client, mock_paho):
        assert mock_paho.disconnect.call_count == 0

        await client.disconnect()

        assert mock_paho.disconnect.call_count == 1
        assert mock_paho.disconnect.call_args == mocker.call()

    @pytest.mark.it("Cancels and removes the reconnect daemon task if it is running")
    async def test_reconnect_daemon(self, mocker, client):
        # Set a fake daemon task
        mock_task = mocker.MagicMock()
        client._reconnect_daemon = mock_task

        await client.disconnect()

        assert mock_task.cancel.call_count == 1
        assert client._reconnect_daemon is None

    # NOTE: It doesn't stop it because it has already been stopped when the connection dropped
    @pytest.mark.it("Does not stop the Paho network loop")
    async def test_network_loop(self, client, mock_paho):
        assert mock_paho.loop_stop.call_count == 0

        await client.disconnect()

        assert mock_paho.loop_stop.call_count == 0

    # NOTE: This is an invalid scenario. Connection being dropped implies there are
    # no pending subscribes or unsubscribes
    @pytest.mark.it("Does not cancel or remove any pending subscribes or unsubscribes")
    async def test_pending_sub_unsub(self, mocker, client, mock_paho):
        # Set mocked pending Futures
        mock_subs = [mocker.MagicMock(), mocker.MagicMock(), mocker.MagicMock()]
        mock_unsubs = [mocker.MagicMock(), mocker.MagicMock(), mocker.MagicMock()]
        client._pending_subs[1] = mock_subs[0]
        client._pending_subs[2] = mock_subs[1]
        client._pending_subs[3] = mock_subs[2]
        client._pending_unsubs[4] = mock_unsubs[0]
        client._pending_unsubs[5] = mock_unsubs[1]
        client._pending_unsubs[6] = mock_unsubs[2]

        await client.disconnect()

        # None were cancelled
        for mock in mock_subs:
            assert mock.cancel.call_count == 0
        for mock in mock_unsubs:
            assert mock.cancel.call_count == 0
        # None were removed
        assert len(client._pending_subs) == 3
        assert len(client._pending_unsubs) == 3

    # NOTE: Unlike the above, this is a valid scenario. Publishes survive a connection drop.
    @pytest.mark.it("Does not cancel or remove any pending publishes")
    async def test_pending_pub(self, mocker, client):
        # Set mocked pending Futures
        mock_pubs = [mocker.MagicMock(), mocker.MagicMock(), mocker.MagicMock()]
        client._pending_pubs[1] = mock_pubs[0]
        client._pending_pubs[2] = mock_pubs[1]
        client._pending_pubs[3] = mock_pubs[2]

        await client.disconnect()

        # None were cancelled
        for mock in mock_pubs:
            assert mock.cancel.call_count == 0
        # None were removed
        assert len(client._pending_pubs) == 3

    @pytest.mark.it("Leaves the client in a disconnected state")
    async def test_state(self, client, mock_paho):
        assert not client.is_connected()

        await client.disconnect()

        assert not client.is_connected()

    @pytest.mark.it("Does not wait for a response before returning")
    async def test_return(self, client, mock_paho):
        # Require manual completion
        mock_paho._manual_mode = True
        # Attempt disconnect
        disconnect_task = asyncio.create_task(client.disconnect())
        await disconnect_task


# NOTE: Because clients in Disconnected and Fresh states have the same behaviors during a connect,
# define a parent class that can be subclassed so tests don't have to be written twice.
class DisconnectWithClientFullyDisconnectedTests(object):
    @pytest.fixture
    async def client(self, fresh_client):
        client = fresh_client
        client_set_disconnected(client)
        return client

    @pytest.mark.it("Does not invoke an MQTT disconnect via Paho")
    async def test_paho_invocation(self, client, mock_paho):
        assert mock_paho.disconnect.call_count == 0

        await client.disconnect()

        assert mock_paho.disconnect.call_count == 0

    # NOTE: This is a completely invalid scenario, there's no way for it to happen
    @pytest.mark.it("Does not alter the reconnect daemon")
    async def test_reconnect_daemon(self, mocker, client):
        # Set a fake daemon task
        mock_task = mocker.MagicMock()
        client._reconnect_daemon = mock_task

        await client.disconnect()

        assert mock_task.cancel.call_count == 0
        assert client._reconnect_daemon is mock_task

    @pytest.mark.it("Does not stop the Paho network loop")
    async def test_network_loop(self, client, mock_paho):
        assert mock_paho.loop_stop.call_count == 0

        await client.disconnect()

        assert mock_paho.loop_stop.call_count == 0

    # NOTE: This is an invalid scenario. Being disconnected implies there are
    # no pending subscribes or unsubscribes
    @pytest.mark.it("Does not cancel or remove any pending subscribes or unsubscribes")
    async def test_pending_sub_unsub(self, mocker, client):
        # Set mocked pending Futures
        mock_subs = [mocker.MagicMock(), mocker.MagicMock(), mocker.MagicMock()]
        mock_unsubs = [mocker.MagicMock(), mocker.MagicMock(), mocker.MagicMock()]
        client._pending_subs[1] = mock_subs[0]
        client._pending_subs[2] = mock_subs[1]
        client._pending_subs[3] = mock_subs[2]
        client._pending_unsubs[4] = mock_unsubs[0]
        client._pending_unsubs[5] = mock_unsubs[1]
        client._pending_unsubs[6] = mock_unsubs[2]

        await client.disconnect()

        # None were cancelled
        for mock in mock_subs:
            assert mock.cancel.call_count == 0
        for mock in mock_unsubs:
            assert mock.cancel.call_count == 0
        # None were removed
        assert len(client._pending_subs) == 3
        assert len(client._pending_unsubs) == 3

    # NOTE: Unlike the above, this is a valid scenario. Publishes survive a disconnect.
    @pytest.mark.it("Does not cancel or remove any pending publishes")
    async def test_pending_pub(self, mocker, client):
        # Set mocked pending Futures
        mock_pubs = [mocker.MagicMock(), mocker.MagicMock(), mocker.MagicMock()]
        client._pending_pubs[1] = mock_pubs[0]
        client._pending_pubs[2] = mock_pubs[1]
        client._pending_pubs[3] = mock_pubs[2]

        await client.disconnect()

        # None were cancelled
        for mock in mock_pubs:
            assert mock.cancel.call_count == 0
        # None were removed
        assert len(client._pending_pubs) == 3

    @pytest.mark.it("Leaves the client in a disconnected state")
    async def test_state(self, client):
        assert not client.is_connected()

        await client.disconnect()

        assert not client.is_connected()

    @pytest.mark.it("Does not wait for a response before returning")
    async def test_return(self, client, mock_paho):
        # Require manual completion
        mock_paho._manual_mode = True
        # Attempt disconnect
        disconnect_task = asyncio.create_task(client.disconnect())
        # No waiting for disconnect response trigger was required
        await disconnect_task


@pytest.mark.describe("MQTTClient - .disconnect() -- Client Already Disconnected")
class TestDisconnectWithClientDisconnected(DisconnectWithClientFullyDisconnectedTests):
    @pytest.fixture
    async def client(self, fresh_client):
        client = fresh_client
        client_set_disconnected(client)
        return client


@pytest.mark.describe("MQTTClient - .disconnect() -- Client Fresh")
class TestDisconnectWithClientFresh(DisconnectWithClientFullyDisconnectedTests):
    @pytest.fixture
    async def client(self, fresh_client):
        return fresh_client


@pytest.mark.describe("MQTTClient - OCCURRENCE: Unexpected Disconnect")
class TestUnexpectedDisconnect(object):
    @pytest.mark.it("Puts the client in a disconnected state")
    async def test_state(self, client, mock_paho):
        client_set_connected(client)
        assert client.is_connected()

        mock_paho.trigger_on_disconnect(rc=mqtt.MQTT_ERR_CONN_LOST)
        await asyncio.sleep(0.1)

        assert not client.is_connected()

    @pytest.mark.it("Stops the Paho network loop")
    async def test_network_loop(self, client, mock_paho):
        client_set_connected(client)
        assert mock_paho.loop_stop.call_count == 0

        mock_paho.trigger_on_disconnect(rc=mqtt.MQTT_ERR_CONN_LOST)
        await asyncio.sleep(0.1)

        assert mock_paho.loop_stop.call_count == 1

    @pytest.mark.it("Does not alter the reconnect daemon")
    async def test_reconnect_daemon(self, mocker, client, mock_paho):
        client_set_connected(client)
        client._auto_reconnect = True
        mock_task = mocker.MagicMock()
        client._reconnect_daemon = mock_task

        mock_paho.trigger_on_disconnect(rc=mqtt.MQTT_ERR_CONN_LOST)
        await asyncio.sleep(0.1)

        assert mock_task.cancel.call_count == 0
        assert client._reconnect_daemon is mock_task

    @pytest.mark.it("Cancels and removes all pending subscribes and unsubscribes")
    async def test_cancel_sub_unsub(self, mocker, client, mock_paho):
        client_set_connected(client)
        # Set mocked pending Futures
        mock_subs = [mocker.MagicMock(), mocker.MagicMock(), mocker.MagicMock()]
        mock_unsubs = [mocker.MagicMock(), mocker.MagicMock(), mocker.MagicMock()]
        client._pending_subs[1] = mock_subs[0]
        client._pending_subs[2] = mock_subs[1]
        client._pending_subs[3] = mock_subs[2]
        client._pending_unsubs[4] = mock_unsubs[0]
        client._pending_unsubs[5] = mock_unsubs[1]
        client._pending_unsubs[6] = mock_unsubs[2]

        # Disconnect
        mock_paho.trigger_on_disconnect(rc=mqtt.MQTT_ERR_CONN_LOST)
        await asyncio.sleep(0.1)

        # All were cancelled
        for mock in mock_subs:
            assert mock.cancel.call_count == 1
        for mock in mock_unsubs:
            assert mock.cancel.call_count == 1
        # All were removed
        assert len(client._pending_subs) == 0
        assert len(client._pending_unsubs) == 0

    @pytest.mark.it("Does not cancel or remove any pending publishes")
    async def test_no_cancel_pub(self, mocker, client, mock_paho):
        client_set_connected(client)
        # Set mocked pending Futures
        mock_pubs = [mocker.MagicMock(), mocker.MagicMock(), mocker.MagicMock()]
        client._pending_pubs[1] = mock_pubs[0]
        client._pending_pubs[2] = mock_pubs[1]
        client._pending_pubs[3] = mock_pubs[2]

        # Disconnect
        mock_paho.trigger_on_disconnect(rc=mqtt.MQTT_ERR_CONN_LOST)
        await asyncio.sleep(0.1)

        # None were cancelled
        for mock in mock_pubs:
            assert mock.cancel.call_count == 0
        # None were removed
        assert len(client._pending_pubs) == 3


@pytest.mark.describe("MQTTClient - Connection Lock")
class TestConnectionLock(object):
    @pytest.mark.it("Waits for a pending connect task to finish before attempting a connect")
    @pytest.mark.parametrize(
        "pending_success",
        [
            pytest.param(True, id="Pending connect succeeds"),
            pytest.param(False, id="Pending connect fails"),
        ],
    )
    async def test_connect_pending_connect(self, client, mock_paho, pending_success):
        # Require manual completion
        mock_paho._manual_mode = True
        assert mock_paho.connect.call_count == 0
        # Client is currently disconnected
        assert not client.is_connected()

        # Attempt first connect
        connect_task1 = asyncio.create_task(client.connect())
        await asyncio.sleep(0.1)
        # Paho connect has been called but task1 is still pending
        assert mock_paho.connect.call_count == 1
        assert not connect_task1.done()
        # Start second attempt
        connect_task2 = asyncio.create_task(client.connect())
        await asyncio.sleep(0.1)
        # Paho connect has NOT been called an additional time and task2 is still pending
        assert mock_paho.connect.call_count == 1
        assert not connect_task2.done()

        # Complete first connect
        if pending_success:
            mock_paho.trigger_on_connect(rc=mqtt.CONNACK_ACCEPTED)
        else:
            # Failure triggers both. Use Server Unavailable as an arbitrary reason for failure.
            mock_paho.trigger_on_connect(rc=mqtt.CONNACK_REFUSED_SERVER_UNAVAILABLE)
            mock_paho.trigger_on_disconnect(rc=mqtt.MQTT_ERR_CONN_REFUSED)
        await asyncio.sleep(0.1)
        assert connect_task1.done()

        if pending_success:
            # Second connect was completed without invoking connect on Paho because it is
            # already connected
            assert client.is_connected()
            assert connect_task2.done()
            assert mock_paho.connect.call_count == 1
            assert client.is_connected()
        else:
            # Second connect has invoked connect on Paho and is waiting for completion
            assert not client.is_connected()
            assert not connect_task2.done()
            assert mock_paho.connect.call_count == 2
            # Complete the second connect successfully
            mock_paho.trigger_on_connect(rc=mqtt.CONNACK_ACCEPTED)
            await connect_task2
            assert client.is_connected()

    # NOTE: Disconnect can't fail
    @pytest.mark.it("Waits for a pending disconnect task to finish before attempting a connect")
    async def test_connect_pending_disconnect(self, client, mock_paho):
        # Require manual completion
        mock_paho._manual_mode = True
        assert mock_paho.connect.call_count == 0
        assert mock_paho.disconnect.call_count == 0
        # Client must be connected for disconnect to pend
        client_set_connected(client)
        assert client.is_connected()

        # Attempt disconnect
        disconnect_task = asyncio.create_task(client.disconnect())
        await asyncio.sleep(0.1)
        # Paho disconnect has been called but task is still pending
        assert mock_paho.disconnect.call_count == 1
        assert not disconnect_task.done()
        # Attempt connect
        connect_task = asyncio.create_task(client.connect())
        await asyncio.sleep(0.1)
        # Paho connect has NOT been called yet and task is still pending
        assert mock_paho.connect.call_count == 0
        assert not connect_task.done()

        # Complete disconnect
        mock_paho.trigger_on_disconnect(rc=mqtt.MQTT_ERR_SUCCESS)
        await asyncio.sleep(0.1)
        assert disconnect_task.done()
        assert not client.is_connected()

        # Connect task has now invoked Paho connect and is waiting for completion
        assert not connect_task.done()
        assert mock_paho.connect.call_count == 1
        # Complete the connect
        mock_paho.trigger_on_connect(rc=mqtt.CONNACK_ACCEPTED)
        await connect_task
        assert client.is_connected()

    @pytest.mark.it("Waits for a pending connect task to finish before attempting a disconnect")
    @pytest.mark.parametrize(
        "pending_success",
        [
            pytest.param(True, id="Pending connect succeeds"),
            pytest.param(False, id="Pending connect fails"),
        ],
    )
    async def test_disconnect_pending_connect(self, client, mock_paho, pending_success):
        # Require manual completion
        mock_paho._manual_mode = True
        assert mock_paho.disconnect.call_count == 0
        assert mock_paho.disconnect.call_count == 0
        # Paho has to be disconnected for connect to pend
        assert not client.is_connected()

        # Attempt connect
        connect_task = asyncio.create_task(client.connect())
        await asyncio.sleep(0.1)
        # Paho connect has been called but task is still pending
        assert mock_paho.connect.call_count == 1
        assert not connect_task.done()
        # Attempt disconnect
        disconnect_task = asyncio.create_task(client.disconnect())
        await asyncio.sleep(0.1)
        # Paho disconnect has NOT been called yet and task is still pending
        assert mock_paho.disconnect.call_count == 0
        assert not disconnect_task.done()

        # Complete connect
        if pending_success:
            mock_paho.trigger_on_connect(rc=mqtt.CONNACK_ACCEPTED)
        else:
            # Failure triggers both. Use server unavailable as an arbitrary reason for failure
            mock_paho.trigger_on_connect(rc=mqtt.CONNACK_REFUSED_SERVER_UNAVAILABLE)
            mock_paho.trigger_on_disconnect(rc=mqtt.MQTT_ERR_CONN_REFUSED)
        await asyncio.sleep(0.1)
        assert connect_task.done()

        if pending_success:
            assert client.is_connected()
            # Disconnect was invoked on Paho and is waiting for completion
            assert not disconnect_task.done()
            assert mock_paho.disconnect.call_count == 1
            # Complete the disconnect
            mock_paho.trigger_on_disconnect(rc=mqtt.MQTT_ERR_SUCCESS)
            await disconnect_task
            assert not client.is_connected()
        else:
            assert not client.is_connected()
            # Disconnect was completed without invoking connect on Paho because it is
            # already disconnected
            assert disconnect_task.done()
            assert mock_paho.disconnect.call_count == 0
            assert not client.is_connected()

    # NOTE: Disconnect can't fail
    @pytest.mark.it("Waits for a pending disconnect task to finish before attempting a disconnect")
    async def test_disconnect_pending_disconnect(self, client, mock_paho):
        # Require manual completion
        mock_paho._manual_mode = True
        assert mock_paho.disconnect.call_count == 0
        # Client is currently connected
        client_set_connected(client)
        assert client.is_connected()

        # Attempt first disconnect
        disconnect_task1 = asyncio.create_task(client.disconnect())
        await asyncio.sleep(0.1)
        # Paho disconnect has been called but task 1 is still pending
        assert mock_paho.disconnect.call_count == 1
        assert not disconnect_task1.done()
        # Attempt second disconnect
        disconnect_task2 = asyncio.create_task(client.disconnect())
        await asyncio.sleep(0.1)
        # Paho disconnect has NOT been called an additional time and task2 is still pending
        assert mock_paho.disconnect.call_count == 1
        assert not disconnect_task2.done()

        # Complete first disconnect
        mock_paho.trigger_on_disconnect(rc=mqtt.MQTT_ERR_SUCCESS)
        await disconnect_task1
        assert not client.is_connected()

        # Second disconnect was completed without invoking disconnect on Paho because it is
        # already disconnected
        await disconnect_task2
        assert mock_paho.disconnect.call_count == 1
        assert not client.is_connected()


@pytest.mark.skipif(sys.version_info < (3, 8), reason="AsyncMock not supported by Python 3.7")
@pytest.mark.describe("MQTTClient - Reconnect Daemon")
class TestReconnectDaemon(object):
    @pytest.fixture
    async def client(self, fresh_client):
        client = fresh_client
        client._auto_reconnect = True
        client._reconnect_interval = 2
        # Successfully connect
        await client.connect()
        assert client.is_connected()
        # Reconnect Daemon is running
        assert isinstance(client._reconnect_daemon, asyncio.Task)
        return client

    @pytest.mark.it("Attempts to connect immediately after an unexpected disconnection")
    async def test_unexpected_drop(self, mocker, client, mock_paho):
        # Set connect to fail. This is kind of arbitrary - we just need it to do something
        client.connect = mocker.AsyncMock(side_effect=MQTTConnectionFailedError)
        assert client.connect.call_count == 0

        # Drop the connection
        mock_paho.trigger_on_disconnect(rc=mqtt.MQTT_ERR_CONN_LOST)
        await asyncio.sleep(0.1)

        # Connect was called by the daemon
        assert client.connect.call_count == 1
        assert client.connect.call_args == mocker.call()

    @pytest.mark.it(
        "Waits for the reconnect interval (in seconds) to try to connect again if the connect attempt fails non-fatally"
    )
    async def test_reconnect_attempt_fails_nonfatal(self, mocker, client, mock_paho):
        # Set connect to fail (nonfatal)
        exc = MQTTConnectionFailedError(rc=mqtt.CONNACK_REFUSED_SERVER_UNAVAILABLE, fatal=False)
        client.connect = mocker.AsyncMock(side_effect=exc)
        assert client.connect.call_count == 0

        # Drop the connection
        mock_paho.trigger_on_disconnect(rc=mqtt.MQTT_ERR_CONN_LOST)
        await asyncio.sleep(0.1)

        # Connect was called by the daemon
        assert client.connect.call_count == 1
        # Wait half the interval
        await asyncio.sleep(client._reconnect_interval / 2)
        # Connect has not been called again
        assert client.connect.call_count == 1
        # Wait the rest of the interval
        await asyncio.sleep(client._reconnect_interval / 2)
        # Connect was attempted again
        assert client.connect.call_count == 2

    @pytest.mark.it("Ends reconnect attempts if the connect attempt fails fatally")
    async def test_reconnect_attempt_fails_fatal(self, mocker, client, mock_paho):
        # Set connect to fail (fatal)
        exc = MQTTConnectionFailedError(message="Some fatal exc", fatal=True)
        client.connect = mocker.AsyncMock(side_effect=exc)
        assert client.connect.call_count == 0

        # Drop the connect
        mock_paho.trigger_on_disconnect(rc=mqtt.MQTT_ERR_CONN_LOST)
        await asyncio.sleep(0.1)

        # Connect was called by the daemon
        assert client.connect.call_count == 1
        # Daemon has exited
        assert client._reconnect_daemon.done()

    @pytest.mark.it(
        "Does not try again until the next unexpected disconnection if the connect attempt succeeds"
    )
    async def test_reconnect_attempt_succeeds(self, mocker, client, mock_paho):
        # Set connect to succeed
        def fake_connect():
            client_set_connected(client)

        client.connect = mocker.AsyncMock(side_effect=fake_connect)
        assert client.connect.call_count == 0

        # Drop the connection
        mock_paho.trigger_on_disconnect(rc=mqtt.MQTT_ERR_CONN_LOST)
        await asyncio.sleep(0.1)

        # Connect was called by the daemon
        assert client.connect.call_count == 1
        # Wait for the interval
        await asyncio.sleep(client._reconnect_interval)
        # Connect was not attempted again
        assert client.connect.call_count == 1

        # Drop the connection again
        mock_paho.trigger_on_disconnect(rc=mqtt.MQTT_ERR_CONN_LOST)
        await asyncio.sleep(0.1)

        # Connect was attempted again
        assert client.connect.call_count == 2

    @pytest.mark.it("Does not attempt to connect after an expected disconnection")
    async def test_disconnect(self, mocker, client):
        # Set connect to fail. This is kind of arbitrary - we just need it to do something
        client.connect = mocker.AsyncMock(side_effect=MQTTConnectionFailedError)
        assert client.connect.call_count == 0

        # Disconnect
        await client.disconnect()
        await asyncio.sleep(0.1)

        # Connect was not called by the daemon
        assert client.connect.call_count == 0


@pytest.mark.describe("MQTTClient - .subscribe()")
class TestSubscribe(object):
    @pytest.mark.it("Invokes an MQTT subscribe via Paho")
    async def test_paho_invocation(self, mocker, client, mock_paho):
        assert mock_paho.subscribe.call_count == 0

        await client.subscribe(fake_topic)

        assert mock_paho.subscribe.call_count == 1
        assert mock_paho.subscribe.call_args == mocker.call(topic=fake_topic, qos=1)

    @pytest.mark.it("Raises a MQTTError if invoking Paho's subscribe returns a failed status")
    @pytest.mark.parametrize("failing_rc", subscribe_failed_rc_params)
    async def test_fail_status(self, client, mock_paho, failing_rc):
        mock_paho._subscribe_rc = failing_rc

        with pytest.raises(MQTTError) as e_info:
            await client.subscribe(fake_topic)
        assert e_info.value.rc == failing_rc

    @pytest.mark.it("Allows any exceptions raised by invoking Paho's subscribe to propagate")
    async def test_fail_paho_invocation(self, client, mock_paho, arbitrary_exception):
        mock_paho.subscribe.side_effect = arbitrary_exception

        with pytest.raises(type(arbitrary_exception)):
            await client.subscribe(fake_topic)

    @pytest.mark.it(
        "Waits to return until Paho receives a matching response if the subscribe invocation succeeded"
    )
    async def test_matching_completion(self, client, mock_paho):
        # Require manual completion
        mock_paho._manual_mode = True

        # Start a subscribe. It won't complete
        subscribe_task = asyncio.create_task(client.subscribe(fake_topic))
        await asyncio.sleep(0.5)
        assert not subscribe_task.done()

        # Trigger subscribe completion
        mock_paho.trigger_on_subscribe(mock_paho._last_mid)
        await subscribe_task

    @pytest.mark.it("Does not return if Paho receives a non-matching response")
    async def test_nonmatching_completion(self, client, mock_paho):
        # Require manual completion
        mock_paho._manual_mode = True

        # Start two subscribes. They won't complete
        subscribe_task1 = asyncio.create_task(client.subscribe(fake_topic))
        await asyncio.sleep(0.1)
        subscribe_task1_mid = mock_paho._last_mid
        subscribe_task2 = asyncio.create_task(client.subscribe(fake_topic))
        await asyncio.sleep(0.1)
        subscribe_task2_mid = mock_paho._last_mid
        assert subscribe_task1_mid != subscribe_task2_mid
        await asyncio.sleep(0.5)
        assert not subscribe_task1.done()
        assert not subscribe_task2.done()

        # Trigger subscribe completion for one of them
        mock_paho.trigger_on_subscribe(subscribe_task2_mid)
        # The corresponding task completes
        await subscribe_task2
        # The other does not
        assert not subscribe_task1.done()

        # Complete the other one
        mock_paho.trigger_on_subscribe(subscribe_task1_mid)
        await subscribe_task1

    @pytest.mark.it("Can handle responses received before or after Paho invocation returns")
    @pytest.mark.parametrize("early_ack", early_ack_params)
    async def test_early_ack(self, client, mock_paho, early_ack):
        mock_paho._early_ack = early_ack
        await client.subscribe(fake_topic)
        # If this doesn't hang, the test passes

    @pytest.mark.it(
        "Retains pending subscribe tracking information only until receiving a response"
    )
    async def test_pending(self, client, mock_paho):
        # Require manual completion
        mock_paho._manual_mode = True

        # Start a subscribe. It won't complete
        subscribe_task = asyncio.create_task(client.subscribe(fake_topic))
        await asyncio.sleep(0.1)

        # Pending subscribe is tracked
        mid = mock_paho._last_mid
        assert mid in client._pending_subs

        # Trigger subscribe completion
        mock_paho.trigger_on_subscribe(mid)
        await subscribe_task

        # Pending subscribe is no longer tracked
        assert mid not in client._pending_subs

    @pytest.mark.it(
        "Does not establish pending subscribe tracking information if invoking Paho's subscribe returns a failed status"
    )
    @pytest.mark.parametrize("failing_rc", subscribe_failed_rc_params)
    async def test_pending_fail_status(self, client, mock_paho, failing_rc):
        mock_paho._subscribe_rc = failing_rc

        with pytest.raises(MQTTError):
            await client.subscribe(fake_topic)

        assert len(client._pending_subs) == 0

    @pytest.mark.it(
        "Does not establish pending subscribe tracking information if invoking Paho's subscribe raises an exception"
    )
    async def test_pending_fail_paho_raise(self, client, mock_paho, arbitrary_exception):
        mock_paho.subscribe.side_effect = arbitrary_exception

        with pytest.raises(type(arbitrary_exception)):
            await client.subscribe(fake_topic)

        assert len(client._pending_subs) == 0

    @pytest.mark.it("Clears pending subscribe tracking information if cancelled")
    async def test_pending_cancelled(self, client, mock_paho):
        # Require manual completion
        mock_paho._manual_mode = True

        # Start a subscribe. It won't complete
        subscribe_task = asyncio.create_task(client.subscribe(fake_topic))
        await asyncio.sleep(0.1)

        # Pending subscribe is tracked
        mid = mock_paho._last_mid
        assert mid in client._pending_subs

        # Cancel
        subscribe_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await subscribe_task

        # Pending subscribe is no longer tracked
        assert mid not in client._pending_subs

    @pytest.mark.it(
        "Raises CancelledError if the pending subscribe is cancelled by a disconnect attempt"
    )
    async def test_cancelled_by_disconnect(self, client, mock_paho):
        client_set_connected(client)
        # Require manual completion
        mock_paho._manual_mode = True

        # Start a subscribe. It won't complete
        subscribe_task = asyncio.create_task(client.subscribe(fake_topic))
        await asyncio.sleep(0.1)

        # Do a disconnect
        disconnect_task = asyncio.create_task(client.disconnect())
        mock_paho.trigger_on_disconnect(rc=mqtt.MQTT_ERR_SUCCESS)
        await asyncio.sleep(0.1)

        with pytest.raises(asyncio.CancelledError):
            await subscribe_task

        await disconnect_task

    @pytest.mark.it(
        "Raises CancelledError if the pending subscribe is cancelled by an unexpected disconnect"
    )
    async def test_cancelled_by_unexpected_disconnect(self, client, mock_paho):
        client_set_connected(client)
        # Require manual completion
        mock_paho._manual_mode = True

        # Start a subscribe. It won't complete
        subscribe_task = asyncio.create_task(client.subscribe(fake_topic))
        await asyncio.sleep(0.1)

        # Trigger unexpected disconnect
        mock_paho.trigger_on_disconnect(rc=mqtt.MQTT_ERR_CONN_LOST)
        await asyncio.sleep(0.1)

        with pytest.raises(asyncio.CancelledError):
            await subscribe_task

    @pytest.mark.it(
        "Can handle receiving a response for a subscribe that was cancelled after it was in-flight"
    )
    async def test_ack_after_cancel(self, client, mock_paho):
        # Require manual completion
        mock_paho._manual_mode = True

        # Start a subscribe. It won't complete
        subscribe_task = asyncio.create_task(client.subscribe(fake_topic))
        await asyncio.sleep(0.1)

        # Pending subscribe is tracked
        mid = mock_paho._last_mid
        assert mid in client._pending_subs

        # Cancel
        subscribe_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await subscribe_task

        # Pending subscribe is no longer tracked
        assert mid not in client._pending_subs

        # Trigger subscribe response after cancellation
        mock_paho.trigger_on_subscribe(mid)
        await asyncio.sleep(0.1)

        # No failure, no problem


@pytest.mark.describe("MQTTClient - .unsubscribe()")
class TestUnsubscribe(object):
    @pytest.mark.it("Invokes an MQTT unsubscribe via Paho")
    async def test_paho_invocation(self, mocker, client, mock_paho):
        assert mock_paho.unsubscribe.call_count == 0

        await client.unsubscribe(fake_topic)

        assert mock_paho.unsubscribe.call_count == 1
        assert mock_paho.unsubscribe.call_args == mocker.call(topic=fake_topic)

    @pytest.mark.it("Raises a MQTTError if invoking Paho's unsubscribe returns a failed status")
    @pytest.mark.parametrize("failing_rc", unsubscribe_failed_rc_params)
    async def test_fail_status(self, client, mock_paho, failing_rc):
        mock_paho._unsubscribe_rc = failing_rc

        with pytest.raises(MQTTError) as e_info:
            await client.unsubscribe(fake_topic)
        assert e_info.value.rc == failing_rc

    @pytest.mark.it("Allows any exceptions raised by invoking Paho's unsubscribe to propagate")
    async def test_fail_paho_invocation(self, client, mock_paho, arbitrary_exception):
        mock_paho.unsubscribe.side_effect = arbitrary_exception

        with pytest.raises(type(arbitrary_exception)):
            await client.unsubscribe(fake_topic)

    @pytest.mark.it(
        "Waits to return until Paho receives a matching response if the unsubscribe invocation succeeded"
    )
    async def test_waits_for_completion(self, client, mock_paho):
        # Require manual completion
        mock_paho._manual_mode = True

        # Start a unsubscribe. It won't complete
        unsubscribe_task = asyncio.create_task(client.unsubscribe(fake_topic))
        await asyncio.sleep(0.5)
        assert not unsubscribe_task.done()

        # Trigger unsubscribe completion
        mock_paho.trigger_on_unsubscribe(mock_paho._last_mid)
        await unsubscribe_task

    @pytest.mark.it("Does not return if Paho receives a non-matching response")
    async def test_nonmatching_completion(self, client, mock_paho):
        # Require manual completion
        mock_paho._manual_mode = True

        # Start two unsubscribes. They won't complete
        unsubscribe_task1 = asyncio.create_task(client.unsubscribe(fake_topic))
        await asyncio.sleep(0.1)
        unsubscribe_task1_mid = mock_paho._last_mid
        unsubscribe_task2 = asyncio.create_task(client.unsubscribe(fake_topic))
        await asyncio.sleep(0.1)
        unsubscribe_task2_mid = mock_paho._last_mid
        assert unsubscribe_task1_mid != unsubscribe_task2_mid
        await asyncio.sleep(0.5)
        assert not unsubscribe_task1.done()
        assert not unsubscribe_task2.done()

        # Trigger unsubscribe completion for one of them
        mock_paho.trigger_on_unsubscribe(unsubscribe_task2_mid)
        # The corresponding task completes
        await unsubscribe_task2
        # The other does not
        assert not unsubscribe_task1.done()

        # Complete the other one
        mock_paho.trigger_on_unsubscribe(unsubscribe_task1_mid)
        await unsubscribe_task1

    @pytest.mark.it("Can handle responses received before or after Paho invocation returns")
    @pytest.mark.parametrize("early_ack", early_ack_params)
    async def test_early_ack(self, client, mock_paho, early_ack):
        mock_paho._early_ack = early_ack
        await client.unsubscribe(fake_topic)
        # If this doesn't hang, the test passes

    @pytest.mark.it(
        "Retains pending unsubscribe tracking information only until receiving a response"
    )
    async def test_pending(self, client, mock_paho):
        # Require manual completion
        mock_paho._manual_mode = True

        # Start a unsubscribe. It won't complete
        unsubscribe_task = asyncio.create_task(client.unsubscribe(fake_topic))
        await asyncio.sleep(0.1)

        # Pending unsubscribe is tracked
        mid = mock_paho._last_mid
        assert mid in client._pending_unsubs

        # Trigger unsubscribe completion
        mock_paho.trigger_on_unsubscribe(mid)
        await unsubscribe_task

        # Pending unsubscribe is no longer tracked
        assert mid not in client._pending_unsubs

    @pytest.mark.it(
        "Does not establish pending unsubscribe tracking information if invoking Paho's unsubscribe returns a failed status"
    )
    @pytest.mark.parametrize("failing_rc", unsubscribe_failed_rc_params)
    async def test_pending_fail_status(self, client, mock_paho, failing_rc):
        mock_paho._unsubscribe_rc = failing_rc

        with pytest.raises(MQTTError):
            await client.unsubscribe(fake_topic)

        assert len(client._pending_unsubs) == 0

    @pytest.mark.it(
        "Does not establish pending unsubscribe tracking information if invoking Paho's unsubscribe raises an exception"
    )
    async def test_pending_fail_paho_raise(self, client, mock_paho, arbitrary_exception):
        mock_paho.unsubscribe.side_effect = arbitrary_exception

        with pytest.raises(type(arbitrary_exception)):
            await client.unsubscribe(fake_topic)

        assert len(client._pending_unsubs) == 0

    @pytest.mark.it("Clears pending unsubscribe tracking information if cancelled")
    async def test_pending_cancelled(self, client, mock_paho):
        # Require manual completion
        mock_paho._manual_mode = True

        # Start a unsubscribe. It won't complete
        unsubscribe_task = asyncio.create_task(client.unsubscribe(fake_topic))
        await asyncio.sleep(0.1)

        # Pending unsubscribe is tracked
        mid = mock_paho._last_mid
        assert mid in client._pending_unsubs

        # Cancel
        unsubscribe_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await unsubscribe_task

        # Pending unsubscribe is no longer tracked
        assert mid not in client._pending_unsubs

    @pytest.mark.it(
        "Raises CancelledError if the pending unsubscribe is cancelled by a disconnect attempt"
    )
    async def test_cancelled_by_disconnect(self, client, mock_paho):
        client_set_connected(client)
        # Require manual completion
        mock_paho._manual_mode = True

        # Start a unsubscribe. It won't complete
        unsubscribe_task = asyncio.create_task(client.unsubscribe(fake_topic))
        await asyncio.sleep(0.1)

        # Do a disconnect
        disconnect_task = asyncio.create_task(client.disconnect())
        mock_paho.trigger_on_disconnect(rc=mqtt.MQTT_ERR_SUCCESS)
        await asyncio.sleep(0.1)

        with pytest.raises(asyncio.CancelledError):
            await unsubscribe_task

        await disconnect_task

    @pytest.mark.it(
        "Raises CancelledError if the pending unsubscribe is cancelled by an unexpected disconnect"
    )
    async def test_cancelled_by_unexpected_disconnect(self, client, mock_paho):
        client_set_connected(client)
        # Require manual completion
        mock_paho._manual_mode = True

        # Start a unsubscribe. It won't complete
        unsubscribe_task = asyncio.create_task(client.unsubscribe(fake_topic))
        await asyncio.sleep(0.1)

        # Trigger unexpected disconnect
        mock_paho.trigger_on_disconnect(rc=mqtt.MQTT_ERR_CONN_LOST)
        await asyncio.sleep(0.1)

        with pytest.raises(asyncio.CancelledError):
            await unsubscribe_task

    @pytest.mark.it(
        "Can handle receiving a response for an unsubscribe that was cancelled after it was in-flight"
    )
    async def test_ack_after_cancel(self, client, mock_paho):
        # Require manual completion
        mock_paho._manual_mode = True

        # Start a unsubscribe. It won't complete
        unsubscribe_task = asyncio.create_task(client.unsubscribe(fake_topic))
        await asyncio.sleep(0.1)

        # Pending unsubscribe is tracked
        mid = mock_paho._last_mid
        assert mid in client._pending_unsubs

        # Cancel
        unsubscribe_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await unsubscribe_task

        # Pending subscribe is no longer tracked
        assert mid not in client._pending_unsubs

        # Trigger unsubscribe response after cancellation
        mock_paho.trigger_on_unsubscribe(mid)
        await asyncio.sleep(0.1)

        # No failure, no problem


@pytest.mark.describe("MQTTClient - .publish()")
class TestPublish(object):
    @pytest.mark.it("Invokes an MQTT publish via Paho")
    async def test_paho_invocation(self, mocker, client, mock_paho):
        assert mock_paho.publish.call_count == 0

        await client.publish(fake_topic, fake_payload)

        assert mock_paho.publish.call_count == 1
        assert mock_paho.publish.call_args == mocker.call(
            topic=fake_topic, payload=fake_payload, qos=1
        )

    # NOTE: MQTT_ERR_NO_CONN is not a failure for publish
    @pytest.mark.it("Raises a MQTTError if invoking Paho's publish returns a failed status")
    @pytest.mark.parametrize("failing_rc", publish_failed_rc_params)
    async def test_fail_status(self, client, mock_paho, failing_rc):
        mock_paho._publish_rc = failing_rc

        with pytest.raises(MQTTError) as e_info:
            await client.publish(fake_topic, fake_payload)
        assert e_info.value.rc == failing_rc

    @pytest.mark.it("Allows any exceptions raised by invoking Paho's publish to propagate")
    async def test_fail_paho_invocation(self, client, mock_paho, arbitrary_exception):
        mock_paho.publish.side_effect = arbitrary_exception

        with pytest.raises(type(arbitrary_exception)):
            await client.publish(fake_topic, fake_payload)

    @pytest.mark.it(
        "Waits to return until Paho receives a matching response if the publish invocation succeeded"
    )
    async def test_matching_completion_success(self, client, mock_paho):
        # Require manual completion
        mock_paho._manual_mode = True
        mock_paho._publish_rc = mqtt.MQTT_ERR_SUCCESS

        # Start a publish. It won't complete
        publish_task = asyncio.create_task(client.publish(fake_topic, fake_payload))
        await asyncio.sleep(0.5)
        assert not publish_task.done()

        # Trigger publish completion
        mock_paho.trigger_on_publish(mock_paho._last_mid)
        await publish_task

    @pytest.mark.it(
        "Waits to return until Paho receives a matching response (after connect established) if the publish invocation returned 'Not Connected'"
    )
    async def test_matching_completion_no_conn(self, client, mock_paho):
        # Require manual completion
        mock_paho._manual_mode = True
        mock_paho._publish_rc = mqtt.MQTT_ERR_NO_CONN

        # Start a publish. It won't complete
        publish_task = asyncio.create_task(client.publish(fake_topic, fake_payload))
        await asyncio.sleep(0.5)
        assert not publish_task.done()

        # NOTE: Yeah, the test refers to after the connect is established, but there's no need
        # to bring connection state into play here. Point is, after becoming connected, Paho will
        # automatically re-publish, and when a response is received it will trigger completion.

        # Trigger publish completion
        mock_paho.trigger_on_publish(mock_paho._last_mid)
        await publish_task

    @pytest.mark.it("Does not return if Paho receives a non-matching response")
    async def test_nonmatching_completion(self, client, mock_paho):
        # Require manual completion
        mock_paho._manual_mode = True

        # Start two publishes. They won't complete
        publish_task1 = asyncio.create_task(client.publish(fake_topic, fake_payload))
        await asyncio.sleep(0.1)
        publish_task1_mid = mock_paho._last_mid
        publish_task2 = asyncio.create_task(client.publish(fake_topic, fake_payload))
        await asyncio.sleep(0.1)
        publish_task2_mid = mock_paho._last_mid
        assert publish_task1_mid != publish_task2_mid
        await asyncio.sleep(0.5)
        assert not publish_task1.done()
        assert not publish_task2.done()

        # Trigger publish completion for one of them
        mock_paho.trigger_on_publish(publish_task2_mid)
        # The corresponding task completes
        await publish_task2
        # The other does not
        assert not publish_task1.done()

        # Complete the other one
        mock_paho.trigger_on_publish(publish_task1_mid)
        await publish_task1

    @pytest.mark.it("Can handle responses received before or after Paho invocation returns")
    @pytest.mark.parametrize("early_ack", early_ack_params)
    async def test_early_ack(self, client, mock_paho, early_ack):
        mock_paho._early_ack = early_ack
        await client.publish(fake_topic, fake_payload)
        # If this doesn't hang, the test passes

    @pytest.mark.it("Retains pending publish tracking information only until receiving a response")
    async def test_pending(self, client, mock_paho):
        # Require manual completion
        mock_paho._manual_mode = True

        # Start a publish. It won't complete
        publish_task = asyncio.create_task(client.publish(fake_topic, fake_payload))
        await asyncio.sleep(0.1)

        # Pending publish is tracked
        mid = mock_paho._last_mid
        assert mid in client._pending_pubs

        # Trigger publish completion
        mock_paho.trigger_on_publish(mid)
        await publish_task

        # Pending publish is no longer tracked
        assert mid not in client._pending_pubs

    @pytest.mark.it(
        "Does not establish pending publish tracking information if invoking Paho's publish returns a failed status"
    )
    @pytest.mark.parametrize("failing_rc", publish_failed_rc_params)
    async def test_pending_fail_status(self, client, mock_paho, failing_rc):
        mock_paho._publish_rc = failing_rc

        with pytest.raises(MQTTError):
            await client.publish(fake_topic, fake_payload)

        assert len(client._pending_pubs) == 0

    @pytest.mark.it(
        "Does not establish pending publish tracking information if invoking Paho's publish raises an exception"
    )
    async def test_pending_fail_paho_raise(self, client, mock_paho, arbitrary_exception):
        mock_paho.publish.side_effect = arbitrary_exception

        with pytest.raises(type(arbitrary_exception)):
            await client.publish(fake_topic, fake_payload)

        assert len(client._pending_subs) == 0

    @pytest.mark.it("Clears pending publish tracking information if cancelled")
    async def test_pending_cancelled(self, client, mock_paho):
        # Require manual completion
        mock_paho._manual_mode = True

        # Start a publish. It won't complete
        publish_task = asyncio.create_task(client.publish(fake_topic, fake_payload))
        await asyncio.sleep(0.1)

        # Pending publish is tracked
        mid = mock_paho._last_mid
        assert mid in client._pending_pubs

        # Cancel
        publish_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await publish_task

        # Pending publish is no longer tracked
        assert mid not in client._pending_pubs

    @pytest.mark.it(
        "Can handle receiving a response for a publish that was cancelled after it was in-flight"
    )
    async def test_ack_after_cancel(self, client, mock_paho):
        # Require manual completion
        mock_paho._manual_mode = True

        # Start a publish. It won't complete
        publish_task = asyncio.create_task(client.publish(fake_topic, fake_payload))
        await asyncio.sleep(0.1)

        # Pending publish is tracked
        mid = mock_paho._last_mid
        assert mid in client._pending_pubs

        # Cancel
        publish_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await publish_task

        # Pending publish is no longer tracked
        assert mid not in client._pending_pubs

        # Trigger publish response after cancellation
        mock_paho.trigger_on_publish(mid)
        await asyncio.sleep(0.1)

        # No failure, no problem
