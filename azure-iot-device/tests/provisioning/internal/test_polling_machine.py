# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
import datetime
from mock import MagicMock
from azure.iot.device.provisioning.internal.request_response_provider import RequestResponseProvider
from azure.iot.device.provisioning.internal.polling_machine import PollingMachine
from azure.iot.device.provisioning.models.registration_result import RegistrationResult
from azure.iot.device.provisioning.transport import constant
import time

fake_request_id = "Request1234"
fake_retry_after = "3"
fake_operation_id = "Operation4567"
fake_status = "Flying"
fake_device_id = "MyNimbus2000"
fake_assigned_hub = "Dumbledore'sArmy"
fake_sub_status = "FlyingOnHippogriff"
fake_created_dttm = datetime.datetime(2020, 5, 17)
fake_last_update_dttm = datetime.datetime(2020, 10, 17)
fake_etag = "HighQualityFlyingBroom"
fake_symmetric_key = "Zm9vYmFy"
fake_registration_id = "MyPensieve"
fake_id_scope = "Enchanted0000Ceiling7898"
fake_success_response_topic = "$dps/registrations/res/200/?"
fake_failure_response_topic = "$dps/registrations/res/400/?"
fake_greater_429_response_topic = "$dps/registrations/res/430/?"
fake_assigning_status = "assigning"
fake_assigned_status = "assigned"


class TestRequestResponseProvider(RequestResponseProvider):
    def receive_response(self, topic, payload):
        return super(TestRequestResponseProvider, self)._receive_response(topic, payload)


@pytest.fixture
def mock_request_response_provider(mocker):
    return mocker.MagicMock(spec=TestRequestResponseProvider)


@pytest.fixture
def mock_polling_machine(mocker, mock_request_response_provider):
    state_based_mqtt = MagicMock()
    mock_init_request_response_provider = mocker.patch(
        "azure.iot.device.provisioning.internal.polling_machine.RequestResponseProvider"
    )
    mock_init_request_response_provider.return_value = mock_request_response_provider
    mock_polling_machine = PollingMachine(state_based_mqtt)
    return mock_polling_machine


@pytest.mark.describe("PollingMachine - Register")
class TestRegister:
    @pytest.mark.it("register in polling machine calls subscribe on request response provider")
    def test_register_calls_subscribe_on_request_response_provider(self, mock_polling_machine):
        mock_request_response_provider = mock_polling_machine._request_response_provider
        mock_polling_machine.register()

        mock_request_response_provider.subscribe.assert_called_once_with(
            topic=constant.SUBSCRIBE_TOPIC_PROVISIONING,
            callback=mock_polling_machine._on_subscribe_completed,
        )

    @pytest.mark.it("subscription being complete calls send request on request response provider")
    def test_on_subscribe_completed_calls_send_register_request_on_request_response_provider(
        self, mock_polling_machine, mocker
    ):
        mock_init_uuid = mocker.patch(
            "azure.iot.device.provisioning.internal.polling_machine.uuid.uuid4"
        )
        mock_init_uuid.return_value = fake_request_id
        mock_init_query_timer = mocker.patch(
            "azure.iot.device.provisioning.internal.polling_machine.Timer"
        )
        mock_query_timer = mock_init_query_timer.return_value
        mocker.patch.object(mock_query_timer, "start")

        mock_polling_machine.state = "initializing"
        mock_request_response_provider = mock_polling_machine._request_response_provider

        mock_polling_machine._on_subscribe_completed()

        mock_request_response_provider.send_request.assert_called_once_with(
            rid=fake_request_id,
            topic=constant.PUBLISH_TOPIC_REGISTRATION.format(fake_request_id),
            request=" ",
            callback=mock_polling_machine._on_register_response_received,
        )


@pytest.mark.describe("PollingMachine - Response from Register")
class TestRegisterResponse:
    # Change the timeout so that the test does not hang for more time
    constant.DEFAULT_TIMEOUT_INTERVAL = 3
    constant.DEFAULT_POLLING_INTERVAL = 0.2

    @pytest.mark.it("response from register with a status of assigning starts querying")
    def test_receive_register_response_assigning_does_query_with_operation_id(self, mocker):
        state_based_mqtt = MagicMock()
        mock_request_response_provider = TestRequestResponseProvider(state_based_mqtt)
        polling_machine = PollingMachine(state_based_mqtt)

        polling_machine._request_response_provider = mock_request_response_provider
        mocker.patch.object(mock_request_response_provider, "subscribe")
        mocker.patch.object(mock_request_response_provider, "publish")

        # to transition into initializing
        polling_machine.register(callback=MagicMock())

        mock_init_uuid = mocker.patch(
            "azure.iot.device.provisioning.internal.polling_machine.uuid.uuid4"
        )
        mock_init_uuid.return_value = fake_request_id

        # to transition into registering
        polling_machine._on_subscribe_completed()

        # reset mock to generate different request id for query
        mock_init_uuid.reset_mock()
        fake_request_id_query = "Request4567"
        mock_init_uuid.return_value = fake_request_id_query

        fake_topic = fake_success_response_topic + "$rid={}&retry-after={}".format(
            fake_request_id, fake_retry_after
        )
        fake_payload_result = (
            '{"operationId":"' + fake_operation_id + '","status":"' + fake_assigning_status + '"}'
        )

        mock_init_polling_timer = mocker.patch(
            "azure.iot.device.provisioning.internal.polling_machine.Timer"
        )

        # Complete string pre-fixed by a b is the one that works for all versions of python
        # or a encode on a string works for all versions of python
        # For only python 3 , bytes(JsonString, "utf-8") can be done
        mock_request_response_provider.receive_response(
            fake_topic, fake_payload_result.encode("utf-8")
        )

        # call polling timer's time up call to simulate polling
        time_up_call = mock_init_polling_timer.call_args[0][1]
        time_up_call()

        assert mock_request_response_provider.publish.call_count == 2
        mock_request_response_provider.publish.assert_any_call(
            topic=constant.PUBLISH_TOPIC_QUERYING.format(fake_request_id_query, fake_operation_id),
            request=" ",
        )

    @pytest.mark.it(
        "response from register with a status of assigned completes registration process"
    )
    def test_receive_register_response_assigned_completes_registration(self, mocker):
        state_based_mqtt = MagicMock()
        mock_request_response_provider = TestRequestResponseProvider(state_based_mqtt)
        polling_machine = PollingMachine(state_based_mqtt)

        polling_machine._request_response_provider = mock_request_response_provider
        mocker.patch.object(mock_request_response_provider, "subscribe")
        mocker.patch.object(mock_request_response_provider, "publish")
        mocker.patch.object(mock_request_response_provider, "disconnect")

        # to transition into initializing
        mock_callback = MagicMock()
        polling_machine.register(callback=mock_callback)

        mock_init_uuid = mocker.patch(
            "azure.iot.device.provisioning.internal.polling_machine.uuid.uuid4"
        )
        mock_init_uuid.return_value = fake_request_id

        # to transition into registering
        polling_machine._on_subscribe_completed()

        fake_topic = fake_success_response_topic + "$rid={}&retry-after={}".format(
            fake_request_id, fake_retry_after
        )

        fake_registration_state = (
            '{"registrationId":"'
            + fake_registration_id
            + '","assignedHub":"'
            + fake_assigned_hub
            + '","deviceId":"'
            + fake_device_id
            + '","substatus":"'
            + fake_sub_status
            + '"}'
        )

        fake_payload_result = (
            '{"operationId":"'
            + fake_operation_id
            + '","status":"'
            + fake_assigned_status
            + '","registrationState":'
            + fake_registration_state
            + "}"
        )

        mock_request_response_provider.receive_response(
            fake_topic, fake_payload_result.encode("utf-8")
        )

        polling_machine._on_disconnect_completed_register()

        assert mock_request_response_provider.publish.call_count == 1
        # assert polling_machine.on_registration_complete.call_count == 1
        assert mock_callback.call_count == 1
        assert isinstance(mock_callback.call_args[0][0], RegistrationResult)
        registration_result = mock_callback.call_args[0][0]

        registration_result.request_id == fake_request_id
        registration_result.operation_id == fake_operation_id
        registration_result.status == fake_assigned_status
        registration_result.registration_state.device_id == fake_device_id
        registration_result.registration_state.sub_status == fake_sub_status

    @pytest.mark.it(
        "response from register that failed calls callback of registration process with error"
    )
    def test_receive_register_response_failure_calls_callback_of_register_error(self, mocker):
        state_based_mqtt = MagicMock()
        mock_request_response_provider = TestRequestResponseProvider(state_based_mqtt)
        polling_machine = PollingMachine(state_based_mqtt)
        polling_machine._request_response_provider = mock_request_response_provider

        mocker.patch.object(mock_request_response_provider, "subscribe")
        mocker.patch.object(mock_request_response_provider, "publish")
        mocker.patch.object(mock_request_response_provider, "disconnect")

        # to transition into initializing
        mock_callback = MagicMock()
        polling_machine.register(callback=mock_callback)

        mock_init_uuid = mocker.patch(
            "azure.iot.device.provisioning.internal.polling_machine.uuid.uuid4"
        )
        mock_init_uuid.return_value = fake_request_id

        # to transition into registering
        polling_machine._on_subscribe_completed()

        fake_topic = fake_failure_response_topic + "$rid={}".format(fake_request_id)

        fake_payload_result = "HelloHogwarts"
        mock_request_response_provider.receive_response(
            fake_topic, fake_payload_result.encode("utf-8")
        )

        polling_machine._on_disconnect_completed_error()

        assert mock_callback.call_count == 1
        assert isinstance(mock_callback.call_args[0][1], ValueError)
        assert mock_callback.call_args[0][1].args[0] == "Incoming message failure"

    @pytest.mark.it(
        "response from register with some unknown status calls callback of registration process with error"
    )
    def test_receive_register_response_some_unknown_status_calls_callback_of_register_error(
        self, mocker
    ):
        state_based_mqtt = MagicMock()
        mock_request_response_provider = TestRequestResponseProvider(state_based_mqtt)
        polling_machine = PollingMachine(state_based_mqtt)
        polling_machine._request_response_provider = mock_request_response_provider

        mocker.patch.object(mock_request_response_provider, "subscribe")
        mocker.patch.object(mock_request_response_provider, "publish")
        mocker.patch.object(mock_request_response_provider, "disconnect")

        # to transition into initializing
        mock_callback = MagicMock()
        polling_machine.register(callback=mock_callback)

        mock_init_uuid = mocker.patch(
            "azure.iot.device.provisioning.internal.polling_machine.uuid.uuid4"
        )
        mock_init_uuid.return_value = fake_request_id

        # to transition into registering
        polling_machine._on_subscribe_completed()

        fake_unknown_status = "disabled"
        fake_topic = fake_success_response_topic + "$rid={}".format(fake_request_id)
        fake_payload_result = (
            '{"operationId":"' + fake_operation_id + '","status":"' + fake_unknown_status + '"}'
        )

        mock_request_response_provider.receive_response(
            fake_topic, fake_payload_result.encode("utf-8")
        )

        polling_machine._on_disconnect_completed_error()

        assert mock_callback.call_count == 1
        assert isinstance(mock_callback.call_args[0][1], ValueError)
        assert mock_callback.call_args[0][1].args[0] == "Other types of failure have occurred."
        assert mock_callback.call_args[0][1].args[1] == fake_payload_result

    @pytest.mark.it("response from register with status code > 429 calls register again")
    def test_receive_register_response_greater_than_429_does_register_again(self, mocker):
        state_based_mqtt = MagicMock()
        mock_request_response_provider = TestRequestResponseProvider(state_based_mqtt)
        polling_machine = PollingMachine(state_based_mqtt)
        polling_machine._request_response_provider = mock_request_response_provider
        mocker.patch.object(mock_request_response_provider, "subscribe")
        mocker.patch.object(mock_request_response_provider, "publish")

        # to transition into initializing
        polling_machine.register(callback=MagicMock())

        mock_init_uuid = mocker.patch(
            "azure.iot.device.provisioning.internal.polling_machine.uuid.uuid4"
        )
        mock_init_uuid.return_value = fake_request_id

        # to transition into registering
        polling_machine._on_subscribe_completed()

        # reset mock to generate different request id for second time register
        mock_init_uuid.reset_mock()
        fake_request_id_2 = "Request4567"
        mock_init_uuid.return_value = fake_request_id_2

        fake_topic = fake_greater_429_response_topic + "$rid={}&retry-after={}".format(
            fake_request_id, fake_retry_after
        )

        fake_payload_result = "HelloHogwarts"

        mock_init_polling_timer = mocker.patch(
            "azure.iot.device.provisioning.internal.polling_machine.Timer"
        )

        mock_request_response_provider.receive_response(
            fake_topic, fake_payload_result.encode("utf-8")
        )

        # call polling timer's time up call to simulate polling
        time_up_call = mock_init_polling_timer.call_args[0][1]
        time_up_call()

        assert mock_request_response_provider.publish.call_count == 2
        mock_request_response_provider.publish.assert_any_call(
            topic=constant.PUBLISH_TOPIC_REGISTRATION.format(fake_request_id_2), request=" "
        )

    @pytest.mark.it("timeout leads to callback of registration process with error")
    def test_receive_register_response_after_query_time_passes_calls_callback_with_error(
        self, mocker
    ):
        state_based_mqtt = MagicMock()
        mock_request_response_provider = TestRequestResponseProvider(state_based_mqtt)
        polling_machine = PollingMachine(state_based_mqtt)
        polling_machine._request_response_provider = mock_request_response_provider

        mocker.patch.object(mock_request_response_provider, "subscribe")
        mocker.patch.object(mock_request_response_provider, "publish")
        mocker.patch.object(mock_request_response_provider, "disconnect")

        # to transition into initializing
        mock_callback = MagicMock()
        polling_machine.register(callback=mock_callback)

        mock_init_uuid = mocker.patch(
            "azure.iot.device.provisioning.internal.polling_machine.uuid.uuid4"
        )
        mock_init_uuid.return_value = fake_request_id

        # to transition into registering
        polling_machine._on_subscribe_completed()

        # sleep so that it times out query
        time.sleep(constant.DEFAULT_TIMEOUT_INTERVAL + 1)

        polling_machine._on_disconnect_completed_error()

        assert mock_request_response_provider.publish.call_count == 1
        assert mock_callback.call_count == 1
        print(mock_callback.call_args)
        assert mock_callback.call_args[0][1].args[0] == "Time is up for query timer"


@pytest.mark.describe("PollingMachine - Response from Query")
class TestQueryResponse:
    # Change the timeout so that the test does not hang for more time
    constant.DEFAULT_TIMEOUT_INTERVAL = 3
    constant.DEFAULT_POLLING_INTERVAL = 0.2

    @pytest.mark.it("response from query with a status of assigning does querying again")
    def test_receive_query_response_assigning_does_query_again_with_same_operation_id(self, mocker):
        state_based_mqtt = MagicMock()
        mock_request_response_provider = TestRequestResponseProvider(state_based_mqtt)
        polling_machine = PollingMachine(state_based_mqtt)
        polling_machine._request_response_provider = mock_request_response_provider

        mocker.patch.object(mock_request_response_provider, "subscribe")
        mocker.patch.object(mock_request_response_provider, "publish")

        # to transition into initializing
        polling_machine.register(callback=MagicMock())

        mock_init_uuid = mocker.patch(
            "azure.iot.device.provisioning.internal.polling_machine.uuid.uuid4"
        )
        mock_init_uuid.return_value = fake_request_id

        # to transition into registering
        polling_machine._on_subscribe_completed()

        # reset mock to generate different request id for first query
        mock_init_uuid.reset_mock()
        fake_request_id_query = "Request4567"
        mock_init_uuid.return_value = fake_request_id_query

        fake_register_topic = fake_success_response_topic + "$rid={}".format(fake_request_id)
        fake_register_payload_result = (
            '{"operationId":"' + fake_operation_id + '","status":"' + fake_assigning_status + '"}'
        )

        mock_init_polling_timer = mocker.patch(
            "azure.iot.device.provisioning.internal.polling_machine.Timer"
        )

        # Response for register to transition to waiting polling
        mock_request_response_provider.receive_response(
            fake_register_topic, fake_register_payload_result.encode("utf-8")
        )

        # call polling timer's time up call to simulate polling
        time_up_call = mock_init_polling_timer.call_args[0][1]
        time_up_call()

        # reset mock to generate different request id for second query
        mock_init_uuid.reset_mock()
        fake_request_id_query_2 = "Request7890"
        mock_init_uuid.return_value = fake_request_id_query_2

        fake_query_topic_1 = fake_success_response_topic + "$rid={}".format(fake_request_id_query)
        fake_query_payload_result = (
            '{"operationId":"' + fake_operation_id + '","status":"' + fake_assigning_status + '"}'
        )

        mock_init_polling_timer.reset_mock()

        mock_request_response_provider.receive_response(
            fake_query_topic_1, fake_query_payload_result.encode("utf-8")
        )

        # call polling timer's time up call to simulate polling
        time_up_call = mock_init_polling_timer.call_args[0][1]
        time_up_call()

        assert mock_request_response_provider.publish.call_count == 3
        mock_request_response_provider.publish.assert_any_call(
            topic=constant.PUBLISH_TOPIC_QUERYING.format(
                fake_request_id_query_2, fake_operation_id
            ),
            request=" ",
        )

    @pytest.mark.it("response from register with a status of assigned completes registration")
    def test_receive_query_response_assigned_completes_registration(self, mocker):
        state_based_mqtt = MagicMock()
        mock_request_response_provider = TestRequestResponseProvider(state_based_mqtt)
        polling_machine = PollingMachine(state_based_mqtt)
        polling_machine._request_response_provider = mock_request_response_provider

        mocker.patch.object(mock_request_response_provider, "subscribe")
        mocker.patch.object(mock_request_response_provider, "publish")
        mocker.patch.object(mock_request_response_provider, "disconnect")

        # to transition into initializing
        mock_callback = MagicMock()
        polling_machine.register(callback=mock_callback)

        mock_init_uuid = mocker.patch(
            "azure.iot.device.provisioning.internal.polling_machine.uuid.uuid4"
        )
        mock_init_uuid.return_value = fake_request_id

        # to transition into registering
        polling_machine._on_subscribe_completed()

        # reset mock to generate different request id for first query
        mock_init_uuid.reset_mock()
        fake_request_id_query = "Request4567"
        mock_init_uuid.return_value = fake_request_id_query

        fake_register_topic = fake_success_response_topic + "$rid={}".format(fake_request_id)
        fake_register_payload_result = (
            '{"operationId":"' + fake_operation_id + '","status":"' + fake_assigning_status + '"}'
        )

        mock_init_polling_timer = mocker.patch(
            "azure.iot.device.provisioning.internal.polling_machine.Timer"
        )

        # Response for register to transition to waiting and polling
        mock_request_response_provider.receive_response(
            fake_register_topic, fake_register_payload_result.encode("utf-8")
        )

        # call polling timer's time up call to simulate polling
        time_up_call = mock_init_polling_timer.call_args[0][1]
        time_up_call()

        fake_query_topic_1 = fake_success_response_topic + "$rid={}".format(fake_request_id_query)

        fake_registration_state = (
            '{"registrationId":"'
            + fake_registration_id
            + '","assignedHub":"'
            + fake_assigned_hub
            + '","deviceId":"'
            + fake_device_id
            + '","substatus":"'
            + fake_sub_status
            + '"}'
        )

        fake_query_payload_result = (
            '{"operationId":"'
            + fake_operation_id
            + '","status":"'
            + fake_assigned_status
            + '","registrationState":'
            + fake_registration_state
            + "}"
        )

        # Response for query
        mock_request_response_provider.receive_response(
            fake_query_topic_1, fake_query_payload_result.encode("utf-8")
        )

        polling_machine._on_disconnect_completed_register()

        assert mock_request_response_provider.publish.call_count == 2
        assert mock_callback.call_count == 1
        assert isinstance(mock_callback.call_args[0][0], RegistrationResult)

    @pytest.mark.it(
        "response from a query that failed calls callback of registration process with error"
    )
    def test_receive_query_response_failure_calls_callback_of_register_error(self, mocker):
        state_based_mqtt = MagicMock()
        mock_request_response_provider = TestRequestResponseProvider(state_based_mqtt)
        polling_machine = PollingMachine(state_based_mqtt)
        polling_machine._request_response_provider = mock_request_response_provider

        mocker.patch.object(mock_request_response_provider, "subscribe")
        mocker.patch.object(mock_request_response_provider, "publish")
        mocker.patch.object(mock_request_response_provider, "disconnect")

        # to transition into initializing
        mock_callback = MagicMock()
        polling_machine.register(callback=mock_callback)

        mock_init_uuid = mocker.patch(
            "azure.iot.device.provisioning.internal.polling_machine.uuid.uuid4"
        )
        mock_init_uuid.return_value = fake_request_id

        # to transition into registering
        polling_machine._on_subscribe_completed()

        # reset mock to generate different request id for first query
        mock_init_uuid.reset_mock()
        fake_request_id_query = "Request4567"
        mock_init_uuid.return_value = fake_request_id_query

        fake_register_topic = fake_success_response_topic + "$rid={}".format(fake_request_id)
        fake_register_payload_result = (
            '{"operationId":"' + fake_operation_id + '","status":"' + fake_assigning_status + '"}'
        )

        mock_init_polling_timer = mocker.patch(
            "azure.iot.device.provisioning.internal.polling_machine.Timer"
        )

        # Response for register to transition to waiting and polling
        mock_request_response_provider.receive_response(
            fake_register_topic, fake_register_payload_result.encode("utf-8")
        )

        # call polling timer's time up call to simulate polling
        time_up_call = mock_init_polling_timer.call_args[0][1]
        time_up_call()

        fake_query_topic_1 = fake_failure_response_topic + "$rid={}".format(fake_request_id_query)
        fake_query_payload_result = "HelloHogwarts"

        # Response for query
        mock_request_response_provider.receive_response(
            fake_query_topic_1, fake_query_payload_result.encode("utf-8")
        )

        polling_machine._on_disconnect_completed_error()

        assert mock_callback.call_count == 1
        assert isinstance(mock_callback.call_args[0][1], ValueError)
        assert mock_callback.call_args[0][1].args[0] == "Incoming message failure"

    @pytest.mark.it("response from query with status code > 429 does query again")
    def test_receive_query_response_greater_than_429_does_query_again_with_same_operation_id(
        self, mocker
    ):
        state_based_mqtt = MagicMock()
        mock_request_response_provider = TestRequestResponseProvider(state_based_mqtt)
        polling_machine = PollingMachine(state_based_mqtt)
        polling_machine._request_response_provider = mock_request_response_provider

        mocker.patch.object(mock_request_response_provider, "subscribe")
        mocker.patch.object(mock_request_response_provider, "publish")

        # to transition into initializing
        polling_machine.register(callback=MagicMock())

        mock_init_uuid = mocker.patch(
            "azure.iot.device.provisioning.internal.polling_machine.uuid.uuid4"
        )
        mock_init_uuid.return_value = fake_request_id

        # to transition into registering
        polling_machine._on_subscribe_completed()

        # reset mock to generate different request id for first query
        mock_init_uuid.reset_mock()
        fake_request_id_query = "Request4567"
        mock_init_uuid.return_value = fake_request_id_query

        fake_register_topic = fake_success_response_topic + "$rid={}".format(fake_request_id)
        fake_register_payload_result = (
            '{"operationId":"' + fake_operation_id + '","status":"' + fake_assigning_status + '"}'
        )

        mock_init_polling_timer = mocker.patch(
            "azure.iot.device.provisioning.internal.polling_machine.Timer"
        )

        # Response for register to transition to waiting polling
        mock_request_response_provider.receive_response(
            fake_register_topic, fake_register_payload_result.encode("utf-8")
        )

        # call polling timer's time up call to simulate polling
        time_up_call = mock_init_polling_timer.call_args[0][1]
        time_up_call()

        # reset mock to generate different request id for second query
        mock_init_uuid.reset_mock()
        fake_request_id_query_2 = "Request7890"
        mock_init_uuid.return_value = fake_request_id_query_2

        fake_query_topic_1 = fake_greater_429_response_topic + "$rid={}".format(
            fake_request_id_query
        )
        fake_query_payload_result = "HelloHogwarts"

        mock_init_polling_timer.reset_mock()

        # Response for query
        mock_request_response_provider.receive_response(
            fake_query_topic_1, fake_query_payload_result.encode("utf-8")
        )

        # call polling timer's time up call to simulate polling
        time_up_call = mock_init_polling_timer.call_args[0][1]
        time_up_call()

        assert mock_request_response_provider.publish.call_count == 3
        mock_request_response_provider.publish.assert_any_call(
            topic=constant.PUBLISH_TOPIC_QUERYING.format(
                fake_request_id_query_2, fake_operation_id
            ),
            request=" ",
        )


@pytest.mark.describe("PollingMachine - Cancel")
class TestCancel:
    # Change the timeout so that the test does not hang for more time
    constant.DEFAULT_TIMEOUT_INTERVAL = 3
    constant.DEFAULT_POLLING_INTERVAL = 0.2

    @pytest.mark.it(
        "cancel calls disconnect on request response provider and calls cancel callback"
    )
    def test_cancel_disconnects_on_request_response_provider_and_calls_callback(
        self, mocker, mock_polling_machine
    ):
        mock_request_response_provider = mock_polling_machine._request_response_provider

        mock_polling_machine.register(callback=MagicMock())

        mock_cancel_callback = MagicMock()
        mock_polling_machine.cancel(mock_cancel_callback)

        mock_request_response_provider.disconnect.assert_called_once_with(
            callback=mock_polling_machine._on_disconnect_completed_cancel
        )

        mock_polling_machine._on_disconnect_completed_cancel()

        assert mock_cancel_callback.call_count == 1

    @pytest.mark.it(
        "cancel calls disconnect on request response provider, clears timers and calls cancel callback"
    )
    def test_register_and_cancel_clears_timers_and_disconnects(self, mocker):
        state_based_mqtt = MagicMock()
        mock_request_response_provider = TestRequestResponseProvider(state_based_mqtt)
        polling_machine = PollingMachine(state_based_mqtt)
        polling_machine._request_response_provider = mock_request_response_provider

        mocker.patch.object(mock_request_response_provider, "subscribe")
        mocker.patch.object(mock_request_response_provider, "publish")
        mocker.patch.object(mock_request_response_provider, "disconnect")

        # to transition into initializing
        polling_machine.register(callback=MagicMock())

        mock_init_uuid = mocker.patch(
            "azure.iot.device.provisioning.internal.polling_machine.uuid.uuid4"
        )
        mock_init_uuid.return_value = fake_request_id

        # to transition into registering
        polling_machine._on_subscribe_completed()

        # reset mock to generate different request id for query
        mock_init_uuid.reset_mock()
        fake_request_id_query = "Request4567"
        mock_init_uuid.return_value = fake_request_id_query

        fake_topic = fake_success_response_topic + "$rid={}&retry-after={}".format(
            fake_request_id, fake_retry_after
        )
        fake_payload_result = (
            '{"operationId":"' + fake_operation_id + '","status":"' + fake_assigning_status + '"}'
        )

        mock_request_response_provider.receive_response(
            fake_topic, fake_payload_result.encode("utf-8")
        )

        polling_timer = polling_machine._polling_timer
        query_timer = polling_machine._query_timer
        poling_timer_cancel = mocker.patch.object(polling_timer, "cancel")
        query_timer_cancel = mocker.patch.object(query_timer, "cancel")

        mock_cancel_callback = MagicMock()
        polling_machine.cancel(mock_cancel_callback)

        assert poling_timer_cancel.call_count == 1
        assert query_timer_cancel.call_count == 1

        mock_request_response_provider.disconnect.assert_called_once_with(
            callback=polling_machine._on_disconnect_completed_cancel
        )
        polling_machine._on_disconnect_completed_cancel()

        assert mock_cancel_callback.call_count == 1
