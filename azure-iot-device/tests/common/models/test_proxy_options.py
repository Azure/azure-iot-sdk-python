# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
import logging
from azure.iot.device.common.models import ProxyOptions

logging.basicConfig(level=logging.DEBUG)


@pytest.mark.describe("ProxyOptions")
class TestProxyOptions(object):
    @pytest.mark.it(
        "Instantiates with the 'proxy_type' property set to the value of the 'proxy_type' parameter"
    )
    def test_proxy_type(self, mocker):
        proxy_type = mocker.MagicMock()
        proxy_options = ProxyOptions(proxy_type=proxy_type, proxy_addr="127.0.0.1", proxy_port=8888)

        assert proxy_options.proxy_type == proxy_type

    @pytest.mark.it("Maintains 'proxy_type' as a read-only property")
    def test_proxy_type_read_only(self, mocker):
        proxy_options = ProxyOptions(
            proxy_type=mocker.MagicMock(), proxy_addr="127.0.0.1", proxy_port=8888
        )
        with pytest.raises(AttributeError):
            proxy_options.proxy_type = "new value"

    @pytest.mark.it(
        "Instantiates with the 'proxy_address' property set to the value of the 'proxy_addr' parameter"
    )
    def test_proxy_address(self, mocker):
        proxy_addr = "127.0.0.1"
        proxy_options = ProxyOptions(
            proxy_type=mocker.MagicMock(), proxy_addr=proxy_addr, proxy_port=8888
        )

        assert proxy_options.proxy_address == proxy_addr

    @pytest.mark.it("Maintains 'proxy_address' as a read-only property")
    def test_proxy_address_read_only(self, mocker):
        proxy_options = ProxyOptions(
            proxy_type=mocker.MagicMock(), proxy_addr="127.0.0.1", proxy_port=8888
        )
        with pytest.raises(AttributeError):
            proxy_options.proxy_address = "new value"

    @pytest.mark.it(
        "Instantiates with the 'proxy_port' property set to the value of the 'proxy_port' parameter"
    )
    def test_proxy_port(self, mocker):
        proxy_port = 8888
        proxy_options = ProxyOptions(
            proxy_type=mocker.MagicMock(), proxy_addr="127.0.0.1", proxy_port=proxy_port
        )

        assert proxy_options.proxy_port == proxy_port

    @pytest.mark.it("Maintains 'proxy_port' as a read-only property")
    def test_proxy_port_read_only(self, mocker):
        proxy_options = ProxyOptions(
            proxy_type=mocker.MagicMock(), proxy_addr="127.0.0.1", proxy_port=8888
        )
        with pytest.raises(AttributeError):
            proxy_options.proxy_port = "new value"

    @pytest.mark.it(
        "Instantiates with the 'proxy_username' property set to the value of the 'proxy_username' parameter, if provided"
    )
    def test_proxy_username(self, mocker):
        proxy_username = "myusername"
        proxy_options = ProxyOptions(
            proxy_type=mocker.MagicMock(),
            proxy_addr="127.0.0.1",
            proxy_port=8888,
            proxy_username=proxy_username,
        )

        assert proxy_options.proxy_username == proxy_username

    @pytest.mark.it(
        "Defaults the 'proxy_username' property to 'None' if the 'proxy_username' parameter is not provided"
    )
    def test_proxy_username_default(self, mocker):
        proxy_options = ProxyOptions(
            proxy_type=mocker.MagicMock(), proxy_addr="127.0.0.1", proxy_port=8888
        )
        assert proxy_options.proxy_username is None

    @pytest.mark.it("Maintains 'proxy_username' as a read-only property")
    def test_proxy_username_read_only(self, mocker):
        proxy_options = ProxyOptions(
            proxy_type=mocker.MagicMock(), proxy_addr="127.0.0.1", proxy_port=8888
        )
        with pytest.raises(AttributeError):
            proxy_options.proxy_username = "new value"

    @pytest.mark.it(
        "Instantiates with the 'proxy_password' property set to the value of the 'proxy_password' parameter, if provided"
    )
    def test_proxy_password(self, mocker):
        proxy_password = "fake_password"
        proxy_options = ProxyOptions(
            proxy_type=mocker.MagicMock(),
            proxy_addr="127.0.0.1",
            proxy_port=8888,
            proxy_password=proxy_password,
        )

        assert proxy_options.proxy_password == proxy_password

    @pytest.mark.it(
        "Defaults the 'proxy_password' property to 'None' if the 'proxy_password' parameter is not provided"
    )
    def test_proxy_password_default(self, mocker):
        proxy_options = ProxyOptions(
            proxy_type=mocker.MagicMock(), proxy_addr="127.0.0.1", proxy_port=8888
        )
        assert proxy_options.proxy_password is None

    @pytest.mark.it("Maintains 'proxy_password' as a read-only property")
    def test_proxy_password_read_only(self, mocker):
        proxy_options = ProxyOptions(
            proxy_type=mocker.MagicMock(), proxy_addr="127.0.0.1", proxy_port=8888
        )
        with pytest.raises(AttributeError):
            proxy_options.proxy_password = "new value"
