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

# TODO: implement these
RECONNECT_MODE_DROP = "RECONNECT_DROP"
RECONNECT_MODE_ALL = "RECONNECT_ALL"

# TODO: what about just number values that aren't mapped right?
# NOTE: Paho can return a lot of rc values. However, most of them shouldn't happen.
# Here are the ones that we can expect for each method.
expected_connect_rc = [mqtt.MQTT_ERR_SUCCESS]
expected_disconnect_rc = [mqtt.MQTT_ERR_SUCCESS, mqtt.MQTT_ERR_NO_CONN]
expected_subscribe_rc = [mqtt.MQTT_ERR_SUCCESS, mqtt.MQTT_ERR_NO_CONN]
expected_unsubscribe_rc = [mqtt.MQTT_ERR_SUCCESS, mqtt.MQTT_ERR_NO_CONN]
expected_publish_rc = [mqtt.MQTT_ERR_SUCCESS, mqtt.MQTT_ERR_NO_CONN, mqtt.MQTT_ERR_QUEUE_SIZE]

# Additionally, some are returned only via handler
expected_on_disconnect_rc = [
    mqtt.MQTT_ERR_SUCCESS,
    mqtt.MQTT_ERR_CONN_REFUSED,
    mqtt.MQTT_ERR_CONN_LOST,
    mqtt.MQTT_ERR_KEEPALIVE,
]
expected_on_connect_rc = [
    mqtt.CONNACK_ACCEPTED,
    mqtt.CONNACK_REFUSED_PROTOCOL_VERSION,
    mqtt.CONNACK_REFUSED_IDENTIFIER_REJECTED,
    mqtt.CONNACK_REFUSED_SERVER_UNAVAILABLE,
    mqtt.CONNACK_REFUSED_BAD_USERNAME_PASSWORD,
    mqtt.CONNACK_REFUSED_NOT_AUTHORIZED,
]


class MQTTError(Exception):
    """Represents a failure with a Paho-given error rc code"""

    def __init__(self, rc):
        self.rc = rc
        super().__init__(mqtt.error_string(rc))


class MQTTConnectionFailedError(Exception):
    """Represents a failure to connect.
    Can have a Paho-given connack rc code, or a message"""

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
    """Async Lock with additional attributes corresponding to the operation.
    These attributes are reset each time the Lock is released"""

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
    """
    Provides an async MQTT message broker interface

    This client currently only supports operations at a QoS (Quality of Service) of 1
    """

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

        # Event Loop
        self._loop = asyncio.get_running_loop()

        # State
        # NOTE: These values do not need to be protected by locks since the code paths that
        # modify them cannot be invoked in parallel.
        self._connected = False
        self._desire_connection = False

        # Synchronization
        self.connected_cond = asyncio.Condition()
        self.disconnected_cond = asyncio.Condition()
        self._connection_lock = ConnectionLock()
        self._mid_tracker_lock = asyncio.Lock()

        # Tasks/Futures
        self._reconnect_daemon = None
        self._pending_subs = {}  # Map mid -> Future
        self._pending_unsubs = {}  # Map mid -> Future
        self._pending_pubs = {}  # Map mid -> Future

        # Incoming Data
        self.incoming_messages = asyncio.Queue()
        self.incoming_filtered_messages = {}  # Map name -> asyncio.Queue

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
            rc_msg = mqtt.error_string(rc)

            # To Do List
            do_set_disconnect = False
            do_stop_network_loop = False
            do_cancel_pending = False

            # NOTE: It's not generally safe to use .is_connected() to determine what to do, since
            # the value could change at any time. However, it IS safe to do so here.
            # This handler, as well as .on_connect() above, are the only two functions that can
            # change the value. They are both invoked on Paho's network loop, which is
            # single-threaded. This means there cannot be overlapping invocations that would
            # change the value, and thus that the value will not change during execution of this
            # block.
            if this.is_connected():
                if this._desire_connection:
                    logger.debug("Unexpected Disconnect: rc {} - {}".format(rc, rc_msg))
                    do_set_disconnect = True
                    do_stop_network_loop = True
                    do_cancel_pending = True
                else:
                    logger.debug("Disconnect Response: rc {} - {}".format(rc, rc_msg))
                    do_set_disconnect = True
                    do_cancel_pending = True
            else:
                if this._connection_lock.connection_type == OP_TYPE_CONNECT:
                    # TODO: can this be simplified to just use rc now that we know this always happens?
                    # When Paho receives a failure response to a connect, the disconnect
                    # handler is also called.
                    # But we don't wish to issue spurious notifications or other behaviors
                    logger.debug(
                        "Connect Failure Disconnect Response: rc {} - {}".format(rc, rc_msg)
                    )
                else:
                    # Double disconnect. Suppress.
                    # Sometimes Paho disconnects twice. Why? Who knows.
                    # But we don't wish to issue spurious notifications or other behaviors
                    logger.debug("Double Disconnect Response: rc {} - {}".format(rc, rc_msg))

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

            if do_cancel_pending:
                # Cancel pending subscribes and unsubscribes only.
                # Publishes can survive a disconnect.
                async def cancel_pending():
                    if len(this._pending_subs) != 0 or len(this._pending_unsubs) != 0:
                        async with this._mid_tracker_lock:
                            logger.debug("Cancelling pending subscribes")
                            mids = this._pending_subs.keys()
                            for mid in mids:
                                this._pending_subs[mid].cancel()
                            this._pending_subs.clear()
                            logger.debug("Cancelling pending unsubscribes")
                            mids = this._pending_unsubs.keys()
                            for mid in mids:
                                this._pending_unsubs[mid].cancel()
                            this._pending_unsubs.clear()

                # NOTE: This coroutine might not be able to finish right away due to the
                # mid_tracker_lock. Don't wait on it's completion or it may lock up.
                asyncio.run_coroutine_threadsafe(cancel_pending(), this._loop)

            if do_stop_network_loop:

                async def stop_network_loop():
                    logger.debug("Stopping Paho network loop due to unexpected disconnect")
                    client.loop_stop()

                # NOTE: This coroutine can't finish execution until after this handler exits
                # since this handler itself is running on the network loop.
                # This means this MUST be the last task that gets scheduled in this handler,
                # since .loop_stop() will block until this handler finishes running.
                asyncio.run_coroutine_threadsafe(stop_network_loop(), this._loop)

        def on_subscribe(client, userdata, mid, granted_qos):
            this = self_weakref()
            logger.debug("SUBACK received for mid {}".format(mid))

            async def complete_sub():
                async with this._mid_tracker_lock:
                    try:
                        f = this._pending_subs[mid]
                        f.set_result(True)
                    except KeyError:
                        logger.warning("Unexpected SUBACK received for mid {}".format(mid))

            asyncio.run_coroutine_threadsafe(complete_sub(), this._loop)

        def on_unsubscribe(client, userdata, mid):
            this = self_weakref()
            logger.debug("UNSUBACK received for mid {}".format(mid))

            async def complete_unsub():
                async with this._mid_tracker_lock:
                    try:
                        f = this._pending_unsubs[mid]
                        f.set_result(True)
                    except KeyError:
                        logger.warning("Unexpected UNSUBACK received for mid {}".format(mid))

            asyncio.run_coroutine_threadsafe(complete_unsub(), this._loop)

        def on_publish(client, userdata, mid):
            this = self_weakref()
            logger.debug("PUBACK received for mid {}".format(mid))

            async def complete_pub():
                async with this._mid_tracker_lock:
                    try:
                        f = this._pending_pubs[mid]
                        f.set_result(True)
                    except KeyError:
                        logger.warning("Unexpected PUBACK received for mid {}".format(mid))

            asyncio.run_coroutine_threadsafe(complete_pub(), this._loop)

        def on_message(client, userdata, message):
            this = self_weakref()
            logger.debug("Incoming MQTT Message received on {}".format(message.topic))

            async def add_to_queue():
                await this.incoming_messages.put(message)

            asyncio.run_coroutine_threadsafe(add_to_queue(), this._loop)

        mqtt_client.on_connect = on_connect
        mqtt_client.on_disconnect = on_disconnect
        mqtt_client.on_subscribe = on_subscribe
        mqtt_client.on_unsubscribe = on_unsubscribe
        mqtt_client.on_publish = on_publish
        mqtt_client.on_message = on_message

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

        :raises: MQTTConnectionFailedError if there is a failure connecting
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
                logger.debug("Attempting connect using port {}...".format(self._port))
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
                    rc_msg = mqtt.error_string(rc)
                    logger.debug("Connect returned rc {} - {}".format(rc, rc_msg))
                # TODO: more specialization of errors to indicate which are/aren't retryable
                except Exception as e:
                    raise MQTTConnectionFailedError(message="Failure in Paho .connect()") from e

                if rc != mqtt.MQTT_ERR_SUCCESS:
                    # NOTE: This block should probably never execute. Paho's .connect() is
                    # supposed to only return success or raise an exception.
                    logger.warning("Unexpected rc {} from Paho .connect()".format(rc))
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
                        "Paho network loop was already (unexpectedly) running. Stopping, then starting."
                    )
                    self._mqtt_client.loop_stop()
                    self._mqtt_client.loop_start()

                # The result of the CONNACK is received via this future stored on the lock
                logger.debug("Waiting for connect response...")
                rc = await self._connection_lock.future
                # Sleep for 0.01 to briefly give up control of the event loop.
                # This is necessary because a connect failure can potentially trigger both
                # .on_connect() and .on_disconnect() and we want to allow them both to resolve
                # before releasing the ConnectionLock.
                # TODO: now that we know it always does, make this more efficient
                await asyncio.sleep(0.01)
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
                rc = await self._loop.run_in_executor(None, self._mqtt_client.disconnect)
                rc_msg = mqtt.error_string(rc)
                logger.debug("Disconnect returned rc {} - {}".format(rc, rc_msg))

                if rc == mqtt.MQTT_ERR_SUCCESS:
                    # Wait for disconnection to complete
                    logger.debug("Waiting for disconnect response...")
                    await disconnect_done
                    logger.debug("Stopping Paho network loop")
                    self._mqtt_client.loop_stop()
                    # Wait slightly for tasks started by the on_disconnect handler to finish.
                    # This will prevent warnings.
                    # TODO: can we remove this? Wait on a queue of tasks or something?
                    await asyncio.sleep(0.01)
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
                    logger.warning(
                        "Unexpected rc {} from Paho .disconnect(). Doing nothing.".format(rc)
                    )
                    disconnect_done.cancel()

            else:
                logger.debug("Already disconnected!")

    async def subscribe(self, topic):
        """
        Subscribe to a topic from the MQTT broker.

        :param str topic: a single string specifying the subscription topic to subscribe to

        :raises: ValueError if topic is None or has zero string length.
        :raises: MQTTError if there is an error subscribing
        """
        try:
            mid = None
            logger.debug("Attempting subscribe")
            # Using this lock allows us to be sure that the ACK won't come in before the
            # Future can be added to the pending dictionary
            async with self._mid_tracker_lock:
                (rc, mid) = await self._loop.run_in_executor(
                    None, functools.partial(self._mqtt_client.subscribe, topic=topic, qos=1)
                )
                rc_msg = mqtt.error_string(rc)
                logger.debug("Subscribe returned rc {} - {}".format(rc, rc_msg))
                if rc != mqtt.MQTT_ERR_SUCCESS:
                    if rc not in expected_subscribe_rc:
                        logger.warning("Unexpected rc {} from Paho .subscribe()".format(rc))
                    raise MQTTError(rc)

                # Establish a pending subscribe
                sub_done = self._loop.create_future()
                self._pending_subs[mid] = sub_done

            logger.debug("Waiting for subscribe response for mid {}".format(mid))
            await sub_done
        except asyncio.CancelledError:
            if mid:
                logger.debug("Subscribe for mid {} was cancelled".format(mid))
            else:
                logger.debug("Subscribe was cancelled before mid was assigned")
            raise
        finally:
            # Delete any pending operation (if it exists)
            async with self._mid_tracker_lock:
                if mid and mid in self._pending_subs:
                    del self._pending_subs[mid]

    async def unsubscribe(self, topic):
        """
        Unsubscribe from a topic on the MQTT broker.

        :param str topic: a single string which is the subscription topic to unsubscribe from.

        :raises: ValueError if topic is None or has zero string length.
        :raises: MQTTError if there is an error subscribing
        """
        try:
            mid = None
            logger.debug("Attempting unsubscribe")
            # Using this lock allows us to be sure that the ACK won't come in before the
            # Future can be added to the pending dictionary
            async with self._mid_tracker_lock:
                (rc, mid) = await self._loop.run_in_executor(
                    None, functools.partial(self._mqtt_client.unsubscribe, topic=topic)
                )
                rc_msg = mqtt.error_string(rc)
                logger.debug("Unsubscribe returned rc {} - {}".format(rc, rc_msg))
                if rc != mqtt.MQTT_ERR_SUCCESS:
                    if rc not in expected_unsubscribe_rc:
                        logger.warning("Unexpected rc {} from Paho .unsubscribe()".format(rc))
                    raise MQTTError(rc)

                # Establish a pending unsubscribe
                unsub_done = self._loop.create_future()
                self._pending_unsubs[mid] = unsub_done

            logger.debug("Waiting for unsubscribe response for mid {}".format(mid))
            await unsub_done
        except asyncio.CancelledError:
            if mid:
                logger.debug("Unsubscribe for mid {} was cancelled".format(mid))
            else:
                logger.debug("Unsubscribe was cancelled before mid was assigned")
            raise
        finally:
            # Delete any pending operation (if it exists)
            async with self._mid_tracker_lock:
                if mid and mid in self._pending_unsubs:
                    del self._pending_unsubs[mid]

    async def publish(self, topic, payload):
        """
        Send a message via the MQTT broker.

        :param str topic: topic: The topic that the message should be published on.
        :param payload: The actual message to send.
        :type payload: str, bytes, int, float or None
        :param int qos: the desired quality of service level for the subscription. Defaults to 1.
        :param callback: A callback to be triggered upon completion (Optional).

        :raises: ValueError if topic is None or has zero string length
        :raises: ValueError if topic contains a wildcard ("+")
        :raises: ValueError if the length of the payload is greater than 268435455 bytes
        :raises: TypeError if payload is not a valid type
        :raises: MQTTError if there is an error publishing
        """
        try:
            mid = None
            logger.debug("Attempting publish")
            # Using this lock allows us to be sure that the ACK won't come in before the
            # Future can be added to the pending dictionary
            async with self._mid_tracker_lock:
                message_info = await self._loop.run_in_executor(
                    None,
                    functools.partial(
                        self._mqtt_client.publish, topic=topic, payload=payload, qos=1
                    ),
                )
                mid = message_info.mid
                rc_msg = mqtt.error_string(message_info.rc)
                logger.debug("Publish returned rc {} - {}".format(message_info.rc, rc_msg))
                if message_info.rc == mqtt.MQTT_ERR_NO_CONN:
                    logger.debug("MQTT Client not connected - will publish upon next connect")
                elif message_info.rc != mqtt.MQTT_ERR_SUCCESS:
                    if message_info.rc not in expected_publish_rc:
                        logger.warning(
                            "Unexpected rc {} from Paho .publish()".format(message_info.rc)
                        )
                    raise MQTTError(message_info.rc)

                # Establish a pending publish
                pub_done = self._loop.create_future()
                self._pending_pubs[mid] = pub_done

            logger.debug("Waiting for publish response")
            # NOTE: Yes, message_info has a method called 'wait_for_publish' which would simplify
            # things, however it has strange behavior in the case of disconnection - it raises a
            # RuntimeError. However, the publish actually persists and still will be sent upon a
            # connection, even though the message_info will NEVER be able to be used to track it
            # (even after connection established).
            # So, alas, we do it the messy handler/Future way, same as with sub and unsub.
            await pub_done
        except asyncio.CancelledError:
            if mid:
                logger.debug("Publish for mid {} was cancelled".format(mid))
                logger.warning("The cancelled publish may still be delivered if it was in-flight")
            else:
                logger.debug("Publish was cancelled before mid was assigned")
            raise
        finally:
            # Delete any pending operation (if it exists)
            async with self._mid_tracker_lock:
                if mid and mid in self._pending_pubs:
                    del self._pending_pubs[mid]
