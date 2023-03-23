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
from v3_async_wip.iothub_session import IoTHubSession
from v3_async_wip import config, models, iot_exceptions
from v3_async_wip import connection_string as cs
from v3_async_wip import iothub_mqtt_client as mqtt
from v3_async_wip import sastoken as st
from v3_async_wip import signing_mechanism as sm

FAKE_DEVICE_ID = "fake_device_id"
FAKE_MODULE_ID = "fake_module_id"
FAKE_HOSTNAME = "fake.hostname"
FAKE_GATEWAY_HOSTNAME = "fake.gateway.hostname"
FAKE_URI = "fake/resource/location"
FAKE_SHARED_ACCESS_KEY = "Zm9vYmFy"
FAKE_SIGNATURE = "ajsc8nLKacIjGsYyB4iYDFCZaRMmmDrUuY5lncYDYPI="

# TODO: aenter/aexit tests

# ~~~~~ Helpers ~~~~~~


def sastoken_generator_fn():
    return "SharedAccessSignature sr={resource}&sig={signature}&se={expiry}".format(
        resource=FAKE_URI, signature=FAKE_SIGNATURE, expiry=str(int(time.time()) + 3600)
    )


def get_expected_uri(hostname, device_id, module_id):
    if module_id:
        return "{hostname}/devices/{device_id}/modules/{module_id}".format(
            hostname=hostname, device_id=device_id, module_id=module_id
        )
    else:
        return "{hostname}/devices/{device_id}".format(hostname=hostname, device_id=device_id)


# ~~~~~ Fixtures ~~~~~~

# Mock out the underlying client in order to not do network operations
@pytest.fixture(autouse=True)
def mock_mqtt_iothub_client(mocker):
    return mocker.patch.object(mqtt, "IoTHubMQTTClient", spec=mqtt.IoTHubMQTTClient).return_value


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


@pytest.fixture
def session(custom_ssl_context):
    """Use a device configuration and custom SSL auth for simplicity"""
    return IoTHubSession(
        hostname=FAKE_HOSTNAME, device_id=FAKE_DEVICE_ID, ssl_context=custom_ssl_context
    )


# ~~~~~ Parametrizations ~~~~~
# Define parametrizations that will be used across multiple test suites, and that may eventually
# need to be changed everywhere, e.g. new auth scheme added.
# Note that some parametrizations are also defined within the scope of a single test suite if that
# is the only unit they are relevant to.


# Parameters for arguments to the __init__ or factory methods. Represent different types of
# authentication. Use this parametrization whenever possible on .create() tests.
# NOTE: Do NOT combine this with the SSL fixtures above. This parametrization contains
# ssl contexts where necessary
create_auth_params = [
    # Provide args in form 'shared_access_key, sastoken_fn, ssl_context'
    pytest.param(
        FAKE_SHARED_ACCESS_KEY, None, None, id="Shared Access Key SAS Auth + Default SSLContext"
    ),
    pytest.param(
        FAKE_SHARED_ACCESS_KEY,
        None,
        lazy_fixture("custom_ssl_context"),
        id="Shared Access Key SAS Auth + Custom SSLContext",
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
# Just the parameters where a Shared Access Key auth is used
create_auth_params_sak = [param for param in create_auth_params if param.values[0] is not None]
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
    # pytest.param("auto_reconnect", False, id="auto_reconnect"),
    pytest.param("keep_alive", 34, id="keep_alive"),
    pytest.param("product_info", "fake-product-info", id="product_info"),
    pytest.param(
        "proxy_options", config.ProxyOptions("HTTP", "fake.address", 1080), id="proxy_options"
    ),
    pytest.param("websockets", True, id="websockets"),
]

sk_sm_create_exceptions = [
    pytest.param(ValueError(), id="ValueError"),
    pytest.param(lazy_fixture("arbitrary_exception"), id="Unexpected Exception"),
]


@pytest.mark.describe("IoTHubSession -- Instantiation")
class TestIoTHubSessionInstantiation:
    create_id_params = [
        # Provide args in the form 'device_id, module_id'
        pytest.param(FAKE_DEVICE_ID, None, id="Device"),
        pytest.param(FAKE_DEVICE_ID, FAKE_MODULE_ID, id="Module"),
    ]

    @pytest.mark.it(
        "Instantiates and stores a SasTokenProvider that uses symmetric key-based token generation, if `shared_access_key` is provided"
    )
    @pytest.mark.parametrize("shared_access_key, sastoken_fn, ssl_context", create_auth_params_sak)
    @pytest.mark.parametrize("device_id, module_id", create_id_params)
    async def test_sak_auth(
        self, mocker, device_id, module_id, shared_access_key, sastoken_fn, ssl_context
    ):
        assert sastoken_fn is None
        spy_sk_sm_cls = mocker.spy(sm, "SymmetricKeySigningMechanism")
        spy_st_generator_cls = mocker.spy(st, "InternalSasTokenGenerator")
        spy_st_provider_cls = mocker.spy(st, "SasTokenProvider")
        expected_uri = get_expected_uri(FAKE_HOSTNAME, device_id, module_id)

        session = IoTHubSession(
            hostname=FAKE_HOSTNAME,
            device_id=device_id,
            module_id=module_id,
            shared_access_key=shared_access_key,
            ssl_context=ssl_context,
        )

        # SymmetricKeySigningMechanism was created from the shared access key
        assert spy_sk_sm_cls.call_count == 1
        assert spy_sk_sm_cls.call_args == mocker.call(shared_access_key)
        # InternalSasTokenGenerator was created from the SymmetricKeySigningMechanism
        assert spy_st_generator_cls.call_count == 1
        assert spy_st_generator_cls.call_args == mocker.call(
            signing_mechanism=spy_sk_sm_cls.spy_return, uri=expected_uri
        )
        # SasTokenProvider was created from the InternalSasTokenGenerator
        assert spy_st_provider_cls.call_count == 1
        assert spy_st_provider_cls.call_args == mocker.call(spy_st_generator_cls.spy_return)
        # SasTokenProvider was set on the Session
        assert session._sastoken_provider is spy_st_provider_cls.spy_return

    @pytest.mark.it(
        "Instantiates and stores a SasTokenProvider that uses callback-based token generation, if `sastoken_fn` is provided"
    )
    @pytest.mark.parametrize(
        "shared_access_key, sastoken_fn, ssl_context", create_auth_params_token_cb
    )
    @pytest.mark.parametrize("device_id, module_id", create_id_params)
    async def test_token_callback_auth(
        self, mocker, device_id, module_id, shared_access_key, sastoken_fn, ssl_context
    ):
        assert shared_access_key is None
        spy_st_generator_cls = mocker.spy(st, "ExternalSasTokenGenerator")
        spy_st_provider_cls = mocker.spy(st, "SasTokenProvider")

        session = IoTHubSession(
            hostname=FAKE_HOSTNAME,
            device_id=device_id,
            module_id=module_id,
            sastoken_fn=sastoken_fn,
            ssl_context=ssl_context,
        )

        # ExternalSasTokenGenerator was created from the sastoken_fn
        assert spy_st_generator_cls.call_count == 1
        assert spy_st_generator_cls.call_args == mocker.call(sastoken_fn)
        # SasTokenProvider was created from the ExternalSasTokenGenerator
        assert spy_st_provider_cls.call_count == 1
        assert spy_st_provider_cls.call_args == mocker.call(spy_st_generator_cls.spy_return)
        # SasTokenProvider was set on the Session
        assert session._sastoken_provider is spy_st_provider_cls.spy_return

    @pytest.mark.it(
        "Does not instantiate or store any SasTokenProvider if neither `shared_access_key` nor `sastoken_fn` are provided"
    )
    @pytest.mark.parametrize("device_id, module_id", create_id_params)
    async def test_non_sas_auth(self, mocker, device_id, module_id, custom_ssl_context):
        spy_st_provider_cls = mocker.spy(st, "SasTokenProvider")

        session = IoTHubSession(
            hostname=FAKE_HOSTNAME,
            device_id=device_id,
            module_id=module_id,
            ssl_context=custom_ssl_context,
        )

        # No SasTokenProvider
        assert session._sastoken_provider is None
        assert spy_st_provider_cls.call_count == 0

    @pytest.mark.it(
        "Instantiates and stores an IoTHubMQTTClient, using a new IoTHubClientConfig object"
    )
    @pytest.mark.parametrize("shared_access_key, sastoken_fn, ssl_context", create_auth_params)
    @pytest.mark.parametrize("device_id, module_id", create_id_params)
    async def test_mqtt_client(
        self, mocker, device_id, module_id, shared_access_key, sastoken_fn, ssl_context
    ):
        spy_config_cls = mocker.spy(config, "IoTHubClientConfig")
        spy_mqtt_cls = mocker.spy(mqtt, "IoTHubMQTTClient")
        assert spy_config_cls.call_count == 0
        assert spy_mqtt_cls.call_count == 0

        session = IoTHubSession(
            hostname=FAKE_HOSTNAME,
            device_id=device_id,
            module_id=module_id,
            shared_access_key=shared_access_key,
            sastoken_fn=sastoken_fn,
            ssl_context=ssl_context,
        )

        assert spy_config_cls.call_count == 1
        assert spy_mqtt_cls.call_count == 1
        assert spy_mqtt_cls.call_args == mocker.call(spy_config_cls.spy_return)
        assert session._mqtt_client is spy_mqtt_cls.spy_return

    @pytest.mark.it(
        "Sets the provided `hostname` on the IoTHubClientConfig used to create the IoTHubMQTTClient"
    )
    @pytest.mark.parametrize("shared_access_key, sastoken_fn, ssl_context", create_auth_params)
    @pytest.mark.parametrize("device_id, module_id", create_id_params)
    async def test_hostname(
        self, mocker, device_id, module_id, shared_access_key, sastoken_fn, ssl_context
    ):
        spy_mqtt_cls = mocker.spy(mqtt, "IoTHubMQTTClient")

        IoTHubSession(
            hostname=FAKE_HOSTNAME,
            device_id=device_id,
            module_id=module_id,
            shared_access_key=shared_access_key,
            sastoken_fn=sastoken_fn,
            ssl_context=ssl_context,
        )

        cfg = spy_mqtt_cls.call_args[0][0]
        assert cfg.hostname == FAKE_HOSTNAME

    @pytest.mark.it(
        "Sets the provided `device_id` and `module_id` values on the IoTHubClientConfig used to create the IoTHubMQTTClient"
    )
    @pytest.mark.parametrize("shared_access_key, sastoken_fn, ssl_context", create_auth_params)
    @pytest.mark.parametrize("device_id, module_id", create_id_params)
    async def test_ids(
        self, mocker, device_id, module_id, shared_access_key, sastoken_fn, ssl_context
    ):
        spy_mqtt_cls = mocker.spy(mqtt, "IoTHubMQTTClient")

        IoTHubSession(
            hostname=FAKE_HOSTNAME,
            device_id=device_id,
            module_id=module_id,
            shared_access_key=shared_access_key,
            sastoken_fn=sastoken_fn,
            ssl_context=ssl_context,
        )

        cfg = spy_mqtt_cls.call_args[0][0]
        assert cfg.device_id == device_id
        assert cfg.module_id == module_id

    @pytest.mark.it(
        "Sets the provided `ssl_context` on the IoTHubClientConfig used to create the IoTHubMQTTClient, if provided"
    )
    @pytest.mark.parametrize(
        "shared_access_key, sastoken_fn, ssl_context", create_auth_params_custom_ssl
    )
    @pytest.mark.parametrize("device_id, module_id", create_id_params)
    async def test_custom_ssl_context(
        self, mocker, device_id, module_id, shared_access_key, sastoken_fn, ssl_context
    ):
        spy_mqtt_cls = mocker.spy(mqtt, "IoTHubMQTTClient")

        IoTHubSession(
            hostname=FAKE_HOSTNAME,
            device_id=device_id,
            module_id=module_id,
            shared_access_key=shared_access_key,
            sastoken_fn=sastoken_fn,
            ssl_context=ssl_context,
        )

        cfg = spy_mqtt_cls.call_args[0][0]
        assert cfg.ssl_context is ssl_context

    @pytest.mark.it(
        "Sets a default SSLContext on the IoTHubClientConfig used to create the IoTHubMQTTClient, if `ssl_context` is not provided"
    )
    @pytest.mark.parametrize(
        "shared_access_key, sastoken_fn, ssl_context", create_auth_params_default_ssl
    )
    @pytest.mark.parametrize("device_id, module_id", create_id_params)
    async def test_default_ssl_context(
        self, mocker, device_id, module_id, shared_access_key, sastoken_fn, ssl_context
    ):
        assert ssl_context is None
        spy_mqtt_cls = mocker.spy(mqtt, "IoTHubMQTTClient")
        my_ssl_context = ssl.SSLContext(protocol=ssl.PROTOCOL_TLS_CLIENT)
        original_ssl_ctx_cls = ssl.SSLContext

        # NOTE: SSLContext is difficult to mock as an entire class, due to how it implements
        # instantiation. Essentially, if you mock the entire class, it will not be able to
        # instantiate due to an internal reference to the class type, which of course has now been
        # changed to MagicMock. To get around this, we mock the class with a side effect that can
        # check the arguments passed to the constructor, return a pre-existing SSLContext, and then
        # unset the mock to prevent future issues.
        def return_and_reset(*args, **kwargs):
            ssl.SSLContext = original_ssl_ctx_cls
            assert kwargs["protocol"] is ssl.PROTOCOL_TLS_CLIENT
            return my_ssl_context

        mocker.patch.object(ssl, "SSLContext", side_effect=return_and_reset)
        mocker.spy(my_ssl_context, "load_default_certs")

        IoTHubSession(
            hostname=FAKE_HOSTNAME,
            device_id=device_id,
            module_id=module_id,
            shared_access_key=shared_access_key,
            sastoken_fn=sastoken_fn,
        )

        cfg = spy_mqtt_cls.call_args[0][0]
        ctx = cfg.ssl_context
        assert ctx is my_ssl_context
        # NOTE: ctx protocol is checked in the `return_and_reset` side effect above
        assert ctx.verify_mode == ssl.CERT_REQUIRED
        assert ctx.check_hostname is True
        assert ctx.load_default_certs.call_count == 1
        assert ctx.load_default_certs.call_args == mocker.call()

    @pytest.mark.it(
        "Sets the stored SasTokenProvider (if any) on the IoTHubClientConfig used to create the IoTHubMQTTClient"
    )
    @pytest.mark.parametrize("shared_access_key, sastoken_fn, ssl_context", create_auth_params)
    @pytest.mark.parametrize("device_id, module_id", create_id_params)
    async def test_sastoken_provider_cfg(
        self, mocker, device_id, module_id, shared_access_key, sastoken_fn, ssl_context
    ):
        spy_mqtt_cls = mocker.spy(mqtt, "IoTHubMQTTClient")

        session = IoTHubSession(
            hostname=FAKE_HOSTNAME,
            device_id=device_id,
            module_id=module_id,
            shared_access_key=shared_access_key,
            sastoken_fn=sastoken_fn,
            ssl_context=ssl_context,
        )

        cfg = spy_mqtt_cls.call_args[0][0]
        assert cfg.sastoken_provider is session._sastoken_provider

    @pytest.mark.it(
        "Sets `auto_reconnect` to False on the IoTHubClientConfig used to create the IoTHubMQTTClient"
    )
    @pytest.mark.parametrize("shared_access_key, sastoken_fn, ssl_context", create_auth_params)
    @pytest.mark.parametrize("device_id, module_id", create_id_params)
    async def test_auto_reconnect_cfg(
        self, mocker, device_id, module_id, shared_access_key, sastoken_fn, ssl_context
    ):
        spy_mqtt_cls = mocker.spy(mqtt, "IoTHubMQTTClient")

        IoTHubSession(
            hostname=FAKE_HOSTNAME,
            device_id=device_id,
            module_id=module_id,
            shared_access_key=shared_access_key,
            sastoken_fn=sastoken_fn,
            ssl_context=ssl_context,
        )

        cfg = spy_mqtt_cls.call_args[0][0]
        assert cfg.auto_reconnect is False

    @pytest.mark.it(
        "Sets any provided optional keyword arguments on the IoTHubClientConfig used to create the IoTHubMQTTClient"
    )
    @pytest.mark.parametrize("shared_access_key, sastoken_fn, ssl_context", create_auth_params)
    @pytest.mark.parametrize("kwarg_name, kwarg_value", factory_kwargs)
    @pytest.mark.parametrize("device_id, module_id", create_id_params)
    async def test_kwargs(
        self,
        mocker,
        device_id,
        module_id,
        shared_access_key,
        sastoken_fn,
        ssl_context,
        kwarg_name,
        kwarg_value,
    ):
        spy_mqtt_cls = mocker.spy(mqtt, "IoTHubMQTTClient")
        kwargs = {kwarg_name: kwarg_value}

        IoTHubSession(
            hostname=FAKE_HOSTNAME,
            device_id=device_id,
            module_id=module_id,
            shared_access_key=shared_access_key,
            sastoken_fn=sastoken_fn,
            ssl_context=ssl_context,
            **kwargs
        )

        cfg = spy_mqtt_cls.call_args[0][0]
        assert getattr(cfg, kwarg_name) == kwarg_value

    @pytest.mark.it(
        "Raises ValueError if neither `shared_access_key`, `sastoken_fn` nor `ssl_context` are provided as parameters"
    )
    @pytest.mark.parametrize("device_id, module_id", create_id_params)
    async def test_no_auth(self, device_id, module_id):
        with pytest.raises(ValueError):
            IoTHubSession(
                device_id=device_id,
                module_id=module_id,
                hostname=FAKE_HOSTNAME,
            )

    @pytest.mark.it(
        "Raises ValueError if both `shared_access_key` and `sastoken_fn` are provided as parameters"
    )
    @pytest.mark.parametrize("device_id, module_id", create_id_params)
    async def test_conflicting_auth(self, device_id, module_id, optional_ssl_context):
        with pytest.raises(ValueError):
            IoTHubSession(
                hostname=FAKE_HOSTNAME,
                device_id=device_id,
                module_id=module_id,
                shared_access_key=FAKE_SHARED_ACCESS_KEY,
                sastoken_fn=sastoken_generator_fn,
                ssl_context=optional_ssl_context,
            )

    @pytest.mark.it("Raises TypeError if an invalid keyword argument is provided")
    @pytest.mark.parametrize("shared_access_key, sastoken_fn, ssl_context", create_auth_params)
    @pytest.mark.parametrize("device_id, module_id", create_id_params)
    async def test_bad_kwarg(
        self, device_id, module_id, shared_access_key, sastoken_fn, ssl_context
    ):
        with pytest.raises(TypeError):
            IoTHubSession(
                hostname=FAKE_HOSTNAME,
                device_id=device_id,
                module_id=module_id,
                shared_access_key=shared_access_key,
                sastoken_fn=sastoken_fn,
                ssl_context=ssl_context,
                invalid_argument="some value",
            )

    @pytest.mark.it(
        "Allows any exceptions raised when creating a SymmetricKeySigningMechanism to propagate"
    )
    @pytest.mark.parametrize("exception", sk_sm_create_exceptions)
    @pytest.mark.parametrize("shared_access_key, sastoken_fn, ssl_context", create_auth_params_sak)
    @pytest.mark.parametrize("device_id, module_id", create_id_params)
    async def test_sksm_raises(
        self, mocker, device_id, module_id, shared_access_key, sastoken_fn, ssl_context, exception
    ):
        mocker.patch.object(sm, "SymmetricKeySigningMechanism", side_effect=exception)
        assert sastoken_fn is None

        with pytest.raises(type(exception)) as e_info:
            IoTHubSession(
                hostname=FAKE_HOSTNAME,
                device_id=device_id,
                module_id=module_id,
                shared_access_key=shared_access_key,
                sastoken_fn=sastoken_fn,
                ssl_context=ssl_context,
            )
        assert e_info.value is exception


@pytest.mark.describe("IoTHubSession - .from_connection_string")
class TestIoTHubSessionFromConnectionString:
    factory_params = [
        # TODO: once Edge support is decided upon, either re-enable, or remove the commented Edge parameters
        # TODO: Do we want gateway hostname tests that are non-Edge? probably?
        pytest.param(
            "HostName={hostname};DeviceId={device_id};SharedAccessKey={shared_access_key}".format(
                hostname=FAKE_HOSTNAME,
                device_id=FAKE_DEVICE_ID,
                shared_access_key=FAKE_SHARED_ACCESS_KEY,
            ),
            None,
            id="Standard Device Connection String w/ SharedAccessKey + Default SSLContext",
        ),
        pytest.param(
            "HostName={hostname};DeviceId={device_id};SharedAccessKey={shared_access_key}".format(
                hostname=FAKE_HOSTNAME,
                device_id=FAKE_DEVICE_ID,
                shared_access_key=FAKE_SHARED_ACCESS_KEY,
            ),
            lazy_fixture("custom_ssl_context"),
            id="Standard Device Connection String w/ SharedAccessKey + Custom SSLContext",
        ),
        # pytest.param(
        #     "HostName={hostname};DeviceId={device_id};SharedAccessKey={shared_access_key};GatewayHostName={gateway_hostname}".format(
        #         hostname=FAKE_HOSTNAME,
        #         device_id=FAKE_DEVICE_ID,
        #         shared_access_key=FAKE_SHARED_ACCESS_KEY,
        #         gateway_hostname=FAKE_GATEWAY_HOSTNAME,
        #     ),
        #     None,
        #     id="Edge Device Connection String w/ SharedAccessKey + Default SSLContext",
        # ),
        # pytest.param(
        #     "HostName={hostname};DeviceId={device_id};SharedAccessKey={shared_access_key};GatewayHostName={gateway_hostname}".format(
        #         hostname=FAKE_HOSTNAME,
        #         device_id=FAKE_DEVICE_ID,
        #         shared_access_key=FAKE_SHARED_ACCESS_KEY,
        #         gateway_hostname=FAKE_GATEWAY_HOSTNAME,
        #     ),
        #     lazy_fixture("custom_ssl_context"),
        #     id="Edge Device Connection String w/ SharedAccessKey + Custom SSLContext",
        # ),
        # NOTE: X509 certs imply use of custom SSLContext
        pytest.param(
            "HostName={hostname};DeviceId={device_id};x509=true".format(
                hostname=FAKE_HOSTNAME,
                device_id=FAKE_DEVICE_ID,
            ),
            lazy_fixture("custom_ssl_context"),
            id="Standard Device Connection String w/ X509",
        ),
        # pytest.param(
        #     "HostName={hostname};DeviceId={device_id};GatewayHostName={gateway_hostname};x509=true".format(
        #         hostname=FAKE_HOSTNAME,
        #         device_id=FAKE_DEVICE_ID,
        #         gateway_hostname=FAKE_GATEWAY_HOSTNAME,
        #     ),
        #     lazy_fixture("custom_ssl_context"),
        #     id="Edge Device Connection String w/ X509",
        # ),
        pytest.param(
            "HostName={hostname};DeviceId={device_id};ModuleId={module_id};SharedAccessKey={shared_access_key}".format(
                hostname=FAKE_HOSTNAME,
                device_id=FAKE_DEVICE_ID,
                module_id=FAKE_MODULE_ID,
                shared_access_key=FAKE_SHARED_ACCESS_KEY,
            ),
            None,
            id="Standard Module Connection String w/ SharedAccessKey + Default SSLContext",
        ),
        pytest.param(
            "HostName={hostname};DeviceId={device_id};ModuleId={module_id};SharedAccessKey={shared_access_key}".format(
                hostname=FAKE_HOSTNAME,
                device_id=FAKE_DEVICE_ID,
                module_id=FAKE_MODULE_ID,
                shared_access_key=FAKE_SHARED_ACCESS_KEY,
            ),
            lazy_fixture("custom_ssl_context"),
            id="Standard Module Connection String w/ SharedAccessKey + Custom SSLContext",
        ),
        # pytest.param(
        #     "HostName={hostname};DeviceId={device_id};ModuleId={module_id};SharedAccessKey={shared_access_key};GatewayHostName={gateway_hostname}".format(
        #         hostname=FAKE_HOSTNAME,
        #         device_id=FAKE_DEVICE_ID,
        #         module_id=FAKE_MODULE_ID,
        #         shared_access_key=FAKE_SHARED_ACCESS_KEY,
        #         gateway_hostname=FAKE_GATEWAY_HOSTNAME,
        #     ),
        #     None,
        #     id="Edge Module Connection String w/ SharedAccessKey + Default SSLContext",
        # ),
        # pytest.param(
        #     "HostName={hostname};DeviceId={device_id};ModuleId={module_id};SharedAccessKey={shared_access_key};GatewayHostName={gateway_hostname}".format(
        #         hostname=FAKE_HOSTNAME,
        #         device_id=FAKE_DEVICE_ID,
        #         module_id=FAKE_MODULE_ID,
        #         shared_access_key=FAKE_SHARED_ACCESS_KEY,
        #         gateway_hostname=FAKE_GATEWAY_HOSTNAME,
        #     ),
        #     lazy_fixture("custom_ssl_context"),
        #     id="Edge Module Connection String w/ SharedAccessKey + Custom SSLContext",
        # ),
        # NOTE: X509 certs imply use of custom SSLContext
        pytest.param(
            "HostName={hostname};DeviceId={device_id};ModuleId={module_id};x509=true".format(
                hostname=FAKE_HOSTNAME,
                device_id=FAKE_DEVICE_ID,
                module_id=FAKE_MODULE_ID,
            ),
            lazy_fixture("custom_ssl_context"),
            id="Standard Module Connection String w/ X509",
        ),
        # pytest.param(
        #     "HostName={hostname};DeviceId={device_id};ModuleId={module_id};GatewayHostName={gateway_hostname};x509=true".format(
        #         hostname=FAKE_HOSTNAME,
        #         device_id=FAKE_DEVICE_ID,
        #         module_id=FAKE_MODULE_ID,
        #         gateway_hostname=FAKE_GATEWAY_HOSTNAME,
        #     ),
        #     lazy_fixture("custom_ssl_context"),
        #     id="Edge Module Connection String w/ X509",
        # ),
    ]
    # Just the parameters for using standard connection strings
    factory_params_no_gateway = [
        param for param in factory_params if cs.GATEWAY_HOST_NAME not in param.values[0]
    ]
    # Just the parameters for using connection strings with a GatewayHostName
    factory_params_gateway = [
        param for param in factory_params if cs.GATEWAY_HOST_NAME in param.values[0]
    ]
    # # Just the parameters where a custom SSLContext is provided
    # factory_params_custom_ssl = [param for param in factory_params if param.values[1] is not None]
    # # Just the parameters where a custom SSLContext is NOT provided
    # factory_params_default_ssl = [param for param in factory_params if param.values[1] is None]
    # # Just the parameters for using SharedAccessKeys
    # factory_params_sak = [
    #     param for param in factory_params if cs.SHARED_ACCESS_KEY in param.values[0]
    # ]
    # Just the parameters for NOT using SharedAccessKeys
    factory_params_no_sak = [
        param for param in factory_params if cs.SHARED_ACCESS_KEY not in param.values[0]
    ]

    @pytest.mark.it("Returns a new IoTHubSession instance")
    @pytest.mark.parametrize("connection_string, ssl_context", factory_params)
    async def test_instantiation(self, connection_string, ssl_context):
        session = IoTHubSession.from_connection_string(connection_string, ssl_context)
        assert isinstance(session, IoTHubSession)

    @pytest.mark.it(
        "Extracts the `DeviceId`, `ModuleId` and `SharedAccessKey` values from the connection string (if present), passing them to the IoTHubSession initializer"
    )
    @pytest.mark.parametrize("connection_string, ssl_context", factory_params)
    async def test_extracts_values(self, mocker, connection_string, ssl_context):
        spy_session_init = mocker.spy(IoTHubSession, "__init__")
        cs_obj = cs.ConnectionString(connection_string)

        IoTHubSession.from_connection_string(connection_string, ssl_context)

        assert spy_session_init.call_count == 1
        assert spy_session_init.call_args[1]["device_id"] == cs_obj[cs.DEVICE_ID]
        assert spy_session_init.call_args[1]["module_id"] == cs_obj.get(cs.MODULE_ID)
        assert spy_session_init.call_args[1]["shared_access_key"] == cs_obj.get(
            cs.SHARED_ACCESS_KEY
        )

    @pytest.mark.it(
        "Extracts the `HostName` value from the connection string and passes it to the IoTHubSession initializer as the `hostname`, if no `GatewayHostName` value is present in the connection string"
    )
    @pytest.mark.parametrize("connection_string, ssl_context", factory_params_no_gateway)
    async def test_hostname(self, mocker, connection_string, ssl_context):
        spy_session_init = mocker.spy(IoTHubSession, "__init__")
        cs_obj = cs.ConnectionString(connection_string)

        IoTHubSession.from_connection_string(connection_string, ssl_context)

        assert spy_session_init.call_count == 1
        assert spy_session_init.call_args[1]["hostname"] == cs_obj[cs.HOST_NAME]

    # TODO: This test is currently being skipped because test data does not include such values
    # Get clarity on how we want to handle Edge, and then clear this up.
    @pytest.mark.it(
        "Extracts the `GatewayHostName` value from the connection string and passes it to the IoTHubSession initializer as the `hostname`, if present in the connection string"
    )
    @pytest.mark.parametrize("connection_string, ssl_context", factory_params_gateway)
    async def test_gateway_hostname(self, mocker, connection_string, ssl_context):
        spy_session_init = mocker.spy(IoTHubSession, "__init__")
        cs_obj = cs.ConnectionString(connection_string)
        assert cs_obj[cs.GATEWAY_HOST_NAME] != cs_obj[cs.HOST_NAME]

        IoTHubSession.from_connection_string(connection_string, ssl_context)

        assert spy_session_init.call_count == 1
        assert spy_session_init.call_args[1]["hostname"] == cs_obj[cs.GATEWAY_HOST_NAME]

    @pytest.mark.it("Passes any provided `ssl_context` to the IoTHubSession initializer")
    @pytest.mark.parametrize("connection_string, ssl_context", factory_params)
    async def test_ssl_context(self, mocker, connection_string, ssl_context):
        spy_session_init = mocker.spy(IoTHubSession, "__init__")

        IoTHubSession.from_connection_string(connection_string, ssl_context)

        assert spy_session_init.call_count == 1
        assert spy_session_init.call_args[1]["ssl_context"] is ssl_context

    @pytest.mark.it(
        "Passes any provided optional keyword arguments to the IoTHubSession initializer"
    )
    @pytest.mark.parametrize("connection_string, ssl_context", factory_params)
    @pytest.mark.parametrize("kwarg_name, kwarg_value", factory_kwargs)
    async def test_kwargs(self, mocker, connection_string, ssl_context, kwarg_name, kwarg_value):
        spy_session_init = mocker.spy(IoTHubSession, "__init__")
        kwargs = {kwarg_name: kwarg_value}

        IoTHubSession.from_connection_string(connection_string, ssl_context, **kwargs)

        assert spy_session_init.call_count == 1
        assert spy_session_init.call_args[1][kwarg_name] == kwarg_value

    @pytest.mark.it(
        "Raises ValueError if `x509=true` is present in the connection string, but no `ssl_context` is provided"
    )
    @pytest.mark.parametrize("connection_string, ssl_context", factory_params_no_sak)
    async def test_x509_true_no_ssl(self, connection_string, ssl_context):
        # Ignore the ssl_context provided by the parametrization
        with pytest.raises(ValueError):
            IoTHubSession.from_connection_string(connection_string)

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
            shared_access_key=FAKE_SHARED_ACCESS_KEY,
        )
        IoTHubSession.from_connection_string(connection_string)
        # If the above invocation didn't raise, the test passed, no assertions required

    @pytest.mark.it("Raises TypeError if an invalid keyword argument is provided")
    @pytest.mark.parametrize("connection_string, ssl_context", factory_params)
    async def test_bad_kwarg(self, connection_string, ssl_context):
        with pytest.raises(TypeError):
            IoTHubSession.from_connection_string(
                connection_string, ssl_context, invalid_argument="some_value"
            )

    @pytest.mark.it("Allows any exceptions raised while parsing the connection string to propagate")
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
            shared_access_key=FAKE_SHARED_ACCESS_KEY,
        )
        # Mock cs parsing
        mocker.patch.object(cs, "ConnectionString", side_effect=exception)

        with pytest.raises(type(exception)) as e_info:
            IoTHubSession.from_connection_string(
                connection_string, ssl_context=optional_ssl_context
            )
        assert e_info.value is exception

    @pytest.mark.it("Allows any exceptions raised by the initializer to propagate")
    @pytest.mark.parametrize("connection_string, ssl_context", factory_params)
    async def test_init_raises(self, mocker, connection_string, ssl_context, arbitrary_exception):
        # NOTE: for an in-depth look at what possible exceptions could be raised,
        # see the TestIoTHubSessionInstantiation suite. To prevent duplication,
        # we will simply use an arbitrary exception here
        mocker.patch.object(IoTHubSession, "__init__", side_effect=arbitrary_exception)

        with pytest.raises(type(arbitrary_exception)) as e_info:
            IoTHubSession.from_connection_string(connection_string, ssl_context)
        assert e_info.value is arbitrary_exception


@pytest.mark.describe("IoTHubSession -- Context Manager Usage")
class TestIoTHubSessionContextManager:
    @pytest.mark.it(
        "Starts the IoTHubMQTTClient upon entry into the context manager, and stops it upon exit"
    )
    async def test_mqtt_client_start_stop(self, session):
        assert session._mqtt_client.start.await_count == 0
        assert session._mqtt_client.stop.await_count == 0

        async with session as session:
            assert session._mqtt_client.start.await_count == 1
            assert session._mqtt_client.stop.await_count == 0

        assert session._mqtt_client.start.await_count == 1
        assert session._mqtt_client.stop.await_count == 1

    @pytest.mark.it(
        "Stops the IoTHubMQTTClient upon exit, even if an error was raised within the block inside the context manager"
    )
    async def test_mqtt_client_start_stop_with_failure(self, session, arbitrary_exception):
        assert session._mqtt_client.start.await_count == 0
        assert session._mqtt_client.stop.await_count == 0

        try:
            async with session as session:
                assert session._mqtt_client.start.await_count == 1
                assert session._mqtt_client.stop.await_count == 0
                raise arbitrary_exception
        except type(arbitrary_exception):
            pass

        assert session._mqtt_client.start.await_count == 1
        assert session._mqtt_client.stop.await_count == 1

    @pytest.mark.it(
        "Connect the IoTHubMQTTClient upon entry into the context manager, and disconnect it upon exit"
    )
    async def test_mqtt_client_connection(self, session):
        assert session._mqtt_client.connect.await_count == 0
        assert session._mqtt_client.disconnect.await_count == 0

        async with session as session:
            assert session._mqtt_client.connect.await_count == 1
            assert session._mqtt_client.disconnect.await_count == 0

        assert session._mqtt_client.connect.await_count == 1
        assert session._mqtt_client.disconnect.await_count == 1

    @pytest.mark.it(
        "Disconnect the IoTHubMQTTClient upon exit, even if an error was raised within the block inside the context manager"
    )
    async def test_mqtt_client_connection_with_failure(self, session, arbitrary_exception):
        assert session._mqtt_client.connect.await_count == 0
        assert session._mqtt_client.disconnect.await_count == 0

        try:
            async with session as session:
                assert session._mqtt_client.connect.await_count == 1
                assert session._mqtt_client.disconnect.await_count == 0
                raise arbitrary_exception
        except type(arbitrary_exception):
            pass

        assert session._mqtt_client.connect.await_count == 1
        assert session._mqtt_client.disconnect.await_count == 1

    @pytest.mark.it(
        "Starts the SasTokenProvider upon entry into the context manager, and stops it upon exit, if one exists"
    )
    async def test_sastoken_provider_start_stop(self, session, mock_sastoken_provider):
        session._sastoken_provider = mock_sastoken_provider
        assert session._sastoken_provider.start.await_count == 0
        assert session._sastoken_provider.stop.await_count == 0

        async with session as session:
            assert session._sastoken_provider.start.await_count == 1
            assert session._sastoken_provider.stop.await_count == 0

        assert session._sastoken_provider.start.await_count == 1
        assert session._sastoken_provider.stop.await_count == 1

    @pytest.mark.it(
        "Stops the SasTokenProvider upon exit, even if an error was raised within the block inside the context manager"
    )
    async def test_sastoken_provider_start_stop_with_failure(
        self, session, mock_sastoken_provider, arbitrary_exception
    ):
        session._sastoken_provider = mock_sastoken_provider
        assert session._sastoken_provider.start.await_count == 0
        assert session._sastoken_provider.stop.await_count == 0

        try:
            async with session as session:
                assert session._sastoken_provider.start.await_count == 1
                assert session._sastoken_provider.stop.await_count == 0
                raise arbitrary_exception
        except type(arbitrary_exception):
            pass

        assert session._sastoken_provider.start.await_count == 1
        assert session._sastoken_provider.stop.await_count == 1

    @pytest.mark.it("Can handle the case where SasTokenProvider does not exist")
    async def test_no_sastoken_provider(self, session):
        assert session._sastoken_provider is None

        async with session as session:
            pass

        # If nothing raises here, the test passes

    @pytest.mark.it(
        "Allows any errors raised within the block inside the context manager to propagate"
    )
    @pytest.mark.parametrize(
        "exception",
        [
            pytest.param(lazy_fixture("arbitrary_exception"), id="Unexpected Exception"),
            # NOTE: it is importat to test the CancelledError since it is a regular Exception in 3.7,
            # but a BaseException from 3.8+
            pytest.param(asyncio.CancelledError(), id="CancelledError"),
        ],
    )
    async def test_error_propagation(self, session, exception):
        with pytest.raises(type(exception)) as e_info:
            async with session as session:
                raise exception
        assert e_info.value is exception

    # TODO: tests re errors in stop


@pytest.mark.describe("IoTHubSession - .send_message()")
class TestIoTHubSessionSendMessage:
    @pytest.mark.it(
        "Invokes .send_message() on the IoTHubMQTTClient, passing the provided `message`, if `message` is a Message object"
    )
    async def test_message_object(self, mocker, session):
        assert session._mqtt_client.send_message.await_count == 0

        m = models.Message("hi")
        await session.send_message(m)

        assert session._mqtt_client.send_message.await_count == 1
        assert session._mqtt_client.send_message.await_args == mocker.call(m)

    @pytest.mark.it(
        "Invokes .send_message() on the IoTHubMQTTClient, passing a new Message object with `message` as the payload, if `message` is a string"
    )
    async def test_message_string(self, session):
        assert session._mqtt_client.send_message.await_count == 0

        m_str = "hi"
        await session.send_message(m_str)

        assert session._mqtt_client.send_message.await_count == 1
        m_obj = session._mqtt_client.send_message.await_args[0][0]
        assert isinstance(m_obj, models.Message)
        assert m_obj.payload == m_str

    @pytest.mark.it("Allows any exceptions raised by the IoTHubMQTTClient to propagate")
    @pytest.mark.parametrize(
        "exception",
        [
            pytest.param(mqtt.MQTTError(5), id="MQTTError"),
            pytest.param(ValueError(), id="ValueError"),
            pytest.param(lazy_fixture("arbitrary_exception"), id="Unexpected Error"),
        ],
    )
    async def test_mqtt_client_raises(self, session, exception):
        session._mqtt_client.send_message.side_effect = exception

        with pytest.raises(type(exception)) as e_info:
            await session.send_message("hi")
        assert e_info.value is exception

    @pytest.mark.it("Can be cancelled while waiting for the IoTHubMQTTClient operation to complete")
    async def test_cancel_during_send(self, session):
        session._mqtt_client.send_message = custom_mock.HangingAsyncMock()

        t = asyncio.create_task(session.send_message("hi"))

        # Hanging, waiting for send to finish
        await session._mqtt_client.send_message.wait_for_hang()
        assert not t.done()

        # Cancel
        t.cancel()
        with pytest.raises(asyncio.CancelledError):
            await t


@pytest.mark.describe("IoTHubSession - .send_direct_method_response()")
class TestIoTHubSessionSendDirectMethodResponse:
    @pytest.fixture
    def direct_method_response(self):
        return models.DirectMethodResponse(request_id="id", status=200, payload={"some": "value"})

    @pytest.mark.it(
        "Invokes .send_direct_method_response() on the IoTHubMQTTClient, passing the provided `method_response`"
    )
    async def test_invoke(self, mocker, session, direct_method_response):
        assert session._mqtt_client.send_direct_method_response.await_count == 0

        await session.send_direct_method_response(direct_method_response)

        assert session._mqtt_client.send_direct_method_response.await_count == 1
        assert session._mqtt_client.send_direct_method_response.await_args == mocker.call(
            direct_method_response
        )

    @pytest.mark.it("Allows any exceptions raised by the IoTHubMQTTClient to propagate")
    @pytest.mark.parametrize(
        "exception",
        [
            pytest.param(mqtt.MQTTError(5), id="MQTTError"),
            pytest.param(ValueError(), id="ValueError"),
            pytest.param(lazy_fixture("arbitrary_exception"), id="Unexpected Error"),
        ],
    )
    async def test_mqtt_client_raises(self, session, direct_method_response, exception):
        session._mqtt_client.send_direct_method_response.side_effect = exception

        with pytest.raises(type(exception)) as e_info:
            await session.send_direct_method_response(direct_method_response)
        assert e_info.value is exception

    @pytest.mark.it("Can be cancelled while waiting for the IoTHubMQTTClient operation to complete")
    async def test_cancel_during_send(self, session, direct_method_response):
        session._mqtt_client.send_direct_method_response = custom_mock.HangingAsyncMock()

        t = asyncio.create_task(session.send_direct_method_response(direct_method_response))

        # Hanging, waiting for send to finish
        await session._mqtt_client.send_direct_method_response.wait_for_hang()
        assert not t.done()

        # Cancel
        t.cancel()
        with pytest.raises(asyncio.CancelledError):
            await t


@pytest.mark.describe("IoTHubSession - .update_reported_properties()")
class TestIoTHubSessionUpdateReportedProperties:
    @pytest.fixture
    def patch(self):
        return {"key1": "value1", "key2": "value2"}

    @pytest.mark.it(
        "Invokes .send_twin_patch() on the IoTHubMQTTClient, passing the provided `patch`"
    )
    async def test_invoke(self, mocker, session, patch):
        assert session._mqtt_client.send_twin_patch.await_count == 0

        await session.update_reported_properties(patch)

        assert session._mqtt_client.send_twin_patch.await_count == 1
        assert session._mqtt_client.send_twin_patch.await_args == mocker.call(patch)

    @pytest.mark.it("Allows any exceptions raised by the IoTHubMQTTClient to propagate")
    @pytest.mark.parametrize(
        "exception",
        [
            pytest.param(iot_exceptions.IoTHubError(), id="IoTHubError"),
            pytest.param(mqtt.MQTTError(5), id="MQTTError"),
            pytest.param(ValueError(), id="ValueError"),
            pytest.param(asyncio.CancelledError(), id="CancelledError"),
            pytest.param(lazy_fixture("arbitrary_exception"), id="Unexpected Error"),
        ],
    )
    async def test_mqtt_client_raises(self, session, patch, exception):
        session._mqtt_client.send_twin_patch.side_effect = exception

        with pytest.raises(type(exception)) as e_info:
            await session.update_reported_properties(patch)
        assert e_info.value is exception

    @pytest.mark.it("Can be cancelled while waiting for the IoTHubMQTTClient operation to complete")
    async def test_cancel_during_send(self, session, patch):
        session._mqtt_client.send_twin_patch = custom_mock.HangingAsyncMock()

        t = asyncio.create_task(session.update_reported_properties(patch))

        # Hanging, waiting for send to finish
        await session._mqtt_client.send_twin_patch.wait_for_hang()
        assert not t.done()

        # Cancel
        t.cancel()
        with pytest.raises(asyncio.CancelledError):
            await t


@pytest.mark.describe("IoTHubSession - .get_twin()")
class TestIoTHubSessionGetTwin:
    @pytest.mark.it("Invokes .get_twin() on the IoTHubMQTTClient")
    async def test_invoke(self, mocker, session):
        assert session._mqtt_client.get_twin.await_count == 0

        await session.get_twin()

        assert session._mqtt_client.get_twin.await_count == 1
        assert session._mqtt_client.get_twin.await_args == mocker.call()

    @pytest.mark.it("Allows any exceptions raised by the IoTHubMQTTClient to propagate")
    @pytest.mark.parametrize(
        "exception",
        [
            pytest.param(iot_exceptions.IoTHubError(), id="IoTHubError"),
            pytest.param(mqtt.MQTTError(5), id="MQTTError"),
            pytest.param(asyncio.CancelledError(), id="CancelledError"),
            pytest.param(lazy_fixture("arbitrary_exception"), id="Unexpected Error"),
        ],
    )
    async def test_mqtt_client_raises(self, session, exception):
        session._mqtt_client.get_twin.side_effect = exception

        with pytest.raises(type(exception)) as e_info:
            await session.get_twin()
        assert e_info.value is exception

    @pytest.mark.it("Can be cancelled while waiting for the IoTHubMQTTClient operation to complete")
    async def test_cancel_during_send(self, session):
        session._mqtt_client.get_twin = custom_mock.HangingAsyncMock()

        t = asyncio.create_task(session.get_twin())

        # Hanging, waiting for send to finish
        await session._mqtt_client.get_twin.wait_for_hang()
        assert not t.done()

        # Cancel
        t.cancel()
        with pytest.raises(asyncio.CancelledError):
            await t


@pytest.mark.describe("IoTHubSession - .messages()")
class TestIoTHubSessionMessages:
    @pytest.mark.it(
        "Enables C2D message receive with the IoTHubMQTTClient upon entry into the context manager and disables C2D message receive upon exit"
    )
    async def test_context_manager(self, session):
        assert session._mqtt_client.enable_c2d_message_receive.await_count == 0
        assert session._mqtt_client.disable_c2d_message_receive.await_count == 0

        async with session.messages():
            assert session._mqtt_client.enable_c2d_message_receive.await_count == 1
            assert session._mqtt_client.disable_c2d_message_receive.await_count == 0

        assert session._mqtt_client.enable_c2d_message_receive.await_count == 1
        assert session._mqtt_client.disable_c2d_message_receive.await_count == 1

    @pytest.mark.it(
        "Disables C2D message receive upon exit, even if an error is raised inside the context manager block"
    )
    async def test_context_manager_failure(self, session, arbitrary_exception):
        assert session._mqtt_client.enable_c2d_message_receive.await_count == 0
        assert session._mqtt_client.disable_c2d_message_receive.await_count == 0

        try:
            async with session.messages():
                assert session._mqtt_client.enable_c2d_message_receive.await_count == 1
                assert session._mqtt_client.disable_c2d_message_receive.await_count == 0
                raise arbitrary_exception
        except type(arbitrary_exception):
            pass

        assert session._mqtt_client.enable_c2d_message_receive.await_count == 1
        assert session._mqtt_client.disable_c2d_message_receive.await_count == 1

    @pytest.mark.it("Yields the IoTHubMQTTClient's incoming C2D message generator")
    async def test_generator(self, session):
        # NOTE: This generator is thoroughly tested in test_iothub_mqtt_client.py
        async with session.messages() as messages:
            assert messages is session._mqtt_client.incoming_c2d_messages


@pytest.mark.describe("IoTHubSession - .direct_method_requests()")
class TestIoTHubSessionDirectMethodRequests:
    @pytest.mark.it(
        "Enables direct method request receive with the IoTHubMQTTClient upon entry into the context manager and disables direct method request receive upon exit"
    )
    async def test_context_manager(self, session):
        assert session._mqtt_client.enable_direct_method_request_receive.await_count == 0
        assert session._mqtt_client.disable_direct_method_request_receive.await_count == 0

        async with session.direct_method_requests():
            assert session._mqtt_client.enable_direct_method_request_receive.await_count == 1
            assert session._mqtt_client.disable_direct_method_request_receive.await_count == 0

        assert session._mqtt_client.enable_direct_method_request_receive.await_count == 1
        assert session._mqtt_client.disable_direct_method_request_receive.await_count == 1

    @pytest.mark.it(
        "Disables direct method request receive upon exit, even if an error is raised inside the context manager block"
    )
    async def test_context_manager_failure(self, session, arbitrary_exception):
        assert session._mqtt_client.enable_direct_method_request_receive.await_count == 0
        assert session._mqtt_client.disable_direct_method_request_receive.await_count == 0

        try:
            async with session.direct_method_requests():
                assert session._mqtt_client.enable_direct_method_request_receive.await_count == 1
                assert session._mqtt_client.disable_direct_method_request_receive.await_count == 0
                raise arbitrary_exception
        except type(arbitrary_exception):
            pass

        assert session._mqtt_client.enable_direct_method_request_receive.await_count == 1
        assert session._mqtt_client.disable_direct_method_request_receive.await_count == 1

    @pytest.mark.it("Yields the IoTHubMQTTClient's incoming direct method request generator")
    async def test_generator(self, session):
        # NOTE: This generator is thoroughly tested in test_iothub_mqtt_client.py
        async with session.direct_method_requests() as method_requests:
            assert method_requests is session._mqtt_client.incoming_direct_method_requests


@pytest.mark.describe("IoTHubSession - .desired_property_updates()")
class TestIoTHubSessionDesiredPropertyUpdates:
    @pytest.mark.it(
        "Enables twin patch receive with the IoTHubMQTTClient upon entry into the context manager and disables twin patch receive upon exit"
    )
    async def test_context_manager(self, session):
        assert session._mqtt_client.enable_twin_patch_receive.await_count == 0
        assert session._mqtt_client.disable_twin_patch_receive.await_count == 0

        async with session.desired_property_updates():
            assert session._mqtt_client.enable_twin_patch_receive.await_count == 1
            assert session._mqtt_client.disable_twin_patch_receive.await_count == 0

        assert session._mqtt_client.enable_twin_patch_receive.await_count == 1
        assert session._mqtt_client.disable_twin_patch_receive.await_count == 1

    @pytest.mark.it(
        "Disables twin patch receive upon exit, even if an error is raised inside the context manager block"
    )
    async def test_context_manager_failure(self, session, arbitrary_exception):
        assert session._mqtt_client.enable_twin_patch_receive.await_count == 0
        assert session._mqtt_client.disable_twin_patch_receive.await_count == 0

        try:
            async with session.desired_property_updates():
                assert session._mqtt_client.enable_twin_patch_receive.await_count == 1
                assert session._mqtt_client.disable_twin_patch_receive.await_count == 0
                raise arbitrary_exception
        except type(arbitrary_exception):
            pass

        assert session._mqtt_client.enable_twin_patch_receive.await_count == 1
        assert session._mqtt_client.disable_twin_patch_receive.await_count == 1

    @pytest.mark.it("Yields the IoTHubMQTTClient's incoming twin patch generator")
    async def test_generator(self, session):
        # NOTE: This generator is thoroughly tested in test_iothub_mqtt_client.py
        async with session.desired_property_updates() as updates:
            assert updates is session._mqtt_client.incoming_twin_patches
