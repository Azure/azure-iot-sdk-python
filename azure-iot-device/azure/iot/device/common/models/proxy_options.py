# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""
This module represents proxy options to enable sending traffic through proxy servers.
"""
import socks

string_to_socks_constant_map = {"HTTP": socks.HTTP, "SOCKS4": socks.SOCKS4, "SOCKS5": socks.SOCKS5}

socks_constant_to_string_map = {socks.HTTP: "HTTP", socks.SOCKS4: "SOCKS4", socks.SOCKS5: "SOCKS5"}


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
        :param str proxy_type: The type of the proxy server. This can be one of three possible choices: "HTTP", "SOCKS4", or "SOCKS5"
        :param str proxy_addr: IP address or DNS name of proxy server
        :param int proxy_port: The port of the proxy server. Defaults to 1080 for socks and 8080 for http.
        :param str proxy_username: (optional) username for SOCKS5 proxy, or userid for SOCKS4 proxy.This parameter is ignored if an HTTP server is being used.
         If it is not provided, authentication will not be used (servers may accept unauthenticated requests).
        :param str proxy_password: (optional) This parameter is valid only for SOCKS5 servers and specifies the respective password for the username provided.
        """
        (self._proxy_type, self._proxy_type_socks) = format_proxy_type(proxy_type)
        self._proxy_addr = proxy_addr
        self._proxy_port = int(proxy_port)
        self._proxy_username = proxy_username
        self._proxy_password = proxy_password

    @property
    def proxy_type(self):
        return self._proxy_type

    @property
    def proxy_type_socks(self):
        return self._proxy_type_socks

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


def format_proxy_type(proxy_type):
    """Returns a tuple of formats for proxy type (string, socks library constant)"""
    try:
        return (proxy_type, string_to_socks_constant_map[proxy_type])
    except KeyError:
        # Backwards compatibility for when we used the socks library constants in the API
        try:
            return (socks_constant_to_string_map[proxy_type], proxy_type)
        except KeyError:
            raise ValueError("Invalid Proxy Type")
