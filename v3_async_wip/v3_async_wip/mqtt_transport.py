# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import paho.mqtt.client as mqtt
import asyncio
import functools
import logging

# import weakref

logger = logging.getLogger(__name__)


class MQTTTransport(object):
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
        Constructor to instantiate an MQTT protocol wrapper.
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
        self._hostname = hostname
        self._port = port
        self._keep_alive = keep_alive

        self._mqtt_client = self._create_mqtt_client(
            client_id, transport, ssl_context, proxy_options, websockets_path
        )

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
        # self_weakref = weakref.ref(self)

        # TODO: define and set any handlers here

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
        """
        loop = asyncio.get_running_loop()

        try:
            logger.debug("Connect using port {}".format(self._port))
            loop.run_in_executor(
                None,
                functools.partial(
                    self._mqtt_client.connect,
                    host=self._hostname,
                    port=self._port,
                    keepalive=self._keep_alive,
                ),
            )
        except Exception:
            pass

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
