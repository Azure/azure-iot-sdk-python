# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import asyncio
import pytest
import ssl
import time
import typing
from dev_utils import custom_mock
from pytest_lazyfixture import lazy_fixture
from azure.iot.device.iothub_session import IoTHubSession
from azure.iot.device import config, models
from azure.iot.device import connection_string as cs
from azure.iot.device import exceptions as exc
from azure.iot.device import iothub_mqtt_client as mqtt
from azure.iot.device import sastoken as st
from azure.iot.device import signing_mechanism as sm

FAKE_DEVICE_ID = "fake_device_id"
FAKE_MODULE_ID = "fake_module_id"
FAKE_HOSTNAME = "fake.hostname"
FAKE_URI = "fake/resource/location"
FAKE_SHARED_ACCESS_KEY = "Zm9vYmFy"
FAKE_SIGNATURE = "ajsc8nLKacIjGsYyB4iYDFCZaRMmmDrUuY5lncYDYPI="

# ~~~~~ Helpers ~~~~~~


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
    mock_client = mocker.patch.object(
        mqtt, "IoTHubMQTTClient", spec=mqtt.IoTHubMQTTClient
    ).return_value
    # Use a HangingAsyncMock here so that the coroutine does not return until we want it to
    mock_client.wait_for_disconnect = custom_mock.HangingAsyncMock()
    return mock_client


@pytest.fixture
def sastoken_str():
    return "SharedAccessSignature sr={resource}&sig={signature}&se={expiry}".format(
        resource=FAKE_URI, signature=FAKE_SIGNATURE, expiry=str(int(time.time()) + 3600)
    )


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
async def session(custom_ssl_context):
    """Use a device configuration and custom SSL auth for simplicity"""
    async with IoTHubSession(
        hostname=FAKE_HOSTNAME, device_id=FAKE_DEVICE_ID, ssl_context=custom_ssl_context
    ) as session:
        yield session


@pytest.fixture
def disconnected_session(custom_ssl_context):
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
    # Provide args in form 'shared_access_key, sastoken, ssl_context'
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
        lazy_fixture("sastoken_str"),
        None,
        id="User-Provided SAS Token Auth + Default SSLContext",
    ),
    pytest.param(
        None,
        lazy_fixture("sastoken_str"),
        lazy_fixture("custom_ssl_context"),
        id="User-Provided SAS Token Auth + Custom SSLContext",
    ),
    pytest.param(None, None, lazy_fixture("custom_ssl_context"), id="Custom SSLContext Auth"),
]
# Just the parameters where SAS auth is used
create_auth_params_sas = [param for param in create_auth_params if "SAS" in param.id]
# Just the parameters where a Shared Access Key auth is used
create_auth_params_sak = [param for param in create_auth_params if param.values[0] is not None]
# Just the parameters where user-provided SAS token auth is used
create_auth_params_user_token = [
    param for param in create_auth_params if param.values[1] is not None
]
# Just the parameters where a custom SSLContext is provided
create_auth_params_custom_ssl = [
    param for param in create_auth_params if param.values[2] is not None
]
# Just the parameters where a custom SSLContext is NOT provided
create_auth_params_default_ssl = [param for param in create_auth_params if param.values[2] is None]


# Covers all option kwargs shared across client factory methods
factory_kwargs = [
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

# TODO: Do these params and associated tests need to be replicated for Provisioning?
# Does the session exit gracefully or because of error?
graceful_exit_params = [
    pytest.param(True, id="graceful exit"),
    pytest.param(False, id="exit because of exception"),
]


@pytest.mark.describe("IoTHubSession -- Instantiation")
class TestIoTHubSessionInstantiation:
    create_id_params = [
        # Provide args in the form 'device_id, module_id'
        pytest.param(FAKE_DEVICE_ID, None, id="Device"),
        pytest.param(FAKE_DEVICE_ID, FAKE_MODULE_ID, id="Module"),
    ]

    @pytest.mark.it(
        "Instantiates and stores a SasTokenGenerator using the `shared_access_key`, if `shared_access_key` is provided"
    )
    @pytest.mark.parametrize("shared_access_key, sastoken, ssl_context", create_auth_params_sak)
    @pytest.mark.parametrize("device_id, module_id", create_id_params)
    async def test_sak_auth(
        self, mocker, device_id, module_id, shared_access_key, sastoken, ssl_context
    ):
        assert sastoken is None
        spy_sk_sm_cls = mocker.spy(sm, "SymmetricKeySigningMechanism")
        spy_st_generator_cls = mocker.spy(st, "SasTokenGenerator")
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
        # SasTokenGenerator was created from the SymmetricKeySigningMechanism
        assert spy_st_generator_cls.call_count == 1
        assert spy_st_generator_cls.call_args == mocker.call(
            signing_mechanism=spy_sk_sm_cls.spy_return, uri=expected_uri, ttl=3600
        )
        # SasTokenGenerator was set on the Session
        assert session._sastoken_generator is spy_st_generator_cls.spy_return

    @pytest.mark.it(
        "Instantiates and stores a SasToken from the `sastoken` string, if `sastoken` is provided"
    )
    @pytest.mark.parametrize(
        "shared_access_key, sastoken, ssl_context", create_auth_params_user_token
    )
    @pytest.mark.parametrize("device_id, module_id", create_id_params)
    async def test_user_sastoken_auth(
        self, device_id, module_id, shared_access_key, sastoken, ssl_context
    ):
        assert shared_access_key is None

        session = IoTHubSession(
            hostname=FAKE_HOSTNAME,
            device_id=device_id,
            module_id=module_id,
            sastoken=sastoken,
            ssl_context=ssl_context,
        )

        assert isinstance(session._user_sastoken, st.SasToken)
        assert str(session._user_sastoken) == sastoken

    @pytest.mark.it(
        "Sets all SAS-related attributes to None if neither `shared_access_key` nor `sastoken` are provided"
    )
    @pytest.mark.parametrize("device_id, module_id", create_id_params)
    async def test_non_sas_auth(self, mocker, device_id, module_id, custom_ssl_context):
        session = IoTHubSession(
            hostname=FAKE_HOSTNAME,
            device_id=device_id,
            module_id=module_id,
            ssl_context=custom_ssl_context,
        )

        # No SAS-related attributes set
        assert session._sastoken_generator is None
        assert session._user_sastoken is None

    @pytest.mark.it(
        "Instantiates and stores an IoTHubMQTTClient, using a new IoTHubClientConfig object"
    )
    @pytest.mark.parametrize("shared_access_key, sastoken, ssl_context", create_auth_params)
    @pytest.mark.parametrize("device_id, module_id", create_id_params)
    async def test_mqtt_client(
        self, mocker, device_id, module_id, shared_access_key, sastoken, ssl_context
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
            sastoken=sastoken,
            ssl_context=ssl_context,
        )

        assert spy_config_cls.call_count == 1
        assert spy_mqtt_cls.call_count == 1
        assert spy_mqtt_cls.call_args == mocker.call(spy_config_cls.spy_return)
        assert session._mqtt_client is spy_mqtt_cls.spy_return

    @pytest.mark.it(
        "Sets the provided `hostname` on the IoTHubClientConfig used to create the IoTHubMQTTClient"
    )
    @pytest.mark.parametrize("shared_access_key, sastoken, ssl_context", create_auth_params)
    @pytest.mark.parametrize("device_id, module_id", create_id_params)
    async def test_hostname(
        self, mocker, device_id, module_id, shared_access_key, sastoken, ssl_context
    ):
        spy_mqtt_cls = mocker.spy(mqtt, "IoTHubMQTTClient")

        IoTHubSession(
            hostname=FAKE_HOSTNAME,
            device_id=device_id,
            module_id=module_id,
            shared_access_key=shared_access_key,
            sastoken=sastoken,
            ssl_context=ssl_context,
        )

        cfg = spy_mqtt_cls.call_args[0][0]
        assert cfg.hostname == FAKE_HOSTNAME

    @pytest.mark.it(
        "Sets the provided `device_id` and `module_id` values on the IoTHubClientConfig used to create the IoTHubMQTTClient"
    )
    @pytest.mark.parametrize("shared_access_key, sastoken, ssl_context", create_auth_params)
    @pytest.mark.parametrize("device_id, module_id", create_id_params)
    async def test_ids(
        self, mocker, device_id, module_id, shared_access_key, sastoken, ssl_context
    ):
        spy_mqtt_cls = mocker.spy(mqtt, "IoTHubMQTTClient")

        IoTHubSession(
            hostname=FAKE_HOSTNAME,
            device_id=device_id,
            module_id=module_id,
            shared_access_key=shared_access_key,
            sastoken=sastoken,
            ssl_context=ssl_context,
        )

        cfg = spy_mqtt_cls.call_args[0][0]
        assert cfg.device_id == device_id
        assert cfg.module_id == module_id

    @pytest.mark.it(
        "Sets the provided `ssl_context` on the IoTHubClientConfig used to create the IoTHubMQTTClient, if provided"
    )
    @pytest.mark.parametrize(
        "shared_access_key, sastoken, ssl_context", create_auth_params_custom_ssl
    )
    @pytest.mark.parametrize("device_id, module_id", create_id_params)
    async def test_custom_ssl_context(
        self, mocker, device_id, module_id, shared_access_key, sastoken, ssl_context
    ):
        spy_mqtt_cls = mocker.spy(mqtt, "IoTHubMQTTClient")

        IoTHubSession(
            hostname=FAKE_HOSTNAME,
            device_id=device_id,
            module_id=module_id,
            shared_access_key=shared_access_key,
            sastoken=sastoken,
            ssl_context=ssl_context,
        )

        cfg = spy_mqtt_cls.call_args[0][0]
        assert cfg.ssl_context is ssl_context

    @pytest.mark.it(
        "Sets a default SSLContext on the IoTHubClientConfig used to create the IoTHubMQTTClient, if `ssl_context` is not provided"
    )
    @pytest.mark.parametrize(
        "shared_access_key, sastoken, ssl_context", create_auth_params_default_ssl
    )
    @pytest.mark.parametrize("device_id, module_id", create_id_params)
    async def test_default_ssl_context(
        self, mocker, device_id, module_id, shared_access_key, sastoken, ssl_context
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
            sastoken=sastoken,
        )

        cfg = spy_mqtt_cls.call_args[0][0]
        ctx = cfg.ssl_context
        assert ctx is my_ssl_context
        # NOTE: ctx protocol is checked in the `return_and_reset` side effect above
        assert ctx.verify_mode == ssl.CERT_REQUIRED
        assert ctx.check_hostname is True
        assert ctx.load_default_certs.call_count == 1
        assert ctx.load_default_certs.call_args == mocker.call()
        assert ctx.minimum_version == ssl.TLSVersion.TLSv1_2

    @pytest.mark.it(
        "Sets `auto_reconnect` to False on the IoTHubClientConfig used to create the IoTHubMQTTClient"
    )
    @pytest.mark.parametrize("shared_access_key, sastoken, ssl_context", create_auth_params)
    @pytest.mark.parametrize("device_id, module_id", create_id_params)
    async def test_auto_reconnect_cfg(
        self, mocker, device_id, module_id, shared_access_key, sastoken, ssl_context
    ):
        spy_mqtt_cls = mocker.spy(mqtt, "IoTHubMQTTClient")

        IoTHubSession(
            hostname=FAKE_HOSTNAME,
            device_id=device_id,
            module_id=module_id,
            shared_access_key=shared_access_key,
            sastoken=sastoken,
            ssl_context=ssl_context,
        )

        cfg = spy_mqtt_cls.call_args[0][0]
        assert cfg.auto_reconnect is False

    @pytest.mark.it(
        "Sets any provided optional keyword arguments on the IoTHubClientConfig used to create the IoTHubMQTTClient"
    )
    @pytest.mark.parametrize("shared_access_key, sastoken, ssl_context", create_auth_params)
    @pytest.mark.parametrize("kwarg_name, kwarg_value", factory_kwargs)
    @pytest.mark.parametrize("device_id, module_id", create_id_params)
    async def test_kwargs(
        self,
        mocker,
        device_id,
        module_id,
        shared_access_key,
        sastoken,
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
            sastoken=sastoken,
            ssl_context=ssl_context,
            **kwargs
        )

        cfg = spy_mqtt_cls.call_args[0][0]
        assert getattr(cfg, kwarg_name) == kwarg_value

    @pytest.mark.it("Sets the `wait_for_disconnect_task` attribute to None")
    @pytest.mark.parametrize("shared_access_key, sastoken, ssl_context", create_auth_params)
    @pytest.mark.parametrize("device_id, module_id", create_id_params)
    async def test_wait_for_disconnect_task(
        self, device_id, module_id, shared_access_key, sastoken, ssl_context
    ):
        session = IoTHubSession(
            hostname=FAKE_HOSTNAME,
            device_id=device_id,
            module_id=module_id,
            shared_access_key=shared_access_key,
            sastoken=sastoken,
            ssl_context=ssl_context,
        )
        assert session._wait_for_disconnect_task is None

    @pytest.mark.it(
        "Raises ValueError if neither `shared_access_key`, `sastoken` nor `ssl_context` are provided as parameters"
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
        "Raises ValueError if both `shared_access_key` and `sastoken` are provided as parameters"
    )
    @pytest.mark.parametrize("device_id, module_id", create_id_params)
    async def test_conflicting_auth(self, device_id, module_id, sastoken_str, optional_ssl_context):
        with pytest.raises(ValueError):
            IoTHubSession(
                hostname=FAKE_HOSTNAME,
                device_id=device_id,
                module_id=module_id,
                shared_access_key=FAKE_SHARED_ACCESS_KEY,
                sastoken=sastoken_str,
                ssl_context=optional_ssl_context,
            )

    @pytest.mark.it("Raises ValueError if the provided `sastoken` is already expired")
    @pytest.mark.parametrize("device_id, module_id", create_id_params)
    async def test_expired_sastoken(self, device_id, module_id, optional_ssl_context):
        expired_sastoken_str = (
            "SharedAccessSignature sr={resource}&sig={signature}&se={expiry}".format(
                resource=FAKE_URI, signature=FAKE_SIGNATURE, expiry=str(int(time.time()) - 10)
            )
        )

        with pytest.raises(ValueError):
            IoTHubSession(
                hostname=FAKE_HOSTNAME,
                device_id=device_id,
                module_id=module_id,
                sastoken=expired_sastoken_str,
                ssl_context=optional_ssl_context,
            )

    @pytest.mark.it("Raises TypeError if an invalid keyword argument is provided")
    @pytest.mark.parametrize("shared_access_key, sastoken, ssl_context", create_auth_params)
    @pytest.mark.parametrize("device_id, module_id", create_id_params)
    async def test_bad_kwarg(self, device_id, module_id, shared_access_key, sastoken, ssl_context):
        with pytest.raises(TypeError):
            IoTHubSession(
                hostname=FAKE_HOSTNAME,
                device_id=device_id,
                module_id=module_id,
                shared_access_key=shared_access_key,
                sastoken=sastoken,
                ssl_context=ssl_context,
                invalid_argument="some value",
            )

    @pytest.mark.it(
        "Allows any exceptions raised when creating a SymmetricKeySigningMechanism to propagate"
    )
    @pytest.mark.parametrize("exception", sk_sm_create_exceptions)
    @pytest.mark.parametrize("shared_access_key, sastoken, ssl_context", create_auth_params_sak)
    @pytest.mark.parametrize("device_id, module_id", create_id_params)
    async def test_sksm_raises(
        self, mocker, device_id, module_id, shared_access_key, sastoken, ssl_context, exception
    ):
        mocker.patch.object(sm, "SymmetricKeySigningMechanism", side_effect=exception)
        assert sastoken is None

        with pytest.raises(type(exception)) as e_info:
            IoTHubSession(
                hostname=FAKE_HOSTNAME,
                device_id=device_id,
                module_id=module_id,
                shared_access_key=shared_access_key,
                sastoken=sastoken,
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
    @pytest.fixture
    def session(self, disconnected_session):
        return disconnected_session

    @pytest.mark.it(
        "Sets the user-provided SasToken on the IoTHubMQTTClient upon entry into the context manager, if using user-provided SAS auth"
    )
    async def test_user_provided_sas(self, mocker, session, sastoken_str):
        session._user_sastoken = st.SasToken(sastoken_str)
        assert session._mqtt_client.set_sastoken.call_count == 0

        async with session as session:
            assert session._mqtt_client.set_sastoken.call_count == 1
            assert session._mqtt_client.set_sastoken.call_args == mocker.call(
                session._user_sastoken
            )

        assert session._mqtt_client.set_sastoken.call_count == 1

    @pytest.mark.it(
        "Generates a SasToken using the SasTokenGenerator, and sets it on the IoTHubMQTTClient upon entry into the context manager, if using Shared Access Key SAS auth"
    )
    async def test_sak_generation_sas(self, mocker, session):
        session._sastoken_generator = mocker.MagicMock(spec=st.SasTokenGenerator)
        assert session._sastoken_generator.generate_sastoken.await_count == 0
        assert session._mqtt_client.set_sastoken.call_count == 0

        async with session as session:
            assert session._sastoken_generator.generate_sastoken.await_count == 1
            assert session._sastoken_generator.generate_sastoken.await_args == mocker.call()
            assert session._mqtt_client.set_sastoken.call_count == 1
            assert session._mqtt_client.set_sastoken.call_args == mocker.call(
                session._sastoken_generator.generate_sastoken.return_value
            )

        assert session._sastoken_generator.generate_sastoken.call_count == 1
        assert session._mqtt_client.set_sastoken.call_count == 1

    @pytest.mark.it("Does not set any SasToken on the IoTHubMQTTClient if not using SAS auth")
    async def test_no_sas(self, session):
        assert session._user_sastoken is None
        assert session._sastoken_generator is None
        assert session._mqtt_client.set_sastoken.call_count == 0

        async with session as session:
            assert session._mqtt_client.set_sastoken.call_count == 0

        assert session._mqtt_client.set_sastoken.call_count == 0

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
        "Creates a Task from the MQTTClient's .wait_for_disconnect() coroutine method and stores it as the `wait_for_disconnect_task` attribute upon entry into the context manager, and cancels and clears the Task upon exit"
    )
    async def test_wait_for_disconnect_task(self, mocker, session):
        assert session._wait_for_disconnect_task is None
        assert session._mqtt_client.wait_for_disconnect.call_count == 0

        async with session as session:
            # Task Created and Method called
            assert isinstance(session._wait_for_disconnect_task, asyncio.Task)
            assert not session._wait_for_disconnect_task.done()
            assert session._mqtt_client.wait_for_disconnect.call_count == 1
            assert session._mqtt_client.wait_for_disconnect.call_args == mocker.call()
            await asyncio.sleep(0.1)
            assert session._mqtt_client.wait_for_disconnect.is_hanging()
            # Returning method completes task (thus task corresponds to method)
            session._mqtt_client.wait_for_disconnect.stop_hanging()
            await asyncio.sleep(0.1)
            assert session._wait_for_disconnect_task.done()
            assert (
                session._wait_for_disconnect_task.result()
                is session._mqtt_client.wait_for_disconnect.return_value
            )
            # Replace the task with a mock so we can show it is cancelled/cleared on exit
            mock_task = mocker.MagicMock()
            session._wait_for_disconnect_task = mock_task
            assert mock_task.cancel.call_count == 0

        # Mocked task was cancelled and cleared
        assert mock_task.cancel.call_count == 1
        assert session._wait_for_disconnect_task is None

    @pytest.mark.it(
        "Cancels and clears the `wait_for_disconnect_task` Task, even if an error was raised within the block inside the context manager"
    )
    async def test_wait_for_disconnect_task_with_failure(self, session, arbitrary_exception):
        assert session._wait_for_disconnect_task is None

        try:
            async with session as session:
                task = session._wait_for_disconnect_task
                assert task is not None
                assert not task.done()
                raise arbitrary_exception
        except type(arbitrary_exception):
            pass

        await asyncio.sleep(0.1)
        assert session._wait_for_disconnect_task is None
        assert task.done()
        assert task.cancelled()

    @pytest.mark.it(
        "Allows any errors raised within the block inside the context manager to propagate"
    )
    @pytest.mark.parametrize(
        "exception",
        [
            pytest.param(lazy_fixture("arbitrary_exception"), id="Unexpected Exception"),
            # NOTE: it is important to test the CancelledError since it is a regular Exception in 3.7,
            # but a BaseException from 3.8+
            pytest.param(asyncio.CancelledError(), id="CancelledError"),
        ],
    )
    async def test_error_propagation(self, session, exception):
        with pytest.raises(type(exception)) as e_info:
            async with session as session:
                raise exception
        assert e_info.value is exception

    # NOTE: This shouldn't happen, but we test it anyway
    @pytest.mark.it(
        "Allows any errors raised while starting the IoTHubMQTTClient during context manager entry to propagate"
    )
    async def test_enter_mqtt_client_start_raises(self, session, arbitrary_exception):
        session._mqtt_client.start.side_effect = arbitrary_exception

        with pytest.raises(type(arbitrary_exception)) as e_info:
            async with session as session:
                pass
        assert e_info.value is arbitrary_exception

    # NOTE: This shouldn't happen, but we test it anyway
    @pytest.mark.it(
        "Stops the IoTHubMQTTClient that was previously started, and does not create the `wait_for_disconnect_task`, if an error is raised while starting the IoTHubMQTTClient during context manager entry"
    )
    async def test_enter_mqtt_client_start_raises_cleanup(
        self, mocker, session, arbitrary_exception
    ):
        session._mqtt_client.start.side_effect = arbitrary_exception
        assert session._mqtt_client.stop.await_count == 0
        assert session._wait_for_disconnect_task is None
        spy_create_task = mocker.spy(asyncio, "create_task")

        with pytest.raises(type(arbitrary_exception)):
            async with session as session:
                pass

        assert session._mqtt_client.stop.await_count == 1
        assert session._wait_for_disconnect_task is None
        assert spy_create_task.call_count == 0

    @pytest.mark.it(
        "Allows any errors raised while connecting with the IoTHubMQTTClient during context manager entry to propagate"
    )
    @pytest.mark.parametrize(
        "exception",
        [
            pytest.param(exc.MQTTConnectionFailedError(), id="MQTTConnectionFailedError"),
            pytest.param(exc.CredentialError(), id="CredentialError"),
            pytest.param(lazy_fixture("arbitrary_exception"), id="Unexpected Exception"),
        ],
    )
    async def test_enter_mqtt_client_connect_raises(self, session, exception):
        session._mqtt_client.connect.side_effect = exception

        with pytest.raises(type(exception)) as e_info:
            async with session as session:
                pass
        assert e_info.value is exception

    @pytest.mark.it(
        "Stops the IoTHubMQTTClient that was previously started, and does not create the `wait_for_disconnect_task`, if an error is raised while connecting during context manager entry"
    )
    @pytest.mark.parametrize(
        "exception",
        [
            pytest.param(exc.MQTTConnectionFailedError(), id="MQTTConnectionFailedError"),
            pytest.param(lazy_fixture("arbitrary_exception"), id="Unexpected Exception"),
        ],
    )
    async def test_enter_mqtt_client_connect_raises_cleanup(self, mocker, session, exception):
        session._mqtt_client.connect.side_effect = exception
        assert session._mqtt_client.stop.await_count == 0
        assert session._wait_for_disconnect_task is None
        spy_create_task = mocker.spy(asyncio, "create_task")

        with pytest.raises(type(exception)):
            async with session as session:
                pass

        assert session._mqtt_client.stop.await_count == 1
        assert session._wait_for_disconnect_task is None
        assert spy_create_task.call_count == 0

    # NOTE: This shouldn't happen, but we test it anyway
    @pytest.mark.it(
        "Allows any errors raised while disconnecting the IoTHubMQTTClient during context manager exit to propagate"
    )
    async def test_exit_disconnect_raises(self, session, arbitrary_exception):
        session._mqtt_client.disconnect.side_effect = arbitrary_exception

        with pytest.raises(type(arbitrary_exception)) as e_info:
            async with session as session:
                pass
        assert e_info.value is arbitrary_exception

    # NOTE: This shouldn't happen, but we test it anyway
    @pytest.mark.it(
        "Stops the IoTHubMQTTClient and cancels and clears the `wait_for_disconnect_task`, even if an error was raised while disconnecting the IoTHubMQTTClient during context manager exit"
    )
    async def test_exit_disconnect_raises_cleanup(self, session, arbitrary_exception):
        session._mqtt_client.disconnect.side_effect = arbitrary_exception
        assert session._mqtt_client.stop.await_count == 0
        assert session._wait_for_disconnect_task is None

        with pytest.raises(type(arbitrary_exception)):
            async with session as session:
                conn_drop_task = session._wait_for_disconnect_task
                assert not conn_drop_task.done()

        assert session._mqtt_client.stop.await_count == 1
        await asyncio.sleep(0.1)
        assert session._wait_for_disconnect_task is None
        assert conn_drop_task.cancelled()

    # NOTE: This shouldn't happen, but we test it anyway
    @pytest.mark.it(
        "Allows any errors raised while stopping the IoTHubMQTTClient during context manager exit to propagate"
    )
    async def test_exit_mqtt_client_stop_raises(self, session, arbitrary_exception):
        session._mqtt_client.stop.side_effect = arbitrary_exception

        with pytest.raises(type(arbitrary_exception)) as e_info:
            async with session as session:
                pass
        assert e_info.value is arbitrary_exception

    # NOTE: This shouldn't happen, but we test it anyway
    @pytest.mark.it(
        "Disconnects the IoTHubMQTTClient, and cancels and clears the `wait_for_disconnect_task`, even if an error was raised while stopping the IoTHubMQTTClient during context manager exit"
    )
    async def test_exit_mqtt_client_stop_raises_cleanup(self, session, arbitrary_exception):
        session._mqtt_client.stop.side_effect = arbitrary_exception
        assert session._mqtt_client.disconnect.await_count == 0
        assert session._wait_for_disconnect_task is None

        with pytest.raises(type(arbitrary_exception)):
            async with session as session:
                conn_drop_task = session._wait_for_disconnect_task
                assert not conn_drop_task.done()

        assert session._mqtt_client.disconnect.await_count == 1
        await asyncio.sleep(0.1)
        assert session._wait_for_disconnect_task is None
        assert conn_drop_task.cancelled()

    # TODO: consider adding detailed cancellation tests
    # Not sure how cancellation would work in a context manager situation, needs more investigation


@pytest.mark.describe("IoTHubSession - .update_sastoken()")
class TestIoTHubSessionUpdateSastoken:
    @pytest.fixture(autouse=True)
    def modify_session(self, session):
        # Session needs to be configured with an existing SasToken
        old_sastoken = "SharedAccessSignature sr={resource}&sig={signature}&se={expiry}".format(
            resource=FAKE_URI, signature=FAKE_SIGNATURE, expiry=str(int(time.time()) + 30)
        )
        session._user_sastoken = st.SasToken(old_sastoken)

    @pytest.mark.it(
        "Instantiates and stores a SasToken from the `sastoken` string, if already using user-provided SAS auth"
    )
    async def test_updates_sastoken(self, session, sastoken_str):
        assert session._user_sastoken is not None
        assert str(session._user_sastoken) != sastoken_str

        session.update_sastoken(sastoken_str)

        assert isinstance(session._user_sastoken, st.SasToken)
        assert str(session._user_sastoken) == sastoken_str

    @pytest.mark.it(
        "Raises SessionError if the IoTHubSession is not already using user-provided SAS auth"
    )
    async def test_not_user_sas(self, session, sastoken_str):
        session._user_sastoken = None

        with pytest.raises(exc.SessionError):
            session.update_sastoken(sastoken_str)

    @pytest.mark.it("Raises ValueError if the provided `sastoken` is already expired")
    async def test_expired_sastoken(self, session):
        assert session._user_sastoken is not None
        expired_sastoken_str = (
            "SharedAccessSignature sr={resource}&sig={signature}&se={expiry}".format(
                resource=FAKE_URI, signature=FAKE_SIGNATURE, expiry=str(int(time.time()) - 10)
            )
        )

        with pytest.raises(ValueError):
            session.update_sastoken(expired_sastoken_str)


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
            pytest.param(exc.MQTTError(5), id="MQTTError"),
            pytest.param(ValueError(), id="ValueError"),
            pytest.param(lazy_fixture("arbitrary_exception"), id="Unexpected Error"),
        ],
    )
    async def test_mqtt_client_raises(self, session, exception):
        session._mqtt_client.send_message.side_effect = exception

        with pytest.raises(type(exception)) as e_info:
            await session.send_message("hi")
        assert e_info.value is exception

    @pytest.mark.it(
        "Raises SessionError without invoking .send_message() on the IoTHubMQTTClient if it is not connected"
    )
    async def test_not_connected(self, mocker, session):
        conn_property_mock = mocker.PropertyMock(return_value=False)
        type(session._mqtt_client).connected = conn_property_mock

        with pytest.raises(exc.SessionError):
            await session.send_message("hi")
        assert session._mqtt_client.send_message.call_count == 0

    @pytest.mark.it(
        "Raises CancelledError if an expected disconnect occurs in the IoTHubMQTTClient while waiting for the operation to complete"
    )
    async def test_expected_disconnect_during_send(self, session):
        session._mqtt_client.send_message = custom_mock.HangingAsyncMock()

        t = asyncio.create_task(session.send_message("hi"))

        # Hanging, waiting for send to finish
        await session._mqtt_client.send_message.wait_for_hang()
        assert not t.done()

        # No disconnect yet
        assert not session._wait_for_disconnect_task.done()
        assert session._mqtt_client.wait_for_disconnect.call_count == 1
        assert session._mqtt_client.wait_for_disconnect.is_hanging()

        # Simulate expected disconnect
        session._mqtt_client.wait_for_disconnect.return_value = None
        session._mqtt_client.wait_for_disconnect.stop_hanging()

        with pytest.raises(asyncio.CancelledError):
            await t

    @pytest.mark.it(
        "Raises the MQTTConnectionDroppedError that caused the unexpected disconnect, if an unexpected disconnect occurs in the IoTHubMQTTClient while waiting for the operation to complete"
    )
    async def test_unexpected_disconnect_during_send(self, session):
        session._mqtt_client.send_message = custom_mock.HangingAsyncMock()

        t = asyncio.create_task(session.send_message("hi"))

        # Hanging, waiting for send to finish
        await session._mqtt_client.send_message.wait_for_hang()
        assert not t.done()

        # No unexpected disconnect yet
        assert not session._wait_for_disconnect_task.done()
        assert session._mqtt_client.wait_for_disconnect.call_count == 1
        assert session._mqtt_client.wait_for_disconnect.is_hanging()

        # Simulate unexpected disconnect
        cause = exc.MQTTConnectionDroppedError(rc=7)
        session._mqtt_client.wait_for_disconnect.return_value = cause
        session._mqtt_client.wait_for_disconnect.stop_hanging()

        with pytest.raises(exc.MQTTConnectionDroppedError) as e_info:
            await t
        assert e_info.value is cause

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
            pytest.param(exc.MQTTError(5), id="MQTTError"),
            pytest.param(ValueError(), id="ValueError"),
            pytest.param(lazy_fixture("arbitrary_exception"), id="Unexpected Error"),
        ],
    )
    async def test_mqtt_client_raises(self, session, direct_method_response, exception):
        session._mqtt_client.send_direct_method_response.side_effect = exception

        with pytest.raises(type(exception)) as e_info:
            await session.send_direct_method_response(direct_method_response)
        assert e_info.value is exception

    @pytest.mark.it(
        "Raises SessionError without invoking .send_direct_method_response() on the IoTHubMQTTClient if it is not connected"
    )
    async def test_not_connected(self, mocker, session, direct_method_response):
        conn_property_mock = mocker.PropertyMock(return_value=False)
        type(session._mqtt_client).connected = conn_property_mock

        with pytest.raises(exc.SessionError):
            await session.send_direct_method_response(direct_method_response)
        assert session._mqtt_client.send_message.call_count == 0

    @pytest.mark.it(
        "Raises CancelledError if an expected disconnect occurs in the IoTHubMQTTClient while waiting for the operation to complete"
    )
    async def test_expected_disconnect_during_send(self, session, direct_method_response):
        session._mqtt_client.send_direct_method_response = custom_mock.HangingAsyncMock()

        t = asyncio.create_task(session.send_direct_method_response(direct_method_response))

        # Hanging, waiting for send to finish
        await session._mqtt_client.send_direct_method_response.wait_for_hang()
        assert not t.done()

        # No disconnect yet
        assert not session._wait_for_disconnect_task.done()
        assert session._mqtt_client.wait_for_disconnect.call_count == 1
        assert session._mqtt_client.wait_for_disconnect.is_hanging()

        # Simulate expected disconnect
        session._mqtt_client.wait_for_disconnect.return_value = None
        session._mqtt_client.wait_for_disconnect.stop_hanging()

        with pytest.raises(asyncio.CancelledError):
            await t

    @pytest.mark.it(
        "Raises the MQTTConnectionDroppedError that caused the unexpected disconnect, if an unexpected disconnect occurs in the IoTHubMQTTClient while waiting for the operation to complete"
    )
    async def test_unexpected_disconnect_during_send(self, session, direct_method_response):
        session._mqtt_client.send_direct_method_response = custom_mock.HangingAsyncMock()

        t = asyncio.create_task(session.send_direct_method_response(direct_method_response))

        # Hanging, waiting for send to finish
        await session._mqtt_client.send_direct_method_response.wait_for_hang()
        assert not t.done()

        # No unexpected disconnect yet
        assert not session._wait_for_disconnect_task.done()
        assert session._mqtt_client.wait_for_disconnect.call_count == 1
        assert session._mqtt_client.wait_for_disconnect.is_hanging()

        # Simulate unexpected disconnect
        cause = exc.MQTTConnectionDroppedError(rc=7)
        session._mqtt_client.wait_for_disconnect.return_value = cause
        session._mqtt_client.wait_for_disconnect.stop_hanging()

        with pytest.raises(exc.MQTTConnectionDroppedError) as e_info:
            await t
        assert e_info.value is cause

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
            pytest.param(exc.IoTHubError(), id="IoTHubError"),
            pytest.param(exc.MQTTError(5), id="MQTTError"),
            pytest.param(ValueError(), id="ValueError"),
            pytest.param(asyncio.CancelledError(), id="CancelledError"),
            pytest.param(lazy_fixture("arbitrary_exception"), id="Unexpected Error"),
        ],
    )
    async def test_mqtt_client_raises(self, session, patch, exception):
        session._mqtt_client.send_twin_patch.side_effect = exception

        with pytest.raises(type(exception)) as e_info:
            await session.update_reported_properties(patch)
        # CancelledError doesn't propagate in some versions of Python
        # TODO: determine which versions exactly
        if not isinstance(exception, asyncio.CancelledError):
            assert e_info.value is exception

    @pytest.mark.it(
        "Raises SessionError without invoking .send_twin_patch() on the IoTHubMQTTClient if it is not connected"
    )
    async def test_not_connected(self, mocker, session, patch):
        conn_property_mock = mocker.PropertyMock(return_value=False)
        type(session._mqtt_client).connected = conn_property_mock

        with pytest.raises(exc.SessionError):
            await session.update_reported_properties(patch)
        assert session._mqtt_client.send_twin_patch.call_count == 0

    @pytest.mark.it(
        "Raises CancelledError if an expected disconnect occurs in the IoTHubMQTTClient while waiting for the operation to complete"
    )
    async def test_expected_disconnect_during_send(self, session, patch):
        session._mqtt_client.send_twin_patch = custom_mock.HangingAsyncMock()

        t = asyncio.create_task(session.update_reported_properties(patch))

        # Hanging, waiting for send to finish
        await session._mqtt_client.send_twin_patch.wait_for_hang()
        assert not t.done()

        # No disconnect yet
        assert not session._wait_for_disconnect_task.done()
        assert session._mqtt_client.wait_for_disconnect.call_count == 1
        assert session._mqtt_client.wait_for_disconnect.is_hanging()

        # Simulate expected disconnect
        session._mqtt_client.wait_for_disconnect.return_value = None
        session._mqtt_client.wait_for_disconnect.stop_hanging()

        with pytest.raises(asyncio.CancelledError):
            await t

    @pytest.mark.it(
        "Raises the MQTTConnectionDroppedError that caused the unexpected disconnect, if an unexpected disconnect occurs in the IoTHubMQTTClient while waiting for the operation to complete"
    )
    async def test_unexpected_disconnect_during_send(self, session, patch):
        session._mqtt_client.send_twin_patch = custom_mock.HangingAsyncMock()

        t = asyncio.create_task(session.update_reported_properties(patch))

        # Hanging, waiting for send to finish
        await session._mqtt_client.send_twin_patch.wait_for_hang()
        assert not t.done()

        # No unexpected disconnect yet
        assert not session._wait_for_disconnect_task.done()
        assert session._mqtt_client.wait_for_disconnect.call_count == 1
        assert session._mqtt_client.wait_for_disconnect.is_hanging()

        # Simulate unexpected disconnect
        cause = exc.MQTTConnectionDroppedError(rc=7)
        session._mqtt_client.wait_for_disconnect.return_value = cause
        session._mqtt_client.wait_for_disconnect.stop_hanging()

        with pytest.raises(exc.MQTTConnectionDroppedError) as e_info:
            await t
        assert e_info.value is cause

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
            pytest.param(exc.IoTHubError(), id="IoTHubError"),
            pytest.param(exc.MQTTError(5), id="MQTTError"),
            pytest.param(asyncio.CancelledError(), id="CancelledError"),
            pytest.param(lazy_fixture("arbitrary_exception"), id="Unexpected Error"),
        ],
    )
    async def test_mqtt_client_raises(self, session, exception):
        session._mqtt_client.get_twin.side_effect = exception

        with pytest.raises(type(exception)) as e_info:
            await session.get_twin()
        # CancelledError doesn't propagate in some versions of Python
        # TODO: determine which versions exactly
        if not isinstance(exception, asyncio.CancelledError):
            assert e_info.value is exception

    @pytest.mark.it(
        "Raises SessionError without invoking .get_twin() on the IoTHubMQTTClient if it is not connected"
    )
    async def test_not_connected(self, mocker, session):
        conn_property_mock = mocker.PropertyMock(return_value=False)
        type(session._mqtt_client).connected = conn_property_mock

        with pytest.raises(exc.SessionError):
            await session.get_twin()
        assert session._mqtt_client.get_twin.call_count == 0

    @pytest.mark.it(
        "Raises CancelledError if an expected disconnect occurs in the IoTHubMQTTClient while waiting for the operation to complete"
    )
    async def test_expected_disconnect_during_send(self, session):
        session._mqtt_client.get_twin = custom_mock.HangingAsyncMock()

        t = asyncio.create_task(session.get_twin())

        # Hanging, waiting for send to finish
        await session._mqtt_client.get_twin.wait_for_hang()
        assert not t.done()

        # No disconnect yet
        assert not session._wait_for_disconnect_task.done()
        assert session._mqtt_client.wait_for_disconnect.call_count == 1
        assert session._mqtt_client.wait_for_disconnect.is_hanging()

        # Simulate expected disconnect
        session._mqtt_client.wait_for_disconnect.return_value = None
        session._mqtt_client.wait_for_disconnect.stop_hanging()

        with pytest.raises(asyncio.CancelledError):
            await t

    @pytest.mark.it(
        "Raises the MQTTConnectionDroppedError that caused the unexpected disconnect, if an unexpected disconnect occurs in the IoTHubMQTTClient while waiting for the operation to complete"
    )
    async def test_unexpected_disconnect_during_send(self, session):
        session._mqtt_client.get_twin = custom_mock.HangingAsyncMock()

        t = asyncio.create_task(session.get_twin())

        # Hanging, waiting for send to finish
        await session._mqtt_client.get_twin.wait_for_hang()
        assert not t.done()

        # No unexpected disconnect yet
        assert not session._wait_for_disconnect_task.done()
        assert session._mqtt_client.wait_for_disconnect.call_count == 1
        assert session._mqtt_client.wait_for_disconnect.is_hanging()

        # Simulate unexpected disconnect
        cause = exc.MQTTConnectionDroppedError(rc=7)
        session._mqtt_client.wait_for_disconnect.return_value = cause
        session._mqtt_client.wait_for_disconnect.stop_hanging()

        with pytest.raises(exc.MQTTConnectionDroppedError) as e_info:
            await t
        assert e_info.value is cause

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

    @pytest.mark.it(
        "Does not attempt to disable C2D message receive upon exit if IoTHubMQTTClient is disconnected"
    )
    @pytest.mark.parametrize("graceful_exit", graceful_exit_params)
    async def test_context_manager_exit_while_disconnected(
        self, session, arbitrary_exception, graceful_exit
    ):
        assert session._mqtt_client.enable_c2d_message_receive.await_count == 0
        assert session._mqtt_client.disable_c2d_message_receive.await_count == 0

        try:
            async with session.messages():
                assert session._mqtt_client.enable_c2d_message_receive.await_count == 1
                assert session._mqtt_client.disable_c2d_message_receive.await_count == 0
                session._mqtt_client.connected = False
                if not graceful_exit:
                    raise arbitrary_exception
        except type(arbitrary_exception):
            pass

        assert session._mqtt_client.enable_c2d_message_receive.await_count == 1
        assert session._mqtt_client.disable_c2d_message_receive.await_count == 0

    @pytest.mark.it(
        "Yields an AsyncGenerator that yields the C2D messages yielded by the IoTHubMQTTClient's incoming C2D message generator"
    )
    async def test_generator_yield(self, mocker, session):
        # Mock IoTHubMQTTClient C2D generator to yield Messages
        yielded_c2d_messages = [models.Message("1"), models.Message("2"), models.Message("3")]
        mock_c2d_gen = mocker.AsyncMock()
        mock_c2d_gen.__anext__.side_effect = yielded_c2d_messages
        # Set it to be returned by PropertyMock
        c2d_gen_property_mock = mocker.PropertyMock(return_value=mock_c2d_gen)
        type(session._mqtt_client).incoming_c2d_messages = c2d_gen_property_mock

        assert not session._wait_for_disconnect_task.done()
        async with session.messages() as messages:
            # Is a generator
            assert isinstance(messages, typing.AsyncGenerator)
            # Yields values from the IoTHubMQTTClient C2D generator
            assert mock_c2d_gen.__anext__.await_count == 0
            val = await messages.__anext__()
            assert val is yielded_c2d_messages[0]
            assert mock_c2d_gen.__anext__.await_count == 1
            val = await messages.__anext__()
            assert val is yielded_c2d_messages[1]
            assert mock_c2d_gen.__anext__.await_count == 2
            val = await messages.__anext__()
            assert val is yielded_c2d_messages[2]
            assert mock_c2d_gen.__anext__.await_count == 3

    @pytest.mark.it(
        "Yields an AsyncGenerator that will raise the MQTTConnectionDroppedError that caused an unexpected disconnect in the IoTHubMQTTClient in the event of an unexpected disconnection"
    )
    async def test_generator_raise_unexpected_disconnect(self, mocker, session):
        # Mock IoTHubMQTTClient C2D generator to not yield anything yet
        mock_c2d_gen = mocker.AsyncMock()
        mock_c2d_gen.__anext__ = custom_mock.HangingAsyncMock()
        # Set it to be returned by PropertyMock
        c2d_gen_property_mock = mocker.PropertyMock(return_value=mock_c2d_gen)
        type(session._mqtt_client).incoming_c2d_messages = c2d_gen_property_mock

        async with session.messages() as messages:
            # Waiting for new item from generator (since mock is hanging / not returning)
            t = asyncio.create_task(messages.__anext__())
            await asyncio.sleep(0.1)
            assert not t.done()

            # No unexpected disconnect yet
            assert not session._wait_for_disconnect_task.done()
            assert session._mqtt_client.wait_for_disconnect.call_count == 1
            assert session._mqtt_client.wait_for_disconnect.is_hanging()

            # Trigger unexpected disconnect
            cause = exc.MQTTConnectionDroppedError(rc=7)
            session._mqtt_client.wait_for_disconnect.return_value = cause
            session._mqtt_client.wait_for_disconnect.stop_hanging()
            await asyncio.sleep(0.1)

            # Generator raised the error that caused disconnect
            assert t.done()
            assert t.exception() is cause

    @pytest.mark.it(
        "Yields an AsyncGenerator that will raise a CancelledError if the event of an expected disconnection"
    )
    async def test_generator_raise_expected_disconnect(self, mocker, session):
        # Mock IoTHubMQTTClient C2D generator to not yield anything yet
        mock_c2d_gen = mocker.AsyncMock()
        mock_c2d_gen.__anext__ = custom_mock.HangingAsyncMock()
        # Set it to be returned by PropertyMock
        c2d_gen_property_mock = mocker.PropertyMock(return_value=mock_c2d_gen)
        type(session._mqtt_client).incoming_c2d_messages = c2d_gen_property_mock

        async with session.messages() as messages:
            # Waiting for new item from generator (since mock is hanging / not returning)
            t = asyncio.create_task(messages.__anext__())
            await asyncio.sleep(0.1)
            assert not t.done()

            # No disconnect yet
            assert not session._wait_for_disconnect_task.done()
            assert session._mqtt_client.wait_for_disconnect.call_count == 1
            assert session._mqtt_client.wait_for_disconnect.is_hanging()

            # Trigger expected disconnect
            session._mqtt_client.wait_for_disconnect.return_value = None
            session._mqtt_client.wait_for_disconnect.stop_hanging()
            await asyncio.sleep(0.1)

            # Generator raised CancelledError
            assert t.done()
            assert t.cancelled()

    @pytest.mark.it(
        "Raises SessionError without enabling C2D message receive on the IoTHubMQTTClient if it is not connected"
    )
    async def test_not_connected(self, mocker, session):
        conn_property_mock = mocker.PropertyMock(return_value=False)
        type(session._mqtt_client).connected = conn_property_mock

        with pytest.raises(exc.SessionError):
            async with session.messages():
                pass
        assert session._mqtt_client.enable_c2d_message_receive.call_count == 0

    @pytest.mark.it(
        "Allows any errors raised while attempting to enable C2D message receive to propagate"
    )
    @pytest.mark.parametrize(
        "exception",
        [
            pytest.param(exc.MQTTError(rc=4), id="MQTTError"),
            pytest.param(lazy_fixture("arbitrary_exception"), id="Unexpected Exception"),
        ],
    )
    async def test_enable_raises(self, session, exception):
        session._mqtt_client.enable_c2d_message_receive.side_effect = exception

        with pytest.raises(type(exception)) as e_info:
            async with session.messages():
                pass
        assert e_info.value is exception
        assert session._mqtt_client.enable_c2d_message_receive.call_count == 1

    @pytest.mark.it(
        "Suppresses any MQTTErrors raised while attempting to disable C2D message receive"
    )
    async def test_disable_raises_mqtt_error(self, session):
        session._mqtt_client.disable_c2d_message_receive.side_effect = exc.MQTTError(rc=4)

        async with session.messages():
            pass
        assert session._mqtt_client.disable_c2d_message_receive.call_count == 1
        # No error raised -> success

    @pytest.mark.it(
        "Allows any unexpected errors raised while attempting to disable C2D message receive to propagate"
    )
    async def test_disable_raises_unexpected(self, session, arbitrary_exception):
        session._mqtt_client.disable_c2d_message_receive.side_effect = arbitrary_exception

        with pytest.raises(type(arbitrary_exception)) as e_info:
            async with session.messages():
                pass
        assert e_info.value is arbitrary_exception
        assert session._mqtt_client.disable_c2d_message_receive.call_count == 1


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

    @pytest.mark.it(
        "Does not attempt to disable direct method request receive upon exit if IoTHubMQTTClient is disconnected"
    )
    @pytest.mark.parametrize("graceful_exit", graceful_exit_params)
    async def test_context_manager_exit_while_disconnected(
        self, session, arbitrary_exception, graceful_exit
    ):
        assert session._mqtt_client.enable_direct_method_request_receive.await_count == 0
        assert session._mqtt_client.disable_direct_method_request_receive.await_count == 0

        try:
            async with session.direct_method_requests():
                assert session._mqtt_client.enable_direct_method_request_receive.await_count == 1
                assert session._mqtt_client.disable_direct_method_request_receive.await_count == 0
                session._mqtt_client.connected = False
                if not graceful_exit:
                    raise arbitrary_exception
        except type(arbitrary_exception):
            pass

        assert session._mqtt_client.enable_direct_method_request_receive.await_count == 1
        assert session._mqtt_client.disable_direct_method_request_receive.await_count == 0

    @pytest.mark.it(
        "Yields an AsyncGenerator that yields the direct method requests yielded by the IoTHubMQTTClient's incoming direct method request message generator"
    )
    async def test_generator_yield(self, mocker, session):
        # Mock IoTHubMQTTClient direct method request generator to yield DirectMethodRequests
        yielded_direct_method_requests = [
            models.DirectMethodRequest("1", "m1", ""),
            models.DirectMethodRequest("2", "m2", ""),
            models.DirectMethodRequest("3", "m3", ""),
        ]
        mock_dm_gen = mocker.AsyncMock()
        mock_dm_gen.__anext__.side_effect = yielded_direct_method_requests
        # Set it to be returned by PropertyMock
        dm_gen_property_mock = mocker.PropertyMock(return_value=mock_dm_gen)
        type(session._mqtt_client).incoming_direct_method_requests = dm_gen_property_mock

        assert not session._wait_for_disconnect_task.done()
        async with session.direct_method_requests() as direct_method_requests:
            # Is a generator
            assert isinstance(direct_method_requests, typing.AsyncGenerator)
            # Yields values from the IoTHubMQTTClient direct method request generator
            assert mock_dm_gen.__anext__.await_count == 0
            val = await direct_method_requests.__anext__()
            assert val is yielded_direct_method_requests[0]
            assert mock_dm_gen.__anext__.await_count == 1
            val = await direct_method_requests.__anext__()
            assert val is yielded_direct_method_requests[1]
            assert mock_dm_gen.__anext__.await_count == 2
            val = await direct_method_requests.__anext__()
            assert val is yielded_direct_method_requests[2]
            assert mock_dm_gen.__anext__.await_count == 3

    @pytest.mark.it(
        "Yields an AsyncGenerator that will raise the MQTTConnectionDroppedError that caused an unexpected disconnect in the IoTHubMQTTClient in the event of an unexpected disconnection"
    )
    async def test_generator_raise_unexpected_disconnect(self, mocker, session):
        # Mock IoTHubMQTTClient direct method request generator to not yield anything yet
        mock_dm_gen = mocker.AsyncMock()
        mock_dm_gen.__anext__ = custom_mock.HangingAsyncMock()
        # Set it to be returned by PropertyMock
        dm_gen_property_mock = mocker.PropertyMock(return_value=mock_dm_gen)
        type(session._mqtt_client).incoming_direct_method_requests = dm_gen_property_mock

        async with session.direct_method_requests() as direct_method_requests:
            # Waiting for new item from generator (since mock is hanging / not returning)
            t = asyncio.create_task(direct_method_requests.__anext__())
            await asyncio.sleep(0.1)
            assert not t.done()

            # No unexpected disconnect yet
            assert not session._wait_for_disconnect_task.done()
            assert session._mqtt_client.wait_for_disconnect.call_count == 1
            assert session._mqtt_client.wait_for_disconnect.is_hanging()

            # Trigger unexpected disconnect
            cause = exc.MQTTConnectionDroppedError(rc=7)
            session._mqtt_client.wait_for_disconnect.return_value = cause
            session._mqtt_client.wait_for_disconnect.stop_hanging()
            await asyncio.sleep(0.1)

            # Generator raised the error that caused disconnect
            assert t.done()
            assert t.exception() is cause

    @pytest.mark.it(
        "Yields an AsyncGenerator that will raise a CancelledError if the event of an expected disconnection"
    )
    async def test_generator_raise_expected_disconnect(self, mocker, session):
        # Mock IoTHubMQTTClient direct method request generator to not yield anything yet
        mock_dm_gen = mocker.AsyncMock()
        mock_dm_gen.__anext__ = custom_mock.HangingAsyncMock()
        # Set it to be returned by PropertyMock
        dm_gen_property_mock = mocker.PropertyMock(return_value=mock_dm_gen)
        type(session._mqtt_client).incoming_direct_method_requests = dm_gen_property_mock

        async with session.direct_method_requests() as direct_method_requests:
            # Waiting for new item from generator (since mock is hanging / not returning)
            t = asyncio.create_task(direct_method_requests.__anext__())
            await asyncio.sleep(0.1)
            assert not t.done()

            # No disconnect yet
            assert not session._wait_for_disconnect_task.done()
            assert session._mqtt_client.wait_for_disconnect.call_count == 1
            assert session._mqtt_client.wait_for_disconnect.is_hanging()

            # Trigger expected disconnect
            session._mqtt_client.wait_for_disconnect.return_value = None
            session._mqtt_client.wait_for_disconnect.stop_hanging()
            await asyncio.sleep(0.1)

            # Generator raised CancelledError
            assert t.done()
            assert t.cancelled()

    @pytest.mark.it(
        "Raises SessionError without enabling direct method request receive on the IoTHubMQTTClient if it is not connected"
    )
    async def test_not_connected(self, mocker, session):
        conn_property_mock = mocker.PropertyMock(return_value=False)
        type(session._mqtt_client).connected = conn_property_mock

        with pytest.raises(exc.SessionError):
            async with session.direct_method_requests():
                pass
        assert session._mqtt_client.enable_direct_method_request_receive.call_count == 0

    @pytest.mark.it(
        "Allows any errors raised while attempting to enable direct method request receive to propagate"
    )
    @pytest.mark.parametrize(
        "exception",
        [
            pytest.param(exc.MQTTError(rc=4), id="MQTTError"),
            pytest.param(lazy_fixture("arbitrary_exception"), id="Unexpected Exception"),
        ],
    )
    async def test_enable_raises(self, session, exception):
        session._mqtt_client.enable_direct_method_request_receive.side_effect = exception

        with pytest.raises(type(exception)) as e_info:
            async with session.direct_method_requests():
                pass
        assert e_info.value is exception
        assert session._mqtt_client.enable_direct_method_request_receive.call_count == 1

    @pytest.mark.it(
        "Suppresses any MQTTErrors raised while attempting to disable direct method request receive"
    )
    async def test_disable_raises_mqtt_error(self, session):
        session._mqtt_client.disable_direct_method_request_receive.side_effect = exc.MQTTError(rc=4)

        async with session.direct_method_requests():
            pass
        assert session._mqtt_client.disable_direct_method_request_receive.call_count == 1
        # No error raised -> success

    @pytest.mark.it(
        "Allows any unexpected errors raised while attempting to disable direct method request receive to propagate"
    )
    async def test_disable_raises_unexpected(self, session, arbitrary_exception):
        session._mqtt_client.disable_direct_method_request_receive.side_effect = arbitrary_exception

        with pytest.raises(type(arbitrary_exception)) as e_info:
            async with session.direct_method_requests():
                pass
        assert e_info.value is arbitrary_exception
        assert session._mqtt_client.disable_direct_method_request_receive.call_count == 1


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

    @pytest.mark.it(
        "Does not attempt to disable twin patch receive upon exit if IoTHubMQTTClient is disconnected"
    )
    @pytest.mark.parametrize("graceful_exit", graceful_exit_params)
    async def test_context_manager_exit_while_disconnected(
        self, session, arbitrary_exception, graceful_exit
    ):
        assert session._mqtt_client.enable_twin_patch_receive.await_count == 0
        assert session._mqtt_client.disable_twin_patch_receive.await_count == 0

        try:
            async with session.desired_property_updates():
                assert session._mqtt_client.enable_twin_patch_receive.await_count == 1
                assert session._mqtt_client.disable_twin_patch_receive.await_count == 0
                session._mqtt_client.connected = False
                if not graceful_exit:
                    raise arbitrary_exception
        except type(arbitrary_exception):
            pass

        assert session._mqtt_client.enable_twin_patch_receive.await_count == 1
        assert session._mqtt_client.disable_twin_patch_receive.await_count == 0

    @pytest.mark.it(
        "Yields an AsyncGenerator that yields the desired property patches yielded by the IoTHubMQTTClient's incoming twin patch generator"
    )
    async def test_generator_yield(self, mocker, session):
        # Mock IoTHubMQTTClient twin patch generator to yield twin patches
        yielded_twin_patches = [{"1": 1}, {"2": 2}, {"3": 3}]
        mock_twin_patch_gen = mocker.AsyncMock()
        mock_twin_patch_gen.__anext__.side_effect = yielded_twin_patches
        # Set it to be returned by PropertyMock
        twin_patch_property_mock = mocker.PropertyMock(return_value=mock_twin_patch_gen)
        type(session._mqtt_client).incoming_twin_patches = twin_patch_property_mock

        assert not session._wait_for_disconnect_task.done()
        async with session.desired_property_updates() as desired_property_updates:
            # Is a generator
            assert isinstance(desired_property_updates, typing.AsyncGenerator)
            # Yields values from the IoTHubMQTTClient C2D generator
            assert mock_twin_patch_gen.__anext__.await_count == 0
            val = await desired_property_updates.__anext__()
            assert val is yielded_twin_patches[0]
            assert mock_twin_patch_gen.__anext__.await_count == 1
            val = await desired_property_updates.__anext__()
            assert val is yielded_twin_patches[1]
            assert mock_twin_patch_gen.__anext__.await_count == 2
            val = await desired_property_updates.__anext__()
            assert val is yielded_twin_patches[2]
            assert mock_twin_patch_gen.__anext__.await_count == 3

    @pytest.mark.it(
        "Yields an AsyncGenerator that will raise the MQTTConnectionDroppedError that caused an unexpected disconnect in the IoTHubMQTTClient in the event of an unexpected disconnection"
    )
    async def test_generator_raise_unexpected_disconnect(self, mocker, session):
        # Mock IoTHubMQTTClient twin patch generator to not yield anything yet
        mock_twin_patch_gen = mocker.AsyncMock()
        mock_twin_patch_gen.__anext__ = custom_mock.HangingAsyncMock()
        # Set it to be returned by PropertyMock
        twin_patch_property_mock = mocker.PropertyMock(return_value=mock_twin_patch_gen)
        type(session._mqtt_client).incoming_twin_patches = twin_patch_property_mock

        async with session.desired_property_updates() as desired_property_updates:
            # Waiting for new item from generator (since mock is hanging / not returning)
            t = asyncio.create_task(desired_property_updates.__anext__())
            await asyncio.sleep(0.1)
            assert not t.done()

            # No unexpected disconnect yet
            assert not session._wait_for_disconnect_task.done()
            assert session._mqtt_client.wait_for_disconnect.call_count == 1
            assert session._mqtt_client.wait_for_disconnect.is_hanging()

            # Trigger unexpected disconnect
            cause = exc.MQTTConnectionDroppedError(rc=7)
            session._mqtt_client.wait_for_disconnect.return_value = cause
            session._mqtt_client.wait_for_disconnect.stop_hanging()
            await asyncio.sleep(0.1)

            # Generator raised the error that caused disconnect
            assert t.done()
            assert t.exception() is cause

    @pytest.mark.it(
        "Yields an AsyncGenerator that will raise a CancelledError if the event of an expected disconnection"
    )
    async def test_generator_raise_expected_disconnect(self, mocker, session):
        # Mock IoTHubMQTTClient twin patch generator to not yield anything yet
        mock_twin_patch_gen = mocker.AsyncMock()
        mock_twin_patch_gen.__anext__ = custom_mock.HangingAsyncMock()
        # Set it to be returned by PropertyMock
        twin_patch_property_mock = mocker.PropertyMock(return_value=mock_twin_patch_gen)
        type(session._mqtt_client).incoming_twin_patches = twin_patch_property_mock

        async with session.desired_property_updates() as desired_property_updates:
            # Waiting for new item from generator (since mock is hanging / not returning)
            t = asyncio.create_task(desired_property_updates.__anext__())
            await asyncio.sleep(0.1)
            assert not t.done()

            # No unexpected disconnect yet
            assert not session._wait_for_disconnect_task.done()
            assert session._mqtt_client.wait_for_disconnect.call_count == 1
            assert session._mqtt_client.wait_for_disconnect.is_hanging()

            # Trigger expected disconnect
            session._mqtt_client.wait_for_disconnect.return_value = None
            session._mqtt_client.wait_for_disconnect.stop_hanging()
            await asyncio.sleep(0.1)

            # Generator raised CancelledError
            assert t.done()
            assert t.cancelled()

    @pytest.mark.it(
        "Raises SessionError without enabling twin patch receive on the IoTHubMQTTClient if it is not connected"
    )
    async def test_not_connected(self, mocker, session):
        conn_property_mock = mocker.PropertyMock(return_value=False)
        type(session._mqtt_client).connected = conn_property_mock

        with pytest.raises(exc.SessionError):
            async with session.desired_property_updates():
                pass
        assert session._mqtt_client.enable_twin_patch_receive.call_count == 0

    @pytest.mark.it(
        "Allows any errors raised while attempting to enable twin patch receive to propagate"
    )
    @pytest.mark.parametrize(
        "exception",
        [
            pytest.param(exc.MQTTError(rc=4), id="MQTTError"),
            pytest.param(lazy_fixture("arbitrary_exception"), id="Unexpected Exception"),
        ],
    )
    async def test_enable_raises(self, session, exception):
        session._mqtt_client.enable_twin_patch_receive.side_effect = exception

        with pytest.raises(type(exception)) as e_info:
            async with session.desired_property_updates():
                pass
        assert e_info.value is exception
        assert session._mqtt_client.enable_twin_patch_receive.call_count == 1

    @pytest.mark.it(
        "Suppresses any MQTTErrors raised while attempting to disable twin patch receive"
    )
    async def test_disable_raises_mqtt_error(self, session):
        session._mqtt_client.disable_twin_patch_receive.side_effect = exc.MQTTError(rc=4)

        async with session.desired_property_updates():
            pass
        assert session._mqtt_client.disable_twin_patch_receive.call_count == 1
        # No error raised -> success

    @pytest.mark.it(
        "Allows any unexpected errors raised while attempting to disable twin patch receive to propagate"
    )
    async def test_disable_raises_unexpected(self, session, arbitrary_exception):
        session._mqtt_client.disable_twin_patch_receive.side_effect = arbitrary_exception

        with pytest.raises(type(arbitrary_exception)) as e_info:
            async with session.desired_property_updates():
                pass
        assert e_info.value is arbitrary_exception
        assert session._mqtt_client.disable_twin_patch_receive.call_count == 1
