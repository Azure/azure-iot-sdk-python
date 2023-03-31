# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
import logging
from v3_async_wip import mqtt_topic_provisioning

logging.basicConfig(level=logging.DEBUG)

# NOTE: All tests (that require it) are parametrized with multiple values for URL encoding.
# This is to show that the URL encoding is done correctly - not all URL encoding encodes
# the same way.
#
# For URL encoding, we must always test the ' ' and '/' characters specifically, in addition
# to a generic URL encoding value (e.g. $, #, etc.)
#
# For URL decoding, we must always test the '+' character specifically, in addition to
# a generic URL encoded value (e.g. %24, %23, etc.)
#
# Please also always test that provided values are converted to strings in order to ensure
# that they can be URL encoded without error.
#
# PLEASE DO THESE TESTS FOR EVEN CASES WHERE THOSE CHARACTERS SHOULD NOT OCCUR, FOR SAFETY.


@pytest.mark.describe(".get_response_topic_for_subscribe()")
class TestGetResponseTopicForSubscribe(object):
    @pytest.mark.it("Returns the topic for subscribing to responses from DPS")
    def test_returns_topic(self):
        topic = mqtt_topic_provisioning.get_response_topic_for_subscribe()
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

    @pytest.mark.it("Converts the request id to string when generating the topic")
    def test_string_conversion(self):
        request_id = 1234
        expected_topic = "$dps/registrations/PUT/iotdps-register/?$rid=1234"
        topic = mqtt_topic_provisioning.get_register_topic_for_publish(request_id)
        assert topic == expected_topic


class TestGetStatusQueryTopicForPublish(object):
    @pytest.mark.it("Returns the topic for publishing status query requests to DPS")
    def test_returns_topic(self):
        request_id = "3226c2f7-3d30-425c-b83b-0c34335f8220"
        operation_id = "4.79f33f69d8eb3870.da2d9251-3097-43e9-b81c-782718485ce7"
        expected_topic = "$dps/registrations/GET/iotdps-get-operationstatus/?$rid=3226c2f7-3d30-425c-b83b-0c34335f8220&operationId=4.79f33f69d8eb3870.da2d9251-3097-43e9-b81c-782718485ce7"
        topic = mqtt_topic_provisioning.get_status_query_topic_for_publish(request_id, operation_id)
        assert topic == expected_topic

    @pytest.mark.it("URL encodes the request id and operation id when generating the topic")
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
        topic = mqtt_topic_provisioning.get_status_query_topic_for_publish(request_id, operation_id)
        assert topic == expected_topic

    @pytest.mark.it("Converts the request id and operation id to string when generating the topic")
    def test_string_conversion(self):
        request_id = 1234
        operation_id = 4567
        expected_topic = (
            "$dps/registrations/GET/iotdps-get-operationstatus/?$rid=1234&operationId=4567"
        )
        topic = mqtt_topic_provisioning.get_status_query_topic_for_publish(request_id, operation_id)
        assert topic == expected_topic


@pytest.mark.describe(".extract_properties_from_response_topic()")
class TestExtractPropertiesFromResponseTopic(object):
    @pytest.fixture
    def topic_base(self):
        return "$dps/registrations/res/200/?"

    @pytest.mark.it(
        "Returns a dictionary mapping of all key/value pairs contained within the given topic string"
    )
    @pytest.mark.parametrize(
        "property_string, expected_dict",
        [
            pytest.param("", {}, id="No properties"),
            pytest.param(
                "key1=value1&key2=value2&key3=value3",
                {"key1": "value1", "key2": "value2", "key3": "value3"},
                id="Some properties",
            ),
        ],
    )
    def test_returns_properties(self, topic_base, property_string, expected_dict):
        topic = topic_base + property_string
        assert (
            mqtt_topic_provisioning.extract_properties_from_response_topic(topic) == expected_dict
        )

    @pytest.mark.it("URL decodes the key/value pairs extracted from the response topic")
    @pytest.mark.parametrize(
        "property_string, expected_dict",
        [
            pytest.param(
                "%24.key1=value%231&%24.key2=value%232",
                {"$.key1": "value#1", "$.key2": "value#2"},
                id="Standard URL Decoding",
            ),
            pytest.param(
                "key%201=value%201&key%202=value%202",
                {"key 1": "value 1", "key 2": "value 2"},
                id="URL Encoding of ' ' Character",
            ),
            pytest.param(
                "key%2F1=value%2F1&key%2F2=value%2F2",
                {"key/1": "value/1", "key/2": "value/2"},
                id="URL Encoding of '/' Character",
            ),
            pytest.param(
                "key+1=request+id",
                {"key+1": "request+id"},
                id="Does NOT decode '+' character",
            ),
        ],
    )
    def test_url_decode_properties(self, topic_base, property_string, expected_dict):
        topic = topic_base + property_string
        assert (
            mqtt_topic_provisioning.extract_properties_from_response_topic(topic) == expected_dict
        )

    @pytest.mark.it("Supports empty string in properties")
    @pytest.mark.parametrize(
        "property_string, expected_dict",
        [
            pytest.param("=value1", {"": "value1"}, id="Empty String Key"),
            pytest.param("key1=", {"key1": ""}, id="Empty String Value"),
        ],
    )
    def test_empty_string(self, topic_base, property_string, expected_dict):
        topic = topic_base + property_string
        assert (
            mqtt_topic_provisioning.extract_properties_from_response_topic(topic) == expected_dict
        )

    @pytest.mark.it(
        "Maps the extracted key to value of empty string if there is a key with no corresponding value present"
    )
    def test_key_only(self, topic_base):
        property_string = "key1&key2&key3=value"
        expected_dict = {"key1": "", "key2": "", "key3": "value"}
        topic = topic_base + property_string
        assert (
            mqtt_topic_provisioning.extract_properties_from_response_topic(topic) == expected_dict
        )

    @pytest.mark.it("Raises a ValueError if the provided topic is not DPS response topic")
    @pytest.mark.parametrize(
        "topic",
        [
            pytest.param("not a topic", id="Not a topic"),
            pytest.param(
                "$iothub/twin/res/200/?$rid=d9d7ce4d-3be9-498b-abde-913b81b880e5",
                id="Topic of wrong type",
            ),
            pytest.param(
                "$dps/registrtaisons/res/200/?$rid=d9d7ce4d-3be9-498b-abde-913b81b880e5",
                id="Malformed response topic",
            ),
        ],
    )
    def test_bad_topic(self, topic):
        with pytest.raises(ValueError):
            mqtt_topic_provisioning.extract_properties_from_response_topic(topic)


@pytest.mark.describe(".extract_status_code_from_response_topic()")
class TestExtractStatusCodeFromDpsResponseTopic(object):
    @pytest.mark.it("Returns the status code from a DPS response topic")
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
            mqtt_topic_provisioning.extract_status_code_from_response_topic(topic)
            == expected_status
        )

    @pytest.mark.it("URL decodes the returned value")
    @pytest.mark.parametrize(
        "topic, expected_status",
        [
            pytest.param(
                "$dps/registrations/res/%24%24%24/?$rid=3226c2f7-3d30-425c-b83b-0c34335f8220",
                "$$$",
                id="Standard URL decoding",
            ),
            pytest.param(
                "$dps/registrations/res/invalid+status/?$rid=3226c2f7-3d30-425c-b83b-0c34335f8220",
                "invalid+status",
                id="Does NOT decode '+' character",
            ),
        ],
    )
    def test_url_decode(self, topic, expected_status):
        assert (
            mqtt_topic_provisioning.extract_status_code_from_response_topic(topic)
            == expected_status
        )

    @pytest.mark.it("Raises a ValueError if the provided topic is not a DPS response topic")
    @pytest.mark.parametrize(
        "topic",
        [
            pytest.param("not a topic", id="Not a topic"),
            pytest.param(
                "$iothub/twin/res/200/?$rid=d9d7ce4d-3be9-498b-abde-913b81b880e5",
                id="Topic of wrong type",
            ),
            pytest.param(
                "$dps/registrtaisons/res/200/?$rid=d9d7ce4d-3be9-498b-abde-913b81b880e5",
                id="Malformed response topic",
            ),
        ],
    )
    def test_invalid_response_topic(self, topic):
        with pytest.raises(ValueError):
            mqtt_topic_provisioning.extract_properties_from_response_topic(topic)
