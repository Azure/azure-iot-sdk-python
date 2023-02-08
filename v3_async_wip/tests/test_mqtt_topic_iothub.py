# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
import logging
from v3_async_wip import mqtt_topic_iothub

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


@pytest.mark.describe(".get_c2d_topic_for_subscribe()")
class TestGetC2DTopicForSubscribe:
    @pytest.mark.it("Returns the topic for subscribing to C2D messages from IoTHub")
    def test_returns_topic(self):
        device_id = "my_device"
        expected_topic = "devices/my_device/messages/devicebound/#"
        topic = mqtt_topic_iothub.get_c2d_topic_for_subscribe(device_id)
        assert topic == expected_topic

    # NOTE: It SHOULD do URL encoding, but Hub doesn't currently support URL decoding, so we have
    # to follow that and not do URL encoding for safety. As a result, some of the values used in
    # this test would actually be invalid in production due to character restrictions on the Hub
    # that exist to prevent Hub from breaking due to a lack of URL decoding.
    # If Hub does begin to support robust URL encoding for safety, this test can easily be switched
    # to show that URL encoding DOES work.
    @pytest.mark.it("Does NOT URL encode the device_id when generating the topic")
    @pytest.mark.parametrize(
        "device_id, expected_topic",
        [
            pytest.param(
                "my$device", "devices/my$device/messages/devicebound/#", id="id contains '$'"
            ),
            pytest.param(
                "my device", "devices/my device/messages/devicebound/#", id="id contains ' '"
            ),
            pytest.param(
                "my/device", "devices/my/device/messages/devicebound/#", id="id contains '/'"
            ),
        ],
    )
    def test_url_encoding(self, device_id, expected_topic):
        topic = mqtt_topic_iothub.get_c2d_topic_for_subscribe(device_id)
        assert topic == expected_topic

    @pytest.mark.it("Converts the device_id to string when generating the topic")
    def test_str_conversion(self):
        device_id = 2000
        expected_topic = "devices/2000/messages/devicebound/#"
        topic = mqtt_topic_iothub.get_c2d_topic_for_subscribe(device_id)
        assert topic == expected_topic


@pytest.mark.describe(".get_input_topic_for_subscribe()")
class TestGetInputTopicForSubscribe:
    @pytest.mark.it("Returns the topic for subscribing to Input messages from IoTHub")
    def test_returns_topic(self):
        device_id = "my_device"
        module_id = "my_module"
        expected_topic = "devices/my_device/modules/my_module/inputs/#"
        topic = mqtt_topic_iothub.get_input_topic_for_subscribe(device_id, module_id)
        assert topic == expected_topic

    # NOTE: It SHOULD do URL encoding, but Hub doesn't currently support URL decoding, so we have
    # to follow that and not do URL encoding for safety. As a result, some of the values used in
    # this test would actually be invalid in production due to character restrictions on the Hub
    # that exist to prevent Hub from breaking due to a lack of URL decoding.
    # If Hub does begin to support robust URL encoding for safety, this test can easily be switched
    # to show that URL encoding DOES work.
    @pytest.mark.it("URL encodes the device_id and module_id when generating the topic")
    @pytest.mark.parametrize(
        "device_id, module_id, expected_topic",
        [
            pytest.param(
                "my$device",
                "my$module",
                "devices/my$device/modules/my$module/inputs/#",
                id="ids contain '$'",
            ),
            pytest.param(
                "my device",
                "my module",
                "devices/my device/modules/my module/inputs/#",
                id="ids contain ' '",
            ),
            pytest.param(
                "my/device",
                "my/module",
                "devices/my/device/modules/my/module/inputs/#",
                id="ids contain '/'",
            ),
        ],
    )
    def test_url_encoding(self, device_id, module_id, expected_topic):
        topic = mqtt_topic_iothub.get_input_topic_for_subscribe(device_id, module_id)
        assert topic == expected_topic

    @pytest.mark.it("Converts the device_id and module_id to string when generating the topic")
    def test_str_conversion(self):
        device_id = 2000
        module_id = 4000
        expected_topic = "devices/2000/modules/4000/inputs/#"
        topic = mqtt_topic_iothub.get_input_topic_for_subscribe(device_id, module_id)
        assert topic == expected_topic


@pytest.mark.describe(".get_method_topic_for_subscribe()")
class TestGetMethodTopicForSubscribe:
    @pytest.mark.it("Returns the topic for subscribing to methods from IoTHub")
    def test_returns_topic(self):
        topic = mqtt_topic_iothub.get_method_topic_for_subscribe()
        assert topic == "$iothub/methods/POST/#"


@pytest.mark.describe("get_twin_response_topic_for_subscribe()")
class TestGetTwinResponseTopicForSubscribe:
    @pytest.mark.it("Returns the topic for subscribing to twin response from IoTHub")
    def test_returns_topic(self):
        topic = mqtt_topic_iothub.get_twin_response_topic_for_subscribe()
        assert topic == "$iothub/twin/res/#"


@pytest.mark.describe("get_twin_patch_topic_for_subscribe()")
class TestGetTwinPatchTopicForSubscribe:
    @pytest.mark.it("Returns the topic for subscribing to twin patches from IoTHub")
    def test_returns_topic(self):
        topic = mqtt_topic_iothub.get_twin_patch_topic_for_subscribe()
        assert topic == "$iothub/twin/PATCH/properties/desired/#"


@pytest.mark.describe(".get_telemetry_topic_for_publish()")
class TestGetTelemetryTopicForPublish:
    @pytest.mark.it("Returns the topic for sending telemetry to IoTHub")
    @pytest.mark.parametrize(
        "device_id, module_id, expected_topic",
        [
            pytest.param("my_device", None, "devices/my_device/messages/events/", id="Device"),
            pytest.param(
                "my_device",
                "my_module",
                "devices/my_device/modules/my_module/messages/events/",
                id="Module",
            ),
        ],
    )
    def test_returns_topic(self, device_id, module_id, expected_topic):
        topic = mqtt_topic_iothub.get_telemetry_topic_for_publish(device_id, module_id)
        assert topic == expected_topic

    # NOTE: It SHOULD do URL encoding, but Hub doesn't currently support URL decoding, so we have
    # to follow that and not do URL encoding for safety. As a result, some of the values used in
    # this test would actually be invalid in production due to character restrictions on the Hub
    # that exist to prevent Hub from breaking due to a lack of URL decoding.
    # If Hub does begin to support robust URL encoding for safety, this test can easily be switched
    # to show that URL encoding DOES work.
    @pytest.mark.it("URL encodes the device_id and module_id when generating the topic")
    @pytest.mark.parametrize(
        "device_id, module_id, expected_topic",
        [
            pytest.param(
                "my$device",
                None,
                "devices/my$device/messages/events/",
                id="Device, id contains '$'",
            ),
            pytest.param(
                "my device",
                None,
                "devices/my device/messages/events/",
                id="Device, id contains ' '",
            ),
            pytest.param(
                "my/device",
                None,
                "devices/my/device/messages/events/",
                id="Device, id contains '/'",
            ),
            pytest.param(
                "my$device",
                "my$module",
                "devices/my$device/modules/my$module/messages/events/",
                id="Module, ids contain '$'",
            ),
            pytest.param(
                "my device",
                "my module",
                "devices/my device/modules/my module/messages/events/",
                id="Module, ids contain ' '",
            ),
            pytest.param(
                "my/device",
                "my/module",
                "devices/my/device/modules/my/module/messages/events/",
                id="Module, ids contain '/'",
            ),
        ],
    )
    def test_url_encoding(self, device_id, module_id, expected_topic):
        topic = mqtt_topic_iothub.get_telemetry_topic_for_publish(device_id, module_id)
        assert topic == expected_topic

    @pytest.mark.it("Converts the device_id and module_id to string when generating the topic")
    @pytest.mark.parametrize(
        "device_id, module_id, expected_topic",
        [
            pytest.param(2000, None, "devices/2000/messages/events/", id="Device"),
            pytest.param(2000, 4000, "devices/2000/modules/4000/messages/events/", id="Module"),
        ],
    )
    def test_str_conversion(self, device_id, module_id, expected_topic):
        topic = mqtt_topic_iothub.get_telemetry_topic_for_publish(device_id, module_id)
        assert topic == expected_topic


@pytest.mark.describe(".get_method_topic_for_publish()")
class TestGetMethodTopicForPublish:
    @pytest.mark.it("Returns the topic for sending a method response to IoTHub")
    @pytest.mark.parametrize(
        "request_id, status, expected_topic",
        [
            pytest.param("1", "200", "$iothub/methods/res/200/?$rid=1", id="Successful result"),
            pytest.param(
                "475764", "500", "$iothub/methods/res/500/?$rid=475764", id="Failure result"
            ),
        ],
    )
    def test_returns_topic(self, request_id, status, expected_topic):
        topic = mqtt_topic_iothub.get_method_topic_for_publish(request_id, status)
        assert topic == expected_topic

    @pytest.mark.it("URL encodes provided values when generating the topic")
    @pytest.mark.parametrize(
        "request_id, status, expected_topic",
        [
            pytest.param(
                "invalid#request?id",
                "invalid$status",
                "$iothub/methods/res/invalid%24status/?$rid=invalid%23request%3Fid",
                id="Standard URL Encoding",
            ),
            pytest.param(
                "invalid request id",
                "invalid status",
                "$iothub/methods/res/invalid%20status/?$rid=invalid%20request%20id",
                id="URL Encoding of ' ' character",
            ),
            pytest.param(
                "invalid/request/id",
                "invalid/status",
                "$iothub/methods/res/invalid%2Fstatus/?$rid=invalid%2Frequest%2Fid",
                id="URL Encoding of '/' character",
            ),
        ],
    )
    def test_url_encoding(self, request_id, status, expected_topic):
        topic = mqtt_topic_iothub.get_method_topic_for_publish(request_id, status)
        assert topic == expected_topic

    @pytest.mark.it("Converts the provided values to strings when generating the topic")
    def test_str_conversion(self):
        request_id = 1
        status = 200
        expected_topic = "$iothub/methods/res/200/?$rid=1"
        topic = mqtt_topic_iothub.get_method_topic_for_publish(request_id, status)
        assert topic == expected_topic


@pytest.mark.describe(".get_twin_request_topic_for_publish()")
class TestGetTwinRequestTopicForPublish:
    @pytest.mark.it("Returns topic for sending a get twin request to IoTHub")
    def test_returns_topic(self):
        request_id = "3226c2f7-3d30-425c-b83b-0c34335f8220"
        expected_topic = "$iothub/twin/GET/?$rid=3226c2f7-3d30-425c-b83b-0c34335f8220"
        topic = mqtt_topic_iothub.get_twin_request_topic_for_publish(request_id)
        assert topic == expected_topic

    @pytest.mark.it("URL encodes 'request_id' parameter when generating the topic")
    @pytest.mark.parametrize(
        "request_id, expected_topic",
        [
            pytest.param(
                "invalid$request?id",
                "$iothub/twin/GET/?$rid=invalid%24request%3Fid",
                id="Standard URL Encoding",
            ),
            pytest.param(
                "invalid request id",
                "$iothub/twin/GET/?$rid=invalid%20request%20id",
                id="URL Encoding of ' ' character",
            ),
            pytest.param(
                "invalid/request/id",
                "$iothub/twin/GET/?$rid=invalid%2Frequest%2Fid",
                id="URL Encoding of '/' character",
            ),
        ],
    )
    def test_url_encoding(self, request_id, expected_topic):
        topic = mqtt_topic_iothub.get_twin_request_topic_for_publish(request_id)
        assert topic == expected_topic

    @pytest.mark.it("Converts 'request_id' parameter to string when generating the topic")
    def test_str_conversion(self):
        request_id = 4000
        expected_topic = "$iothub/twin/GET/?$rid=4000"
        topic = mqtt_topic_iothub.get_twin_request_topic_for_publish(request_id)
        assert topic == expected_topic


@pytest.mark.describe(".get_twin_patch_topic_for_publish()")
class TestGetTwinPatchTopicForPublish:
    @pytest.mark.it("Returns topic for sending a twin patch to IoTHub")
    def test_returns_topic(self):
        request_id = "5002b415-af16-47e9-b89c-8680e01b502f"
        expected_topic = (
            "$iothub/twin/PATCH/properties/reported/?$rid=5002b415-af16-47e9-b89c-8680e01b502f"
        )
        topic = mqtt_topic_iothub.get_twin_patch_topic_for_publish(request_id)
        assert topic == expected_topic

    @pytest.mark.it("URL encodes 'request_id' parameter when generating the topic")
    @pytest.mark.parametrize(
        "request_id, expected_topic",
        [
            pytest.param(
                "invalid$request?id",
                "$iothub/twin/PATCH/properties/reported/?$rid=invalid%24request%3Fid",
                id="Standard URL Encoding",
            ),
            pytest.param(
                "invalid request id",
                "$iothub/twin/PATCH/properties/reported/?$rid=invalid%20request%20id",
                id="URL Encoding of ' ' character",
            ),
            pytest.param(
                "invalid/request/id",
                "$iothub/twin/PATCH/properties/reported/?$rid=invalid%2Frequest%2Fid",
                id="URL Encoding of '/' character",
            ),
        ],
    )
    def test_url_encoding(self, request_id, expected_topic):
        topic = mqtt_topic_iothub.get_twin_patch_topic_for_publish(request_id)
        assert topic == expected_topic

    @pytest.mark.it("Converts 'request_id' parameter to string when generating the topic")
    def test_str_conversion(self):
        request_id = 4000
        expected_topic = "$iothub/twin/PATCH/properties/reported/?$rid=4000"
        topic = mqtt_topic_iothub.get_twin_patch_topic_for_publish(request_id)
        assert topic == expected_topic


@pytest.mark.describe(".insert_message_properties_in_topic()")
class TestEncodeMessagePropertiesInTopic:
    @pytest.fixture(params=["C2D Message", "Input Message"])
    def message_topic(self, request):
        if request.param == "C2D Message":
            return "devices/fake_device/messages/events/"
        else:
            return "devices/fake_device/modules/fake_module/messages/events/"

    @pytest.mark.it(
        "Returns a new version of the given topic string that contains the provided properties as key/value pairs"
    )
    @pytest.mark.parametrize(
        "system_properties, custom_properties, expected_encoding",
        [
            pytest.param({}, {}, "", id="No Properties"),
            pytest.param(
                {"sys_prop1": "value1", "sys_prop2": "value2"},
                {},
                "sys_prop1=value1&sys_prop2=value2",
                id="System Properties Only",
            ),
            pytest.param(
                {},
                {"cust_prop1": "value3", "cust_prop2": "value4"},
                "cust_prop1=value3&cust_prop2=value4",
                id="Custom Properties Only",
            ),
            pytest.param(
                {"sys_prop1": "value1", "sys_prop2": "value2"},
                {"cust_prop1": "value3", "cust_prop2": "value4"},
                "sys_prop1=value1&sys_prop2=value2&cust_prop1=value3&cust_prop2=value4",
                id="System Properties and Custom Properties",
            ),
        ],
    )
    def test_adds_properties(
        self, message_topic, system_properties, custom_properties, expected_encoding
    ):
        expected_topic = message_topic + expected_encoding
        encoded_topic = mqtt_topic_iothub.insert_message_properties_in_topic(
            message_topic, system_properties, custom_properties
        )
        assert encoded_topic == expected_topic

    @pytest.mark.it(
        "URL encodes keys and values in the provided properties when adding them to the topic string"
    )
    @pytest.mark.parametrize(
        "system_properties, custom_properties, expected_encoding",
        [
            pytest.param(
                {"$.mid": "message#id", "$.ce": "utf-#"},
                {},
                "%24.mid=message%23id&%24.ce=utf-%23",
                id="System Properties Only (Standard URL Encoding)",
            ),
            pytest.param(
                {},
                {"cu$tom1": "value#3", "cu$tom2": "value#4"},
                "cu%24tom1=value%233&cu%24tom2=value%234",
                id="Custom Properties Only (Standard URL Encoding)",
            ),
            pytest.param(
                {"$.mid": "message#id", "$.ce": "utf-#"},
                {"cu$tom1": "value#3", "cu$tom2": "value#4"},
                "%24.mid=message%23id&%24.ce=utf-%23&cu%24tom1=value%233&cu%24tom2=value%234",
                id="System Properties and Custom Properties (Standard URL Encoding)",
            ),
            pytest.param(
                {"m id": "message id", "c e": "utf 8"},
                {},
                "m%20id=message%20id&c%20e=utf%208",
                id="System Properties Only (URL Encoding of ' ' Character)",
            ),
            pytest.param(
                {},
                {"custom 1": "value 1", "custom 2": "value 2"},
                "custom%201=value%201&custom%202=value%202",
                id="Custom Properties Only (URL Encoding of ' ' Character)",
            ),
            pytest.param(
                {"m id": "message id", "c e": "utf 8"},
                {"custom 1": "value 1", "custom 2": "value 2"},
                "m%20id=message%20id&c%20e=utf%208&custom%201=value%201&custom%202=value%202",
                id="System Properties and Custom Properties (URL Encoding of ' ' Character)",
            ),
            pytest.param(
                {"m/id": "message/id", "c/e": "utf/8"},
                {},
                "m%2Fid=message%2Fid&c%2Fe=utf%2F8",
                id="System Properties Only (URL Encoding of '/' Character)",
            ),
            pytest.param(
                {},
                {"custom/1": "value/1", "custom/2": "value/2"},
                "custom%2F1=value%2F1&custom%2F2=value%2F2",
                id="Custom Properties Only (URL Encoding of '/' Character)",
            ),
            pytest.param(
                {"m/id": "message/id", "c/e": "utf/8"},
                {"custom/1": "value/1", "custom/2": "value/2"},
                "m%2Fid=message%2Fid&c%2Fe=utf%2F8&custom%2F1=value%2F1&custom%2F2=value%2F2",
                id="System Properties and Custom Properties (URL Encoding of '/' Character)",
            ),
        ],
    )
    def test_url_encoding(
        self, message_topic, system_properties, custom_properties, expected_encoding
    ):
        expected_topic = message_topic + expected_encoding
        encoded_topic = mqtt_topic_iothub.insert_message_properties_in_topic(
            message_topic, system_properties, custom_properties
        )
        assert encoded_topic == expected_topic


@pytest.mark.describe(".extract_properties_from_message_topic()")
class TestExtractPropertiesFromMessageTopic:
    @pytest.fixture(params=["C2D Message", "Input Message"])
    def message_topic_base(self, request):
        if request.param == "C2D Message":
            return "devices/fake_device/messages/devicebound/"
        else:
            return "devices/fake_device/modules/fake_module/inputs/fake_input/"

    @pytest.mark.it(
        "Returns a dictionary mapping of all key/value pairs contained within the given topic string"
    )
    @pytest.mark.parametrize(
        "property_string, expected_property_dict",
        [
            pytest.param("", {}, id="No properties"),
            pytest.param(
                "key1=value1&key2=value2&key3=value3",
                {"key1": "value1", "key2": "value2", "key3": "value3"},
                id="Some Properties",
            ),
        ],
    )
    def test_returns_map(self, message_topic_base, property_string, expected_property_dict):
        topic = message_topic_base + property_string
        properties = mqtt_topic_iothub.extract_properties_from_message_topic(topic)
        assert properties == expected_property_dict

    @pytest.mark.it("URL decodes the key/value pairs extracted from the topic")
    @pytest.mark.parametrize(
        "property_string, expected_property_dict",
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
        ],
    )
    def test_url_decoding(self, message_topic_base, property_string, expected_property_dict):
        topic = message_topic_base + property_string
        properties = mqtt_topic_iothub.extract_properties_from_message_topic(topic)
        assert properties == expected_property_dict

    @pytest.mark.it("Supports empty string in properties")
    @pytest.mark.parametrize(
        "property_string, expected_property_dict",
        [
            pytest.param("=value1", {"": "value1"}, id="Empty String Key"),
            pytest.param("key1=", {"key1": ""}, id="Empty String Value"),
        ],
    )
    def test_empty_string(self, message_topic_base, property_string, expected_property_dict):
        topic = message_topic_base + property_string
        properties = mqtt_topic_iothub.extract_properties_from_message_topic(topic)
        assert properties == expected_property_dict

    @pytest.mark.it(
        "Maps the extracted key to value of empty string if there is a key with no corresponding value present"
    )
    def test_key_only(self, message_topic_base):
        property_string = "key1&key2&key3=value"
        expected_property_dict = {"key1": "", "key2": "", "key3": "value"}
        topic = message_topic_base + property_string
        properties = mqtt_topic_iothub.extract_properties_from_message_topic(topic)
        assert properties == expected_property_dict

    @pytest.mark.it(
        "Raises a ValueError if the provided topic is not a C2D topic or an Input Message topic"
    )
    @pytest.mark.parametrize(
        "topic",
        [
            pytest.param("not a topic", id="Not a topic"),
            pytest.param(
                "$iothub/twin/res/200/?$rid=d9d7ce4d-3be9-498b-abde-913b81b880e5",
                id="Topic of wrong type",
            ),
            pytest.param(
                "devices/fake_device/messages/devicebnd/%24.mid=6b822696-f75a-46f5-8b02-0680db65abf5&%24.to=%2Fdevices%2Ffake_device%2Fmessages%2Fdevicebound",
                id="Malformed C2D topic",
            ),
            pytest.param(
                "devices/fake_device/modules/fake_module/inutps/fake_input/%24.mid=6b822696-f75a-46f5-8b02-0680db65abf5&%24.to=%2Fdevices%2Ffake_device%2Fmodules%2Ffake_module%2Finputs%2Ffake_input",
                id="Malformed input message topic",
            ),
        ],
    )
    def test_bad_topic(self, topic):
        with pytest.raises(ValueError):
            mqtt_topic_iothub.extract_properties_from_message_topic(topic)


@pytest.mark.describe(".extract_name_from_method_request_topic()")
class TestExtractNameFromMethodRequestTopic:
    @pytest.mark.it("Returns the method name from a method topic")
    def test_valid_method_topic(self):
        topic = "$iothub/methods/POST/fake_method/?$rid=1"
        expected_method_name = "fake_method"

        assert (
            mqtt_topic_iothub.extract_name_from_method_request_topic(topic) == expected_method_name
        )

    @pytest.mark.it("URL decodes the returned method name")
    @pytest.mark.parametrize(
        "topic, expected_method_name",
        [
            pytest.param(
                "$iothub/methods/POST/fake%24method/?$rid=1",
                "fake$method",
                id="Standard URL Decoding",
            ),
            pytest.param(
                "$iothub/methods/POST/fake+method/?$rid=1",
                "fake+method",
                id="Does NOT decode '+' character",
            ),
        ],
    )
    def test_url_decodes_value(self, topic, expected_method_name):
        assert (
            mqtt_topic_iothub.extract_name_from_method_request_topic(topic) == expected_method_name
        )

    @pytest.mark.it("Raises a ValueError if the provided topic is not a method topic")
    @pytest.mark.parametrize(
        "topic",
        [
            pytest.param("not a topic", id="Not a topic"),
            pytest.param(
                "devices/fake_device/modules/fake_module/inputs/fake_input",
                id="Topic of wrong type",
            ),
            pytest.param("$iothub/methdos/POST/fake_method/?$rid=1", id="Malformed topic"),
        ],
    )
    def test_invalid_method_topic(self, topic):
        with pytest.raises(ValueError):
            mqtt_topic_iothub.extract_name_from_method_request_topic(topic)


@pytest.mark.describe(".extract_request_id_from_method_request_topic()")
class TestExtractRequestIdFromMethodRequestTopic:
    @pytest.mark.it("Returns the request id from a method topic")
    def test_valid_method_topic(self):
        topic = "$iothub/methods/POST/fake_method/?$rid=1"
        expected_request_id = "1"

        assert (
            mqtt_topic_iothub.extract_request_id_from_method_request_topic(topic)
            == expected_request_id
        )

    @pytest.mark.it("URL decodes the returned value")
    @pytest.mark.parametrize(
        "topic, expected_request_id",
        [
            pytest.param(
                "$iothub/methods/POST/fake_method/?$rid=fake%24request%2Fid",
                "fake$request/id",
                id="Standard URL Decoding",
            ),
            pytest.param(
                "$iothub/methods/POST/fake_method/?$rid=fake+request+id",
                "fake+request+id",
                id="Does NOT decode '+' character",
            ),
        ],
    )
    def test_url_decodes_value(self, topic, expected_request_id):
        assert (
            mqtt_topic_iothub.extract_request_id_from_method_request_topic(topic)
            == expected_request_id
        )

    @pytest.mark.it("Raises a ValueError if the provided topic is not a method topic")
    @pytest.mark.parametrize(
        "topic",
        [
            pytest.param("not a topic", id="Not a topic"),
            pytest.param(
                "devices/fake_device/modules/fake_module/inputs/fake_input",
                id="Topic of wrong type",
            ),
            pytest.param("$iothub/methdos/POST/fake_method/?$rid=1", id="Malformed topic"),
        ],
    )
    def test_invalid_method_topic(self, topic):
        with pytest.raises(ValueError):
            mqtt_topic_iothub.extract_request_id_from_method_request_topic(topic)

    @pytest.mark.it("Raises a ValueError if the provided topic does not contain a request id")
    @pytest.mark.parametrize(
        "topic",
        [
            pytest.param("$iothub/methods/POST/fake_method/?$mid=1", id="No request id key"),
            pytest.param("$iothub/methods/POST/fake_method/?$rid", id="No request id value"),
            pytest.param("$iothub/methods/POST/fake_method/?$rid=", id="Empty request id value"),
        ],
    )
    def test_no_request_id(self, topic):
        with pytest.raises(ValueError):
            mqtt_topic_iothub.extract_request_id_from_method_request_topic(topic)


@pytest.mark.describe(".extract_status_code_from_twin_response_topic()")
class TestExtractStatusCodeFromTwinResponseTopic:
    @pytest.mark.it("Returns the status from a twin response topic")
    def test_valid_twin_response_topic(self):
        topic = "$iothub/twin/res/200/?rid=1"
        expected_status = "200"

        assert (
            mqtt_topic_iothub.extract_status_code_from_twin_response_topic(topic) == expected_status
        )

    @pytest.mark.it("URL decodes the returned value")
    @pytest.mark.parametrize(
        "topic, expected_status",
        [
            pytest.param("$iothub/twin/res/%24%24%24/?rid=1", "$$$", id="Standard URL decoding"),
            pytest.param(
                "$iothub/twin/res/invalid+status/?rid=1",
                "invalid+status",
                id="Does NOT decode '+' character",
            ),
        ],
    )
    def test_url_decode(self, topic, expected_status):
        assert (
            mqtt_topic_iothub.extract_status_code_from_twin_response_topic(topic) == expected_status
        )

    @pytest.mark.it("Raises a ValueError if the provided topic is not a twin response topic")
    @pytest.mark.parametrize(
        "topic",
        [
            pytest.param("not a topic", id="Not a topic"),
            pytest.param(
                "devices/fake_device/modules/fake_module/inputs/fake_input",
                id="Topic of wrong type",
            ),
            pytest.param("$iothub/twn/res/200?rid=1", id="Malformed topic"),
        ],
    )
    def test_invalid_twin_response_topic(self, topic):
        with pytest.raises(ValueError):
            mqtt_topic_iothub.extract_status_code_from_twin_response_topic(topic)


@pytest.mark.describe(".extract_request_id_from_twin_response_topic()")
class TestExtractRequestIdFromTwinResponseTopic:
    @pytest.mark.it("Returns the request id from a twin response topic")
    def test_valid_twin_response_topic(self):
        topic = "$iothub/twin/res/200/?$rid=1"
        expected_request_id = "1"

        assert (
            mqtt_topic_iothub.extract_request_id_from_twin_response_topic(topic)
            == expected_request_id
        )

    @pytest.mark.it("URL decodes the returned value")
    @pytest.mark.parametrize(
        "topic, expected_request_id",
        [
            pytest.param(
                "$iothub/twin/res/200/?$rid=fake%24request%2Fid",
                "fake$request/id",
                id="Standard URL Decoding",
            ),
            pytest.param(
                "$iothub/twin/res/200/?$rid=fake+request+id",
                "fake+request+id",
                id="Does NOT decode '+' character",
            ),
        ],
    )
    def test_url_decodes_value(self, topic, expected_request_id):
        assert (
            mqtt_topic_iothub.extract_request_id_from_twin_response_topic(topic)
            == expected_request_id
        )

    @pytest.mark.it("Raises a ValueError if the provided topic is not a twin response topic")
    @pytest.mark.parametrize(
        "topic",
        [
            pytest.param("not a topic", id="Not a topic"),
            pytest.param(
                "devices/fake_device/modules/fake_module/inputs/fake_input",
                id="Topic of wrong type",
            ),
            pytest.param("$iothub/twn/res/200?$rid=1", id="Malformed topic"),
        ],
    )
    def test_invalid_twin_response_topic(self, topic):
        with pytest.raises(ValueError):
            mqtt_topic_iothub.extract_request_id_from_twin_response_topic(topic)

    @pytest.mark.it("Raises a ValueError if the provided topic does not contain a request id")
    @pytest.mark.parametrize(
        "topic",
        [
            pytest.param("$iothub/twin/res/200/?$mid=1", id="No request id key"),
            pytest.param("$iothub/twin/res/200/?$rid", id="No request id value"),
            pytest.param("$iothub/twin/res/200/?$rid=", id="Empty request id value"),
        ],
    )
    def test_no_request_id(self, topic):
        with pytest.raises(ValueError):
            mqtt_topic_iothub.extract_request_id_from_twin_response_topic(topic)
