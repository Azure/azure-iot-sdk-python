# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

from v3_async_wip.mqtt_client import MQTTClient, MQTTError, MQTTConnectionFailedError
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
fake_mid = 52
fake_rc = 0

PAHO_STATE_NEW = "NEW"
PAHO_STATE_DISCONNECTED = "DISCONNECTED"
PAHO_STATE_CONNECTED = "CONNECTED"
PAHO_STATE_CONNECTION_LOST = "CONNECTION_LOST"

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
    # Indicates whether or not invocations should automatically trigger completions
    mock_paho._manual_mode = False
    # Indicates whether or not invocations should trigger completions immediately
    # (i.e. before invocation return)
    # NOTE: While the "normal" behavior we can expect is NOT an early ack, we set early ack
    # as the default for test performance reasons
    # TODO: incorporate this into conn/disconn tests
    mock_paho._early_ack = True
    # Default rc value to return on invocations of method mocks
    # NOTE: There is no _disconnect_rc because disconnect return values are deterministic
    # See the implementation of trigger_disconnect and the mock disconnect below.
    mock_paho._connect_rc = 0
    mock_paho._publish_rc = 0
    mock_paho._subscribe_rc = 0
    mock_paho._unsubscribe_rc = 0
    # Last mid that was returned. Will be incremented over time (see _get_next_mid())
    # NOTE: 0 means no mid has been sent yet
    mock_paho._last_mid = 0

    # Utility helpers
    def trigger_connect(rc=0):
        if rc == 0:
            # State is only set to connected if successfully connecting
            mock_paho._state = PAHO_STATE_CONNECTED
        else:
            # If it fails it ends up in a "new" state.
            mock_paho._state = PAHO_STATE_NEW
        paho_threadpool.submit(
            mock_paho.on_connect, client=mock_paho, userdata=None, flags=None, rc=rc
        )

    mock_paho.trigger_connect = trigger_connect

    def trigger_disconnect(rc=0):
        if mock_paho._state == PAHO_STATE_CONNECTED:
            mock_paho._state = PAHO_STATE_CONNECTION_LOST
        paho_threadpool.submit(mock_paho.on_disconnect, client=mock_paho, userdata=None, rc=rc)

    mock_paho.trigger_disconnect = trigger_disconnect

    def trigger_subscribe(mid=None):
        if not mid:
            mid = mock_paho._last_mid
        if not mock_paho._early_ack:
            paho_threadpool.submit(time.sleep, ACK_DELAY)
        paho_threadpool.submit(
            mock_paho.on_subscribe, client=mock_paho, userdata=None, mid=mid, granted_qos=1
        )

    mock_paho.trigger_subscribe = trigger_subscribe

    def trigger_unsubscribe(mid=None):
        if not mid:
            mid = mock_paho._last_mid
        if not mock_paho._early_ack:
            paho_threadpool.submit(time.sleep, ACK_DELAY)
        paho_threadpool.submit(mock_paho.on_unsubscribe, client=mock_paho, userdata=None, mid=mid)

    mock_paho.trigger_unsubscribe = trigger_unsubscribe

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
        # Only trigger completion if returning rc=0
        if not mock_paho._manual_mode and mock_paho._connect_rc == 0:
            mock_paho.trigger_connect()
        return mock_paho._connect_rc

    def disconnect(*args, **kwargs):
        # NOTE: THERE IS NO WAY TO OVERRIDE THIS RETURN VALUE AS IT IS DETERMINISTIC
        # BASED ON THE PAHO STATE
        if mock_paho._state == PAHO_STATE_CONNECTED:
            mock_paho._state = PAHO_STATE_DISCONNECTED
            if not mock_paho._manual_mode:
                mock_paho.trigger_disconnect()
            rc = 0
        else:
            mock_paho._state = PAHO_STATE_DISCONNECTED
            rc = 4
        return rc

    def subscribe(*args, **kwargs):
        if mock_paho._subscribe_rc != 0:
            mid = None
        else:
            mid = mock_paho._get_next_mid()
            if not mock_paho._manual_mode:
                mock_paho.trigger_subscribe(mid)
        return (mock_paho._subscribe_rc, mid)

    def unsubscribe(*args, **kwargs):
        if mock_paho._unsubscribe_rc != 0:
            mid = None
        else:
            mid = mock_paho._get_next_mid()
            if not mock_paho._manual_mode:
                mock_paho.trigger_unsubscribe(mid)
        return (mock_paho._unsubscribe_rc, mid)

    mock_paho.is_connected.side_effect = is_connected
    mock_paho.connect.side_effect = connect
    mock_paho.disconnect.side_effect = disconnect
    mock_paho.subscribe.side_effect = subscribe
    mock_paho.unsubscribe.side_effect = unsubscribe

    mock_paho.publish = mocker.MagicMock(return_value=(fake_rc, fake_mid))

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

    @pytest.mark.it("Does not set any proxy if no ProxyOptions is provided")
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

    @pytest.mark.it("Sets the websockets path using the provided value if using websockets")
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

    @pytest.mark.it("Does not set the websocket path if it is not provided")
    async def test_no_ws_path(self, mocker):
        mock_paho = mocker.patch.object(mqtt, "Client").return_value

        MQTTClient(
            client_id=fake_device_id, hostname=fake_hostname, port=fake_port, transport="websockets"
        )

        # Websockets path was not set
        assert mock_paho.ws_set_options.call_count == 0

    @pytest.mark.it("Does not set the websocket path if not using websockets")
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


# NOTE: Because clients in Disconnected, Connection Dropped, and Fresh states have the same
# behaviors during a connect, define a parent class that can be subclassed so tests don't have
# to be written twice.
# NOTE: Failure responses can be either a single invocation of Paho's .on_connect handler
# or a paired invocation of both Paho's .on_connect and .on_disconnect. Both cases are covered.
# Why does this happen? I don't know. But it does, and the client is designed to handle it.
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

    @pytest.mark.it(
        "Raises a MQTTConnectionFailedError if invoking Paho's connect returns a failed status"
    )
    async def test_fail_status(self, client, mock_paho):
        failing_rc = 1
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

    @pytest.mark.it("Does not start the Paho network loop if the connect returns a failed status")
    async def test_network_loop_connect_fail_status(self, client, mock_paho):
        assert mock_paho.loop_start.call_count == 0
        mock_paho._connect_rc = 1

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
        "Waits to return until Paho receives a response if the connect invocation succeeded"
    )
    @pytest.mark.parametrize(
        "success",
        [pytest.param(True, id="Connect Success"), pytest.param(False, id="Connect Failure")],
    )
    async def test_waits_for_completion(self, client, mock_paho, success):
        # Require manual completion
        mock_paho._manual_mode = True

        # Start a connect. It won't complete
        connect_task = asyncio.create_task(client.connect())
        await asyncio.sleep(0.5)
        assert not connect_task.done()

        # Trigger connect completion
        rc = 0 if success else 1
        mock_paho.trigger_connect(rc)
        await asyncio.sleep(0.1)
        assert connect_task.done()

    @pytest.mark.it(
        "Raises a MQTTConnectionFailedError if the connect attempt receives a failure response"
    )
    @pytest.mark.parametrize(
        "paired_failure",
        [
            pytest.param(False, id="Single Connect Failure Response"),
            pytest.param(True, id="Paired Connect/Disconnect Failure Response"),
        ],
    )
    async def test_fail_response(self, client, mock_paho, paired_failure):
        # Require manual completion
        mock_paho._manual_mode = True

        # Attempt connect
        connect_task = asyncio.create_task(client.connect())
        await asyncio.sleep(0.1)

        # Send failure response
        mock_paho.trigger_connect(rc=5)
        if paired_failure:
            mock_paho.trigger_disconnect(rc=5)
        with pytest.raises(MQTTConnectionFailedError) as e_info:
            await connect_task
        assert e_info.value.rc == 5

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

    @pytest.mark.it(
        "Leaves the client in a disconnected state if invoking Paho's connect returns a failed status"
    )
    async def test_state_fail_status(self, client, mock_paho):
        # Return a fail status
        mock_paho._connect_rc = 1
        assert not client.is_connected()

        with pytest.raises(MQTTConnectionFailedError):
            await client.connect()

        assert not client.is_connected()

    @pytest.mark.it(
        "Leaves the client in a disconnected state if the connect attempt receives a failure response"
    )
    @pytest.mark.parametrize(
        "paired_failure",
        [
            pytest.param(False, id="Single Connect Failure Response"),
            pytest.param(True, id="Paired Connect/Disconnect Failure Response"),
        ],
    )
    async def test_state_fail_response(self, client, mock_paho, paired_failure):
        # Require manual completion
        mock_paho._manual_mode = True
        assert not client.is_connected()

        # Attempt connect
        connect_task = asyncio.create_task(client.connect())
        await asyncio.sleep(0.1)
        # Send fail response
        mock_paho.trigger_connect(rc=5)
        if paired_failure:
            mock_paho.trigger_disconnect(rc=5)

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

    @pytest.mark.it(
        "Leaves the reconnect daemon running if invoking Paho's connect returns a failed status"
    )
    async def test_reconnect_daemon_fail_status(self, client, mock_paho):
        # Return a fail status
        mock_paho._connect_rc = 1
        client._auto_reconnect = True
        assert client._reconnect_daemon is None

        with pytest.raises(MQTTConnectionFailedError):
            await client.connect()

        assert isinstance(client._reconnect_daemon, asyncio.Task)
        assert not client._reconnect_daemon.done()

    @pytest.mark.it(
        "Leaves the reconnect daemon running if the connect attempt receives a failure response"
    )
    @pytest.mark.parametrize(
        "paired_failure",
        [
            pytest.param(False, id="Single Connect Failure Response"),
            pytest.param(True, id="Paired Connect/Disconnect Failure Response"),
        ],
    )
    async def test_reconnect_daemon_fail_response(self, client, mock_paho, paired_failure):
        # Require manual completion
        mock_paho._manual_mode = True
        client._auto_reconnect = True
        assert client._reconnect_daemon is None

        # Attempt connect
        connect_task = asyncio.create_task(client.connect())
        await asyncio.sleep(0.1)
        # Send fail response
        mock_paho.trigger_connect(rc=5)
        if paired_failure:
            mock_paho.trigger_disconnect(rc=5)

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
    @pytest.mark.parametrize(
        "paired_failure",
        [
            pytest.param(False, id="Single Connect Failure Response"),
            pytest.param(True, id="Paired Connect/Disconnect Failure Response"),
        ],
    )
    async def test_network_loop_fail_response(self, mocker, client, mock_paho, paired_failure):
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

        # Send failure response
        mock_paho.trigger_connect(rc=5)
        if paired_failure:
            mock_paho.trigger_disconnect(rc=5)
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
# NOTE: Paho's .disconnect() method will always return success (rc = 0) when the client is
# connected. As such, we don't have to test rc != 0 here (it is covered in other test classes)
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
        mock_paho.trigger_disconnect(rc=0)
        if double_response:
            mock_paho.trigger_disconnect(rc=0)
        await disconnect_task

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
        mock_paho.trigger_disconnect(rc=0)
        if double_response:
            mock_paho.trigger_disconnect(rc=0)
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
        mock_paho.trigger_disconnect(rc=0)
        if double_response:
            mock_paho.trigger_disconnect(rc=0)
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
        mock_paho.trigger_disconnect(rc=0)
        if double_response:
            mock_paho.trigger_disconnect(rc=0)
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
        mock_paho.trigger_disconnect(rc=0)
        if double_response:
            mock_paho.trigger_disconnect(rc=0)
        await disconnect_task

        # All were cancelled
        for mock in mock_subs:
            assert mock.cancel.call_count == 1
        for mock in mock_unsubs:
            assert mock.cancel.call_count == 1
        # All were removed
        assert len(client._pending_subs) == 0
        assert len(client._pending_unsubs) == 0


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

        mock_paho.trigger_disconnect(rc=7)
        await asyncio.sleep(0.1)

        assert not client.is_connected()

    @pytest.mark.it("Stops the Paho network loop")
    async def test_network_loop(self, client, mock_paho):
        client_set_connected(client)
        assert mock_paho.loop_stop.call_count == 0

        mock_paho.trigger_disconnect(rc=7)
        await asyncio.sleep(0.1)

        assert mock_paho.loop_stop.call_count == 1

    @pytest.mark.it("Does not alter the reconnect daemon")
    async def test_reconnect_daemon(self, mocker, client, mock_paho):
        client_set_connected(client)
        client._auto_reconnect = True
        mock_task = mocker.MagicMock()
        client._reconnect_daemon = mock_task

        mock_paho.trigger_disconnect(rc=7)
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
        mock_paho.trigger_disconnect(rc=7)
        await asyncio.sleep(0.1)

        # All were cancelled
        for mock in mock_subs:
            assert mock.cancel.call_count == 1
        for mock in mock_unsubs:
            assert mock.cancel.call_count == 1
        # All were removed
        assert len(client._pending_subs) == 0
        assert len(client._pending_unsubs) == 0


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
        rc = 0 if pending_success else 1
        mock_paho.trigger_connect(rc=rc)
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
            mock_paho.trigger_connect(rc=0)
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
        mock_paho.trigger_disconnect(rc=0)
        await asyncio.sleep(0.1)
        assert disconnect_task.done()
        assert not client.is_connected()

        # Connect task has now invoked Paho connect and is waiting for completion
        assert not connect_task.done()
        assert mock_paho.connect.call_count == 1
        # Complete the connect
        mock_paho.trigger_connect(rc=0)
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
        rc = 0 if pending_success else 1
        mock_paho.trigger_connect(rc=rc)
        await asyncio.sleep(0.1)
        assert connect_task.done()

        if pending_success:
            assert client.is_connected()
            # Disconnect was invoked on Paho and is waiting for completion
            assert not disconnect_task.done()
            assert mock_paho.disconnect.call_count == 1
            # Complete the disconnect
            mock_paho.trigger_disconnect(rc=0)
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
        mock_paho.trigger_disconnect(rc=0)
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
        mock_paho.trigger_disconnect(rc=7)
        await asyncio.sleep(0.1)

        # Connect was called by the daemon
        assert client.connect.call_count == 1
        assert client.connect.call_args == mocker.call()

    @pytest.mark.it(
        "Waits for the reconnect interval (in seconds) to try to connect again if the connect attempt fails non-fatally"
    )
    async def test_reconnect_attempt_fails_nonfatal(self, mocker, client, mock_paho):
        # Set connect to fail (nonfatal)
        exc = MQTTConnectionFailedError(rc=1, fatal=False)
        client.connect = mocker.AsyncMock(side_effect=exc)
        assert client.connect.call_count == 0

        # Drop the connection
        mock_paho.trigger_disconnect(rc=7)
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
        mock_paho.trigger_disconnect(rc=7)
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
        mock_paho.trigger_disconnect(rc=7)
        await asyncio.sleep(0.1)

        # Connect was called by the daemon
        assert client.connect.call_count == 1
        # Wait for the interval
        await asyncio.sleep(client._reconnect_interval)
        # Connect was not attempted again
        assert client.connect.call_count == 1

        # Drop the connection again
        mock_paho.trigger_disconnect(rc=7)
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
    async def test_fail_status(self, client, mock_paho):
        failing_rc = 4
        mock_paho._subscribe_rc = failing_rc

        with pytest.raises(MQTTError) as e_info:
            await client.subscribe(fake_topic)
        assert e_info.value.rc == failing_rc

    @pytest.mark.it("Allows any exceptions raised by invoking Paho's subscribe to propagate")
    async def test_fail_paho_invocation(self, client, mock_paho, arbitrary_exception):
        mock_paho.subscribe.side_effect = arbitrary_exception

        with pytest.raises(type(arbitrary_exception)):
            await client.subscribe(fake_topic)

    @pytest.mark.it("Waits to return until Paho receives a response")
    async def test_waits_for_completion(self, client, mock_paho):
        # Require manual completion
        mock_paho._manual_mode = True

        # Start a subscribe. It won't complete
        subscribe_task = asyncio.create_task(client.subscribe(fake_topic))
        await asyncio.sleep(0.5)
        assert not subscribe_task.done()

        # Trigger subscribe completion
        mock_paho.trigger_subscribe(mock_paho._last_mid)
        await subscribe_task

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

        # Pending subscription is tracked
        mid = mock_paho._last_mid
        assert mid in client._pending_subs

        # Trigger subscribe completion
        mock_paho.trigger_subscribe(mid)
        await subscribe_task

        # Pending subscription is no longer tracked
        assert mid not in client._pending_subs

    @pytest.mark.it(
        "Does not establish pending subscribe tracking information if invoking Paho's subscribe returns a failed status"
    )
    async def test_pending_fail_status(self, client, mock_paho):
        failing_rc = 4
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

        # Pending subscription is tracked
        mid = mock_paho._last_mid
        assert mid in client._pending_subs

        # Cancel
        subscribe_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await subscribe_task

        # Pending subscription is no longer tracked
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
        mock_paho.trigger_disconnect(rc=0)
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
        mock_paho.trigger_disconnect(rc=7)
        await asyncio.sleep(0.1)

        with pytest.raises(asyncio.CancelledError):
            await subscribe_task


@pytest.mark.describe("MQTTClient - .unsubscribe()")
class TestUnsubscribe(object):
    @pytest.mark.it("Invokes an MQTT unsubscribe via Paho")
    async def test_paho_invocation(self, mocker, client, mock_paho):
        assert mock_paho.unsubscribe.call_count == 0

        await client.unsubscribe(fake_topic)

        assert mock_paho.unsubscribe.call_count == 1
        assert mock_paho.unsubscribe.call_args == mocker.call(topic=fake_topic)

    @pytest.mark.it("Raises a MQTTError if invoking Paho's unsubscribe returns a failed status")
    async def test_fail_status(self, client, mock_paho):
        failing_rc = 4
        mock_paho._unsubscribe_rc = failing_rc

        with pytest.raises(MQTTError) as e_info:
            await client.unsubscribe(fake_topic)
        assert e_info.value.rc == failing_rc

    @pytest.mark.it("Allows any exceptions raised by invoking Paho's unsubscribe to propagate")
    async def test_fail_paho_invocation(self, client, mock_paho, arbitrary_exception):
        mock_paho.unsubscribe.side_effect = arbitrary_exception

        with pytest.raises(type(arbitrary_exception)):
            await client.unsubscribe(fake_topic)

    @pytest.mark.it("Waits to return until Paho receives a response")
    async def test_waits_for_completion(self, client, mock_paho):
        # Require manual completion
        mock_paho._manual_mode = True

        # Start a unsubscribe. It won't complete
        unsubscribe_task = asyncio.create_task(client.unsubscribe(fake_topic))
        await asyncio.sleep(0.5)
        assert not unsubscribe_task.done()

        # Trigger unsubscribe completion
        mock_paho.trigger_unsubscribe(mock_paho._last_mid)
        await unsubscribe_task

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

        # Pending subscription is tracked
        mid = mock_paho._last_mid
        assert mid in client._pending_unsubs

        # Trigger unsubscribe completion
        mock_paho.trigger_unsubscribe(mid)
        await unsubscribe_task

        # Pending subscription is no longer tracked
        assert mid not in client._pending_unsubs

    @pytest.mark.it(
        "Does not establish pending unsubscribe tracking information if invoking Paho's unsubscribe returns a failed status"
    )
    async def test_pending_fail_status(self, client, mock_paho):
        failing_rc = 4
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

        # Pending subscription is tracked
        mid = mock_paho._last_mid
        assert mid in client._pending_unsubs

        # Cancel
        unsubscribe_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await unsubscribe_task

        # Pending subscription is no longer tracked
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
        mock_paho.trigger_disconnect(rc=0)
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
        mock_paho.trigger_disconnect(rc=7)
        await asyncio.sleep(0.1)

        with pytest.raises(asyncio.CancelledError):
            await unsubscribe_task
