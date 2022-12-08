# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

from v3_async_wip.mqtt_client import MQTTClient
from v3_async_wip import exceptions
from azure.iot.device.common import ProxyOptions
import paho.mqtt.client as mqtt
import asyncio
import logging
import pytest
from concurrent.futures import ThreadPoolExecutor

logging.basicConfig(level=logging.DEBUG)


fake_device_id = "MyDevice"
fake_hostname = "fake.hostname"
fake_password = "fake_password"
fake_username = fake_hostname + "/" + fake_device_id
fake_port = 443
fake_keepalive = 1234
fake_ws_path = "/fake/path"
fake_mid = 52
fake_rc = 0

PAHO_STATE_NEW = "NEW"
PAHO_STATE_DISCONNECTED = "DISCONNECTED"
PAHO_STATE_CONNECTED = "CONNECTED"
PAHO_STATE_CONNECTION_LOST = "CONNECTION_LOST"


@pytest.fixture(scope="module")
def paho_threadpool():
    # TODO: verify
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
    # "desired" connection state. The true connection is derived by other means (sockets).
    # For simplicity, I've rolled all the information relevant to mocking behavior into a
    # 3-state value.
    mock_paho._state = PAHO_STATE_DISCONNECTED
    # Indicates whether or not invocations should immediately trigger completions
    mock_paho._manual_mode = False
    # Default rc value to return on invocations of method mocks
    mock_paho._connect_rc = 0
    mock_paho._publish_rc = 0
    mock_paho._subscribe_rc = 0
    mock_paho._unsubscribe_rc = 0
    # NOTE: There is no _disconnect_rc because disconnect return values are deterministic
    # See the implementation of trigger_disconnect and the mock disconnect below.

    # Utility helpers
    def trigger_connect(rc=0):
        if rc == 0:
            # State is only set to connected if successfully connecting
            mock_paho._state = PAHO_STATE_CONNECTED
        paho_threadpool.submit(
            mock_paho.on_connect, client=mock_paho, userdata=None, flags=None, rc=rc
        )

    mock_paho.trigger_connect = trigger_connect

    def trigger_disconnect(rc=0):
        if mock_paho._state == PAHO_STATE_CONNECTED:
            mock_paho._state = PAHO_STATE_CONNECTION_LOST
        paho_threadpool.submit(mock_paho.on_disconnect, client=mock_paho, userdata=None, rc=rc)

    mock_paho.trigger_disconnect = trigger_disconnect

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

    mock_paho.is_connected.side_effect = is_connected
    mock_paho.connect.side_effect = connect
    mock_paho.disconnect.side_effect = disconnect

    mock_paho.subscribe = mocker.MagicMock(return_value=(fake_rc, fake_mid))
    mock_paho.unsubscribe = mocker.MagicMock(return_value=(fake_rc, fake_mid))
    mock_paho.publish = mocker.MagicMock(return_value=(fake_rc, fake_mid))

    mocker.patch.object(mqtt, "Client", return_value=mock_paho)

    return mock_paho


@pytest.fixture
async def fresh_client(mock_paho):
    # Implicitly imports the mocked Paho MQTT Client due to patch in mock_paho
    client = MQTTClient(client_id=fake_device_id, hostname=fake_hostname, port=fake_port)
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
    client._connected = True
    client._mqtt_client._state = PAHO_STATE_CONNECTED


def client_set_disconnected(client):
    client._connected = False
    client._mqtt_client._state = PAHO_STATE_DISCONNECTED


def client_set_connection_dropped(client):
    client._connected = False
    client._mqtt_client._state = PAHO_STATE_CONNECTION_LOST


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


# NOTE: Because clients in Disconnected and Connection Dropped states have the same behaviors
# during a connect, define a parent class that can be subclassed so tests don't have to be
# written twice.
# NOTE: Failure responses can be either a single invocation of Paho's .on_connect handler
# or a paired invocation of both Paho's .on_connect and .on_disconnect. Both cases are covered.
# Why does this happen? I don't know. But it does, and the client is designed to handle it.
class ConnectWithClientNotConnectedTests(object):
    @pytest.mark.it("Invokes an MQTT connect via Paho using stored values")
    async def test_paho_invocation(self, mocker, client, mock_paho):
        assert mock_paho.connect.call_count == 0

        await client.connect()

        assert mock_paho.connect.call_count == 1
        assert mock_paho.connect.call_args == mocker.call(
            host=client._hostname, port=client._port, keepalive=client._keep_alive
        )

    @pytest.mark.it("Raises a ConnectionFailedError if there is a failure invoking Paho's connect")
    async def test_fail_paho_invocation(self, client, mock_paho, arbitrary_exception):
        mock_paho.connect.side_effect = arbitrary_exception

        with pytest.raises(exceptions.ConnectionFailedError) as e_info:
            await client.connect()
        e_info.value.__cause__ is arbitrary_exception

    @pytest.mark.it(
        "Raises a ConnectionFailedError if invoking Paho's connect returns a failed status"
    )
    async def test_fail_status(self, client, mock_paho):
        mock_paho._connect_rc = 1

        with pytest.raises(exceptions.ConnectionFailedError):
            await client.connect()

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

        with pytest.raises(exceptions.ConnectionFailedError):
            await client.connect()

        assert mock_paho.loop_start.call_count == 0

    @pytest.mark.it("Does not start the Paho network loop if the connect returns a failed status")
    async def test_network_loop_connect_fail_status(self, client, mock_paho):
        assert mock_paho.loop_start.call_count == 0
        mock_paho._connect_rc = 1

        with pytest.raises(exceptions.ConnectionFailedError):
            await client.connect()

        assert mock_paho.loop_start.call_count == 0

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
        "Raises a ConnectionFailedError if the connect attempt receives a failure response"
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

        # Send failure response
        mock_paho.trigger_connect(rc=5)
        if paired_failure:
            mock_paho.trigger_disconnect(rc=5)
        with pytest.raises(exceptions.ConnectionFailedError):
            await connect_task

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

        with pytest.raises(exceptions.ConnectionFailedError):
            await client.connect()

        assert not client.is_connected()

    @pytest.mark.it(
        "Leaves the client in a disconnected state if invoking Paho's connect returns a failed status"
    )
    async def test_state_fail_status(self, client, mock_paho):
        # Return a fail status
        mock_paho._connect_rc = 1
        assert not client.is_connected()

        with pytest.raises(exceptions.ConnectionFailedError):
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
        # Send fail response
        mock_paho.trigger_connect(rc=5)
        if paired_failure:
            mock_paho.trigger_disconnect(rc=5)

        with pytest.raises(exceptions.ConnectionFailedError):
            await connect_task

        assert not client.is_connected()

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
        with pytest.raises(exceptions.ConnectionFailedError):
            await connect_task
        assert mock_paho.loop_start.call_count == 1
        assert mock_paho.loop_stop.call_count == 1


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
    async def test_paho_invocation(self, mocker, client, mock_paho):
        assert mock_paho.connect.call_count == 0

        await client.connect()

        assert mock_paho.connect.call_count == 0

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
        # Trigger disconnect completion
        mock_paho.trigger_disconnect(rc=0)
        if double_response:
            mock_paho.trigger_disconnect(rc=0)
        await disconnect_task

        assert not client.is_connected()


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

    @pytest.mark.it("Stops the Paho network loop")
    async def test_network_loop(self, client, mock_paho):
        assert mock_paho.loop_stop.call_count == 0

        await client.disconnect()

        assert mock_paho.loop_stop.call_count == 1

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


@pytest.mark.describe("MQTTClient - .disconnect() -- Client Already Disconnected")
class TestDisconnectWithClientDisconnected(object):
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

    @pytest.mark.it("Does not stop the Paho network loop")
    async def test_network_loop(self, client, mock_paho):
        assert mock_paho.loop_stop.call_count == 0

        await client.disconnect()

        assert mock_paho.loop_stop.call_count == 0

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


@pytest.mark.describe("MQTTClient - OCCURRENCE: Unexpected Disconnect")
class TestUnexpectedDisconnect(object):
    @pytest.mark.it("Puts the client in a disconnected state")
    async def test_state(self, client, mock_paho):
        client_set_connected(client)
        assert client.is_connected()

        mock_paho.trigger_disconnect(rc=7)
        await asyncio.sleep(0.1)

        assert not client.is_connected()

    @pytest.mark.it("Does not stop the Paho network loop")
    async def test_network_loop(self, client, mock_paho):
        client_set_connected(client)
        assert mock_paho.loop_stop.call_count == 0

        mock_paho.trigger_disconnect(rc=7)
        await asyncio.sleep(0.1)

        assert mock_paho.loop_stop.call_count == 0


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
