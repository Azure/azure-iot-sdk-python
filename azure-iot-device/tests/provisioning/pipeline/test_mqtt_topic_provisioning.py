# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
import logging
from azure.iot.device.provisioning.pipeline import mqtt_topic_provisioning

logging.basicConfig(level=logging.DEBUG)

# NOTE: All tests (that require it) are parametrized with multiple values for URL encoding.
# This is to show that the URL encoding is done correctly - not all URL encoding encodes
# the same way. We must always test the ' ' and '/' characters specifically, in addition
# to a generic URL encoding value (e.g. $, #, etc.)
#
# PLEASE DO THESE TESTS FOR EVEN CASES WHERE THOSE CHARACTERS SHOULD NOT OCCUR, FOR SAFETY.


@pytest.mark.describe(".get_register_topic_for_subscribe()")
class TestGetRegisterTopicForSubscribe(object):
    @pytest.mark.it("Returns the topic for subscribing to registration responses from DPS")
    def test_returns_topic(self):
        topic = mqtt_topic_provisioning.get_register_topic_for_subscribe()
        assert topic == "$dps/registrations/res/#"


@pytest.mark.describe(".get_register_topic_for_publish()")
class TestGetRegisterTopicForPublish(object):
    @pytest.mark.it("Returns the topic for publishing registration requests to DPS")
    def test_returns_topic(self):
        request_id = "3226c2f7-3d30-425c-b83b-0c34335f8220"
        expected_topic = (
            "$dps/registrations/PUT/iotdps-register/?$rid=3226c2f7-3d30-425c-b83b-0c34335f8220"
        )
        topic = mqtt_topic_provisioning.get_register_topic_for_publish(request_id)
        assert topic == expected_topic

    # NOTE: request_id should not require URL encoding.
    # No valid value would require URL encoding to be transmitted.
    # However, we encode it anyway for safety.
    @pytest.mark.it("URL encodes the request id when generating the topic")
    @pytest.mark.parametrize(
        "request_id, expected_topic",
        [
            pytest.param(
                "invalid$request?id",
                "$dps/registrations/PUT/iotdps-register/?$rid=invalid%24request%3Fid",
                id="Standard URL Encoding",
            ),
            pytest.param(
                "invalid request id",
                "$dps/registrations/PUT/iotdps-register/?$rid=invalid%20request%20id",
                id="URL Encoding of ' ' character",
            ),
            pytest.param(
                "invalid/request/id",
                "$dps/registrations/PUT/iotdps-register/?$rid=invalid%2Frequest%2Fid",
                id="URL Encoding of '/' character",
            ),
        ],
    )
    def test_url_encoding(self, request_id, expected_topic):
        topic = mqtt_topic_provisioning.get_register_topic_for_publish(request_id)
        assert topic == expected_topic


class TestGetQueryTopicForPublish(object):
    @pytest.mark.it("Returns the topic for publishing query requests to DPS")
    def test_returns_topic(self):
        request_id = "3226c2f7-3d30-425c-b83b-0c34335f8220"
        operation_id = "4.79f33f69d8eb3870.da2d9251-3097-43e9-b81c-782718485ce7"
        expected_topic = "$dps/registrations/GET/iotdps-get-operationstatus/?$rid=3226c2f7-3d30-425c-b83b-0c34335f8220&operationId=4.79f33f69d8eb3870.da2d9251-3097-43e9-b81c-782718485ce7"
        topic = mqtt_topic_provisioning.get_query_topic_for_publish(request_id, operation_id)
        assert topic == expected_topic

    # NOTE: request_id and operation_id should not require URL encoding.
    # No valid value would require URL encoding to be transmitted.
    # However, we encode them anyway for safety.
    @pytest.mark.it("URL encodes the request id and operation id")
    @pytest.mark.parametrize(
        "request_id, operation_id, expected_topic",
        [
            pytest.param(
                "invalid#request?id",
                "invalid?operation$id",
                "$dps/registrations/GET/iotdps-get-operationstatus/?$rid=invalid%23request%3Fid&operationId=invalid%3Foperation%24id",
                id="Standard URL Encoding",
            ),
            pytest.param(
                "invalid request id",
                "invalid operation id",
                "$dps/registrations/GET/iotdps-get-operationstatus/?$rid=invalid%20request%20id&operationId=invalid%20operation%20id",
                id="URL Encoding of ' ' character",
            ),
            pytest.param(
                "invalid/request/id",
                "invalid/operation/id",
                "$dps/registrations/GET/iotdps-get-operationstatus/?$rid=invalid%2Frequest%2Fid&operationId=invalid%2Foperation%2Fid",
                id="URL Encoding of '/' character",
            ),
        ],
    )
    def test_url_encoding(self, request_id, operation_id, expected_topic):
        topic = mqtt_topic_provisioning.get_query_topic_for_publish(request_id, operation_id)
        assert topic == expected_topic


@pytest.mark.describe(".is_dps_response_topic()")
class TestIsDpsResponseTopic(object):
    @pytest.mark.it("Returns True if the topic is a DPS response topic")
    @pytest.mark.parametrize(
        "topic",
        [
            pytest.param(
                "$dps/registrations/res/200/?$rid=3226c2f7-3d30-425c-b83b-0c34335f8220",
                id="Successful (200) response",
            ),
            pytest.param(
                "$dps/registrations/res/202/?$rid=3226c2f7-3d30-425c-b83b-0c34335f8220&retry-after=3",
                id="Retry-after (202) response",
            ),
            pytest.param(
                "$dps/registrations/res/401/?$rid=3226c2f7-3d30-425c-b83b-0c34335f8220",
                id="Unauthorized (401) response",
            ),
        ],
    )
    def test_is_dps_response_topic(self, topic):
        assert mqtt_topic_provisioning.is_dps_response_topic(topic)

    @pytest.mark.it("Returns False if the topic is not a DPS response topic")
    @pytest.mark.parametrize(
        "topic",
        [
            pytest.param("not a topic", id="Not a topic"),
            pytest.param(
                "$dps/registrations/PUT/iotdps-register/?$rid=3226c2f7-3d30-425c-b83b-0c34335f8220",
                id="Topic of wrong type",
            ),
            pytest.param(
                "$dps/resigtrations/res/200/?$rid=3226c2f7-3d30-425c-b83b-0c34335f8220",
                id="Malformed topic",
            ),
        ],
    )
    def test_is_not_dps_response_topic(self, topic):
        assert not mqtt_topic_provisioning.is_dps_response_topic(topic)


@pytest.mark.describe(".extract_properties_from_dps_response_topic()")
class TestExtractPropertiesFromDpsResponseTopic(object):
    @pytest.mark.it("Returns the properties from a valid DPS response topic as a dictionary")
    @pytest.mark.parametrize(
        "topic, expected_dict",
        [
            pytest.param(
                "$dps/registrations/res/200/?$rid=3226c2f7-3d30-425c-b83b-0c34335f8220",
                {"rid": "3226c2f7-3d30-425c-b83b-0c34335f8220"},
                id="Successful (200) response",
            ),
            pytest.param(
                "$dps/registrations/res/202/?$rid=3226c2f7-3d30-425c-b83b-0c34335f8220&retry-after=3",
                {"rid": "3226c2f7-3d30-425c-b83b-0c34335f8220", "retry-after": "3"},
                id="Retry-after (202) response",
            ),
            pytest.param(
                "$dps/registrations/res/401/?$rid=3226c2f7-3d30-425c-b83b-0c34335f8220",
                {"rid": "3226c2f7-3d30-425c-b83b-0c34335f8220"},
                id="Unauthorized (401) response",
            ),
            pytest.param(
                "$dps/registrations/res/200/?$rid=3226c2f7-3d30-425c-b83b-0c34335f8220&foo=value1&bar=value2&buzz=value3",
                {
                    "rid": "3226c2f7-3d30-425c-b83b-0c34335f8220",
                    "foo": "value1",
                    "bar": "value2",
                    "buzz": "value3",
                },
                id="Arbitrary number of properties in response",
            ),
        ],
    )
    def test_returns_properties(self, topic, expected_dict):
        assert (
            mqtt_topic_provisioning.extract_properties_from_dps_response_topic(topic)
            == expected_dict
        )

    # NOTE: properties should not require URL decoding.
    # No valid value would require URL encoding to be transmitted.
    # However, we treat them as if they were encoded anyway for safety (and ease of use).
    @pytest.mark.it("URL decodes properties extracted from the DPS response topic")
    @pytest.mark.parametrize(
        "topic, expected_dict",
        [
            pytest.param(
                "$dps/registrations/res/200/?$rid=request%3Fid",
                {"rid": "request?id"},
                id="Standard URL decoding",
            ),
            pytest.param(
                "$dps/registrations/res/200/?$rid=request%20id",
                {"rid": "request id"},
                id="URL decoding of ' ' character",
            ),
            pytest.param(
                "$dps/registrations/res/200/?$rid=request%2Fid",
                {"rid": "request/id"},
                id="URL decoding of '/' character",
            ),
        ],
    )
    def test_url_decode_properties(self, topic, expected_dict):
        assert (
            mqtt_topic_provisioning.extract_properties_from_dps_response_topic(topic)
            == expected_dict
        )

    @pytest.mark.it(
        "Raises ValueError if there are duplicate property keys in the DPS response topic"
    )
    def test_duplicate_keys(self):
        topic = "$dps/registrations/res/200/?$rid=3226c2f7-3d30-425c-b83b-0c34335f8220&rid=something-else"
        with pytest.raises(ValueError):
            mqtt_topic_provisioning.extract_properties_from_dps_response_topic(topic)


@pytest.mark.describe(".extract_status_code_from_dps_response_topic()")
class TestExtractStatusCodeFromDpsResponseTopic(object):
    @pytest.mark.it("Returns the status code from a valid DPS response topic")
    @pytest.mark.parametrize(
        "topic, expected_status",
        [
            pytest.param(
                "$dps/registrations/res/200/?$rid=3226c2f7-3d30-425c-b83b-0c34335f8220",
                "200",
                id="Successful (200) response",
            ),
            pytest.param(
                "$dps/registrations/res/202/?$rid=3226c2f7-3d30-425c-b83b-0c34335f8220&retry-after=3",
                "202",
                id="Retry-after (202) response",
            ),
            pytest.param(
                "$dps/registrations/res/401/?$rid=3226c2f7-3d30-425c-b83b-0c34335f8220",
                "401",
                id="Unauthorized (401) response",
            ),
        ],
    )
    def test_returns_status(self, topic, expected_status):
        assert (
            mqtt_topic_provisioning.extract_status_code_from_dps_response_topic(topic)
            == expected_status
        )
