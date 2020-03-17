# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import pytest
from azure.iot.device import ProxyOptions


class PipelineConfigInstantiationTestBase(object):
    """All PipelineConfig instantiation tests should inherit from this  base class.
    It provides tests for shared functionality among all PipelineConfigs, derived from
    the BasePipelineConfig class.
    """

    @pytest.mark.it(
        "Instantiates with the 'websockets' attribute set to the provided 'websockets' parameter"
    )
    @pytest.mark.parametrize(
        "websockets", [True, False], ids=["websockets == True", "websockets == False"]
    )
    def test_websockets_set(self, config_cls, websockets):
        config = config_cls(websockets=websockets)
        assert config.websockets is websockets

    @pytest.mark.it(
        "Instantiates with the 'websockets' attribute to 'False' if no 'websockets' parameter is provided"
    )
    def test_websockets_default(self, config_cls):
        config = config_cls()
        assert config.websockets is False

    @pytest.mark.it(
        "Instantiates with the 'cipher' attribute set to OpenSSL list formatted version of the provided 'cipher' parameter"
    )
    @pytest.mark.parametrize(
        "cipher_input, expected_cipher",
        [
            pytest.param(
                "DHE-RSA-AES128-SHA",
                "DHE-RSA-AES128-SHA",
                id="Single cipher suite, OpenSSL list formatted string",
            ),
            pytest.param(
                "DHE-RSA-AES128-SHA:DHE-RSA-AES256-SHA:ECDHE-ECDSA-AES128-GCM-SHA256",
                "DHE-RSA-AES128-SHA:DHE-RSA-AES256-SHA:ECDHE-ECDSA-AES128-GCM-SHA256",
                id="Multiple cipher suites, OpenSSL list formatted string",
            ),
            pytest.param(
                "DHE_RSA_AES128_SHA",
                "DHE-RSA-AES128-SHA",
                id="Single cipher suite, as string with '_' delimited algorithms/protocols",
            ),
            pytest.param(
                "DHE_RSA_AES128_SHA:DHE_RSA_AES256_SHA:ECDHE_ECDSA_AES128_GCM_SHA256",
                "DHE-RSA-AES128-SHA:DHE-RSA-AES256-SHA:ECDHE-ECDSA-AES128-GCM-SHA256",
                id="Multiple cipher suites, as string with '_' delimited algorithms/protocols and ':' delimited suites",
            ),
            pytest.param(
                ["DHE-RSA-AES128-SHA"],
                "DHE-RSA-AES128-SHA",
                id="Single cipher suite, in a list, with '-' delimited algorithms/protocols",
            ),
            pytest.param(
                ["DHE-RSA-AES128-SHA", "DHE-RSA-AES256-SHA", "ECDHE-ECDSA-AES128-GCM-SHA256"],
                "DHE-RSA-AES128-SHA:DHE-RSA-AES256-SHA:ECDHE-ECDSA-AES128-GCM-SHA256",
                id="Multiple cipher suites, in a list, with '-' delimited algorithms/protocols",
            ),
            pytest.param(
                ["DHE_RSA_AES128_SHA"],
                "DHE-RSA-AES128-SHA",
                id="Single cipher suite, in a list, with '_' delimited algorithms/protocols",
            ),
            pytest.param(
                ["DHE_RSA_AES128_SHA", "DHE_RSA_AES256_SHA", "ECDHE_ECDSA_AES128_GCM_SHA256"],
                "DHE-RSA-AES128-SHA:DHE-RSA-AES256-SHA:ECDHE-ECDSA-AES128-GCM-SHA256",
                id="Multiple cipher suites, in a list, with '_' delimited algorithms/protocols",
            ),
        ],
    )
    def test_cipher(self, config_cls, cipher_input, expected_cipher):
        config = config_cls(cipher=cipher_input)
        assert config.cipher == expected_cipher

    @pytest.mark.it(
        "Raises TypeError if the provided 'cipher' attribute is neither list nor string"
    )
    @pytest.mark.parametrize(
        "cipher",
        [
            pytest.param(123, id="int"),
            pytest.param(
                {"cipher1": "DHE-RSA-AES128-SHA", "cipher2": "DHE_RSA_AES256_SHA"}, id="dict"
            ),
            pytest.param(object(), id="complex object"),
        ],
    )
    def test_invalid_cipher_param(self, config_cls, cipher):
        with pytest.raises(TypeError):
            config_cls(cipher=cipher)

    @pytest.mark.it(
        "Instantiates with the 'cipher' attribute to empty string ('') if no 'cipher' parameter is provided"
    )
    def test_cipher_default(self, config_cls):
        config = config_cls()
        assert config.cipher == ""

    @pytest.mark.it(
        "Instantiates with the 'proxy_options' attribute set to the ProxyOptions object provided in the 'proxy_options' parameter"
    )
    def test_proxy_options(self, mocker, config_cls):
        proxy_options = ProxyOptions(
            proxy_type=mocker.MagicMock(), proxy_addr="127.0.0.1", proxy_port=8888
        )
        config = config_cls(proxy_options=proxy_options)
        assert config.proxy_options is proxy_options

    @pytest.mark.it(
        "Instantiates with the 'proxy_options' attribute to 'None' if no 'proxy_options' parameter is provided"
    )
    def test_proxy_options_default(self, config_cls):
        config = config_cls()
        assert config.proxy_options is None
