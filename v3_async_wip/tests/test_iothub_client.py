# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import asyncio
import os
import pytest
import ssl
import time
from dev_utils import custom_mock
from pytest_lazyfixture import lazy_fixture
from v3_async_wip.iothub_client import IoTHubDeviceClient, IoTHubModuleClient
from v3_async_wip import config, edge_hsm, iothub_client, iot_exceptions
from v3_async_wip import connection_string as cs
from v3_async_wip import iothub_mqtt_client as mqtt
from v3_async_wip import iothub_http_client as http
from v3_async_wip import sastoken as st
from v3_async_wip import signing_mechanism as sm

FAKE_DEVICE_ID = "fake_device_id"
FAKE_MODULE_ID = "fake_module_id"
FAKE_HOSTNAME = "fake.hostname"
FAKE_GATEWAY_HOSTNAME = "fake.gateway.hostname"
FAKE_URI = "fake/resource/location"
FAKE_SYMMETRIC_KEY = "Zm9vYmFy"
FAKE_SIGNATURE = "ajsc8nLKacIjGsYyB4iYDFCZaRMmmDrUuY5lncYDYPI="


# NOTE: HELPFUL INFORMATION ABOUT NAVIGATING THIS FILE
# This is a very long test file. Lots going on in here. To help navigate, there are headings for
# various sections. You can use the search feature of your IDE to jump to these headings:
#
#   - Shared Client Tests
#   - IoTHubDeviceClient Tests
#   - IoTHubModuleClient Tests


# ~~~~~ Helpers ~~~~~~


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


@pytest.fixture(autouse=True)
def mock_sastoken_provider(mocker):
    return mocker.patch.object(st, "SasTokenProvider", spec=st.SasTokenProvider).return_value


@pytest.fixture
def custom_ssl_context():
    # NOTE: It doesn't matter how the SSLContext is configured for the tests that use this fixture,
    # so it isn't configured at all.
    return ssl.SSLContext()


@pytest.fixture(params=["Default SSLContext", "Custom SSLContext"])
def optional_ssl_context(request, custom_ssl_context):
    """Sometimes tests need to show something works with or without an SSLContext"""
    if request.param == "Custom SSLContext":
        return custom_ssl_context
    else:
        return None


# ~~~~~ Parametrizations ~~~~~
# Define parametrizations that will be used across multiple test suites, and that may eventually
# need to be changed everywhere, e.g. new auth scheme added.
# Note that some parametrizations are also defined within the scope of a single test suite if that
# is the only unit they are relevant to.


# Parameters for arguments to the .create() method of clients. Represent different types of
# authentication. Use this parametrization whenever possible on .create() tests.
# NOTE: Do NOT combine this with the SSL fixtures above. This parametrization contains
# ssl contexts where necessary
create_auth_params = [
    # Provide args in form 'symmetric_key, sastoken_fn, ssl_context'
    pytest.param(FAKE_SYMMETRIC_KEY, None, None, id="Symmetric Key SAS Auth + Default SSLContext"),
    pytest.param(
        FAKE_SYMMETRIC_KEY,
        None,
        lazy_fixture("custom_ssl_context"),
        id="Symmetric Key SAS Auth + Custom SSLContext",
    ),
    pytest.param(
        None,
        sastoken_generator_fn,
        None,
        id="User-Provided SAS Token Auth + Default SSLContext",
    ),
    pytest.param(
        None,
        sastoken_generator_fn,
        lazy_fixture("custom_ssl_context"),
        id="User-Provided SAS Token Auth + Custom SSLContext",
    ),
    pytest.param(None, None, lazy_fixture("custom_ssl_context"), id="Custom SSLContext Auth"),
]
# Just the parameters where SAS auth is used
create_auth_params_sas = [param for param in create_auth_params if "SAS" in param.id]
# Just the parameters where a Symmetric Key auth is used
create_auth_params_sk = [param for param in create_auth_params if param.values[0] is not None]
# Just the parameters where SAS callback auth is used
create_auth_params_token_cb = [param for param in create_auth_params if param.values[1] is not None]
# Just the parameters where a custom SSLContext is provided
create_auth_params_custom_ssl = [
    param for param in create_auth_params if param.values[2] is not None
]
# Just the parameters where a custom SSLContext is NOT provided
create_auth_params_default_ssl = [param for param in create_auth_params if param.values[2] is None]


# Covers all option kwargs shared across client factory methods
factory_kwargs = [
    pytest.param("auto_reconnect", False, id="auto_reconnect"),
    pytest.param("keep_alive", 34, id="keep_alive"),
    pytest.param("product_info", "fake-product-info", id="product_info"),
    pytest.param(
        "proxy_options", config.ProxyOptions("HTTP", "fake.address", 1080), id="proxy_options"
    ),
    pytest.param("websockets", True, id="websockets"),
]

sastoken_provider_create_exceptions = [
    pytest.param(st.SasTokenError(), id="SasTokenError"),
    pytest.param(lazy_fixture("arbitrary_exception"), id="Unexpected Exception"),
]

sk_sm_create_exceptions = [
    pytest.param(ValueError(), id="ValueError"),
    pytest.param(lazy_fixture("arbitrary_exception"), id="Unexpected Exception"),
]


# ~~~~~ Shared Client Tests ~~~~~~
# Many methods are the same between an IoTHubDeviceClient and an IoTHubModuleClient.
# For those tests, write a single suite, that can use generic fixtures, and then
# inherit the generic suite class into a child suite class that provides specific
# versions of those fixtures.
# Only do this if the tests are identical aside from client class - if there are
# distinctions, even if minor, just write two separate suites - it is not worth the
# trouble.


class SharedClientInstantiationTests:
    """Defines shared tests for instantiation of Device/Module clients"""

    @pytest.fixture
    def client_config(self, custom_ssl_context):
        # NOTE: It really doesn't matter whether or not this has a module_id for the purposes
        # of these tests, so don't make this more complicated than it needs to be.
        return config.IoTHubClientConfig(
            device_id=FAKE_DEVICE_ID, hostname=FAKE_HOSTNAME, ssl_context=custom_ssl_context
        )

    @pytest.mark.it(
        "Instantiates and stores an IoTHubMQTTClient using the provided IoTHubClientConfig"
    )
    async def test_mqtt_client(self, mocker, client_class, client_config):
        assert mqtt.IoTHubMQTTClient.call_count == 0

        client = client_class(client_config)

        assert client._mqtt_client is mqtt.IoTHubMQTTClient.return_value
        assert mqtt.IoTHubMQTTClient.call_count == 1
        assert mqtt.IoTHubMQTTClient.call_args == mocker.call(client_config)

        await client.shutdown()

    @pytest.mark.it(
        "Instantiates and stores an IoTHubHTTPClient using the provided IoTHubClientConfig"
    )
    async def test_http_client(self, mocker, client_class, client_config):
        assert http.IoTHubHTTPClient.call_count == 0

        client = client_class(client_config)

        assert client._http_client is http.IoTHubHTTPClient.return_value
        assert http.IoTHubHTTPClient.call_count == 1
        assert http.IoTHubHTTPClient.call_args == mocker.call(client_config)

        await client.shutdown()

    @pytest.mark.it("Stores the IoTHubClientConfig's `sastoken_provider`, if it exists")
    async def test_sastoken_provider(self, client_class, client_config, mock_sastoken_provider):
        client_config.sastoken_provider = mock_sastoken_provider

        client = client_class(client_config)

        assert client._sastoken_provider is mock_sastoken_provider

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

    @pytest.mark.it("Shuts down the SasTokenProvider, if present")
    async def test_sastoken_provider_shutdown(self, mocker, client, mock_sastoken_provider):
        # Add the mock sastoken provider since it isn't there by default
        assert client._sastoken_provider is None
        client._sastoken_provider = mock_sastoken_provider
        assert mock_sastoken_provider.shutdown.await_count == 0

        await client.shutdown()

        assert mock_sastoken_provider.shutdown.await_count == 1
        assert mock_sastoken_provider.shutdown.await_args == mocker.call()

    @pytest.mark.it("Handles the case where no SasTokenProvider is present")
    async def test_no_sastoken_provider(self, client):
        assert client._sastoken_provider is None

        await client.shutdown()

        # If no error was raised, this test passes

    @pytest.mark.it(
        "Allows any exception raised during IoTHubMQTTClient shutdown to propagate, but only after completing the rest of the shutdown procedure"
    )
    @pytest.mark.parametrize(
        "sastoken_provider",
        [
            pytest.param(lazy_fixture("mock_sastoken_provider"), id="W/ SasTokenProvider"),
            pytest.param(None, id="No SasTokenProvider"),
        ],
    )
    async def test_mqtt_client_raises(self, client, sastoken_provider, arbitrary_exception):
        client._sastoken_provider = sastoken_provider
        assert client._mqtt_client.shutdown.await_count == 0
        assert client._http_client.shutdown.await_count == 0
        if sastoken_provider:
            assert client._sastoken_provider.shutdown.await_count == 0

        # MQTT shutdown will raise
        client._mqtt_client.shutdown.side_effect = arbitrary_exception
        try:
            # MQTT shutdown error propagates
            with pytest.raises(type(arbitrary_exception)) as e_info:
                await client.shutdown()
            assert e_info.value is arbitrary_exception

            # But the whole shutdown protocol was executed
            assert client._mqtt_client.shutdown.await_count == 1
            assert client._http_client.shutdown.await_count == 1
            if sastoken_provider:
                assert client._sastoken_provider.shutdown.await_count == 1
        finally:
            # Unset the the MQTT shutdown failure so teardown doesn't crash
            client._mqtt_client.shutdown.side_effect = None

    @pytest.mark.it(
        "Allows any exception raised during IoTHubHTTPClient shutdown to propagate, but only after completing the rest of the shutdown procedure"
    )
    @pytest.mark.parametrize(
        "sastoken_provider",
        [
            pytest.param(lazy_fixture("mock_sastoken_provider"), id="W/ SasTokenProvider"),
            pytest.param(None, id="No SasTokenProvider"),
        ],
    )
    async def test_http_client_raises(self, client, sastoken_provider, arbitrary_exception):
        client._sastoken_provider = sastoken_provider
        assert client._mqtt_client.shutdown.await_count == 0
        assert client._http_client.shutdown.await_count == 0
        if sastoken_provider:
            assert client._sastoken_provider.shutdown.await_count == 0

        # HTTP shutdown will raise
        client._http_client.shutdown.side_effect = arbitrary_exception

        try:
            # HTTP shutdown error propagates
            with pytest.raises(type(arbitrary_exception)) as e_info:
                await client.shutdown()
            assert e_info.value is arbitrary_exception

            # But the whole shutdown protocol was executed
            assert client._mqtt_client.shutdown.await_count == 1
            assert client._http_client.shutdown.await_count == 1
            if sastoken_provider:
                assert client._sastoken_provider.shutdown.await_count == 1
        finally:
            # Unset the the HTTP shutdown failure so teardown doesn't crash
            client._http_client.shutdown.side_effect = None

    @pytest.mark.it(
        "Allows any exception raised during SasTokenProvider shutdown to propagate, but only after completing the rest of the shutdown procedure"
    )
    async def test_sastoken_provider_raises(
        self, client, mock_sastoken_provider, arbitrary_exception
    ):
        client._sastoken_provider = mock_sastoken_provider
        assert client._mqtt_client.shutdown.await_count == 0
        assert client._http_client.shutdown.await_count == 0
        assert client._sastoken_provider.shutdown.await_count == 0

        # SasTokenProvider shutdown will raise
        client._sastoken_provider.shutdown.side_effect = arbitrary_exception

        try:
            # SasTokenProvider shutdown error propagates
            with pytest.raises(type(arbitrary_exception)) as e_info:
                await client.shutdown()
            assert e_info.value is arbitrary_exception

            # But the whole shutdown protocol was executed
            assert client._mqtt_client.shutdown.await_count == 1
            assert client._http_client.shutdown.await_count == 1
            assert client._sastoken_provider.shutdown.await_count == 1
        finally:
            # Unset the the SasTokenProvider shutdown failure so teardown doesn't crash
            client._sastoken_provider.shutdown.side_effect = None

    @pytest.mark.it(
        "Can be cancelled during IoTHubMQTTClient shutdown, but shutdown procedure will still complete"
    )
    @pytest.mark.parametrize(
        "sastoken_provider",
        [
            pytest.param(lazy_fixture("mock_sastoken_provider"), id="W/ SasTokenProvider"),
            pytest.param(None, id="No SasTokenProvider"),
        ],
    )
    async def test_cancel_mqtt_client(self, client, sastoken_provider):
        client._sastoken_provider = sastoken_provider
        assert client._mqtt_client.shutdown.await_count == 0
        assert client._http_client.shutdown.await_count == 0
        if sastoken_provider:
            assert client._sastoken_provider.shutdown.await_count == 0

        # MQTT shutdown will hang
        original_shutdown = client._mqtt_client.shutdown
        client._mqtt_client.shutdown = custom_mock.HangingAsyncMock()

        try:
            # Attempt to shutdown will hang
            t = asyncio.create_task(client.shutdown())
            await client._mqtt_client.shutdown.wait_for_hang()
            assert not t.done()

            # Shutdown can be cancelled
            t.cancel()
            with pytest.raises(asyncio.CancelledError):
                await t

            # But the whole shutdown protocol was still executed
            assert client._mqtt_client.shutdown.await_count == 1
            assert client._http_client.shutdown.await_count == 1
            if sastoken_provider:
                assert client._sastoken_provider.shutdown.await_count == 1

            # TODO: This test doesn't actually prove that the shutdowns of the various
            # components actually complete. Fix that, if we decide to ship this client.

        finally:
            # Since this task was protected from cancellation, we have to manually stop the hang
            client._mqtt_client.shutdown.stop_hanging()
            # Unset the the MQTT shutdown hang so teardown doesn't hang
            client._mqtt_client.shutdown = original_shutdown

    @pytest.mark.it(
        "Can be cancelled during IoTHubHTTPClient shutdown, but shutdown procedure will still complete"
    )
    @pytest.mark.parametrize(
        "sastoken_provider",
        [
            pytest.param(lazy_fixture("mock_sastoken_provider"), id="W/ SasTokenProvider"),
            pytest.param(None, id="No SasTokenProvider"),
        ],
    )
    async def test_cancel_http_client(self, client, sastoken_provider):
        client._sastoken_provider = sastoken_provider
        assert client._mqtt_client.shutdown.await_count == 0
        assert client._http_client.shutdown.await_count == 0
        if sastoken_provider:
            assert client._sastoken_provider.shutdown.await_count == 0

        # HTTP shutdown will hang
        original_shutdown = client._http_client.shutdown
        client._http_client.shutdown = custom_mock.HangingAsyncMock()

        try:
            # Attempt to shutdown will hang
            t = asyncio.create_task(client.shutdown())
            await client._http_client.shutdown.wait_for_hang()
            assert not t.done()

            # Shutdown can be cancelled
            t.cancel()
            with pytest.raises(asyncio.CancelledError):
                await t

            # But the whole shutdown protocol was still executed
            assert client._mqtt_client.shutdown.await_count == 1
            assert client._http_client.shutdown.await_count == 1
            if sastoken_provider:
                assert client._sastoken_provider.shutdown.await_count == 1

            # TODO: This test doesn't actually prove that the shutdowns of the various
            # components actually complete. Fix that, if we decide to ship this client.

        finally:
            # Since this task was protected from cancellation, we have to manually stop the hang
            client._http_client.shutdown.stop_hanging()
            # Unset the the HTTP shutdown hang so teardown doesn't hang
            client._http_client.shutdown = original_shutdown

    @pytest.mark.it(
        "Can be cancelled during SasTokenProvider shutdown, but shutdown procedure will still complete"
    )
    async def test_cancel_sastoken_provider(self, client, mock_sastoken_provider):
        client._sastoken_provider = mock_sastoken_provider
        assert client._mqtt_client.shutdown.await_count == 0
        assert client._http_client.shutdown.await_count == 0
        assert client._sastoken_provider.shutdown.await_count == 0

        # SasTokenProvider shutdown will hang
        original_shutdown = client._sastoken_provider.shutdown
        client._sastoken_provider.shutdown = custom_mock.HangingAsyncMock()

        try:
            # Attempt to shutdown will hang
            t = asyncio.create_task(client.shutdown())
            await client._sastoken_provider.shutdown.wait_for_hang()
            assert not t.done()

            # Shutdown can be cancelled
            t.cancel()
            with pytest.raises(asyncio.CancelledError):
                await t

            # But the whole shutdown protocol was still executed
            assert client._mqtt_client.shutdown.await_count == 1
            assert client._http_client.shutdown.await_count == 1
            assert client._sastoken_provider.shutdown.await_count == 1

            # TODO: This test doesn't actually prove that the shutdowns of the various
            # components actually complete. Fix that, if we decide to ship this client.

        finally:
            # Since this task was protected from cancellation, we have to manually stop the hang
            client._sastoken_provider.shutdown.stop_hanging()
            # Unset the the HTTP shutdown hang so teardown doesn't hang
            client._sastoken_provider.shutdown = original_shutdown


# ~~~~~ IoTHubDeviceClient Tests ~~~~~


class IoTHubDeviceClientTestConfig:
    """Mixin parent class defining a set of fixtures used in IoTHubDeviceClient tests"""

    @pytest.fixture
    async def client(self, custom_ssl_context):
        # Use a custom_ssl_context for auth for simplicity. Almost any test using this fixture
        # will not be affected by auth type, so just use the simplest one.
        client_config = config.IoTHubClientConfig(
            device_id=FAKE_DEVICE_ID, hostname=FAKE_HOSTNAME, ssl_context=custom_ssl_context
        )
        client = IoTHubDeviceClient(client_config)
        yield client
        await client.shutdown()

    @pytest.fixture
    def client_class(self):
        return IoTHubDeviceClient


@pytest.mark.describe("IoTHubDeviceClient -- Instantiation")
class TestIoTHubDeviceClientInstantiation(
    SharedClientInstantiationTests, IoTHubDeviceClientTestConfig
):
    pass


@pytest.mark.describe("IoTHubDeviceClient - .create()")
class TestIoTHubDeviceClientCreate(IoTHubDeviceClientTestConfig):
    @pytest.mark.it(
        "Returns a new IoTHubDeviceClient instance, created with the use of a new IoTHubClientConfig object"
    )
    @pytest.mark.parametrize("symmetric_key, sastoken_fn, ssl_context", create_auth_params)
    async def test_instantiation(self, mocker, symmetric_key, sastoken_fn, ssl_context):
        spy_config_cls = mocker.spy(config, "IoTHubClientConfig")
        spy_client_init = mocker.spy(IoTHubDeviceClient, "__init__")
        assert spy_config_cls.call_count == 0
        assert spy_client_init.call_count == 0

        client = await IoTHubDeviceClient.create(
            device_id=FAKE_DEVICE_ID,
            hostname=FAKE_HOSTNAME,
            symmetric_key=symmetric_key,
            sastoken_fn=sastoken_fn,
            ssl_context=ssl_context,
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
        "Sets the provided `device_id` on the IoTHubClientConfig used to create the client"
    )
    @pytest.mark.parametrize("symmetric_key, sastoken_fn, ssl_context", create_auth_params)
    async def test_device_id(self, mocker, symmetric_key, sastoken_fn, ssl_context):
        spy_client_init = mocker.spy(IoTHubDeviceClient, "__init__")

        client = await IoTHubDeviceClient.create(
            device_id=FAKE_DEVICE_ID,
            hostname=FAKE_HOSTNAME,
            symmetric_key=symmetric_key,
            sastoken_fn=sastoken_fn,
            ssl_context=ssl_context,
        )

        assert spy_client_init.call_count == 1
        assert spy_client_init.call_args == mocker.call(client, mocker.ANY)
        config = spy_client_init.call_args[0][1]
        assert config.device_id == FAKE_DEVICE_ID

        # Graceful exit
        await client.shutdown()

    @pytest.mark.it(
        "Does not set any `module_id` on the IoTHubClientConfig used to create the client"
    )
    @pytest.mark.parametrize("symmetric_key, sastoken_fn, ssl_context", create_auth_params)
    async def test_module_id(self, mocker, symmetric_key, sastoken_fn, ssl_context):
        spy_client_init = mocker.spy(IoTHubDeviceClient, "__init__")

        client = await IoTHubDeviceClient.create(
            device_id=FAKE_DEVICE_ID,
            hostname=FAKE_HOSTNAME,
            symmetric_key=symmetric_key,
            sastoken_fn=sastoken_fn,
            ssl_context=ssl_context,
        )

        assert spy_client_init.call_count == 1
        assert spy_client_init.call_args == mocker.call(client, mocker.ANY)
        config = spy_client_init.call_args[0][1]
        assert config.module_id is None

        # Graceful exit
        await client.shutdown()

    @pytest.mark.it(
        "Sets the provided `hostname` on the IoTHubClientConfig used to create the client"
    )
    @pytest.mark.parametrize("symmetric_key, sastoken_fn, ssl_context", create_auth_params)
    async def test_hostname(self, mocker, symmetric_key, sastoken_fn, ssl_context):
        spy_client_init = mocker.spy(IoTHubDeviceClient, "__init__")

        client = await IoTHubDeviceClient.create(
            device_id=FAKE_DEVICE_ID,
            hostname=FAKE_HOSTNAME,
            symmetric_key=symmetric_key,
            sastoken_fn=sastoken_fn,
            ssl_context=ssl_context,
        )

        assert spy_client_init.call_count == 1
        assert spy_client_init.call_args == mocker.call(client, mocker.ANY)
        config = spy_client_init.call_args[0][1]
        assert config.hostname == FAKE_HOSTNAME

        # Graceful exit
        await client.shutdown()

    @pytest.mark.it(
        "Sets the provided `ssl_context` on the IoTHubClientConfig used to create the client, if provided"
    )
    @pytest.mark.parametrize(
        "symmetric_key, sastoken_fn, ssl_context", create_auth_params_custom_ssl
    )
    async def test_custom_ssl_context(self, mocker, symmetric_key, sastoken_fn, ssl_context):
        spy_client_init = mocker.spy(IoTHubDeviceClient, "__init__")
        assert ssl_context is not None

        client = await IoTHubDeviceClient.create(
            device_id=FAKE_DEVICE_ID,
            hostname=FAKE_HOSTNAME,
            symmetric_key=symmetric_key,
            sastoken_fn=sastoken_fn,
            ssl_context=ssl_context,
        )

        assert spy_client_init.call_count == 1
        assert spy_client_init.call_args == mocker.call(client, mocker.ANY)
        config = spy_client_init.call_args[0][1]
        assert config.ssl_context is ssl_context

        # Graceful exit
        await client.shutdown()

    # NOTE: The details of this default SSLContext are covered in the TestDefaultSSLContext suite
    @pytest.mark.it(
        "Sets a default SSLContext on the IoTHubClientConfig used to create the client, if `ssl_context` is not provided"
    )
    @pytest.mark.parametrize(
        "symmetric_key, sastoken_fn, ssl_context", create_auth_params_default_ssl
    )
    async def test_default_ssl_context(self, mocker, symmetric_key, sastoken_fn, ssl_context):
        spy_client_init = mocker.spy(IoTHubDeviceClient, "__init__")
        spy_default_ssl = mocker.spy(iothub_client, "_default_ssl_context")
        assert ssl_context is None

        client = await IoTHubDeviceClient.create(
            device_id=FAKE_DEVICE_ID,
            hostname=FAKE_HOSTNAME,
            symmetric_key=symmetric_key,
            sastoken_fn=sastoken_fn,
        )

        assert spy_client_init.call_count == 1
        assert spy_client_init.call_args == mocker.call(client, mocker.ANY)
        config = spy_client_init.call_args[0][1]
        assert config.ssl_context is not None
        assert isinstance(config.ssl_context, ssl.SSLContext)
        # This SSLContext was returned from the default ssl context helper
        assert spy_default_ssl.call_count == 1
        assert spy_default_ssl.call_args == mocker.call()
        assert config.ssl_context is spy_default_ssl.spy_return

        # Graceful exit
        await client.shutdown()

    @pytest.mark.it(
        "Creates a SasTokenProvider that uses symmetric key-based token generation and sets it on the IoTHubClientConfig used to create the client, if `symmetric_key` is provided as a parameter"
    )
    @pytest.mark.parametrize("symmetric_key, sastoken_fn, ssl_context", create_auth_params_sk)
    async def test_sk_auth(self, mocker, symmetric_key, sastoken_fn, ssl_context):
        spy_client_init = mocker.spy(IoTHubDeviceClient, "__init__")
        spy_sk_sm_cls = mocker.spy(sm, "SymmetricKeySigningMechanism")
        spy_st_generator_cls = mocker.spy(st, "InternalSasTokenGenerator")
        spy_st_provider_create = mocker.spy(st.SasTokenProvider, "create_from_generator")
        expected_token_uri = "{hostname}/devices/{device_id}".format(
            hostname=FAKE_HOSTNAME, device_id=FAKE_DEVICE_ID
        )
        assert sastoken_fn is None

        client = await IoTHubDeviceClient.create(
            device_id=FAKE_DEVICE_ID,
            hostname=FAKE_HOSTNAME,
            symmetric_key=symmetric_key,
            ssl_context=ssl_context,
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
        assert spy_client_init.call_args == mocker.call(client, mocker.ANY)
        config = spy_client_init.call_args[0][1]
        assert config.sastoken_provider is spy_st_provider_create.spy_return

        # Graceful exit
        await client.shutdown()

    @pytest.mark.it(
        "Creates a SasTokenProvider that uses user callback-based token generation and sets it on the IoTHubClientConfig used to create the client, if `sastoken_fn` is provided as a parameter"
    )
    @pytest.mark.parametrize("symmetric_key, sastoken_fn, ssl_context", create_auth_params_token_cb)
    async def test_token_callback_auth(self, mocker, symmetric_key, sastoken_fn, ssl_context):
        spy_client_init = mocker.spy(IoTHubDeviceClient, "__init__")
        spy_st_generator_cls = mocker.spy(st, "ExternalSasTokenGenerator")
        spy_st_provider_create = mocker.spy(st.SasTokenProvider, "create_from_generator")
        assert symmetric_key is None

        client = await IoTHubDeviceClient.create(
            device_id=FAKE_DEVICE_ID,
            hostname=FAKE_HOSTNAME,
            sastoken_fn=sastoken_fn,
            ssl_context=ssl_context,
        )

        # ExternalSasTokenGenerator was created from the `sastoken_fn``
        assert spy_st_generator_cls.call_count == 1
        assert spy_st_generator_cls.call_args == mocker.call(sastoken_generator_fn)
        # SasTokenProvider was created from the ExternalSasTokenGenerator
        assert spy_st_provider_create.call_count == 1
        assert spy_st_provider_create.call_args == mocker.call(spy_st_generator_cls.spy_return)
        # The SasTokenProvider was set on the IoTHubClientConfig that was used to instantiate the client
        assert spy_client_init.call_count == 1
        assert spy_client_init.call_args == mocker.call(client, mocker.ANY)
        config = spy_client_init.call_args[0][1]
        assert config.sastoken_provider is spy_st_provider_create.spy_return

        # Graceful exit
        await client.shutdown()

    @pytest.mark.it(
        "Does not set any SasTokenProvider on the IoTHubClientConfig used to create the client if neither `symmetric_key` nor `sastoken_fn` are provided as parameters"
    )
    async def test_non_sas_auth(self, mocker, custom_ssl_context):
        spy_client_init = mocker.spy(IoTHubDeviceClient, "__init__")

        client = await IoTHubDeviceClient.create(
            device_id=FAKE_DEVICE_ID,
            hostname=FAKE_HOSTNAME,
            ssl_context=custom_ssl_context,
        )

        # No SasTokenProvider was set on the IoTHubClientConfig that was used to instantiate the client
        assert spy_client_init.call_count == 1
        assert spy_client_init.call_args == mocker.call(client, mocker.ANY)
        config = spy_client_init.call_args[0][1]
        assert config.sastoken_provider is None

        # Graceful exit
        await client.shutdown()

    @pytest.mark.it(
        "Sets any provided optional keyword arguments on IoTHubClientConfig used to create the client"
    )
    @pytest.mark.parametrize("symmetric_key, sastoken_fn, ssl_context", create_auth_params)
    @pytest.mark.parametrize("kwarg_name, kwarg_value", factory_kwargs)
    async def test_kwargs(
        self, mocker, symmetric_key, sastoken_fn, ssl_context, kwarg_name, kwarg_value
    ):
        spy_client_init = mocker.spy(IoTHubDeviceClient, "__init__")

        kwargs = {kwarg_name: kwarg_value}

        client = await IoTHubDeviceClient.create(
            device_id=FAKE_DEVICE_ID,
            hostname=FAKE_HOSTNAME,
            symmetric_key=symmetric_key,
            sastoken_fn=sastoken_fn,
            ssl_context=ssl_context,
            **kwargs
        )

        assert spy_client_init.call_count == 1
        assert spy_client_init.call_args == mocker.call(client, mocker.ANY)
        config = spy_client_init.call_args[0][1]
        assert getattr(config, kwarg_name) == kwarg_value

        # Graceful exit
        await client.shutdown()

    @pytest.mark.it(
        "Raises ValueError if neither `symmetric_key` nor `sastoken_fn` nor `ssl_context` are provided as parameters"
    )
    async def test_no_auth(self):
        with pytest.raises(ValueError):
            await IoTHubDeviceClient.create(
                device_id=FAKE_DEVICE_ID,
                hostname=FAKE_HOSTNAME,
            )

    @pytest.mark.it(
        "Raises ValueError if both `symmetric_key` and `sastoken_fn` are provided as parameters"
    )
    async def test_conflicting_auth(self, optional_ssl_context):
        with pytest.raises(ValueError):
            await IoTHubDeviceClient.create(
                device_id=FAKE_DEVICE_ID,
                hostname=FAKE_HOSTNAME,
                symmetric_key=FAKE_SYMMETRIC_KEY,
                sastoken_fn=sastoken_generator_fn,
                ssl_context=optional_ssl_context,
            )

    @pytest.mark.it(
        "Allows any exceptions raised when creating a SymmetricKeySigningMechanism to propagate"
    )
    @pytest.mark.parametrize("exception", sk_sm_create_exceptions)
    @pytest.mark.parametrize("symmetric_key, sastoken_fn, ssl_context", create_auth_params_sk)
    async def test_sksm_raises(self, mocker, symmetric_key, sastoken_fn, ssl_context, exception):
        mocker.patch.object(sm, "SymmetricKeySigningMechanism", side_effect=exception)
        assert sastoken_fn is None

        with pytest.raises(type(exception)) as e_info:
            await IoTHubDeviceClient.create(
                device_id=FAKE_DEVICE_ID,
                hostname=FAKE_HOSTNAME,
                symmetric_key=symmetric_key,
                ssl_context=ssl_context,
            )
        assert e_info.value is exception

    @pytest.mark.it("Allows any exceptions raised when creating a SasTokenProvider to propagate")
    @pytest.mark.parametrize("symmetric_key, sastoken_fn, ssl_context", create_auth_params_sas)
    @pytest.mark.parametrize("exception", sastoken_provider_create_exceptions)
    async def test_sastoken_provider_raises(
        self, mocker, symmetric_key, sastoken_fn, ssl_context, exception
    ):
        mocker.patch.object(st.SasTokenProvider, "create_from_generator", side_effect=exception)

        with pytest.raises(type(exception)) as e_info:
            await IoTHubDeviceClient.create(
                device_id=FAKE_DEVICE_ID,
                hostname=FAKE_HOSTNAME,
                symmetric_key=symmetric_key,
                sastoken_fn=sastoken_fn,
                ssl_context=ssl_context,
            )
        assert e_info.value is exception

    @pytest.mark.it("Can be cancelled while waiting for SasTokenProvider creation")
    @pytest.mark.parametrize("symmetric_key, sastoken_fn, ssl_context", create_auth_params_sas)
    async def test_cancel_during_sastoken_provider_creation(
        self, mocker, symmetric_key, sastoken_fn, ssl_context
    ):
        mocker.patch.object(
            st.SasTokenProvider, "create_from_generator", custom_mock.HangingAsyncMock()
        )

        coro = IoTHubDeviceClient.create(
            device_id=FAKE_DEVICE_ID,
            hostname=FAKE_HOSTNAME,
            symmetric_key=symmetric_key,
            sastoken_fn=sastoken_fn,
            ssl_context=ssl_context,
        )
        t = asyncio.create_task(coro)

        # Hanging, waiting for SasTokenProvider creation to finish
        await st.SasTokenProvider.create_from_generator.wait_for_hang()
        assert not t.done()

        # Cancel
        t.cancel()
        with pytest.raises(asyncio.CancelledError):
            await t


@pytest.mark.describe("IoTHubDeviceClient - .create_from_connection_string()")
class TestIoTHubDeviceClientCreateFromConnectionString(IoTHubDeviceClientTestConfig):

    factory_params = [
        pytest.param(
            "HostName={hostname};DeviceId={device_id};SharedAccessKey={shared_access_key}".format(
                hostname=FAKE_HOSTNAME,
                device_id=FAKE_DEVICE_ID,
                shared_access_key=FAKE_SYMMETRIC_KEY,
            ),
            None,
            id="Standard Connection String w/ SharedAccessKey + Default SSLContext",
        ),
        pytest.param(
            "HostName={hostname};DeviceId={device_id};SharedAccessKey={shared_access_key}".format(
                hostname=FAKE_HOSTNAME,
                device_id=FAKE_DEVICE_ID,
                shared_access_key=FAKE_SYMMETRIC_KEY,
            ),
            lazy_fixture("custom_ssl_context"),
            id="Standard Connection String w/ SharedAccessKey + Custom SSLContext",
        ),
        pytest.param(
            "HostName={hostname};DeviceId={device_id};SharedAccessKey={shared_access_key};GatewayHostName={gateway_hostname}".format(
                hostname=FAKE_HOSTNAME,
                device_id=FAKE_DEVICE_ID,
                shared_access_key=FAKE_SYMMETRIC_KEY,
                gateway_hostname=FAKE_GATEWAY_HOSTNAME,
            ),
            None,
            id="Edge Connection String w/ SharedAccessKey + Default SSLContext",
        ),
        pytest.param(
            "HostName={hostname};DeviceId={device_id};SharedAccessKey={shared_access_key};GatewayHostName={gateway_hostname}".format(
                hostname=FAKE_HOSTNAME,
                device_id=FAKE_DEVICE_ID,
                shared_access_key=FAKE_SYMMETRIC_KEY,
                gateway_hostname=FAKE_GATEWAY_HOSTNAME,
            ),
            lazy_fixture("custom_ssl_context"),
            id="Edge Connection String w/ SharedAccessKey + Custom SSLContext",
        ),
        # NOTE: X509 certs imply use of custom SSLContext
        pytest.param(
            "HostName={hostname};DeviceId={device_id};x509=true".format(
                hostname=FAKE_HOSTNAME,
                device_id=FAKE_DEVICE_ID,
            ),
            lazy_fixture("custom_ssl_context"),
            id="Standard Connection String w/ X509",
        ),
        pytest.param(
            "HostName={hostname};DeviceId={device_id};GatewayHostName={gateway_hostname};x509=true".format(
                hostname=FAKE_HOSTNAME,
                device_id=FAKE_DEVICE_ID,
                gateway_hostname=FAKE_GATEWAY_HOSTNAME,
            ),
            lazy_fixture("custom_ssl_context"),
            id="Edge Connection String w/ X509",
        ),
    ]
    # Just the parameters for using standard connection strings
    factory_params_no_gateway = [
        param for param in factory_params if cs.GATEWAY_HOST_NAME not in param.values[0]
    ]
    # Just the parameters for using connection strings with a GatewayHostName
    factory_params_gateway = [
        param for param in factory_params if cs.GATEWAY_HOST_NAME in param.values[0]
    ]
    # Just the parameters where a custom SSLContext is provided
    factory_params_custom_ssl = [param for param in factory_params if param.values[1] is not None]
    # Just the parameters where a custom SSLContext is NOT provided
    factory_params_default_ssl = [param for param in factory_params if param.values[1] is None]
    # Just the parameters for using SharedAccessKeys
    factory_params_sak = [
        param for param in factory_params if cs.SHARED_ACCESS_KEY in param.values[0]
    ]
    # Just the parameters for NOT using SharedAccessKeys
    factory_params_no_sak = [
        param for param in factory_params if cs.SHARED_ACCESS_KEY not in param.values[0]
    ]

    @pytest.mark.it(
        "Returns a new IoTHubDeviceClient instance, created with the use of a new IoTHubClientConfig object"
    )
    @pytest.mark.parametrize("connection_string, ssl_context", factory_params)
    async def test_instantiation(self, mocker, connection_string, ssl_context):
        spy_config_cls = mocker.spy(config, "IoTHubClientConfig")
        spy_client_init = mocker.spy(IoTHubDeviceClient, "__init__")
        assert spy_config_cls.call_count == 0
        assert spy_client_init.call_count == 0

        client = await IoTHubDeviceClient.create_from_connection_string(
            connection_string, ssl_context=ssl_context
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
        "Sets the `DeviceId` from the connection string as the `device_id` on the IoTHubClientConfig used to create the client"
    )
    @pytest.mark.parametrize("connection_string, ssl_context", factory_params)
    async def test_device_id(self, mocker, connection_string, ssl_context):
        spy_client_init = mocker.spy(IoTHubDeviceClient, "__init__")
        # Create a ConnectionString object from the connection string to simply value access
        cs_obj = cs.ConnectionString(connection_string)

        client = await IoTHubDeviceClient.create_from_connection_string(
            connection_string, ssl_context=ssl_context
        )

        assert spy_client_init.call_count == 1
        assert spy_client_init.call_args == mocker.call(client, mocker.ANY)
        config = spy_client_init.call_args[0][1]
        assert config.device_id == cs_obj[cs.DEVICE_ID]

        # Graceful exit
        await client.shutdown()

    @pytest.mark.it(
        "Does not set any `module_id` on the IoTHubClientConfig used to create the client"
    )
    @pytest.mark.parametrize("connection_string, ssl_context", factory_params)
    async def test_module_id(self, mocker, connection_string, ssl_context):
        spy_client_init = mocker.spy(IoTHubDeviceClient, "__init__")

        client = await IoTHubDeviceClient.create_from_connection_string(
            connection_string, ssl_context=ssl_context
        )

        assert spy_client_init.call_count == 1
        assert spy_client_init.call_args == mocker.call(client, mocker.ANY)
        config = spy_client_init.call_args[0][1]
        assert config.module_id is None

        # Graceful exit
        await client.shutdown()

    @pytest.mark.it(
        "Sets the `HostName` from the connection string as the `hostname` on the IoTHubClientConfig, if no `GatewayHostName` is present in the connection string"
    )
    @pytest.mark.parametrize("connection_string, ssl_context", factory_params_no_gateway)
    async def test_hostname_cs_has_no_gateway(self, mocker, connection_string, ssl_context):
        spy_client_init = mocker.spy(IoTHubDeviceClient, "__init__")
        # Create a ConnectionString object from the connection string to simply value access
        cs_obj = cs.ConnectionString(connection_string)
        assert cs.GATEWAY_HOST_NAME not in cs_obj

        client = await IoTHubDeviceClient.create_from_connection_string(
            connection_string, ssl_context=ssl_context
        )

        assert spy_client_init.call_count == 1
        assert spy_client_init.call_args == mocker.call(client, mocker.ANY)
        config = spy_client_init.call_args[0][1]
        assert config.hostname == cs_obj[cs.HOST_NAME]

        # Graceful exit
        await client.shutdown()

    @pytest.mark.it(
        "Sets the `HostName` from the connection string as the `hostname` on the IoTHubClientConfig used to create the client, if no `GatewayHostName` is present in the connection string"
    )
    @pytest.mark.parametrize("connection_string, ssl_context", factory_params_gateway)
    async def test_hostname_cs_has_gateway(self, mocker, connection_string, ssl_context):
        spy_client_init = mocker.spy(IoTHubDeviceClient, "__init__")
        # Create a ConnectionString object from the connection string to simply value access
        cs_obj = cs.ConnectionString(connection_string)
        assert cs.GATEWAY_HOST_NAME in cs_obj
        assert cs_obj[cs.GATEWAY_HOST_NAME] != cs_obj[cs.HOST_NAME]

        client = await IoTHubDeviceClient.create_from_connection_string(
            connection_string, ssl_context=ssl_context
        )

        assert spy_client_init.call_count == 1
        assert spy_client_init.call_args == mocker.call(client, mocker.ANY)
        config = spy_client_init.call_args[0][1]
        assert config.hostname == cs_obj[cs.GATEWAY_HOST_NAME]

        # Graceful exit
        await client.shutdown()

    @pytest.mark.it(
        "Sets the provided `ssl_context` on the IoTHubClientConfig used to create the client, if provided"
    )
    @pytest.mark.parametrize("connection_string, ssl_context", factory_params_custom_ssl)
    async def test_custom_ssl_context(self, mocker, connection_string, ssl_context):
        spy_client_init = mocker.spy(IoTHubDeviceClient, "__init__")
        assert ssl_context is not None

        client = await IoTHubDeviceClient.create_from_connection_string(
            connection_string, ssl_context=ssl_context
        )

        assert spy_client_init.call_count == 1
        assert spy_client_init.call_args == mocker.call(client, mocker.ANY)
        config = spy_client_init.call_args[0][1]
        assert config.ssl_context is ssl_context

        # Graceful exit
        await client.shutdown()

    # NOTE: The details of this default SSLContext are covered in the TestDefaultSSLContext suite
    @pytest.mark.it(
        "Sets a default SSLContext as the `ssl_context` on the IoTHubClientConfig used to create the client, if `ssl_context` is not provided"
    )
    @pytest.mark.parametrize("connection_string, ssl_context", factory_params_default_ssl)
    async def test_default_ssl_context(self, mocker, connection_string, ssl_context):
        spy_client_init = mocker.spy(IoTHubDeviceClient, "__init__")
        spy_default_ssl = mocker.spy(iothub_client, "_default_ssl_context")
        assert ssl_context is None

        client = await IoTHubDeviceClient.create_from_connection_string(connection_string)

        assert spy_default_ssl.call_count == 1
        assert spy_default_ssl.call_args == mocker.call()
        assert spy_client_init.call_count == 1
        assert spy_client_init.call_args == mocker.call(client, mocker.ANY)
        config = spy_client_init.call_args[0][1]
        assert config.ssl_context is spy_default_ssl.spy_return

        # Graceful exit
        await client.shutdown()

    @pytest.mark.it(
        "Creates a SasTokenProvider that uses symmetric key-based token generation and sets it on the IoTHubClientConfig used to create the client, if `SharedAccessKey` is present in the connection string"
    )
    @pytest.mark.parametrize("connection_string, ssl_context", factory_params_sak)
    async def test_sk_auth(self, mocker, connection_string, ssl_context):
        # Create a ConnectionString object from the connection string to simply value access
        cs_obj = cs.ConnectionString(connection_string)
        assert cs.SHARED_ACCESS_KEY in cs_obj
        # Mock
        spy_client_init = mocker.spy(IoTHubDeviceClient, "__init__")
        spy_sk_sm_cls = mocker.spy(sm, "SymmetricKeySigningMechanism")
        spy_st_generator_cls = mocker.spy(st, "InternalSasTokenGenerator")
        spy_st_provider_create = mocker.spy(st.SasTokenProvider, "create_from_generator")
        expected_token_uri = "{hostname}/devices/{device_id}".format(
            hostname=cs_obj.get(cs.GATEWAY_HOST_NAME, default=cs_obj[cs.HOST_NAME]),
            device_id=cs_obj[cs.DEVICE_ID],
        )

        client = await IoTHubDeviceClient.create_from_connection_string(
            connection_string, ssl_context=ssl_context
        )

        # SymmetricKeySigningMechanism was created from the SharedAccessKey
        assert spy_sk_sm_cls.call_count == 1
        assert spy_sk_sm_cls.call_args == mocker.call(cs_obj[cs.SHARED_ACCESS_KEY])
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
        assert spy_client_init.call_args == mocker.call(client, mocker.ANY)
        config = spy_client_init.call_args[0][1]
        assert config.sastoken_provider is spy_st_provider_create.spy_return

        # Graceful exit
        await client.shutdown()

    @pytest.mark.it(
        "Does not set any SasTokenProvider on the IoTHubClientConfig used to create the client if no `SharedAccessKey` is present in the connection string"
    )
    @pytest.mark.parametrize("connection_string, ssl_context", factory_params_no_sak)
    async def test_non_sas_auth(self, mocker, connection_string, ssl_context):
        spy_client_init = mocker.spy(IoTHubDeviceClient, "__init__")
        # Create a ConnectionString object from the connection string to simply value access
        cs_obj = cs.ConnectionString(connection_string)
        assert cs.SHARED_ACCESS_KEY not in cs_obj

        client = await IoTHubDeviceClient.create_from_connection_string(
            connection_string, ssl_context=ssl_context
        )

        # No SasTokenProvider was set on the IoTHubClientConfig that was used to instantiate the client
        assert spy_client_init.call_count == 1
        assert spy_client_init.call_args == mocker.call(client, mocker.ANY)
        config = spy_client_init.call_args[0][1]
        assert config.sastoken_provider is None

        # Graceful exit
        await client.shutdown()

    @pytest.mark.it(
        "Sets any provided optional keyword arguments on IoTHubClientConfig used to create the client"
    )
    @pytest.mark.parametrize("connection_string, ssl_context", factory_params)
    @pytest.mark.parametrize("kwarg_name, kwarg_value", factory_kwargs)
    async def test_kwargs(self, mocker, connection_string, ssl_context, kwarg_name, kwarg_value):
        spy_client_init = mocker.spy(IoTHubDeviceClient, "__init__")

        kwargs = {kwarg_name: kwarg_value}

        client = await IoTHubDeviceClient.create_from_connection_string(
            connection_string, ssl_context=ssl_context, **kwargs
        )

        assert spy_client_init.call_count == 1
        assert spy_client_init.call_args == mocker.call(client, mocker.ANY)
        config = spy_client_init.call_args[0][1]
        assert getattr(config, kwarg_name) == kwarg_value

        # Graceful exit
        await client.shutdown()

    @pytest.mark.it("Raises ValueError if a `ModuleId` is present in the connection string")
    async def test_module_id_in_string(self, optional_ssl_context):
        # NOTE: There could be many strings containing a ModuleId, but I'm not going to try them
        # all to avoid confounds with other errors, I'll just use a standard module string that
        # uses a SharedAccessKey
        connection_string = "HostName={hostname};DeviceId={device_id};ModuleId={module_id};SharedAccessKey={shared_access_key}".format(
            hostname=FAKE_HOSTNAME,
            device_id=FAKE_DEVICE_ID,
            module_id=FAKE_MODULE_ID,
            shared_access_key=FAKE_SYMMETRIC_KEY,
        )
        with pytest.raises(ValueError):
            await IoTHubDeviceClient.create_from_connection_string(
                connection_string, ssl_context=optional_ssl_context
            )

    @pytest.mark.it(
        "Raises ValueError if `x509=true` is present in the connection string, but no `ssl_context` is provided"
    )
    @pytest.mark.parametrize("connection_string, ssl_context", factory_params_no_sak)
    async def test_x509_with_no_ssl(self, connection_string, ssl_context):
        # Ignore the ssl_context provided by the parametrization
        with pytest.raises(ValueError):
            await IoTHubDeviceClient.create_from_connection_string(connection_string)

    @pytest.mark.it(
        "Does not raise a ValueError if `x509=false` is present in the connection string and no `ssl_context` is provided"
    )
    async def test_x509_equals_false(self):
        # NOTE: This is a weird test in that if you aren't using X509 certs, there shouldn't be
        # an `x509` field in your connection string in the first place. But, semantically, it feels
        # as though this test ought to exist to validate that we are checking the value of the
        # field, not just the key name.
        # NOTE: Because we're in the land of undefined behavior here, on account of this scenario
        # not being supposed to happen, I'm arbitrarily deciding we're testing this with a string
        # containing a SharedAccessKey and no GatewayHostName for simplicity.
        connection_string = "HostName={hostname};DeviceId={device_id};SharedAccessKey={shared_access_key};x509=false".format(
            hostname=FAKE_HOSTNAME, device_id=FAKE_DEVICE_ID, shared_access_key=FAKE_SYMMETRIC_KEY
        )
        client = await IoTHubDeviceClient.create_from_connection_string(connection_string)
        # If the above invocation didn't raise, the test passed, no assertions required

        # Graceful exit
        await client.shutdown()

    @pytest.mark.it("Allows any exceptions raised when parsing the connection string to propagate")
    @pytest.mark.parametrize(
        "exception",
        [
            pytest.param(ValueError(), id="ValueError"),
            pytest.param(lazy_fixture("arbitrary_exception"), id="Unexpected Exception"),
        ],
    )
    async def test_cs_parsing_raises(self, mocker, optional_ssl_context, exception):
        # NOTE: This test covers all invalid connection string scenarios. For more detail, see the
        # dedicated connection string parsing tests for the `connection_string.py` module - there's
        # no reason to replicate them all here.
        # NOTE: For the purposes of this test, it does not matter what this connection string is.
        # The one provided here is valid, but the mock will cause the parsing to raise anyway.
        connection_string = (
            "HostName={hostname};DeviceId={device_id};SharedAccessKey={shared_access_key}".format(
                hostname=FAKE_HOSTNAME,
                device_id=FAKE_DEVICE_ID,
                shared_access_key=FAKE_SYMMETRIC_KEY,
            )
        )
        # Mock cs parsing
        mocker.patch.object(cs, "ConnectionString", side_effect=exception)

        with pytest.raises(type(exception)) as e_info:
            await IoTHubDeviceClient.create_from_connection_string(
                connection_string, ssl_context=optional_ssl_context
            )
        assert e_info.value is exception

    @pytest.mark.it(
        "Allows any exceptions raised when creating a SymmetricKeySigningMechanism to propagate"
    )
    @pytest.mark.parametrize("connection_string, ssl_context", factory_params_sak)
    @pytest.mark.parametrize("exception", sk_sm_create_exceptions)
    async def test_sksm_raises(self, mocker, connection_string, ssl_context, exception):
        mocker.patch.object(sm, "SymmetricKeySigningMechanism", side_effect=exception)

        with pytest.raises(type(exception)) as e_info:
            await IoTHubDeviceClient.create_from_connection_string(
                connection_string,
                ssl_context=ssl_context,
            )
        assert e_info.value is exception

    @pytest.mark.it("Allows any exceptions raised when creating a SasTokenProvider to propagate")
    @pytest.mark.parametrize("connection_string, ssl_context", factory_params_sak)
    @pytest.mark.parametrize("exception", sastoken_provider_create_exceptions)
    async def test_sastoken_provider_raises(
        self, mocker, connection_string, ssl_context, exception
    ):
        mocker.patch.object(st.SasTokenProvider, "create_from_generator", side_effect=exception)

        with pytest.raises(type(exception)) as e_info:
            await IoTHubDeviceClient.create_from_connection_string(
                connection_string,
                ssl_context=ssl_context,
            )
        assert e_info.value is exception

    @pytest.mark.it("Can be cancelled while waiting for SasTokenProvider creation")
    @pytest.mark.parametrize("connection_string, ssl_context", factory_params_sak)
    async def test_cancel_during_sastoken_provider_creation(
        self, mocker, connection_string, ssl_context
    ):
        mocker.patch.object(
            st.SasTokenProvider, "create_from_generator", custom_mock.HangingAsyncMock()
        )

        coro = IoTHubDeviceClient.create_from_connection_string(
            connection_string,
            ssl_context=ssl_context,
        )
        t = asyncio.create_task(coro)

        # Hanging, waiting for SasTokenProvider creation to finish
        await st.SasTokenProvider.create_from_generator.wait_for_hang()
        assert not t.done()

        # Cancel
        t.cancel()
        with pytest.raises(asyncio.CancelledError):
            await t


@pytest.mark.describe("IoTHubDeviceClient - .shutdown()")
class TestIoTHubDeviceClientShutdown(SharedClientShutdownTests, IoTHubDeviceClientTestConfig):
    pass


# ~~~~~ IoTHubModuleClient Tests ~~~~~


class IoTHubModuleClientTestConfig:
    """Mixin parent class defining a set of fixtures used in IoTHubModuleClient tests"""

    @pytest.fixture
    async def client(self, custom_ssl_context):
        # Use a custom_ssl_context for auth for simplicity. Almost any test using this fixture
        # will not be affected by auth type, so just use the simplest one.
        client_config = config.IoTHubClientConfig(
            device_id=FAKE_DEVICE_ID,
            module_id=FAKE_MODULE_ID,
            hostname=FAKE_HOSTNAME,
            ssl_context=custom_ssl_context,
        )
        client = IoTHubDeviceClient(client_config)
        yield client
        await client.shutdown()

    @pytest.fixture
    def client_class(self):
        return IoTHubModuleClient


@pytest.mark.describe("IoTHubModuleClient -- Instantiation")
class TestIoTHubModuleClientInstantiation(
    SharedClientInstantiationTests, IoTHubModuleClientTestConfig
):
    pass


@pytest.mark.describe("IoTHubModuleClient - .create()")
class TestIoTHubModuleClientCreate(IoTHubModuleClientTestConfig):
    @pytest.mark.it(
        "Returns a new IoTHubModuleClient instance, created with the use of a new IoTHubClientConfig object"
    )
    @pytest.mark.parametrize("symmetric_key, sastoken_fn, ssl_context", create_auth_params)
    async def test_instantiation(self, mocker, symmetric_key, sastoken_fn, ssl_context):
        spy_config_cls = mocker.spy(config, "IoTHubClientConfig")
        spy_client_init = mocker.spy(IoTHubModuleClient, "__init__")
        assert spy_config_cls.call_count == 0
        assert spy_client_init.call_count == 0

        client = await IoTHubModuleClient.create(
            device_id=FAKE_DEVICE_ID,
            module_id=FAKE_MODULE_ID,
            hostname=FAKE_HOSTNAME,
            symmetric_key=symmetric_key,
            sastoken_fn=sastoken_fn,
            ssl_context=ssl_context,
        )

        assert spy_config_cls.call_count == 1
        assert spy_client_init.call_count == 1
        # NOTE: Normally passing through self or cls isn't necessary in a mock call, but
        # it seems that when mocking the __init__ it is. This is actually good though, as it
        # allows us to match the specific object reference which otherwise is very dicey when
        # mocking constructors/initializers
        assert spy_client_init.call_args == mocker.call(client, spy_config_cls.spy_return)
        assert isinstance(client, IoTHubModuleClient)

        # Graceful exit
        await client.shutdown()

    @pytest.mark.it(
        "Sets the provided `device_id` on the IoTHubClientConfig used to create the client"
    )
    @pytest.mark.parametrize("symmetric_key, sastoken_fn, ssl_context", create_auth_params)
    async def test_device_id(self, mocker, symmetric_key, sastoken_fn, ssl_context):
        spy_client_init = mocker.spy(IoTHubModuleClient, "__init__")

        client = await IoTHubModuleClient.create(
            device_id=FAKE_DEVICE_ID,
            module_id=FAKE_MODULE_ID,
            hostname=FAKE_HOSTNAME,
            symmetric_key=symmetric_key,
            sastoken_fn=sastoken_fn,
            ssl_context=ssl_context,
        )

        assert spy_client_init.call_count == 1
        assert spy_client_init.call_args == mocker.call(client, mocker.ANY)
        config = spy_client_init.call_args[0][1]
        assert config.device_id == FAKE_DEVICE_ID

        # Graceful exit
        await client.shutdown()

    @pytest.mark.it(
        "Sets the provided `module_id` on the IoTHubClientConfig used to create the client"
    )
    @pytest.mark.parametrize("symmetric_key, sastoken_fn, ssl_context", create_auth_params)
    async def test_module_id(self, mocker, symmetric_key, sastoken_fn, ssl_context):
        spy_client_init = mocker.spy(IoTHubModuleClient, "__init__")

        client = await IoTHubModuleClient.create(
            device_id=FAKE_DEVICE_ID,
            module_id=FAKE_MODULE_ID,
            hostname=FAKE_HOSTNAME,
            symmetric_key=symmetric_key,
            sastoken_fn=sastoken_fn,
            ssl_context=ssl_context,
        )

        assert spy_client_init.call_count == 1
        assert spy_client_init.call_args == mocker.call(client, mocker.ANY)
        config = spy_client_init.call_args[0][1]
        assert config.module_id == FAKE_MODULE_ID

        # Graceful exit
        await client.shutdown()

    @pytest.mark.it(
        "Sets the provided `hostname` on the IoTHubClientConfig used to create the client"
    )
    @pytest.mark.parametrize("symmetric_key, sastoken_fn, ssl_context", create_auth_params)
    async def test_hostname(self, mocker, symmetric_key, sastoken_fn, ssl_context):
        spy_client_init = mocker.spy(IoTHubModuleClient, "__init__")

        client = await IoTHubModuleClient.create(
            device_id=FAKE_DEVICE_ID,
            module_id=FAKE_MODULE_ID,
            hostname=FAKE_HOSTNAME,
            symmetric_key=symmetric_key,
            sastoken_fn=sastoken_fn,
            ssl_context=ssl_context,
        )

        assert spy_client_init.call_count == 1
        assert spy_client_init.call_args == mocker.call(client, mocker.ANY)
        config = spy_client_init.call_args[0][1]
        assert config.hostname == FAKE_HOSTNAME

        # Graceful exit
        await client.shutdown()

    @pytest.mark.it(
        "Sets the provided `ssl_context` on the IoTHubClientConfig used to create the client, if provided"
    )
    @pytest.mark.parametrize(
        "symmetric_key, sastoken_fn, ssl_context", create_auth_params_custom_ssl
    )
    async def test_custom_ssl_context(self, mocker, symmetric_key, sastoken_fn, ssl_context):
        spy_client_init = mocker.spy(IoTHubModuleClient, "__init__")
        assert ssl_context is not None

        client = await IoTHubModuleClient.create(
            device_id=FAKE_DEVICE_ID,
            module_id=FAKE_MODULE_ID,
            hostname=FAKE_HOSTNAME,
            symmetric_key=symmetric_key,
            sastoken_fn=sastoken_fn,
            ssl_context=custom_ssl_context,
        )

        assert spy_client_init.call_count == 1
        assert spy_client_init.call_args == mocker.call(client, mocker.ANY)
        config = spy_client_init.call_args[0][1]
        assert config.ssl_context is custom_ssl_context

        # Graceful exit
        await client.shutdown()

    # NOTE: The details of this default SSLContext are covered in the TestDefaultSSLContext suite
    @pytest.mark.it(
        "Sets a default SSLContext on the IoTHubClientConfig used to create the client, if `ssl_context` is not provided"
    )
    @pytest.mark.parametrize(
        "symmetric_key, sastoken_fn, ssl_context", create_auth_params_default_ssl
    )
    async def test_default_ssl_context(self, mocker, symmetric_key, sastoken_fn, ssl_context):
        spy_client_init = mocker.spy(IoTHubModuleClient, "__init__")
        spy_default_ssl = mocker.spy(iothub_client, "_default_ssl_context")
        assert ssl_context is None

        client = await IoTHubModuleClient.create(
            device_id=FAKE_DEVICE_ID,
            module_id=FAKE_MODULE_ID,
            hostname=FAKE_HOSTNAME,
            symmetric_key=symmetric_key,
            sastoken_fn=sastoken_fn,
        )

        assert spy_client_init.call_count == 1
        assert spy_client_init.call_args == mocker.call(client, mocker.ANY)
        config = spy_client_init.call_args[0][1]
        assert config.ssl_context is not None
        assert isinstance(config.ssl_context, ssl.SSLContext)
        # This SSLContext was returned from the default ssl context helper
        assert spy_default_ssl.call_count == 1
        assert spy_default_ssl.call_args == mocker.call()
        assert config.ssl_context is spy_default_ssl.spy_return

        # Graceful exit
        await client.shutdown()

    @pytest.mark.it(
        "Creates a SasTokenProvider that uses symmetric key-based token generation and sets it on the IoTHubClientConfig used to create the client, if `symmetric_key` is provided as a parameter"
    )
    @pytest.mark.parametrize("symmetric_key, sastoken_fn, ssl_context", create_auth_params_sk)
    async def test_sk_auth(self, mocker, symmetric_key, sastoken_fn, ssl_context):
        spy_client_init = mocker.spy(IoTHubModuleClient, "__init__")
        spy_sk_sm_cls = mocker.spy(sm, "SymmetricKeySigningMechanism")
        spy_st_generator_cls = mocker.spy(st, "InternalSasTokenGenerator")
        spy_st_provider_create = mocker.spy(st.SasTokenProvider, "create_from_generator")
        expected_token_uri = "{hostname}/devices/{device_id}/modules/{module_id}".format(
            hostname=FAKE_HOSTNAME, device_id=FAKE_DEVICE_ID, module_id=FAKE_MODULE_ID
        )
        assert sastoken_fn is None

        client = await IoTHubModuleClient.create(
            device_id=FAKE_DEVICE_ID,
            module_id=FAKE_MODULE_ID,
            hostname=FAKE_HOSTNAME,
            symmetric_key=symmetric_key,
            ssl_context=ssl_context,
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
        assert spy_client_init.call_args == mocker.call(client, mocker.ANY)
        config = spy_client_init.call_args[0][1]
        assert config.sastoken_provider is spy_st_provider_create.spy_return

        # Graceful exit
        await client.shutdown()

    @pytest.mark.it(
        "Creates a SasTokenProvider that uses user callback-based token generation and sets it on the IoTHubClientConfig used to create the client, if `sastoken_fn` is provided as a parameter"
    )
    @pytest.mark.parametrize("symmetric_key, sastoken_fn, ssl_context", create_auth_params_token_cb)
    async def test_token_callback_auth(self, mocker, symmetric_key, sastoken_fn, ssl_context):
        spy_client_init = mocker.spy(IoTHubModuleClient, "__init__")
        spy_st_generator_cls = mocker.spy(st, "ExternalSasTokenGenerator")
        spy_st_provider_create = mocker.spy(st.SasTokenProvider, "create_from_generator")
        assert symmetric_key is None

        client = await IoTHubModuleClient.create(
            device_id=FAKE_DEVICE_ID,
            module_id=FAKE_MODULE_ID,
            hostname=FAKE_HOSTNAME,
            sastoken_fn=sastoken_fn,
            ssl_context=ssl_context,
        )

        # ExternalSasTokenGenerator was created from the `sastoken_fn``
        assert spy_st_generator_cls.call_count == 1
        assert spy_st_generator_cls.call_args == mocker.call(sastoken_generator_fn)
        # SasTokenProvider was created from the ExternalSasTokenGenerator
        assert spy_st_provider_create.call_count == 1
        assert spy_st_provider_create.call_args == mocker.call(spy_st_generator_cls.spy_return)
        # The SasTokenProvider was set on the IoTHubClientConfig that was used to instantiate the client
        assert spy_client_init.call_count == 1
        assert spy_client_init.call_args == mocker.call(client, mocker.ANY)
        config = spy_client_init.call_args[0][1]
        assert config.sastoken_provider is spy_st_provider_create.spy_return

        # Graceful exit
        await client.shutdown()

    @pytest.mark.it(
        "Does not set any SasTokenProvider on the IoTHubClientConfig used to create the client if neither `symmetric_key` nor `sastoken_fn` are provided as parameters"
    )
    async def test_non_sas_auth(self, mocker, custom_ssl_context):
        spy_client_init = mocker.spy(IoTHubModuleClient, "__init__")

        client = await IoTHubModuleClient.create(
            device_id=FAKE_DEVICE_ID,
            module_id=FAKE_MODULE_ID,
            hostname=FAKE_HOSTNAME,
            ssl_context=custom_ssl_context,
        )

        # No SasTokenProvider was set on the IoTHubClientConfig that was used to instantiate the client
        assert spy_client_init.call_count == 1
        assert spy_client_init.call_args == mocker.call(client, mocker.ANY)
        config = spy_client_init.call_args[0][1]
        assert config.sastoken_provider is None

        # Graceful exit
        await client.shutdown()

    @pytest.mark.it(
        "Sets any provided optional keyword arguments on IoTHubClientConfig used to create the client"
    )
    @pytest.mark.parametrize("symmetric_key, sastoken_fn, ssl_context", create_auth_params)
    @pytest.mark.parametrize("kwarg_name, kwarg_value", factory_kwargs)
    async def test_kwargs(
        self, mocker, symmetric_key, sastoken_fn, ssl_context, kwarg_name, kwarg_value
    ):
        spy_client_init = mocker.spy(IoTHubModuleClient, "__init__")

        kwargs = {kwarg_name: kwarg_value}

        client = await IoTHubModuleClient.create(
            device_id=FAKE_DEVICE_ID,
            module_id=FAKE_MODULE_ID,
            hostname=FAKE_HOSTNAME,
            symmetric_key=symmetric_key,
            sastoken_fn=sastoken_fn,
            ssl_context=ssl_context,
            **kwargs
        )

        assert spy_client_init.call_count == 1
        assert spy_client_init.call_args == mocker.call(client, mocker.ANY)
        config = spy_client_init.call_args[0][1]
        assert getattr(config, kwarg_name) == kwarg_value

        # Graceful exit
        await client.shutdown()

    @pytest.mark.it(
        "Raises ValueError if neither `symmetric_key` nor `sastoken_fn` nor `ssl_context` are provided as parameters"
    )
    async def test_no_auth(self):
        with pytest.raises(ValueError):
            await IoTHubModuleClient.create(
                device_id=FAKE_DEVICE_ID,
                module_id=FAKE_MODULE_ID,
                hostname=FAKE_HOSTNAME,
            )

    @pytest.mark.it(
        "Raises ValueError if both `symmetric_key` and `sastoken_fn` are provided as parameters"
    )
    async def test_conflicting_auth(self, optional_ssl_context):
        with pytest.raises(ValueError):
            await IoTHubModuleClient.create(
                device_id=FAKE_DEVICE_ID,
                module_id=FAKE_MODULE_ID,
                hostname=FAKE_HOSTNAME,
                symmetric_key=FAKE_SYMMETRIC_KEY,
                sastoken_fn=sastoken_generator_fn,
                ssl_context=optional_ssl_context,
            )

    @pytest.mark.it(
        "Allows any exceptions raised when creating a SymmetricKeySigningMechanism to propagate"
    )
    @pytest.mark.parametrize("exception", sk_sm_create_exceptions)
    @pytest.mark.parametrize("symmetric_key, sastoken_fn, ssl_context", create_auth_params_sk)
    async def test_sksm_raises(self, mocker, symmetric_key, sastoken_fn, ssl_context, exception):
        mocker.patch.object(sm, "SymmetricKeySigningMechanism", side_effect=exception)
        assert sastoken_fn is None

        with pytest.raises(type(exception)) as e_info:
            await IoTHubModuleClient.create(
                device_id=FAKE_DEVICE_ID,
                module_id=FAKE_MODULE_ID,
                hostname=FAKE_HOSTNAME,
                symmetric_key=symmetric_key,
                ssl_context=ssl_context,
            )
        assert e_info.value is exception

    @pytest.mark.it("Allows any exceptions raised when creating a SasTokenProvider to propagate")
    @pytest.mark.parametrize("symmetric_key, sastoken_fn, ssl_context", create_auth_params_sas)
    @pytest.mark.parametrize("exception", sastoken_provider_create_exceptions)
    async def test_sastoken_provider_raises(
        self, mocker, symmetric_key, sastoken_fn, ssl_context, exception
    ):
        mocker.patch.object(st.SasTokenProvider, "create_from_generator", side_effect=exception)

        with pytest.raises(type(exception)) as e_info:
            await IoTHubModuleClient.create(
                device_id=FAKE_DEVICE_ID,
                module_id=FAKE_MODULE_ID,
                hostname=FAKE_HOSTNAME,
                symmetric_key=symmetric_key,
                sastoken_fn=sastoken_fn,
                ssl_context=ssl_context,
            )
        assert e_info.value is exception

    @pytest.mark.it("Can be cancelled while waiting for SasTokenProvider creation")
    @pytest.mark.parametrize("symmetric_key, sastoken_fn, ssl_context", create_auth_params_sas)
    async def test_cancel_during_sastoken_provider_creation(
        self, mocker, symmetric_key, sastoken_fn, ssl_context
    ):
        mocker.patch.object(
            st.SasTokenProvider, "create_from_generator", custom_mock.HangingAsyncMock()
        )

        coro = IoTHubModuleClient.create(
            device_id=FAKE_DEVICE_ID,
            module_id=FAKE_MODULE_ID,
            hostname=FAKE_HOSTNAME,
            symmetric_key=symmetric_key,
            sastoken_fn=sastoken_fn,
            ssl_context=ssl_context,
        )
        t = asyncio.create_task(coro)

        # Hanging, waiting for SasTokenProvider creation to finish
        await st.SasTokenProvider.create_from_generator.wait_for_hang()
        assert not t.done()

        # Cancel
        t.cancel()
        with pytest.raises(asyncio.CancelledError):
            await t


@pytest.mark.describe("IoTHubModuleClient - .create_from_connection_string()")
class TestIoTHubModuleClientCreateFromConnectionString(IoTHubModuleClientTestConfig):

    factory_params = [
        pytest.param(
            "HostName={hostname};DeviceId={device_id};ModuleId={module_id};SharedAccessKey={shared_access_key}".format(
                hostname=FAKE_HOSTNAME,
                device_id=FAKE_DEVICE_ID,
                module_id=FAKE_MODULE_ID,
                shared_access_key=FAKE_SYMMETRIC_KEY,
            ),
            None,
            id="Standard Connection String w/ SharedAccessKey + Default SSLContext",
        ),
        pytest.param(
            "HostName={hostname};DeviceId={device_id};ModuleId={module_id};SharedAccessKey={shared_access_key}".format(
                hostname=FAKE_HOSTNAME,
                device_id=FAKE_DEVICE_ID,
                module_id=FAKE_MODULE_ID,
                shared_access_key=FAKE_SYMMETRIC_KEY,
            ),
            lazy_fixture("custom_ssl_context"),
            id="Standard Connection String w/ SharedAccessKey + Custom SSLContext",
        ),
        pytest.param(
            "HostName={hostname};DeviceId={device_id};ModuleId={module_id};SharedAccessKey={shared_access_key};GatewayHostName={gateway_hostname}".format(
                hostname=FAKE_HOSTNAME,
                device_id=FAKE_DEVICE_ID,
                module_id=FAKE_MODULE_ID,
                shared_access_key=FAKE_SYMMETRIC_KEY,
                gateway_hostname=FAKE_GATEWAY_HOSTNAME,
            ),
            None,
            id="Edge Connection String w/ SharedAccessKey + Default SSLContext",
        ),
        pytest.param(
            "HostName={hostname};DeviceId={device_id};ModuleId={module_id};SharedAccessKey={shared_access_key};GatewayHostName={gateway_hostname}".format(
                hostname=FAKE_HOSTNAME,
                device_id=FAKE_DEVICE_ID,
                module_id=FAKE_MODULE_ID,
                shared_access_key=FAKE_SYMMETRIC_KEY,
                gateway_hostname=FAKE_GATEWAY_HOSTNAME,
            ),
            lazy_fixture("custom_ssl_context"),
            id="Edge Connection String w/ SharedAccessKey + Custom SSLContext",
        ),
        # NOTE: X509 certs imply use of custom SSLContext
        pytest.param(
            "HostName={hostname};DeviceId={device_id};ModuleId={module_id};x509=true".format(
                hostname=FAKE_HOSTNAME,
                device_id=FAKE_DEVICE_ID,
                module_id=FAKE_MODULE_ID,
            ),
            lazy_fixture("custom_ssl_context"),
            id="Standard Connection String w/ X509",
        ),
        pytest.param(
            "HostName={hostname};DeviceId={device_id};ModuleId={module_id};GatewayHostName={gateway_hostname};x509=true".format(
                hostname=FAKE_HOSTNAME,
                device_id=FAKE_DEVICE_ID,
                module_id=FAKE_MODULE_ID,
                gateway_hostname=FAKE_GATEWAY_HOSTNAME,
            ),
            lazy_fixture("custom_ssl_context"),
            id="Edge Connection String w/ X509",
        ),
    ]
    # Just the parameters for using standard connection strings
    factory_params_no_gateway = [
        param for param in factory_params if cs.GATEWAY_HOST_NAME not in param.values[0]
    ]
    # Just the parameters for using connection strings with a GatewayHostName
    factory_params_gateway = [
        param for param in factory_params if cs.GATEWAY_HOST_NAME in param.values[0]
    ]
    # Just the parameters where a custom SSLContext is provided
    factory_params_custom_ssl = [param for param in factory_params if param.values[1] is not None]
    # Just the parameters where a custom SSLContext is NOT provided
    factory_params_default_ssl = [param for param in factory_params if param.values[1] is None]
    # Just the parameters for using SharedAccessKeys
    factory_params_sak = [
        param for param in factory_params if cs.SHARED_ACCESS_KEY in param.values[0]
    ]
    # Just the parameters for NOT using SharedAccessKeys
    factory_params_no_sak = [
        param for param in factory_params if cs.SHARED_ACCESS_KEY not in param.values[0]
    ]

    @pytest.mark.it(
        "Returns a new IoTHubModuleClient instance, created with the use of a new IoTHubClientConfig object"
    )
    @pytest.mark.parametrize("connection_string, ssl_context", factory_params)
    async def test_instantiation(self, mocker, connection_string, ssl_context):
        spy_config_cls = mocker.spy(config, "IoTHubClientConfig")
        spy_client_init = mocker.spy(IoTHubModuleClient, "__init__")
        assert spy_config_cls.call_count == 0
        assert spy_client_init.call_count == 0

        client = await IoTHubModuleClient.create_from_connection_string(
            connection_string, ssl_context=ssl_context
        )

        assert spy_config_cls.call_count == 1
        assert spy_client_init.call_count == 1
        # NOTE: Normally passing through self or cls isn't necessary in a mock call, but
        # it seems that when mocking the __init__ it is. This is actually good though, as it
        # allows us to match the specific object reference which otherwise is very dicey when
        # mocking constructors/initializers
        assert spy_client_init.call_args == mocker.call(client, spy_config_cls.spy_return)
        assert isinstance(client, IoTHubModuleClient)

        # Graceful exit
        await client.shutdown()

    @pytest.mark.it(
        "Sets the `DeviceId` from the connection string as the `device_id` on the IoTHubClientConfig used to create the client"
    )
    @pytest.mark.parametrize("connection_string, ssl_context", factory_params)
    async def test_device_id(self, mocker, connection_string, ssl_context):
        spy_client_init = mocker.spy(IoTHubModuleClient, "__init__")
        # Create a ConnectionString object from the connection string to simply value access
        cs_obj = cs.ConnectionString(connection_string)

        client = await IoTHubModuleClient.create_from_connection_string(
            connection_string, ssl_context=ssl_context
        )

        assert spy_client_init.call_count == 1
        assert spy_client_init.call_args == mocker.call(client, mocker.ANY)
        config = spy_client_init.call_args[0][1]
        assert config.device_id == cs_obj[cs.DEVICE_ID]

        # Graceful exit
        await client.shutdown()

    @pytest.mark.it(
        "Sets the `ModuleId` from the connection string as the `module_id` on the IoTHubClientConfig used to create the client"
    )
    @pytest.mark.parametrize("connection_string, ssl_context", factory_params)
    async def test_module_id(self, mocker, connection_string, ssl_context):
        spy_client_init = mocker.spy(IoTHubModuleClient, "__init__")
        # Create a ConnectionString object from the connection string to simply value access
        cs_obj = cs.ConnectionString(connection_string)

        client = await IoTHubModuleClient.create_from_connection_string(
            connection_string, ssl_context=ssl_context
        )

        assert spy_client_init.call_count == 1
        assert spy_client_init.call_args == mocker.call(client, mocker.ANY)
        config = spy_client_init.call_args[0][1]
        assert config.module_id == cs_obj[cs.MODULE_ID]

        # Graceful exit
        await client.shutdown()

    @pytest.mark.it(
        "Sets the `HostName` from the connection string as the `hostname` on the IoTHubClientConfig, if no `GatewayHostName` is present in the connection string"
    )
    @pytest.mark.parametrize("connection_string, ssl_context", factory_params_no_gateway)
    async def test_hostname_cs_has_no_gateway(self, mocker, connection_string, ssl_context):
        spy_client_init = mocker.spy(IoTHubModuleClient, "__init__")
        # Create a ConnectionString object from the connection string to simply value access
        cs_obj = cs.ConnectionString(connection_string)
        assert cs.GATEWAY_HOST_NAME not in cs_obj

        client = await IoTHubModuleClient.create_from_connection_string(
            connection_string, ssl_context=ssl_context
        )

        assert spy_client_init.call_count == 1
        assert spy_client_init.call_args == mocker.call(client, mocker.ANY)
        config = spy_client_init.call_args[0][1]
        assert config.hostname == cs_obj[cs.HOST_NAME]

        # Graceful exit
        await client.shutdown()

    @pytest.mark.it(
        "Sets the `HostName` from the connection string as the `hostname` on the IoTHubClientConfig used to create the client, if no `GatewayHostName` is present in the connection string"
    )
    @pytest.mark.parametrize("connection_string, ssl_context", factory_params_gateway)
    async def test_hostname_cs_has_gateway(self, mocker, connection_string, ssl_context):
        spy_client_init = mocker.spy(IoTHubModuleClient, "__init__")
        # Create a ConnectionString object from the connection string to simply value access
        cs_obj = cs.ConnectionString(connection_string)
        assert cs.GATEWAY_HOST_NAME in cs_obj
        assert cs_obj[cs.GATEWAY_HOST_NAME] != cs_obj[cs.HOST_NAME]

        client = await IoTHubModuleClient.create_from_connection_string(
            connection_string, ssl_context=ssl_context
        )

        assert spy_client_init.call_count == 1
        assert spy_client_init.call_args == mocker.call(client, mocker.ANY)
        config = spy_client_init.call_args[0][1]
        assert config.hostname == cs_obj[cs.GATEWAY_HOST_NAME]

        # Graceful exit
        await client.shutdown()

    @pytest.mark.it(
        "Sets the provided `ssl_context` on the IoTHubClientConfig used to create the client, if provided"
    )
    @pytest.mark.parametrize("connection_string, ssl_context", factory_params_custom_ssl)
    async def test_custom_ssl_context(self, mocker, connection_string, ssl_context):
        spy_client_init = mocker.spy(IoTHubModuleClient, "__init__")
        assert ssl_context is not None

        client = await IoTHubModuleClient.create_from_connection_string(
            connection_string, ssl_context=ssl_context
        )

        assert spy_client_init.call_count == 1
        assert spy_client_init.call_args == mocker.call(client, mocker.ANY)
        config = spy_client_init.call_args[0][1]
        assert config.ssl_context is ssl_context

        # Graceful exit
        await client.shutdown()

    # NOTE: The details of this default SSLContext are covered in the TestDefaultSSLContext suite
    @pytest.mark.it(
        "Sets a default SSLContext as the `ssl_context` on the IoTHubClientConfig used to create the client, if `ssl_context` is not provided"
    )
    @pytest.mark.parametrize("connection_string, ssl_context", factory_params_default_ssl)
    async def test_default_ssl_context(self, mocker, connection_string, ssl_context):
        spy_client_init = mocker.spy(IoTHubModuleClient, "__init__")
        spy_default_ssl = mocker.spy(iothub_client, "_default_ssl_context")
        assert ssl_context is None

        client = await IoTHubModuleClient.create_from_connection_string(connection_string)

        assert spy_default_ssl.call_count == 1
        assert spy_default_ssl.call_args == mocker.call()
        assert spy_client_init.call_count == 1
        assert spy_client_init.call_args == mocker.call(client, mocker.ANY)
        config = spy_client_init.call_args[0][1]
        assert config.ssl_context is spy_default_ssl.spy_return

        # Graceful exit
        await client.shutdown()

    @pytest.mark.it(
        "Creates a SasTokenProvider that uses symmetric key-based token generation and sets it on the IoTHubClientConfig used to create the client, if `SharedAccessKey` is present in the connection string"
    )
    @pytest.mark.parametrize("connection_string, ssl_context", factory_params_sak)
    async def test_sk_auth(self, mocker, connection_string, ssl_context):
        # Create a ConnectionString object from the connection string to simply value access
        cs_obj = cs.ConnectionString(connection_string)
        assert cs.SHARED_ACCESS_KEY in cs_obj
        # Mock
        spy_client_init = mocker.spy(IoTHubModuleClient, "__init__")
        spy_sk_sm_cls = mocker.spy(sm, "SymmetricKeySigningMechanism")
        spy_st_generator_cls = mocker.spy(st, "InternalSasTokenGenerator")
        spy_st_provider_create = mocker.spy(st.SasTokenProvider, "create_from_generator")
        expected_token_uri = "{hostname}/devices/{device_id}/modules/{module_id}".format(
            hostname=cs_obj.get(cs.GATEWAY_HOST_NAME, default=cs_obj[cs.HOST_NAME]),
            device_id=cs_obj[cs.DEVICE_ID],
            module_id=cs_obj[cs.MODULE_ID],
        )

        client = await IoTHubModuleClient.create_from_connection_string(
            connection_string, ssl_context=ssl_context
        )

        # SymmetricKeySigningMechanism was created from the SharedAccessKey
        assert spy_sk_sm_cls.call_count == 1
        assert spy_sk_sm_cls.call_args == mocker.call(cs_obj[cs.SHARED_ACCESS_KEY])
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
        assert spy_client_init.call_args == mocker.call(client, mocker.ANY)
        config = spy_client_init.call_args[0][1]
        assert config.sastoken_provider is spy_st_provider_create.spy_return

        # Graceful exit
        await client.shutdown()

    @pytest.mark.it(
        "Does not set any SasTokenProvider on the IoTHubClientConfig used to create the client if no `SharedAccessKey` is present in the connection string"
    )
    @pytest.mark.parametrize("connection_string, ssl_context", factory_params_no_sak)
    async def test_non_sas_auth(self, mocker, connection_string, ssl_context):
        spy_client_init = mocker.spy(IoTHubModuleClient, "__init__")
        # Create a ConnectionString object from the connection string to simply value access
        cs_obj = cs.ConnectionString(connection_string)
        assert cs.SHARED_ACCESS_KEY not in cs_obj

        client = await IoTHubModuleClient.create_from_connection_string(
            connection_string, ssl_context=ssl_context
        )

        # No SasTokenProvider was set on the IoTHubClientConfig that was used to instantiate the client
        assert spy_client_init.call_count == 1
        assert spy_client_init.call_args == mocker.call(client, mocker.ANY)
        config = spy_client_init.call_args[0][1]
        assert config.sastoken_provider is None

        # Graceful exit
        await client.shutdown()

    @pytest.mark.it(
        "Sets any provided optional keyword arguments on IoTHubClientConfig used to create the client"
    )
    @pytest.mark.parametrize("connection_string, ssl_context", factory_params)
    @pytest.mark.parametrize("kwarg_name, kwarg_value", factory_kwargs)
    async def test_kwargs(self, mocker, connection_string, ssl_context, kwarg_name, kwarg_value):
        spy_client_init = mocker.spy(IoTHubModuleClient, "__init__")

        kwargs = {kwarg_name: kwarg_value}

        client = await IoTHubModuleClient.create_from_connection_string(
            connection_string, ssl_context=ssl_context, **kwargs
        )

        assert spy_client_init.call_count == 1
        assert spy_client_init.call_args == mocker.call(client, mocker.ANY)
        config = spy_client_init.call_args[0][1]
        assert getattr(config, kwarg_name) == kwarg_value

        # Graceful exit
        await client.shutdown()

    @pytest.mark.it("Raises ValueError if a `ModuleId` is not present in the connection string")
    async def test_module_id_in_string(self, optional_ssl_context):
        # NOTE: There could be many strings containing not containing a ModuleId, but I'm not going
        # to try them all to avoid confounds with other errors, I'll just use a standard device
        # string that uses a SharedAccessKey
        connection_string = (
            "HostName={hostname};DeviceId={device_id};SharedAccessKey={shared_access_key}".format(
                hostname=FAKE_HOSTNAME,
                device_id=FAKE_DEVICE_ID,
                shared_access_key=FAKE_SYMMETRIC_KEY,
            )
        )
        with pytest.raises(ValueError):
            await IoTHubModuleClient.create_from_connection_string(
                connection_string, ssl_context=optional_ssl_context
            )

    @pytest.mark.it(
        "Raises ValueError if `x509=true` is present in the connection string, but no `ssl_context` is provided"
    )
    @pytest.mark.parametrize("connection_string, ssl_context", factory_params_no_sak)
    async def test_x509_with_no_ssl(self, connection_string, ssl_context):
        # Ignore the ssl_context provided by the parametrization
        with pytest.raises(ValueError):
            await IoTHubModuleClient.create_from_connection_string(connection_string)

    @pytest.mark.it(
        "Does not raise a ValueError if `x509=false` is present in the connection string and no `ssl_context` is provided"
    )
    async def test_x509_equals_false(self):
        # NOTE: This is a weird test in that if you aren't using X509 certs, there shouldn't be
        # an `x509` field in your connection string in the first place. But, semantically, it feels
        # as though this test ought to exist to validate that we are checking the value of the
        # field, not just the key name.
        # NOTE: Because we're in the land of undefined behavior here, on account of this scenario
        # not being supposed to happen, I'm arbitrarily deciding we're testing this with a string
        # containing a SharedAccessKey and no GatewayHostName for simplicity.
        connection_string = "HostName={hostname};DeviceId={device_id};ModuleId={module_id};SharedAccessKey={shared_access_key};x509=false".format(
            hostname=FAKE_HOSTNAME,
            device_id=FAKE_DEVICE_ID,
            module_id=FAKE_MODULE_ID,
            shared_access_key=FAKE_SYMMETRIC_KEY,
        )
        client = await IoTHubModuleClient.create_from_connection_string(connection_string)
        # If the above invocation didn't raise, the test passed, no assertions required

        # Graceful exit
        await client.shutdown()

    @pytest.mark.it("Allows any exceptions raised when parsing the connection string to propagate")
    @pytest.mark.parametrize(
        "exception",
        [
            pytest.param(ValueError(), id="ValueError"),
            pytest.param(lazy_fixture("arbitrary_exception"), id="Unexpected Exception"),
        ],
    )
    async def test_cs_parsing_raises(self, mocker, optional_ssl_context, exception):
        # NOTE: This test covers all invalid connection string scenarios. For more detail, see the
        # dedicated connection string parsing tests for the `connection_string.py` module - there's
        # no reason to replicate them all here.
        # NOTE: For the purposes of this test, it does not matter what this connection string is.
        # The one provided here is valid, but the mock will cause the parsing to raise anyway.
        connection_string = "HostName={hostname};DeviceId={device_id};ModuleId={module_id};SharedAccessKey={shared_access_key}".format(
            hostname=FAKE_HOSTNAME,
            device_id=FAKE_DEVICE_ID,
            module_id=FAKE_MODULE_ID,
            shared_access_key=FAKE_SYMMETRIC_KEY,
        )
        # Mock cs parsing
        mocker.patch.object(cs, "ConnectionString", side_effect=exception)

        with pytest.raises(type(exception)) as e_info:
            await IoTHubModuleClient.create_from_connection_string(
                connection_string, ssl_context=optional_ssl_context
            )
        assert e_info.value is exception

    @pytest.mark.it(
        "Allows any exceptions raised when creating a SymmetricKeySigningMechanism to propagate"
    )
    @pytest.mark.parametrize("connection_string, ssl_context", factory_params_sak)
    @pytest.mark.parametrize("exception", sk_sm_create_exceptions)
    async def test_sksm_raises(self, mocker, connection_string, ssl_context, exception):
        mocker.patch.object(sm, "SymmetricKeySigningMechanism", side_effect=exception)

        with pytest.raises(type(exception)) as e_info:
            await IoTHubModuleClient.create_from_connection_string(
                connection_string,
                ssl_context=ssl_context,
            )
        assert e_info.value is exception

    @pytest.mark.it("Allows any exceptions raised when creating a SasTokenProvider to propagate")
    @pytest.mark.parametrize("connection_string, ssl_context", factory_params_sak)
    @pytest.mark.parametrize("exception", sastoken_provider_create_exceptions)
    async def test_sastoken_provider_raises(
        self, mocker, connection_string, ssl_context, exception
    ):
        mocker.patch.object(st.SasTokenProvider, "create_from_generator", side_effect=exception)

        with pytest.raises(type(exception)) as e_info:
            await IoTHubModuleClient.create_from_connection_string(
                connection_string,
                ssl_context=ssl_context,
            )
        assert e_info.value is exception

    @pytest.mark.it("Can be cancelled while waiting for SasTokenProvider creation")
    @pytest.mark.parametrize("connection_string, ssl_context", factory_params_sak)
    async def test_cancel_during_sastoken_provider_creation(
        self, mocker, connection_string, ssl_context
    ):
        mocker.patch.object(
            st.SasTokenProvider, "create_from_generator", custom_mock.HangingAsyncMock()
        )

        coro = IoTHubModuleClient.create_from_connection_string(
            connection_string,
            ssl_context=ssl_context,
        )
        t = asyncio.create_task(coro)

        # Hanging, waiting for SasTokenProvider creation to finish
        await st.SasTokenProvider.create_from_generator.wait_for_hang()
        assert not t.done()

        # Cancel
        t.cancel()
        with pytest.raises(asyncio.CancelledError):
            await t


@pytest.mark.describe(
    "IoTHubModuleClient - .create_from_edge_environment() -- Real Edge Environment"
)
class TestIoTHubModuleClientCreateFromEdgeEnvironmentRealEdgeEnvironment(
    IoTHubModuleClientTestConfig
):
    @pytest.fixture
    def edge_environment_variables(self):
        return {
            "IOTEDGE_DEVICEID": FAKE_DEVICE_ID,
            "IOTEDGE_MODULEID": FAKE_MODULE_ID,
            "IOTEDGE_IOTHUBHOSTNAME": FAKE_HOSTNAME,
            "IOTEDGE_GATEWAYHOSTNAME": FAKE_GATEWAY_HOSTNAME,
            "IOTEDGE_APIVERSION": "04-07-3023",
            "IOTEDGE_MODULEGENERATIONID": "fake_generation_id",
            "IOTEDGE_WORKLOADURI": "http://fake.workload/uri/",
            # NOTE: I've included the IOTHUBHOSTNAME environment variable here,
            # even though it is not actually used in practice by the client.
            # By including it here, we can demonstrate that it is not used.
        }

    @pytest.fixture(autouse=True)
    def mock_environment_variables(self, mocker, edge_environment_variables):
        """Auto-used fixture that will mock out os.environ to return the variables defined
        in the fixture above. You shouldn't need to directly interact with this mock, so
        no value is returned by this fixture, and as a result, you shouldn't ever need to
        add it as a test parameter. It will just work"""
        mocker.patch.dict(os.environ, edge_environment_variables, clear=True)

    @pytest.fixture(autouse=True)
    def mock_ssl_load_verify_locations(self, mocker):
        """Autouse fixture that will mock SSL cert chain loading so that fake values don't
        get in the way. You shouldn't need to directly interact with this mock, so no value
        is returned by this fixture, and as a result, you should'nt ever need to add it as a
        test parameter. It will just work
        """
        mocker.patch.object(ssl.SSLContext, "load_verify_locations")

    @pytest.fixture(autouse=True)
    def mock_edge_hsm_cls(self, mocker):
        mock_edge_hsm_cls = mocker.patch.object(edge_hsm, "IoTEdgeHsm", spec=edge_hsm.IoTEdgeHsm)
        mock_edge_hsm_cls.return_value.sign.return_value = FAKE_SIGNATURE
        mock_edge_hsm_cls.return_value.get_certificate.return_value = "fake_svc_string"
        return mock_edge_hsm_cls

    @pytest.mark.it(
        "Returns a new IoTHubModuleClient instance, created with the use of a new IoTHubClientConfig object"
    )
    async def test_instantiation(self, mocker):
        spy_config_cls = mocker.spy(config, "IoTHubClientConfig")
        spy_client_init = mocker.spy(IoTHubModuleClient, "__init__")
        assert spy_config_cls.call_count == 0
        assert spy_client_init.call_count == 0

        client = await IoTHubModuleClient.create_from_edge_environment()

        assert spy_config_cls.call_count == 1
        assert spy_client_init.call_count == 1
        # NOTE: Normally passing through self or cls isn't necessary in a mock call, but
        # it seems that when mocking the __init__ it is. This is actually good though, as it
        # allows us to match the specific object reference which otherwise is very dicey when
        # mocking constructors/initializers
        assert spy_client_init.call_args == mocker.call(client, spy_config_cls.spy_return)
        assert isinstance(client, IoTHubModuleClient)

        # Graceful exit
        await client.shutdown()

    @pytest.mark.it(
        "Sets the IOTEDGE_DEVICEID value from the Edge environment as the `device_id` on the IoTHubClientConfig used to create the client"
    )
    async def test_device_id(self, mocker, edge_environment_variables):
        spy_client_init = mocker.spy(IoTHubModuleClient, "__init__")

        client = await IoTHubModuleClient.create_from_edge_environment()

        assert spy_client_init.call_count == 1
        assert spy_client_init.call_args == mocker.call(client, mocker.ANY)
        config = spy_client_init.call_args[0][1]
        assert config.device_id == edge_environment_variables["IOTEDGE_DEVICEID"]

        # Graceful exit
        await client.shutdown()

    @pytest.mark.it(
        "Sets the IOTEDGE_MODULEID value from the Edge environment as the `module_id` on the IoTHubClientConfig used to create the client"
    )
    async def test_module_id(self, mocker, edge_environment_variables):
        spy_client_init = mocker.spy(IoTHubModuleClient, "__init__")

        client = await IoTHubModuleClient.create_from_edge_environment()

        assert spy_client_init.call_count == 1
        assert spy_client_init.call_args == mocker.call(client, mocker.ANY)
        config = spy_client_init.call_args[0][1]
        assert config.module_id == edge_environment_variables["IOTEDGE_MODULEID"]

        # Graceful exit
        await client.shutdown()

    @pytest.mark.it(
        "Sets the IOTEDGE_GATEWAYHOSTNAME (and NOT the IOTEDGE_IOTHUBHOSTNAME) value from the Edge environment as the `hostname` on the IoTHubClientConfig used to create the client"
    )
    async def test_hostname(self, mocker, edge_environment_variables):
        spy_client_init = mocker.spy(IoTHubModuleClient, "__init__")

        client = await IoTHubModuleClient.create_from_edge_environment()

        assert spy_client_init.call_count == 1
        assert spy_client_init.call_args == mocker.call(client, mocker.ANY)
        config = spy_client_init.call_args[0][1]
        assert config.hostname == edge_environment_variables["IOTEDGE_GATEWAYHOSTNAME"]
        assert config.hostname != edge_environment_variables["IOTEDGE_IOTHUBHOSTNAME"]

        # Graceful exit
        await client.shutdown()

    @pytest.mark.it("Creates an IoTEdgeHsm using values from the Edge environment")
    async def test_edge_hsm(self, mocker, edge_environment_variables, mock_edge_hsm_cls):
        assert mock_edge_hsm_cls.call_count == 0

        client = await IoTHubModuleClient.create_from_edge_environment()

        assert mock_edge_hsm_cls.call_count == 1
        assert mock_edge_hsm_cls.call_args == mocker.call(
            module_id=edge_environment_variables["IOTEDGE_MODULEID"],
            generation_id=edge_environment_variables["IOTEDGE_MODULEGENERATIONID"],
            workload_uri=edge_environment_variables["IOTEDGE_WORKLOADURI"],
            api_version=edge_environment_variables["IOTEDGE_APIVERSION"],
        )

        # Graceful exit
        await client.shutdown()

    @pytest.mark.it(
        "Creates a SasTokenProvider that uses the IoTEdgeHsm to generate SAS tokens, and sets it as the `sastoken_provider` on the IoTHubClientConfig used to create the client"
    )
    async def test_sastoken_provider(self, mocker, edge_environment_variables, mock_edge_hsm_cls):
        spy_client_init = mocker.spy(IoTHubModuleClient, "__init__")
        spy_st_generator_cls = mocker.spy(st, "InternalSasTokenGenerator")
        spy_st_provider_create = mocker.spy(st.SasTokenProvider, "create_from_generator")
        expected_token_uri = "{hostname}/devices/{device_id}/modules/{module_id}".format(
            hostname=edge_environment_variables["IOTEDGE_GATEWAYHOSTNAME"],
            device_id=edge_environment_variables["IOTEDGE_DEVICEID"],
            module_id=edge_environment_variables["IOTEDGE_MODULEID"],
        )

        client = await IoTHubModuleClient.create_from_edge_environment()

        # IoTEdgeHsm was created
        assert mock_edge_hsm_cls.call_count == 1
        # InternalSasTokenGenerator was created from the IoTEdgeHsm and expected URI
        assert spy_st_generator_cls.call_count == 1
        assert spy_st_generator_cls.call_args == mocker.call(
            signing_mechanism=mock_edge_hsm_cls.return_value, uri=expected_token_uri
        )
        # SasTokenProvider was created from the InternalSasTokenGenerator
        assert spy_st_provider_create.call_count == 1
        assert spy_st_provider_create.call_args == mocker.call(spy_st_generator_cls.spy_return)
        # The SasTokenProvider was set on the IoTHubClientConfig that was used to instantiate the client
        assert spy_client_init.call_count == 1
        assert spy_client_init.call_args == mocker.call(client, mocker.ANY)
        config = spy_client_init.call_args[0][1]
        assert config.sastoken_provider is spy_st_provider_create.spy_return

        # Graceful exit
        await client.shutdown()

    # NOTE: The details of this default SSLContext are covered in the TestDefaultSSLContext suite
    @pytest.mark.it(
        "Modifies a default SSLContext by loading a server verification certificate retrieved from the IoTEdgeHsm and sets it as the `ssl_context` on the IoTHubClientConfig used to create the client"
    )
    async def test_ssl_context(self, mocker, mock_edge_hsm_cls):
        mock_edge_hsm = mock_edge_hsm_cls.return_value
        spy_client_init = mocker.spy(IoTHubModuleClient, "__init__")
        mock_default_ssl = mocker.patch.object(iothub_client, "_default_ssl_context")
        mock_ssl_context = mock_default_ssl.return_value

        client = await IoTHubModuleClient.create_from_edge_environment()

        assert mock_default_ssl.call_count == 1
        assert mock_default_ssl.call_args == mocker.call()
        assert spy_client_init.call_count == 1
        assert spy_client_init.call_args == mocker.call(client, mocker.ANY)
        # SSLContext was set on the Config
        config = spy_client_init.call_args[0][1]
        assert config.ssl_context is mock_ssl_context
        # SSLContext was modified to load the cert returned by the HSM
        expected_sv_cert = mock_edge_hsm.get_certificate.return_value
        assert mock_ssl_context.load_verify_locations.call_count == 1
        assert mock_ssl_context.load_verify_locations.call_args == mocker.call(
            cadata=expected_sv_cert
        )

        # Graceful exit
        await client.shutdown()

    @pytest.mark.it(
        "Sets any provided optional keyword arguments on IoTHubClientConfig used to create the client"
    )
    @pytest.mark.parametrize("kwarg_name, kwarg_value", factory_kwargs)
    async def test_kwargs(self, mocker, kwarg_name, kwarg_value):
        spy_client_init = mocker.spy(IoTHubModuleClient, "__init__")

        kwargs = {kwarg_name: kwarg_value}

        client = await IoTHubModuleClient.create_from_edge_environment(**kwargs)

        assert spy_client_init.call_count == 1
        assert spy_client_init.call_args == mocker.call(client, mocker.ANY)
        config = spy_client_init.call_args[0][1]
        assert getattr(config, kwarg_name) == kwarg_value

        # Graceful exit
        await client.shutdown()

    # NOTE: For what happens when the simulator variables ARE present, see the
    # TestIoTHubModuleClientCreateFromEdgeEnvironmentSimulatedEdgeEnvironment test suite.
    @pytest.mark.it(
        "Raises IoTEdgeEnvironmentError if any expected environment variables cannot be found in the Edge environment, and no Edge Simulator variables are present either"
    )
    @pytest.mark.parametrize(
        "missing_variable",
        [
            "IOTEDGE_MODULEID",
            "IOTEDGE_DEVICEID",
            "IOTEDGE_GATEWAYHOSTNAME",
            "IOTEDGE_APIVERSION",
            "IOTEDGE_MODULEGENERATIONID",
            "IOTEDGE_WORKLOADURI",
            # NOTE: "IOTEDGE_IOTHUBHOSTNAME" is not listed here, because it is not required
        ],
    )
    async def test_env_missing_vars(self, mocker, edge_environment_variables, missing_variable):
        # Remove variable from env and re-patch
        del edge_environment_variables[missing_variable]
        mocker.patch.dict(os.environ, edge_environment_variables, clear=True)
        # No simulator variables are in the environment either
        assert "EdgeHubConnectionString" not in edge_environment_variables
        assert "EdgeModuleCACertificateFile" not in edge_environment_variables

        with pytest.raises(iot_exceptions.IoTEdgeEnvironmentError):
            await IoTHubModuleClient.create_from_edge_environment()

    @pytest.mark.it("Allows any exceptions raised while creating the IoTEdgeHsm to propagate")
    @pytest.mark.parametrize(
        "exception",
        [
            pytest.param(ValueError(), id="ValueError"),
            pytest.param(TypeError(), id="TypeError"),
            pytest.param(lazy_fixture("arbitrary_exception"), id="Unexpected Exception"),
        ],
    )
    async def test_edge_hsm_instantiation_raises(self, mock_edge_hsm_cls, exception):
        # NOTE: Why might this raise? Lots of reasons, probably due to corrupted env variables
        mock_edge_hsm_cls.side_effect = exception

        with pytest.raises(type(exception)) as e_info:
            await IoTHubModuleClient.create_from_edge_environment()
        assert e_info.value is exception

    @pytest.mark.it(
        "Allows any exceptions raised while fetching the server verification cert using the IoTEdgeHsm to propagate"
    )
    @pytest.mark.parametrize(
        "exception",
        [
            pytest.param(iot_exceptions.IoTEdgeError(), id="IoTEdgeError"),
            pytest.param(lazy_fixture("arbitrary_exception"), id="Unexpected Exception"),
        ],
    )
    async def test_edge_hsm_get_cert_raises(self, mock_edge_hsm_cls, exception):
        mock_edge_hsm_cls.return_value.get_certificate.side_effect = exception

        with pytest.raises(type(exception)) as e_info:
            await IoTHubModuleClient.create_from_edge_environment()
        assert e_info.value is exception

    @pytest.mark.it(
        "Allows any exceptions raised while loading the server verification cert to propagate"
    )
    @pytest.mark.parametrize(
        "exception",
        [
            pytest.param(ValueError(), id="ValueError"),
            pytest.param(TypeError(), id="TypeError"),
            pytest.param(lazy_fixture("arbitrary_exception"), id="Unexpected Exception"),
        ],
    )
    async def test_ssl_load_verify_locations_raises(self, mocker, exception):
        mocker.patch.object(ssl.SSLContext, "load_verify_locations", side_effect=exception)

        with pytest.raises(type(exception)) as e_info:
            await IoTHubModuleClient.create_from_edge_environment()
        assert e_info.value is exception

    @pytest.mark.it("Allows any exceptions raised when creating a SasTokenProvider to propagate")
    @pytest.mark.parametrize("exception", sastoken_provider_create_exceptions)
    async def test_sastoken_provider_raises(self, mocker, exception):
        mocker.patch.object(st.SasTokenProvider, "create_from_generator", side_effect=exception)

        with pytest.raises(type(exception)) as e_info:
            await IoTHubModuleClient.create_from_edge_environment()
        assert e_info.value is exception

    @pytest.mark.it(
        "Can be cancelled while waiting for the server verification cert to be retrieved"
    )
    async def test_cancel_during_get_certificate(self, mock_edge_hsm_cls):
        mock_edge_hsm = mock_edge_hsm_cls.return_value
        mock_edge_hsm.get_certificate = custom_mock.HangingAsyncMock()

        t = asyncio.create_task(IoTHubModuleClient.create_from_edge_environment())

        # Hanging, waiting for certificate retrieval to finish
        await mock_edge_hsm.get_certificate.wait_for_hang()
        assert not t.done()

        # Cancel
        t.cancel()
        with pytest.raises(asyncio.CancelledError):
            await t

    @pytest.mark.it("Can be cancelled while waiting for SasTokenProvider creation")
    async def test_cancel_during_sastoken_provider_creation(self, mocker):
        mocker.patch.object(
            st.SasTokenProvider, "create_from_generator", custom_mock.HangingAsyncMock()
        )

        t = asyncio.create_task(IoTHubModuleClient.create_from_edge_environment())

        # Hanging, waiting for SasTokenProvider creation to finish
        await st.SasTokenProvider.create_from_generator.wait_for_hang()
        assert not t.done()

        # Cancel
        t.cancel()
        with pytest.raises(asyncio.CancelledError):
            await t


@pytest.mark.describe(
    "IoTHubModuleClient - .create_from_edge_environment() -- Simulated Edge Environment"
)
class TestIoTHubModuleClientCreateFromEdgeEnvironmentSimulatedEdgeEnvironment(
    IoTHubModuleClientTestConfig
):
    @pytest.fixture
    def edge_environment_variables(self):
        edge_cs = "HostName={hostname};DeviceId={device_id};ModuleId={module_id};SharedAccessKey={shared_access_key};GatewayHostName={gateway_hostname}".format(
            hostname=FAKE_HOSTNAME,
            device_id=FAKE_DEVICE_ID,
            module_id=FAKE_MODULE_ID,
            shared_access_key=FAKE_SYMMETRIC_KEY,
            gateway_hostname=FAKE_GATEWAY_HOSTNAME,
        )
        return {
            "EdgeHubConnectionString": edge_cs,
            "EdgeModuleCACertificateFile": "fake/file/path",
        }

    @pytest.fixture(autouse=True)
    def mock_environment_variables(self, mocker, edge_environment_variables):
        """Auto-used fixture that will mock out os.environ to return the variables defined
        in the fixture above. You shouldn't need to directly interact with this mock, so
        no value is returned by this fixture, and as a result, you shouldn't ever need to
        add it as a test parameter. It will just work"""
        mocker.patch.dict(os.environ, edge_environment_variables, clear=True)

    @pytest.fixture(autouse=True)
    def mock_ssl_load_verify_locations(self, mocker):
        """Autouse fixture that will mock SSL cert chain loading so that fake values don't
        get in the way. You shouldn't need to directly interact with this mock, so no value
        is returned by this fixture, and as a result, you should'nt ever need to add it as a
        test parameter. It will just work
        """
        mocker.patch.object(ssl.SSLContext, "load_verify_locations")

    @pytest.mark.it(
        "Invokes and returns the result of the .create_from_connection_string() factory method, passing a connection string contained in the `EdgeHubConnectionString` environment variable and a default SSLContext"
    )
    async def test_invokes_connection_string_factory(self, mocker, edge_environment_variables):
        spy_create_from_cs = mocker.spy(IoTHubModuleClient, "create_from_connection_string")
        mock_default_ssl = mocker.patch.object(iothub_client, "_default_ssl_context")

        client = await IoTHubModuleClient.create_from_edge_environment()

        assert spy_create_from_cs.await_count == 1
        assert spy_create_from_cs.await_args == mocker.call(
            edge_environment_variables["EdgeHubConnectionString"],
            ssl_context=mock_default_ssl.return_value,
        )
        assert client is spy_create_from_cs.spy_return
        assert isinstance(client, IoTHubModuleClient)

        # Graceful exit
        await client.shutdown()

    @pytest.mark.it(
        "Modifies the default SSLContext by loading a server verification certificate from the filepath contained in the `EdgeModuleCACertificate` environment variable"
    )
    async def test_ssl_context(self, mocker, edge_environment_variables):
        spy_create_from_cs = mocker.spy(IoTHubModuleClient, "create_from_connection_string")
        mock_default_ssl = mocker.patch.object(iothub_client, "_default_ssl_context")
        mock_ssl_context = mock_default_ssl.return_value

        client = await IoTHubModuleClient.create_from_edge_environment()

        assert mock_default_ssl.call_count == 1
        assert mock_default_ssl.call_args == mocker.call()
        # SSLContext was modified to the load the certfile in the environment variable
        assert mock_ssl_context.load_verify_locations.call_count == 1
        assert mock_ssl_context.load_verify_locations.call_args == mocker.call(
            cafile=edge_environment_variables["EdgeModuleCACertificateFile"]
        )
        # SSLContext was the one passed to the .create_from_connection_string() factory method
        assert spy_create_from_cs.await_count == 1
        assert spy_create_from_cs.await_args == mocker.call(
            mocker.ANY, ssl_context=mock_ssl_context
        )

        # Graceful exit
        await client.shutdown()

    @pytest.mark.it(
        "Passes any provided optional keyword arguments to the .create_from_connection_string() factory method"
    )
    @pytest.mark.parametrize("kwarg_name, kwarg_value", factory_kwargs)
    async def test_kwargs(self, mocker, kwarg_name, kwarg_value):
        spy_create_from_cs = mocker.spy(IoTHubModuleClient, "create_from_connection_string")
        kwargs = {kwarg_name: kwarg_value}

        client = await IoTHubModuleClient.create_from_edge_environment(**kwargs)

        assert spy_create_from_cs.await_count == 1
        assert spy_create_from_cs.await_args == mocker.call(
            mocker.ANY, ssl_context=mocker.ANY, **kwargs
        )

        # Graceful exit
        await client.shutdown()

    @pytest.mark.it(
        "Does not invoke .create_from_connection_string() at all if real Edge environment variables are found"
    )
    async def test_real_env_variables_found(self, mocker):
        spy_create_from_cs = mocker.spy(IoTHubModuleClient, "create_from_connection_string")
        # Mock Edge HSM from the Real Edge path, since it's where we're going to go
        mock_edge_hsm_cls = mocker.patch.object(edge_hsm, "IoTEdgeHsm", spec=edge_hsm.IoTEdgeHsm)
        mock_edge_hsm_cls.return_value.sign.return_value = FAKE_SIGNATURE
        mock_edge_hsm_cls.return_value.get_certificate.return_value = "fake_svc_string"
        # Add the Real Edge env vars to our environment
        real_env_vars = {
            "IOTEDGE_DEVICEID": FAKE_DEVICE_ID,
            "IOTEDGE_MODULEID": FAKE_MODULE_ID,
            "IOTEDGE_IOTHUBHOSTNAME": FAKE_HOSTNAME,
            "IOTEDGE_GATEWAYHOSTNAME": FAKE_GATEWAY_HOSTNAME,
            "IOTEDGE_APIVERSION": "04-07-3023",
            "IOTEDGE_MODULEGENERATIONID": "fake_generation_id",
            "IOTEDGE_WORKLOADURI": "http://fake.workload/uri/",
        }
        mocker.patch.dict(os.environ, real_env_vars, clear=False)
        # The Simulator variables are also here
        assert "EdgeHubConnectionString" in os.environ
        assert "EdgeModuleCACertificateFile" in os.environ

        client = await IoTHubModuleClient.create_from_edge_environment()

        # But we did not follow the Simulator path due to real variables existing
        assert spy_create_from_cs.await_count == 0
        # Instead we followed the Real Edge path
        assert mock_edge_hsm_cls.call_count == 1
        # NOTE: I could show all the mocks and values that get invoked here, but there's a whole
        # test suite dedicated to those so no point in replicating it here.

        # Graceful exit
        await client.shutdown()

    @pytest.mark.it(
        "Raises IoTEdgeEnvironmentError if any expected environment variables cannot be found in the Edge environment"
    )
    @pytest.mark.parametrize(
        "missing_variable", ["EdgeHubConnectionString", "EdgeModuleCACertificateFile"]
    )
    async def test_env_missing_vars(self, mocker, edge_environment_variables, missing_variable):
        # Remove variable from env and re-patch
        del edge_environment_variables[missing_variable]
        mocker.patch.dict(os.environ, edge_environment_variables, clear=True)

        with pytest.raises(iot_exceptions.IoTEdgeEnvironmentError):
            await IoTHubModuleClient.create_from_edge_environment()

    @pytest.mark.it(
        "Allows any exceptions raised by the .create_from_connection_string() factory method to propagate"
    )
    @pytest.mark.parametrize(
        "exception",
        [
            pytest.param(ValueError(), id="ValueError"),
            pytest.param(st.SasTokenError(), id="SasTokenError"),
            pytest.param(lazy_fixture("arbitrary_exception"), id="Unexpected Exception"),
        ],
    )
    async def test_create_from_connection_string_raises(self, mocker, exception):
        mocker.patch.object(
            IoTHubModuleClient, "create_from_connection_string", side_effect=exception
        )

        with pytest.raises(type(exception)) as e_info:
            await IoTHubModuleClient.create_from_edge_environment()
        assert e_info.value is exception

    @pytest.mark.it(
        "Can be cancelled while waiting for the client to be created from the connection string"
    )
    async def test_cancelled_during_create_from_connection_string(self, mocker):
        mocker.patch.object(
            IoTHubModuleClient, "create_from_connection_string", custom_mock.HangingAsyncMock()
        )

        t = asyncio.create_task(IoTHubModuleClient.create_from_edge_environment())

        # Hanging, waiting for client instantiation via connection string
        await IoTHubModuleClient.create_from_connection_string.wait_for_hang()
        assert not t.done()

        # Cancel
        t.cancel()
        with pytest.raises(asyncio.CancelledError):
            await t


@pytest.mark.describe("IoTHubModuleClient - .shutdown()")
class TestIoTHubModuleClientShutdown(SharedClientShutdownTests, IoTHubModuleClientTestConfig):
    pass


# NOTE: This is a convention-private helper, which would normally just be implicitly tested, but
# since it is used so frequently, it's easier to just test separately
@pytest.mark.describe("Default SSLContext")
class TestDefaultSSLContext:
    @pytest.mark.it("Returns an SSLContext")
    def test_is_ssl_context(self):
        ctx = iothub_client._default_ssl_context()
        assert isinstance(ctx, ssl.SSLContext)

    @pytest.mark.it("Sets the protocol of the SSLContext to PROTOCOL_TLS_CLIENT")
    def test_protocol(self):
        ctx = iothub_client._default_ssl_context()
        assert ctx.protocol == ssl.PROTOCOL_TLS_CLIENT

    @pytest.mark.it("Sets the verify mode of the SSLContext to CERT_REQUIRED")
    def test_verify_mode(self):
        ctx = iothub_client._default_ssl_context()
        assert ctx.verify_mode == ssl.CERT_REQUIRED

    @pytest.mark.it("Sets the `check_hostname` flag on the SSLContext to True")
    def test_check_hostname(self):
        ctx = iothub_client._default_ssl_context()
        assert ctx.check_hostname is True

    @pytest.mark.it("Loads the default certificate chain on the SSLContext")
    def test_default_certs(self, mocker):
        mocker.patch.object(ssl, "SSLContext")
        mock_ctx = iothub_client._default_ssl_context()
        assert mock_ctx.load_default_certs.call_count == 1
        assert mock_ctx.load_default_certs.call_args == mocker.call()
