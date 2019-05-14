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
    state_based_mqtt = MagicMock()
    request_response_provider = RequestResponseProvider(state_based_mqtt)
    request_response_provider.on_response_received = MagicMock()
    return request_response_provider


@pytest.mark.it("connect calls connect on state based provider with given callback")
def test_connect_calls_connect_on_state_based_provider_with_provided_callback(
    request_response_provider
):
    mock_mqtt_state_based_provider = request_response_provider._state_based_provider
    mock_callback = MagicMock()
    request_response_provider.connect(mock_callback)
    mock_mqtt_state_based_provider.connect.assert_called_once_with(callback=mock_callback)


@pytest.mark.it("connect calls connect on state based provider with defined callback")
def test_connect_calls_connect_on_state_based_provider(request_response_provider):
    mock_mqtt_state_based_provider = request_response_provider._state_based_provider
    request_response_provider.connect()
    mock_mqtt_state_based_provider.connect.assert_called_once_with(
        callback=request_response_provider._on_connection_state_change
    )


@pytest.mark.it("disconnect calls disconnect on state based provider with given callback")
def test_disconnect_calls_disconnect_on_state_based_provider_with_provided_callback(
    request_response_provider
):
    mock_mqtt_state_based_provider = request_response_provider._state_based_provider
    mock_callback = MagicMock()
    request_response_provider.disconnect(mock_callback)
    mock_mqtt_state_based_provider.disconnect.assert_called_once_with(callback=mock_callback)


@pytest.mark.it("disconnect calls disconnect on state based provider with defined callback")
def test_disconnect_calls_disconnect_on_state_based_provider(request_response_provider):
    mock_mqtt_state_based_provider = request_response_provider._state_based_provider
    request_response_provider.disconnect()
    mock_mqtt_state_based_provider.disconnect.assert_called_once_with(
        callback=request_response_provider._on_connection_state_change
    )


@pytest.mark.it("send request calls publish on state based provider with message")
def test_send_request_calls_publish_on_state_based_provider(request_response_provider):
    mock_mqtt_state_based_provider = request_response_provider._state_based_provider
    req = "Leviosa"
    mock_callback = MagicMock()
    request_response_provider.send_request(
        rid=fake_rid, topic=fake_request_topic.format(fake_rid), request=req, callback=mock_callback
    )
    assert mock_mqtt_state_based_provider.publish.call_count == 1
    assert mock_mqtt_state_based_provider.publish.call_args[1][
        "topic"
    ] == fake_request_topic.format(fake_rid)
    assert mock_mqtt_state_based_provider.publish.call_args[1]["message"] == req


@pytest.mark.it("publish calls publish on state based provider with message")
def test_publish_calls_publish_on_state_based_provider(request_response_provider):
    mock_mqtt_state_based_provider = request_response_provider._state_based_provider
    req = "Leviosa"
    request_response_provider.publish(topic=fake_request_topic.format(fake_rid), request=req)

    assert mock_mqtt_state_based_provider.publish.call_count == 1
    assert mock_mqtt_state_based_provider.publish.call_args[1][
        "topic"
    ] == fake_request_topic.format(fake_rid)
    assert mock_mqtt_state_based_provider.publish.call_args[1]["message"] == req


@pytest.mark.it("subscribe calls subscribe on state based provider with topic and given callback")
def test_subscribe_calls_subscribe_on_state_based_provider_with_provided_callback(
    request_response_provider
):
    mock_mqtt_state_based_provider = request_response_provider._state_based_provider
    mock_callback = MagicMock()
    request_response_provider.subscribe(fake_subscribe_topic, mock_callback)
    mock_mqtt_state_based_provider.subscribe.assert_called_once_with(
        topic=fake_subscribe_topic, callback=mock_callback
    )


@pytest.mark.it("subscribe calls subscribe on state based provider with topic and defined callback")
def test_subscribe_calls_subscribe_on_state_based_provider(request_response_provider):
    mock_mqtt_state_based_provider = request_response_provider._state_based_provider
    request_response_provider.subscribe(fake_subscribe_topic)
    mock_mqtt_state_based_provider.subscribe.assert_called_once_with(
        topic=fake_subscribe_topic, callback=request_response_provider._on_subscribe_completed
    )


@pytest.mark.it(
    "unsubscribe calls unsubscribe on state based provider with topic and given callback"
)
def test_unsubscribe_calls_unsubscribe_on_state_based_provider_with_provided_callback(
    request_response_provider
):
    mock_mqtt_state_based_provider = request_response_provider._state_based_provider
    mock_callback = MagicMock()
    request_response_provider.unsubscribe(fake_subscribe_topic, mock_callback)
    mock_mqtt_state_based_provider.unsubscribe.assert_called_once_with(
        topic=fake_subscribe_topic, callback=mock_callback
    )


@pytest.mark.it(
    "unsubscribe calls unsubscribe on state based provider with topic and defined callback"
)
def test_unsubscribe_calls_unsubscribe_on_state_based_provider(request_response_provider):
    mock_mqtt_state_based_provider = request_response_provider._state_based_provider
    request_response_provider.unsubscribe(fake_subscribe_topic)
    mock_mqtt_state_based_provider.unsubscribe.assert_called_once_with(
        topic=fake_subscribe_topic, callback=request_response_provider._on_unsubscribe_completed
    )


@pytest.mark.it("message received calls callabck passed with payload")
def test_on_provider_message_received_receives_response_and_calls_callback(
    request_response_provider
):
    mock_mqtt_state_based_provider = request_response_provider._state_based_provider
    req = "Leviosa"

    mock_callback = MagicMock()
    request_response_provider.send_request(
        rid=fake_rid, topic=fake_request_topic.format(fake_rid), request=req, callback=mock_callback
    )
    assigning_status = "assigning"

    payload = '{"operationId":"' + fake_operation_id + '","status":"' + assigning_status + '"}'

    mock_payload = payload.encode("utf-8")
    mock_mqtt_state_based_provider.on_state_based_provider_message_received(
        fake_success_response_topic, mock_payload
    )

    topic_parts = fake_success_response_topic.split("$")
    key_value_dict = urllib.parse.parse_qs(topic_parts[POS_QUERY_PARAM_PORTION])
    mock_callback.assert_called_once_with(topic_parts[POS_URL_PORTION], key_value_dict, payload)
