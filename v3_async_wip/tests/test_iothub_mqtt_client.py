# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import abc
import asyncio
import json
import pytest
import ssl
import sys
import time
import typing
import urllib
from pytest_lazyfixture import lazy_fixture
from dev_utils import custom_mock
from v3_async_wip.iothub_mqtt_client import (
    IoTHubMQTTClient,
    DEFAULT_RECONNECT_INTERVAL,
)
from v3_async_wip.iot_exceptions import IoTHubClientError, IoTHubError
from v3_async_wip import config, constant, models, user_agent
from v3_async_wip import mqtt_client as mqtt
from v3_async_wip import request_response as rr
from v3_async_wip import mqtt_topic_iothub as mqtt_topic
from v3_async_wip import sastoken as st


FAKE_DEVICE_ID = "fake_device_id"
FAKE_MODULE_ID = "fake_module_id"
FAKE_DEVICE_CLIENT_ID = "fake_device_id"
FAKE_MODULE_CLIENT_ID = "fake_device_id/fake_module_id"
FAKE_HOSTNAME = "fake.hostname"
FAKE_SIGNATURE = "ajsc8nLKacIjGsYyB4iYDFCZaRMmmDrUuY5lncYDYPI="
FAKE_EXPIRY = str(int(time.time()) + 3600)
FAKE_URI = "fake/resource/location"
FAKE_INPUT_NAME = "fake_input"


# Parametrizations
# TODO: expand this when we know more about what exceptions get raised from MQTTClient
mqtt_connect_exceptions = [
    pytest.param(mqtt.MQTTConnectionFailedError(), id="MQTTConnectionFailedError"),
    pytest.param(lazy_fixture("arbitrary_exception"), id="Unexpected Exception"),
]
mqtt_disconnect_exceptions = [
    pytest.param(lazy_fixture("arbitrary_exception"), id="Unexpected Exception")
]
mqtt_publish_exceptions = [
    pytest.param(mqtt.MQTTError(rc=5), id="MQTTError"),
    pytest.param(ValueError(), id="ValueError"),
    pytest.param(TypeError(), id="TypeError"),
    pytest.param(lazy_fixture("arbitrary_exception"), id="Unexpected Exception"),
]
mqtt_subscribe_exceptions = [
    # NOTE: CancelledError is here because network failure can cancel a subscribe
    # without explicit invocation of cancel on the subscribe
    pytest.param(mqtt.MQTTError(rc=5), id="MQTTError"),
    pytest.param(asyncio.CancelledError(), id="CancelledError (Not initiated)"),
    pytest.param(lazy_fixture("arbitrary_exception"), id="Unexpected Exception"),
]
mqtt_unsubscribe_exceptions = [
    # NOTE: CancelledError is here because network failure can cancel an unsubscribe
    # without explicit invocation of cancel on the unsubscribe
    pytest.param(mqtt.MQTTError(rc=5), id="MQTTError"),
    pytest.param(asyncio.CancelledError(), id="CancelledError (Not initiated)"),
    pytest.param(lazy_fixture("arbitrary_exception"), id="Unexpected Exception"),
]


# Fixtures


@pytest.fixture
def sastoken():
    sastoken_str = "SharedAccessSignature sr={resource}&sig={signature}&se={expiry}".format(
        resource=FAKE_URI, signature=FAKE_SIGNATURE, expiry=FAKE_EXPIRY
    )
    return st.SasToken(sastoken_str)


@pytest.fixture
def mock_sastoken_provider(mocker, sastoken):
    provider = mocker.MagicMock(spec=st.SasTokenProvider)
    provider.get_current_sastoken.return_value = sastoken
    # Use a HangingAsyncMock so that it isn't constantly returning
    provider.wait_for_new_sastoken = custom_mock.HangingAsyncMock()
    provider.wait_for_new_sastoken.return_value = sastoken
    # NOTE: Technically, this mock just always returns the same SasToken,
    # even after an "update", but for the purposes of testing at this level,
    # it doesn't matter
    return provider


@pytest.fixture
def client_config():
    """Defaults to Device Configuration. Required values only.
    Customize in test if you need specific options (incl. Module)"""

    client_config = config.IoTHubClientConfig(
        device_id=FAKE_DEVICE_ID, hostname=FAKE_HOSTNAME, ssl_context=ssl.SSLContext()
    )
    return client_config


@pytest.fixture
async def client(mocker, client_config):
    client = IoTHubMQTTClient(client_config)
    # Mock just the network operations from the MQTTClient, not the whole thing.
    # This makes using the generators easier
    client._mqtt_client.connect = mocker.AsyncMock()
    client._mqtt_client.disconnect = mocker.AsyncMock()
    client._mqtt_client.subscribe = mocker.AsyncMock()
    client._mqtt_client.unsubscribe = mocker.AsyncMock()
    client._mqtt_client.publish = mocker.AsyncMock()
    # Also mock the set credentials method since we test that
    client._mqtt_client.set_credentials = mocker.MagicMock()

    yield client
    await client.shutdown()


@pytest.mark.describe("IoTHubMQTTClient -- Instantiation")
class TestIoTHubMQTTClientInstantiation:
    # NOTE: As the instantiation is the unit under test here, we shouldn't use the client fixture.
    # This means that you must do graceful exit by shutting down the client at the end of all tests
    # and you may need to do a manual mock of the underlying MQTTClient where appropriate.

    @pytest.mark.it(
        "Stores the `device_id` and `module_id` values from the IoTHubClientConfig as attributes"
    )
    @pytest.mark.parametrize(
        "device_id, module_id",
        [
            pytest.param(FAKE_DEVICE_ID, None, id="Device Configuration"),
            pytest.param(FAKE_DEVICE_ID, FAKE_MODULE_ID, id="Module Configuration"),
        ],
    )
    async def test_simple_ids(self, client_config, device_id, module_id):
        client_config.device_id = device_id
        client_config.module_id = module_id

        client = IoTHubMQTTClient(client_config)
        assert client._device_id == client_config.device_id
        assert client._module_id == client_config.module_id
        await client.shutdown()

    @pytest.mark.it(
        "Derives the `client_id` from the `device_id` and `module_id` and stores it as an attribute"
    )
    @pytest.mark.parametrize(
        "device_id, module_id, expected_client_id",
        [
            pytest.param(FAKE_DEVICE_ID, None, FAKE_DEVICE_CLIENT_ID, id="Device Configuration"),
            pytest.param(
                FAKE_DEVICE_ID, FAKE_MODULE_ID, FAKE_MODULE_CLIENT_ID, id="Module Configuration"
            ),
        ],
    )
    async def test_client_id(self, client_config, device_id, module_id, expected_client_id):
        client_config.device_id = device_id
        client_config.module_id = module_id

        client = IoTHubMQTTClient(client_config)
        assert client._client_id == expected_client_id
        await client.shutdown()

    @pytest.mark.it("Derives the `username` and stores the result as an attribute")
    @pytest.mark.parametrize(
        "device_id, module_id, client_id",
        [
            pytest.param(FAKE_DEVICE_ID, None, FAKE_DEVICE_CLIENT_ID, id="Device Configuration"),
            pytest.param(
                FAKE_DEVICE_ID, FAKE_MODULE_ID, FAKE_MODULE_CLIENT_ID, id="Module Configuration"
            ),
        ],
    )
    @pytest.mark.parametrize(
        "product_info",
        [
            pytest.param("", id="No Product Info"),
            pytest.param("my-product-info", id="Custom Product Info"),
            pytest.param("my$product$info", id="Custom Product Info (URL encoding required)"),
            pytest.param(
                constant.DIGITAL_TWIN_PREFIX + ":com:example:ClimateSensor;1",
                id="Digital Twin Product Info",
            ),
            pytest.param(
                constant.DIGITAL_TWIN_PREFIX + ":com:example:$Climate$ensor;1",
                id="Digital Twin Product Info (URL encoding required)",
            ),
        ],
    )
    async def test_username(
        self,
        client_config,
        device_id,
        module_id,
        client_id,
        product_info,
    ):
        client_config.device_id = device_id
        client_config.module_id = module_id
        client_config.product_info = product_info

        ua = user_agent.get_iothub_user_agent()
        url_encoded_user_agent = urllib.parse.quote(ua, safe="")
        # NOTE: This assertion shows the URL encoding was meaningful
        assert user_agent != url_encoded_user_agent

        url_encoded_product_info = urllib.parse.quote(product_info, safe="")
        # NOTE: We can't really make the same assertion here, because this isn't always meaningful

        # Determine expected username based on config
        if product_info.startswith(constant.DIGITAL_TWIN_PREFIX):
            expected_username = "{hostname}/{client_id}/?api-version={api_version}&DeviceClientType={user_agent}&{digital_twin_prefix}={custom_product_info}".format(
                hostname=client_config.hostname,
                client_id=client_id,
                api_version=constant.IOTHUB_API_VERSION,
                user_agent=url_encoded_user_agent,
                digital_twin_prefix=constant.DIGITAL_TWIN_QUERY_HEADER,
                custom_product_info=url_encoded_product_info,
            )
        else:
            expected_username = "{hostname}/{client_id}/?api-version={api_version}&DeviceClientType={user_agent}{custom_product_info}".format(
                hostname=client_config.hostname,
                client_id=client_id,
                api_version=constant.IOTHUB_API_VERSION,
                user_agent=url_encoded_user_agent,
                custom_product_info=url_encoded_product_info,
            )

        client = IoTHubMQTTClient(client_config)
        # The expected username was derived
        assert client._username == expected_username
        await client.shutdown()

    @pytest.mark.it("Stores the `sastoken_provider` from the IoTHubClientConfig as an attribute")
    @pytest.mark.parametrize(
        "sastoken_provider",
        [
            pytest.param(lazy_fixture("mock_sastoken_provider"), id="SasTokenProvider present"),
            pytest.param(None, id="No SasTokenProvider present"),
        ],
    )
    @pytest.mark.parametrize(
        "device_id, module_id",
        [
            pytest.param(FAKE_DEVICE_ID, None, id="Device Configuration"),
            pytest.param(FAKE_DEVICE_ID, FAKE_MODULE_ID, id="Module Configuration"),
        ],
    )
    async def test_sastoken_provider(self, client_config, sastoken_provider, device_id, module_id):
        client_config.device_id = device_id
        client_config.module_id = module_id
        client_config.sastoken_provider = sastoken_provider

        client = IoTHubMQTTClient(client_config)
        assert client._sastoken_provider is sastoken_provider
        await client.shutdown()

    @pytest.mark.it(
        "Creates an MQTTClient instance based on the configuration of IoTHubClientConfig and stores it as an attribute"
    )
    @pytest.mark.parametrize(
        "device_id, module_id, expected_client_id",
        [
            pytest.param(FAKE_DEVICE_ID, None, FAKE_DEVICE_CLIENT_ID, id="Device Configuration"),
            pytest.param(
                FAKE_DEVICE_ID, FAKE_MODULE_ID, FAKE_MODULE_CLIENT_ID, id="Module Configuration"
            ),
        ],
    )
    @pytest.mark.parametrize(
        "websockets, expected_transport, expected_port, expected_ws_path",
        [
            pytest.param(True, "websockets", 443, "/$iothub/websocket", id="WebSockets"),
            pytest.param(False, "tcp", 8883, None, id="TCP"),
        ],
    )
    async def test_mqtt_client(
        self,
        mocker,
        client_config,
        device_id,
        module_id,
        expected_client_id,
        websockets,
        expected_transport,
        expected_port,
        expected_ws_path,
    ):
        # Configure the client_config based on params
        client_config.device_id = device_id
        client_config.module_id = module_id
        client_config.websockets = websockets

        # Patch the MQTTClient constructor
        mock_constructor = mocker.patch.object(mqtt, "MQTTClient", spec=mqtt.MQTTClient)
        assert mock_constructor.call_count == 0

        # Create the client under test
        client = IoTHubMQTTClient(client_config)

        # Assert that the MQTTClient was constructed as expected
        assert mock_constructor.call_count == 1
        assert mock_constructor.call_args == mocker.call(
            client_id=expected_client_id,
            hostname=client_config.hostname,
            port=expected_port,
            transport=expected_transport,
            keep_alive=client_config.keep_alive,
            auto_reconnect=client_config.auto_reconnect,
            reconnect_interval=DEFAULT_RECONNECT_INTERVAL,
            ssl_context=client_config.ssl_context,
            websockets_path=expected_ws_path,
            proxy_options=client_config.proxy_options,
        )

        # Graceful exit
        await client.shutdown()

    @pytest.mark.it(
        "Uses the derived `username` as the username, with no password as the credentials for the newly created MQTTClient instance when not using SAS authentication"
    )
    @pytest.mark.parametrize(
        "device_id, module_id",
        [
            pytest.param(FAKE_DEVICE_ID, None, id="Device Configuration"),
            pytest.param(FAKE_DEVICE_ID, FAKE_MODULE_ID, id="Module Configuration"),
        ],
    )
    async def test_mqtt_client_credentials_no_sas(
        self, mocker, client_config, device_id, module_id
    ):
        client_config.device_id = device_id
        client_config.module_id = module_id
        assert client_config.sastoken_provider is None

        mocker.patch.object(mqtt, "MQTTClient", spec=mqtt.MQTTClient)
        client = IoTHubMQTTClient(client_config)
        expected_username = client._username
        expected_password = None
        assert client._mqtt_client.set_credentials.call_count == 1
        assert client._mqtt_client.set_credentials.call_args(expected_username, expected_password)

        await client.shutdown()

    @pytest.mark.it(
        "Uses the derived `username` as the username and the string-converted current SasToken from the SasTokenProvider as the password when setting credentials for the newly created MQTTClient instance when using SAS authentication"
    )
    @pytest.mark.parametrize(
        "device_id, module_id",
        [
            pytest.param(FAKE_DEVICE_ID, None, id="Device Configuration"),
            pytest.param(FAKE_DEVICE_ID, FAKE_MODULE_ID, id="Module Configuration"),
        ],
    )
    async def test_mqtt_client_credentials_with_sas(
        self, mocker, client_config, device_id, module_id, mock_sastoken_provider
    ):
        client_config.device_id = device_id
        client_config.module_id = module_id
        client_config.sastoken_provider = mock_sastoken_provider

        fake_sastoken = mock_sastoken_provider.get_current_sastoken.return_value

        mocker.patch.object(mqtt, "MQTTClient", spec=mqtt.MQTTClient)
        client = IoTHubMQTTClient(client_config)
        expected_username = client._username
        expected_password = str(fake_sastoken)
        assert client._mqtt_client.set_credentials.call_count == 1
        assert client._mqtt_client.set_credentials.call_args(expected_username, expected_password)

        await client.shutdown()

    @pytest.mark.it("Adds incoming message filter on the MQTTClient for C2D messages")
    @pytest.mark.parametrize(
        "device_id, module_id",
        [
            pytest.param(FAKE_DEVICE_ID, None, id="Device Configuration"),
            pytest.param(FAKE_DEVICE_ID, FAKE_MODULE_ID, id="Module Configuration"),
        ],
    )
    async def test_c2d_filter(self, mocker, client_config, device_id, module_id):
        client_config.device_id = device_id
        client_config.module_id = module_id
        expected_topic = mqtt_topic.get_c2d_topic_for_subscribe(device_id)

        mocker.patch.object(mqtt, "MQTTClient", spec=mqtt.MQTTClient)
        client = IoTHubMQTTClient(client_config)

        # NOTE: Multiple filters are added, but not all are covered in this test
        assert (
            mocker.call(expected_topic)
            in client._mqtt_client.add_incoming_message_filter.call_args_list
        )

        await client.shutdown()

    @pytest.mark.it("Adds incoming message filter on the MQTTClient for direct method requests")
    @pytest.mark.parametrize(
        "device_id, module_id",
        [
            pytest.param(FAKE_DEVICE_ID, None, id="Device Configuration"),
            pytest.param(FAKE_DEVICE_ID, FAKE_MODULE_ID, id="Module Configuration"),
        ],
    )
    async def test_direct_method_request_filter(self, mocker, client_config, device_id, module_id):
        client_config.device_id = device_id
        client_config.module_id = module_id
        expected_topic = mqtt_topic.get_direct_method_request_topic_for_subscribe()

        mocker.patch.object(mqtt, "MQTTClient", spec=mqtt.MQTTClient)
        client = IoTHubMQTTClient(client_config)

        # NOTE: Multiple filters are added, but not all are covered in this test
        assert (
            mocker.call(expected_topic)
            in client._mqtt_client.add_incoming_message_filter.call_args_list
        )

        await client.shutdown()

    @pytest.mark.it("Adds incoming message filter on the MQTTClient for twin patches")
    @pytest.mark.parametrize(
        "device_id, module_id",
        [
            pytest.param(FAKE_DEVICE_ID, None, id="Device Configuration"),
            pytest.param(FAKE_DEVICE_ID, FAKE_MODULE_ID, id="Module Configuration"),
        ],
    )
    async def test_twin_patch_filter(self, mocker, client_config, device_id, module_id):
        client_config.device_id = device_id
        client_config.module_id = module_id
        expected_topic = mqtt_topic.get_twin_patch_topic_for_subscribe()

        mocker.patch.object(mqtt, "MQTTClient", spec=mqtt.MQTTClient)
        client = IoTHubMQTTClient(client_config)

        # NOTE: Multiple filters are added, but not all are covered in this test
        assert (
            mocker.call(expected_topic)
            in client._mqtt_client.add_incoming_message_filter.call_args_list
        )

        await client.shutdown()

    @pytest.mark.it("Adds incoming message filter on the MQTTClient for twin responses")
    @pytest.mark.parametrize(
        "device_id, module_id",
        [
            pytest.param(FAKE_DEVICE_ID, None, id="Device Configuration"),
            pytest.param(FAKE_DEVICE_ID, FAKE_MODULE_ID, id="Module Configuration"),
        ],
    )
    async def test_twin_response_filter(self, mocker, client_config, device_id, module_id):
        client_config.device_id = device_id
        client_config.module_id = module_id
        expected_topic = mqtt_topic.get_twin_response_topic_for_subscribe()

        mocker.patch.object(mqtt, "MQTTClient", spec=mqtt.MQTTClient)
        client = IoTHubMQTTClient(client_config)

        # NOTE: Multiple filters are added, but not all are covered in this test
        assert (
            mocker.call(expected_topic)
            in client._mqtt_client.add_incoming_message_filter.call_args_list
        )

        await client.shutdown()

    @pytest.mark.it(
        "Adds incoming message filter on the MQTTClient for input messages, if using a Module Configuration"
    )
    async def test_input_message_filter_module(self, mocker, client_config):
        client_config.device_id = FAKE_DEVICE_ID
        client_config.module_id = FAKE_MODULE_ID
        expected_topic = mqtt_topic.get_input_topic_for_subscribe(FAKE_DEVICE_ID, FAKE_MODULE_ID)

        mocker.patch.object(mqtt, "MQTTClient", spec=mqtt.MQTTClient)
        client = IoTHubMQTTClient(client_config)

        # NOTE: Multiple filters are added, but not all are covered in this test
        assert (
            mocker.call(expected_topic)
            in client._mqtt_client.add_incoming_message_filter.call_args_list
        )

        await client.shutdown()

    @pytest.mark.it(
        "Does not add incoming message filter on the MQTTClient for input messages, if using a Device Configuration"
    )
    async def test_input_message_filter_device(self, mocker, client_config):
        client_config.device_id = FAKE_DEVICE_ID

        mocker.patch.object(mqtt, "MQTTClient", spec=mqtt.MQTTClient)
        client = IoTHubMQTTClient(client_config)

        # NOTE: It's kind of weird to try and show a method wasn't called with an argument, when
        # what that argument would even be can't be created without a module ID in the first place.
        # What we do here is check every topic that a filter is added for to ensure none of them
        # contain the word "input", which an input message topic would uniquely have
        for call in client._mqtt_client.add_incoming_message_filter.call_args_list:
            topic = call[0][0]
            assert "inputs" not in topic

        await client.shutdown()

    # NOTE: For testing the functionality of this generator, see the corresponding test suite (TestIoTHubMQTTClientIncomingC2DMessages)
    @pytest.mark.it("Creates and stores an incoming C2D message generator as an attribute")
    @pytest.mark.parametrize(
        "device_id, module_id",
        [
            pytest.param(FAKE_DEVICE_ID, None, id="Device Configuration"),
            pytest.param(FAKE_DEVICE_ID, FAKE_MODULE_ID, id="Module Configuration"),
        ],
    )
    async def test_c2d_generator(self, client_config, device_id, module_id):
        client_config.device_id = device_id
        client_config.module_id = module_id
        client = IoTHubMQTTClient(client_config)
        assert isinstance(client.incoming_c2d_messages, typing.AsyncGenerator)

        await client.shutdown()

    # NOTE: For testing the functionality of this generator, see the corresponding test suite (TestIoTHubMQTTClientIncomingDirectDirectMethodRequests)
    @pytest.mark.it(
        "Creates and stores an incoming direct method request generator as an attribute"
    )
    @pytest.mark.parametrize(
        "device_id, module_id",
        [
            pytest.param(FAKE_DEVICE_ID, None, id="Device Configuration"),
            pytest.param(FAKE_DEVICE_ID, FAKE_MODULE_ID, id="Module Configuration"),
        ],
    )
    async def test_direct_method_request_generator(self, client_config, device_id, module_id):
        client_config.device_id = device_id
        client_config.module_id = module_id
        client = IoTHubMQTTClient(client_config)
        assert isinstance(client.incoming_direct_method_requests, typing.AsyncGenerator)

        await client.shutdown()

    # NOTE: For testing the functionality of this generator, see the corresponding test suite (TestIoTHubMQTTClientIncomingTwinPatches)
    @pytest.mark.it("Creates and stores an incoming twin patch generator as an attribute")
    @pytest.mark.parametrize(
        "device_id, module_id",
        [
            pytest.param(FAKE_DEVICE_ID, None, id="Device Configuration"),
            pytest.param(FAKE_DEVICE_ID, FAKE_MODULE_ID, id="Module Configuration"),
        ],
    )
    async def test_twin_patch_generator(self, client_config, device_id, module_id):
        client_config.device_id = device_id
        client_config.module_id = module_id
        client = IoTHubMQTTClient(client_config)
        assert isinstance(client.incoming_twin_patches, typing.AsyncGenerator)

        await client.shutdown()

    # NOTE: For testing the functionality of this generator, see the corresponding test suite (TestIoTHubMQTTClientIncomingInputMessages)
    @pytest.mark.it(
        "Creates and stores an incoming input message generator as an attribute, if using a Module Configuration"
    )
    async def test_input_message_generator_module(self, client_config):
        client_config.device_id = FAKE_DEVICE_ID
        client_config.module_id = FAKE_MODULE_ID
        client = IoTHubMQTTClient(client_config)
        assert isinstance(client.incoming_input_messages, typing.AsyncGenerator)

        await client.shutdown()

    @pytest.mark.it(
        "Does not create an incoming input message generator, if using a Device Configuration"
    )
    async def test_input_message_generator_device(self, client_config):
        client_config.device_id = FAKE_DEVICE_ID
        client_config.module_id = None
        client = IoTHubMQTTClient(client_config)
        assert client.incoming_input_messages is None

        await client.shutdown()

    @pytest.mark.it("Creates an empty RequestLedger")
    @pytest.mark.parametrize(
        "device_id, module_id",
        [
            pytest.param(FAKE_DEVICE_ID, None, id="Device Configuration"),
            pytest.param(FAKE_DEVICE_ID, FAKE_MODULE_ID, id="Module Configuration"),
        ],
    )
    async def test_request_ledger(self, client_config, device_id, module_id):
        client_config.device_id = device_id
        client_config.module_id = module_id
        client = IoTHubMQTTClient(client_config)
        assert isinstance(client._request_ledger, rr.RequestLedger)
        assert len(client._request_ledger) == 0
        await client.shutdown()

    @pytest.mark.it("Sets the twin_responses_enabled flag to False")
    @pytest.mark.parametrize(
        "device_id, module_id",
        [
            pytest.param(FAKE_DEVICE_ID, None, id="Device Configuration"),
            pytest.param(FAKE_DEVICE_ID, FAKE_MODULE_ID, id="Module Configuration"),
        ],
    )
    async def test_twin_responses_enabled(self, client_config, device_id, module_id):
        client_config.device_id = device_id
        client_config.module_id = module_id
        client = IoTHubMQTTClient(client_config)
        assert client._twin_responses_enabled is False

        await client.shutdown()

    # NOTE: For testing the functionality of this task, see the corresponding test suite (TestIoTHubMQTTClientIncomingTwinResponse)
    @pytest.mark.it(
        "Begins running the ._process_twin_responses() coroutine method as a background task, storing it as an attribute"
    )
    @pytest.mark.parametrize(
        "device_id, module_id",
        [
            pytest.param(FAKE_DEVICE_ID, None, id="Device Configuration"),
            pytest.param(FAKE_DEVICE_ID, FAKE_MODULE_ID, id="Module Configuration"),
        ],
    )
    async def test_process_twin_responses_bg_task(self, client_config, device_id, module_id):
        client_config.device_id = device_id
        client_config.module_id = module_id
        client = IoTHubMQTTClient(client_config)

        assert isinstance(client._process_twin_responses_bg_task, asyncio.Task)
        assert not client._process_twin_responses_bg_task.done()
        if sys.version_info > (3, 8):
            # NOTE: There isn't a way to validate the contents of a task until 3.8
            # as far as I can tell.
            task_coro = client._process_twin_responses_bg_task.get_coro()
            assert task_coro.__qualname__ == "IoTHubMQTTClient._process_twin_responses"

        await client.shutdown()

    # NOTE: For testing the functionality of this task, see the corresponding test suite (???)
    # TODO: add this test suite
    @pytest.mark.it(
        "Begins running the ._keep_credentials_fresh() coroutine method as a background task, storing it as an attribute, if using SAS authentication"
    )
    @pytest.mark.parametrize(
        "device_id, module_id",
        [
            pytest.param(FAKE_DEVICE_ID, None, id="Device Configuration"),
            pytest.param(FAKE_DEVICE_ID, FAKE_MODULE_ID, id="Module Configuration"),
        ],
    )
    async def test_keep_credentials_fresh_bg_task(
        self, client_config, device_id, module_id, mock_sastoken_provider
    ):
        client_config.device_id = device_id
        client_config.module_id = module_id
        client_config.sastoken_provider = mock_sastoken_provider
        client = IoTHubMQTTClient(client_config)

        assert isinstance(client._keep_credentials_fresh_bg_task, asyncio.Task)
        assert not client._keep_credentials_fresh_bg_task.done()
        if sys.version_info > (3, 8):
            # NOTE: There isn't a way to validate the contents of a task until 3.8
            # as far as I can tell.
            task_coro = client._keep_credentials_fresh_bg_task.get_coro()
            assert task_coro.__qualname__ == "IoTHubMQTTClient._keep_credentials_fresh"

        await client.shutdown()

    @pytest.mark.it(
        "Does not begin running the ._keep_credentials_fresh() coroutine method as a background task if not using SAS authentication"
    )
    @pytest.mark.parametrize(
        "device_id, module_id",
        [
            pytest.param(FAKE_DEVICE_ID, None, id="Device Configuration"),
            pytest.param(FAKE_DEVICE_ID, FAKE_MODULE_ID, id="Module Configuration"),
        ],
    )
    async def test_keep_credentials_fresh_bg_task_no_sas(self, client_config, device_id, module_id):
        client_config.device_id = device_id
        client_config.module_id = module_id
        assert client_config.sastoken_provider is None
        client = IoTHubMQTTClient(client_config)

        assert client._keep_credentials_fresh_bg_task is None

        await client.shutdown()


@pytest.mark.describe("IoTHubMQTTClient - .shutdown()")
class TestIoTHubMQTTClientShutdown:
    @pytest.fixture(autouse=True)
    def modify_client_config(self, client_config, mock_sastoken_provider):
        # NOTE: This has to be changed on the config, not the client,
        # because it affects client initialization
        client_config.sastoken_provider = mock_sastoken_provider

    @pytest.mark.it("Disconnects the MQTTClient")
    async def test_disconnect(self, mocker, client):
        # NOTE: rather than mocking the MQTTClient, we just mock the .disconnect() method of the
        # IoTHubMQTTClient instead, since it's been fully tested elsewhere, and we assume
        # correctness, lest we have to repeat all .disconnect() tests here.
        original_disconnect = client.disconnect
        client.disconnect = mocker.AsyncMock()
        try:
            assert client.disconnect.await_count == 0

            await client.shutdown()

            assert client.disconnect.await_count == 1
            assert client.disconnect.await_args == mocker.call()
        finally:
            client.disconnect = original_disconnect

    @pytest.mark.it("Cancels the 'process_twin_responses' background task")
    async def test_process_twin_responses_bg_task(self, client):
        assert isinstance(client._process_twin_responses_bg_task, asyncio.Task)
        assert not client._process_twin_responses_bg_task.done()

        await client.shutdown()

        assert client._process_twin_responses_bg_task.done()
        assert client._process_twin_responses_bg_task.cancelled()

    @pytest.mark.it("Cancels the 'keep_credentials_fresh' background task, if it exists")
    async def test_keep_credentials_fresh_bg_task_exists(self, client):
        assert isinstance(client._keep_credentials_fresh_bg_task, asyncio.Task)
        assert not client._keep_credentials_fresh_bg_task.done()

        await client.shutdown()

        assert client._keep_credentials_fresh_bg_task.done()
        assert client._keep_credentials_fresh_bg_task.cancelled()

    @pytest.mark.it("Handles the case where no 'keep_credentials_fresh' background task exists")
    async def test_keep_credentials_fresh_bg_task_no_exist(self, client, client_config):
        # NOTE: in this test we don't want to have the SAS bg task, so override the modified fixture
        client_config.sastoken_provider = None
        client = IoTHubMQTTClient(client_config)
        assert client._keep_credentials_fresh_bg_task is None
        await client.shutdown()
        # No AttributeError means success!

    @pytest.mark.it(
        "Allows any exception raised during MQTTClient disconnect to propagate, but only after cancelling background tasks"
    )
    @pytest.mark.parametrize("exception", mqtt_disconnect_exceptions)
    async def test_disconnect_raises(self, mocker, client, exception):
        # NOTE: rather than mocking the MQTTClient, we just mock the .disconnect() method of the
        # IoTHubMQTTClient instead, since it's been fully tested elsewhere, and we assume
        # correctness, lest we have to repeat all .disconnect() tests here.
        original_disconnect = client.disconnect
        client.disconnect = mocker.AsyncMock(side_effect=exception)
        try:
            assert not client._keep_credentials_fresh_bg_task.done()
            assert not client._process_twin_responses_bg_task.done()

            with pytest.raises(type(exception)) as e_info:
                await client.shutdown()
            assert e_info.value is exception

            # Background tasks were also cancelled despite the exception
            assert client._keep_credentials_fresh_bg_task.done()
            assert client._keep_credentials_fresh_bg_task.cancelled()
            assert client._process_twin_responses_bg_task.done()
            assert client._process_twin_responses_bg_task.cancelled()
        finally:
            # Unset the mock so that tests can clean up
            client.disconnect = original_disconnect

    @pytest.mark.it(
        "Can be cancelled while waiting for the MQTTClient disconnect to finish, but it won't stop background task cancellation"
    )
    async def test_cancel_disconnect(self, client):
        # NOTE: rather than mocking the MQTTClient, we just mock the .disconnect() method of the
        # IoTHubMQTTClient instead, since it's been fully tested elsewhere, and we assume
        # correctness, lest we have to repeat all .disconnect() tests here.
        original_disconnect = client.disconnect
        client.disconnect = custom_mock.HangingAsyncMock()
        try:
            t = asyncio.create_task(client.shutdown())

            # Hanging, waiting for disconnect to finish
            await client.disconnect.wait_for_hang()
            assert not t.done()

            # Cancel
            t.cancel()
            with pytest.raises(asyncio.CancelledError):
                await t
            # Due to cancellation, the tasks we want to assert are done may need a moment
            # to finish, since we aren't waiting on them to exit
            await asyncio.sleep(0.1)

            # And yet the background tasks still were cancelled anyway
            assert client._keep_credentials_fresh_bg_task.done()
            assert client._keep_credentials_fresh_bg_task.cancelled()
            assert client._process_twin_responses_bg_task.done()
            assert client._process_twin_responses_bg_task.cancelled()
        finally:
            # Unset the mock so that tests can clean up.
            client.disconnect = original_disconnect

    @pytest.mark.it(
        "Can be cancelled while waiting for the background tasks to finish cancellation, but it won't stop the background task cancellation"
    )
    async def test_cancel_gather(self, mocker, client):
        original_gather = asyncio.gather
        asyncio.gather = custom_mock.HangingAsyncMock()
        spy_twin_response_bg_task_cancel = mocker.spy(
            client._process_twin_responses_bg_task, "cancel"
        )
        spy_credentials_bg_task_cancel = mocker.spy(
            client._keep_credentials_fresh_bg_task, "cancel"
        )
        try:
            t = asyncio.create_task(client.shutdown())

            # Hanging waiting for gather to return (indicating tasks are all done cancellation)
            await asyncio.gather.wait_for_hang()
            assert not t.done()
            # Background tests may or may not have completed cancellation yet, hard to test accurately.
            # But their cancellation HAS been requested.
            assert spy_twin_response_bg_task_cancel.call_count == 1
            assert spy_credentials_bg_task_cancel.call_count == 1

            # Cancel
            t.cancel()
            with pytest.raises(asyncio.CancelledError):
                await t

            # Tasks will be cancelled very soon (if they aren't already)
            await asyncio.sleep(0.1)
            assert client._keep_credentials_fresh_bg_task.done()
            assert client._keep_credentials_fresh_bg_task.cancelled()
            assert client._process_twin_responses_bg_task.done()
            assert client._process_twin_responses_bg_task.cancelled()
        finally:
            # Unset the mock so that tests can clean up.
            asyncio.gather = original_gather


@pytest.mark.describe("IoTHubMQTTClient - .connect()")
class TestIoTHubMQTTClientConnect:
    @pytest.mark.it("Awaits a connect using the MQTTClient")
    async def test_mqtt_connect(self, mocker, client):
        assert client._mqtt_client.connect.await_count == 0

        await client.connect()

        assert client._mqtt_client.connect.await_count == 1
        assert client._mqtt_client.connect.await_args == mocker.call()

    @pytest.mark.it("Allows any exceptions raised during the MQTTClient connect to propagate")
    @pytest.mark.parametrize("exception", mqtt_connect_exceptions)
    async def test_mqtt_exception(self, client, exception):
        client._mqtt_client.connect.side_effect = exception

        with pytest.raises(type(exception)) as e_info:
            await client.connect()
        assert e_info.value is exception

    @pytest.mark.it("Can be cancelled while waiting for the MQTTClient connect to finish")
    async def test_cancel(self, client):
        client._mqtt_client.connect = custom_mock.HangingAsyncMock()

        t = asyncio.create_task(client.connect())

        # Hanging, waiting for MQTT connect to finish
        await client._mqtt_client.connect.wait_for_hang()
        assert not t.done()

        # Cancel
        t.cancel()
        with pytest.raises(asyncio.CancelledError):
            await t


@pytest.mark.describe("IoTHubMQTTClient - .disconnect()")
class TestIoTHubMQTTClientDisconnect:
    @pytest.mark.it("Awaits a disconnect using the MQTTClient")
    async def test_mqtt_disconnect(self, mocker, client):
        assert client._mqtt_client.disconnect.await_count == 0

        await client.disconnect()

        assert client._mqtt_client.disconnect.await_count == 1
        assert client._mqtt_client.disconnect.await_args == mocker.call()

    @pytest.mark.it("Allows any exceptions raised during the MQTTClient disconnect to propagate")
    @pytest.mark.parametrize("exception", mqtt_disconnect_exceptions)
    async def test_mqtt_exception(self, client, exception):
        client._mqtt_client.disconnect.side_effect = exception
        try:
            with pytest.raises(type(exception)) as e_info:
                await client.disconnect()
            assert e_info.value is exception
        finally:
            # Unset the side effect for cleanup (since shutdown uses disconnect)
            client._mqtt_client.disconnect.side_effect = None

    @pytest.mark.it("Can be cancelled while waiting for the MQTTClient disconnect to finish")
    async def test_cancel(self, mocker, client):
        client._mqtt_client.disconnect = custom_mock.HangingAsyncMock()
        try:
            t = asyncio.create_task(client.disconnect())

            # Hanging, waiting for MQTT disconnect to finish
            await client._mqtt_client.disconnect.wait_for_hang()
            assert not t.done()

            # Cancel
            t.cancel()
            with pytest.raises(asyncio.CancelledError):
                await t
        finally:
            # Unset the HangingMock for clean (since shutdown uses disconnect)
            client._mqtt_client.disconnect = mocker.AsyncMock()


@pytest.mark.describe("IoTHubMQTTClient - .send_message()")
class TestIoTHubMQTTClientSendMessage:
    @pytest.fixture
    def message(self):
        return models.Message("some payload")

    @pytest.mark.it(
        "Awaits a publish to the telemetry topic using the MQTTClient, sending the given Message's payload converted to bytes"
    )
    @pytest.mark.parametrize(
        "device_id, module_id",
        [
            pytest.param(FAKE_DEVICE_ID, None, id="Device Configuration"),
            pytest.param(FAKE_DEVICE_ID, FAKE_MODULE_ID, id="Module Configuration"),
        ],
    )
    async def test_mqtt_publish(self, mocker, client, device_id, module_id):
        assert client._mqtt_client.publish.await_count == 0
        client._device_id = device_id
        client._module_id = module_id
        message = models.Message(payload="some_payload")
        base_topic = mqtt_topic.get_telemetry_topic_for_publish(device_id, module_id)
        expected_topic = mqtt_topic.insert_message_properties_in_topic(
            topic=base_topic,
            system_properties=message.get_system_properties_dict(),
            custom_properties=message.custom_properties,
        )
        expected_payload = message.payload.encode("utf-8")

        assert client._mqtt_client.publish.await_count == 0
        await client.send_message(message)

        assert client._mqtt_client.publish.await_count == 1
        assert client._mqtt_client.publish.await_args == mocker.call(
            expected_topic, expected_payload
        )
        assert isinstance(expected_payload, bytes)

    @pytest.mark.it(
        "Derives the byte payload from the Message payload according to the Message's content encoding and content type properties"
    )
    @pytest.mark.parametrize(
        "device_id, module_id",
        [
            pytest.param(FAKE_DEVICE_ID, None, id="Device Configuration"),
            pytest.param(FAKE_DEVICE_ID, FAKE_MODULE_ID, id="Module Configuration"),
        ],
    )
    @pytest.mark.parametrize("content_encoding", ["utf-8", "utf-16", "utf-32"])
    @pytest.mark.parametrize(
        "content_type, payload, expected_str_payload",
        [
            pytest.param("text/plain", "some_text", "some_text", id="text/plain"),
            pytest.param(
                "application/json", {"some": "json"}, '{"some": "json"}', id="application/json"
            ),
        ],
    )
    async def test_publish_payload(
        self,
        mocker,
        client,
        device_id,
        module_id,
        content_encoding,
        content_type,
        payload,
        expected_str_payload,
    ):
        client._device_id = device_id
        client._module_id = module_id
        message = models.Message(
            payload=payload, content_encoding=content_encoding, content_type=content_type
        )
        base_topic = mqtt_topic.get_telemetry_topic_for_publish(device_id, module_id)
        expected_topic = mqtt_topic.insert_message_properties_in_topic(
            topic=base_topic,
            system_properties=message.get_system_properties_dict(),
            custom_properties=message.custom_properties,
        )
        expected_byte_payload = expected_str_payload.encode(content_encoding)

        await client.send_message(message)

        assert client._mqtt_client.publish.await_count == 1
        assert client._mqtt_client.publish.await_args == mocker.call(
            expected_topic, expected_byte_payload
        )

    @pytest.mark.it("Supports any string-convertible payload when using text/plain content type")
    @pytest.mark.parametrize(
        "device_id, module_id",
        [
            pytest.param(FAKE_DEVICE_ID, None, id="Device Configuration"),
            pytest.param(FAKE_DEVICE_ID, FAKE_MODULE_ID, id="Module Configuration"),
        ],
    )
    @pytest.mark.parametrize(
        "payload",
        [
            pytest.param("String Payload", id="String Payload"),
            pytest.param(1234, id="Int Payload"),
            pytest.param(2.0, id="Float Payload"),
            pytest.param(True, id="Boolean Payload"),
            pytest.param([1, 2, 3], id="List Payload"),
            pytest.param({"some": {"dictionary": "value"}}, id="Dictionary Payload"),
            pytest.param((1, 2), id="Tuple Payload"),
            pytest.param(None, id="No Payload"),
        ],
    )
    async def test_text_plain_payload(self, mocker, client, device_id, module_id, payload):
        client._device_id = device_id
        client._module_id = module_id
        message = models.Message(payload=payload, content_type="text/plain")
        base_topic = mqtt_topic.get_telemetry_topic_for_publish(device_id, module_id)
        expected_topic = mqtt_topic.insert_message_properties_in_topic(
            topic=base_topic,
            system_properties=message.get_system_properties_dict(),
            custom_properties=message.custom_properties,
        )
        expected_byte_payload = str(message.payload).encode("utf-8")

        await client.send_message(message)

        assert client._mqtt_client.publish.await_count == 1
        assert client._mqtt_client.publish.await_args == mocker.call(
            expected_topic, expected_byte_payload
        )

    @pytest.mark.it(
        "Supports any JSON-serializable payload when using application/json content type"
    )
    @pytest.mark.parametrize(
        "device_id, module_id",
        [
            pytest.param(FAKE_DEVICE_ID, None, id="Device Configuration"),
            pytest.param(FAKE_DEVICE_ID, FAKE_MODULE_ID, id="Module Configuration"),
        ],
    )
    @pytest.mark.parametrize(
        "payload",
        [
            pytest.param("String Payload", id="String Payload"),
            pytest.param(1234, id="Int Payload"),
            pytest.param(2.0, id="Float Payload"),
            pytest.param(True, id="Boolean Payload"),
            pytest.param([1, 2, 3], id="List Payload"),
            pytest.param({"some": {"dictionary": "value"}}, id="Dictionary Payload"),
            pytest.param((1, 2), id="Tuple Payload"),
            pytest.param(None, id="No Payload"),
        ],
    )
    async def test_application_json_payload(self, mocker, client, device_id, module_id, payload):
        client._device_id = device_id
        client._module_id = module_id
        message = models.Message(payload=payload, content_type="application/json")
        base_topic = mqtt_topic.get_telemetry_topic_for_publish(device_id, module_id)
        expected_topic = mqtt_topic.insert_message_properties_in_topic(
            topic=base_topic,
            system_properties=message.get_system_properties_dict(),
            custom_properties=message.custom_properties,
        )
        expected_byte_payload = json.dumps(message.payload).encode("utf-8")

        await client.send_message(message)

        assert client._mqtt_client.publish.await_count == 1
        assert client._mqtt_client.publish.await_args == mocker.call(
            expected_topic, expected_byte_payload
        )

    @pytest.mark.it("Inserts any Message properties in the telemetry topic")
    @pytest.mark.parametrize(
        "device_id, module_id",
        [
            pytest.param(FAKE_DEVICE_ID, None, id="Device Configuration"),
            pytest.param(FAKE_DEVICE_ID, FAKE_MODULE_ID, id="Module Configuration"),
        ],
    )
    async def test_message_properties(self, mocker, client, device_id, module_id, message):
        assert client._mqtt_client.publish.await_count == 0
        client._device_id = device_id
        client._module_id = module_id

        message.message_id = "some message id"
        message.content_encoding = "utf-8"
        message.content_type = "text/plain"
        message.output_name = "some output"
        message.custom_properties["custom_property1"] = 123
        message.custom_properties["custom_property2"] = "456"
        message.set_as_security_message()
        base_topic = mqtt_topic.get_telemetry_topic_for_publish(device_id, module_id)
        expected_topic = mqtt_topic.insert_message_properties_in_topic(
            topic=base_topic,
            system_properties=message.get_system_properties_dict(),
            custom_properties=message.custom_properties,
        )

        assert "%24.mid" in expected_topic  # message_id
        assert "%24.ce" in expected_topic  # content_encoding
        assert "%24.ct" in expected_topic  # content_type
        assert "%24.on" in expected_topic  # output_name
        assert "%24.ifid" in expected_topic  # security message indicator
        assert "custom_property1" in expected_topic  # custom property
        assert "custom_property2" in expected_topic  # custom property

        await client.send_message(message)

        assert client._mqtt_client.publish.await_count == 1
        assert client._mqtt_client.publish.await_args == mocker.call(expected_topic, mocker.ANY)

    @pytest.mark.it("Allows any exceptions raised from the MQTTClient publish to propagate")
    @pytest.mark.parametrize("exception", mqtt_publish_exceptions)
    async def test_mqtt_exception(self, client, exception, message):
        client._mqtt_client.publish.side_effect = exception

        with pytest.raises(type(exception)) as e_info:
            await client.send_message(message)
        assert e_info.value is exception

    @pytest.mark.it("Can be cancelled while waiting for the MQTTClient publish to finish")
    async def test_cancel(self, client, message):
        client._mqtt_client.publish = custom_mock.HangingAsyncMock()

        t = asyncio.create_task(client.send_message(message))

        # Hanging, waiting for MQTT publish to finish
        await client._mqtt_client.publish.wait_for_hang()
        assert not t.done()

        # Cancel
        t.cancel()
        with pytest.raises(asyncio.CancelledError):
            await t


@pytest.mark.describe("IoTHubMQTTClient - .send_direct_method_response()")
class TestIoTHubMQTTClientSendDirectMethodResponse:
    @pytest.fixture
    def method_response(self):
        json_response = {"some": {"json": "payload"}}
        method_response = models.DirectMethodResponse(
            request_id="123", status=200, payload=json_response
        )
        return method_response

    @pytest.mark.it(
        "Awaits a publish to the direct method response topic using the MQTTClient, sending the given DirectMethodResponse's JSON payload converted to string"
    )
    async def test_mqtt_publish(self, mocker, client, method_response):
        assert client._mqtt_client.publish.await_count == 0

        expected_topic = mqtt_topic.get_direct_method_response_topic_for_publish(
            method_response.request_id, method_response.status
        )
        expected_payload = json.dumps(method_response.payload)

        await client.send_direct_method_response(method_response)

        assert client._mqtt_client.publish.await_count == 1
        assert client._mqtt_client.publish.await_args == mocker.call(
            expected_topic, expected_payload
        )

    @pytest.mark.it("Allows any exceptions raised from the MQTTClient publish to propagate")
    @pytest.mark.parametrize("exception", mqtt_publish_exceptions)
    async def test_mqtt_exception(self, client, method_response, exception):
        client._mqtt_client.publish.side_effect = exception

        with pytest.raises(type(exception)) as e_info:
            await client.send_direct_method_response(method_response)
        assert e_info.value is exception

    @pytest.mark.it("Can be cancelled while waiting for the MQTTClient publish to finish")
    async def test_cancel(self, client, method_response):
        client._mqtt_client.publish = custom_mock.HangingAsyncMock()

        t = asyncio.create_task(client.send_direct_method_response(method_response))

        # Hanging, waiting for MQTT publish to finish
        await client._mqtt_client.publish.wait_for_hang()
        assert not t.done()

        # Cancel
        t.cancel()
        with pytest.raises(asyncio.CancelledError):
            await t


@pytest.mark.describe("IoTHubMQTTClient - .send_twin_patch()")
class TestIoTHubMQTTClientSendTwinPatch:
    @pytest.fixture
    def twin_patch(self):
        return {"property": "updated_value"}

    @pytest.fixture(autouse=True)
    def modify_publish(self, client):
        # Add a side effect to publish that will complete the pending request for that request id.
        # This will allow most tests to be able to ignore request/response infrastructure mocks.
        # If this is not the desired behavior (such as in tests OF the request/response paradigm)
        # override the publish behavior.
        #
        # To see tests regarding how this actually works in practice, see the relevant test suite
        async def fake_publish(topic, payload):
            rid = topic[topic.rfind("$rid=") :].split("=")[1]
            response = rr.Response(rid, 200, "body")
            await client._request_ledger.match_response(response)

        client._mqtt_client.publish.side_effect = fake_publish

    @pytest.mark.it(
        "Awaits a subscribe to the twin response topic using the MQTTClient, if twin responses have not already been enabled"
    )
    async def test_mqtt_subscribe_not_enabled(self, mocker, client, twin_patch):
        assert client._mqtt_client.subscribe.await_count == 0
        assert client._twin_responses_enabled is False
        expected_topic = mqtt_topic.get_twin_response_topic_for_subscribe()

        await client.send_twin_patch(twin_patch)

        assert client._mqtt_client.subscribe.await_count == 1
        assert client._mqtt_client.subscribe.await_args == mocker.call(expected_topic)

    @pytest.mark.it("Does not perform a subscribe if twin responses have already been enabled")
    async def test_mqtt_subscribe_already_enabled(self, client, twin_patch):
        assert client._mqtt_client.subscribe.await_count == 0
        client._twin_responses_enabled = True

        await client.send_twin_patch(twin_patch)

        assert client._mqtt_client.subscribe.call_count == 0

    @pytest.mark.it("Sets the twin_response_enabled flag to True upon subscribe success")
    async def test_response_enabled_flag_success(self, client, twin_patch):
        assert client._twin_responses_enabled is False

        await client.send_twin_patch(twin_patch)

        assert client._twin_responses_enabled is True

    @pytest.mark.it("Generates a new Request, using the RequestLedger stored on the client")
    @pytest.mark.parametrize(
        "responses_enabled",
        [
            pytest.param(True, id="Twin Responses Already Enabled"),
            pytest.param(False, id="Twin Responses Not Yet Enabled"),
        ],
    )
    async def test_generate_request(self, mocker, client, twin_patch, responses_enabled):
        client._twin_responses_enabled = responses_enabled
        spy_create_request = mocker.spy(client._request_ledger, "create_request")

        await client.send_twin_patch(twin_patch)

        assert spy_create_request.await_count == 1

    @pytest.mark.it(
        "Awaits a publish to the twin patch topic using the MQTTClient, sending the given twin patch JSON converted to string"
    )
    @pytest.mark.parametrize(
        "responses_enabled",
        [
            pytest.param(True, id="Twin Responses Already Enabled"),
            pytest.param(False, id="Twin Responses Not Yet Enabled"),
        ],
    )
    async def test_mqtt_publish(self, mocker, client, twin_patch, responses_enabled):
        client._twin_responses_enabled = responses_enabled
        spy_create_request = mocker.spy(client._request_ledger, "create_request")
        assert client._mqtt_client.publish.await_count == 0

        await client.send_twin_patch(twin_patch)

        request = spy_create_request.spy_return
        expected_topic = mqtt_topic.get_twin_patch_topic_for_publish(request.request_id)
        expected_payload = json.dumps(twin_patch)

        assert client._mqtt_client.publish.await_count == 1
        assert client._mqtt_client.publish.await_args == mocker.call(
            expected_topic, expected_payload
        )

    @pytest.mark.it("Awaits a received Response to the Request")
    @pytest.mark.parametrize(
        "responses_enabled",
        [
            pytest.param(True, id="Twin Responses Already Enabled"),
            pytest.param(False, id="Twin Responses Not Yet Enabled"),
        ],
    )
    async def test_get_response(self, mocker, client, twin_patch, responses_enabled):
        client._twin_responses_enabled = responses_enabled
        # Override autocompletion behavior on publish (we don't want it here)
        client._mqtt_client.publish = mocker.AsyncMock()
        # Mock out the ledger to return a mocked request
        mock_request = mocker.MagicMock(spec=rr.Request)
        mock_request.request_id = "fake_request_id"  # Need this for string manipulation
        mocker.patch.object(client._request_ledger, "create_request", return_value=mock_request)
        # Mock out the request to return a response
        mock_response = mocker.MagicMock(spec=rr.Response)
        mock_response.status = 200
        mock_request.get_response.return_value = mock_response

        await client.send_twin_patch(twin_patch)

        assert mock_request.get_response.await_count == 1
        assert mock_request.get_response.await_args == mocker.call()

    @pytest.mark.it("Raises an IoTHubError if an unsuccessful status is received via the Response")
    @pytest.mark.parametrize(
        "responses_enabled",
        [
            pytest.param(True, id="Twin Responses Already Enabled"),
            pytest.param(False, id="Twin Responses Not Yet Enabled"),
        ],
    )
    @pytest.mark.parametrize(
        "failed_status",
        [
            pytest.param(300, id="Status Code: 300"),
            pytest.param(400, id="Status Code: 400"),
            pytest.param(500, id="Status Code: 500"),
        ],
    )
    async def test_failed_response(
        self, mocker, client, twin_patch, responses_enabled, failed_status
    ):
        client._twin_responses_enabled = responses_enabled
        # Override autocompletion behavior on publish (we don't need it here)
        client._mqtt_client.publish = mocker.AsyncMock()
        # Mock out the ledger to return a mocked request
        mock_request = mocker.MagicMock(spec=rr.Request)
        mock_request.request_id = "fake_request_id"  # Need this for string manipulation
        mocker.patch.object(client._request_ledger, "create_request", return_value=mock_request)
        # Mock out the request to return a response
        mock_response = mocker.MagicMock(spec=rr.Response)
        mock_response.status = failed_status
        mock_request.get_response.return_value = mock_response

        with pytest.raises(IoTHubError):
            await client.send_twin_patch(twin_patch)

    # NOTE: MQTTClient subscribe can generate it's own cancellations due to network failure.
    # This is different from a user-initiated cancellation
    @pytest.mark.it("Allows any exceptions raised from the MQTTClient subscribe to propagate")
    @pytest.mark.parametrize("exception", mqtt_subscribe_exceptions)
    async def test_mqtt_subscribe_exception(self, client, twin_patch, exception):
        assert client._twin_responses_enabled is False
        client._mqtt_client.subscribe.side_effect = exception

        with pytest.raises(type(exception)) as e_info:
            await client.send_twin_patch(twin_patch)
        assert e_info.value is exception

    # NOTE: MQTTClient subscribe can generate it's own cancellations due to network failure.
    # This is different from a user-initiated cancellation
    @pytest.mark.it(
        "Does not set the twin_response_enabled flag to True or create a Request if MQTTClient subscribe raises"
    )
    @pytest.mark.parametrize("exception", mqtt_subscribe_exceptions)
    async def test_subscribe_exception_cleanup(self, mocker, client, twin_patch, exception):
        assert client._twin_responses_enabled is False
        spy_create_request = mocker.spy(client._request_ledger, "create_request")
        client._mqtt_client.subscribe.side_effect = exception

        with pytest.raises(type(exception)):
            await client.send_twin_patch(twin_patch)

        assert client._twin_responses_enabled is False
        assert spy_create_request.await_count == 0

    # NOTE: This is a user invoked cancel, as opposed to one above, which was generated by the
    # MQTTClient in response to a network failure.
    @pytest.mark.it(
        "Does not set the twin_response_enabled flag to True or create a Request if cancelled while waiting for the MQTT subscribe to finish"
    )
    async def test_mqtt_subscribe_cancel_cleanup(self, mocker, client, twin_patch):
        assert client._twin_responses_enabled is False
        spy_create_request = mocker.spy(client._request_ledger, "create_request")
        client._mqtt_client.subscribe = custom_mock.HangingAsyncMock()

        t = asyncio.create_task(client.send_twin_patch(twin_patch))

        # Hanging, waiting for MQTT publish to finish
        await client._mqtt_client.subscribe.wait_for_hang()
        assert not t.done()

        # Cancel
        t.cancel()
        with pytest.raises(asyncio.CancelledError):
            await t

        assert client._twin_responses_enabled is False
        assert spy_create_request.await_count == 0

    @pytest.mark.it("Allows any exceptions raised from the MQTTClient publish to propagate")
    @pytest.mark.parametrize("exception", mqtt_publish_exceptions)
    async def test_mqtt_publish_exception(self, client, twin_patch, exception):
        client._mqtt_client.publish.side_effect = exception

        with pytest.raises(type(exception)) as e_info:
            await client.send_twin_patch(twin_patch)
        assert e_info.value is exception

    @pytest.mark.it("Deletes the Request from the RequestLedger if MQTTClient publish raises")
    @pytest.mark.parametrize("exception", mqtt_publish_exceptions)
    async def test_mqtt_publish_exception_cleanup(self, mocker, client, twin_patch, exception):
        client._mqtt_client.publish.side_effect = exception
        spy_create_request = mocker.spy(client._request_ledger, "create_request")
        spy_delete_request = mocker.spy(client._request_ledger, "delete_request")

        with pytest.raises(type(exception)):
            await client.send_twin_patch(twin_patch)

        # The Request that was created was also deleted
        assert spy_create_request.await_count == 1
        assert spy_create_request.await_args == mocker.call()
        assert spy_delete_request.await_count == 1
        assert spy_delete_request.await_args == mocker.call(
            spy_create_request.spy_return.request_id
        )

    @pytest.mark.it(
        "Deletes the Request from the RequestLedger if cancelled while waiting for the MQTTClient publish to finish"
    )
    async def test_mqtt_publish_cancel_cleanup(self, mocker, client, twin_patch):
        client._mqtt_client.publish = custom_mock.HangingAsyncMock()
        spy_create_request = mocker.spy(client._request_ledger, "create_request")
        spy_delete_request = mocker.spy(client._request_ledger, "delete_request")

        t = asyncio.create_task(client.send_twin_patch(twin_patch))

        # Hanging, waiting for MQTT publish to finish
        await client._mqtt_client.publish.wait_for_hang()
        assert not t.done()

        # Request was created, but not yet deleted
        assert spy_create_request.await_count == 1
        assert spy_create_request.await_args == mocker.call()
        assert spy_delete_request.await_count == 0

        # Cancel
        t.cancel()
        with pytest.raises(asyncio.CancelledError):
            await t

        # The Request that was created has now been deleted
        assert spy_delete_request.await_count == 1
        assert spy_delete_request.await_args == mocker.call(
            spy_create_request.spy_return.request_id
        )

    @pytest.mark.it(
        "Deletes the Request from the RequestLedger if cancelled while waiting for a twin response"
    )
    async def test_waiting_response_cancel_cleanup(self, mocker, client, twin_patch):
        # Override autocompletion behavior on publish (we don't want it here)
        client._mqtt_client.publish = mocker.AsyncMock()

        # Mock Request creation to return a specific, mocked request that hangs on
        # awaiting a Response
        request = rr.Request()
        request.get_response = custom_mock.HangingAsyncMock()
        mocker.patch.object(rr, "Request", return_value=request)
        spy_create_request = mocker.spy(client._request_ledger, "create_request")
        spy_delete_request = mocker.spy(client._request_ledger, "delete_request")

        send_task = asyncio.create_task(client.send_twin_patch(twin_patch))

        # Hanging, waiting for response
        await request.get_response.wait_for_hang()
        assert not send_task.done()

        # Request was created, but not yet deleted
        assert spy_create_request.await_count == 1
        assert spy_create_request.await_args == mocker.call()
        assert spy_delete_request.await_count == 0

        # Cancel
        send_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await send_task

        # The Request that was created was also deleted
        assert spy_delete_request.await_count == 1
        assert spy_delete_request.await_args == mocker.call(request.request_id)


@pytest.mark.describe("IoTHubMQTTClient - .get_twin()")
class TestIoTHubMQTTClientGetTwin:
    @pytest.fixture(autouse=True)
    def modify_publish(self, client):
        # Add a side effect to publish that will complete the pending request for that request id.
        # This will allow most tests to be able to ignore request/response infrastructure mocks.
        # If this is not the desired behavior (such as in tests OF the request/response paradigm)
        # override the publish behavior.
        #
        # To see tests regarding how this actually works in practice, see the relevant test suite
        async def fake_publish(topic, payload):
            rid = topic[topic.rfind("$rid=") :].split("=")[1]
            response = rr.Response(rid, 200, '{"json": "in", "a": {"string": "format"}}')
            await client._request_ledger.match_response(response)

        client._mqtt_client.publish.side_effect = fake_publish

    @pytest.mark.it(
        "Awaits a subscribe to the twin response topic using the MQTTClient, if twin responses have not already been enabled"
    )
    async def test_mqtt_subscribe_not_enabled(self, mocker, client):
        assert client._mqtt_client.subscribe.await_count == 0
        assert client._twin_responses_enabled is False
        expected_topic = mqtt_topic.get_twin_response_topic_for_subscribe()

        await client.get_twin()

        assert client._mqtt_client.subscribe.await_count == 1
        assert client._mqtt_client.subscribe.await_args == mocker.call(expected_topic)

    @pytest.mark.it("Does not perform a subscribe if twin responses have already been enabled")
    async def test_mqtt_subscribe_already_enabled(self, client):
        assert client._mqtt_client.subscribe.await_count == 0
        client._twin_responses_enabled = True

        await client.get_twin()

        assert client._mqtt_client.subscribe.call_count == 0

    @pytest.mark.it("Sets the twin_response_enabled flag to True upon subscribe success")
    async def test_response_enabled_flag_success(self, client):
        assert client._twin_responses_enabled is False

        await client.get_twin()

        assert client._twin_responses_enabled is True

    @pytest.mark.it("Generates a new Request, using the RequestLedger stored on the client")
    @pytest.mark.parametrize(
        "responses_enabled",
        [
            pytest.param(True, id="Twin Responses Already Enabled"),
            pytest.param(False, id="Twin Responses Not Yet Enabled"),
        ],
    )
    async def test_generate_request(self, mocker, client, responses_enabled):
        client._twin_responses_enabled = responses_enabled
        spy_create_request = mocker.spy(client._request_ledger, "create_request")

        await client.get_twin()

        assert spy_create_request.await_count == 1

    @pytest.mark.it("Awaits a publish to the twin request topic using the MQTTClient")
    @pytest.mark.parametrize(
        "responses_enabled",
        [
            pytest.param(True, id="Twin Responses Already Enabled"),
            pytest.param(False, id="Twin Responses Not Yet Enabled"),
        ],
    )
    async def test_mqtt_publish(self, mocker, client, responses_enabled):
        client._twin_responses_enabled = responses_enabled
        spy_create_request = mocker.spy(client._request_ledger, "create_request")
        assert client._mqtt_client.publish.await_count == 0

        await client.get_twin()

        request = spy_create_request.spy_return
        expected_topic = mqtt_topic.get_twin_request_topic_for_publish(request.request_id)
        expected_payload = " "

        assert client._mqtt_client.publish.await_count == 1
        assert client._mqtt_client.publish.await_args == mocker.call(
            expected_topic, expected_payload
        )

    @pytest.mark.it("Awaits a received Response to the Request")
    @pytest.mark.parametrize(
        "responses_enabled",
        [
            pytest.param(True, id="Twin Responses Already Enabled"),
            pytest.param(False, id="Twin Responses Not Yet Enabled"),
        ],
    )
    async def test_get_response(self, mocker, client, responses_enabled):
        client._twin_responses_enabled = responses_enabled
        # Override autocompletion behavior on publish (we don't want it here)
        client._mqtt_client.publish = mocker.AsyncMock()
        # Mock out the ledger to return a mocked request
        mock_request = mocker.MagicMock(spec=rr.Request)
        mock_request.request_id = "fake_request_id"  # Need this for string manipulation
        mocker.patch.object(client._request_ledger, "create_request", return_value=mock_request)
        # Mock out the request to return a response
        mock_response = mocker.MagicMock(spec=rr.Response)
        mock_response.status = 200
        mock_response.body = '{"json": "in", "a": {"string": "format"}}'
        mock_request.get_response.return_value = mock_response

        await client.get_twin()

        assert mock_request.get_response.await_count == 1
        assert mock_request.get_response.await_args == mocker.call()

    @pytest.mark.it("Raises an IoTHubError if an unsuccessful status is received via the Response")
    @pytest.mark.parametrize(
        "responses_enabled",
        [
            pytest.param(True, id="Twin Responses Already Enabled"),
            pytest.param(False, id="Twin Responses Not Yet Enabled"),
        ],
    )
    @pytest.mark.parametrize(
        "failed_status",
        [
            pytest.param(300, id="Status Code: 300"),
            pytest.param(400, id="Status Code: 400"),
            pytest.param(500, id="Status Code: 500"),
        ],
    )
    async def test_failed_response(self, mocker, client, responses_enabled, failed_status):
        client._twin_responses_enabled = responses_enabled
        # Override autocompletion behavior on publish (we don't need it here)
        client._mqtt_client.publish = mocker.AsyncMock()
        # Mock out the ledger to return a mocked request
        mock_request = mocker.MagicMock(spec=rr.Request)
        mock_request.request_id = "fake_request_id"  # Need this for string manipulation
        mocker.patch.object(client._request_ledger, "create_request", return_value=mock_request)
        # Mock out the request to return a response
        mock_response = mocker.MagicMock(spec=rr.Response)
        mock_response.status = failed_status
        mock_response.body = " "
        mock_request.get_response.return_value = mock_response

        with pytest.raises(IoTHubError):
            await client.get_twin()

    @pytest.mark.it(
        "Returns the twin received in the Response, converted to JSON, if the Response status was successful"
    )
    @pytest.mark.parametrize(
        "responses_enabled",
        [
            pytest.param(True, id="Twin Responses Already Enabled"),
            pytest.param(False, id="Twin Responses Not Yet Enabled"),
        ],
    )
    async def test_success_response(self, mocker, client, responses_enabled):
        client._twin_responses_enabled = responses_enabled
        # Override autocompletion behavior on publish (we don't need it here)
        client._mqtt_client.publish = mocker.AsyncMock()
        # Mock out the ledger to return a mocked request
        mock_request = mocker.MagicMock(spec=rr.Request)
        mock_request.request_id = "fake_request_id"  # Need this for string manipulation
        mocker.patch.object(client._request_ledger, "create_request", return_value=mock_request)
        # Mock out the request to return a response
        mock_response = mocker.MagicMock(spec=rr.Response)
        mock_response.status = 200
        fake_twin_string = '{"json": "in", "a": {"string": "format"}}'
        mock_response.body = fake_twin_string
        mock_request.get_response.return_value = mock_response

        twin = await client.get_twin()
        assert twin == json.loads(fake_twin_string)

    # NOTE: MQTTClient subscribe can generate it's own cancellations due to network failure.
    # This is different from a user-initiated cancellation
    @pytest.mark.it("Allows any exceptions raised from the MQTTClient subscribe to propagate")
    @pytest.mark.parametrize("exception", mqtt_subscribe_exceptions)
    async def test_mqtt_subscribe_exception(self, client, exception):
        assert client._twin_responses_enabled is False
        client._mqtt_client.subscribe.side_effect = exception

        with pytest.raises(type(exception)) as e_info:
            await client.get_twin()
        assert e_info.value is exception

    # NOTE: MQTTClient subscribe can generate it's own cancellations due to network failure.
    # This is different from a user-initiated cancellation
    @pytest.mark.it(
        "Does not set the twin_response_enabled flag to True or create a Request if MQTTClient subscribe raises"
    )
    @pytest.mark.parametrize("exception", mqtt_subscribe_exceptions)
    async def test_subscribe_exception_cleanup(self, mocker, client, exception):
        assert client._twin_responses_enabled is False
        spy_create_request = mocker.spy(client._request_ledger, "create_request")
        client._mqtt_client.subscribe.side_effect = exception

        with pytest.raises(type(exception)):
            await client.get_twin()

        assert client._twin_responses_enabled is False
        assert spy_create_request.await_count == 0

    # NOTE: This is a user invoked cancel, as opposed to one above, which was generated by the
    # MQTTClient in response to a network failure.
    @pytest.mark.it(
        "Does not set the twin_response_enabled flag to True or create a Request if cancelled while waiting for the MQTTClient subscribe to finish"
    )
    async def test_mqtt_subscribe_cancel_cleanup(self, mocker, client):
        assert client._twin_responses_enabled is False
        spy_create_request = mocker.spy(client._request_ledger, "create_request")
        client._mqtt_client.subscribe = custom_mock.HangingAsyncMock()

        t = asyncio.create_task(client.get_twin())

        # Hanging, waiting for MQTT publish to finish
        await client._mqtt_client.subscribe.wait_for_hang()
        assert not t.done()

        # Cancel
        t.cancel()
        with pytest.raises(asyncio.CancelledError):
            await t

        assert client._twin_responses_enabled is False
        assert spy_create_request.await_count == 0

    @pytest.mark.it("Allows any exceptions raised from the MQTTClient publish to propagate")
    @pytest.mark.parametrize("exception", mqtt_publish_exceptions)
    async def test_mqtt_publish_exception(self, client, exception):
        client._mqtt_client.publish.side_effect = exception

        with pytest.raises(type(exception)) as e_info:
            await client.get_twin()
        assert e_info.value is exception

    @pytest.mark.it("Deletes the Request from the RequestLedger if MQTTClient publish raises")
    @pytest.mark.parametrize("exception", mqtt_publish_exceptions)
    async def test_mqtt_publish_exception_cleanup(self, mocker, client, exception):
        client._mqtt_client.publish.side_effect = exception
        spy_create_request = mocker.spy(client._request_ledger, "create_request")
        spy_delete_request = mocker.spy(client._request_ledger, "delete_request")

        with pytest.raises(type(exception)):
            await client.get_twin()

        assert spy_create_request.await_count == 1
        assert spy_create_request.await_args == mocker.call()
        assert spy_delete_request.await_count == 1
        assert spy_delete_request.await_args == mocker.call(
            spy_create_request.spy_return.request_id
        )

    @pytest.mark.it(
        "Deletes the Request from the RequestLedger if cancelled while waiting for the MQTTClient publish to finish"
    )
    async def test_mqtt_publish_cancel_cleanup(self, mocker, client):
        client._mqtt_client.publish = custom_mock.HangingAsyncMock()
        spy_create_request = mocker.spy(client._request_ledger, "create_request")
        spy_delete_request = mocker.spy(client._request_ledger, "delete_request")

        t = asyncio.create_task(client.get_twin())

        # Hanging, waiting for MQTT publish to finish
        await client._mqtt_client.publish.wait_for_hang()
        assert not t.done()

        # Request was created, but not yet deleted
        assert spy_create_request.await_count == 1
        assert spy_create_request.await_args == mocker.call()
        assert spy_delete_request.await_count == 0

        # Cancel
        t.cancel()
        with pytest.raises(asyncio.CancelledError):
            await t

        # The Request that was created has now been deleted
        assert spy_delete_request.await_count == 1
        assert spy_delete_request.await_args == mocker.call(
            spy_create_request.spy_return.request_id
        )

    @pytest.mark.it(
        "Deletes the Request from the RequestLedger if cancelled while waiting for a twin response"
    )
    async def test_waiting_response_cancel_cleanup(self, mocker, client):
        # Override autocompletion behavior on publish (we don't want it here)
        client._mqtt_client.publish = mocker.AsyncMock()

        # Mock Request creation to return a specific, mocked request that hangs on
        # awaiting a Response
        request = rr.Request()
        request.get_response = custom_mock.HangingAsyncMock()
        mocker.patch.object(rr, "Request", return_value=request)
        spy_create_request = mocker.spy(client._request_ledger, "create_request")
        spy_delete_request = mocker.spy(client._request_ledger, "delete_request")

        send_task = asyncio.create_task(client.get_twin())

        # Hanging, waiting for response
        await request.get_response.wait_for_hang()
        assert not send_task.done()

        # Request was created, but not yet deleted
        assert spy_create_request.await_count == 1
        assert spy_create_request.await_args == mocker.call()
        assert spy_delete_request.await_count == 0

        # Cancel
        send_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await send_task

        # The Request that was created was also deleted
        assert spy_delete_request.await_count == 1
        assert spy_delete_request.await_args == mocker.call(request.request_id)


class IoTHubMQTTClientEnableReceiveTest(abc.ABC):
    """Base class for the .enable_x() methods"""

    @abc.abstractmethod
    @pytest.fixture
    def method_name(self):
        """Return the name of the enable method under test"""
        pass

    @abc.abstractmethod
    @pytest.fixture
    def expected_topic(self):
        """Return the expected topic string to subscribe to"""
        pass

    @pytest.mark.it("Awaits a subscribe to the associated incoming data topic using the MQTTClient")
    async def test_mqtt_subscribe(self, mocker, client, method_name, expected_topic):
        assert client._mqtt_client.subscribe.await_count == 0

        method = getattr(client, method_name)
        await method()

        assert client._mqtt_client.subscribe.await_count == 1
        assert client._mqtt_client.subscribe.await_args == mocker.call(expected_topic)

    @pytest.mark.it("Allows any exceptions raised from the MQTTClient subscribe to propagate")
    @pytest.mark.parametrize("exception", mqtt_subscribe_exceptions)
    async def test_mqtt_subscribe_exception(self, client, method_name, exception):
        client._mqtt_client.subscribe.side_effect = exception

        with pytest.raises(type(exception)) as e_info:
            method = getattr(client, method_name)
            await method()
        assert e_info.value is exception

    @pytest.mark.it("Can be cancelled while waiting for the MQTTClient subscribe to finish")
    async def test_cancel(self, client, method_name):
        client._mqtt_client.subscribe = custom_mock.HangingAsyncMock()

        method = getattr(client, method_name)
        t = asyncio.create_task(method())

        # Hanging, waiting for MQTT subscribe to finish
        await client._mqtt_client.subscribe.wait_for_hang()
        assert not t.done()

        t.cancel()
        with pytest.raises(asyncio.CancelledError):
            await t


class IoTHubMQTTClientDisableReceiveTest(abc.ABC):
    """Base class for the .disable_x() methods"""

    @abc.abstractmethod
    @pytest.fixture
    def method_name(self):
        """Return the name of the disable method under test"""
        pass

    @abc.abstractmethod
    @pytest.fixture
    def expected_topic(self):
        """Return the expected topic string to unsubscribe from"""
        pass

    @pytest.mark.it(
        "Awaits an unsubscribe from the associated incoming data topic using the MQTTClient"
    )
    async def test_mqtt_unsubscribe(self, mocker, client, method_name, expected_topic):
        assert client._mqtt_client.unsubscribe.await_count == 0

        method = getattr(client, method_name)
        await method()

        assert client._mqtt_client.unsubscribe.await_count == 1
        assert client._mqtt_client.unsubscribe.await_args == mocker.call(expected_topic)

    @pytest.mark.it("Allows any exceptions raised from the MQTTClient unsubscribe to propagate")
    @pytest.mark.parametrize("exception", mqtt_subscribe_exceptions)
    async def test_mqtt_unsubscribe_exception(self, client, method_name, exception):
        client._mqtt_client.unsubscribe.side_effect = exception

        with pytest.raises(type(exception)) as e_info:
            method = getattr(client, method_name)
            await method()
        assert e_info.value is exception

    @pytest.mark.it("Can be cancelled while waiting for the MQTTClient unsubscribe to finish")
    async def test_cancel(self, client, method_name):
        client._mqtt_client.unsubscribe = custom_mock.HangingAsyncMock()

        method = getattr(client, method_name)
        t = asyncio.create_task(method())

        # Hanging, waiting for MQTT subscribe to finish
        await client._mqtt_client.unsubscribe.wait_for_hang()
        assert not t.done()

        t.cancel()
        with pytest.raises(asyncio.CancelledError):
            await t


@pytest.mark.describe("IoTHubMQTTClient - .enable_c2d_message_receive()")
class TestIoTHubMQTTClientEnableC2DMessageReceive(IoTHubMQTTClientEnableReceiveTest):
    @pytest.fixture
    def method_name(self):
        return "enable_c2d_message_receive"

    @pytest.fixture
    def expected_topic(self, client):
        return mqtt_topic.get_c2d_topic_for_subscribe(client._device_id)

    @pytest.mark.it("Raises IoTHubClientError if client not configured for a Device")
    async def test_with_module_id(self, client):
        client._module_id = FAKE_MODULE_ID
        with pytest.raises(IoTHubClientError):
            await client.enable_c2d_message_receive()


@pytest.mark.describe("IoTHubMQTTClient - .disable_c2d_message_receive()")
class TestIoTHubMQTTClientDisableC2DMessageReceive(IoTHubMQTTClientDisableReceiveTest):
    @pytest.fixture
    def method_name(self):
        return "disable_c2d_message_receive"

    @pytest.fixture
    def expected_topic(self, client):
        return mqtt_topic.get_c2d_topic_for_subscribe(client._device_id)

    @pytest.mark.it("Raises IoTHubClientError if client not configured for a Device")
    async def test_with_module_id(self, client):
        client._module_id = FAKE_MODULE_ID
        with pytest.raises(IoTHubClientError):
            await client.disable_c2d_message_receive()


@pytest.mark.describe("IoTHubMQTTClient - .enable_input_message_receive()")
class TestIoTHubMQTTClientEnableInputMessageReceive(IoTHubMQTTClientEnableReceiveTest):
    @pytest.fixture(autouse=True)
    def modify_client(self, client):
        """Add a module ID to the client"""
        client._module_id = FAKE_MODULE_ID

    @pytest.fixture
    def method_name(self):
        return "enable_input_message_receive"

    @pytest.fixture
    def expected_topic(self, client):
        return mqtt_topic.get_input_topic_for_subscribe(client._device_id, client._module_id)

    @pytest.mark.it("Raises IoTHubClientError if client not configured for a Module")
    async def test_no_module_id(self, client):
        client._module_id = None
        with pytest.raises(IoTHubClientError):
            await client.enable_input_message_receive()


@pytest.mark.describe("IoTHubMQTTClient - .disable_input_message_receive()")
class TestIoTHubMQTTClientDisableInputMessageReceive(IoTHubMQTTClientDisableReceiveTest):
    @pytest.fixture(autouse=True)
    def modify_client(self, client):
        """Add a module ID to the client"""
        client._module_id = FAKE_MODULE_ID

    @pytest.fixture
    def method_name(self):
        return "disable_input_message_receive"

    @pytest.fixture
    def expected_topic(self, client):
        return mqtt_topic.get_input_topic_for_subscribe(client._device_id, client._module_id)

    @pytest.mark.it("Raises IoTHubClientError if client not configured for a Module")
    async def test_no_module_id(self, client):
        client._module_id = None
        with pytest.raises(IoTHubClientError):
            await client.disable_input_message_receive()


@pytest.mark.describe("IoTHubMQTTClient - .enable_direct_method_request_receive()")
class TestIoTHubMQTTClientEnableDirectMethodRequestReceive(IoTHubMQTTClientEnableReceiveTest):
    @pytest.fixture
    def method_name(self):
        return "enable_direct_method_request_receive"

    @pytest.fixture
    def expected_topic(self):
        return mqtt_topic.get_direct_method_request_topic_for_subscribe()


@pytest.mark.describe("IoTHubMQTTClient - .disable_direct_method_request_receive()")
class TestIoTHubMQTTClientDisableDirectMethodRequestReceive(IoTHubMQTTClientDisableReceiveTest):
    @pytest.fixture
    def method_name(self):
        return "disable_direct_method_request_receive"

    @pytest.fixture
    def expected_topic(self):
        return mqtt_topic.get_direct_method_request_topic_for_subscribe()


@pytest.mark.describe("IoTHubMQTTClient - .enable_twin_patch_receive()")
class TestIoTHubMQTTClientEnableTwinPatchReceive(IoTHubMQTTClientEnableReceiveTest):
    @pytest.fixture
    def method_name(self):
        return "enable_twin_patch_receive"

    @pytest.fixture
    def expected_topic(self):
        return mqtt_topic.get_twin_patch_topic_for_subscribe()


@pytest.mark.describe("IoTHubMQTTClient - .disable_twin_patch_receive()")
class TestIoTHubMQTTClientDisableTwinPatchReceive(IoTHubMQTTClientDisableReceiveTest):
    @pytest.fixture
    def method_name(self):
        return "disable_twin_patch_receive"

    @pytest.fixture
    def expected_topic(self):
        return mqtt_topic.get_twin_patch_topic_for_subscribe()


@pytest.mark.describe("IoTHubMQTTClient - .incoming_c2d_messages")
class TestIoTHubMQTTClientIncomingC2DMessages:
    @pytest.mark.it(
        "Yields a Message whenever the MQTTClient receives an MQTTMessage on the incoming C2D message topic"
    )
    async def test_yields_message(self, client):
        sub_topic = mqtt_topic.get_c2d_topic_for_subscribe(client._device_id)
        receive_topic = sub_topic.rstrip("#")
        mqtt_msg1 = mqtt.MQTTMessage(mid=1, topic=receive_topic.encode("utf-8"))
        mqtt_msg2 = mqtt.MQTTMessage(mid=2, topic=receive_topic.encode("utf-8"))
        # Load the MQTTMessages into the MQTTClient's filtered message queue
        await client._mqtt_client._incoming_filtered_messages[sub_topic].put(mqtt_msg1)
        await client._mqtt_client._incoming_filtered_messages[sub_topic].put(mqtt_msg2)
        # Get items from the generator
        msg1 = await client.incoming_c2d_messages.__anext__()
        assert isinstance(msg1, models.Message)
        msg2 = await client.incoming_c2d_messages.__anext__()
        assert isinstance(msg2, models.Message)
        assert msg1 != msg2

    @pytest.mark.it(
        "Derives the yielded Message payload from the MQTTMessage byte payload according to the content encoding and content type properties contained in the MQTTMessage's topic"
    )
    @pytest.mark.parametrize("content_encoding", ["utf-8", "utf-16", "utf-32"])
    @pytest.mark.parametrize(
        "content_type, payload_str, expected_payload",
        [
            pytest.param("text/plain", "some_payload", "some_payload", id="text/plain"),
            pytest.param(
                "application/json", '{"some": "json"}', {"some": "json"}, id="application/json"
            ),
        ],
    )
    async def test_payload(
        self, client, content_encoding, payload_str, content_type, expected_payload
    ):
        sub_topic = mqtt_topic.get_c2d_topic_for_subscribe(client._device_id)
        receive_topic = mqtt_topic.insert_message_properties_in_topic(
            topic=sub_topic.rstrip("#"),
            system_properties={"$.ce": content_encoding, "$.ct": content_type},
            custom_properties={},
        )
        # NOTE: topics are always utf-8 encoded, even if the payload is different
        mqtt_msg = mqtt.MQTTMessage(mid=1, topic=receive_topic.encode("utf-8"))
        mqtt_msg.payload = payload_str.encode(content_encoding)

        await client._mqtt_client._incoming_filtered_messages[sub_topic].put(mqtt_msg)
        msg = await client.incoming_c2d_messages.__anext__()
        assert msg.payload != mqtt_msg.payload
        assert msg.payload == expected_payload

    @pytest.mark.it(
        "Supports conversion to JSON object for any valid JSON string payload when using application/json content type"
    )
    @pytest.mark.parametrize(
        "str_payload, expected_json_payload",
        [
            pytest.param('"String Payload"', "String Payload", id="String Payload"),
            pytest.param("1234", 1234, id="Int Payload"),
            pytest.param("2.0", 2.0, id="Float Payload"),
            pytest.param("true", True, id="Boolean Payload"),
            pytest.param("[1, 2, 3]", [1, 2, 3], id="List Payload"),
            pytest.param(
                '{"some": {"dictionary": "value"}}',
                {"some": {"dictionary": "value"}},
                id="Dictionary Payload",
            ),
            pytest.param("null", None, id="No Payload"),
        ],
    )
    async def test_application_json_payload(self, client, str_payload, expected_json_payload):
        sub_topic = mqtt_topic.get_c2d_topic_for_subscribe(client._device_id)
        receive_topic = mqtt_topic.insert_message_properties_in_topic(
            topic=sub_topic.rstrip("#"),
            system_properties={"$.ct": "application/json"},
            custom_properties={},
        )
        mqtt_msg = mqtt.MQTTMessage(mid=1, topic=receive_topic.encode("utf-8"))
        mqtt_msg.payload = str_payload.encode("utf-8")

        await client._mqtt_client._incoming_filtered_messages[sub_topic].put(mqtt_msg)
        msg = await client.incoming_c2d_messages.__anext__()
        assert msg.payload == expected_json_payload

    @pytest.mark.it(
        "Uses a default utf-8 codec to decode the MQTTMessage byte payload if no content encoding property is contained in the MQTTMessage's topic"
    )
    @pytest.mark.parametrize(
        "content_type, payload_str, expected_payload",
        [
            pytest.param("text/plain", "some_payload", "some_payload", id="text/plain"),
            pytest.param(
                "application/json", '{"some": "json"}', {"some": "json"}, id="application/json"
            ),
        ],
    )
    async def test_payload_content_encoding_default(
        self, client, content_type, payload_str, expected_payload
    ):
        sub_topic = mqtt_topic.get_c2d_topic_for_subscribe(client._device_id)
        receive_topic = mqtt_topic.insert_message_properties_in_topic(
            topic=sub_topic.rstrip("#"),
            system_properties={"$.ct": content_type},
            custom_properties={},
        )
        assert "$.ce" not in receive_topic

        mqtt_msg = mqtt.MQTTMessage(mid=1, topic=receive_topic.encode("utf-8"))
        mqtt_msg.payload = payload_str.encode("utf-8")

        await client._mqtt_client._incoming_filtered_messages[sub_topic].put(mqtt_msg)
        msg = await client.incoming_c2d_messages.__anext__()
        assert msg.payload != mqtt_msg.payload
        assert msg.payload == expected_payload

    @pytest.mark.it(
        "Treats the payload as text/plain content by default if no content type property is contained in the MQTTMessage's topic"
    )
    @pytest.mark.parametrize("content_encoding", ["utf-8", "utf-16", "utf-32"])
    async def test_payload_content_type_default(self, client, content_encoding):
        sub_topic = mqtt_topic.get_c2d_topic_for_subscribe(client._device_id)
        receive_topic = mqtt_topic.insert_message_properties_in_topic(
            topic=sub_topic.rstrip("#"),
            system_properties={"$.ce": content_encoding},
            custom_properties={},
        )
        assert "$.ct" not in receive_topic

        mqtt_msg = mqtt.MQTTMessage(mid=1, topic=receive_topic.encode("utf-8"))
        payload_str = '{"payload": "that", "could": "be", "json": {"or could be": "string"}}'
        mqtt_msg.payload = payload_str.encode(content_encoding)

        await client._mqtt_client._incoming_filtered_messages[sub_topic].put(mqtt_msg)
        msg = await client.incoming_c2d_messages.__anext__()
        assert msg.payload != mqtt_msg.payload
        assert msg.payload == payload_str
        assert msg.payload != json.loads(payload_str)

    @pytest.mark.it(
        "Sets any message properties contained in the MQTTMessage's topic onto the resulting Message"
    )
    @pytest.mark.parametrize(
        "system_properties, custom_properties",
        [
            pytest.param(
                {
                    "$.mid": "message_id",
                    "$.ce": "utf-8",
                    "$.ct": "text/plain",
                    "iothub-ack": "ack",
                    "$.exp": "expiry_time",
                    "$.uid": "user_id",
                    "$.cid": "correlation_id",
                },
                {},
                id="System Properties Only",
            ),
            pytest.param(
                {
                    "$.mid": "message_id",
                    "$.ce": "utf-8",
                    "$.ct": "text/plain",
                    "iothub-ack": "ack",
                    "$.exp": "expiry_time",
                    "$.uid": "user_id",
                    "$.cid": "correlation_id",
                },
                {"cust_prop1": "value1", "cust_prop2": "value2"},
                id="System Properties and Custom Properties",
            ),
        ],
    )
    async def test_message_properties(self, client, system_properties, custom_properties):
        sub_topic = mqtt_topic.get_c2d_topic_for_subscribe(client._device_id)
        receive_topic = mqtt_topic.insert_message_properties_in_topic(
            topic=sub_topic.rstrip("#"),
            system_properties=system_properties,
            custom_properties=custom_properties,
        )
        mqtt_msg = mqtt.MQTTMessage(mid=1, topic=receive_topic.encode("utf-8"))
        mqtt_msg.payload = "some payload".encode("utf-8")

        await client._mqtt_client._incoming_filtered_messages[sub_topic].put(mqtt_msg)
        msg = await client.incoming_c2d_messages.__anext__()
        assert msg.get_system_properties_dict() == system_properties
        assert msg.custom_properties == custom_properties

    @pytest.mark.it(
        "Sets default system properties onto the resulting Message if they are not provided in the MQTTMessage's topic"
    )
    async def test_message_property_defaults(self, client):
        sub_topic = mqtt_topic.get_c2d_topic_for_subscribe(client._device_id)
        receive_topic = mqtt_topic.insert_message_properties_in_topic(
            topic=sub_topic.rstrip("#"),
            system_properties={},
            custom_properties={},
        )
        mqtt_msg = mqtt.MQTTMessage(mid=1, topic=receive_topic.encode("utf-8"))

        await client._mqtt_client._incoming_filtered_messages[sub_topic].put(mqtt_msg)
        msg = await client.incoming_c2d_messages.__anext__()
        assert msg.get_system_properties_dict() == {"$.ce": "utf-8", "$.ct": "text/plain"}
        assert msg.content_type == "text/plain"
        assert msg.content_encoding == "utf-8"


@pytest.mark.describe("IoTHubMQTTClient - .incoming_input_messages")
class TestIoTHubMQTTClientIncomingInputMessages:
    @pytest.fixture(autouse=True)
    def modify_client_config(self, client_config):
        # Input Messages only work for Module Configuration.
        # NOTE: This has to be changed on the config, not the client,
        # because it affects client initialization
        client_config.module_id = FAKE_MODULE_ID

    @pytest.mark.it(
        "Yields a Message whenever the MQTTClient receives an MQTTMessage on the incoming Input message topic"
    )
    async def test_yields_message(self, client):
        sub_topic = mqtt_topic.get_input_topic_for_subscribe(client._device_id, client._module_id)
        receive_topic = sub_topic.rstrip("#") + FAKE_INPUT_NAME + "/"
        mqtt_msg1 = mqtt.MQTTMessage(mid=1, topic=receive_topic.encode("utf-8"))
        mqtt_msg2 = mqtt.MQTTMessage(mid=2, topic=receive_topic.encode("utf-8"))
        # Load the MQTTMessages into the MQTTClient's filtered message queue
        await client._mqtt_client._incoming_filtered_messages[sub_topic].put(mqtt_msg1)
        await client._mqtt_client._incoming_filtered_messages[sub_topic].put(mqtt_msg2)
        # Get items from the generator
        msg1 = await client.incoming_input_messages.__anext__()
        assert isinstance(msg1, models.Message)
        msg2 = await client.incoming_input_messages.__anext__()
        assert isinstance(msg2, models.Message)
        assert msg1 != msg2

    @pytest.mark.it(
        "Derives the yielded Message payload from the MQTTMessage byte payload according to the content encoding and content type properties contained in the MQTTMessage's topic"
    )
    @pytest.mark.parametrize("content_encoding", ["utf-8", "utf-16", "utf-32"])
    @pytest.mark.parametrize(
        "content_type, payload_str, expected_payload",
        [
            pytest.param("text/plain", "some_payload", "some_payload", id="text/plain"),
            pytest.param(
                "application/json", '{"some": "json"}', {"some": "json"}, id="application/json"
            ),
        ],
    )
    async def test_payload(
        self, client, content_encoding, payload_str, content_type, expected_payload
    ):
        sub_topic = mqtt_topic.get_input_topic_for_subscribe(client._device_id, client._module_id)
        receive_topic = mqtt_topic.insert_message_properties_in_topic(
            topic=sub_topic.rstrip("#") + FAKE_INPUT_NAME + "/",
            system_properties={"$.ce": content_encoding, "$.ct": content_type},
            custom_properties={},
        )
        # NOTE: topics are always utf-8 encoded, even if the payload is different
        mqtt_msg = mqtt.MQTTMessage(mid=1, topic=receive_topic.encode("utf-8"))
        mqtt_msg.payload = payload_str.encode(content_encoding)

        await client._mqtt_client._incoming_filtered_messages[sub_topic].put(mqtt_msg)
        msg = await client.incoming_input_messages.__anext__()
        assert msg.payload != mqtt_msg.payload
        assert msg.payload == expected_payload

    @pytest.mark.it(
        "Supports conversion to JSON object for any valid JSON string payload when using application/json content type"
    )
    @pytest.mark.parametrize(
        "str_payload, expected_json_payload",
        [
            pytest.param('"String Payload"', "String Payload", id="String Payload"),
            pytest.param("1234", 1234, id="Int Payload"),
            pytest.param("2.0", 2.0, id="Float Payload"),
            pytest.param("true", True, id="Boolean Payload"),
            pytest.param("[1, 2, 3]", [1, 2, 3], id="List Payload"),
            pytest.param(
                '{"some": {"dictionary": "value"}}',
                {"some": {"dictionary": "value"}},
                id="Dictionary Payload",
            ),
            pytest.param("null", None, id="No Payload"),
        ],
    )
    async def test_application_json_payload(self, client, str_payload, expected_json_payload):
        sub_topic = mqtt_topic.get_input_topic_for_subscribe(client._device_id, client._module_id)
        receive_topic = mqtt_topic.insert_message_properties_in_topic(
            topic=sub_topic.rstrip("#") + FAKE_INPUT_NAME + "/",
            system_properties={"$.ct": "application/json"},
            custom_properties={},
        )
        mqtt_msg = mqtt.MQTTMessage(mid=1, topic=receive_topic.encode("utf-8"))
        mqtt_msg.payload = str_payload.encode("utf-8")

        await client._mqtt_client._incoming_filtered_messages[sub_topic].put(mqtt_msg)
        msg = await client.incoming_input_messages.__anext__()
        assert msg.payload == expected_json_payload

    @pytest.mark.it(
        "Uses a default utf-8 codec to decode the MQTTMessage byte payload if no content encoding property is contained in the MQTTMessage's topic"
    )
    @pytest.mark.parametrize(
        "content_type, payload_str, expected_payload",
        [
            pytest.param("text/plain", "some_payload", "some_payload", id="text/plain"),
            pytest.param(
                "application/json", '{"some": "json"}', {"some": "json"}, id="application/json"
            ),
        ],
    )
    async def test_payload_content_encoding_default(
        self, client, content_type, payload_str, expected_payload
    ):
        sub_topic = mqtt_topic.get_input_topic_for_subscribe(client._device_id, client._module_id)
        receive_topic = mqtt_topic.insert_message_properties_in_topic(
            topic=sub_topic.rstrip("#") + FAKE_INPUT_NAME + "/",
            system_properties={"$.ct": content_type},
            custom_properties={},
        )
        assert "$.ce" not in receive_topic

        mqtt_msg = mqtt.MQTTMessage(mid=1, topic=receive_topic.encode("utf-8"))
        mqtt_msg.payload = payload_str.encode("utf-8")

        await client._mqtt_client._incoming_filtered_messages[sub_topic].put(mqtt_msg)
        msg = await client.incoming_input_messages.__anext__()
        assert msg.payload != mqtt_msg.payload
        assert msg.payload == expected_payload

    @pytest.mark.it(
        "Treats the payload as text/plain content by default if no content type property is contained in the MQTTMessage's topic"
    )
    @pytest.mark.parametrize("content_encoding", ["utf-8", "utf-16", "utf-32"])
    async def test_payload_content_type_default(self, client, content_encoding):
        sub_topic = mqtt_topic.get_input_topic_for_subscribe(client._device_id, client._module_id)
        receive_topic = mqtt_topic.insert_message_properties_in_topic(
            topic=sub_topic.rstrip("#") + FAKE_INPUT_NAME + "/",
            system_properties={"$.ce": content_encoding},
            custom_properties={},
        )
        assert "$.ct" not in receive_topic

        mqtt_msg = mqtt.MQTTMessage(mid=1, topic=receive_topic.encode("utf-8"))
        payload_str = '{"payload": "that", "could": "be", "json": {"or could be": "string"}}'
        mqtt_msg.payload = payload_str.encode(content_encoding)

        await client._mqtt_client._incoming_filtered_messages[sub_topic].put(mqtt_msg)
        msg = await client.incoming_input_messages.__anext__()
        assert msg.payload != mqtt_msg.payload
        assert msg.payload == payload_str
        assert msg.payload != json.loads(payload_str)

    @pytest.mark.it(
        "Sets any message properties contained in the MQTTMessage's topic onto the resulting Message"
    )
    @pytest.mark.parametrize(
        "system_properties, custom_properties",
        [
            pytest.param(
                {
                    "$.mid": "message_id",
                    "$.to": "some_input",
                    "$.ce": "utf-8",
                    "$.ct": "text/plain",
                    "iothub-ack": "ack",
                    "$.exp": "expiry_time",
                    "$.uid": "user_id",
                    "$.cid": "correlation_id",
                },
                {},
                id="System Properties Only",
            ),
            pytest.param(
                {
                    "$.mid": "message_id",
                    "$.to": "some_input",
                    "$.ce": "utf-8",
                    "$.ct": "text/plain",
                    "iothub-ack": "ack",
                    "$.exp": "expiry_time",
                    "$.uid": "user_id",
                    "$.cid": "correlation_id",
                },
                {"cust_prop1": "value1", "cust_prop2": "value2"},
                id="System Properties and Custom Properties",
            ),
        ],
    )
    async def test_message_properties(self, client, system_properties, custom_properties):
        sub_topic = mqtt_topic.get_input_topic_for_subscribe(client._device_id, client._module_id)
        receive_topic = mqtt_topic.insert_message_properties_in_topic(
            topic=sub_topic.rstrip("#") + FAKE_INPUT_NAME + "/",
            system_properties=system_properties,
            custom_properties=custom_properties,
        )
        mqtt_msg = mqtt.MQTTMessage(mid=1, topic=receive_topic.encode("utf-8"))
        mqtt_msg.payload = "some payload".encode("utf-8")

        await client._mqtt_client._incoming_filtered_messages[sub_topic].put(mqtt_msg)
        msg = await client.incoming_input_messages.__anext__()
        assert msg.get_system_properties_dict() == system_properties
        assert msg.custom_properties == custom_properties

    @pytest.mark.it(
        "Sets default system properties onto the resulting Message if they are not provided in the MQTTMessage's topic"
    )
    async def test_message_property_defaults(self, client):
        sub_topic = mqtt_topic.get_input_topic_for_subscribe(client._device_id, client._module_id)
        receive_topic = mqtt_topic.insert_message_properties_in_topic(
            topic=sub_topic.rstrip("#") + FAKE_INPUT_NAME + "/",
            system_properties={},
            custom_properties={},
        )
        mqtt_msg = mqtt.MQTTMessage(mid=1, topic=receive_topic.encode("utf-8"))

        await client._mqtt_client._incoming_filtered_messages[sub_topic].put(mqtt_msg)
        msg = await client.incoming_input_messages.__anext__()
        assert msg.get_system_properties_dict() == {"$.ce": "utf-8", "$.ct": "text/plain"}
        assert msg.content_type == "text/plain"
        assert msg.content_encoding == "utf-8"


@pytest.mark.describe("IoTHubMQTTClient - .incoming_direct_s")
class TestIoTHubMQTTClientIncomingDirectMethodRequests:
    @pytest.mark.it(
        "Yields a DirectMethodRequest whenever the MQTTClient receives an MQTTMessage on the incoming direct method request topic"
    )
    async def test_yields_direct_(self, client):
        generic_topic = mqtt_topic.get_direct_method_request_topic_for_subscribe()

        # Create MQTTMessages
        mreq1_name = "some_method"
        mreq1_id = "12"
        mreq1_topic = generic_topic.rstrip("#") + "{}/?$rid={}".format(mreq1_name, mreq1_id)
        mqtt_msg1 = mqtt.MQTTMessage(mid=1, topic=mreq1_topic.encode("utf-8"))
        mqtt_msg1.payload = '{"json": "in", "a": {"string": "format"}}'.encode("utf-8")
        mreq2_name = "some_other_method"
        mreq2_id = "17"
        mreq2_topic = generic_topic.rstrip("#") + "{}/?$rid={}".format(mreq2_name, mreq2_id)
        mqtt_msg2 = mqtt.MQTTMessage(mid=2, topic=mreq2_topic.encode("utf-8"))
        mqtt_msg2.payload = '{"json": "in", "a": {"different": {"string": "format"}}}'.encode(
            "utf-8"
        )

        # Load the MQTTMessages into the MQTTClient's filtered message queue
        await client._mqtt_client._incoming_filtered_messages[generic_topic].put(mqtt_msg1)
        await client._mqtt_client._incoming_filtered_messages[generic_topic].put(mqtt_msg2)

        # Get items from generator
        mreq1 = await client.incoming_direct_method_requests.__anext__()
        assert isinstance(mreq1, models.DirectMethodRequest)
        mreq2 = await client.incoming_direct_method_requests.__anext__()
        assert isinstance(mreq2, models.DirectMethodRequest)
        assert mreq1 != mreq2

    @pytest.mark.it(
        "Extracts the method name and request id from the MQTTMessage's topic and sets them on the resulting DirectMethodRequest"
    )
    async def test_direct_method_request_attributes(self, client):
        generic_topic = mqtt_topic.get_direct_method_request_topic_for_subscribe()

        mreq_name = "some_method"
        mreq_id = "12"
        mreq_topic = generic_topic.rstrip("#") + "{}/?$rid={}".format(mreq_name, mreq_id)
        mqtt_msg1 = mqtt.MQTTMessage(mid=1, topic=mreq_topic.encode("utf-8"))
        mqtt_msg1.payload = '{"json": "in", "a": {"string": "format"}}'.encode("utf-8")

        await client._mqtt_client._incoming_filtered_messages[generic_topic].put(mqtt_msg1)
        mreq = await client.incoming_direct_method_requests.__anext__()

        assert mreq.name == mreq_name
        assert mreq.request_id == mreq_id

    @pytest.mark.it(
        "Derives the yielded DirectMethodRequest JSON payload from the MQTTMessage's byte payload using the utf-8 codec"
    )
    async def test_payload(self, client):
        generic_topic = mqtt_topic.get_direct_method_request_topic_for_subscribe()
        expected_payload = {"json": "derived", "from": {"byte": "payload"}}

        mreq_name = "some_method"
        mreq_id = "12"
        mreq_topic = generic_topic.rstrip("#") + "{}/?$rid={}".format(mreq_name, mreq_id)
        mqtt_msg1 = mqtt.MQTTMessage(mid=1, topic=mreq_topic.encode("utf-8"))
        mqtt_msg1.payload = json.dumps(expected_payload).encode("utf-8")

        await client._mqtt_client._incoming_filtered_messages[generic_topic].put(mqtt_msg1)
        mreq = await client.incoming_direct_method_requests.__anext__()

        assert mreq.payload == expected_payload


@pytest.mark.describe("IoTHubMQTTClient - .incoming_twin_patches")
class TestIoTHubMQTTClientIncomingTwinPatches:
    @pytest.mark.it(
        "Yields a JSON-formatted dictionary whenever the MQTTClient receives an MQTTMessage on the incoming twin patch topic"
    )
    async def test_yields_twin(self, client):
        generic_topic = mqtt_topic.get_twin_patch_topic_for_subscribe()
        patch1_topic = generic_topic.rstrip("#") + "?$version=1"
        patch2_topic = generic_topic.rstrip("#") + "?$version=2"
        # Create MQTTMessages
        mqtt_msg1 = mqtt.MQTTMessage(mid=1, topic=patch1_topic.encode("utf-8"))
        mqtt_msg1.payload = '{"property1": "value1", "property2": "value2", "$version": 1}'.encode(
            "utf-8"
        )
        mqtt_msg2 = mqtt.MQTTMessage(mid=2, topic=patch2_topic.encode("utf-8"))
        mqtt_msg2.payload = '{"property1": "value3", "property2": "value4", "$version": 2}'.encode(
            "utf-8"
        )
        # Load the MQTTMessages into the MQTTClient's filtered message queue
        await client._mqtt_client._incoming_filtered_messages[generic_topic].put(mqtt_msg1)
        await client._mqtt_client._incoming_filtered_messages[generic_topic].put(mqtt_msg2)
        # Get items form generator
        patch1 = await client.incoming_twin_patches.__anext__()
        assert isinstance(patch1, dict)
        assert json.dumps(patch1)  # This would fail if it's not valid JSON
        patch2 = await client.incoming_twin_patches.__anext__()
        assert isinstance(patch2, dict)
        assert json.dumps(patch1)  # This would fail if it's not valid JSON

    @pytest.mark.it(
        "Derives the yielded JSON-formatted dictionary from the MQTTMessage's byte payload using the utf-8 codec"
    )
    async def test_payload(self, client):
        generic_topic = mqtt_topic.get_twin_patch_topic_for_subscribe()
        patch_topic = generic_topic.rstrip("#") + "?$version=1"
        expected_json = {"property1": "value1", "property2": "value2", "$version": 1}
        mqtt_msg = mqtt.MQTTMessage(mid=1, topic=patch_topic.encode("utf-8"))
        mqtt_msg.payload = json.dumps(expected_json).encode("utf-8")

        await client._mqtt_client._incoming_filtered_messages[generic_topic].put(mqtt_msg)
        patch = await client.incoming_twin_patches.__anext__()
        assert patch == expected_json


# TODO: To reflect the complexity of background tasks, these tests need to be adjusted
# to be about the background task itself, not a reaction to an event. This is probably the
# end of any "OCCURRENCE" tests in the client layer
@pytest.mark.describe("IoTHubMQTTClient - OCCURRENCE: Twin Response Received")
class TestIoTHubMQTTClientIncomingTwinResponse:
    # NOTE: This test suite exists for simplicity - twin responses are used in both
    # .get_twin() and .send_twin_patch(), and rather than testing this functionality twice
    # it has been isolated out to test here. This also makes mocking behavior for the tests of
    # the aforementioned methods much simpler.
    @pytest.mark.it(
        "Creates a Response containing the request id and status code from the topic, as well as the utf-8 decoded payload of the MQTTMessage, whenever the MQTTClient receives an MQTTMessage on the twin response topic"
    )
    @pytest.mark.parametrize(
        "status",
        [
            pytest.param(200, id="Status Code: 200"),
            pytest.param(300, id="Status Code: 300"),
            pytest.param(400, id="Status Code: 400"),
            pytest.param(500, id="Status Code: 500"),
        ],
    )
    async def test_response(self, mocker, client, status):
        # Mocks
        mocker.patch.object(client, "_request_ledger", spec=rr.RequestLedger)
        spy_response_factory = mocker.spy(rr, "Response")
        # MQTTMessages
        generic_topic = mqtt_topic.get_twin_response_topic_for_subscribe()
        rid1 = "some rid"
        msg1_topic = generic_topic.rstrip("#") + "{}/?$rid={}".format(status, rid1)
        mqtt_msg1 = mqtt.MQTTMessage(mid=1, topic=msg1_topic.encode("utf-8"))
        # Empty payload used in twin patch responses
        mqtt_msg1.payload = " ".encode("utf-8")
        rid2 = "some other rid"
        msg2_topic = generic_topic.rstrip("#") + "{}/?$rid={}".format(status, rid2)
        mqtt_msg2 = mqtt.MQTTMessage(mid=2, topic=msg2_topic.encode("utf-8"))
        # JSON payload used in get twin responses
        mqtt_msg2.payload = '{"json": "in", "a": {"string": "format"}}'.encode("utf-8")
        # No responses have been created yet
        assert spy_response_factory.call_count == 0
        # Load the MQTTMessages into the MQTTClient's filtered message queue
        await client._mqtt_client._incoming_filtered_messages[generic_topic].put(mqtt_msg1)
        await asyncio.sleep(0.1)
        assert spy_response_factory.call_count == 1
        resp1 = spy_response_factory.spy_return
        assert resp1.request_id == rid1
        assert resp1.status == status
        assert resp1.body == mqtt_msg1.payload.decode("utf-8")
        await client._mqtt_client._incoming_filtered_messages[generic_topic].put(mqtt_msg2)
        await asyncio.sleep(0.1)
        assert spy_response_factory.call_count == 2
        resp2 = spy_response_factory.spy_return
        assert resp2.request_id == rid2
        assert resp2.status == status
        assert resp2.body == mqtt_msg2.payload.decode("utf-8")

    @pytest.mark.it("Matches the newly created Response on the RequestLedger")
    async def test_match(self, mocker, client):
        mock_ledger = mocker.patch.object(client, "_request_ledger", spec=rr.RequestLedger)
        spy_response_factory = mocker.spy(rr, "Response")
        generic_topic = mqtt_topic.get_twin_response_topic_for_subscribe()
        topic = generic_topic.rstrip("#") + "{}/?$rid={}".format(200, "some rid")
        mqtt_msg = mqtt.MQTTMessage(mid=1, topic=topic.encode("utf-8"))
        assert spy_response_factory.call_count == 0
        assert mock_ledger.match_response.call_count == 0
        # Load the MQTTMessage into the MQTTClient's filtered message queue
        await client._mqtt_client._incoming_filtered_messages[generic_topic].put(mqtt_msg)
        await asyncio.sleep(0.1)
        assert spy_response_factory.call_count == 1
        resp1 = spy_response_factory.spy_return
        assert mock_ledger.match_response.call_count == 1
        assert mock_ledger.match_response.call_args == mocker.call(resp1)


# TODO: To reflect the complexity of background tasks, these tests need to be adjusted
# to be about the background task itself, not a reaction to an event. This is probably the
# end of any "OCCURRENCE" tests in the client layer
@pytest.mark.describe("IoTHubMQTTClient - OCCURRENCE: SasTokenProvider Updates SasToken")
class TestIoTHubMQTTClientSasTokenUpdate:
    @pytest.fixture(autouse=True)
    def modify_client_config(self, client_config, mock_sastoken_provider):
        # Need to use a client with SAS token auth
        # NOTE: This has to be changed on the config, not the client,
        # because it affects client initialization
        client_config.sastoken_provider = mock_sastoken_provider

    @pytest.mark.it(
        "Updates the MQTTClient's credentials, using the stored username as the username, and the string-converted new SasToken as the password"
    )
    async def test_updates_credentials(self, mocker, client):
        # Client is waiting on a new SasToken
        assert client._sastoken_provider.wait_for_new_sastoken.await_count == 1
        assert client._sastoken_provider.wait_for_new_sastoken.is_hanging()
        assert client._mqtt_client.set_credentials.call_count == 0

        # Trigger new SasToken arrival
        client._sastoken_provider.wait_for_new_sastoken.stop_hanging()
        new_sastoken = client._sastoken_provider.wait_for_new_sastoken.return_value
        assert isinstance(new_sastoken, st.SasToken)
        await asyncio.sleep(0.1)

        # Credentials are updated
        assert client._mqtt_client.set_credentials.call_count == 1
        assert client._mqtt_client.set_credentials.call_args == mocker.call(
            client._username, str(new_sastoken)
        )

        # Client is now waiting on a new SasToken again
        assert client._sastoken_provider.wait_for_new_sastoken.await_count == 2
        assert client._sastoken_provider.wait_for_new_sastoken.is_hanging()
        assert client._mqtt_client.set_credentials.call_count == 1

        # Trigger new SasToken arrival again
        client._sastoken_provider.wait_for_new_sastoken.stop_hanging()
        new_sastoken = client._sastoken_provider.wait_for_new_sastoken.return_value
        assert isinstance(new_sastoken, st.SasToken)
        await asyncio.sleep(0.1)

        # Credentials are updated again
        assert client._mqtt_client.set_credentials.call_count == 2
        assert client._mqtt_client.set_credentials.call_args == mocker.call(
            client._username, str(new_sastoken)
        )

        # And so it continues forever and ever

        await client.shutdown()
