# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging
import threading
import abc
from azure.iot.device import constant


logger = logging.getLogger(__name__)

DEFAULT_KEEPALIVE = 60


class BasePipelineConfig(abc.ABC):
    """A base class for storing all configurations/options shared across the Azure IoT Python Device Client Library.
    More specific configurations such as those that only apply to the IoT Hub Client will be found in the respective
    config files.
    """

    def __init__(
        self,
        hostname,
        gateway_hostname=None,
        sastoken=None,
        x509=None,
        server_verification_cert=None,
        websockets=False,
        cipher="",
        proxy_options=None,
        keep_alive=DEFAULT_KEEPALIVE,
        auto_connect=True,
        connection_retry=True,
        connection_retry_interval=10,
    ):
        """Initializer for BasePipelineConfig

        :param str hostname: The hostname being connected to
        :param str gateway_hostname: The gateway hostname optionally being used
        :param sastoken: SasToken to be used for authentication. Mutually exclusive with x509.
        :type sastoken: :class:`azure.iot.device.common.auth.SasToken`
        :param x509: X509 to be used for authentication. Mutually exclusive with sastoken.
        :type x509: :class:`azure.iot.device.models.X509`
        :param str server_verification_cert: The trusted certificate chain.
            Necessary when using connecting to an endpoint which has a non-standard root of trust,
            such as a protocol gateway.
        :param bool websockets: Enabling/disabling websockets in MQTT. This feature is relevant
            if a firewall blocks port 8883 from use.
        :param cipher: Optional cipher suite(s) for TLS/SSL, as a string in
            "OpenSSL cipher list format" or as a list of cipher suite strings.
        :type cipher: str or list(str)
        :param proxy_options: Details of proxy configuration
        :type proxy_options: :class:`azure.iot.device.common.models.ProxyOptions`
        :param int keepalive: Maximum period in seconds between communications with the
            broker.
        :param bool auto_connect: Indicates if automatic connects should occur
        :param bool connection_retry: Indicates if dropped connection should result in attempts to
            re-establish it
        :param int connection_retry_interval: Interval (in seconds) between connection retries
        """
        # Network
        self.hostname = hostname
        self.gateway_hostname = gateway_hostname
        self.keep_alive = self._sanitize_keep_alive(keep_alive)

        # Auth
        self.sastoken = sastoken
        self.x509 = x509
        if (not sastoken and not x509) or (sastoken and x509):
            raise ValueError("One of either 'sastoken' or 'x509' must be provided")
        self.server_verification_cert = server_verification_cert
        self.websockets = websockets
        self.cipher = self._sanitize_cipher(cipher)
        self.proxy_options = proxy_options

        # Pipeline
        self.auto_connect = auto_connect
        self.connection_retry = connection_retry
        self.connection_retry_interval = self._sanitize_connection_retry_interval(
            connection_retry_interval
        )

    @staticmethod
    def _sanitize_cipher(cipher):
        """Sanitize the cipher input and convert to a string in OpenSSL list format"""
        if isinstance(cipher, list):
            cipher = ":".join(cipher)

        if isinstance(cipher, str):
            cipher = cipher.upper()
            cipher = cipher.replace("_", "-")
        else:
            raise TypeError("Invalid type for 'cipher'")

        return cipher

    @staticmethod
    def _sanitize_keep_alive(keep_alive):
        try:
            keep_alive = int(keep_alive)
        except (ValueError, TypeError):
            raise TypeError("Invalid type for 'keep alive'. Must be a numeric value.")

        if keep_alive <= 0:
            # Not allowing a keep alive of 0 as this would mean frequent ping exchanges.
            raise ValueError("'keep alive' must be greater than 0")

        if keep_alive > constant.MAX_KEEP_ALIVE_SECS:
            raise ValueError("'keep_alive' cannot exceed 1740 seconds (29 minutes)")

        return keep_alive

    @staticmethod
    def _sanitize_connection_retry_interval(connection_retry_interval):
        try:
            connection_retry_interval = int(connection_retry_interval)
        except (ValueError, TypeError):
            raise TypeError("Invalid type for 'connection_retry_interval'. Must be a numeric value")

        if connection_retry_interval > threading.TIMEOUT_MAX:
            # Python timers have a (platform dependent) max timeout.
            raise ValueError(
                "'connection_retry_interval' cannot exceed {} seconds".format(threading.TIMEOUT_MAX)
            )

        if connection_retry_interval <= 0:
            raise ValueError("'connection_retry_interval' must be greater than 0")

        return connection_retry_interval
