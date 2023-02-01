# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging
import socks
import ssl
from typing import Optional, Any
from azure.iot.device.common.auth import sastoken as st  # type: ignore

# TODO: add typings for imports
# TODO: update docs to ensure types are correct


logger = logging.getLogger(__name__)

# The max keep alive is determined by the load balancer currently.
MAX_KEEP_ALIVE_SECS = 1740


string_to_socks_constant_map = {"HTTP": socks.HTTP, "SOCKS4": socks.SOCKS4, "SOCKS5": socks.SOCKS5}
socks_constant_to_string_map = {socks.HTTP: "HTTP", socks.SOCKS4: "SOCKS4", socks.SOCKS5: "SOCKS5"}


class ProxyOptions(object):
    """
    A class containing various options to send traffic through proxy servers by enabling
    proxying of MQTT connection.
    """

    def __init__(
        self,
        proxy_type: str,
        proxy_addr: str,
        proxy_port: int,
        proxy_username: Optional[str] = None,
        proxy_password: Optional[str] = None,
    ):
        """
        Initializer for proxy options.
        :param str proxy_type: The type of the proxy server. This can be one of three possible choices: "HTTP", "SOCKS4", or "SOCKS5"
        :param str proxy_addr: IP address or DNS name of proxy server
        :param int proxy_port: The port of the proxy server. Defaults to 1080 for socks and 8080 for http.
        :param str proxy_username: (optional) username for SOCKS5 proxy, or userid for SOCKS4 proxy.This parameter is ignored if an HTTP server is being used.
         If it is not provided, authentication will not be used (servers may accept unauthenticated requests).
        :param str proxy_password: (optional) This parameter is valid only for SOCKS5 servers and specifies the respective password for the username provided.
        """
        (self._proxy_type, self._proxy_type_socks) = _format_proxy_type(proxy_type)
        self._proxy_addr = proxy_addr
        self._proxy_port = int(proxy_port)
        self._proxy_username = proxy_username
        self._proxy_password = proxy_password


class ClientConfig:
    """
    Class for storing all configurations/options shared across the
    Azure IoT Python Device Client Library.
    """

    def __init__(
        self,
        *,
        ssl_context: ssl.SSLContext,
        hostname: str,
        gateway_hostname: Optional[str] = None,
        proxy_options: Optional[ProxyOptions] = None,
        sastoken: Optional[st.SasToken] = None,
        keep_alive: int = 60,
        auto_reconnect: bool = True,
        websockets: bool = False,
    ) -> None:
        """Initializer for ClientConfig

        :param str hostname: The hostname being connected to
        :param str gateway_hostname: The gateway hostname optionally being used
        :param proxy_options: Details of proxy configuration
        :type proxy_options: :class:`azure.iot.device.common.models.ProxyOptions`
        :param ssl_context: SSLContext to use with the client
        :type ssl_context: :class:`ssl.SSLContext`
        :param sastoken: SasToken to be used for authentication. Mutually exclusive with x509.
        :type sastoken: :class:`azure.iot.device.common.auth.SasToken`
        :param int keepalive: Maximum period in seconds between communications with the
            broker.
        :param bool auto_reconnect: Indicates if dropped connection should result in attempts to
            re-establish it
        :param bool websockets: Enabling/disabling websockets in MQTT. This feature is relevant
            if a firewall blocks port 8883 from use.
        """
        # Network
        self.hostname = hostname
        self.gateway_hostname = gateway_hostname
        self.proxy_options = proxy_options
        self.ssl_context = ssl_context

        # Auth
        self.sastoken = sastoken

        # MQTT
        self.keep_alive = _sanitize_keep_alive(keep_alive)
        self.auto_reconnect = auto_reconnect
        self.websockets = websockets


class IoTHubClientConfig(ClientConfig):
    def __init__(
        self,
        *,
        device_id: str,
        module_id: Optional[str] = None,
        product_info: str = "",
        **kwargs: Any,
    ) -> None:
        """
        Config object used for IoTHub clients, containing all relevant details and options.

        :param str device_id: The device identity being used with the IoTHub
        :param str module_id: The module identity being used with the IoTHub
        :param str product_info: A custom identification string.

        Additional parameters found in the docstring of the parent class
        """
        self.device_id = device_id
        self.module_id = module_id
        self.product_info = product_info
        super().__init__(**kwargs)


class ProvisioningClientConfig(ClientConfig):
    def __init__(self, *, registration_id: str, id_scope: str, **kwargs) -> None:
        """
        Config object used for Provisioning clients, containing all relevant details and options.

        :param str registration_id: The device registration identity being provisioned
        :param str id_scope: The identity of the provisioning service being used
        """
        self.registration_id = registration_id
        self.id_scope = id_scope
        super().__init__(**kwargs)


# Sanitization #


def _format_proxy_type(proxy_type):
    """Returns a tuple of formats for proxy type (string, socks library constant)"""
    try:
        return (proxy_type, string_to_socks_constant_map[proxy_type])
    except KeyError:
        # Backwards compatibility for when we used the socks library constants in the API
        try:
            return (socks_constant_to_string_map[proxy_type], proxy_type)
        except KeyError:
            raise ValueError("Invalid Proxy Type")


def _sanitize_keep_alive(keep_alive):
    try:
        keep_alive = int(keep_alive)
    except (ValueError, TypeError):
        raise TypeError("Invalid type for 'keep alive'. Must be a numeric value.")

    if keep_alive <= 0:
        # Not allowing a keep alive of 0 as this would mean frequent ping exchanges.
        raise ValueError("'keep alive' must be greater than 0")

    if keep_alive > MAX_KEEP_ALIVE_SECS:
        raise ValueError("'keep_alive' cannot exceed 1740 seconds (29 minutes)")

    return keep_alive
