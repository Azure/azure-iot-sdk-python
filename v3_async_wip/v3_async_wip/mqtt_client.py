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

        # Info
        self._connected = False  # TODO: do we need a lock for this?

        # Synchronization
        self.connected_cond = asyncio.Condition()
        self.disconnected_cond = asyncio.Condition()
        self._connect_failed_cond = asyncio.Condition()
        self._connection_lock = ConnectionLock()

        # Tasks
        # self._reconnect_daemon = None

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
                async def notify_connected():
                    logger.debug("Client State: CONNECTED")
                    this._connected = True
                    async with this.connected_cond:
                        this.connected_cond.notify_all()

                asyncio.run_coroutine_threadsafe(notify_connected(), this._loop)

                # # Start the reconnect daemon (if enabled)
                # if this._auto_reconnect and not this._reconnect_daemon:
                #     logger.debug("Starting Reconnect Daemon")
                #     asyncio.run_coroutine_threadsafe(this._start_reconnect_daemon(), this._loop)
            else:

                # Notify tasks waiting on failed connection
                async def notify_connection_fail():
                    async with this._connect_failed_cond:
                        this._connect_failed_cond.notify_all()

                asyncio.run_coroutine_threadsafe(notify_connection_fail(), this._loop)

        def on_disconnect(client, userdata, rc):
            this = self_weakref()
            message = mqtt.error_string(rc)

            if this.is_connected():
                if this._should_be_connected():
                    logger.debug("Unexpected Disconnect: rc {} - {}".format(rc, message))
                else:
                    logger.debug("Disconnect Response: rc {} - {}".format(rc, message))
                    # if this._reconnect_daemon:
                    #     asyncio.run_coroutine_threadsafe(this._cancel_reconnect_daemon(), this._loop)

                # Stop the network loop. Call this back on the event loop, since calling it from
                # within the network loop thread will not properly stop the thread.
                async def stop_network_loop():
                    client.loop_stop()

                asyncio.run_coroutine_threadsafe(stop_network_loop(), this._loop)

                # Notify tasks waiting on disconnect
                async def notify_disconnected():
                    logger.debug("Client State: DISCONNECTED")
                    this._connected = False
                    async with this.disconnected_cond:
                        this.disconnected_cond.notify_all()

                asyncio.run_coroutine_threadsafe(notify_disconnected(), this._loop)

            else:
                if this._connection_lock.connection_type == OP_TYPE_CONNECT:
                    # Sometimes when Paho receives a failure response to a connect, the disconnect
                    # handler is also called. Why? Who knows.
                    # But we don't wish to issue spurious notifications or network loop stoppage.
                    # TODO: OR DO WE WANT NETWORK LOOP STOPPAGE????
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

    # async def _start_reconnect_daemon(self):
    #     # Use weak references to ensure there are no memory leaks
    #     self_weakref = weakref.ref(self)

    #     async def _reconnect_daemon():
    #         this = self_weakref()
    #         try:
    #             while True:
    #                 logger.debug("Reconnect Daemon waiting for unexpected disconnect...")
    #                 # Wait for disconnect notification
    #                 async with this.disconnected_cond:
    #                     await this.disconnected_cond.wait_for(this._should_be_connected)

    #                 logger.debug("Reconnect Daemon awoke due to unexpected disconnect!")
    #                 # Try to reconnect until connection is restored, or until
    #                 # the connection is no longer desired.
    #                 while not this.is_connected() and this._should_be_connected():
    #                     logger.debug("Reconnect Daemon attempting to reconnect...")
    #                     try:
    #                         await this.connect()
    #                         logger.debug("Reconnect Daemon reconnect attempt succeeded")
    #                     except exceptions.ConnectionFailedError:
    #                         # Try again after the interval
    #                         interval = this._reconnect_interval
    #                         logger.debug("Reconnect Daemon reconnect attempt failed. Trying again in {} seconds".format(interval))
    #                         await asyncio.sleep(interval)

    #                 logger.debug("Reconnect Daemon done reconnecting. Connected: {}, Should Be Connected: {}".format(
    #                     this.is_connected(), this._should_be_connected()
    #                 ))
    #         except asyncio.CancelledError:
    #             logger.debug("Reconnect Daemon was cancelled")
    #             raise

    #     self._reconnect_daemon = asyncio.create_task(self._reconnect_daemon())

    # async def _cancel_reconnect_daemon(self):
    #     logger.debug("Cancelling Reconnect Daemon...")
    #     self._reconnect_daemon.cancel()
    #     try:
    #         await self._reconnect_daemon
    #     except asyncio.CancelledError:
    #         pass
    #     self._reconnect_daemon = None

    def _should_be_connected(self):
        """Returns a boolean indicating whether we expect to be connected"""
        # Counter-intuitively, Paho's .is_connected() does not indicate the true connection state.
        # Rather, it returns whether or not Paho thinks it should be connected.
        # Fortunately, this is still pretty useful information for identifying
        # unexpected disconnects. We alias it here to be more readable.
        return self._mqtt_client.is_connected()

    def is_connected(self):
        """
        Returns a boolean indicating whether the MQTT client is currently connected.
        """
        return self._connected

    def set_credentials(self, username, password=None):
        """
        Set a username and optionally a password for broker authentication.

        Must be called before connect() to have any effect.

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
            if not self.is_connected():
                # Record the type of operation in progress
                self._connection_lock.connection_type = OP_TYPE_CONNECT

                # Start listening for connect before performing Paho connect to make sure
                # we don't miss it. This could possibly happen due to timing issues on the
                # Paho thread (i.e. CONNACK received after invoking connect, but before our
                # listening tasks have started)
                # TODO: Is there a risk of Paho connecting between the connection check and the tasks starting?
                async def wait_for_success():
                    async with self.connected_cond:
                        await self.connected_cond.wait()

                async def wait_for_failure():
                    async with self._connect_failed_cond:
                        await self._connect_failed_cond.wait()

                success = asyncio.create_task(wait_for_success())
                failure = asyncio.create_task(wait_for_failure())

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

                if rc != 0:
                    # Clean up listener tasks
                    success.cancel()
                    failure.cancel()
                    raise exceptions.ConnectionFailedError(
                        "Connect returned rc {} - {}".format(rc, message)
                    )

                # Start Paho network loop
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

                # Raise exception if connect failed
                completed = done.pop()
                if completed is failure:
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

            if self.is_connected():
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

                # Paho Disconnect
                # NOTE: Paho disconnect shouldn't raise any exceptions
                logger.debug("Attempting disconnect")
                rc = await loop.run_in_executor(None, self._mqtt_client.disconnect)
                message = mqtt.error_string(rc)
                logger.debug("Disconnect returned rc {} - {}".format(rc, message))

                if rc == 0:
                    # Wait for disconnection to complete
                    logger.debug("Waiting for disconnect response...")
                    await disconnect_done
                else:
                    # If disconnect returns an error it means we're already disconnected.
                    # So... we got where wanted to... that's a success.
                    # No waiting required.
                    logger.debug("Client State: DISCONNECTED")
                    self._connected = False

                # NOTE: Paho's network loop will be stopped in the on_disconnect handler.
                # This is because we want to stop it whether the disconnect is expected or not.

            else:
                logger.debug("Already disconnected!")
