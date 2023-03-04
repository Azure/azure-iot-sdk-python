# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import asyncio
import pytest
import ssl
import time
from dev_utils import custom_mock
from pytest_lazyfixture import lazy_fixture
from v3_async_wip.iothub_client import IoTHubDeviceClient, IoTHubModuleClient
from v3_async_wip import config, iothub_client
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

# TODO: Why are these create tests so slow?
# It's not due to the shutdown method. Auth?


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


# # Mock out all auth-related objects to improve test performance
# @pytest.fixture(autouse=True)
# def mock_all_auth(mocker):
#     mocker.patch.object(st, "SasTokenProvider", spec=st.SasTokenProvider)
#     mocker.patch.object(st, "InternalSasTokenGenerator", spec=st.InternalSasTokenGenerator)
#     mocker.patch.object(st, "ExternalSasTokenGenerator", spec=st.ExternalSasTokenGenerator)
#     mocker.patch.object(sm, "SymmetricKeySigningMechanism", spec=sm.SymmetricKeySigningMechanism)


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
# Define parametrizations that will be used across multiple tests, and that may eventually need
# to be changed everywhere, e.g. new auth scheme added.


# Parameters for arguments to the .create() method of clients. Represent different types of
# authentication. Use this parametrization whenever possible on .create() tests.
# NOTE: Do NOT combine this with the SSL fixtures above. This parametrization contains
# it where necessary, as not all entries can be combined with SSL.
auth_configurations = [
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

# Similar to the above, but only SAS related configurations, and no variable SSLContext.
# Use this when testing SAS-specific functionality.
# If SSLContext is needed (it usually is) use the SAS fixtures above in tandem with these.
sas_auth_configurations = [
    # Provides args in the form 'symmetric_key, 'sastoken_fn'
    pytest.param(FAKE_SYMMETRIC_KEY, None, id="Symmetric Key SAS Auth"),
    pytest.param(None, sastoken_generator_fn, id="User-Provided SAS Token Auth"),
]

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

    @pytest.mark.it("Shuts down SasTokenProvider (if present)")
    async def test_sastoken_provider_shutdown(self, client):
        pass

    # TODO: cancel tests


# ~~~~~ IoTHubDeviceClient Tests ~~~~~


class IoTHubDeviceClientTestConfig:
    """Mixin parent class defining a set of fixtures used in IoTHubDeviceClient tests"""

    @pytest.fixture
    async def client(self, custom_ssl_context):
        # Use a custom_ssl_context for auth for simplicity. Any test using this fixture is not
        # affected by auth type, so just use the simplest one.
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
        "Returns a new IoTHubDeviceClient instance, created with use of a new IoTHubClientConfig object"
    )
    @pytest.mark.parametrize("symmetric_key, sastoken_fn, ssl_context", auth_configurations)
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
    @pytest.mark.parametrize("symmetric_key, sastoken_fn, ssl_context", auth_configurations)
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
        "Sets the provided `hostname` on the IoTHubClientConfig used to create the client"
    )
    @pytest.mark.parametrize("symmetric_key, sastoken_fn, ssl_context", auth_configurations)
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
    @pytest.mark.parametrize("symmetric_key, sastoken_fn", sas_auth_configurations)
    async def test_custom_ssl_context(self, mocker, symmetric_key, sastoken_fn, custom_ssl_context):
        spy_client_init = mocker.spy(IoTHubDeviceClient, "__init__")

        client = await IoTHubDeviceClient.create(
            device_id=FAKE_DEVICE_ID,
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
    @pytest.mark.parametrize("symmetric_key, sastoken_fn", sas_auth_configurations)
    async def test_default_ssl_context(self, mocker, symmetric_key, sastoken_fn):
        spy_client_init = mocker.spy(IoTHubDeviceClient, "__init__")
        spy_default_ssl = mocker.spy(iothub_client, "_default_ssl_context")

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
    async def test_sk_auth(self, mocker, optional_ssl_context):
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
            ssl_context=optional_ssl_context,
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
    async def test_token_callback_auth(self, mocker, optional_ssl_context):
        spy_client_init = mocker.spy(IoTHubDeviceClient, "__init__")
        spy_st_generator_cls = mocker.spy(st, "ExternalSasTokenGenerator")
        spy_st_provider_create = mocker.spy(st.SasTokenProvider, "create_from_generator")

        client = await IoTHubDeviceClient.create(
            device_id=FAKE_DEVICE_ID,
            hostname=FAKE_HOSTNAME,
            sastoken_fn=sastoken_generator_fn,
            ssl_context=optional_ssl_context,
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
    @pytest.mark.parametrize("symmetric_key, sastoken_fn, ssl_context", auth_configurations)
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
    async def test_conflicting_auth(self):
        with pytest.raises(ValueError):
            await IoTHubDeviceClient.create(
                device_id=FAKE_DEVICE_ID,
                hostname=FAKE_HOSTNAME,
                symmetric_key=FAKE_SYMMETRIC_KEY,
                sastoken_fn=sastoken_generator_fn,
            )

    @pytest.mark.it(
        "Allows any exceptions raised when creating a SymmetricKeySigningMechanism to propagate"
    )
    @pytest.mark.parametrize("exception", sk_sm_create_exceptions)
    async def test_sksm_raises(self, mocker, optional_ssl_context, exception):
        mocker.patch.object(sm, "SymmetricKeySigningMechanism", side_effect=exception)

        with pytest.raises(type(exception)) as e_info:
            await IoTHubDeviceClient.create(
                device_id=FAKE_DEVICE_ID,
                hostname=FAKE_HOSTNAME,
                symmetric_key=FAKE_SYMMETRIC_KEY,
                ssl_context=optional_ssl_context,
            )
        assert e_info.value is exception

    @pytest.mark.it("Allows any exceptions raised when creating a SasTokenProvider to propagate")
    @pytest.mark.parametrize("symmetric_key, sastoken_fn", sas_auth_configurations)
    @pytest.mark.parametrize("exception", sastoken_provider_create_exceptions)
    async def test_sastoken_provider_raises(
        self, mocker, symmetric_key, sastoken_fn, optional_ssl_context, exception
    ):
        mocker.patch.object(st.SasTokenProvider, "create_from_generator", side_effect=exception)

        with pytest.raises(type(exception)) as e_info:
            await IoTHubDeviceClient.create(
                device_id=FAKE_DEVICE_ID,
                hostname=FAKE_HOSTNAME,
                symmetric_key=symmetric_key,
                sastoken_fn=sastoken_fn,
                ssl_context=optional_ssl_context,
            )
        assert e_info.value is exception

    @pytest.mark.it("Can be cancelled while waiting for SasTokenProvider creation")
    @pytest.mark.parametrize("symmetric_key, sastoken_fn", sas_auth_configurations)
    async def test_cancel_during_sastoken_provider_creation(
        self, mocker, symmetric_key, sastoken_fn, optional_ssl_context
    ):
        mocker.patch.object(
            st.SasTokenProvider, "create_from_generator", custom_mock.HangingAsyncMock()
        )

        coro = IoTHubDeviceClient.create(
            device_id=FAKE_DEVICE_ID,
            hostname=FAKE_HOSTNAME,
            symmetric_key=symmetric_key,
            sastoken_fn=sastoken_fn,
            ssl_context=optional_ssl_context,
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
        # Use a custom_ssl_context for auth for simplicity. Any test using this fixture is not
        # affected by auth type, so just use the simplest one.
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
        "Returns a new IoTHubModuleClient instance, created with use of a new IoTHubClientConfig object"
    )
    @pytest.mark.parametrize("symmetric_key, sastoken_fn, ssl_context", auth_configurations)
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
    @pytest.mark.parametrize("symmetric_key, sastoken_fn, ssl_context", auth_configurations)
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
    @pytest.mark.parametrize("symmetric_key, sastoken_fn, ssl_context", auth_configurations)
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
    @pytest.mark.parametrize("symmetric_key, sastoken_fn, ssl_context", auth_configurations)
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
    @pytest.mark.parametrize("symmetric_key, sastoken_fn", sas_auth_configurations)
    async def test_custom_ssl_context(self, mocker, symmetric_key, sastoken_fn, custom_ssl_context):
        spy_client_init = mocker.spy(IoTHubModuleClient, "__init__")

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
    @pytest.mark.parametrize("symmetric_key, sastoken_fn", sas_auth_configurations)
    async def test_default_ssl_context(self, mocker, symmetric_key, sastoken_fn):
        spy_client_init = mocker.spy(IoTHubModuleClient, "__init__")
        spy_default_ssl = mocker.spy(iothub_client, "_default_ssl_context")

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
    async def test_sk_auth(self, mocker, optional_ssl_context):
        spy_client_init = mocker.spy(IoTHubModuleClient, "__init__")
        spy_sk_sm_cls = mocker.spy(sm, "SymmetricKeySigningMechanism")
        spy_st_generator_cls = mocker.spy(st, "InternalSasTokenGenerator")
        spy_st_provider_create = mocker.spy(st.SasTokenProvider, "create_from_generator")
        expected_token_uri = "{hostname}/devices/{device_id}/modules/{module_id}".format(
            hostname=FAKE_HOSTNAME, device_id=FAKE_DEVICE_ID, module_id=FAKE_MODULE_ID
        )

        client = await IoTHubModuleClient.create(
            device_id=FAKE_DEVICE_ID,
            module_id=FAKE_MODULE_ID,
            hostname=FAKE_HOSTNAME,
            symmetric_key=FAKE_SYMMETRIC_KEY,
            ssl_context=optional_ssl_context,
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
    async def test_token_callback_auth(self, mocker, optional_ssl_context):
        spy_client_init = mocker.spy(IoTHubModuleClient, "__init__")
        spy_st_generator_cls = mocker.spy(st, "ExternalSasTokenGenerator")
        spy_st_provider_create = mocker.spy(st.SasTokenProvider, "create_from_generator")

        client = await IoTHubModuleClient.create(
            device_id=FAKE_DEVICE_ID,
            module_id=FAKE_MODULE_ID,
            hostname=FAKE_HOSTNAME,
            sastoken_fn=sastoken_generator_fn,
            ssl_context=optional_ssl_context,
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
    @pytest.mark.parametrize("symmetric_key, sastoken_fn, ssl_context", auth_configurations)
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
    async def test_conflicting_auth(self):
        with pytest.raises(ValueError):
            await IoTHubModuleClient.create(
                device_id=FAKE_DEVICE_ID,
                module_id=FAKE_MODULE_ID,
                hostname=FAKE_HOSTNAME,
                symmetric_key=FAKE_SYMMETRIC_KEY,
                sastoken_fn=sastoken_generator_fn,
            )

    @pytest.mark.it(
        "Allows any exceptions raised when creating a SymmetricKeySigningMechanism to propagate"
    )
    @pytest.mark.parametrize("exception", sk_sm_create_exceptions)
    async def test_sksm_raises(self, mocker, optional_ssl_context, exception):
        mocker.patch.object(sm, "SymmetricKeySigningMechanism", side_effect=exception)

        with pytest.raises(type(exception)) as e_info:
            await IoTHubModuleClient.create(
                device_id=FAKE_DEVICE_ID,
                module_id=FAKE_MODULE_ID,
                hostname=FAKE_HOSTNAME,
                symmetric_key=FAKE_SYMMETRIC_KEY,
                ssl_context=optional_ssl_context,
            )
        assert e_info.value is exception

    @pytest.mark.it("Allows any exceptions raised when creating a SasTokenProvider to propagate")
    @pytest.mark.parametrize("symmetric_key, sastoken_fn", sas_auth_configurations)
    @pytest.mark.parametrize("exception", sastoken_provider_create_exceptions)
    async def test_sastoken_provider_raises(
        self, mocker, symmetric_key, sastoken_fn, optional_ssl_context, exception
    ):
        mocker.patch.object(st.SasTokenProvider, "create_from_generator", side_effect=exception)

        with pytest.raises(type(exception)) as e_info:
            await IoTHubModuleClient.create(
                device_id=FAKE_DEVICE_ID,
                module_id=FAKE_MODULE_ID,
                hostname=FAKE_HOSTNAME,
                symmetric_key=symmetric_key,
                sastoken_fn=sastoken_fn,
                ssl_context=optional_ssl_context,
            )
        assert e_info.value is exception

    @pytest.mark.it("Can be cancelled while waiting for SasTokenProvider creation")
    @pytest.mark.parametrize("symmetric_key, sastoken_fn", sas_auth_configurations)
    async def test_cancel_during_sastoken_provider_creation(
        self, mocker, symmetric_key, sastoken_fn, optional_ssl_context
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
            ssl_context=optional_ssl_context,
        )
        t = asyncio.create_task(coro)

        # Hanging, waiting for SasTokenProvider creation to finish
        await st.SasTokenProvider.create_from_generator.wait_for_hang()
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
