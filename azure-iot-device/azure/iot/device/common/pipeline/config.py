# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging
import six
import abc
from azure.iot.device import constant

# For making long work in python 2 and 3
from builtins import int

logger = logging.getLogger(__name__)

DEFAULT_KEEPALIVE = 180


@six.add_metaclass(abc.ABCMeta)
class BasePipelineConfig(object):
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
        """
        # Network
        self.hostname = hostname
        self.gateway_hostname = gateway_hostname

        # Auth
        self.sastoken = sastoken
        self.x509 = x509
        if (not sastoken and not x509) or (sastoken and x509):
            raise ValueError("One of either 'sastoken' or 'x509' must be provided")
        self.server_verification_cert = server_verification_cert
        self.websockets = websockets
        self.cipher = self._sanitize_cipher(cipher)
        self.proxy_options = proxy_options
        self.keep_alive = self._rectify_keep_alive(keep_alive)

    @staticmethod
    def _sanitize_cipher(cipher):
        """Sanitize the cipher input and convert to a string in OpenSSL list format
        """
        if isinstance(cipher, list):
            cipher = ":".join(cipher)

        if isinstance(cipher, str):
            cipher = cipher.upper()
            cipher = cipher.replace("_", "-")
        else:
            raise TypeError("Invalid type for 'cipher'")

        return cipher

    @staticmethod
    def _rectify_keep_alive(keep_alive):
        if keep_alive and not isinstance(keep_alive, (int, float)):
            raise TypeError("Invalid type for 'keep alive'. Permissible types are number.")

        if keep_alive is not None and keep_alive <= 0:
            # Not allowing a keep alive of 0 as this would mean frequent ping exchanges.
            logger.error(
                "'keep alive' can not be zero or negative. A default value of 'keep alive' will be used by the protocol."
            )
            keep_alive = DEFAULT_KEEPALIVE
        elif keep_alive and keep_alive > constant.MAX_KEEP_ALIVE_SECS:
            # This is Hub's maximum Load Balancer Limit before
            logger.error(
                "'keep alive' can not be more than 29 minutes. 'keep alive' will be set to max value of 29 minutes to continue."
            )
            keep_alive = constant.MAX_KEEP_ALIVE_SECS

        return keep_alive
