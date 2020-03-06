# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""
This module represents proxy options to enable sending traffic through proxy servers.
"""


class ProxyOptions(object):
    """
    A class containing various options to send traffic through proxy servers by enabling
    proxying of MQTT connection.
    """

    def __init__(
        self, proxy_type, proxy_addr, proxy_port, proxy_username=None, proxy_password=None
    ):
        """
        Initializer for proxy options.
        :param proxy_type: The type of the proxy server. This can be one of three possible choices:socks.HTTP, socks.SOCKS4, or socks.SOCKS5
        :param proxy_addr: IP address or DNS name of proxy server
        :param proxy_port: The port of the proxy server. Defaults to 1080 for socks and 8080 for http.
        :param proxy_username: (optional) username for SOCKS5 proxy, or userid for SOCKS4 proxy.This parameter is ignored if an HTTP server is being used.
         If it is not provided, authentication will not be used (servers may accept unauthenticated requests).
        :param proxy_password: (optional) This parameter is valid only for SOCKS5 servers and specifies the respective password for the username provided.
        """
        self._proxy_type = proxy_type
        self._proxy_addr = proxy_addr
        self._proxy_port = proxy_port
        self._proxy_username = proxy_username
        self._proxy_password = proxy_password

    @property
    def proxy_type(self):
        return self._proxy_type

    @property
    def proxy_address(self):
        return self._proxy_addr

    @property
    def proxy_port(self):
        return self._proxy_port

    @property
    def proxy_username(self):
        return self._proxy_username

    @property
    def proxy_password(self):
        return self._proxy_password
