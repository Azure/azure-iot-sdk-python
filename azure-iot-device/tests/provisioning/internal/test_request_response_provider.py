# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
import six.moves.urllib as urllib
from mock import MagicMock
from azure.iot.device.provisioning.internal.request_response_provider import RequestResponseProvider


fake_rid = "Request1234"
fake_operation_id = "Operation4567"
fake_request_topic = "$ministryservices/wizardregistrations/rid={}"
fake_subscribe_topic = "$dps/registrations/res/#"
fake_success_response_topic = "$dps/registrations/res/9999/?$rid={}".format(fake_rid)
POS_STATUS_CODE_IN_TOPIC = 3
POS_QUERY_PARAM_PORTION = 2
POS_URL_PORTION = 1


@pytest.fixture
def request_response_provider():
    provisioning_pipeline = MagicMock()
    request_response_provider = RequestResponseProvider(provisioning_pipeline)
    request_response_provider.on_response_received = MagicMock()
    return request_response_provider


@pytest.mark.describe("RequestResponseProvider")
class TestRequestResponseProvider:
    @pytest.mark.it("connect calls connect on state based provider with given callback")
    def test_connect_calls_connect_on_provisioning_pipeline_with_provided_callback(
        self, request_response_provider
    ):
        mock_provisioning_pipeline = request_response_provider._provisioning_pipeline
        mock_callback = MagicMock()
        request_response_provider.connect(mock_callback)
        mock_provisioning_pipeline.connect.assert_called_once_with(callback=mock_callback)

    @pytest.mark.it("connect calls connect on state based provider with defined callback")
    def test_connect_calls_connect_on_provisioning_pipeline(self, request_response_provider):
        mock_provisioning_pipeline = request_response_provider._provisioning_pipeline
        request_response_provider.connect()
        mock_provisioning_pipeline.connect.assert_called_once_with(
            callback=request_response_provider._on_connection_state_change
        )

    @pytest.mark.it("disconnect calls disconnect on state based provider with given callback")
    def test_disconnect_calls_disconnect_on_provisioning_pipeline_with_provided_callback(
        self, request_response_provider
    ):
        mock_provisioning_pipeline = request_response_provider._provisioning_pipeline
        mock_callback = MagicMock()
        request_response_provider.disconnect(mock_callback)
        mock_provisioning_pipeline.disconnect.assert_called_once_with(callback=mock_callback)

    @pytest.mark.it("disconnect calls disconnect on state based provider with defined callback")
    def test_disconnect_calls_disconnect_on_provisioning_pipeline(self, request_response_provider):
        mock_provisioning_pipeline = request_response_provider._provisioning_pipeline
        request_response_provider.disconnect()
        mock_provisioning_pipeline.disconnect.assert_called_once_with(
            callback=request_response_provider._on_connection_state_change
        )

    @pytest.mark.it("send request calls send request on pipeline with request")
    def test_send_request_calls_publish_on_provisioning_pipeline(self, request_response_provider):
        mock_provisioning_pipeline = request_response_provider._provisioning_pipeline
        req = "Leviosa"
        mock_callback = MagicMock()
        request_response_provider.send_request(
            rid=fake_rid,
            request_payload=req,
            operation_id=fake_operation_id,
            callback_on_response=mock_callback,
        )
        assert mock_provisioning_pipeline.send_request.call_count == 1
        print(mock_provisioning_pipeline.send_request.call_args)
        assert (
            mock_provisioning_pipeline.send_request.call_args[1]["operation_id"]
            == fake_operation_id
        )
        assert mock_provisioning_pipeline.send_request.call_args[1]["rid"] == fake_rid

        assert mock_provisioning_pipeline.send_request.call_args[1]["request_payload"] == req

    @pytest.mark.it(
        "enable_responses calls enable_responses on pipeline with topic and given callback"
    )
    def test_enable_responses_calls_enable_responses_on_provisioning_pipeline_with_provided_callback(
        self, request_response_provider
    ):
        mock_provisioning_pipeline = request_response_provider._provisioning_pipeline
        mock_callback = MagicMock()
        request_response_provider.enable_responses(mock_callback)
        mock_provisioning_pipeline.enable_responses.assert_called_once_with(callback=mock_callback)

    @pytest.mark.it(
        "enable_responses calls enable_responses on pipeline with topic and defined callback"
    )
    def test_enable_responses_calls_enable_responses_on_provisioning_pipeline(
        self, request_response_provider
    ):
        mock_provisioning_pipeline = request_response_provider._provisioning_pipeline
        request_response_provider.enable_responses()
        mock_provisioning_pipeline.enable_responses.assert_called_once_with(
            callback=request_response_provider._on_subscribe_completed
        )

    @pytest.mark.it("unsubscribe calls unsubscribe on pipeline with topic and given callback")
    def test_disable_responses_calls_disable_responses_on_provisioning_pipeline_with_provided_callback(
        self, request_response_provider
    ):
        mock_provisioning_pipeline = request_response_provider._provisioning_pipeline
        mock_callback = MagicMock()
        request_response_provider.disable_responses(mock_callback)
        mock_provisioning_pipeline.disable_responses.assert_called_once_with(callback=mock_callback)

    @pytest.mark.it(
        "disable_response calls disable_response on pipeline with topic and defined callback"
    )
    def test_disable_responses_calls_disable_responses_on_provisioning_pipeline(
        self, request_response_provider
    ):
        mock_provisioning_pipeline = request_response_provider._provisioning_pipeline
        request_response_provider.disable_responses()
        mock_provisioning_pipeline.disable_responses.assert_called_once_with(
            callback=request_response_provider._on_unsubscribe_completed
        )

    @pytest.mark.it("receives message and calls callback passed with payload")
    def test_on_provider_message_received_receives_response_and_calls_callback(
        self, request_response_provider
    ):
        mock_provisioning_pipeline = request_response_provider._provisioning_pipeline
        req = "Leviosa"

        mock_callback = MagicMock()
        request_response_provider.send_request(
            rid=fake_rid,
            request_payload=req,
            operation_id=fake_operation_id,
            callback_on_response=mock_callback,
        )
        assigning_status = "assigning"

        payload = '{"operationId":"' + fake_operation_id + '","status":"' + assigning_status + '"}'

        topic_parts = fake_success_response_topic.split("$")
        key_value_dict = urllib.parse.parse_qs(topic_parts[POS_QUERY_PARAM_PORTION])

        mock_payload = payload.encode("utf-8")
        mock_provisioning_pipeline.on_provisioning_pipeline_message_received(
            fake_rid, "202", key_value_dict, mock_payload
        )

        mock_callback.assert_called_once_with(fake_rid, "202", key_value_dict, mock_payload)
