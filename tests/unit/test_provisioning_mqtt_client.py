# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import asyncio
import json
import uuid

import pytest
import ssl
import sys
import time

import urllib
from pytest_lazyfixture import lazy_fixture
from dev_utils import custom_mock
from azure.iot.device.provisioning_mqtt_client import (
    ProvisioningMQTTClient,
    DEFAULT_RECONNECT_INTERVAL,
    DEFAULT_POLLING_INTERVAL,
    DEFAULT_TIMEOUT_INTERVAL,
)

from azure.iot.device.iot_exceptions import ProvisioningServiceError
from azure.iot.device import config, constant, user_agent
from azure.iot.device import mqtt_client as mqtt
from azure.iot.device import request_response as rr
from azure.iot.device import mqtt_topic_provisioning as mqtt_topic
from azure.iot.device import sastoken as st


FAKE_REGISTER_REQUEST_ID = "fake_register_request_id"
FAKE_POLLING_REQUEST_ID = "fake_polling_request_id"
FAKE_REGISTRATION_ID = "fake_registration_id"
FAKE_ID_SCOPE = "fake_idscope"
FAKE_HOSTNAME = "fake.hostname"
FAKE_SIGNATURE = "ajsc8nLKacIjGsYyB4iYDFCZaRMmmDrUuY5lncYDYPI="
FAKE_EXPIRY = str(int(time.time()) + 3600)
FAKE_URI = "fake/resource/location"
FAKE_STATUS = "assigned"
FAKE_SUB_STATUS = "OK"
FAKE_OPERATION_ID = "fake_operation_id"
FAKE_DEVICE_ID = "MyDevice"
FAKE_ASSIGNED_HUB = "MyIoTHub"

# Parametrization
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
    """Defaults to DPS Configuration. Required values only.
    Customize in test if you need specific options"""
    client_config = config.ProvisioningClientConfig(
        registration_id=FAKE_REGISTRATION_ID,
        hostname=FAKE_HOSTNAME,
        id_scope=FAKE_ID_SCOPE,
        ssl_context=ssl.SSLContext(),
    )
    return client_config


@pytest.fixture
async def client(mocker, client_config):
    client = ProvisioningMQTTClient(client_config)
    # Mock just the network operations from the MQTTClient, not the whole thing.
    # This makes using the generators easier
    client._mqtt_client.connect = mocker.AsyncMock()
    client._mqtt_client.disconnect = mocker.AsyncMock()
    client._mqtt_client.subscribe = mocker.AsyncMock()
    client._mqtt_client.unsubscribe = mocker.AsyncMock()
    client._mqtt_client.publish = mocker.AsyncMock()
    # Also mock the set credentials method since we test that
    client._mqtt_client.set_credentials = mocker.MagicMock()
    client._mqtt_client.is_connected = mocker.MagicMock()

    # NOTE: No need to invoke .start() here, at least, not yet.
    return client


@pytest.mark.describe("ProvisioningMQTTClient -- Instantiation")
class TestProvisioningMQTTClientInstantiation:
    @pytest.mark.it("Stores the `registration_id` from the ProvisioningClientConfig as attributes")
    async def test_simple_ids(self, client_config):
        client = ProvisioningMQTTClient(client_config)
        assert client._registration_id == client_config.registration_id

    @pytest.mark.it("Derives the `username` and stores the result as an attribute")
    async def test_username(
        self,
        client_config,
    ):
        client_config.registration_id = FAKE_REGISTRATION_ID
        client_config.id_scope = FAKE_ID_SCOPE

        ua = user_agent.get_provisioning_user_agent()
        url_encoded_user_agent = urllib.parse.quote(ua, safe="")
        # NOTE: This assertion shows the URL encoding was meaningful
        assert user_agent != url_encoded_user_agent
        expected_username = "{id_scope}/registrations/{registration_id}/api-version={api_version}&ClientVersion={user_agent}".format(
            id_scope=client_config.id_scope,
            registration_id=client_config.registration_id,
            api_version=constant.PROVISIONING_API_VERSION,
            user_agent=url_encoded_user_agent,
        )
        client = ProvisioningMQTTClient(client_config)
        # The expected username was derived
        assert client._username == expected_username

    @pytest.mark.it(
        "Stores the `sastoken_provider` from the ProvisioningClientConfig as an attribute"
    )
    @pytest.mark.parametrize(
        "sastoken_provider",
        [
            pytest.param(lazy_fixture("mock_sastoken_provider"), id="SasTokenProvider present"),
            pytest.param(None, id="No SasTokenProvider present"),
        ],
    )
    async def test_sastoken_provider(self, client_config, sastoken_provider):
        client_config.registration_id = FAKE_REGISTRATION_ID
        client_config.sastoken_provider = sastoken_provider

        client = ProvisioningMQTTClient(client_config)
        assert client._sastoken_provider is sastoken_provider

    @pytest.mark.it(
        "Creates an MQTTClient instance based on the configuration of ProvisioningClientConfig and stores it as an attribute"
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
        websockets,
        expected_transport,
        expected_port,
        expected_ws_path,
    ):
        # Configure the client_config based on params
        client_config.registration_id = FAKE_REGISTRATION_ID
        client_config.websockets = websockets

        # Patch the MQTTClient constructor
        mock_constructor = mocker.patch.object(mqtt, "MQTTClient", spec=mqtt.MQTTClient)
        assert mock_constructor.call_count == 0

        # Create the client under test
        client = ProvisioningMQTTClient(client_config)

        # Assert that the MQTTClient was constructed as expected
        assert mock_constructor.call_count == 1
        assert mock_constructor.call_args == mocker.call(
            client_id=client_config.registration_id,
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
        assert client._mqtt_client is mock_constructor.return_value

    @pytest.mark.it("Adds incoming message filter on the MQTTClient for dps responses")
    async def test_dps_response_filter(self, mocker, client_config):
        client_config.registration_id = FAKE_REGISTRATION_ID
        expected_topic = mqtt_topic.get_response_topic_for_subscribe()

        mocker.patch.object(mqtt, "MQTTClient", spec=mqtt.MQTTClient)
        client = ProvisioningMQTTClient(client_config)

        # NOTE: Multiple filters are added, but not all are covered in this test
        assert (
            mocker.call(expected_topic)
            in client._mqtt_client.add_incoming_message_filter.call_args_list
        )

    @pytest.mark.it("Creates an empty RequestLedger")
    async def test_request_ledger(self, client_config):
        client_config.registration_id = FAKE_REGISTRATION_ID
        client = ProvisioningMQTTClient(client_config)
        assert isinstance(client._request_ledger, rr.RequestLedger)
        assert len(client._request_ledger) == 0

    @pytest.mark.it("Sets the _register_responses_enabled flag to False")
    async def test_dps_responses_enabled(self, client_config):
        client_config.registration_id = FAKE_REGISTRATION_ID
        client = ProvisioningMQTTClient(client_config)
        assert client._register_responses_enabled is False

    @pytest.mark.it("Sets background task attributes to None")
    async def test_bg_tasks(self, client_config):
        client_config.registration_id = FAKE_REGISTRATION_ID
        client = ProvisioningMQTTClient(client_config)
        assert client._process_dps_responses_task is None


@pytest.mark.describe("ProvisioningMQTTClient - .start()")
class TestProvisioningMQTTClientStart:
    @pytest.mark.it(
        "Sets the credentials on the MQTTClient, using the stored `username` as the username and no password, "
        "when not using SAS authentication"
    )
    async def test_mqtt_client_credentials_no_sas(self, mocker, client):
        assert client._sastoken_provider is None
        assert client._mqtt_client.set_credentials.call_count == 0

        await client.start()

        assert client._mqtt_client.set_credentials.call_count == 1
        assert client._mqtt_client.set_credentials.call_args == mocker.call(client._username, None)

        # Cleanup
        await client.stop()

    @pytest.mark.it(
        "Sets the credentials on the MQTTClient, using the stored `username` as the username and the string-converted "
        "current SasToken from the SasTokenProvider as the password, when using SAS authentication"
    )
    async def test_mqtt_client_credentials_with_sas(self, client, mock_sastoken_provider):
        client._sastoken_provider = mock_sastoken_provider
        fake_sastoken = mock_sastoken_provider.get_current_sastoken.return_value
        assert client._mqtt_client.set_credentials.call_count == 0

        await client.start()

        assert client._mqtt_client.set_credentials.call_count == 1
        assert client._mqtt_client.set_credentials.call_args(client._username, str(fake_sastoken))

        await client.stop()

    @pytest.mark.it(
        "Begins running the ._process_dps_responses_task() coroutine method as a background task, storing it as an attribute"
    )
    async def test_process_dps_responses_bg_task(self, client):
        assert client._process_dps_responses_task is None

        await client.start()

        assert isinstance(client._process_dps_responses_task, asyncio.Task)
        assert not client._process_dps_responses_task.done()
        if sys.version_info > (3, 8):
            # NOTE: There isn't a way to validate the contents of a task until 3.8
            # as far as I can tell.
            task_coro = client._process_dps_responses_task.get_coro()
            assert task_coro.__qualname__ == "ProvisioningMQTTClient._process_dps_responses"

        # Cleanup
        await client.stop()


@pytest.mark.describe("ProvisioningMQTTClient - .stop()")
class TestProvisioningMQTTClientStop:
    @pytest.fixture(autouse=True)
    async def modify_client(self, client, mock_sastoken_provider):
        client._sastoken_provider = mock_sastoken_provider
        # Need to start the client so we can stop it.
        await client.start()

    @pytest.mark.it("Disconnects the MQTTClient")
    async def test_disconnect(self, mocker, client):
        # NOTE: rather than mocking the MQTTClient, we just mock the .disconnect() method of the
        # ProvisioningMQTTClient instead, since it's been fully tested elsewhere, and we assume
        # correctness, lest we have to repeat all .disconnect() tests here.
        original_disconnect = client.disconnect
        client.disconnect = mocker.AsyncMock()
        try:
            assert client.disconnect.await_count == 0

            await client.stop()

            assert client.disconnect.await_count == 1
            assert client.disconnect.await_args == mocker.call()
        finally:
            client.disconnect = original_disconnect

    @pytest.mark.it(
        "Cancels the 'process_dps_responses' background task and removes it, if it exists"
    )
    async def test_process_dps_responses_bg_task(self, client):
        assert isinstance(client._process_dps_responses_task, asyncio.Task)
        t = client._process_dps_responses_task
        assert not t.done()

        await client.stop()

        assert t.done()
        assert t.cancelled()
        assert client._process_dps_responses_task is None

    # NOTE: Currently this is an invalid scenario. This shouldn't happen, but test it anyway.
    @pytest.mark.it("Handles the case where no 'process_dps_responses' background task exists")
    async def test_process_dps_responses_bg_task_no_exist(self, client):
        # The task is already running, so cancel and remove it
        assert isinstance(client._process_dps_responses_task, asyncio.Task)
        client._process_dps_responses_task.cancel()
        client._process_dps_responses_task = None

        await client.stop()
        # No AttributeError means success!

    @pytest.mark.it(
        "Allows any exception raised during MQTTClient disconnect to propagate, but only after cancelling background tasks"
    )
    @pytest.mark.parametrize("exception", mqtt_disconnect_exceptions)
    async def test_disconnect_raises(self, mocker, client, exception):
        # NOTE: rather than mocking the MQTTClient, we just mock the .disconnect() method of the
        # ProvisioningMQTTClient instead, since it's been fully tested elsewhere, and we assume
        # correctness, lest we have to repeat all .disconnect() tests here.
        original_disconnect = client.disconnect
        client.disconnect = mocker.AsyncMock(side_effect=exception)
        try:
            process_dps_responses_bg_task = client._process_dps_responses_task
            assert not process_dps_responses_bg_task.done()

            with pytest.raises(type(exception)) as e_info:
                await client.stop()
            assert e_info.value is exception

            # Background tasks were also cancelled despite the exception
            assert process_dps_responses_bg_task.done()
            assert process_dps_responses_bg_task.cancelled()
            # And they were unset too
            assert client._process_dps_responses_task is None
        finally:
            # Unset the mock so that tests can clean up
            client.disconnect = original_disconnect

    # TODO: when run by itself, this test leaves a task unresolved. Not sure why. Not too important.
    @pytest.mark.it(
        "Does not alter any background tasks if already stopped, but does disconnect again"
    )
    async def test_already_stopped(self, mocker, client):
        original_disconnect = client.disconnect
        client.disconnect = mocker.AsyncMock()
        try:
            assert client.disconnect.await_count == 0

            # Stop
            await client.stop()
            assert client._process_dps_responses_task is None
            assert client.disconnect.await_count == 1

            # Stop again
            await client.stop()
            assert client._process_dps_responses_task is None
            assert client.disconnect.await_count == 2

        finally:
            client.disconnect = original_disconnect

    # TODO: when run by itself, this test leaves a task unresolved. Not sure why. Not too important.
    @pytest.mark.it(
        "Can be cancelled while waiting for the MQTTClient disconnect to finish, but it won't stop background task cancellation"
    )
    async def test_cancel_disconnect(self, client):
        # NOTE: rather than mocking the MQTTClient, we just mock the .disconnect() method of the
        # ProvisioningMQTTClient instead, since it's been fully tested elsewhere, and we assume
        # correctness, lest we have to repeat all .disconnect() tests here.
        original_disconnect = client.disconnect
        client.disconnect = custom_mock.HangingAsyncMock()
        try:

            process_dps_responses_bg_task = client._process_dps_responses_task
            assert not process_dps_responses_bg_task.done()

            t = asyncio.create_task(client.stop())

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
            assert process_dps_responses_bg_task.done()
            assert process_dps_responses_bg_task.cancelled()
            # And they were unset too
            assert client._process_dps_responses_task is None
        finally:
            # Unset the mock so that tests can clean up.
            client.disconnect = original_disconnect

    @pytest.mark.it(
        "Can be cancelled while waiting for the background tasks to finish cancellation, but it won't stop the background task cancellation"
    )
    async def test_cancel_gather(self, mocker, client):
        original_gather = asyncio.gather
        asyncio.gather = custom_mock.HangingAsyncMock()
        spy_register_dps_response_bg_task_cancel = mocker.spy(
            client._process_dps_responses_task, "cancel"
        )
        try:
            process_dps_responses_bg_task = client._process_dps_responses_task
            assert not process_dps_responses_bg_task.done()

            t = asyncio.create_task(client.stop())

            # Hanging waiting for gather to return (indicating tasks are all done cancellation)
            await asyncio.gather.wait_for_hang()
            assert not t.done()
            # Background tests may or may not have completed cancellation yet, hard to test accurately.
            # But their cancellation HAS been requested.
            assert spy_register_dps_response_bg_task_cancel.call_count == 1

            # Cancel
            t.cancel()
            with pytest.raises(asyncio.CancelledError):
                await t

            # Tasks will be cancelled very soon (if they aren't already)
            await asyncio.sleep(0.1)
            assert process_dps_responses_bg_task.done()
            assert process_dps_responses_bg_task.cancelled()
            # And they were unset too
            assert client._process_dps_responses_task is None
        finally:
            # Unset the mock so that tests can clean up.
            asyncio.gather = original_gather


@pytest.mark.describe("ProvisioningMQTTClient - .connect()")
class TestProvisioningMQTTClientConnect:
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


@pytest.mark.describe("ProvisioningMQTTClient - .disconnect()")
class TestProvisioningMQTTClientDisconnect:
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


@pytest.mark.describe("ProvisioningMQTTClient - .send_register()")
class TestProvisioningMQTTClientSendRegister:
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
            response_body_dict = {
                "operationId": FAKE_OPERATION_ID,
                "status": FAKE_STATUS,
                "registrationState": {"registrationId": FAKE_REGISTRATION_ID},
            }
            response = rr.Response(rid, 200, json.dumps(response_body_dict))
            await client._request_ledger.match_response(response)

        client._mqtt_client.publish.side_effect = fake_publish

    @pytest.mark.it(
        "Awaits a subscribe to the register dps response topic using the MQTTClient, if register dps responses have not already been enabled"
    )
    @pytest.mark.parametrize(
        "registration_payload",
        [
            pytest.param('{"text": "this is registration payload"}', id="Some payload"),
            pytest.param(None, id="No payload"),
        ],
    )
    async def test_mqtt_subscribe_not_enabled(self, mocker, client, registration_payload):
        assert client._mqtt_client.subscribe.await_count == 0
        assert client._register_responses_enabled is False
        expected_topic = mqtt_topic.get_response_topic_for_subscribe()

        await client.send_register(payload=registration_payload)

        assert client._mqtt_client.subscribe.await_count == 1
        assert client._mqtt_client.subscribe.await_args == mocker.call(expected_topic)

    @pytest.mark.it(
        "Does not perform a subscribe if register dps responses have already been enabled"
    )
    @pytest.mark.parametrize(
        "registration_payload",
        [
            pytest.param('{"text": "this is registration payload"}', id="Some payload"),
            pytest.param(None, id="No payload"),
        ],
    )
    async def test_mqtt_subscribe_already_enabled(self, client, registration_payload):
        assert client._mqtt_client.subscribe.await_count == 0
        client._register_responses_enabled = True

        await client.send_register(payload=registration_payload)

        assert client._mqtt_client.subscribe.call_count == 0

    @pytest.mark.it("Sets the register_responses_enabled flag to True upon subscribe success")
    @pytest.mark.parametrize(
        "registration_payload",
        [
            pytest.param('{"text": "this is registration payload"}', id="Some payload"),
            pytest.param(None, id="No payload"),
        ],
    )
    async def test_response_enabled_flag_success(self, client, registration_payload):
        assert client._register_responses_enabled is False

        await client.send_register(payload=registration_payload)

        assert client._register_responses_enabled is True

    @pytest.mark.it("Generates a new Request, using the RequestLedger stored on the client")
    @pytest.mark.parametrize(
        "responses_enabled",
        [
            pytest.param(True, id="Register Responses Already Enabled"),
            pytest.param(False, id="Register Responses Not Yet Enabled"),
        ],
    )
    @pytest.mark.parametrize(
        "registration_payload",
        [
            pytest.param('{"text": "this is registration payload"}', id="Some payload"),
            pytest.param(None, id="No payload"),
        ],
    )
    async def test_generate_request(self, mocker, client, responses_enabled, registration_payload):
        client._register_responses_enabled = responses_enabled
        spy_create_request = mocker.spy(client._request_ledger, "create_request")

        # Mock the uuid call as well to return fake request id
        mocker.patch.object(uuid, "uuid4", return_value=FAKE_REGISTER_REQUEST_ID)

        await client.send_register(payload=registration_payload)

        assert spy_create_request.await_count == 1
        assert spy_create_request.await_args == mocker.call(FAKE_REGISTER_REQUEST_ID)

    @pytest.mark.it("Awaits a publish to the register request topic using the MQTTClient")
    @pytest.mark.parametrize(
        "responses_enabled",
        [
            pytest.param(True, id="Register Responses Already Enabled"),
            pytest.param(False, id="Register Responses Not Yet Enabled"),
        ],
    )
    @pytest.mark.parametrize(
        "registration_payload",
        [
            pytest.param('{"text": "this is registration payload"}', id="Some payload"),
            pytest.param(None, id="No payload"),
        ],
    )
    async def test_mqtt_publish(self, mocker, client, responses_enabled, registration_payload):
        client._register_responses_enabled = responses_enabled
        spy_create_request = mocker.spy(client._request_ledger, "create_request")
        assert client._mqtt_client.publish.await_count == 0

        await client.send_register(payload=registration_payload)

        request = spy_create_request.spy_return
        expected_topic = mqtt_topic.get_register_topic_for_publish(request.request_id)
        payload_dict = {"payload": registration_payload, "registrationId": FAKE_REGISTRATION_ID}
        expected_payload = json.dumps(payload_dict)

        assert client._mqtt_client.publish.await_count == 1
        assert client._mqtt_client.publish.await_args == mocker.call(
            expected_topic, expected_payload
        )

    @pytest.mark.it("Awaits a received Response to the Request")
    @pytest.mark.parametrize(
        "responses_enabled",
        [
            pytest.param(True, id="Register Responses Already Enabled"),
            pytest.param(False, id="Register Responses Not Yet Enabled"),
        ],
    )
    @pytest.mark.parametrize(
        "registration_payload",
        [
            pytest.param('{"text": "this is registration payload"}', id="Some payload"),
            pytest.param(None, id="No payload"),
        ],
    )
    async def test_get_response(self, mocker, client, responses_enabled, registration_payload):
        client._register_responses_enabled = responses_enabled
        # Override autocompletion behavior on publish (we don't want it here)
        client._mqtt_client.publish = mocker.AsyncMock()
        # Mock out the ledger to return a mocked request
        mock_request = mocker.MagicMock(spec=rr.Request)
        mock_request.request_id = FAKE_REGISTER_REQUEST_ID  # Need this for string manipulation
        mocker.patch.object(client._request_ledger, "create_request", return_value=mock_request)
        # Mock out the request to return a response
        mock_response = mocker.MagicMock(spec=rr.Response)
        mock_response.status = 200
        response_body_dict = {
            "operationId": FAKE_OPERATION_ID,
            "status": FAKE_STATUS,
            "registrationState": {"registrationId": FAKE_REGISTRATION_ID},
        }
        mock_response.body = json.dumps(response_body_dict)
        mock_request.get_response.return_value = mock_response

        await client.send_register(payload=registration_payload)

        assert mock_request.get_response.await_count == 1
        assert mock_request.get_response.await_args == mocker.call()

    @pytest.mark.it(
        "Raises an ProvisioningServiceError if an unsuccessful status (300-429) is received via the Response"
    )
    @pytest.mark.parametrize(
        "responses_enabled",
        [
            pytest.param(True, id="Register Responses Already Enabled"),
            pytest.param(False, id="Register Responses Not Yet Enabled"),
        ],
    )
    @pytest.mark.parametrize(
        "failed_status",
        [
            pytest.param(300, id="Status Code: 300"),
            pytest.param(400, id="Status Code: 400"),
            pytest.param(428, id="Status Code: 428"),
        ],
    )
    @pytest.mark.parametrize(
        "registration_payload",
        [
            pytest.param('{"text": "this is registration payload"}', id="Some payload"),
            pytest.param(None, id="No payload"),
        ],
    )
    async def test_failed_response(
        self, mocker, client, responses_enabled, failed_status, registration_payload
    ):
        client._register_responses_enabled = responses_enabled
        # Override autocompletion behavior on publish (we don't need it here)
        client._mqtt_client.publish = mocker.AsyncMock()
        # Mock out the ledger to return a mocked request
        mock_request = mocker.MagicMock(spec=rr.Request)
        mock_request.request_id = FAKE_REGISTER_REQUEST_ID  # Need this for string manipulation
        mocker.patch.object(client._request_ledger, "create_request", return_value=mock_request)
        # Mock out the request to return a response
        mock_response = mocker.MagicMock(spec=rr.Response)
        mock_response.status = failed_status
        mock_response.body = " "
        mock_request.get_response.return_value = mock_response

        with pytest.raises(ProvisioningServiceError):
            await client.send_register(payload=registration_payload)

    @pytest.mark.it(
        "Returns the registration result received in the Response, converted to JSON, if the Response status was successful"
    )
    @pytest.mark.parametrize(
        "responses_enabled",
        [
            pytest.param(True, id="Register Responses Already Enabled"),
            pytest.param(False, id="Register Responses Not Yet Enabled"),
        ],
    )
    @pytest.mark.parametrize(
        "registration_payload",
        [
            pytest.param('{"text": "this is registration payload"}', id="Some payload"),
            pytest.param(None, id="No payload"),
        ],
    )
    async def test_success_response(self, mocker, client, responses_enabled, registration_payload):
        client._register_responses_enabled = responses_enabled
        # Override autocompletion behavior on publish (we don't need it here)
        client._mqtt_client.publish = mocker.AsyncMock()
        # Mock out the ledger to return a mocked request
        mock_request = mocker.MagicMock(spec=rr.Request)
        mock_request.request_id = FAKE_REGISTER_REQUEST_ID  # Need this for string manipulation
        mocker.patch.object(client._request_ledger, "create_request", return_value=mock_request)
        # Mock out the request to return a response
        mock_response = mocker.MagicMock(spec=rr.Response)
        mock_response.status = 200
        response_body_dict = {
            "operationId": FAKE_OPERATION_ID,
            "status": FAKE_STATUS,
            "registrationState": {
                "assignedHub": FAKE_ASSIGNED_HUB,
                "createdDateTimeUtc": None,
                "deviceId": FAKE_DEVICE_ID,
                "etag": None,
                "lastUpdatedDateTimeUtc": None,
                "payload": None,
                "subStatus": FAKE_SUB_STATUS,
            },
        }

        fake_response_string = json.dumps(response_body_dict)
        mock_response.body = fake_response_string
        mock_request.get_response.return_value = mock_response

        registration_response = await client.send_register(payload=registration_payload)
        assert registration_response == json.loads(fake_response_string)

    @pytest.mark.it(
        "Calls the send_register method thrice after different interval retry after values and "
        "then finally returns the registration result received in the Response, converted to JSON, "
        "when the Response status was successful on the last attempt"
    )
    @pytest.mark.parametrize(
        "responses_enabled",
        [
            pytest.param(True, id="Register Responses Already Enabled"),
            pytest.param(False, id="Register Responses Not Yet Enabled"),
        ],
    )
    @pytest.mark.parametrize(
        "registration_payload",
        [
            pytest.param('{"text": "this is registration payload"}', id="Some payload"),
            pytest.param(None, id="No payload"),
        ],
    )
    async def test_retry_response(self, mocker, client, responses_enabled, registration_payload):
        retry_after_val_1 = 1
        retry_after_val_2 = 2
        client._register_responses_enabled = responses_enabled
        # Override autocompletion behavior on publish (we don't need it here)
        client._mqtt_client.publish = mocker.AsyncMock()
        # Mock out the ledger to return a mocked request
        mock_request = mocker.MagicMock(spec=rr.Request)
        mock_request.request_id = FAKE_REGISTER_REQUEST_ID  # Need this for string manipulation
        mocker.patch.object(client._request_ledger, "create_request", return_value=mock_request)
        # Mock out the request to return 3 different responses
        mock_response_1 = mocker.MagicMock(spec=rr.Response)
        mock_response_1.status = 429
        mock_response_1.body = " "
        mock_response_1.properties = {"retry-after": str(retry_after_val_1)}

        mock_response_2 = mocker.MagicMock(spec=rr.Response)
        mock_response_2.status = 429
        mock_response_2.body = " "
        mock_response_2.properties = {"retry-after": str(retry_after_val_2)}
        mock_response_3 = mocker.MagicMock(spec=rr.Response)
        mock_response_3.status = 200
        response_body_dict = {
            "operationId": FAKE_OPERATION_ID,
            "status": FAKE_STATUS,
            "registrationState": {
                "assignedHub": FAKE_ASSIGNED_HUB,
                "createdDateTimeUtc": None,
                "deviceId": FAKE_DEVICE_ID,
                "etag": None,
                "lastUpdatedDateTimeUtc": None,
                "payload": None,
                "subStatus": FAKE_SUB_STATUS,
            },
        }
        fake_response_string = json.dumps(response_body_dict)
        mock_response_3.body = fake_response_string

        mock_request.get_response.side_effect = [mock_response_1, mock_response_2, mock_response_3]
        spy_sleep_factory = mocker.spy(asyncio, "sleep")
        mocker.patch.object(uuid, "uuid4", return_value=mock_request.request_id)

        expected_topic_register = mqtt_topic.get_register_topic_for_publish(mock_request.request_id)
        payload_dict = {"payload": registration_payload, "registrationId": FAKE_REGISTRATION_ID}
        expected_registration_payload = json.dumps(payload_dict)

        registration_response = await client.send_register(payload=registration_payload)

        assert spy_sleep_factory.call_count == 3

        # First sleep is 0 and then retry after
        assert spy_sleep_factory.call_args_list == [
            mocker.call(0),
            mocker.call(retry_after_val_1),
            mocker.call(retry_after_val_2),
        ]

        assert client._mqtt_client.publish.await_count == 3
        # all publish calls happen with same topic nad same payload
        assert client._mqtt_client.publish.await_args_list == [
            mocker.call(expected_topic_register, expected_registration_payload),
            mocker.call(expected_topic_register, expected_registration_payload),
            mocker.call(expected_topic_register, expected_registration_payload),
        ]
        assert registration_response == json.loads(fake_response_string)

    @pytest.mark.it(
        "Calls the send_register on the register topic method and then the send_polling on a different topic after a "
        "polling interval of 2 secs and then finally returns the registration result received in the Response, "
        "converted to JSON, when the Response status was successful on the last attempt"
    )
    @pytest.mark.parametrize(
        "responses_enabled",
        [
            pytest.param(True, id="Register Responses Already Enabled"),
            pytest.param(False, id="Register Responses Not Yet Enabled"),
        ],
    )
    @pytest.mark.parametrize(
        "registration_payload",
        [
            pytest.param('{"text": "this is registration payload"}', id="Some payload"),
            pytest.param(None, id="No payload"),
        ],
    )
    async def test_polling_response(self, mocker, client, responses_enabled, registration_payload):
        client._register_responses_enabled = responses_enabled
        # Override autocompletion behavior on publish (we don't need it here)
        client._mqtt_client.publish = mocker.AsyncMock()
        # Mock out the ledger to return a mocked request
        mock_request = mocker.MagicMock(spec=rr.Request)
        mock_request.request_id = FAKE_REGISTER_REQUEST_ID  # Need this for string manipulation
        mocker.patch.object(client._request_ledger, "create_request", return_value=mock_request)

        # Mock out the request to return 2 different responses
        mock_response_1 = mocker.MagicMock(spec=rr.Response)
        mock_response_1.status = 202
        response_body_dict = {"operationId": FAKE_OPERATION_ID, "status": "assigning"}
        fake_response_string = json.dumps(response_body_dict)
        mock_response_1.body = fake_response_string

        mock_response_2 = mocker.MagicMock(spec=rr.Response)
        mock_response_2.status = 200
        response_body_dict = {
            "operationId": FAKE_OPERATION_ID,
            "status": FAKE_STATUS,
            "registrationState": {
                "assignedHub": FAKE_ASSIGNED_HUB,
                "createdDateTimeUtc": None,
                "deviceId": FAKE_DEVICE_ID,
                "etag": None,
                "lastUpdatedDateTimeUtc": None,
                "payload": None,
                "subStatus": FAKE_SUB_STATUS,
            },
        }
        fake_response_string = json.dumps(response_body_dict)
        mock_response_2.body = fake_response_string

        mock_request.get_response.side_effect = [mock_response_1, mock_response_2]

        spy_sleep_factory = mocker.spy(asyncio, "sleep")
        # Mock uuid4 to return the fake request id
        mocker.patch.object(uuid, "uuid4", return_value=mock_request.request_id)

        expected_topic_register = mqtt_topic.get_register_topic_for_publish(mock_request.request_id)
        expected_topic_query = mqtt_topic.get_status_query_topic_for_publish(
            mock_request.request_id, FAKE_OPERATION_ID
        )
        payload_dict = {"payload": registration_payload, "registrationId": FAKE_REGISTRATION_ID}
        expected_registration_payload = json.dumps(payload_dict)

        registration_response = await client.send_register(payload=registration_payload)

        assert spy_sleep_factory.call_count == 2

        # First sleep is 0 and then DEFAULT_POLLING_INTERVAL
        assert spy_sleep_factory.call_args_list == [
            mocker.call(0),
            mocker.call(DEFAULT_POLLING_INTERVAL),
        ]

        assert client._mqtt_client.publish.await_count == 2
        assert client._mqtt_client.publish.await_args_list == [
            mocker.call(expected_topic_register, expected_registration_payload),
            mocker.call(expected_topic_query, " "),
        ]
        assert registration_response == json.loads(fake_response_string)

    # NOTE: MQTTClient subscribe can generate it's own cancellations due to network failure.
    # This is different from a user-initiated cancellation
    @pytest.mark.it("Allows any exceptions raised from the MQTTClient subscribe to propagate")
    @pytest.mark.parametrize("exception", mqtt_subscribe_exceptions)
    @pytest.mark.parametrize(
        "registration_payload",
        [
            pytest.param('{"text": "this is registration payload"}', id="Some payload"),
            pytest.param(None, id="No payload"),
        ],
    )
    async def test_mqtt_subscribe_exception(self, client, exception, registration_payload):
        assert client._register_responses_enabled is False
        client._mqtt_client.subscribe.side_effect = exception

        with pytest.raises(type(exception)) as e_info:
            await client.send_register(payload=registration_payload)
        assert e_info.value is exception

    # NOTE: MQTTClient subscribe can generate it's own cancellations due to network failure.
    # This is different from a user-initiated cancellation
    @pytest.mark.it(
        "Does not set the register_responses_enabled flag to True or create a Request if MQTTClient subscribe raises"
    )
    @pytest.mark.parametrize("exception", mqtt_subscribe_exceptions)
    @pytest.mark.parametrize(
        "registration_payload",
        [
            pytest.param('{"text": "this is registration payload"}', id="Some payload"),
            pytest.param(None, id="No payload"),
        ],
    )
    async def test_subscribe_exception_cleanup(
        self, mocker, client, exception, registration_payload
    ):
        assert client._register_responses_enabled is False
        spy_create_request = mocker.spy(client._request_ledger, "create_request")
        client._mqtt_client.subscribe.side_effect = exception

        with pytest.raises(type(exception)):
            await client.send_register(payload=registration_payload)

        assert client._register_responses_enabled is False
        assert spy_create_request.await_count == 0

    # NOTE: This is a user invoked cancel, as opposed to one above, which was generated by the
    # MQTTClient in response to a network failure.
    @pytest.mark.it(
        "Does not set the register_responses_enabled flag to True or create a Request if cancelled while waiting for the MQTTClient subscribe to finish"
    )
    @pytest.mark.parametrize(
        "registration_payload",
        [
            pytest.param('{"text": "this is registration payload"}', id="Some payload"),
            pytest.param(None, id="No payload"),
        ],
    )
    async def test_mqtt_subscribe_cancel_cleanup(self, mocker, client, registration_payload):
        assert client._register_responses_enabled is False
        spy_create_request = mocker.spy(client._request_ledger, "create_request")
        client._mqtt_client.subscribe = custom_mock.HangingAsyncMock()

        t = asyncio.create_task(client.send_register(payload=registration_payload))

        # Hanging, waiting for MQTT publish to finish
        await client._mqtt_client.subscribe.wait_for_hang()
        assert not t.done()

        # Cancel
        t.cancel()
        with pytest.raises(asyncio.CancelledError):
            await t

        assert client._register_responses_enabled is False
        assert spy_create_request.await_count == 0

    @pytest.mark.it("Allows any exceptions raised from the MQTTClient publish to propagate")
    @pytest.mark.parametrize("exception", mqtt_publish_exceptions)
    @pytest.mark.parametrize(
        "registration_payload",
        [
            pytest.param('{"text": "this is registration payload"}', id="Some payload"),
            pytest.param(None, id="No payload"),
        ],
    )
    async def test_mqtt_publish_exception(self, client, exception, registration_payload):
        client._mqtt_client.publish.side_effect = exception

        with pytest.raises(type(exception)) as e_info:
            await client.send_register(payload=registration_payload)
        assert e_info.value is exception

    @pytest.mark.it("Deletes the Request from the RequestLedger if MQTTClient publish raises")
    @pytest.mark.parametrize("exception", mqtt_publish_exceptions)
    @pytest.mark.parametrize(
        "registration_payload",
        [
            pytest.param('{"text": "this is registration payload"}', id="Some payload"),
            pytest.param(None, id="No payload"),
        ],
    )
    async def test_mqtt_publish_exception_cleanup(
        self, mocker, client, exception, registration_payload
    ):
        client._mqtt_client.publish.side_effect = exception
        spy_create_request = mocker.spy(client._request_ledger, "create_request")
        spy_delete_request = mocker.spy(client._request_ledger, "delete_request")
        # Mock the uuid call as well to return fake request id
        mocker.patch.object(uuid, "uuid4", return_value=FAKE_REGISTER_REQUEST_ID)

        with pytest.raises(type(exception)):
            await client.send_register(payload=registration_payload)

        assert spy_create_request.await_count == 1
        assert spy_create_request.await_args == mocker.call(FAKE_REGISTER_REQUEST_ID)
        assert spy_delete_request.await_count == 1
        assert spy_delete_request.await_args == mocker.call(
            spy_create_request.spy_return.request_id
        )

    @pytest.mark.it(
        "Deletes the Request from the RequestLedger if cancelled while waiting for the MQTTClient publish to finish"
    )
    @pytest.mark.parametrize(
        "registration_payload",
        [
            pytest.param('{"text": "this is registration payload"}', id="Some payload"),
            pytest.param(None, id="No payload"),
        ],
    )
    async def test_mqtt_publish_cancel_cleanup(self, mocker, client, registration_payload):
        client._mqtt_client.publish = custom_mock.HangingAsyncMock()
        spy_create_request = mocker.spy(client._request_ledger, "create_request")
        spy_delete_request = mocker.spy(client._request_ledger, "delete_request")
        # Mock the uuid call as well to return fake request id
        mocker.patch.object(uuid, "uuid4", return_value=FAKE_REGISTER_REQUEST_ID)

        t = asyncio.create_task(client.send_register(payload=registration_payload))

        # Hanging, waiting for MQTT publish to finish
        await client._mqtt_client.publish.wait_for_hang()
        assert not t.done()

        # Request was created, but not yet deleted
        assert spy_create_request.await_count == 1
        assert spy_create_request.await_args == mocker.call(FAKE_REGISTER_REQUEST_ID)
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
        "Deletes the Request from the RequestLedger if cancelled while waiting for a register dps response"
    )
    @pytest.mark.parametrize(
        "registration_payload",
        [
            pytest.param('{"text": "this is registration payload"}', id="Some payload"),
            pytest.param(None, id="No payload"),
        ],
    )
    async def test_waiting_response_cancel_cleanup(self, mocker, client, registration_payload):
        # Override autocompletion behavior on publish (we don't want it here)
        client._mqtt_client.publish = mocker.AsyncMock()

        # Mock Request creation to return a specific, mocked request that hangs on
        # awaiting a Response
        request = rr.Request("fake_request_id")
        request.get_response = custom_mock.HangingAsyncMock()
        mocker.patch.object(rr, "Request", return_value=request)
        spy_create_request = mocker.spy(client._request_ledger, "create_request")
        spy_delete_request = mocker.spy(client._request_ledger, "delete_request")

        # Mock the uuid call as well to return fake request id
        mocker.patch.object(uuid, "uuid4", return_value=FAKE_REGISTER_REQUEST_ID)

        send_task = asyncio.create_task(client.send_register(payload=registration_payload))

        # Hanging, waiting for response
        await request.get_response.wait_for_hang()
        assert not send_task.done()

        # Request was created, but not yet deleted
        assert spy_create_request.await_count == 1
        assert spy_create_request.await_args == mocker.call(FAKE_REGISTER_REQUEST_ID)
        assert spy_delete_request.await_count == 0

        # Cancel
        send_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await send_task

        # The Request that was created was also deleted
        assert spy_delete_request.await_count == 1
        assert spy_delete_request.await_args == mocker.call(request.request_id)

    @pytest.mark.it("Waits to retrieve response within a default period of time")
    @pytest.mark.parametrize(
        "responses_enabled",
        [
            pytest.param(True, id="Register Responses Already Enabled"),
            pytest.param(False, id="Register Responses Not Yet Enabled"),
        ],
    )
    @pytest.mark.parametrize(
        "registration_payload",
        [
            pytest.param('{"text": "this is registration payload"}', id="Some payload"),
            pytest.param(None, id="No payload"),
        ],
    )
    async def test_waiting_response_within_default_timeout(
        self, mocker, client, responses_enabled, registration_payload
    ):
        client._register_responses_enabled = responses_enabled
        # Override autocompletion behavior on publish (we don't need it here)
        client._mqtt_client.publish = mocker.AsyncMock()
        # Mock out the ledger to return a mocked request
        mock_request = mocker.MagicMock(spec=rr.Request)
        mock_request.request_id = FAKE_REGISTER_REQUEST_ID  # Need this for string manipulation
        mocker.patch.object(client._request_ledger, "create_request", return_value=mock_request)

        # Mock out the response to return completely successful response
        mock_response = mocker.MagicMock(spec=rr.Response)
        mock_response.status = 200
        response_body_dict = {
            "operationId": FAKE_OPERATION_ID,
            "status": FAKE_STATUS,
            "registrationState": {
                "assignedHub": FAKE_ASSIGNED_HUB,
                "createdDateTimeUtc": None,
                "deviceId": FAKE_DEVICE_ID,
                "etag": None,
                "lastUpdatedDateTimeUtc": None,
                "payload": None,
                "subStatus": FAKE_SUB_STATUS,
            },
        }
        fake_response_string = json.dumps(response_body_dict)
        mock_response.body = fake_response_string

        mock_request.get_response.return_value = mock_response

        spy_wait_for = mocker.spy(asyncio, "wait_for")

        await client.send_register(payload=registration_payload)

        assert spy_wait_for.await_count == 1
        assert asyncio.iscoroutine(spy_wait_for.await_args.args[0])
        assert spy_wait_for.await_args.args[1] == DEFAULT_TIMEOUT_INTERVAL

    @pytest.mark.it(
        "Raises ProvisioningServiceError from TimeoutError if the response is not retrieved within a default period"
    )
    @pytest.mark.parametrize(
        "responses_enabled",
        [
            pytest.param(True, id="Register Responses Already Enabled"),
            pytest.param(False, id="Register Responses Not Yet Enabled"),
        ],
    )
    @pytest.mark.parametrize(
        "registration_payload",
        [
            pytest.param('{"text": "this is registration payload"}', id="Some payload"),
            pytest.param(None, id="No payload"),
        ],
    )
    async def test_waiting_response_timeout_exception(
        self, mocker, client, responses_enabled, registration_payload
    ):
        client._register_responses_enabled = responses_enabled
        # Override autocompletion behavior on publish (we don't need it here)
        client._mqtt_client.publish = mocker.AsyncMock()
        # Mock out the ledger to return a mocked request
        mock_request = mocker.MagicMock(spec=rr.Request)
        mock_request.request_id = FAKE_REGISTER_REQUEST_ID  # Need this for string manipulation
        mocker.patch.object(client._request_ledger, "create_request", return_value=mock_request)

        patch_wait_for = mocker.patch.object(asyncio, "wait_for")
        fake_exception = asyncio.TimeoutError("fake timeout exception")
        patch_wait_for.side_effect = fake_exception

        raised = False

        # can not use with pytest.raises(ProvisioningServiceError) as e_info as e_info does not contain cause
        try:
            await client.send_register(payload=registration_payload)
        except ProvisioningServiceError as pe:
            raised = True
            assert pe.__cause__ is fake_exception
            assert mock_request.request_id in pe.args[0]

        assert raised

    @pytest.mark.it(
        "Deletes the Request from the RequestLedger if timeout occurred while waiting for a register dps response"
    )
    @pytest.mark.parametrize(
        "responses_enabled",
        [
            pytest.param(True, id="Register Responses Already Enabled"),
            pytest.param(False, id="Register Responses Not Yet Enabled"),
        ],
    )
    @pytest.mark.parametrize(
        "registration_payload",
        [
            pytest.param('{"text": "this is registration payload"}', id="Some payload"),
            pytest.param(None, id="No payload"),
        ],
    )
    async def test_waiting_response_timeout_cleanup(
        self, mocker, client, responses_enabled, registration_payload
    ):
        client._register_responses_enabled = responses_enabled
        # Override autocompletion behavior on publish (we don't need it here)
        client._mqtt_client.publish = mocker.AsyncMock()

        # Mock the uuid call as well to return fake request id
        mocker.patch.object(uuid, "uuid4", return_value=FAKE_REGISTER_REQUEST_ID)

        spy_create_request = mocker.spy(client._request_ledger, "create_request")
        spy_delete_request = mocker.spy(client._request_ledger, "delete_request")

        patch_wait_for = mocker.patch.object(asyncio, "wait_for")
        fake_exception = asyncio.TimeoutError("fake timeout exception")
        patch_wait_for.side_effect = fake_exception

        with pytest.raises(ProvisioningServiceError):
            await client.send_register(payload=registration_payload)

        # Request was created, but not yet deleted
        assert spy_create_request.await_count == 1

        # The Request that was created was also deleted
        assert spy_delete_request.await_count == 1
        assert spy_delete_request.await_args == mocker.call(FAKE_REGISTER_REQUEST_ID)


@pytest.mark.describe("ProvisioningMQTTClient - .send_polling()")
class TestProvisioningMQTTClientSendPolling:
    @pytest.fixture(autouse=True)
    def modify_publish(self, client):
        # Add a side effect to publish that will complete the pending request for that request id.
        # This will allow most tests to be able to ignore request/response infrastructure mocks.
        # If this is not the desired behavior (such as in tests OF the request/response paradigm)
        # override the publish behavior.
        #
        # To see tests regarding how this actually works in practice, see the relevant test suite
        async def fake_publish(topic, payload):
            rid = topic.split("&")[0].split("=")[1]
            response_body_dict = {
                "operationId": FAKE_OPERATION_ID,
                "status": FAKE_STATUS,
                "registrationState": {"registrationId": FAKE_REGISTRATION_ID},
            }
            response = rr.Response(rid, 200, json.dumps(response_body_dict))
            await client._request_ledger.match_response(response)

        client._mqtt_client.publish.side_effect = fake_publish

    @pytest.mark.it("Generates a new Request, using the RequestLedger stored on the client")
    async def test_generate_request(self, mocker, client):
        spy_create_request = mocker.spy(client._request_ledger, "create_request")

        # Mock the uuid call as well to return fake request id
        mocker.patch.object(uuid, "uuid4", return_value=FAKE_POLLING_REQUEST_ID)

        await client.send_polling(operation_id=FAKE_OPERATION_ID)

        assert spy_create_request.await_count == 1
        assert spy_create_request.await_args == mocker.call(FAKE_POLLING_REQUEST_ID)

    @pytest.mark.it("Awaits a publish to the polling request topic using the MQTTClient")
    async def test_mqtt_publish(self, mocker, client):
        # Mock the uuid call as well to return fake request id
        mocker.patch.object(uuid, "uuid4", return_value=FAKE_POLLING_REQUEST_ID)

        spy_create_request = mocker.spy(client._request_ledger, "create_request")

        assert client._mqtt_client.publish.await_count == 0

        await client.send_polling(operation_id=FAKE_OPERATION_ID)

        request = spy_create_request.spy_return
        expected_topic = mqtt_topic.get_status_query_topic_for_publish(
            request.request_id, FAKE_OPERATION_ID
        )

        assert client._mqtt_client.publish.await_count == 1
        assert client._mqtt_client.publish.await_args == mocker.call(expected_topic, " ")

    @pytest.mark.it("Awaits a received Response to the Request")
    async def test_get_response(self, mocker, client):
        # Override autocompletion behavior on publish (we don't want it here)
        client._mqtt_client.publish = mocker.AsyncMock()
        # Mock out the ledger to return a mocked request
        mock_request = mocker.MagicMock(spec=rr.Request)
        mock_request.request_id = FAKE_POLLING_REQUEST_ID  # Need this for string manipulation
        mocker.patch.object(client._request_ledger, "create_request", return_value=mock_request)
        # Mock out the request to return a response
        mock_response = mocker.MagicMock(spec=rr.Response)
        mock_response.status = 200
        response_body_dict = {
            "operationId": FAKE_OPERATION_ID,
            "status": FAKE_STATUS,
            "registrationState": {"registrationId": FAKE_REGISTRATION_ID},
        }
        mock_response.body = json.dumps(response_body_dict)
        mock_request.get_response.return_value = mock_response

        await client.send_polling(FAKE_OPERATION_ID)

        assert mock_request.get_response.await_count == 1
        assert mock_request.get_response.await_args == mocker.call()

    @pytest.mark.it(
        "Raises an ProvisioningServiceError if an unsuccessful status (300-429) is received via the Response"
    )
    @pytest.mark.parametrize(
        "failed_status",
        [
            pytest.param(300, id="Status Code: 300"),
            pytest.param(400, id="Status Code: 400"),
            pytest.param(428, id="Status Code: 428"),
        ],
    )
    async def test_failed_response(self, mocker, client, failed_status):
        # Override autocompletion behavior on publish (we don't need it here)
        client._mqtt_client.publish = mocker.AsyncMock()
        # Mock out the ledger to return a mocked request
        mock_request = mocker.MagicMock(spec=rr.Request)
        mock_request.request_id = FAKE_POLLING_REQUEST_ID  # Need this for string manipulation
        mocker.patch.object(client._request_ledger, "create_request", return_value=mock_request)
        # Mock out the request to return a response
        mock_response = mocker.MagicMock(spec=rr.Response)
        mock_response.status = failed_status
        mock_response.body = " "
        mock_request.get_response.return_value = mock_response

        with pytest.raises(ProvisioningServiceError):
            await client.send_polling(FAKE_OPERATION_ID)

    @pytest.mark.it(
        "Returns the registration result received in the Response, converted to JSON, if the Response status was successful"
    )
    async def test_success_response(self, mocker, client):
        # Override autocompletion behavior on publish (we don't need it here)
        client._mqtt_client.publish = mocker.AsyncMock()
        # Mock out the ledger to return a mocked request
        mock_request = mocker.MagicMock(spec=rr.Request)
        mock_request.request_id = FAKE_POLLING_REQUEST_ID  # Need this for string manipulation
        mocker.patch.object(client._request_ledger, "create_request", return_value=mock_request)
        # Mock out the request to return a response
        mock_response = mocker.MagicMock(spec=rr.Response)
        mock_response.status = 200
        response_body_dict = {
            "operationId": FAKE_OPERATION_ID,
            "status": FAKE_STATUS,
            "registrationState": {
                "assignedHub": FAKE_ASSIGNED_HUB,
                "createdDateTimeUtc": None,
                "deviceId": FAKE_DEVICE_ID,
                "etag": None,
                "lastUpdatedDateTimeUtc": None,
                "payload": None,
                "subStatus": FAKE_SUB_STATUS,
            },
        }

        fake_response_string = json.dumps(response_body_dict)
        mock_response.body = fake_response_string
        mock_request.get_response.return_value = mock_response

        registration_response = await client.send_polling(FAKE_OPERATION_ID)
        assert registration_response == json.loads(fake_response_string)

    @pytest.mark.it(
        "Calls the send_polling method thrice with different interval and retry after values and "
        "then finally returns the registration result received in the Response, converted to JSON, "
        "when the Response status was successful on the last attempt"
    )
    async def test_retry_response(self, mocker, client):
        retry_after_val_1 = 1
        retry_after_val_2 = 2
        # Override autocompletion behavior on publish (we don't need it here)
        client._mqtt_client.publish = mocker.AsyncMock()
        # Mock out the ledger to return a mocked request
        mock_request = mocker.MagicMock(spec=rr.Request)
        mock_request.request_id = FAKE_POLLING_REQUEST_ID  # Need this for string manipulation
        mocker.patch.object(client._request_ledger, "create_request", return_value=mock_request)
        # Mock out the request to return 3 different responses
        mock_response_1 = mocker.MagicMock(spec=rr.Response)
        mock_response_1.status = 429
        mock_response_1.body = " "
        mock_response_1.properties = {"retry-after": str(retry_after_val_1)}

        mock_response_2 = mocker.MagicMock(spec=rr.Response)
        mock_response_2.status = 429
        mock_response_2.body = " "
        mock_response_2.properties = {"retry-after": str(retry_after_val_2)}
        mock_response_3 = mocker.MagicMock(spec=rr.Response)
        mock_response_3.status = 200
        response_body_dict = {
            "operationId": FAKE_OPERATION_ID,
            "status": FAKE_STATUS,
            "registrationState": {
                "assignedHub": FAKE_ASSIGNED_HUB,
                "createdDateTimeUtc": None,
                "deviceId": FAKE_DEVICE_ID,
                "etag": None,
                "lastUpdatedDateTimeUtc": None,
                "payload": None,
                "subStatus": FAKE_SUB_STATUS,
            },
        }
        fake_response_string = json.dumps(response_body_dict)
        mock_response_3.body = fake_response_string

        mock_request.get_response.side_effect = [mock_response_1, mock_response_2, mock_response_3]
        spy_sleep_factory = mocker.spy(asyncio, "sleep")
        mocker.patch.object(uuid, "uuid4", return_value=mock_request.request_id)

        expected_topic_query = mqtt_topic.get_status_query_topic_for_publish(
            mock_request.request_id, FAKE_OPERATION_ID
        )

        registration_response = await client.send_polling(FAKE_OPERATION_ID)

        assert spy_sleep_factory.call_count == 3

        # First sleep is default polling interval and then retry after
        assert spy_sleep_factory.call_args_list == [
            mocker.call(2),
            mocker.call(retry_after_val_1),
            mocker.call(retry_after_val_2),
        ]

        assert client._mqtt_client.publish.await_count == 3
        # all publish calls happen with same topic nad same payload
        assert client._mqtt_client.publish.await_args_list == [
            mocker.call(expected_topic_query, " "),
            mocker.call(expected_topic_query, " "),
            mocker.call(expected_topic_query, " "),
        ]
        assert registration_response == json.loads(fake_response_string)

    @pytest.mark.it(
        "Calls the send_polling on the query topic 2 times after a polling interval of 2 secs and then "
        "finally returns the registration result received in the Response, "
        "converted to JSON, when the Response status was successful on the last attempt"
    )
    async def test_polling_response(self, mocker, client):
        # Override autocompletion behavior on publish (we don't need it here)
        client._mqtt_client.publish = mocker.AsyncMock()
        # Mock out the ledger to return a mocked request
        mock_request = mocker.MagicMock(spec=rr.Request)
        mock_request.request_id = FAKE_POLLING_REQUEST_ID  # Need this for string manipulation
        mocker.patch.object(client._request_ledger, "create_request", return_value=mock_request)

        # Mock out the request to return 2 different responses
        mock_response_1 = mocker.MagicMock(spec=rr.Response)
        mock_response_1.status = 202
        response_body_dict = {"operationId": FAKE_OPERATION_ID, "status": "assigning"}
        fake_response_string = json.dumps(response_body_dict)
        mock_response_1.body = fake_response_string
        # EMoty dict with no retry after
        mock_response_1.properties = {}

        mock_response_2 = mocker.MagicMock(spec=rr.Response)
        mock_response_2.status = 200
        response_body_dict = {
            "operationId": FAKE_OPERATION_ID,
            "status": FAKE_STATUS,
            "registrationState": {
                "assignedHub": FAKE_ASSIGNED_HUB,
                "createdDateTimeUtc": None,
                "deviceId": FAKE_DEVICE_ID,
                "etag": None,
                "lastUpdatedDateTimeUtc": None,
                "payload": None,
                "subStatus": FAKE_SUB_STATUS,
            },
        }
        fake_response_string = json.dumps(response_body_dict)
        mock_response_2.body = fake_response_string

        # Need to use side effect instead of return value to generate different responses
        mock_request.get_response.side_effect = [mock_response_1, mock_response_2]

        spy_sleep_factory = mocker.spy(asyncio, "sleep")
        # Mock uuid4 to return the fake request id
        mocker.patch.object(uuid, "uuid4", return_value=mock_request.request_id)

        expected_topic_query = mqtt_topic.get_status_query_topic_for_publish(
            mock_request.request_id, FAKE_OPERATION_ID
        )

        registration_response = await client.send_polling(FAKE_OPERATION_ID)

        assert spy_sleep_factory.call_count == 2

        # Both sleep are DEFAULT_POLLING_INTERVAL
        assert spy_sleep_factory.call_args_list == [
            mocker.call(DEFAULT_POLLING_INTERVAL),
            mocker.call(DEFAULT_POLLING_INTERVAL),
        ]

        assert client._mqtt_client.publish.await_count == 2
        assert client._mqtt_client.publish.await_args_list == [
            mocker.call(expected_topic_query, " "),
            mocker.call(expected_topic_query, " "),
        ]
        assert registration_response == json.loads(fake_response_string)

    @pytest.mark.it("Allows any exceptions raised from the MQTTClient publish to propagate")
    @pytest.mark.parametrize("exception", mqtt_publish_exceptions)
    async def test_mqtt_publish_exception(self, client, exception):
        client._mqtt_client.publish.side_effect = exception

        with pytest.raises(type(exception)) as e_info:
            await client.send_polling(FAKE_OPERATION_ID)
        assert e_info.value is exception

    @pytest.mark.it("Deletes the Request from the RequestLedger if MQTTClient publish raises")
    @pytest.mark.parametrize("exception", mqtt_publish_exceptions)
    async def test_mqtt_publish_exception_cleanup(self, mocker, client, exception):
        client._mqtt_client.publish.side_effect = exception
        spy_create_request = mocker.spy(client._request_ledger, "create_request")
        spy_delete_request = mocker.spy(client._request_ledger, "delete_request")
        # Mock the uuid call as well to return fake request id
        mocker.patch.object(uuid, "uuid4", return_value=FAKE_POLLING_REQUEST_ID)

        with pytest.raises(type(exception)):
            await client.send_polling(FAKE_OPERATION_ID)

        assert spy_create_request.await_count == 1
        assert spy_create_request.await_args == mocker.call(FAKE_POLLING_REQUEST_ID)
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
        # Mock the uuid call as well to return fake request id
        mocker.patch.object(uuid, "uuid4", return_value=FAKE_POLLING_REQUEST_ID)

        t = asyncio.create_task(client.send_polling(FAKE_OPERATION_ID))

        # Hanging, waiting for MQTT publish to finish
        await client._mqtt_client.publish.wait_for_hang()
        assert not t.done()

        # Request was created, but not yet deleted
        assert spy_create_request.await_count == 1
        assert spy_create_request.await_args == mocker.call(FAKE_POLLING_REQUEST_ID)
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
        "Deletes the Request from the RequestLedger if cancelled while waiting for a register dps response"
    )
    async def test_waiting_response_cancel_cleanup(self, mocker, client):
        # Override autocompletion behavior on publish (we don't want it here)
        client._mqtt_client.publish = mocker.AsyncMock()

        # Mock Request creation to return a specific, mocked request that hangs on
        # awaiting a Response
        request = rr.Request(FAKE_POLLING_REQUEST_ID)
        request.get_response = custom_mock.HangingAsyncMock()
        mocker.patch.object(rr, "Request", return_value=request)
        spy_create_request = mocker.spy(client._request_ledger, "create_request")
        spy_delete_request = mocker.spy(client._request_ledger, "delete_request")

        # Mock the uuid call as well to return fake request id
        mocker.patch.object(uuid, "uuid4", return_value=FAKE_POLLING_REQUEST_ID)

        send_task = asyncio.create_task(client.send_polling(FAKE_OPERATION_ID))

        # Hanging, waiting for response
        await request.get_response.wait_for_hang()
        assert not send_task.done()

        # Request was created, but not yet deleted
        assert spy_create_request.await_count == 1
        assert spy_create_request.await_args == mocker.call(FAKE_POLLING_REQUEST_ID)
        assert spy_delete_request.await_count == 0

        # Cancel
        send_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await send_task

        # The Request that was created was also deleted
        assert spy_delete_request.await_count == 1
        assert spy_delete_request.await_args == mocker.call(request.request_id)

    @pytest.mark.it("Waits to retrieve response within a default period of time")
    async def test_waiting_response_within_default_timeout(self, mocker, client):
        # Override autocompletion behavior on publish (we don't need it here)
        client._mqtt_client.publish = mocker.AsyncMock()
        # Mock out the ledger to return a mocked request
        mock_request = mocker.MagicMock(spec=rr.Request)
        mock_request.request_id = FAKE_POLLING_REQUEST_ID
        mocker.patch.object(client._request_ledger, "create_request", return_value=mock_request)

        # Mock out the response to return completely successful response
        mock_response = mocker.MagicMock(spec=rr.Response)
        mock_response.status = 200
        response_body_dict = {
            "operationId": FAKE_OPERATION_ID,
            "status": FAKE_STATUS,
            "registrationState": {
                "assignedHub": FAKE_ASSIGNED_HUB,
                "createdDateTimeUtc": None,
                "deviceId": FAKE_DEVICE_ID,
                "etag": None,
                "lastUpdatedDateTimeUtc": None,
                "payload": None,
                "subStatus": FAKE_SUB_STATUS,
            },
        }
        fake_response_string = json.dumps(response_body_dict)
        mock_response.body = fake_response_string

        mock_request.get_response.return_value = mock_response

        spy_wait_for = mocker.spy(asyncio, "wait_for")

        await client.send_polling(operation_id=FAKE_OPERATION_ID)

        assert spy_wait_for.await_count == 1
        assert asyncio.iscoroutine(spy_wait_for.await_args.args[0])
        assert spy_wait_for.await_args.args[1] == DEFAULT_TIMEOUT_INTERVAL

    @pytest.mark.it(
        "Raises ProvisioningServiceError from TimeoutError if the response is not retrieved within a default period"
    )
    async def test_waiting_response_timeout_exception(self, mocker, client):
        # Override autocompletion behavior on publish (we don't need it here)
        client._mqtt_client.publish = mocker.AsyncMock()
        # Mock out the ledger to return a mocked request
        mock_request = mocker.MagicMock(spec=rr.Request)
        mock_request.request_id = FAKE_POLLING_REQUEST_ID
        mocker.patch.object(client._request_ledger, "create_request", return_value=mock_request)

        patch_wait_for = mocker.patch.object(asyncio, "wait_for")
        fake_exception = asyncio.TimeoutError("fake timeout exception")
        patch_wait_for.side_effect = fake_exception

        raised = False

        # can not use with pytest.raises(ProvisioningServiceError) as e_info as e_info does not contain cause
        try:
            await client.send_polling(operation_id=FAKE_OPERATION_ID)
        except ProvisioningServiceError as pe:
            raised = True
            assert pe.__cause__ is fake_exception
            assert mock_request.request_id in pe.args[0]

        assert raised

    @pytest.mark.it(
        "Deletes the Request from the RequestLedger if timeout occurred while waiting for a register dps response"
    )
    async def test_waiting_response_timeout_cleanup(self, mocker, client):
        # Override autocompletion behavior on publish (we don't need it here)
        client._mqtt_client.publish = mocker.AsyncMock()

        # Mock the uuid call as well to return fake request id
        mocker.patch.object(uuid, "uuid4", return_value=FAKE_POLLING_REQUEST_ID)

        spy_create_request = mocker.spy(client._request_ledger, "create_request")
        spy_delete_request = mocker.spy(client._request_ledger, "delete_request")

        patch_wait_for = mocker.patch.object(asyncio, "wait_for")
        fake_exception = asyncio.TimeoutError("fake timeout exception")
        patch_wait_for.side_effect = fake_exception

        with pytest.raises(ProvisioningServiceError):
            await client.send_polling(operation_id=FAKE_OPERATION_ID)

        # Request was created, but not yet deleted
        assert spy_create_request.await_count == 1

        # The Request that was created was also deleted
        assert spy_delete_request.await_count == 1
        assert spy_delete_request.await_args == mocker.call(FAKE_POLLING_REQUEST_ID)


@pytest.mark.describe("ProvisioningMQTTClient - PROPERTY: .connected")
class TestProvisioningMQTTClientConnected:
    @pytest.mark.it("Returns the result of the MQTTClient's .is_connected() method")
    def test_returns_result(self, mocker, client):
        assert client._mqtt_client.is_connected.call_count == 0

        result = client.connected

        assert client._mqtt_client.is_connected.call_count == 1
        assert client._mqtt_client.is_connected.call_args == mocker.call()
        assert result is client._mqtt_client.is_connected.return_value


@pytest.mark.describe("ProvisioningMQTTClient - BG TASK: ._process_dps_responses")
class TestProvisioningMQTTClientProcessDPSResponses:
    response_payloads = [
        pytest.param('{"json": "in", "a": {"string": "format"}}', id="Some DPS Response"),
        pytest.param(" ", id="DPS Empty Response"),
    ]

    @pytest.mark.it(
        "Creates a Response containing the request id and status code and extracted properties from the topic, "
        "as well as the utf-8 decoded payload of the MQTTMessage, when the MQTTClient receives an "
        "MQTTMessage on the dps response topic"
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
    @pytest.mark.parametrize("payload_str", response_payloads)
    async def test_response(self, mocker, client, status, payload_str):
        # Mocks
        mocker.patch.object(client, "_request_ledger", spec=rr.RequestLedger)
        spy_response_factory = mocker.spy(rr, "Response")
        # Set up MQTTMessages
        generic_topic = mqtt_topic.get_response_topic_for_subscribe()
        rid = "some rid"
        value1 = "fake value 1"
        value2 = "fake value 2"
        props = {"$rid": rid, "prop1": value1, "prop2": value2}
        msg_topic = "$dps/registrations/res/{status}/?$rid={rid}&prop1={v1}&prop2={v2}".format(
            status=status, rid=rid, v1=value1, v2=value2
        )
        mqtt_msg = mqtt.MQTTMessage(mid=1, topic=msg_topic.encode("utf-8"))
        mqtt_msg.payload = payload_str.encode("utf-8")

        # Start task
        t = asyncio.create_task(client._process_dps_responses())
        await asyncio.sleep(0.1)

        # No Responses have been created yet
        assert spy_response_factory.call_count == 0

        # Load the MQTTMessage into the MQTTClient's filtered message queue
        await client._mqtt_client._incoming_filtered_messages[generic_topic].put(mqtt_msg)
        await asyncio.sleep(0.1)

        # Response was created
        assert spy_response_factory.call_count == 1
        resp1 = spy_response_factory.spy_return
        assert resp1.request_id == rid
        assert resp1.status == status
        assert resp1.body == payload_str
        assert resp1.properties == props

        t.cancel()

    @pytest.mark.it("Matches the newly created Response on the RequestLedger")
    @pytest.mark.parametrize("payload_str", response_payloads)
    async def test_match(self, mocker, client, payload_str):
        # Mock
        mock_ledger = mocker.patch.object(client, "_request_ledger", spec=rr.RequestLedger)
        spy_response_factory = mocker.spy(rr, "Response")
        # Set up MQTTMessage
        generic_topic = mqtt_topic.get_response_topic_for_subscribe()
        topic = generic_topic.rstrip("#") + "{}/?$rid={}".format(200, "some rid")
        mqtt_msg = mqtt.MQTTMessage(mid=1, topic=topic.encode("utf-8"))
        mqtt_msg.payload = payload_str.encode("utf-8")

        # No Responses have been created yet
        assert spy_response_factory.call_count == 0
        assert mock_ledger.match_response.call_count == 0

        # Start task
        t = asyncio.create_task(client._process_dps_responses())
        await asyncio.sleep(0.1)

        # Load the MQTTMessage into the MQTTClient's filtered message queue
        await client._mqtt_client._incoming_filtered_messages[generic_topic].put(mqtt_msg)
        await asyncio.sleep(0.1)

        # Response was created
        assert spy_response_factory.call_count == 1
        resp1 = spy_response_factory.spy_return
        assert mock_ledger.match_response.call_count == 1
        assert mock_ledger.match_response.call_args == mocker.call(resp1)

        t.cancel()

    @pytest.mark.it("Indefinitely repeats")
    async def test_repeat(self, mocker, client):
        mock_ledger = mocker.patch.object(client, "_request_ledger", spec=rr.RequestLedger)
        spy_response_factory = mocker.spy(rr, "Response")
        assert spy_response_factory.call_count == 0
        assert mock_ledger.match_response.call_count == 0

        generic_topic = mqtt_topic.get_response_topic_for_subscribe()
        topic = generic_topic.rstrip("#") + "{}/?$rid={}".format(200, "some rid")

        t = asyncio.create_task(client._process_dps_responses())
        await asyncio.sleep(0.1)

        # Test that behavior repeats up to 10 times. No way to really prove infinite
        i = 0
        assert mock_ledger.match_response.call_count == 0
        while i < 10:
            i += 1
            mqtt_msg = mqtt.MQTTMessage(mid=1, topic=topic.encode("utf-8"))
            # Switch between Polling and Register responses
            if i % 2 == 0:
                mqtt_msg.payload = '{"operationId":"fake_operation_id","status":"assigning","registrationState":{"registrationId":"fake_reg_id","status":"assigning"}}'.encode(
                    "utf-8"
                )
            else:
                mqtt_msg.payload = (
                    '{"operationId":"fake_operation_id","status":"assigning"}'.encode("utf-8")
                )
            # Load the MQTTMessage into the MQTTClient's filtered message queue
            await client._mqtt_client._incoming_filtered_messages[generic_topic].put(mqtt_msg)
            await asyncio.sleep(0.1)
            # Response was created
            assert spy_response_factory.call_count == i

        assert not t.done()
        t.cancel()

    @pytest.mark.it(
        "Suppresses any unexpected exceptions raised while extracting properties along with request id from the "
        "MQTTMessage, dropping the MQTTMessage and continuing"
    )
    async def test_request_properties_extraction_fails(self, mocker, client, arbitrary_exception):
        # Inject failure
        original_fn = mqtt_topic.extract_properties_from_response_topic
        mocker.patch.object(
            mqtt_topic,
            "extract_properties_from_response_topic",
            side_effect=arbitrary_exception,
        )

        # Create two messages that are the same other than the request id
        generic_topic = mqtt_topic.get_response_topic_for_subscribe()
        # Response #1
        rid1 = "rid1"
        msg1_topic = generic_topic.rstrip("#") + "{}/?$rid={}".format(200, rid1)
        mqtt_msg1 = mqtt.MQTTMessage(mid=1, topic=msg1_topic.encode("utf-8"))
        mqtt_msg1.payload = " ".encode("utf-8")
        # Response #2
        rid2 = "rid2"
        msg2_topic = generic_topic.rstrip("#") + "{}/?$rid={}".format(200, rid2)
        mqtt_msg2 = mqtt.MQTTMessage(mid=1, topic=msg2_topic.encode("utf-8"))
        mqtt_msg2.payload = " ".encode("utf-8")

        # Spy on the Response object
        spy_response_factory = mocker.spy(rr, "Response")

        # Start task
        t = asyncio.create_task(client._process_dps_responses())

        # Load the first MQTTMessage
        await client._mqtt_client._incoming_filtered_messages[generic_topic].put(mqtt_msg1)
        await asyncio.sleep(0.1)

        # No Response was created due to the injected failure (but failure was suppressed)
        assert spy_response_factory.call_count == 0
        mqtt_topic.extract_properties_from_response_topic.call_count == 1

        # Un-inject the failure
        mqtt_topic.extract_properties_from_response_topic = original_fn

        # Load the second MQTTMessage
        await client._mqtt_client._incoming_filtered_messages[generic_topic].put(mqtt_msg2)
        await asyncio.sleep(0.1)

        # This time a Response was created, demonstrating that the task is still functional
        assert spy_response_factory.call_count == 1
        resp2 = spy_response_factory.spy_return
        assert resp2.request_id == rid2
        assert resp2.status == 200
        assert resp2.body == mqtt_msg2.payload.decode("utf-8")

        assert not t.done()

        t.cancel()

    @pytest.mark.it(
        "Suppresses any unexpected exceptions raised while extracting the status code from the MQTTMessage, "
        "dropping the MQTTMessage and continuing"
    )
    async def test_status_code_extraction_fails(self, mocker, client, arbitrary_exception):
        # Inject failure
        original_fn = mqtt_topic.extract_status_code_from_response_topic
        mocker.patch.object(
            mqtt_topic,
            "extract_status_code_from_response_topic",
            side_effect=arbitrary_exception,
        )

        # Create two messages that are the same other than the request id
        generic_topic = mqtt_topic.get_response_topic_for_subscribe()
        # Response #1
        rid1 = "rid1"
        msg1_topic = generic_topic.rstrip("#") + "{}/?$rid={}".format(200, rid1)
        mqtt_msg1 = mqtt.MQTTMessage(mid=1, topic=msg1_topic.encode("utf-8"))
        mqtt_msg1.payload = " ".encode("utf-8")
        # Response #2
        rid2 = "rid2"
        msg2_topic = generic_topic.rstrip("#") + "{}/?$rid={}".format(200, rid2)
        mqtt_msg2 = mqtt.MQTTMessage(mid=1, topic=msg2_topic.encode("utf-8"))
        mqtt_msg2.payload = " ".encode("utf-8")

        # Spy on the Response object
        spy_response_factory = mocker.spy(rr, "Response")

        # Start task
        t = asyncio.create_task(client._process_dps_responses())

        # Load the first MQTTMessage
        await client._mqtt_client._incoming_filtered_messages[generic_topic].put(mqtt_msg1)
        await asyncio.sleep(0.1)

        # No Response was created due to the injected failure (but failure was suppressed)
        assert spy_response_factory.call_count == 0
        mqtt_topic.extract_status_code_from_response_topic.call_count == 1

        # Un-inject the failure
        mqtt_topic.extract_status_code_from_response_topic = original_fn

        # Load the second MQTTMessage
        await client._mqtt_client._incoming_filtered_messages[generic_topic].put(mqtt_msg2)
        await asyncio.sleep(0.1)

        # This time a Response was created, demonstrating that the previous failure did not
        # crash the task
        assert spy_response_factory.call_count == 1
        resp2 = spy_response_factory.spy_return
        assert resp2.request_id == rid2
        assert resp2.status == 200
        assert resp2.body == mqtt_msg2.payload.decode("utf-8")

        assert not t.done()

        t.cancel()

    @pytest.mark.it(
        "Suppresses any unexpected exceptions raised while decoding the payload from the MQTTMessage, dropping the MQTTMessage and continuing"
    )
    async def test_payload_decode_fails(self, mocker, client, arbitrary_exception):
        # Create two messages that are the same other than the request id
        generic_topic = mqtt_topic.get_response_topic_for_subscribe()
        # Response #1
        rid1 = "rid1"
        msg1_topic = generic_topic.rstrip("#") + "{}/?$rid={}".format(200, rid1)
        mqtt_msg1 = mqtt.MQTTMessage(mid=1, topic=msg1_topic.encode("utf-8"))
        mqtt_msg1.payload = " ".encode("utf-8")
        # Response #2
        rid2 = "rid2"
        msg2_topic = generic_topic.rstrip("#") + "{}/?$rid={}".format(200, rid2)
        mqtt_msg2 = mqtt.MQTTMessage(mid=1, topic=msg2_topic.encode("utf-8"))
        mqtt_msg2.payload = " ".encode("utf-8")

        # Spy on the Response object
        spy_response_factory = mocker.spy(rr, "Response")

        # Inject failure into the first MQTTMessage's payload
        mqtt_msg1.payload = mocker.MagicMock()
        mqtt_msg1.payload.decode.side_effect = arbitrary_exception

        # Start task
        t = asyncio.create_task(client._process_dps_responses())

        # Load the first MQTTMessage
        await client._mqtt_client._incoming_filtered_messages[generic_topic].put(mqtt_msg1)
        await asyncio.sleep(0.1)

        # No Response was created due to the injected failure (but failure was suppressed)
        assert spy_response_factory.call_count == 0
        assert mqtt_msg1.payload.decode.call_count == 1

        # Load the second MQTTMessage
        await client._mqtt_client._incoming_filtered_messages[generic_topic].put(mqtt_msg2)
        await asyncio.sleep(0.1)

        # This time a Response was created, demonstrating that the previous failure did not
        # crash the task
        assert spy_response_factory.call_count == 1
        resp2 = spy_response_factory.spy_return
        assert resp2.request_id == rid2
        assert resp2.status == 200
        assert resp2.body == mqtt_msg2.payload.decode("utf-8")

        assert not t.done()

        t.cancel()

    @pytest.mark.it(
        "Suppresses any unexpected exceptions raised instantiating the Response object from the MQTTMessage values, dropping the MQTTMessage and continuing"
    )
    async def test_response_instantiation_fails(self, mocker, client, arbitrary_exception):
        # Inject failure
        original_cls = rr.Response
        mocker.patch.object(rr, "Response", side_effect=arbitrary_exception)

        # Create two messages that are the same other than the request id
        generic_topic = mqtt_topic.get_response_topic_for_subscribe()
        # Response #1
        rid1 = "rid1"
        msg1_topic = generic_topic.rstrip("#") + "{}/?$rid={}".format(200, rid1)
        mqtt_msg1 = mqtt.MQTTMessage(mid=1, topic=msg1_topic.encode("utf-8"))
        mqtt_msg1.payload = " ".encode("utf-8")
        # Response #2
        rid2 = "rid2"
        msg2_topic = generic_topic.rstrip("#") + "{}/?$rid={}".format(200, rid2)
        mqtt_msg2 = mqtt.MQTTMessage(mid=1, topic=msg2_topic.encode("utf-8"))
        mqtt_msg2.payload = " ".encode("utf-8")

        # Mock the ledger so we can see if it is used
        mock_ledger = mocker.patch.object(client, "_request_ledger", spec=rr.RequestLedger)

        # Start task
        t = asyncio.create_task(client._process_dps_responses())

        # Load the first MQTTMessage
        await client._mqtt_client._incoming_filtered_messages[generic_topic].put(mqtt_msg1)
        await asyncio.sleep(0.1)

        # No Response matched to the injected failure (but failure was suppressed)
        assert mock_ledger.match_response.call_count == 0
        assert rr.Response.call_count == 1

        # Un-inject the failure
        rr.Response = original_cls

        # Load the second MQTTMessage
        await client._mqtt_client._incoming_filtered_messages[generic_topic].put(mqtt_msg2)
        await asyncio.sleep(0.1)

        # This time a Response was created and matched, demonstrating that the previous
        # failure did not crash the task
        assert mock_ledger.match_response.call_count == 1
        resp = mock_ledger.match_response.call_args[0][0]
        assert resp.request_id == rid2
        assert resp.status == 200
        assert resp.body == mqtt_msg2.payload.decode("utf-8")

        assert not t.done()

        t.cancel()

    @pytest.mark.it(
        "Suppresses any exceptions raised while matching the Response, dropping the MQTTMessage and continuing"
    )
    @pytest.mark.parametrize(
        "exception",
        [
            pytest.param(KeyError(), id="KeyError"),
            pytest.param(lazy_fixture("arbitrary_exception"), id="Unexpected Exception"),
        ],
    )
    async def test_response_match_fails(self, mocker, client, exception):
        mock_ledger = mocker.patch.object(client, "_request_ledger", spec=rr.RequestLedger)

        # Create two messages that are the same other than the request id
        generic_topic = mqtt_topic.get_response_topic_for_subscribe()
        # Response #1
        rid1 = "rid1"
        msg1_topic = generic_topic.rstrip("#") + "{}/?$rid={}".format(200, rid1)
        mqtt_msg1 = mqtt.MQTTMessage(mid=1, topic=msg1_topic.encode("utf-8"))
        mqtt_msg1.payload = " ".encode("utf-8")
        # Response #2
        rid2 = "rid2"
        msg2_topic = generic_topic.rstrip("#") + "{}/?$rid={}".format(200, rid2)
        mqtt_msg2 = mqtt.MQTTMessage(mid=1, topic=msg2_topic.encode("utf-8"))
        mqtt_msg2.payload = " ".encode("utf-8")

        # Inject failure into the response match
        mock_ledger.match_response.side_effect = exception

        # Start task
        t = asyncio.create_task(client._process_dps_responses())

        # Load the first MQTTMessage
        await client._mqtt_client._incoming_filtered_messages[generic_topic].put(mqtt_msg1)
        await asyncio.sleep(0.1)

        # Attempt to match response ocurred (and thus, failed, due to mock)
        assert mock_ledger.match_response.call_count == 1

        # Un-inject the failure
        mock_ledger.match_response.side_effect = None

        # Load the second MQTTMessage
        await client._mqtt_client._incoming_filtered_messages[generic_topic].put(mqtt_msg2)
        await asyncio.sleep(0.1)

        # Another response match ocurred, demonstrating that the previous failure did not
        # crash the task
        assert mock_ledger.match_response.call_count == 2
        resp2 = mock_ledger.match_response.call_args[0][0]
        assert resp2.request_id == rid2
        assert resp2.status == 200
        assert resp2.body == mqtt_msg2.payload.decode("utf-8")

        assert not t.done()

        t.cancel()

    @pytest.mark.skip(reason="Currently can't figure out how to mock a generator correctly")
    @pytest.mark.it("Can be cancelled while waiting for an MQTTMessage to arrive")
    async def test_cancelled_while_waiting_for_message(self):
        pass

    @pytest.mark.it("Can be cancelled while matching Response")
    async def test_cancelled_while_matching_response(self, mocker, client):
        mock_ledger = mocker.patch.object(client, "_request_ledger", spec=rr.RequestLedger)
        mock_ledger.match_response = custom_mock.HangingAsyncMock()

        # Set up MQTTMessage
        generic_topic = mqtt_topic.get_response_topic_for_subscribe()
        topic = generic_topic.rstrip("#") + "{}/?$rid={}".format(200, "some rid")
        mqtt_msg = mqtt.MQTTMessage(mid=1, topic=topic.encode("utf-8"))
        mqtt_msg.payload = " ".encode("utf-8")

        # Start task
        t = asyncio.create_task(client._process_dps_responses())
        await asyncio.sleep(0.1)

        # Load the MQTTMessage into the MQTTClient's filtered message queue
        await client._mqtt_client._incoming_filtered_messages[generic_topic].put(mqtt_msg)

        # Matching response is hanging
        await mock_ledger.match_response.wait_for_hang()

        # Task can be cancelled
        t.cancel()
        with pytest.raises(asyncio.CancelledError):
            await t


@pytest.mark.describe("ProvisioningMQTTClient - .wait_for_disconnect()")
class TestProvisioningMQTTClientReportConnectionDrop:
    @pytest.mark.it(
        "Returns None if an expected disconnect has previously occurred in the MQTTClient"
    )
    async def test_previous_expected_disconnect(self, client):
        # Simulate expected disconnect
        client._mqtt_client._disconnection_cause = None
        client._mqtt_client.is_connected.return_value = False
        async with client._mqtt_client.disconnected_cond:
            client._mqtt_client.disconnected_cond.notify_all()

        # Reports no cause (i.e. expected disconnect)
        t = asyncio.create_task(client.wait_for_disconnect())
        await asyncio.sleep(0.1)
        assert t.done()
        assert t.result() is None

    @pytest.mark.it(
        "Waits for a disconnect to occur in the MQTTClient, and returns None once an expected disconnect occurs, if no disconnect has yet ocurred"
    )
    async def test_expected_disconnect(self, client):
        # No connection drop to report
        t = asyncio.create_task(client.wait_for_disconnect())
        await asyncio.sleep(0.1)
        assert not t.done()

        # Simulate expected disconnect
        client._mqtt_client._disconnection_cause = None
        client._mqtt_client.is_connected.return_value = False
        async with client._mqtt_client.disconnected_cond:
            client._mqtt_client.disconnected_cond.notify_all()

        # Report no cause (i.e. expected disconnect)
        await asyncio.sleep(0.1)
        assert t.done()
        assert t.result() is None

    @pytest.mark.it(
        "Returns the MQTTError that caused an unexpected disconnect in the MQTTClient, if an unexpected disconnect has already occurred"
    )
    async def test_previous_unexpected_disconnect(self, client):
        # Simulate unexpected disconnect
        cause = mqtt.MQTTError(rc=7)
        client._mqtt_client._disconnection_cause = cause
        client._mqtt_client.is_connected.return_value = False
        async with client._mqtt_client.disconnected_cond:
            client._mqtt_client.disconnected_cond.notify_all()

        # Reports the cause that is already available
        t = asyncio.create_task(client.wait_for_disconnect())
        await asyncio.sleep(0.1)
        assert t.done()
        assert t.result() is cause

    @pytest.mark.it(
        "Waits for a disconnect to occur in the MQTTClient, and returns the MQTTError that caused it once an unexpected disconnect occurs, if no disconnect has not yet ocurred"
    )
    async def test_unexpected_disconnect(self, client):
        # No connection drop to report yet
        t = asyncio.create_task(client.wait_for_disconnect())
        await asyncio.sleep(0.1)
        assert not t.done()

        # Simulate unexpected disconnect
        cause = mqtt.MQTTError(rc=7)
        client._mqtt_client._disconnection_cause = cause
        client._mqtt_client.is_connected.return_value = False
        async with client._mqtt_client.disconnected_cond:
            client._mqtt_client.disconnected_cond.notify_all()

        # Cause can now be reported
        await asyncio.sleep(0.1)
        assert t.done()
        assert t.result() is cause
