# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
import logging
import socks
from azure.iot.device.common.models import ProxyOptions

logging.basicConfig(level=logging.DEBUG)


@pytest.mark.describe("ProxyOptions")
class TestProxyOptions(object):
    @pytest.mark.it(
        "Instantiates with the 'proxy_type' and 'proxy_type_socks' properties set based on the value of the 'proxy_type' parameter"
    )
    @pytest.mark.parametrize(
        "proxy_type_input, expected_proxy_type, expected_proxy_type_socks",
        [
            pytest.param("HTTP", "HTTP", socks.HTTP, id="HTTP (string)"),
            pytest.param("SOCKS4", "SOCKS4", socks.SOCKS4, id="SOCKS4 (string)"),
            pytest.param("SOCKS5", "SOCKS5", socks.SOCKS5, id="SOCKS5 (string)"),
            # Backwards compatibility
            pytest.param(socks.HTTP, "HTTP", socks.HTTP, id="HTTP (socks constant)"),
            pytest.param(socks.SOCKS4, "SOCKS4", socks.SOCKS4, id="SOCKS4 (socks constant)"),
            pytest.param(socks.SOCKS5, "SOCKS5", socks.SOCKS5, id="SOCKS5 (socks constant)"),
        ],
    )
    def test_proxy_type(self, proxy_type_input, expected_proxy_type, expected_proxy_type_socks):
        proxy_options = ProxyOptions(
            proxy_type=proxy_type_input, proxy_addr="127.0.0.1", proxy_port=8888
        )

        assert proxy_options.proxy_type == expected_proxy_type
        assert proxy_options.proxy_type_socks == expected_proxy_type_socks

    @pytest.mark.it("Maintains 'proxy_type' as a read-only property")
    def test_proxy_type_read_only(self):
        proxy_options = ProxyOptions(proxy_type="HTTP", proxy_addr="127.0.0.1", proxy_port=8888)
        with pytest.raises(AttributeError):
            proxy_options.proxy_type = "new value"

    @pytest.mark.it("Maintains 'proxy_type_socks' as a read-only property")
    def test_proxy_type_socks_read_only(self):
        proxy_options = ProxyOptions(proxy_type="HTTP", proxy_addr="127.0.0.1", proxy_port=8888)
        with pytest.raises(AttributeError):
            proxy_options.proxy_type_socks = "new value"

    @pytest.mark.it("Raises a ValueError if proxy_type is invalid")
    def test_invalid_proxy_type(self):
        with pytest.raises(ValueError):
            ProxyOptions(proxy_type="INVALID", proxy_addr="127.0.0.1", proxy_port=8888)

    @pytest.mark.it(
        "Instantiates with the 'proxy_address' property set to the value of the 'proxy_addr' parameter"
    )
    def test_proxy_address(self):
        proxy_addr = "127.0.0.1"
        proxy_options = ProxyOptions(proxy_type=socks.HTTP, proxy_addr=proxy_addr, proxy_port=8888)

        assert proxy_options.proxy_address == proxy_addr

    @pytest.mark.it("Maintains 'proxy_address' as a read-only property")
    def test_proxy_address_read_only(self):
        proxy_options = ProxyOptions(proxy_type=socks.HTTP, proxy_addr="127.0.0.1", proxy_port=8888)
        with pytest.raises(AttributeError):
            proxy_options.proxy_address = "new value"

    @pytest.mark.it(
        "Instantiates with the 'proxy_port' property set to the value of the 'proxy_port' parameter"
    )
    def test_proxy_port(self):
        proxy_port = 8888
        proxy_options = ProxyOptions(
            proxy_type=socks.HTTP, proxy_addr="127.0.0.1", proxy_port=proxy_port
        )

        assert proxy_options.proxy_port == proxy_port

    @pytest.mark.it(
        "Converts the 'proxy_port' property to an integer if the 'proxy_port' parameter is provided as a string"
    )
    def test_proxy_port_conversion(self):
        proxy_port = "8888"
        proxy_options = ProxyOptions(
            proxy_type=socks.HTTP, proxy_addr="127.0.0.1", proxy_port=proxy_port
        )

        assert proxy_options.proxy_port == int(proxy_port)

    @pytest.mark.it("Maintains 'proxy_port' as a read-only property")
    def test_proxy_port_read_only(self):
        proxy_options = ProxyOptions(proxy_type=socks.HTTP, proxy_addr="127.0.0.1", proxy_port=8888)
        with pytest.raises(AttributeError):
            proxy_options.proxy_port = "new value"

    @pytest.mark.it(
        "Instantiates with the 'proxy_username' property set to the value of the 'proxy_username' parameter, if provided"
    )
    def test_proxy_username(self):
        proxy_username = "myusername"
        proxy_options = ProxyOptions(
            proxy_type=socks.HTTP,
            proxy_addr="127.0.0.1",
            proxy_port=8888,
            proxy_username=proxy_username,
        )

        assert proxy_options.proxy_username == proxy_username

    @pytest.mark.it(
        "Defaults the 'proxy_username' property to 'None' if the 'proxy_username' parameter is not provided"
    )
    def test_proxy_username_default(self):
        proxy_options = ProxyOptions(proxy_type=socks.HTTP, proxy_addr="127.0.0.1", proxy_port=8888)
        assert proxy_options.proxy_username is None

    @pytest.mark.it("Maintains 'proxy_username' as a read-only property")
    def test_proxy_username_read_only(self):
        proxy_options = ProxyOptions(proxy_type=socks.HTTP, proxy_addr="127.0.0.1", proxy_port=8888)
        with pytest.raises(AttributeError):
            proxy_options.proxy_username = "new value"

    @pytest.mark.it(
        "Instantiates with the 'proxy_password' property set to the value of the 'proxy_password' parameter, if provided"
    )
    def test_proxy_password(self):
        proxy_password = "fake_password"
        proxy_options = ProxyOptions(
            proxy_type=socks.HTTP,
            proxy_addr="127.0.0.1",
            proxy_port=8888,
            proxy_password=proxy_password,
        )

        assert proxy_options.proxy_password == proxy_password

    @pytest.mark.it(
        "Defaults the 'proxy_password' property to 'None' if the 'proxy_password' parameter is not provided"
    )
    def test_proxy_password_default(self):
        proxy_options = ProxyOptions(proxy_type=socks.HTTP, proxy_addr="127.0.0.1", proxy_port=8888)
        assert proxy_options.proxy_password is None

    @pytest.mark.it("Maintains 'proxy_password' as a read-only property")
    def test_proxy_password_read_only(self):
        proxy_options = ProxyOptions(proxy_type=socks.HTTP, proxy_addr="127.0.0.1", proxy_port=8888)
        with pytest.raises(AttributeError):
            proxy_options.proxy_password = "new value"
