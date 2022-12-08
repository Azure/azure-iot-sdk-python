# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import asyncio
import functools
import logging
import paho.mqtt.client as mqtt
import weakref
from v3_async_wip import exceptions


logger = logging.getLogger(__name__)

OP_TYPE_CONNECT = "CONNECT"
OP_TYPE_DISCONNECT = "DISCONNECT"

RECONNECT_MODE_DROP = "RECONNECT_DROP"
RECONNECT_MODE_ALL = "RECONNECT_ALL"


class ConnectionLock(asyncio.Lock):
    """
    Async Lock with an attribute that can be set indicating the type of connection operation
    This information is just for logging purposes.
    """

    def __init__(self, *args, **kwargs):
        self.connection_type = None
        super().__init__(*args, **kwargs)

    def release(self):
        self.connection_type = None
        super().release()


class MQTTClient(object):
    """Provides an async MQTT message broker interface."""

    def __init__(
        self,
        client_id,
        hostname,
        port,
        transport="tcp",
        keep_alive=60,
        auto_reconnect=False,
        ssl_context=None,
        websockets_path=None,
        proxy_options=None,
    ):
        """
        Constructor to instantiate client.
        :param str client_id: The id of the client connecting to the broker.
        :param str hostname: Hostname or IP address of the remote broker.
        :param int port: Network port to connect to
        :param str transport: "tcp" for TCP or "websockets" for WebSockets.
        :param int keep_alive: Number of seconds before connection timeout.
        :param bool auto_reconnect: Indicates whether or not client should reconnect when a
            connection is unexpectedly dropped.
        :param ssl_context: The SSL Context to use with MQTT. If not provided will use default.
        :type ssl_context: :class:`ssl.SSLContext`
        :param str websockets_path: Path for websocket connection.
            Starts with '/' and should be the endpoint of the mqtt connection on the remote server.
        :param proxy_options: Options for sending traffic through proxy servers.
        """
        # Configuration
        self._hostname = hostname
        self._port = port
        self._keep_alive = keep_alive
        self._auto_reconnect = auto_reconnect
        self._reconnect_interval = 10  # TODO: make this configurable

        # Client
        self._mqtt_client = self._create_mqtt_client(
            client_id, transport, ssl_context, proxy_options, websockets_path
        )

        # Connection State
        # NOTE: This doesn't need a lock to protect it. State is only changed via Paho handlers.
        # Those handlers cannot be run simultaneously.
        # TODO: is this actually true though? Sure, it's only written from one place, but what about reads?
        self._connected = False

        # Synchronization
        self.connected_cond = asyncio.Condition()
        self.disconnected_cond = asyncio.Condition()
        self._connect_failed_cond = asyncio.Condition()
        self._connection_lock = ConnectionLock()

        # Tasks
        self._reconnect_daemon = None

        # Event Loop
        self._loop = asyncio.get_running_loop()

    def _create_mqtt_client(
        self, client_id, transport, ssl_context, proxy_options, websockets_path
    ):
        """
        Create the MQTT client object and assign all necessary event handler callbacks.
        """
        logger.debug("Creating Paho client")

        # Instantiate the client
        mqtt_client = mqtt.Client(
            client_id=client_id,
            clean_session=False,
            protocol=mqtt.MQTTv311,
            transport=transport,
            reconnect_on_failure=False,  # We handle reconnect logic ourselves
        )
        if transport == "websockets" and websockets_path:
            logger.debug("Configuring Paho client for connecting using MQTT over websockets")
            mqtt_client.ws_set_options(path=websockets_path)
        else:
            logger.debug("Configuring Paho client for connecting using MQTT over TCP")

        if proxy_options:
            logger.debug("Configuring custom proxy options on Paho client")
            mqtt_client.proxy_set(
                proxy_type=proxy_options.proxy_type_socks,
                proxy_addr=proxy_options.proxy_address,
                proxy_port=proxy_options.proxy_port,
                proxy_username=proxy_options.proxy_username,
                proxy_password=proxy_options.proxy_password,
            )

        mqtt_client.enable_logger(logging.getLogger("paho"))

        # Configure TLS/SSL. If the value passed is None, will use default.
        mqtt_client.tls_set_context(context=ssl_context)

        # Set event handlers.  Use weak references back into this object to prevent leaks
        self_weakref = weakref.ref(self)

        def on_connect(client, userdata, flags, rc):
            this = self_weakref()
            message = mqtt.connack_string(rc)
            logger.debug("Connect Response: rc {} - {}".format(rc, message))

            if rc == mqtt.CONNACK_ACCEPTED:

                # Notify tasks waiting on successful connection
                async def set_connected():
                    logger.debug("Client State: CONNECTED")
                    this._connected = True
                    async with this.connected_cond:
                        this.connected_cond.notify_all()

                f = asyncio.run_coroutine_threadsafe(set_connected(), this._loop)
                # Need to wait for this one to finish since we don't want to let another
                # Paho handler invoke until we know the connection state has been set.
                f.result()
            else:

                # Notify tasks waiting on failed connection
                async def notify_connection_fail():
                    async with this._connect_failed_cond:
                        this._connect_failed_cond.notify_all()

                asyncio.run_coroutine_threadsafe(notify_connection_fail(), this._loop)

        def on_disconnect(client, userdata, rc):
            this = self_weakref()
            message = mqtt.error_string(rc)

            # NOTE: It's not generally safe to use .is_connected() to determine what to do, since
            # the value could change at any time. However, it IS safe to do so here.
            # This handler, as well as .on_connect() above, are the only two functions that can
            # change the value. They are both invoked on Paho's network loop, which is
            # single-threaded. This means there cannot be overlapping invocations that would
            # change the value, and thus that the value will not change during execution of this
            # block.
            if this.is_connected():
                if this._should_be_connected():
                    logger.debug("Unexpected Disconnect: rc {} - {}".format(rc, message))
                else:
                    logger.debug("Disconnect Response: rc {} - {}".format(rc, message))

                # Change state and notify tasks waiting on disconnect
                async def set_disconnected():
                    logger.debug("Client State: DISCONNECTED")
                    this._connected = False
                    async with this.disconnected_cond:
                        this.disconnected_cond.notify_all()

                f = asyncio.run_coroutine_threadsafe(set_disconnected(), this._loop)
                # Need to wait for this one to finish since we don't want to let another
                # Paho handler invoke until we know the connection state has been set.
                f.result()

            else:
                if this._connection_lock.connection_type == OP_TYPE_CONNECT:
                    # Sometimes when Paho receives a failure response to a connect, the disconnect
                    # handler is also called. Why? Who knows.
                    # But we don't wish to issue spurious notifications or network loop stoppage.
                    logger.debug(
                        "Connect Failure Disconnect Response: rc {} - {}".format(rc, message)
                    )
                else:
                    # Double disconnect. Suppress.
                    # Sometimes Paho disconnects twice. Why? Who knows.
                    # But we don't wish to issue spurious notifications or network loop stoppage.
                    logger.debug("Double Disconnect Response: rc {} - {}".format(rc, message))

        def on_subscribe(client, userdata, mid):
            pass

        def on_unsubscribe(client, userdata, mid):
            pass

        mqtt_client.on_connect = on_connect
        mqtt_client.on_disconnect = on_disconnect
        mqtt_client.on_subscribe = on_subscribe
        mqtt_client.on_unsubscribe = on_unsubscribe

        return mqtt_client

    async def _reconnect_loop(self):
        logger.debug("Reconnect Daemon starting...")
        try:
            while True:
                async with self.disconnected_cond:
                    # NOTE: is_connected() MUST be evaluated first
                    await self.disconnected_cond.wait_for(
                        lambda: not self.is_connected() and self._should_be_connected()
                    )
                try:
                    logger.debug("Reconnect Daemon attempting to reconnect...")
                    logger.debug("FAKE RECONNECT")
                    raise exceptions.ConnectionFailedError
                    # # TODO: This changes Paho's internal state and breaks the code
                    # await self.connect()
                    # logger.debug("Reconnect Daemon reconnect attempt succeeded")
                except exceptions.ConnectionFailedError:
                    interval = self._reconnect_interval
                    logger.debug(
                        "Reconnect Daemon reconnect attempt failed. Trying again in {} seconds".format(
                            interval
                        )
                    )
                    await asyncio.sleep(interval)
        except asyncio.CancelledError:
            logger.debug("Reconnect Daemon was cancelled")
            raise

    def _should_be_connected(self):
        """Returns a boolean indicating whether we expect to be connected

        Note that while this value is only accurate as of the time it returns, it is generally
        safer to use than the below .is_connected(). It can't just change at any time, it can
        only be changed by invocations into Paho.
        """
        # Counter-intuitively, Paho's .is_connected() does not indicate the true connection state.
        # Rather, it returns whether Paho *thinks* it should be connected.
        # Fortunately, this is still pretty useful information for identifying unexpected
        # disconnects. We alias it here for more readable code.
        return self._mqtt_client.is_connected()

    def is_connected(self):
        """
        Returns a boolean indicating whether the MQTT client is currently connected.

        Note that this value is only accurate as of the time it returns. It could change at
        any point.
        """
        return self._connected

    def set_credentials(self, username, password=None):
        """
        Set a username and optionally a password for broker authentication.

        Must be called before .connect() to have any effect.

        :param str username: The username for broker authentication
        :param str password: The password for broker authentication (Optional)
        """
        self._mqtt_client.username_pw_set(username=username, password=password)

    async def connect(self):
        """
        Connect to the MQTT broker using details set at instantiation.

        :raises: ConnectionFailedError if there is a failure connecting
        """
        # Wait for permission to alter the connection
        async with self._connection_lock:
            # NOTE: It's not generally safe to use .is_connected() to determine what to do, since
            # the value could change at any time. However, it IS safe to do so here. The only way
            # to become connected is to invoke a Paho .connect() and wait for a success. Due to the
            # fact that this is the only method that can invoke Paho's .connect(), it does not
            # return until a response is received, and it is protected by the ConnectionLock,
            # we can be sure that there can't be overlapping invocations of Paho .connect().
            # Thus, we know that the state will not be changing on us within this block.
            if not self.is_connected():
                # Record the type of operation in progress
                self._connection_lock.connection_type = OP_TYPE_CONNECT

                # Start listening for connect before performing Paho connect to make sure
                # we don't miss it. This could possibly happen due to timing issues on the
                # Paho thread (i.e. CONNACK received after invoking connect, but before our
                # listening tasks have started)
                async def wait_for_success():
                    async with self.connected_cond:
                        await self.connected_cond.wait()

                async def wait_for_failure():
                    async with self._connect_failed_cond:
                        await self._connect_failed_cond.wait()

                success = asyncio.create_task(wait_for_success())
                failure = asyncio.create_task(wait_for_failure())

                # Start the reconnect daemon (if enabled and not already running)
                if self._auto_reconnect and not self._reconnect_daemon:
                    self._reconnect_daemon = asyncio.create_task(self._reconnect_loop())

                # Make sure the tasks are running
                await asyncio.sleep(0)

                # Paho Connect
                logger.debug("Attempting connect using port {}".format(self._port))
                try:
                    rc = await self._loop.run_in_executor(
                        None,
                        functools.partial(
                            self._mqtt_client.connect,
                            host=self._hostname,
                            port=self._port,
                            keepalive=self._keep_alive,
                        ),
                    )
                    message = mqtt.error_string(rc)
                    logger.debug("Connect returned rc {} - {}".format(rc, message))
                # TODO: more specialization of errors
                except Exception as e:
                    # Clean up listener tasks
                    success.cancel()
                    failure.cancel()
                    raise exceptions.ConnectionFailedError("Connect failed") from e

                if rc != mqtt.MQTT_ERR_SUCCESS:
                    # Clean up listener tasks
                    success.cancel()
                    failure.cancel()
                    raise exceptions.ConnectionFailedError(
                        "Connect returned rc {} - {}".format(rc, message)
                    )

                # Start Paho network loop. If already started, this will return a fail code,
                # but we don't really care - no harm, no foul.
                self._mqtt_client.loop_start()

                # Wait for connection to complete (success or fail)
                logger.debug("Waiting for connect response...")
                done, pending = await asyncio.wait(
                    [success, failure], return_when=asyncio.FIRST_COMPLETED
                )
                for t in pending:
                    t.cancel()

                # Sleep for 0.01 to briefly give up control of the event loop.
                # This is necessary because a connect failure can potentially trigger both
                # .on_connect() and .on_disconnect() and we want to allow them both to resolve
                # before clearing this value.
                # This isn't necessary for correct functionality, but it is necessary for
                # correct logging (.on_disconnect() wants access to the connection type stored
                # on the ConnectionLock)
                await asyncio.sleep(0.01)

                # Stop loop and raise exception if connect failed
                completed = done.pop()
                if completed is failure:
                    self._mqtt_client.loop_stop()
                    raise exceptions.ConnectionFailedError("Connect response failure")

            else:
                logger.debug("Already connected!")

    async def disconnect(self):
        """
        Disconnect from the MQTT broker
        """
        # Wait for permission to alter the connection
        async with self._connection_lock:
            loop = asyncio.get_running_loop()

            if self._should_be_connected():
                # Record the type of operation in progress
                self._connection_lock.connection_type = OP_TYPE_DISCONNECT

                # Start listening for disconnect before performing Paho disconnect to make sure
                # we don't miss it. This could happen due to timing issues on the Paho thread
                # (i.e. disconnect received after invoking disconnect, but before our listening
                # task has started) or due to an unexpected disconnect happening during
                # the execution of this block.
                async def wait_for_disconnect():
                    async with self.disconnected_cond:
                        await self.disconnected_cond.wait()

                disconnect_done = asyncio.create_task(wait_for_disconnect())

                # Make sure the task is running
                await asyncio.sleep(0)

                # Cancel reconnection attempts
                if self._reconnect_daemon:
                    self._reconnect_daemon.cancel()

                # Paho Disconnect
                # NOTE: Paho disconnect shouldn't raise any exceptions
                logger.debug("Attempting disconnect")
                rc = await loop.run_in_executor(None, self._mqtt_client.disconnect)
                message = mqtt.error_string(rc)
                logger.debug("Disconnect returned rc {} - {}".format(rc, message))

                if rc == mqtt.MQTT_ERR_SUCCESS:
                    # Wait for disconnection to complete
                    logger.debug("Waiting for disconnect response...")
                    await disconnect_done
                elif rc == mqtt.MQTT_ERR_NO_CONN:
                    # This happens when we disconnect while already disconnected.
                    # In this implementation, it should only happen if Paho's state indicates
                    # we would like to be connected, but we actually aren't.
                    # We still want to do this disconnect however, because doing so changes
                    # Paho's state to indicate we no longer wish to be connected.
                    logger.debug("Early disconnect return (Already disconnected)")
                    disconnect_done.cancel()
                else:
                    # This block should never execute
                    logger.error("Unexpected result from Paho disconnect. Doing nothing.")
                    disconnect_done.cancel()

                # Stop the network loop. If already stopped, this will return a fail code,
                # but we don't really care - no harm, no foul. Shouldn't even be able to
                # happen in the first place though.
                self._mqtt_client.loop_stop()

            else:
                logger.debug("Already disconnected!")