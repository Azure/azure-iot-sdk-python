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


logger = logging.getLogger(__name__)

OP_TYPE_CONNECT = "CONNECT"
OP_TYPE_DISCONNECT = "DISCONNECT"

RECONNECT_MODE_DROP = "RECONNECT_DROP"
RECONNECT_MODE_ALL = "RECONNECT_ALL"


class MQTTError(Exception):
    """Represents a failure with a Paho-given error rc code"""

    def __init__(self, rc):
        self.rc = rc
        super().__init__(mqtt.error_string(rc))


class MQTTConnectionFailedError(Exception):
    """Represents a failure to a connect"""

    def __init__(self, rc=None, message=None, fatal=False):
        if not rc and not message:
            raise ValueError("must provide rc or message")
        if rc and message:
            raise ValueError("rc and message are mutually exclusive")
        self.rc = rc
        self.fatal = fatal
        if rc:
            message = mqtt.connack_string(rc)
        super().__init__(message)


class ConnectionLock(asyncio.Lock):
    """Async Lock with additional attributes regarding the operation."""

    def __init__(self, *args, **kwargs):
        # Type of connection operation (i.e. OP_TYPE_CONNECT, OP_TYPE_DISCONNECT)
        self.connection_type = None
        # Future for connection operation completion.
        # Currently this is only used for OP_TYPE_CONNECT
        self.future = None
        super().__init__(*args, **kwargs)

    async def acquire(self):
        rv = await super().acquire()
        loop = asyncio.get_running_loop()
        self.future = loop.create_future()
        return rv

    def release(self):
        self.connection_type = None
        self.future = None
        return super().release()


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
        reconnect_interval=10,
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
        :param int reconnect_interval: Number of seconds between reconnect attempts
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
        self._reconnect_interval = reconnect_interval

        # Client
        self._mqtt_client = self._create_mqtt_client(
            client_id, transport, ssl_context, proxy_options, websockets_path
        )

        # State
        # NOTE: These values do not need to be protected by locks since the code paths that
        # modify them cannot be invoked in parallel.
        self._connected = False
        self._desire_connection = False

        # Synchronization
        self.connected_cond = asyncio.Condition()
        self.disconnected_cond = asyncio.Condition()
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

            # Change state, report result, and notify connection established
            async def set_result():
                if rc == mqtt.CONNACK_ACCEPTED:
                    logger.debug("Client State: CONNECTED")
                    this._connected = True
                    this._desire_connection = True
                    async with this.connected_cond:
                        this.connected_cond.notify_all()
                this._connection_lock.future.set_result(rc)

            f = asyncio.run_coroutine_threadsafe(set_result(), this._loop)
            # Need to wait for this one to finish since we don't want to let another
            # Paho handler invoke until we know the connection state has been set.
            f.result()

        def on_disconnect(client, userdata, rc):
            this = self_weakref()
            message = mqtt.error_string(rc)

            # To Do List
            do_set_disconnect = False
            do_stop_network_loop = False

            # NOTE: It's not generally safe to use .is_connected() to determine what to do, since
            # the value could change at any time. However, it IS safe to do so here.
            # This handler, as well as .on_connect() above, are the only two functions that can
            # change the value. They are both invoked on Paho's network loop, which is
            # single-threaded. This means there cannot be overlapping invocations that would
            # change the value, and thus that the value will not change during execution of this
            # block.
            if this.is_connected():
                if this._desire_connection:
                    logger.debug("Unexpected Disconnect: rc {} - {}".format(rc, message))
                    do_set_disconnect = True
                    do_stop_network_loop = True
                else:
                    logger.debug("Disconnect Response: rc {} - {}".format(rc, message))
                    do_set_disconnect = True
            else:
                if this._connection_lock.connection_type == OP_TYPE_CONNECT:
                    # Sometimes when Paho receives a failure response to a connect, the disconnect
                    # handler is also called. Why? Who knows.
                    # But we don't wish to issue spurious notifications or event loop stoppages.
                    logger.debug(
                        "Connect Failure Disconnect Response: rc {} - {}".format(rc, message)
                    )
                else:
                    # Double disconnect. Suppress.
                    # Sometimes Paho disconnects twice. Why? Who knows.
                    # But we don't wish to issue spurious notifications or event loop stoppages.
                    logger.debug("Double Disconnect Response: rc {} - {}".format(rc, message))

            if do_set_disconnect:
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

            if do_stop_network_loop:

                async def stop_network_loop():
                    logger.debug("Stopping Paho network loop due to unexpected disconnect")
                    client.loop_stop()

                # NOTE: This coroutine can't finish execution until after this handler exits
                # since this handler itself is running on the network loop.
                # This means this MUST be the last task that gets scheduled in this handler,
                # since .loop_stop() will block until this handler finishes running.
                asyncio.run_coroutine_threadsafe(stop_network_loop(), this._loop)

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
                    await self.disconnected_cond.wait_for(
                        lambda: not self.is_connected() and self._desire_connection
                    )
                try:
                    logger.debug("Reconnect Daemon attempting to reconnect...")
                    await self.connect()
                    logger.debug("Reconnect Daemon reconnect attempt succeeded")
                except MQTTConnectionFailedError as e:
                    if not e.fatal:
                        interval = self._reconnect_interval
                        logger.debug(
                            "Reconnect Daemon reconnect attempt failed. Trying again in {} seconds".format(
                                interval
                            )
                        )
                        await asyncio.sleep(interval)
                    else:
                        logger.error("Reconnect failure was fatal - cannot reconnect")
                        logger.error(str(e))
                        break
        except asyncio.CancelledError:
            logger.debug("Reconnect Daemon was cancelled")
            raise

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

                # Start the reconnect daemon (if enabled and not already running)
                if self._auto_reconnect and not self._reconnect_daemon:
                    self._reconnect_daemon = asyncio.create_task(self._reconnect_loop())

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
                    raise MQTTConnectionFailedError(message="Failure in Paho .connect()") from e

                if rc != mqtt.MQTT_ERR_SUCCESS:
                    # NOTE: This block should probably never execute. Paho's .connect() is
                    # supposed to only return success or raise an exception.
                    logger.warning("Unexpected rc from Paho .connect()")
                    # MQTTConnectionFailedError expects a connack rc, but this is a regular rc.
                    # So chain a regular mqtt exception into a connection mqtt exception.
                    try:
                        raise MQTTError(rc=rc)
                    except MQTTError as e:
                        raise MQTTConnectionFailedError(
                            message="Unexpected Paho .connect() rc"
                        ) from e

                # Start Paho network loop.
                logger.debug("Starting Paho network loop")
                rc = self._mqtt_client.loop_start()
                if rc == mqtt.MQTT_ERR_INVAL:
                    # This happens if the network loop thread already exists.
                    # Stop the existing one, and start a new one.
                    # This (probably) shouldn't happen.
                    # TODO: Investigate if this is truly necessary once stress testing is set up
                    logger.warning(
                        "Paho network loop was already running. Stopping, then starting."
                    )
                    self._mqtt_client.loop_stop()
                    self._mqtt_client.loop_start()

                # Sleep for 0.01 to briefly give up control of the event loop.
                # This is necessary because a connect failure can potentially trigger both
                # .on_connect() and .on_disconnect() and we want to allow them both to resolve
                # before clearing this value.
                await asyncio.sleep(0.01)

                # The result of the CONNACK is received via this future stored on the lock
                rc = await self._connection_lock.future
                if rc != mqtt.CONNACK_ACCEPTED:
                    logger.debug("Stopping Paho network loop due to connect failure")
                    self._mqtt_client.loop_stop()
                    raise MQTTConnectionFailedError(rc=rc)

            else:
                logger.debug("Already connected!")

    async def disconnect(self):
        """
        Disconnect from the MQTT broker.

        Ensure this is called for graceful exit.
        """
        # Wait for permission to alter the connection
        async with self._connection_lock:
            loop = asyncio.get_running_loop()

            if self._desire_connection:
                # Record the type of operation in progress
                self._connection_lock.connection_type = OP_TYPE_DISCONNECT

                # We no longer wish to be connected
                self._desire_connection = False

                # Start listening for disconnect before performing Paho disconnect to make sure
                # we don't miss it. This could happen due to timing issues on the Paho thread
                # (i.e. disconnect received after invoking disconnect, but before our listening
                # task has started) or due to an unexpected disconnect happening during
                # the execution of this block.
                async def wait_for_disconnect():
                    async with self.disconnected_cond:
                        await self.disconnected_cond.wait()

                # We use a listener task here rather than waiting for the ConnectionLock's Future
                # since we don't actually care about the response rc, we just need to wait for
                # the state change.
                disconnect_done = asyncio.create_task(wait_for_disconnect())

                # Make sure the task is running
                await asyncio.sleep(0)

                # Cancel reconnection attempts
                if self._reconnect_daemon:
                    self._reconnect_daemon.cancel()
                    self._reconnect_daemon = None

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
                    logger.debug("Stopping Paho network loop")
                    self._mqtt_client.loop_stop()
                elif rc == mqtt.MQTT_ERR_NO_CONN:
                    # This happens when we disconnect while already disconnected.
                    # In this implementation, it should only happen if Paho's inner state
                    # indicates we would like to be connected, but we actually aren't.
                    # We still want to do this disconnect however, because doing so changes
                    # Paho's state to indicate we no longer wish to be connected.
                    logger.debug("Early disconnect return (Already disconnected)")
                    disconnect_done.cancel()
                else:
                    # This block should never execute
                    logger.error("Unexpected result from Paho disconnect. Doing nothing.")
                    disconnect_done.cancel()

            else:
                logger.debug("Already disconnected!")
