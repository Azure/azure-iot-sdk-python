# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import aiohttp
import asyncio
import pytest
import ssl
import time
import urllib.parse
from pytest_lazyfixture import lazy_fixture
from dev_utils import custom_mock
from v3_async_wip import config, constant, user_agent
from v3_async_wip import http_path_iothub as http_path
from v3_async_wip import sastoken as st
from v3_async_wip.iot_exceptions import IoTHubClientError, IoTHubError, IoTEdgeError
from v3_async_wip.iothub_http_client import IoTHubHTTPClient

FAKE_DEVICE_ID = "fake_device_id"
FAKE_MODULE_ID = "fake_module_id"
FAKE_HOSTNAME = "fake.hostname"
FAKE_SIGNATURE = "ajsc8nLKacIjGsYyB4iYDFCZaRMmmDrUuY5lncYDYPI="
FAKE_EXPIRY = str(int(time.time()) + 3600)
FAKE_URI = "fake/resource/location"
FAKE_CORRELATION_ID = (
    "MjAyMzAyMjIwNTQ5XzNjNTM5YTQyLWM1STItNDM3OS1iMzc5LWFiMTlhYTNhZWJjZV9zb21lIGJsb2JfdmVyMi4w"
)


# NOTE: We use "async with" statements when using aiohttp to do HTTP requests, i.e. context managers.
# It is not as easy to mock out context managers as regular functions/coroutines, but still quite
# doable, although doing so relies on some implementation knowledge of how context managers work.
# That said, you should be able to follow along fairly easily even without that, so just follow the
# templates here if modifying this file.
#
# All you really need to know is that the HTTP request itself (e.g. POST) is a regular function
# that ends up returning an async context manager, which is then used to do the request in an
# asynchronous fashion. This is why most tests related to the request itself will be checking
# the mock 'calls' rather than 'awaits', with only a few really verifying that the async context
# manager is being used by verifying the 'await' of the `__aenter__` coroutine


# ~~~~~ Fixtures ~~~~~
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
    return provider


@pytest.fixture(autouse=True)
def mock_session(mocker):
    mock_session = mocker.MagicMock(spec=aiohttp.ClientSession)
    # Mock out POST and it's response
    mock_response = mock_session.post.return_value.__aenter__.return_value
    mock_response.status = 200
    mock_response.reason = "some reason"
    return mock_session


@pytest.fixture
def client_config():
    """Defaults to Device Configuration. Required values only.
    Customize in test if you need specific options (incl. Module)"""

    client_config = config.IoTHubClientConfig(
        device_id=FAKE_DEVICE_ID, hostname=FAKE_HOSTNAME, ssl_context=ssl.SSLContext()
    )
    return client_config


@pytest.fixture
async def client(mocker, client_config, mock_session):
    client = IoTHubHTTPClient(client_config)
    client._session = mock_session

    yield client
    # Shutdown contains a sleep of 250ms, so mock it out to speed up test performance
    mocker.patch.object(asyncio, "sleep")
    await client.shutdown()


# ~~~~~ Saved Parametrizations ~~~~~
failed_status_codes = [
    pytest.param(300, id="Status Code: 300"),
    pytest.param(400, id="Status Code: 400"),
    pytest.param(500, id="Status Code: 500"),
]

http_post_exceptions = [
    # TODO: are there expected exceptions here? Needs to be manually tested and investigated
    pytest.param(lazy_fixture("arbitrary_exception"), id="Unexpected Exception")
]

http_response_json_exceptions = [
    # TODO: are there expected exceptions here? Needs to be manually tested and investigated
    pytest.param(lazy_fixture("arbitrary_exception"), id="Unexpected Exception")
]


# ~~~~~ Tests ~~~~~
@pytest.mark.describe("IoTHubHTTPClient -- Instantiation")
class TestIoTHubHTTPClientInstantiation:
    # NOTE: As the instantiation is the unit under test here, we shouldn't use the client fixture.
    # This means that you must do graceful exit by shutting down the client at the end of all tests
    # and you may need to do a manual mock of the underlying HTTP client where appropriate.
    configurations = [
        pytest.param(FAKE_DEVICE_ID, None, id="Device Configuration"),
        pytest.param(FAKE_DEVICE_ID, FAKE_MODULE_ID, id="Module Configuration"),
    ]

    @pytest.fixture(autouse=True)
    def mock_asyncio_sleep(self, mocker):
        """Mock asyncio sleep for performance so that shutdowns don't have a delay"""
        mocker.patch.object(asyncio, "sleep")

    @pytest.mark.it(
        "Stores the `device_id` and `module_id` values from the IoTHubClientConfig as attributes"
    )
    @pytest.mark.parametrize("device_id, module_id", configurations)
    async def test_simple_ids(self, client_config, device_id, module_id):
        client_config.device_id = device_id
        client_config.module_id = module_id

        client = IoTHubHTTPClient(client_config)
        assert client._device_id == device_id
        assert client._module_id == module_id

        await client.shutdown()

    @pytest.mark.it(
        "Derives the `edge_module_id` from the `device_id` and `module_id` if the IoTHubClientConfig contains a `module_id`"
    )
    async def test_edge_module_id(self, client_config):
        client_config.device_id = FAKE_DEVICE_ID
        client_config.module_id = FAKE_MODULE_ID
        expected_edge_module_id = "{device_id}/{module_id}".format(
            device_id=FAKE_DEVICE_ID, module_id=FAKE_MODULE_ID
        )

        client = IoTHubHTTPClient(client_config)
        assert client._edge_module_id == expected_edge_module_id

        await client.shutdown()

    # NOTE: It would be nice if we could only do this for Edge modules, but there's no way to
    # indicate a Module is Edge vs non-Edge
    @pytest.mark.it("Sets the `edge_module_id` to None if not using a Module")
    async def test_no_edge_module_id(self, client_config):
        client_config.device_id = FAKE_DEVICE_ID
        client_config.module_id = None

        client = IoTHubHTTPClient(client_config)
        assert client._edge_module_id is None

        await client.shutdown()

    @pytest.mark.it(
        "Constructs the `user_agent_string` by concatenating the base IoTHub user agent with the `product_info` from the IoTHubClientConfig"
    )
    @pytest.mark.parametrize("device_id, module_id", configurations)
    @pytest.mark.parametrize(
        "product_info",
        [
            pytest.param("", id="No Product Info"),
            pytest.param("my-product-info", id="Custom Product Info"),
            pytest.param(
                constant.DIGITAL_TWIN_PREFIX + ":com:example:ClimateSensor;1",
                id="Digital Twin Product Info",
            ),
        ],
    )
    async def test_user_agent(self, client_config, device_id, module_id, product_info):
        client_config.device_id = device_id
        client_config.module_id = module_id
        client_config.product_info = product_info
        expected_user_agent = user_agent.get_iothub_user_agent() + product_info

        client = IoTHubHTTPClient(client_config)
        assert client._user_agent_string == expected_user_agent

        await client.shutdown()

    @pytest.mark.it("Does not URL encode the user agent string")
    @pytest.mark.parametrize("device_id, module_id", configurations)
    @pytest.mark.parametrize(
        "product_info",
        [
            pytest.param("my$product$info", id="Custom Product Info"),
            pytest.param(
                constant.DIGITAL_TWIN_PREFIX + ":com:example:$Climate$ensor;1",
                id="Digital Twin Product Info",
            ),
        ],
    )
    async def test_user_agent_no_url_encoding(
        self, client_config, device_id, module_id, product_info
    ):
        # NOTE: The user agent DOES eventually get url encoded, just not here, and not yet
        client_config.device_id = device_id
        client_config.module_id = module_id
        client_config.product_info = product_info
        expected_user_agent = user_agent.get_iothub_user_agent() + product_info
        url_encoded_expected_user_agent = urllib.parse.quote_plus(expected_user_agent)
        assert url_encoded_expected_user_agent != expected_user_agent

        client = IoTHubHTTPClient(client_config)
        assert client._user_agent_string == expected_user_agent

        await client.shutdown()

    @pytest.mark.it(
        "Creates a aiohttp ClientSession configured for accessing a URL based on the IoTHubClientConfig's `hostname`, with a timeout of 10 seconds"
    )
    @pytest.mark.parametrize("device_id, module_id", configurations)
    async def test_client_session(self, mocker, client_config, device_id, module_id):
        client_config.device_id = device_id
        client_config.module_id = module_id

        spy_session_init = mocker.spy(aiohttp, "ClientSession")
        expected_base_url = "https://" + client_config.hostname
        expected_timeout = 10

        client = IoTHubHTTPClient(client_config)
        assert spy_session_init.call_count == 1
        assert spy_session_init.call_args == mocker.call(
            base_url=expected_base_url, timeout=mocker.ANY
        )
        timeout_obj = spy_session_init.call_args[1]["timeout"]
        assert isinstance(timeout_obj, aiohttp.ClientTimeout)
        assert timeout_obj.total == expected_timeout
        assert client._session is spy_session_init.spy_return

        await client.shutdown()

    @pytest.mark.it("Stores the `ssl_context` from the IoTHubClientConfig as an attribute")
    @pytest.mark.parametrize("device_id, module_id", configurations)
    async def test_ssl_context(self, client_config, device_id, module_id):
        client_config.device_id = device_id
        client_config.module_id = module_id
        assert client_config.ssl_context is not None

        client = IoTHubHTTPClient(client_config)
        assert client._ssl_context is client_config.ssl_context

        await client.shutdown()

    @pytest.mark.it("Stores the `sastoken_provider` from the IoTHubClientConfig as an attribute")
    @pytest.mark.parametrize("device_id, module_id", configurations)
    @pytest.mark.parametrize(
        "sastoken_provider",
        [
            pytest.param(lazy_fixture("mock_sastoken_provider"), id="SasTokenProvider present"),
            pytest.param(None, id="No SasTokenProvider present"),
        ],
    )
    async def test_sastoken_provider(self, client_config, device_id, module_id, sastoken_provider):
        client_config.device_id = device_id
        client_config.module_id = module_id
        client_config.sastoken_provider = sastoken_provider

        client = IoTHubHTTPClient(client_config)
        assert client._sastoken_provider is client_config.sastoken_provider

        await client.shutdown()


@pytest.mark.describe("IoTHubHTTPClient - .shutdown()")
class TestIoTHubHTTPClientShutdown:
    @pytest.fixture(autouse=True)
    def mock_asyncio_sleep(self, mocker):
        """Mock asyncio sleep for performance so that shutdowns don't have a delay"""
        return mocker.patch.object(asyncio, "sleep")

    @pytest.mark.it("Closes the aiohttp ClientSession")
    async def test_close_session(self, mocker, client):
        assert client._session.close.await_count == 0

        await client.shutdown()
        assert client._session.close.await_count == 1
        assert client._session.close.await_args == mocker.call()

    @pytest.mark.it("Waits 250ms to allow for proper SSL cleanup")
    async def test_wait(self, mocker, client, mock_asyncio_sleep):
        assert mock_asyncio_sleep.await_count == 0

        await client.shutdown()

        assert mock_asyncio_sleep.await_count == 1
        assert mock_asyncio_sleep.await_args == mocker.call(0.25)

    @pytest.mark.it("Does not return a value")
    async def test_return_value(self, client):
        retval = await client.shutdown()
        assert retval is None

    @pytest.mark.it("Can be cancelled while waiting for the aiohttp ClientSession to close")
    async def test_cancel_during_close(self, client):
        original_close = client._session.close
        client._session.close = custom_mock.HangingAsyncMock()

        t = asyncio.create_task(client.shutdown())

        # Hanging, waiting for close to finish
        await client._session.close.wait_for_hang()
        assert not t.done()

        # Cancel
        t.cancel()
        with pytest.raises(asyncio.CancelledError):
            await t

        # Restore original close so cleanup works correctly
        client._session.close = original_close

    @pytest.mark.it("Can be cancelled while waiting for SSL cleanup")
    async def test_cancel_during_wait(self, client):
        original_sleep = asyncio.sleep
        asyncio.sleep = custom_mock.HangingAsyncMock()

        t = asyncio.create_task(client.shutdown())

        # Hanging, waiting for sleep to finish
        await asyncio.sleep.wait_for_hang()
        assert not t.done()

        # Cancel
        t.cancel()
        with pytest.raises(asyncio.CancelledError):
            await t

        # Restore original sleep to... everything... works correctly
        asyncio.sleep = original_sleep


@pytest.mark.describe("IoTHubHTTPClient - .invoke_direct_method()")
class TestIoTHubHTTPClientInvokeDirectMethod:
    @pytest.fixture(autouse=True)
    def modify_client_config(self, client_config):
        """Modify the client config to always be an Edge Module"""
        client_config.device_id = FAKE_DEVICE_ID
        client_config.module_id = FAKE_MODULE_ID

    @pytest.fixture(autouse=True)
    def modify_post_response(self, client):
        fake_method_response = {
            "status": 200,
            "payload": "fake payload",
        }
        mock_response = client._session.post.return_value.__aenter__.return_value
        mock_response.json.return_value = fake_method_response

    @pytest.fixture
    def method_params(self):
        return {
            "methodName": "fake method",
            "payload": "fake payload",
            "connectTimeoutInSeconds": 47,
            "responseTimeoutInSeconds": 42,
        }

    targets = [
        pytest.param("target_device", None, id="Target: Device"),
        pytest.param("target_device", "target_module", id="Target: Module"),
    ]

    @pytest.mark.it(
        "Does an asynchronous POST request operation to the relative 'direct method invoke' path using the aiohttp ClientSession and the stored SSL context"
    )
    @pytest.mark.parametrize("target_device_id, target_module_id", targets)
    async def test_http_post(
        self, mocker, client, target_device_id, target_module_id, method_params
    ):
        post_ctx_manager = client._session.post.return_value
        assert client._session.post.call_count == 0
        assert post_ctx_manager.__aenter__.await_count == 0
        expected_path = http_path.get_direct_method_invoke_path(target_device_id, target_module_id)

        await client.invoke_direct_method(
            device_id=target_device_id, module_id=target_module_id, method_params=method_params
        )

        assert client._session.post.call_count == 1
        assert client._session.post.call_args == mocker.call(
            url=expected_path,
            json=mocker.ANY,
            params=mocker.ANY,
            headers=mocker.ANY,
            ssl=client._ssl_context,
        )
        assert post_ctx_manager.__aenter__.await_count == 1
        assert post_ctx_manager.__aenter__.await_args == mocker.call()

    @pytest.mark.it(
        "Sends the provided method parameters with the POST request as the JSON payload"
    )
    @pytest.mark.parametrize("target_device_id, target_module_id", targets)
    async def test_post_json(
        self, mocker, client, target_device_id, target_module_id, method_params
    ):
        assert client._session.post.call_count == 0

        await client.invoke_direct_method(
            device_id=target_device_id, module_id=target_module_id, method_params=method_params
        )

        assert client._session.post.call_count == 1
        assert client._session.post.call_args == mocker.call(
            url=mocker.ANY,
            json=method_params,
            params=mocker.ANY,
            headers=mocker.ANY,
            ssl=mocker.ANY,
        )

    @pytest.mark.it("Sends the API version with the POST request as a query parameter")
    @pytest.mark.parametrize("target_device_id, target_module_id", targets)
    async def test_post_query_params(
        self, mocker, client, target_device_id, target_module_id, method_params
    ):
        assert client._session.post.call_count == 0
        expected_params = {"api-version": constant.IOTHUB_API_VERSION}

        await client.invoke_direct_method(
            device_id=target_device_id, module_id=target_module_id, method_params=method_params
        )

        assert client._session.post.call_count == 1
        assert client._session.post.call_args == mocker.call(
            url=mocker.ANY,
            json=mocker.ANY,
            params=expected_params,
            headers=mocker.ANY,
            ssl=mocker.ANY,
        )

    @pytest.mark.it(
        "Sets the 'User-Agent' HTTP header on the POST request to the URL-encoded `user_agent` value stored on the client"
    )
    @pytest.mark.parametrize("target_device_id, target_module_id", targets)
    async def test_post_user_agent_header(
        self, client, target_device_id, target_module_id, method_params
    ):
        assert client._session.post.call_count == 0
        expected_user_agent = urllib.parse.quote_plus(client._user_agent_string)
        assert expected_user_agent != client._user_agent_string

        await client.invoke_direct_method(
            device_id=target_device_id, module_id=target_module_id, method_params=method_params
        )

        assert client._session.post.call_count == 1
        headers = client._session.post.call_args[1]["headers"]
        assert headers["User-Agent"] == expected_user_agent

    @pytest.mark.it(
        "Sets the 'x-ms-edge-moduleId' HTTP header on the POST request to the `edge_module_id` value stored on the client"
    )
    @pytest.mark.parametrize("target_device_id, target_module_id", targets)
    async def test_post_edge_module_id_header(
        self, client, target_device_id, target_module_id, method_params
    ):
        assert client._session.post.call_count == 0

        await client.invoke_direct_method(
            device_id=target_device_id, module_id=target_module_id, method_params=method_params
        )

        assert client._session.post.call_count == 1
        headers = client._session.post.call_args[1]["headers"]
        assert headers["x-ms-edge-moduleId"] == client._edge_module_id

    @pytest.mark.it(
        "Sets the 'Authorization' HTTP header on the POST request to the current SAS Token string from the SasTokenProvider stored on the client, if it exists"
    )
    @pytest.mark.parametrize("target_device_id, target_module_id", targets)
    async def test_post_authorization_header_sas(
        self, client, target_device_id, target_module_id, method_params, mock_sastoken_provider
    ):
        assert client._session.post.call_count == 0
        client._sastoken_provider = mock_sastoken_provider
        assert mock_sastoken_provider.get_current_sastoken.call_count == 0
        expected_sastoken_string = str(mock_sastoken_provider.get_current_sastoken.return_value)

        await client.invoke_direct_method(
            device_id=target_device_id, module_id=target_module_id, method_params=method_params
        )

        assert client._session.post.call_count == 1
        headers = client._session.post.call_args[1]["headers"]
        assert headers["Authorization"] == expected_sastoken_string

    @pytest.mark.it(
        "Does not include an 'Authorization' HTTP header on the POST request if not using SAS Token authentication"
    )
    @pytest.mark.parametrize("target_device_id, target_module_id", targets)
    async def test_post_authorization_header_no_sas(
        self, client, target_device_id, target_module_id, method_params
    ):
        assert client._session.post.call_count == 0
        assert client._sastoken_provider is None

        await client.invoke_direct_method(
            device_id=target_device_id, module_id=target_module_id, method_params=method_params
        )

        assert client._session.post.call_count == 1
        headers = client._session.post.call_args[1]["headers"]
        assert "Authorization" not in headers

    @pytest.mark.it(
        "Fetches and returns the JSON payload of the HTTP response, if the HTTP request was successful"
    )
    @pytest.mark.parametrize("target_device_id, target_module_id", targets)
    async def test_returns_json_payload(
        self, client, target_device_id, target_module_id, method_params
    ):
        mock_response = client._session.post.return_value.__aenter__.return_value
        assert mock_response.status == 200

        method_response = await client.invoke_direct_method(
            device_id=target_device_id, module_id=target_module_id, method_params=method_params
        )

        assert method_response is mock_response.json.return_value

    @pytest.mark.it(
        "Raises an IoTEdgeError if a HTTP response is received with a failed status code"
    )
    @pytest.mark.parametrize("target_device_id, target_module_id", targets)
    @pytest.mark.parametrize("failed_status", failed_status_codes)
    async def test_failed_response(
        self, client, target_device_id, target_module_id, method_params, failed_status
    ):
        mock_response = client._session.post.return_value.__aenter__.return_value
        mock_response.status = failed_status

        with pytest.raises(IoTEdgeError):
            await client.invoke_direct_method(
                device_id=target_device_id, module_id=target_module_id, method_params=method_params
            )

    # NOTE: It'd be really great if we could reject non-Edge modules, but we can't.
    @pytest.mark.it("Raises IoTHubClientError if not configured as a Module")
    @pytest.mark.parametrize("target_device_id, target_module_id", targets)
    async def test_not_edge(self, client, target_device_id, target_module_id, method_params):
        client._module_id = None
        client._edge_module_id = None

        with pytest.raises(IoTHubClientError):
            await client.invoke_direct_method(
                device_id=target_device_id, module_id=target_module_id, method_params=method_params
            )

    @pytest.mark.it("Allows any exceptions raised by the POST request to propagate")
    @pytest.mark.parametrize("target_device_id, target_module_id", targets)
    @pytest.mark.parametrize("exception", http_post_exceptions)
    async def test_http_post_raises(
        self, client, target_device_id, target_module_id, method_params, exception
    ):
        client._session.post.side_effect = exception

        with pytest.raises(type(exception)) as e_info:
            await client.invoke_direct_method(
                device_id=target_device_id, module_id=target_module_id, method_params=method_params
            )
        assert e_info.value is exception

    @pytest.mark.it("Allows any exceptions raised while getting the JSON response to propagate")
    @pytest.mark.parametrize("target_device_id, target_module_id", targets)
    @pytest.mark.parametrize("exception", http_response_json_exceptions)
    async def test_http_response_json_raises(
        self, client, target_device_id, target_module_id, method_params, exception
    ):
        mock_response = client._session.post.return_value.__aenter__.return_value
        mock_response.json.side_effect = exception

        with pytest.raises(type(exception)) as e_info:
            await client.invoke_direct_method(
                device_id=target_device_id, module_id=target_module_id, method_params=method_params
            )
        assert e_info.value is exception

    @pytest.mark.it("Can be cancelled while waiting for the HTTP response")
    @pytest.mark.parametrize("target_device_id, target_module_id", targets)
    async def test_cancel_during_request(
        self, client, target_device_id, target_module_id, method_params
    ):
        post_ctx_manager = client._session.post.return_value
        post_ctx_manager.__aenter__ = custom_mock.HangingAsyncMock()

        t = asyncio.create_task(
            client.invoke_direct_method(
                device_id=target_device_id, module_id=target_module_id, method_params=method_params
            )
        )

        # Hanging, waiting for response
        await post_ctx_manager.__aenter__.wait_for_hang()
        assert not t.done()

        # Cancel
        t.cancel()
        with pytest.raises(asyncio.CancelledError):
            await t

    @pytest.mark.it("Can be cancelled while fetching the payload of the HTTP response")
    @pytest.mark.parametrize("target_device_id, target_module_id", targets)
    async def test_cancel_during_payload_fetch(
        self, client, target_device_id, target_module_id, method_params
    ):
        response = client._session.post.return_value.__aenter__.return_value
        response.json = custom_mock.HangingAsyncMock()

        t = asyncio.create_task(
            client.invoke_direct_method(
                device_id=target_device_id, module_id=target_module_id, method_params=method_params
            )
        )

        # Hanging, waiting to fetch JSON
        await response.json.wait_for_hang()
        assert not t.done()

        # Cancel
        t.cancel()
        with pytest.raises(asyncio.CancelledError):
            await t


@pytest.mark.describe("IoTHubHTTPClient - .get_storage_info_for_blob")
class TestIoTHubHTTPClientGetStorageInfoForBlob:
    @pytest.fixture(autouse=True)
    def modify_client_config(self, client_config):
        """Modify the client config to always be a Device"""
        client_config.device_id = FAKE_DEVICE_ID
        client_config.module_id = None

    @pytest.fixture(autouse=True)
    def modify_post_response(self, client):
        fake_storage_info = {
            "correlationId": FAKE_CORRELATION_ID,
            "hostName": "fakeblobstorage.blob.core.windows.net",
            "containerName": "fakeblobcontainer",
            "blobName": "fake_device_id/fake_blob",
            "sasToken": "?sv=2018-03-28&sr=b&sig=9x00K4bgLhiif0mVPTXRL8axz4yPG32LvnpVhwW4IfQ%3D&se=2023-02-22T05%3A39%3A49Z&sp=rw",
        }
        mock_response = client._session.post.return_value.__aenter__.return_value
        mock_response.json.return_value = fake_storage_info

    @pytest.mark.it(
        "Does an asynchronous POST request operation to the relative 'get storage info' path using the aiohttp ClientSession and the stored SSL context"
    )
    async def test_http_post(self, mocker, client):
        post_ctx_manager = client._session.post.return_value
        assert client._session.post.call_count == 0
        assert post_ctx_manager.__aenter__.await_count == 0
        expected_path = http_path.get_storage_info_for_blob_path(client._device_id)

        await client.get_storage_info_for_blob(blob_name="fake_blob")

        assert client._session.post.call_count == 1
        assert client._session.post.call_args == mocker.call(
            url=expected_path,
            json=mocker.ANY,
            params=mocker.ANY,
            headers=mocker.ANY,
            ssl=client._ssl_context,
        )
        assert post_ctx_manager.__aenter__.await_count == 1
        assert post_ctx_manager.__aenter__.await_args == mocker.call()

    @pytest.mark.it("Sends the provided `blob_name` with the POST request inside a JSON payload")
    async def test_post_json(self, mocker, client):
        assert client._session.post.call_count == 0
        expected_json = {"blobName": "fake_blob"}

        await client.get_storage_info_for_blob(blob_name="fake_blob")

        assert client._session.post.call_count == 1
        assert client._session.post.call_args == mocker.call(
            url=mocker.ANY,
            json=expected_json,
            params=mocker.ANY,
            headers=mocker.ANY,
            ssl=mocker.ANY,
        )

    @pytest.mark.it("Sends the API version with the POST request as a query parameter")
    async def test_post_query_params(self, mocker, client):
        assert client._session.post.call_count == 0
        expected_params = {"api-version": constant.IOTHUB_API_VERSION}

        await client.get_storage_info_for_blob(blob_name="fake_blob")

        assert client._session.post.call_count == 1
        assert client._session.post.call_args == mocker.call(
            url=mocker.ANY,
            json=mocker.ANY,
            params=expected_params,
            headers=mocker.ANY,
            ssl=mocker.ANY,
        )

    @pytest.mark.it(
        "Sets the 'User-Agent' HTTP header on the POST request to the URL-encoded `user_agent` value stored on the client"
    )
    async def test_post_user_agent_header(self, client):
        assert client._session.post.call_count == 0
        expected_user_agent = urllib.parse.quote_plus(client._user_agent_string)
        assert expected_user_agent != client._user_agent_string

        await client.get_storage_info_for_blob(blob_name="fake_blob")

        assert client._session.post.call_count == 1
        headers = client._session.post.call_args[1]["headers"]
        assert headers["User-Agent"] == expected_user_agent

    @pytest.mark.it(
        "Sets the 'Authorization' HTTP header on the POST request to the current SAS Token string from the SasTokenProvider stored on the client, if it exists"
    )
    async def test_post_authorization_header_sas(self, client, mock_sastoken_provider):
        assert client._session.post.call_count == 0
        client._sastoken_provider = mock_sastoken_provider
        assert mock_sastoken_provider.get_current_sastoken.call_count == 0
        expected_sastoken_string = str(mock_sastoken_provider.get_current_sastoken.return_value)

        await client.get_storage_info_for_blob(blob_name="fake_blob")

        assert client._session.post.call_count == 1
        headers = client._session.post.call_args[1]["headers"]
        assert headers["Authorization"] == expected_sastoken_string

    @pytest.mark.it(
        "Does not include an 'Authorization' HTTP header on the POST request if not using SAS Token authentication"
    )
    async def test_post_authorization_header_no_sas(self, client):
        assert client._session.post.call_count == 0
        assert client._sastoken_provider is None

        await client.get_storage_info_for_blob(blob_name="fake_blob")

        assert client._session.post.call_count == 1
        headers = client._session.post.call_args[1]["headers"]
        assert "Authorization" not in headers

    @pytest.mark.it(
        "Fetches and returns the JSON payload of the HTTP response, if the HTTP request was successful"
    )
    async def test_returns_json_payload(self, client):
        mock_response = client._session.post.return_value.__aenter__.return_value
        assert mock_response.status == 200

        storage_info = await client.get_storage_info_for_blob(blob_name="fake_blob")

        assert storage_info is mock_response.json.return_value

    @pytest.mark.it(
        "Raises an IoTHubError if a HTTP response is received with a failed status code"
    )
    @pytest.mark.parametrize("failed_status", failed_status_codes)
    async def test_failed_response(self, client, failed_status):
        mock_response = client._session.post.return_value.__aenter__.return_value
        mock_response.status = failed_status

        with pytest.raises(IoTHubError):
            await client.get_storage_info_for_blob(blob_name="fake_blob")

    @pytest.mark.it("Raises IoTHubClientError if not configured as a Device")
    @pytest.mark.parametrize(
        "edge_module_id",
        [
            pytest.param(None, id="Module Configuration"),
            pytest.param(FAKE_DEVICE_ID + "/" + FAKE_MODULE_ID, id="Edge Module Configuration"),
        ],
    )
    async def test_not_device(self, client, edge_module_id):
        assert client._device_id is not None
        client._module_id = FAKE_MODULE_ID
        client._edge_module_id = edge_module_id

        with pytest.raises(IoTHubClientError):
            await client.get_storage_info_for_blob(blob_name="some blob")

    @pytest.mark.it("Allows any exceptions raised by the POST request to propagate")
    @pytest.mark.parametrize("exception", http_post_exceptions)
    async def test_http_post_raises(self, client, exception):
        client._session.post.side_effect = exception

        with pytest.raises(type(exception)) as e_info:
            await client.get_storage_info_for_blob(blob_name="some blob")
        assert e_info.value is exception

    @pytest.mark.it("Allows any exceptions raised while getting the JSON response to propagate")
    @pytest.mark.parametrize("exception", http_response_json_exceptions)
    async def test_http_response_json_raises(self, client, exception):
        mock_response = client._session.post.return_value.__aenter__.return_value
        mock_response.json.side_effect = exception

        with pytest.raises(type(exception)) as e_info:
            await client.get_storage_info_for_blob(blob_name="some blob")
        assert e_info.value is exception

    @pytest.mark.it("Can be cancelled while waiting for the HTTP response")
    async def test_cancel_during_request(self, client):
        post_ctx_manager = client._session.post.return_value
        post_ctx_manager.__aenter__ = custom_mock.HangingAsyncMock()

        t = asyncio.create_task(client.get_storage_info_for_blob(blob_name="some blob"))

        # Hanging, waiting for response
        await post_ctx_manager.__aenter__.wait_for_hang()
        assert not t.done()

        # Cancel
        t.cancel()
        with pytest.raises(asyncio.CancelledError):
            await t

    @pytest.mark.it("Can be cancelled while fetching the payload of the HTTP response")
    async def test_cancel_during_payload_fetch(self, client):
        response = client._session.post.return_value.__aenter__.return_value
        response.json = custom_mock.HangingAsyncMock()

        t = asyncio.create_task(client.get_storage_info_for_blob(blob_name="some blob"))

        # Hanging, waiting to fetch JSON
        await response.json.wait_for_hang()
        assert not t.done()

        # Cancel
        t.cancel()
        with pytest.raises(asyncio.CancelledError):
            await t


@pytest.mark.describe("IoTHubHTTPClient - .notify_blob_upload_status")
class TestIoTHubHTTPClientNotifyBlobUploadStatus:
    @pytest.fixture(autouse=True)
    def modify_client_config(self, client_config):
        """Modify the client config to always be a Device"""
        client_config.device_id = FAKE_DEVICE_ID
        client_config.module_id = None

    @pytest.fixture(params=["Notify Upload Success", "Notify Upload Failure"])
    def kwargs(self, request):
        """Because there are correlated semantics across a set of given arguments, using a fixture
        just makes things easier
        """
        if request.param == "Notify Upload Success":
            kwargs = {
                "correlation_id": FAKE_CORRELATION_ID,
                "is_success": True,
                "status_code": 200,
                "status_description": "Success!",
            }
        else:
            kwargs = {
                "correlation_id": FAKE_CORRELATION_ID,
                "is_success": False,
                "status_code": 500,
                "status_description": "Failure!",
            }
        return kwargs

    @pytest.mark.it(
        "Does an asynchronous POST request operation to the relative 'notify blob upload status' path using the aiohttp ClientSession and the stored SSL context"
    )
    async def test_http_post(self, mocker, client, kwargs):
        post_ctx_manager = client._session.post.return_value
        assert client._session.post.call_count == 0
        assert post_ctx_manager.__aenter__.await_count == 0
        expected_path = http_path.get_notify_blob_upload_status_path(client._device_id)

        await client.notify_blob_upload_status(**kwargs)

        assert client._session.post.call_count == 1
        assert client._session.post.call_args == mocker.call(
            url=expected_path,
            json=mocker.ANY,
            params=mocker.ANY,
            headers=mocker.ANY,
            ssl=client._ssl_context,
        )
        assert post_ctx_manager.__aenter__.await_count == 1
        assert post_ctx_manager.__aenter__.await_args == mocker.call()

    @pytest.mark.it("Sends all the provided parameters with the POST request inside a JSON payload")
    async def test_post_json(self, mocker, client, kwargs):
        assert client._session.post.call_count == 0
        expected_json = {
            "correlationId": kwargs["correlation_id"],
            "isSuccess": kwargs["is_success"],
            "statusCode": kwargs["status_code"],
            "statusDescription": kwargs["status_description"],
        }

        await client.notify_blob_upload_status(**kwargs)

        assert client._session.post.call_count == 1
        assert client._session.post.call_args == mocker.call(
            url=mocker.ANY,
            json=expected_json,
            params=mocker.ANY,
            headers=mocker.ANY,
            ssl=mocker.ANY,
        )

    @pytest.mark.it("Sends the API version with the POST request as a query parameter")
    async def test_post_query_params(self, mocker, client, kwargs):
        assert client._session.post.call_count == 0
        expected_params = {"api-version": constant.IOTHUB_API_VERSION}

        await client.notify_blob_upload_status(**kwargs)

        assert client._session.post.call_count == 1
        assert client._session.post.call_args == mocker.call(
            url=mocker.ANY,
            json=mocker.ANY,
            params=expected_params,
            headers=mocker.ANY,
            ssl=mocker.ANY,
        )

    @pytest.mark.it(
        "Sets the 'User-Agent' HTTP header on the POST request to the URL-encoded `user_agent` value stored on the client"
    )
    async def test_post_user_agent_header(self, client, kwargs):
        assert client._session.post.call_count == 0
        expected_user_agent = urllib.parse.quote_plus(client._user_agent_string)
        assert expected_user_agent != client._user_agent_string

        await client.notify_blob_upload_status(**kwargs)

        assert client._session.post.call_count == 1
        headers = client._session.post.call_args[1]["headers"]
        assert headers["User-Agent"] == expected_user_agent

    @pytest.mark.it(
        "Sets the 'Authorization' HTTP header on the POST request to the current SAS Token string from the SasTokenProvider stored on the client, if it exists"
    )
    async def test_post_authorization_header_sas(self, client, kwargs, mock_sastoken_provider):
        assert client._session.post.call_count == 0
        client._sastoken_provider = mock_sastoken_provider
        assert mock_sastoken_provider.get_current_sastoken.call_count == 0
        expected_sastoken_string = str(mock_sastoken_provider.get_current_sastoken.return_value)

        await client.notify_blob_upload_status(**kwargs)

        assert client._session.post.call_count == 1
        headers = client._session.post.call_args[1]["headers"]
        assert headers["Authorization"] == expected_sastoken_string

    @pytest.mark.it(
        "Does not include an 'Authorization' HTTP header on the POST request if not using SAS Token authentication"
    )
    async def test_post_authorization_header_no_sas(self, client, kwargs):
        assert client._session.post.call_count == 0
        assert client._sastoken_provider is None

        await client.notify_blob_upload_status(**kwargs)

        assert client._session.post.call_count == 1
        headers = client._session.post.call_args[1]["headers"]
        assert "Authorization" not in headers

    @pytest.mark.it("Does not return a value")
    async def test_return_value(self, client, kwargs):
        retval = await client.notify_blob_upload_status(**kwargs)
        assert retval is None

    @pytest.mark.it(
        "Raises an IoTHubError if a HTTP response is received with a failed status code"
    )
    @pytest.mark.parametrize("failed_status", failed_status_codes)
    async def test_failed_response(self, client, kwargs, failed_status):
        mock_response = client._session.post.return_value.__aenter__.return_value
        mock_response.status = failed_status

        with pytest.raises(IoTHubError):
            await client.notify_blob_upload_status(**kwargs)

    @pytest.mark.it("Raises IoTHubClientError if not configured as a Device")
    @pytest.mark.parametrize(
        "edge_module_id",
        [
            pytest.param(None, id="Module Configuration"),
            pytest.param(FAKE_DEVICE_ID + "/" + FAKE_MODULE_ID, id="Edge Module Configuration"),
        ],
    )
    async def test_not_device(self, client, kwargs, edge_module_id):
        assert client._device_id is not None
        client._module_id = FAKE_MODULE_ID
        client._edge_module_id = edge_module_id

        with pytest.raises(IoTHubClientError):
            await client.notify_blob_upload_status(**kwargs)

    @pytest.mark.it("Allows any exceptions raised by the POST request to propagate")
    @pytest.mark.parametrize("exception", http_post_exceptions)
    async def test_http_post_raises(self, client, kwargs, exception):
        client._session.post.side_effect = exception

        with pytest.raises(type(exception)) as e_info:
            await client.notify_blob_upload_status(**kwargs)
        assert e_info.value is exception

    @pytest.mark.it("Can be cancelled while waiting for the HTTP response")
    async def test_cancel_during_request(self, client, kwargs):
        post_ctx_manager = client._session.post.return_value
        post_ctx_manager.__aenter__ = custom_mock.HangingAsyncMock()

        t = asyncio.create_task(client.notify_blob_upload_status(**kwargs))

        # Hanging, waiting for response
        await post_ctx_manager.__aenter__.wait_for_hang()
        assert not t.done()

        # Cancel
        t.cancel()
        with pytest.raises(asyncio.CancelledError):
            await t
