# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import pytest
import abc
import threading
from azure.iot.device import ProxyOptions
from azure.iot.device.common.pipeline.config import DEFAULT_KEEPALIVE


class PipelineConfigInstantiationTestBase(abc.ABC):
    """All PipelineConfig instantiation tests should inherit from this  base class.
    It provides tests for shared functionality among all PipelineConfigs, derived from
    the BasePipelineConfig class.
    """

    @abc.abstractmethod
    def config_cls(self):
        """This must be implemented in the child test class.
        It returns the child class under test"""
        pass

    @abc.abstractmethod
    def required_kwargs(self):
        """This must be implemented in the child test class.
        It returns required kwargs for the child class under test"""
        pass

    # PipelineConfig objects require exactly one auth mechanism, sastoken or x509.
    # For the sake of ease of testing, we will assume sastoken is being used unless
    # otherwise specified.
    # It does not matter which is used for the purposes of these tests.

    @pytest.fixture
    def sastoken(self, mocker):
        return mocker.MagicMock()

    @pytest.fixture
    def x509(self, mocker):
        return mocker.MagicMock()

    @pytest.mark.it(
        "Instantiates with the 'hostname' attribute set to the provided 'hostname' parameter"
    )
    def test_hostname_set(self, config_cls, required_kwargs, sastoken):
        # Hostname is one of the required kwargs, because it is required for the child
        config = config_cls(sastoken=sastoken, **required_kwargs)
        assert config.hostname == required_kwargs["hostname"]

    @pytest.mark.it(
        "Instantiates with the 'gateway_hostname' attribute set to the provided 'gateway_hostname' parameter"
    )
    def test_gateway_hostname_set(self, config_cls, required_kwargs, sastoken):
        fake_gateway_hostname = "gateway-hostname.some-domain.net"
        config = config_cls(
            sastoken=sastoken, gateway_hostname=fake_gateway_hostname, **required_kwargs
        )
        assert config.gateway_hostname == fake_gateway_hostname

    @pytest.mark.it(
        "Instantiates with the 'gateway_hostname' attribute set to 'None' if no 'gateway_hostname' parameter is provided"
    )
    def test_gateway_hostname_default(self, config_cls, required_kwargs, sastoken):
        config = config_cls(sastoken=sastoken, **required_kwargs)
        assert config.gateway_hostname is None

    @pytest.mark.it(
        "Instantiates with the 'keep_alive' attribute set to the provided 'keep_alive' parameter (converting the value to int)"
    )
    @pytest.mark.parametrize(
        "keep_alive",
        [
            pytest.param(1, id="int"),
            pytest.param(35.90, id="float"),
            pytest.param(0b1010, id="binary"),
            pytest.param(0x9, id="hexadecimal"),
            pytest.param("7", id="Numeric string"),
        ],
    )
    def test_keep_alive_valid_with_conversion(
        self, mocker, required_kwargs, config_cls, sastoken, keep_alive
    ):
        config = config_cls(sastoken=sastoken, keep_alive=keep_alive, **required_kwargs)
        assert config.keep_alive == int(keep_alive)

    @pytest.mark.it(
        "Instantiates with the 'keep_alive' attribute to 'None' if no 'keep_alive' parameter is provided"
    )
    def test_keep_alive_default(self, config_cls, required_kwargs, sastoken):
        config = config_cls(sastoken=sastoken, **required_kwargs)
        assert config.keep_alive == DEFAULT_KEEPALIVE

    @pytest.mark.it("Raises TypeError if the provided 'keep_alive' parameter is not numeric")
    @pytest.mark.parametrize(
        "keep_alive",
        [
            pytest.param("sectumsempra", id="non-numeric string"),
            pytest.param((1, 2), id="tuple"),
            pytest.param([1, 2], id="list"),
            pytest.param(object(), id="object"),
        ],
    )
    def test_keep_alive_invalid_type(self, config_cls, required_kwargs, sastoken, keep_alive):
        with pytest.raises(TypeError):
            config_cls(sastoken=sastoken, keep_alive=keep_alive, **required_kwargs)

    @pytest.mark.it("Raises ValueError if the provided 'keep_alive' parameter has an invalid value")
    @pytest.mark.parametrize(
        "keep_alive",
        [
            pytest.param(9876543210987654321098765432109876543210, id="> than max"),
            pytest.param(-2001, id="negative"),
            pytest.param(0, id="zero"),
        ],
    )
    def test_keep_alive_invalid_value(
        self, mocker, required_kwargs, config_cls, sastoken, keep_alive
    ):
        with pytest.raises(ValueError):
            config_cls(sastoken=sastoken, keep_alive=keep_alive, **required_kwargs)

    @pytest.mark.it(
        "Instantiates with the 'sastoken' attribute set to the provided 'sastoken' parameter"
    )
    def test_sastoken_set(self, config_cls, required_kwargs, sastoken):
        config = config_cls(sastoken=sastoken, **required_kwargs)
        assert config.sastoken is sastoken

    @pytest.mark.it(
        "Instantiates with the 'sastoken' attribute set to 'None' if no 'sastoken' parameter is provided"
    )
    def test_sastoken_default(self, config_cls, required_kwargs, x509):
        config = config_cls(x509=x509, **required_kwargs)
        assert config.sastoken is None

    @pytest.mark.it("Instantiates with the 'x509' attribute set to the provided 'x509' parameter")
    def test_x509_set(self, config_cls, required_kwargs, x509):
        config = config_cls(x509=x509, **required_kwargs)
        assert config.x509 is x509

    @pytest.mark.it(
        "Instantiates with the 'x509' attribute set to 'None' if no 'x509 parameter is provided"
    )
    def test_x509_default(self, config_cls, required_kwargs, sastoken):
        config = config_cls(sastoken=sastoken, **required_kwargs)
        assert config.x509 is None

    @pytest.mark.it(
        "Raises a ValueError if neither the 'sastoken' nor 'x509' parameter is provided"
    )
    def test_no_auths_provided(self, config_cls, required_kwargs):
        with pytest.raises(ValueError):
            config_cls(**required_kwargs)

    @pytest.mark.it("Raises a ValueError if both the 'sastoken' and 'x509' parameters are provided")
    def test_both_auths_provided(self, config_cls, required_kwargs, sastoken, x509):
        with pytest.raises(ValueError):
            config_cls(sastoken=sastoken, x509=x509, **required_kwargs)

    @pytest.mark.it(
        "Instantiates with the 'server_verification_cert' attribute set to the provided 'server_verification_cert' parameter"
    )
    def test_server_verification_cert_set(self, config_cls, required_kwargs, sastoken):
        svc = "fake_server_verification_cert"
        config = config_cls(sastoken=sastoken, server_verification_cert=svc, **required_kwargs)
        assert config.server_verification_cert == svc

    @pytest.mark.it(
        "Instantiates with the 'server_verification_cert' attribute set to 'None' if no 'server_verification_cert' parameter is provided"
    )
    def test_server_verification_cert_default(self, config_cls, required_kwargs, sastoken):
        config = config_cls(sastoken=sastoken, **required_kwargs)
        assert config.server_verification_cert is None

    @pytest.mark.it(
        "Instantiates with the 'websockets' attribute set to the provided 'websockets' parameter"
    )
    @pytest.mark.parametrize(
        "websockets", [True, False], ids=["websockets == True", "websockets == False"]
    )
    def test_websockets_set(self, config_cls, required_kwargs, sastoken, websockets):
        config = config_cls(sastoken=sastoken, websockets=websockets, **required_kwargs)
        assert config.websockets is websockets

    @pytest.mark.it(
        "Instantiates with the 'websockets' attribute to 'False' if no 'websockets' parameter is provided"
    )
    def test_websockets_default(self, config_cls, required_kwargs, sastoken):
        config = config_cls(sastoken=sastoken, **required_kwargs)
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
    def test_cipher(self, config_cls, required_kwargs, sastoken, cipher_input, expected_cipher):
        config = config_cls(sastoken=sastoken, cipher=cipher_input, **required_kwargs)
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
    def test_invalid_cipher_param(self, config_cls, required_kwargs, sastoken, cipher):
        with pytest.raises(TypeError):
            config_cls(sastoken=sastoken, cipher=cipher, **required_kwargs)

    @pytest.mark.it(
        "Instantiates with the 'cipher' attribute to empty string ('') if no 'cipher' parameter is provided"
    )
    def test_cipher_default(self, config_cls, required_kwargs, sastoken):
        config = config_cls(sastoken=sastoken, **required_kwargs)
        assert config.cipher == ""

    @pytest.mark.it(
        "Instantiates with the 'proxy_options' attribute set to the ProxyOptions object provided in the 'proxy_options' parameter"
    )
    def test_proxy_options(self, mocker, required_kwargs, config_cls, sastoken):
        proxy_options = ProxyOptions(proxy_type=1, proxy_addr="127.0.0.1", proxy_port=8888)
        config = config_cls(sastoken=sastoken, proxy_options=proxy_options, **required_kwargs)
        assert config.proxy_options is proxy_options

    @pytest.mark.it(
        "Instantiates with the 'proxy_options' attribute to 'None' if no 'proxy_options' parameter is provided"
    )
    def test_proxy_options_default(self, config_cls, required_kwargs, sastoken):
        config = config_cls(sastoken=sastoken, **required_kwargs)
        assert config.proxy_options is None

    @pytest.mark.it(
        "Instantiates with the 'auto_connect' attribute set to the provided 'auto_connect' parameter"
    )
    def test_auto_connect_set(self, config_cls, required_kwargs, sastoken):
        config = config_cls(sastoken=sastoken, auto_connect=False, **required_kwargs)
        assert config.auto_connect is False

    @pytest.mark.it(
        "Instantiates with the 'auto_connect' attribute set to 'None' if no 'auto_connect' parameter is provided"
    )
    def test_auto_connect_default(self, config_cls, required_kwargs, sastoken):
        config = config_cls(sastoken=sastoken, **required_kwargs)
        assert config.auto_connect is True

    @pytest.mark.it(
        "Instantiates with the 'connection_retry' attribute set to the provided 'connection_retry' parameter"
    )
    def test_connection_retry_set(self, config_cls, required_kwargs, sastoken):
        config = config_cls(sastoken=sastoken, connection_retry=False, **required_kwargs)
        assert config.connection_retry is False

    @pytest.mark.it(
        "Instantiates with the 'connection_retry' attribute set to 'True' if no 'connection_retry' parameter is provided"
    )
    def test_connection_retry_default(self, config_cls, required_kwargs, sastoken):
        config = config_cls(sastoken=sastoken, **required_kwargs)
        assert config.connection_retry is True

    @pytest.mark.it(
        "Instantiates with the 'connection_retry_interval' attribute set to the provided 'connection_retry_interval' parameter (converting the value to int)"
    )
    @pytest.mark.parametrize(
        "connection_retry_interval",
        [
            pytest.param(1, id="int"),
            pytest.param(35.90, id="float"),
            pytest.param(0b1010, id="binary"),
            pytest.param(0x9, id="hexadecimal"),
            pytest.param("7", id="Numeric string"),
        ],
    )
    def test_connection_retry_interval_set(
        self, connection_retry_interval, config_cls, required_kwargs, sastoken
    ):
        config = config_cls(
            sastoken=sastoken,
            connection_retry_interval=connection_retry_interval,
            **required_kwargs
        )
        assert config.connection_retry_interval == int(connection_retry_interval)

    @pytest.mark.it(
        "Instantiates with the 'connection_retry_interval' attribute set to 10 if no 'connection_retry_interval' parameter is provided"
    )
    def test_connection_retry_interval_default(self, config_cls, required_kwargs, sastoken):
        config = config_cls(sastoken=sastoken, **required_kwargs)
        assert config.connection_retry_interval == 10

    @pytest.mark.it(
        "Raises a TypeError if the provided 'connection_retry_interval' parameter is not numeric"
    )
    @pytest.mark.parametrize(
        "connection_retry_interval",
        [
            pytest.param("non-numeric-string", id="non-numeric string"),
            pytest.param((1, 2), id="tuple"),
            pytest.param([1, 2], id="list"),
            pytest.param(object(), id="object"),
        ],
    )
    def test_connection_retry_interval_invalid_type(
        self, config_cls, sastoken, required_kwargs, connection_retry_interval
    ):
        with pytest.raises(TypeError):
            config_cls(
                sastoken=sastoken,
                connection_retry_interval=connection_retry_interval,
                **required_kwargs
            )

    @pytest.mark.it(
        "Raises a ValueError if the provided 'connection_retry_interval' parameter has an invalid value"
    )
    @pytest.mark.parametrize(
        "connection_retry_interval",
        [
            pytest.param(threading.TIMEOUT_MAX + 1, id="> than max"),
            pytest.param(-1, id="negative"),
            pytest.param(0, id="zero"),
        ],
    )
    def test_connection_retry_interval_invalid_value(
        self, config_cls, sastoken, required_kwargs, connection_retry_interval
    ):
        with pytest.raises(ValueError):
            config_cls(
                sastoken=sastoken,
                connection_retry_interval=connection_retry_interval,
                **required_kwargs
            )
