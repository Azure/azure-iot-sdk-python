# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import pytest
import ssl
import time
from pytest_lazyfixture import lazy_fixture
from v3_async_wip.iothub_client import IoTHubDeviceClient, IoTHubModuleClient
from v3_async_wip import config
from v3_async_wip import iothub_mqtt_client as mqtt
from v3_async_wip import iothub_http_client as http
from v3_async_wip import sastoken as st
from v3_async_wip import signing_mechanism as sm

FAKE_DEVICE_ID = "fake_device_id"
FAKE_MODULE_ID = "fake_module_id"
FAKE_HOSTNAME = "fake.hostname"
FAKE_URI = "fake/resource/location"
FAKE_SYMMETRIC_KEY = "Zm9vYmFy"
FAKE_SIGNATURE = "ajsc8nLKacIjGsYyB4iYDFCZaRMmmDrUuY5lncYDYPI="


def sastoken_generator_fn():
    return "SharedAccessSignature sr={resource}&sig={signature}&se={expiry}".format(
        resource=FAKE_URI, signature=FAKE_SIGNATURE, expiry=str(int(time.time()) + 3600)
    )


# ~~~~~ Fixtures ~~~~~~

# Mock out the underlying clients to avoid starting up tasks that will reduce performance
@pytest.fixture(autouse=True)
def mock_mqtt_iothub_client(mocker):
    return mocker.patch.object(mqtt, "IoTHubMQTTClient", spec=mqtt.IoTHubMQTTClient).return_value


@pytest.fixture(autouse=True)
def mock_http_iothub_client(mocker):
    return mocker.patch.object(http, "IoTHubHTTPClient", spec=http.IoTHubHTTPClient).return_value


# Mock out the SasTokenProvider to avoid starting up tasks that will reduce performance
@pytest.fixture(autouse=True)
def mock_sastoken_provider(mocker):
    return mocker.patch.object(st, "SasTokenProvider", spec=st.SasTokenProvider).return_value


@pytest.fixture
def ssl_context():
    # NOTE: It doesn't matter how the SSLContext is configured for the tests that use this fixture,
    # so it isn't configured at all.
    return ssl.SSLContext()


@pytest.fixture(params=["Default SSLContext", "Custom SSLContext"])
def var_ssl_context(request):
    # TODO: try and find an elegant way to reduce the ssl fixtures and complexity
    if request.param == "Custom SSLContext":
        return ssl.SSLContext()
    else:
        return None


# ~~~~~ Parametrizations ~~~~~
auth_args = [
    # Provide args in form 'symmetric_key, sastoken_fn, ssl_ctx'
    pytest.param(
        FAKE_SYMMETRIC_KEY, None, None, id="Symmetric Key Authorization + Default SSLContext"
    ),
    pytest.param(
        FAKE_SYMMETRIC_KEY,
        None,
        lazy_fixture("ssl_context"),
        id="Symmetric Key Authorization + Custom SSLContext",
    ),
    pytest.param(
        None,
        sastoken_generator_fn,
        None,
        id="User-Provided SAS Token Authorization + Default SSLContext",
    ),
    pytest.param(
        None,
        sastoken_generator_fn,
        lazy_fixture("ssl_context"),
        id="User-Provided SAS Token Authorization + Custom SSLContext",
    ),
    pytest.param(None, None, lazy_fixture("ssl_context"), id="X509 Authorization"),
    # NOTE: X509 implies use of Custom SSLContext, so no extra configuration for X509 + Custom SSLContext.
    # Default SSLContext is invalid for use with X509
]


class SharedClientInstantiationTests:
    """Defines shared tests for instantiation of Device/Module clients"""

    @pytest.fixture
    def client_config(self, ssl_context):
        # NOTE: It really doesn't matter whether or not this has a module_id for the purposes
        # of these tests, so don't make this more complicated than it needs to be.
        return config.IoTHubClientConfig(
            device_id=FAKE_DEVICE_ID, hostname=FAKE_HOSTNAME, ssl_context=ssl_context
        )

    @pytest.mark.it(
        "Instantiates and stores an IoTHubMQTTClient from the provided IoTHubClientConfig"
    )
    async def test_mqtt_client(self, mocker, client_class, client_config):
        assert mqtt.IoTHubMQTTClient.call_count == 0

        client = client_class(client_config)

        assert client._mqtt_client is mqtt.IoTHubMQTTClient.return_value
        assert mqtt.IoTHubMQTTClient.call_count == 1
        assert mqtt.IoTHubMQTTClient.call_args == mocker.call(client_config)

        await client.shutdown()

    @pytest.mark.it(
        "Instantiates and stores an IoTHubHTTPClient from the provided IoTHubClientConfig"
    )
    async def test_http_client(self, mocker, client_class, client_config):
        assert http.IoTHubHTTPClient.call_count == 0

        client = client_class(client_config)

        assert client._http_client is http.IoTHubHTTPClient.return_value
        assert http.IoTHubHTTPClient.call_count == 1
        assert http.IoTHubHTTPClient.call_args == mocker.call(client_config)

        await client.shutdown()


class SharedClientShutdownTests:
    """Defines shared tests for Device/Module client .shutdown() method"""

    @pytest.mark.it("Shuts down the IoTHubMQTTClient")
    async def test_mqtt_shutdown(self, client):
        assert client._mqtt_client.shutdown.await_count == 0

        await client.shutdown()

        assert client._mqtt_client.shutdown.await_count == 1

    @pytest.mark.it("Shuts down the IoTHubHTTPClient")
    async def test_http_shutdown(self, client):
        assert client._http_client.shutdown.await_count == 0

        await client.shutdown()

        assert client._http_client.shutdown.await_count == 1

    @pytest.mark.it("Shuts down SasTokenProvider (if present)")
    async def test_sastoken_provider_shutdown(self, client):
        pass

    # TODO: cancel tests


# ~~~~~ IoTHubDeviceClientTests ~~~~~


class IoTHubDeviceClientTestConfig:
    """Mixin parent class defining a set of fixtures used in IoTHubDeviceClient tests"""

    @pytest.fixture
    async def client(self, ssl_context):
        client_config = config.IoTHubClientConfig(
            device_id=FAKE_DEVICE_ID, hostname=FAKE_HOSTNAME, ssl_context=ssl_context
        )
        client = IoTHubDeviceClient(client_config)
        yield client
        await client.shutdown()


@pytest.mark.describe("IoTHubDeviceClient -- Instantiation")
class TestIoTHubDeviceClientInstantiation(
    SharedClientInstantiationTests, IoTHubDeviceClientTestConfig
):
    @pytest.fixture
    def client_class(self):
        return IoTHubDeviceClient


@pytest.mark.describe("IoTHubDeviceClient - .create()")
class TestIoTHubDeviceClientCreate(IoTHubDeviceClientTestConfig):
    @pytest.mark.it(
        "Returns a new IoTHubDeviceClient instance, created with use of a new IoTHubClientConfig object"
    )
    @pytest.mark.parametrize("symmetric_key, sastoken_fn, ssl_ctx", auth_args)
    async def test_instantiation(self, mocker, symmetric_key, sastoken_fn, ssl_ctx):
        spy_config_cls = mocker.spy(config, "IoTHubClientConfig")
        spy_client_init = mocker.spy(IoTHubDeviceClient, "__init__")
        assert spy_config_cls.call_count == 0
        assert spy_client_init.call_count == 0

        client = await IoTHubDeviceClient.create(
            device_id=FAKE_DEVICE_ID,
            hostname=FAKE_HOSTNAME,
            symmetric_key=symmetric_key,
            sastoken_fn=sastoken_fn,
            ssl_context=ssl_ctx,
        )

        assert spy_config_cls.call_count == 1
        assert spy_client_init.call_count == 1
        # NOTE: Normally passing through self or cls isn't necessary in a mock call, but
        # it seems that when mocking the __init__ it is. This is actually good though, as it
        # allows us to match the specific object reference which otherwise is very dicey when
        # mocking constructors/initializers
        assert spy_client_init.call_args == mocker.call(client, spy_config_cls.spy_return)
        assert isinstance(client, IoTHubDeviceClient)

        # Graceful exit
        await client.shutdown()

    @pytest.mark.it(
        "Creates a SasTokenProvider that uses symmetric key-based token generation and sets it on the IoTHubClientConfig, if `symmetric_key` is provided as a parameter"
    )
    async def test_sk_auth(self, mocker, var_ssl_context):
        spy_client_init = mocker.spy(IoTHubDeviceClient, "__init__")
        spy_sk_sm_cls = mocker.spy(sm, "SymmetricKeySigningMechanism")
        spy_st_generator_cls = mocker.spy(st, "InternalSasTokenGenerator")
        spy_st_provider_create = mocker.spy(st.SasTokenProvider, "create_from_generator")
        expected_token_uri = "{hostname}/devices/{device_id}".format(
            hostname=FAKE_HOSTNAME, device_id=FAKE_DEVICE_ID
        )

        client = await IoTHubDeviceClient.create(
            device_id=FAKE_DEVICE_ID,
            hostname=FAKE_HOSTNAME,
            symmetric_key=FAKE_SYMMETRIC_KEY,
            ssl_context=var_ssl_context,
        )

        # SymmetricKeySigningMechanism was created from the symmetric key
        assert spy_sk_sm_cls.call_count == 1
        assert spy_sk_sm_cls.call_args == mocker.call(FAKE_SYMMETRIC_KEY)
        # InternalSasTokenGenerator was created from the SymmetricKeySigningMechanism and expected URI
        assert spy_st_generator_cls.call_count == 1
        assert spy_st_generator_cls.call_args == mocker.call(
            signing_mechanism=spy_sk_sm_cls.spy_return, uri=expected_token_uri
        )
        # SasTokenProvider was created from the InternalSasTokenGenerator
        assert spy_st_provider_create.call_count == 1
        assert spy_st_provider_create.call_args == mocker.call(spy_st_generator_cls.spy_return)
        # The SasTokenProvider was set on the IoTHubClientConfig that was used to instantiate the client
        assert spy_client_init.call_count == 1
        config = spy_client_init.call_args[0][1]
        assert config.sastoken_provider is spy_st_provider_create.spy_return

        # Graceful exit
        await client.shutdown()

    @pytest.mark.it(
        "Creates a SasTokenProvider that uses user callback-based token generation and sets it on the IoTHubClientConfig, if `sastoken_fn` is provided as a parameter"
    )
    async def test_token_callback_auth(self, mocker, var_ssl_context):
        spy_client_init = mocker.spy(IoTHubDeviceClient, "__init__")
        spy_st_generator_cls = mocker.spy(st, "ExternalSasTokenGenerator")
        spy_st_provider_create = mocker.spy(st.SasTokenProvider, "create_from_generator")

        client = await IoTHubDeviceClient.create(
            device_id=FAKE_DEVICE_ID,
            hostname=FAKE_HOSTNAME,
            sastoken_fn=sastoken_generator_fn,
            ssl_context=var_ssl_context,
        )

        # ExternalSasTokenGenerator was created from the `sastoken_fn``
        assert spy_st_generator_cls.call_count == 1
        assert spy_st_generator_cls.call_args == mocker.call(sastoken_generator_fn)
        # SasTokenProvider was created from the ExternalSasTokenGenerator
        assert spy_st_provider_create.call_count == 1
        assert spy_st_provider_create.call_args == mocker.call(spy_st_generator_cls.spy_return)
        # The SasTokenProvider was set on the IoTHubClientConfig that was used to instantiate the client
        assert spy_client_init.call_count == 1
        config = spy_client_init.call_args[0][1]
        assert config.sastoken_provider is spy_st_provider_create.spy_return

        # Graceful exit
        await client.shutdown()

    @pytest.mark.it(
        "Does not set any SasTokenProvider on the IoTHubClientConfig if neither `symmetric_key` nor `sastoken_fn` are provided as parameters"
    )
    async def test_non_sas_auth(self, mocker, ssl_context):
        spy_client_init = mocker.spy(IoTHubDeviceClient, "__init__")

        client = await IoTHubDeviceClient.create(
            device_id=FAKE_DEVICE_ID,
            hostname=FAKE_HOSTNAME,
            ssl_context=ssl_context,
        )

        # No SasTokenProvider was set on the IoTHubClientConfig that was used to instantiate the client
        assert spy_client_init.call_count == 1
        config = spy_client_init.call_args[0][1]
        assert config.sastoken_provider is None

        # Graceful exit
        await client.shutdown()


@pytest.mark.describe("IoTHubDeviceClient - .shutdown()")
class TestIoTHubDeviceClientShutdown(SharedClientShutdownTests, IoTHubDeviceClientTestConfig):
    pass


# ~~~~~ IoTHubModuleClientTests ~~~~~


class IoTHubModuleClientTestConfig:
    """Mixin parent class defining a set of fixtures used in IoTHubModuleClient tests"""

    @pytest.fixture
    async def client(self, ssl_context):
        client_config = config.IoTHubClientConfig(
            device_id=FAKE_DEVICE_ID,
            module_id=FAKE_MODULE_ID,
            hostname=FAKE_HOSTNAME,
            ssl_context=ssl_context,
        )
        client = IoTHubDeviceClient(client_config)
        yield client
        await client.shutdown()


@pytest.mark.describe("IoTHubModuleClient -- Instantiation")
class TestIoTHubModuleClientInstantiation(
    SharedClientInstantiationTests, IoTHubModuleClientTestConfig
):
    @pytest.fixture
    def client_class(self):
        return IoTHubModuleClient


@pytest.mark.describe("IoTHubModuleClient - .shutdown()")
class TestIoTHubModuleClientShutdown(SharedClientShutdownTests, IoTHubModuleClientTestConfig):
    pass
