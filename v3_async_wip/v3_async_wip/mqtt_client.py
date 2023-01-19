# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import asyncio
import functools
import logging
import paho.mqtt.client as mqtt  # type: ignore
import ssl
from typing import Any, Dict, AsyncGenerator, Optional, Union
from azure.iot.device.common import ProxyOptions  # type:ignore


logger = logging.getLogger(__name__)


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


class MQTTClient:
    """
    Provides an async MQTT message broker interface

    This client currently only supports operations at a QoS (Quality of Service) of 1
    """

    def __init__(
        self,
        client_id: str,
        hostname: str,
        port: int,
        transport: str = "tcp",
        keep_alive: int = 60,
        auto_reconnect: bool = False,
        reconnect_interval: int = 10,
        ssl_context: Optional[ssl.SSLContext] = None,
        websockets_path: Optional[str] = None,
        proxy_options: Optional[ProxyOptions] = None,
    ) -> None:
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
        :type proxy_options: :class:`azure.iot.device.common.ProxyOptions`
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
        self._event_loop = asyncio.get_running_loop()

        # State
        # NOTE: These values do not need to be protected by locks since the code paths that
        # modify them cannot be invoked in parallel.
        self._connected = False
        self._desire_connection = False

        # Synchronization
        self.connected_cond = asyncio.Condition()
        self.disconnected_cond = asyncio.Condition()
        self._connection_lock = asyncio.Lock()
        self._mid_tracker_lock = asyncio.Lock()

        # Tasks/Futures
        self._network_loop: Optional[asyncio.Future] = None
        self._reconnect_daemon: Optional[asyncio.Task] = None
        # NOTE: pending connect is protected by the connection lock
        # Other pending ops are protected by the _mid_tracker_lock
        self._pending_connect: Optional[asyncio.Future] = None
        self._pending_subs: Dict[int, asyncio.Future] = {}
        self._pending_unsubs: Dict[int, asyncio.Future] = {}
        self._pending_pubs: Dict[int, asyncio.Future] = {}

        # Incoming Data
        self._incoming_messages: asyncio.Queue[mqtt.MQTTMessage] = asyncio.Queue()
        self._incoming_filtered_messages: Dict[str, asyncio.Queue[mqtt.MQTTMessage]] = {}

    def _create_mqtt_client(
        self,
        client_id: str,
        transport: str,
        ssl_context: Optional[ssl.SSLContext],
        proxy_options: Optional[ProxyOptions],
        websockets_path: Optional[str],
    ) -> mqtt.Client:
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

        def on_connect(client: mqtt.Client, userdata: Any, flags: Dict[str, int], rc: int) -> None:
            message = mqtt.connack_string(rc)
            logger.debug("Connect Response: rc {} - {}".format(rc, message))
            if rc not in expected_on_connect_rc:
                logger.warning("Connect Response rc {} was unexpected".format(rc))

            # Change state, report result, and notify connection established
            async def set_result() -> None:
                if rc == mqtt.CONNACK_ACCEPTED:
                    logger.debug("Client State: CONNECTED")
                    self._connected = True
                    self._desire_connection = True
                    async with self.connected_cond:
                        self.connected_cond.notify_all()
                if self._pending_connect:
                    self._pending_connect.set_result(rc)
                else:
                    logger.warning(
                        "Connect response received without outstanding attempt (likely was cancelled)"
                    )

            f = asyncio.run_coroutine_threadsafe(set_result(), self._event_loop)
            # Need to wait for this one to finish since we don't want to let another
            # Paho handler invoke until we know the connection state has been set.
            f.result()

        def on_disconnect(client: mqtt.Client, userdata: Any, rc: int) -> None:
            rc_msg = mqtt.error_string(rc)

            # NOTE: It's not generally safe to use .is_connected() to determine what to do, since
            # the value could change at any time. However, it IS safe to do so here.
            # This handler, as well as .on_connect() above, are the only two functions that can
            # change the value. They are both invoked on Paho's network loop, which is
            # single-threaded. This means there cannot be overlapping invocations that would
            # change the value, and thus that the value will not change during execution of this
            # block.
            if not self.is_connected():
                if rc == mqtt.MQTT_ERR_CONN_REFUSED:
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
            else:
                if rc == mqtt.MQTT_ERR_SUCCESS:
                    logger.debug("Disconnect Response: rc {} - {}".format(rc, rc_msg))
                else:
                    logger.debug("Unexpected Disconnect: rc {} - {}".format(rc, rc_msg))

                # Change state and notify tasks waiting on disconnect
                async def set_disconnected() -> None:
                    logger.debug("Client State: DISCONNECTED")
                    self._connected = False
                    async with self.disconnected_cond:
                        self.disconnected_cond.notify_all()

                f = asyncio.run_coroutine_threadsafe(set_disconnected(), self._event_loop)
                # Need to wait for this one to finish since we don't want to let another
                # Paho handler invoke until we know the connection state has been set.
                f.result()

                # Cancel pending subscribes and unsubscribes only.
                # Publishes can survive a disconnect.
                async def cancel_pending() -> None:
                    if len(self._pending_subs) != 0 or len(self._pending_unsubs) != 0:
                        async with self._mid_tracker_lock:
                            logger.debug("Cancelling pending subscribes")
                            mids = self._pending_subs.keys()
                            for mid in mids:
                                self._pending_subs[mid].cancel()
                            self._pending_subs.clear()
                            logger.debug("Cancelling pending unsubscribes")
                            mids = self._pending_unsubs.keys()
                            for mid in mids:
                                self._pending_unsubs[mid].cancel()
                            self._pending_unsubs.clear()

                # NOTE: This coroutine might not be able to finish right away due to the
                # mid_tracker_lock. Don't wait on it's completion or it may deadlock.
                asyncio.run_coroutine_threadsafe(cancel_pending(), self._event_loop)

        def on_subscribe(client: mqtt.Client, userdata: Any, mid: int, granted_qos: int) -> None:
            logger.debug("SUBACK received for mid {}".format(mid))

            async def complete_sub() -> None:
                async with self._mid_tracker_lock:
                    try:
                        f = self._pending_subs[mid]
                        f.set_result(True)
                    except KeyError:
                        logger.warning("Unexpected SUBACK received for mid {}".format(mid))

            # NOTE: The complete_sub() coroutine cannot finish right away due to the
            # mid_tracker_lock being held by the invocation of .subscribe(), waiting for a result.
            # Do not wait on the completion of complete_sub() or this callback will deadlock the
            # Paho network loop. Just schedule the eventual completion, and keep it moving.
            asyncio.run_coroutine_threadsafe(complete_sub(), self._event_loop)

        def on_unsubscribe(client: mqtt.Client, userdata: Any, mid: int) -> None:
            logger.debug("UNSUBACK received for mid {}".format(mid))

            async def complete_unsub() -> None:
                async with self._mid_tracker_lock:
                    try:
                        f = self._pending_unsubs[mid]
                        f.set_result(True)
                    except KeyError:
                        logger.warning("Unexpected UNSUBACK received for mid {}".format(mid))

            # NOTE: The complete_unsub() coroutine cannot finish right away due to the
            # mid_tracker_lock being held by the invocation of .unsubscribe(), waiting for a result.
            # Do not wait on the completion of complete_unsub() or this callback will deadlock the
            # Paho network loop. Just schedule the eventual completion, and keep it moving.
            asyncio.run_coroutine_threadsafe(complete_unsub(), self._event_loop)

        def on_publish(client: mqtt.Client, userdata: Any, mid: int) -> None:
            logger.debug("PUBACK received for mid {}".format(mid))

            async def complete_pub() -> None:
                async with self._mid_tracker_lock:
                    try:
                        f = self._pending_pubs[mid]
                        f.set_result(True)
                    except KeyError:
                        logger.warning("Unexpected PUBACK received for mid {}".format(mid))

            # NOTE: The complete_pub() coroutine cannot finish right away due to the
            # mid_tracker_lock being held by the invocation of .publish(), waiting for a result.
            # Do not wait on the completion of complete_pub() or this callback will deadlock the
            # Paho network loop. Just schedule the eventual completion, and keep it moving.
            asyncio.run_coroutine_threadsafe(complete_pub(), self._event_loop)

        def on_message(client: mqtt.Client, userdata: Any, message: mqtt.MQTTMessage) -> None:
            logger.debug("Incoming MQTT Message received on {}".format(message.topic))

            async def add_to_queue() -> None:
                await self._incoming_messages.put(message)

            asyncio.run_coroutine_threadsafe(add_to_queue(), self._event_loop)

        mqtt_client.on_connect = on_connect
        mqtt_client.on_disconnect = on_disconnect
        mqtt_client.on_subscribe = on_subscribe
        mqtt_client.on_unsubscribe = on_unsubscribe
        mqtt_client.on_publish = on_publish
        mqtt_client.on_message = on_message

        return mqtt_client

    async def _reconnect_loop(self) -> None:
        """Reconnect logic"""
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

    def _network_loop_running(self) -> bool:
        """Internal helper method to assess network loop"""
        if self._network_loop and not self._network_loop.done():
            return True
        else:
            return False

    def is_connected(self) -> bool:
        """
        Returns a boolean indicating whether the MQTT client is currently connected.

        Note that this value is only accurate as of the time it returns. It could change at
        any point.
        """
        return self._connected

    def set_credentials(self, username: str, password: Optional[str] = None) -> None:
        """
        Set a username and optionally a password for broker authentication.

        Must be called before .connect() to have any effect.

        :param str username: The username for broker authentication
        :param str password: The password for broker authentication (Optional)
        """
        self._mqtt_client.username_pw_set(username=username, password=password)

    def add_incoming_message_filter(self, topic: str) -> None:
        """
        Filter incoming messages on a specific topic.

        :param str topic: The topic you wish to filter on

        :raises: ValueError if a filter is already applied for the topic
        """
        if topic in self._incoming_filtered_messages:
            raise ValueError("Filter already applied for this topic")

        # Add a Queue for this filter
        self._incoming_filtered_messages[topic] = asyncio.Queue()

        def callback(client, userdata, message):
            logger.debug("Incoming MQTT Message received on filter {}".format(message.topic))

            async def add_to_queue():
                await self._incoming_filtered_messages[topic].put(message)

            asyncio.run_coroutine_threadsafe(add_to_queue(), self._event_loop)

        # Add the callback as a filter
        self._mqtt_client.message_callback_add(topic, callback)

    def remove_incoming_message_filter(self, topic: str) -> None:
        """
        Stop filtering incoming messages on a specific topic

        :param str topic: The topic you wish to stop filtering on

        :raises: ValueError if a filter is not already applied for the topic
        """
        if topic not in self._incoming_filtered_messages:
            raise ValueError("Filter not yet applied to this topic")

        # Remove the callback
        self._mqtt_client.message_callback_remove(topic)

        # Delete the filter queue
        del self._incoming_filtered_messages[topic]

    def get_incoming_message_generator(
        self, filter_topic: Optional[str] = None
    ) -> AsyncGenerator[mqtt.MQTTMessage, None]:
        """
        Return a generator that yields incoming messages

        :param str filter_topic: The topic you wish to receive a generator for.
            If not provided, will return a generator for non-filtered messages

        :raises: ValueError if a filter is not already applied for the given topic

        :returns: A generator that yields incoming messages
        """
        if filter_topic is not None and filter_topic not in self._incoming_filtered_messages:
            raise ValueError("No filter applied for given topic")
        elif filter_topic is not None:
            incoming_messages = self._incoming_filtered_messages[filter_topic]
        else:
            incoming_messages = self._incoming_messages

        async def message_generator() -> AsyncGenerator[mqtt.MQTTMessage, None]:
            while True:
                yield await incoming_messages.get()

        return message_generator()

    async def connect(self) -> None:
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

                # Start the reconnect daemon (if enabled and not already running)
                #
                # NOTE: We need to track if the daemon was started by this attempt to know if
                # we should cancel it in the event of this attempt being cancelled. Cancelling
                # a connect attempt should not cancel a pre-existing reconnect daemon.
                #
                # Consider the case where a connection is established with a daemon, and the
                # connection is later lost. In between automatic reconnect attempts, the .connect()
                # method is invoked manually - if that manual connect attempt is cancelled, we
                # should not be cancelling the pre-existing reconnect daemon that is trying to
                # re-establish the original connection.
                if self._auto_reconnect and not self._reconnect_daemon:
                    self._reconnect_daemon = asyncio.create_task(self._reconnect_loop())
                    reconnect_started_on_this_attempt = True
                else:
                    reconnect_started_on_this_attempt = False

                try:
                    await self._do_connect()
                except asyncio.CancelledError:
                    logger.debug("Connect attempt was cancelled")
                    logger.warning(
                        "The cancelled connect attempt may still complete as it is in-flight"
                    )
                    if self._reconnect_daemon and reconnect_started_on_this_attempt:
                        logger.debug(
                            "Reconnect daemon was started with this connect attempt. Cancelling it."
                        )
                        self._reconnect_daemon.cancel()
                        self._reconnect_daemon = None

                        # NOTE: Because a connection could still complete after cancellation due to
                        # it being in flight, this means that it's possible a connection could be
                        # established without a running reconnect daemon, even if auto_reconnect
                        # is enabled. This could be remedied fairly easily if so desired, but I've
                        # chosen to leave it out for simplicity.
                    else:
                        logger.debug(
                            "Reconnect daemon was started on a previous connect. Leaving it alone."
                        )
                    raise
                finally:
                    # Pending operation is completed regardless of outcome
                    del self._pending_connect
                    self._pending_connect = None

            else:
                logger.debug("Already connected!")

    async def _do_connect(self) -> None:
        """Connect, start network loop, and wait for response"""

        # NOTE: we know this is safe because of the connection lock in the outer method
        self._pending_connect = self._event_loop.create_future()

        # Paho Connect
        logger.debug("Attempting connect using port {}...".format(self._port))
        try:
            rc = await self._event_loop.run_in_executor(
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
        except asyncio.CancelledError:
            # Handled in outer method
            raise
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
                raise MQTTConnectionFailedError(message="Unexpected Paho .connect() rc") from e

        # Start Paho network loop, and store the task. This task will complete upon disconnect
        # whether due to invocation of .disconnect(), an unexpected network drop, or a connection
        # failure (which Paho considers to be a disconnect)
        #
        # NOTE: If the connect attempt is cancelled, the network loop cannot be stopped.
        # This is because when using .loop_forever(), the loop lifecycle is managed by Paho.
        # It cannot be manually ended; one of the above termination conditions must be met.
        #
        # However, in the case of a cancelled connect, it's likely that none of those conditions
        # will be met, and thus the network loop will persist.
        # This is fine, since it'll eventually get cleaned up, as at the very least, a
        # .disconnect() invocation is required for graceful exit, if not sooner.
        #
        # But, this does introduce a case where the network loop may already be running
        # during a connect attempt due to a previously cancelled attempt, so make sure it isn't
        # before trying to start it again.
        #
        # NOTE: This MUST be called after connecting - loop_forever requires a socket to have been
        # already established. This is not true of other network loop APIs, but it is true of this
        # one.
        if not self._network_loop_running():
            logger.debug("Starting Paho network loop")
            self._network_loop = self._event_loop.run_in_executor(
                None, self._mqtt_client.loop_forever
            )
        else:
            logger.debug(
                "Paho network loop was already running. Likely due to a previous cancellation."
            )

        # The result of the CONNACK is received via the pending connect Future
        logger.debug("Waiting for connect response...")
        rc = await self._pending_connect
        if rc != mqtt.CONNACK_ACCEPTED:
            # If the connect failed, the network loop will stop.
            # Might take a moment though, so wait on the network loop completion before clearing
            if self._network_loop is not None:
                # This block should always execute. This condition is just to help the type checker.
                logger.debug("Waiting for network loop to exit and clearing task")
                await self._network_loop
                self._network_loop = None
            raise MQTTConnectionFailedError(rc=rc)

    async def disconnect(self) -> None:
        """
        Disconnect from the MQTT broker.

        Ensure this is called for graceful exit.
        """
        # Wait for permission to alter the connection
        async with self._connection_lock:

            # We no longer wish to be connected
            self._desire_connection = False

            # Cancel reconnection attempts
            if self._reconnect_daemon:
                logger.debug("Cancelling reconnect daemon")
                self._reconnect_daemon.cancel()
                self._reconnect_daemon = None

            # The network loop Future being present (running or not) indicates one of a few things:
            # 1) We are connected
            # 2) We were previously connected and the connection was lost
            # 3) A connect attempt started the loop, and then was cancelled before connect finished
            # In all of these cases, we need to invoke Paho's .disconnect() to clean up.
            if self._network_loop:

                # Paho Disconnect
                # NOTE: Paho disconnect shouldn't raise any exceptions
                logger.debug("Attempting disconnect")
                rc = await self._event_loop.run_in_executor(None, self._mqtt_client.disconnect)
                rc_msg = mqtt.error_string(rc)
                logger.debug("Disconnect returned rc {} - {}".format(rc, rc_msg))

                if rc == mqtt.MQTT_ERR_SUCCESS:
                    # Wait for disconnection to complete
                    logger.debug("Waiting for disconnect to complete...")
                    async with self.disconnected_cond:
                        await self.disconnected_cond.wait_for(lambda: not self.is_connected())
                    logger.debug("Waiting for network loop to exit and clearing task")
                    await self._network_loop
                    self._network_loop = None
                    # Wait slightly for tasks started by the on_disconnect handler to finish.
                    # This will prevent warnings.
                    # TODO: improve efficiency by being able to wait on something specific
                    await asyncio.sleep(0.02)
                elif rc == mqtt.MQTT_ERR_NO_CONN:
                    # This happens when we disconnect while already disconnected.
                    # In this implementation, it should only happen if Paho's inner state
                    # indicates we would like to be connected, but we actually aren't.
                    # We still want to do this disconnect however, because doing so changes
                    # Paho's state to indicate we no longer wish to be connected.
                    logger.debug("Early disconnect return (Already disconnected)")
                    # if self._network_loop_running():
                    #     # This block should never execute
                    #     logger.warning("Network loop unexpectedly still running. Waiting")
                    #     await self._network_loop
                    logger.debug("Clearing network loop task")
                    self._network_loop = None
                else:
                    # This block should never execute
                    logger.warning(
                        "Unexpected rc {} from Paho .disconnect(). Doing nothing.".format(rc)
                    )

            else:
                logger.debug("Already disconnected!")

    async def subscribe(self, topic: str) -> None:
        """
        Subscribe to a topic from the MQTT broker.

        :param str topic: a single string specifying the subscription topic to subscribe to

        :raises: ValueError if topic is None or has zero string length.
        :raises: MQTTError if there is an error subscribing
        """
        try:
            mid = None
            logger.debug("Attempting subscribe")
            # Using this lock postpones any code that runs in the on_subscribe callback that will
            # be invoked on response, as the callback also uses the lock. This ensures that the
            # result cannot be received before we have a Future created for the eventual result.
            async with self._mid_tracker_lock:
                (rc, mid) = await self._event_loop.run_in_executor(
                    None, functools.partial(self._mqtt_client.subscribe, topic=topic, qos=1)
                )
                rc_msg = mqtt.error_string(rc)
                logger.debug("Subscribe returned rc {} - {}".format(rc, rc_msg))
                if rc != mqtt.MQTT_ERR_SUCCESS:
                    if rc not in expected_subscribe_rc:
                        logger.warning("Unexpected rc {} from Paho .subscribe()".format(rc))
                    raise MQTTError(rc)

                # Establish a pending subscribe
                sub_done = self._event_loop.create_future()
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

    async def unsubscribe(self, topic: str) -> None:
        """
        Unsubscribe from a topic on the MQTT broker.

        :param str topic: a single string which is the subscription topic to unsubscribe from.

        :raises: ValueError if topic is None or has zero string length.
        :raises: MQTTError if there is an error subscribing
        """
        try:
            mid = None
            logger.debug("Attempting unsubscribe")
            # Using this lock postpones any code that runs in the on_unsubscribe callback that will
            # be invoked on response, as the callback also uses the lock. This ensures that the
            # result cannot be received before we have a Future created for the eventual result.
            async with self._mid_tracker_lock:
                (rc, mid) = await self._event_loop.run_in_executor(
                    None, functools.partial(self._mqtt_client.unsubscribe, topic=topic)
                )
                rc_msg = mqtt.error_string(rc)
                logger.debug("Unsubscribe returned rc {} - {}".format(rc, rc_msg))
                if rc != mqtt.MQTT_ERR_SUCCESS:
                    if rc not in expected_unsubscribe_rc:
                        logger.warning("Unexpected rc {} from Paho .unsubscribe()".format(rc))
                    raise MQTTError(rc)

                # Establish a pending unsubscribe
                unsub_done = self._event_loop.create_future()
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

    async def publish(self, topic: str, payload: Union[str, bytes, int, float, None]) -> None:
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
            # Using this lock postpones any code that runs in the on_publish callback that will
            # be invoked on response, as the callback also uses the lock. This ensures that the
            # result cannot be received before we have a Future created for the eventual result.
            async with self._mid_tracker_lock:
                message_info = await self._event_loop.run_in_executor(
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
                pub_done = self._event_loop.create_future()
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
