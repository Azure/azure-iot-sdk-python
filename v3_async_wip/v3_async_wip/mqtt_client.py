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


class MQTTClient(object):
    """Provides an async MQTT message broker interface."""

    def __init__(
        self,
        client_id,
        hostname,
        port,
        transport="tcp",
        keep_alive=60,
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

        # Client
        self._mqtt_client = self._create_mqtt_client(
            client_id, transport, ssl_context, proxy_options, websockets_path
        )

        # Synchronization
        self.connected_cond = asyncio.Condition()
        self.disconnected_cond = asyncio.Condition()
        self._connect_failed_cond = asyncio.Condition()
        self._connection_permission = asyncio.Lock()

        # Event Loop
        self._loop = asyncio.get_running_loop()

    def _create_mqtt_client(
        self, client_id, transport, ssl_context, proxy_options, websockets_path
    ):
        """
        Create the MQTT client object and assign all necessary event handler callbacks.
        """
        logger.debug("creating mqtt client")

        # Instantiate the client
        mqtt_client = mqtt.Client(
            client_id=client_id,
            clean_session=False,
            protocol=mqtt.MQTTv311,
            transport=transport,
            reconnect_on_failure=False,
        )
        if transport == "websockets" and websockets_path:
            logger.debug("Creating client for connecting using MQTT over websockets")
            mqtt_client.ws_set_options(path=websockets_path)
        else:
            logger.debug("Creating client for connecting using MQTT over TCP")

        if proxy_options:
            logger.debug("Setting custom proxy options on mqtt client")
            mqtt_client.proxy_set(
                proxy_type=proxy_options.proxy_type_socks,
                proxy_addr=proxy_options.proxy_address,
                proxy_port=proxy_options.proxy_port,
                proxy_username=proxy_options.proxy_username,
                proxy_password=proxy_options.proxy_password,
            )

        mqtt_client.enable_logger(logging.getLogger("paho"))

        # Configure TLS/SSL
        mqtt_client.tls_set_context(context=ssl_context)

        # Set event handlers.  Use weak references back into this object to prevent leaks
        self_weakref = weakref.ref(self)

        def on_connect(client, userdata, flags, rc):
            this = self_weakref()
            message = mqtt.connack_string(rc)
            logger.debug("CONNACK rc {} - {}".format(rc, message))

            # Notify relevant tasks based on result
            if client.is_connected():

                async def notify_connected():
                    with this.connected_cond:
                        this.connected_cond.notify_all()

                asyncio.run_coroutine_threadsafe(notify_connected(), this._loop)

            else:

                async def notify_connection_fail():
                    with this._connect_failed_cond:
                        this._connect_failed_cond.notify_all()

                asyncio.run_coroutine_threadsafe(notify_connection_fail(), this._loop)

        def on_disconnect(client, userdata, rc):
            this = self_weakref()
            message = mqtt.error_string(rc)
            logger.debug("DISCONNECTED rc {} - {}".format(rc, message))

            # TODO: implement support for unexpected disconnect / reconnect
            # TODO: implement suppression of double disconnect
            # Probably need some kind of "desired state" internally to support the
            # two above items

            # Notify tasks waiting on disconnect
            async def notify_disconnected():
                with this.disconnected_cond:
                    this.disconnected_cond.notify_all()

            asyncio.run_coroutine_threadsafe(notify_disconnected(), this._loop)

        def on_subscribe(client, userdata, mid):
            pass

        def on_unsubscribe(client, userdata, mid):
            pass

        mqtt_client.on_connect = on_connect
        mqtt_client.on_disconnect = on_disconnect
        mqtt_client.on_subscribe = on_subscribe
        mqtt_client.on_unsubscribe = on_unsubscribe

        logger.debug("Created MQTT protocol client, assigned callbacks")
        return mqtt_client

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
        async with self._connection_permission:
            if not self._mqtt_client.is_connected():
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

                # Paho Connect
                logger.debug("Attempting connect using port {}".format(self._port))
                try:
                    await self._loop.run_in_executor(
                        None,
                        functools.partial(
                            self._mqtt_client.connect,
                            host=self._hostname,
                            port=self._port,
                            keepalive=self._keep_alive,
                        ),
                    )
                # TODO: more specialization of errors
                except Exception as e:
                    raise exceptions.ConnectionFailedError("Connect Invocation Failure") from e

                # Start Paho loop
                self._mqtt_client.loop_forever()

                # Wait for connection to complete (success or fail)
                done, pending = await asyncio.wait(
                    [success, failure], return_when=asyncio.FIRST_COMPLETED
                )
                for t in pending:
                    t.cancel()

                # Raise exception if connect failed
                completed = done.pop()
                if completed is failure:
                    raise exceptions.ConnectionFailedError("CONNACK Failure")

            else:
                logger.debug("Already connected!")

    async def disconnect(self):
        """
        Disconnect from the MQTT broker
        """
        # Wait for permission to alter the connection
        async with self._connection_permission:
            loop = asyncio.get_running_loop()

            if self._mqtt_client.is_connected():
                # Start listening for disconnect before performing Paho disconnect to make sure
                # we don't miss it. This could happen due to timing issues on the Paho thread
                # (i.e. disconnect received after invoking disconnect, but before our listening
                # task has started) or due to an unexpected disconnect happening during
                # the execution of this block.
                async def wait_for_disconnect():
                    with self.disconnected_cond:
                        await self.disconnected_cond.wait()

                disconnect_done = asyncio.create_task(wait_for_disconnect())

                # Paho Disconnect
                logger.debug("Attempting disconnect")
                await loop.run_in_executor(None, self._mqtt_client.disconnect())

                # Wait for disconnection to complete
                await disconnect_done

            else:
                logger.debug("Already disconnected!")

    # def connect(self):
    #     """
    #     Connect to the MQTT broker, using hostname and username set at instantiation.

    #     This method should be called as an entry point before sending any telemetry.

    #     If MQTT connection has been proxied, connection will take a bit longer to allow negotiation
    #     with the proxy server. Any errors in the proxy connection process will trigger exceptions

    #     :raises: ConnectionFailedError if connection could not be established.
    #     :raises: ConnectionDroppedError if connection is dropped during execution.
    #     :raises: UnauthorizedError if there is an error authenticating.
    #     :raises: NoConnectionError in certain failure scenarios where a connection could not be established
    #     :raises: ProtocolClientError if there is some other client error.
    #     :raises: TlsExchangeAuthError if there a failure with TLS certificate exchange
    #     :raises: ProtocolProxyError if there is a proxy-specific error
    #     """
    #     logger.debug("connecting to mqtt broker")

    #     try:
    #         if self._websockets:
    #             logger.info("Connect using port 443 (websockets)")
    #             rc = self._mqtt_client.connect(
    #                 host=self._hostname, port=443, keepalive=self._keep_alive
    #             )
    #         else:
    #             logger.info("Connect using port 8883 (TCP)")
    #             rc = self._mqtt_client.connect(
    #                 host=self._hostname, port=8883, keepalive=self._keep_alive
    #             )
    #     except socket.error as e:
    #         self._force_transport_disconnect_and_cleanup()

    #         # Only this type will raise a special error
    #         # To stop it from retrying.
    #         if (
    #             isinstance(e, ssl.SSLError)
    #             and e.strerror is not None
    #             and "CERTIFICATE_VERIFY_FAILED" in e.strerror
    #         ):
    #             raise exceptions.TlsExchangeAuthError() from e
    #         elif isinstance(e, socks.ProxyError):
    #             if isinstance(e, socks.SOCKS5AuthError):
    #                 # TODO This is the only I felt like specializing
    #                 raise exceptions.UnauthorizedError() from e
    #             else:
    #                 raise exceptions.ProtocolProxyError() from e
    #         else:
    #             # If the socket can't open (e.g. using iptables REJECT), we get a
    #             # socket.error.  Convert this into ConnectionFailedError so we can retry
    #             raise exceptions.ConnectionFailedError() from e

    #     except Exception as e:
    #         self._force_transport_disconnect_and_cleanup()

    #         raise exceptions.ProtocolClientError("Unexpected Paho failure during connect") from e

    #     logger.debug("_mqtt_client.connect returned rc={}".format(rc))
    #     if rc:
    #         raise _create_error_from_rc_code(rc)
    #     self._mqtt_client.loop_start()
