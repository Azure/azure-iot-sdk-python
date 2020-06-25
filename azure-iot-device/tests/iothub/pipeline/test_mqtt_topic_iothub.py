# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
import logging
import datetime
from azure.iot.device.iothub.pipeline import mqtt_topic_iothub
from azure.iot.device import Message

logging.basicConfig(level=logging.DEBUG)

# NOTE: All tests (that require it) are parametrized with multiple values for URL encoding.
# This is to show that the URL encoding is done correctly - not all URL encoding encodes
# the same way.
#
# For URL encoding, we must always test the ' ' and '/' characters specifically, in addition
# to a generic URL encoding value (e.g. $, #, etc.)
#
# For URL decoding, we must always test the '+' character speicifically, in addition to
# a generic URL encoded value (e.g. %24, %23, etc.)
#
# Please also always test that provided values are converted to strings in order to ensure
# that they can be URL encoded without error.
#
# PLEASE DO THESE TESTS FOR EVEN CASES WHERE THOSE CHARACTERS SHOULD NOT OCCUR, FOR SAFETY.


@pytest.mark.describe(".get_c2d_topic_for_subscribe()")
class TestGetC2DTopicForSubscribe(object):
    @pytest.mark.it("Returns the topic for subscribing to C2D messages from IoTHub")
    def test_returns_topic(self):
        device_id = "my_device"
        expected_topic = "devices/my_device/messages/devicebound/#"
        topic = mqtt_topic_iothub.get_c2d_topic_for_subscribe(device_id)
        assert topic == expected_topic

    @pytest.mark.it("URL encodes the device_id when generating the topic")
    @pytest.mark.parametrize(
        "device_id, expected_topic",
        [
            pytest.param(
                "my$device", "devices/my%24device/messages/devicebound/#", id="id contains '$'"
            ),
            pytest.param(
                "my device", "devices/my%20device/messages/devicebound/#", id="id contains ' '"
            ),
            pytest.param(
                "my/device", "devices/my%2Fdevice/messages/devicebound/#", id="id contains '/'"
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
class TestGetInputTopicForSubscribe(object):
    @pytest.mark.it("Returns the topic for subscribing to Input messages from IoTHub")
    def test_returns_topic(self):
        device_id = "my_device"
        module_id = "my_module"
        expected_topic = "devices/my_device/modules/my_module/inputs/#"
        topic = mqtt_topic_iothub.get_input_topic_for_subscribe(device_id, module_id)
        assert topic == expected_topic

    @pytest.mark.it("URL encodes the device_id and module_id when generating the topic")
    @pytest.mark.parametrize(
        "device_id, module_id, expected_topic",
        [
            pytest.param(
                "my$device",
                "my$module",
                "devices/my%24device/modules/my%24module/inputs/#",
                id="ids contain '$'",
            ),
            pytest.param(
                "my device",
                "my module",
                "devices/my%20device/modules/my%20module/inputs/#",
                id="ids contain ' '",
            ),
            pytest.param(
                "my/device",
                "my/module",
                "devices/my%2Fdevice/modules/my%2Fmodule/inputs/#",
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
class TestGetMethodTopicForSubscribe(object):
    @pytest.mark.it("Returns the topic for subscribing to methods from IoTHub")
    def test_returns_topic(self):
        topic = mqtt_topic_iothub.get_method_topic_for_subscribe()
        assert topic == "$iothub/methods/POST/#"


@pytest.mark.describe("get_twin_response_topic_for_subscribe()")
class TestGetTwinResponseTopicForSubscribe(object):
    @pytest.mark.it("Returns the topic for subscribing to twin repsonse from IoTHub")
    def test_returns_topic(self):
        topic = mqtt_topic_iothub.get_twin_response_topic_for_subscribe()
        assert topic == "$iothub/twin/res/#"


@pytest.mark.describe("get_twin_patch_topic_for_subscribe()")
class TestGetTwinPatchTopicForSubscribe(object):
    @pytest.mark.it("Returns the topic for subscribing to twin patches from IoTHub")
    def test_returns_topic(self):
        topic = mqtt_topic_iothub.get_twin_patch_topic_for_subscribe()
        assert topic == "$iothub/twin/PATCH/properties/desired/#"


@pytest.mark.describe(".get_telemetry_topic_for_publish()")
class TestGetTelemetryTopicForPublish(object):
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

    @pytest.mark.it("URL encodes the device_id and module_id when generating the topic")
    @pytest.mark.parametrize(
        "device_id, module_id, expected_topic",
        [
            pytest.param(
                "my$device",
                None,
                "devices/my%24device/messages/events/",
                id="Device, id contains '$'",
            ),
            pytest.param(
                "my device",
                None,
                "devices/my%20device/messages/events/",
                id="Device, id contains ' '",
            ),
            pytest.param(
                "my/device",
                None,
                "devices/my%2Fdevice/messages/events/",
                id="Device, id contains '/'",
            ),
            pytest.param(
                "my$device",
                "my$module",
                "devices/my%24device/modules/my%24module/messages/events/",
                id="Module, ids contain '$'",
            ),
            pytest.param(
                "my device",
                "my module",
                "devices/my%20device/modules/my%20module/messages/events/",
                id="Module, ids contain ' '",
            ),
            pytest.param(
                "my/device",
                "my/module",
                "devices/my%2Fdevice/modules/my%2Fmodule/messages/events/",
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
class TestGetMethodTopicForPublish(object):
    @pytest.mark.it("Returns the topic for sending a method response to IoTHub")
    @pytest.mark.parametrize(
        "request_id, status, expected_topic",
        [
            pytest.param("1", "200", "$iothub/methods/res/200/?$rid=1", id="Succesful result"),
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


@pytest.mark.describe(".get_twin_topic_for_publish()")
class TestGetTwinTopicForPublish(object):
    @pytest.mark.it("Returns topic for sending a twin request to IoTHub")
    @pytest.mark.parametrize(
        "method, resource_location, request_id, expected_topic",
        [
            # Get Twin
            pytest.param(
                "GET",
                "/",
                "3226c2f7-3d30-425c-b83b-0c34335f8220",
                "$iothub/twin/GET/?$rid=3226c2f7-3d30-425c-b83b-0c34335f8220",
                id="Get Twin",
            ),
            # Patch Twin
            pytest.param(
                "POST",
                "/properties/reported/",
                "5002b415-af16-47e9-b89c-8680e01b502f",
                "$iothub/twin/POST/properties/reported/?$rid=5002b415-af16-47e9-b89c-8680e01b502f",
                id="Patch Twin",
            ),
        ],
    )
    def test_returns_topic(self, method, resource_location, request_id, expected_topic):
        topic = mqtt_topic_iothub.get_twin_topic_for_publish(method, resource_location, request_id)
        assert topic == expected_topic

    @pytest.mark.it("URL encodes 'request_id' parameter")
    @pytest.mark.parametrize(
        "method, resource_location, request_id, expected_topic",
        [
            pytest.param(
                "GET",
                "/",
                "invalid$request?id",
                "$iothub/twin/GET/?$rid=invalid%24request%3Fid",
                id="Get Twin, Standard URL Encoding",
            ),
            pytest.param(
                "GET",
                "/",
                "invalid request id",
                "$iothub/twin/GET/?$rid=invalid%20request%20id",
                id="Get Twin, URL Encoding of ' ' character",
            ),
            pytest.param(
                "GET",
                "/",
                "invalid/request/id",
                "$iothub/twin/GET/?$rid=invalid%2Frequest%2Fid",
                id="Get Twin, URL Encoding of '/' character",
            ),
            pytest.param(
                "POST",
                "/properties/reported/",
                "invalid$request?id",
                "$iothub/twin/POST/properties/reported/?$rid=invalid%24request%3Fid",
                id="Patch Twin, Standard URL Encoding",
            ),
            pytest.param(
                "POST",
                "/properties/reported/",
                "invalid request id",
                "$iothub/twin/POST/properties/reported/?$rid=invalid%20request%20id",
                id="Patch Twin, URL Encoding of ' ' character",
            ),
            pytest.param(
                "POST",
                "/properties/reported/",
                "invalid/request/id",
                "$iothub/twin/POST/properties/reported/?$rid=invalid%2Frequest%2Fid",
                id="Patch Twin, URL Encoding of '/' character",
            ),
        ],
    )
    def test_url_encoding(self, method, resource_location, request_id, expected_topic):
        topic = mqtt_topic_iothub.get_twin_topic_for_publish(method, resource_location, request_id)
        assert topic == expected_topic

    @pytest.mark.it("Converts 'request_id' parameter to string when generating the topic")
    @pytest.mark.parametrize(
        "method, resource_location, request_id, expected_topic",
        [
            # Get Twin
            pytest.param("GET", "/", 4000, "$iothub/twin/GET/?$rid=4000", id="Get Twin"),
            # Patch Twin
            pytest.param(
                "POST",
                "/properties/reported/",
                2000,
                "$iothub/twin/POST/properties/reported/?$rid=2000",
                id="Patch Twin",
            ),
        ],
    )
    def test_str_conversion(self, method, resource_location, request_id, expected_topic):
        topic = mqtt_topic_iothub.get_twin_topic_for_publish(method, resource_location, request_id)
        assert topic == expected_topic


@pytest.mark.describe(".is_c2d_topic()")
class TestIsC2DTopic(object):
    @pytest.mark.it(
        "Returns True if the provided topic is a C2D topic and matches the provided device id"
    )
    def test_is_c2d_topic(self):
        topic = "devices/fake_device/messages/devicebound/%24.mid=6b822696-f75a-46f5-8b02-0680db65abf5&%24.to=%2Fdevices%2Ffake_device%2Fmessages%2Fdevicebound"
        device_id = "fake_device"
        assert mqtt_topic_iothub.is_c2d_topic(topic, device_id)

    @pytest.mark.it("URL encodes the device id when matching to the topic")
    @pytest.mark.parametrize(
        "topic, device_id",
        [
            pytest.param(
                "devices/fake%3Fdevice/messages/devicebound/%24.mid=6b822696-f75a-46f5-8b02-0680db65abf5&%24.to=%2Fdevices%2Ffake%3Fdevice%2Fmessages%2Fdevicebound",
                "fake?device",
                id="Standard URL encoding required for device_id",
            ),
            pytest.param(
                "devices/fake%20device/messages/devicebound/%24.mid=6b822696-f75a-46f5-8b02-0680db65abf5&%24.to=%2Fdevices%2Ffake%20device%2Fmessages%2Fdevicebound",
                "fake device",
                id="URL encoding of ' ' character required for device_id",
            ),
            # Note that this topic string is completely broken, even beyond the fact that device id's can't have a '/' in them.
            # A device id with a '/' would not be possible to decode correctly, because the '/' in the device name encoded in the
            # system properties would cause the system properties to not be able to be decoded correctly. But, like many tests
            # this is just for completeness, safety, and consistency.
            pytest.param(
                "devices/fake%2Fdevice/messages/devicebound/%24.mid=6b822696-f75a-46f5-8b02-0680db65abf5&%24.to=%2Fdevices%2Ffake%2Fdevice%2Fmessages%2Fdevicebound",
                "fake/device",
                id="URL encoding of '/' character required for device_id",
            ),
        ],
    )
    def test_url_encodes(self, topic, device_id):
        assert mqtt_topic_iothub.is_c2d_topic(topic, device_id)

    @pytest.mark.it("Converts the device id to string when matching to the topic")
    def test_str_conversion(self):
        topic = "devices/2000/messages/devicebound/%24.mid=6b822696-f75a-46f5-8b02-0680db65abf5&%24.to=%2Fdevices%2F2000%2Fmessages%2Fdevicebound"
        device_id = 2000
        assert mqtt_topic_iothub.is_c2d_topic(topic, device_id)

    @pytest.mark.it("Returns False if the provided topic is not a C2D topic")
    @pytest.mark.parametrize(
        "topic, device_id",
        [
            pytest.param("not a topic", "fake_device", id="Not a topic"),
            pytest.param(
                "devices/fake_device/modules/fake_module/inputs/fake_input/%24.mid=6b822696-f75a-46f5-8b02-0680db65abf5&%24.to=%2Fdevices%2Ffake_device%2Fmessages%2Fdevicebound",
                "fake_device",
                id="Topic of wrong type",
            ),
            pytest.param(
                "devices/fake_device/msgs/devicebound/%24.mid=6b822696-f75a-46f5-8b02-0680db65abf5&%24.to=%2Fdevices%2Ffake_device%2Fmessages%2Fdevicebound",
                "fake_device",
                id="Malformed topic",
            ),
        ],
    )
    def test_is_not_c2d_topic(self, topic, device_id):
        assert not mqtt_topic_iothub.is_c2d_topic(topic, device_id)

    @pytest.mark.it(
        "Returns False if the provided topic is a C2D topic, but does not match the provided device id"
    )
    def test_is_c2d_topic_but_wrong_device_id(self):
        topic = "devices/fake_device/messages/devicebound/%24.mid=6b822696-f75a-46f5-8b02-0680db65abf5&%24.to=%2Fdevices%2Ffake_device%2Fmessages%2Fdevicebound"
        device_id = "VERY_fake_device"
        assert not mqtt_topic_iothub.is_c2d_topic(topic, device_id)


@pytest.mark.describe(".is_input_topic()")
class TestIsInputTopic(object):
    @pytest.mark.it(
        "Returns True if the provided topic is an input topic and matches the provided device id and module id"
    )
    def test_is_input_topic(self):
        topic = "devices/fake_device/modules/fake_module/inputs/fake_input/%24.mid=6b822696-f75a-46f5-8b02-0680db65abf5&%24.to=%2Fdevices%2Ffake_device%2Fmodules%2Ffake_module%2Finputs%2Ffake_input"
        device_id = "fake_device"
        module_id = "fake_module"
        assert mqtt_topic_iothub.is_input_topic(topic, device_id, module_id)

    @pytest.mark.it("URL encodes the device id and module_id when matching to the topic")
    @pytest.mark.parametrize(
        "topic, device_id, module_id",
        [
            pytest.param(
                "devices/fake%3Fdevice/modules/fake%24module/inputs/fake%23input/%24.mid=6b822696-f75a-46f5-8b02-0680db65abf5&%24.to=%2Fdevices%2Ffake%3Fdevice%2Fmodules%2Ffake%24module%2Finputs%2Ffake%23input",
                "fake?device",
                "fake$module",
                id="Standard URL encoding required for ids",
            ),
            pytest.param(
                "devices/fake%20device/modules/fake%20module/inputs/fake%20input/%24.mid=6b822696-f75a-46f5-8b02-0680db65abf5&%24.to=%2Fdevices%2Ffake%20device%2Fmodules%2Ffake%20module%2Finputs%2Ffake%20input",
                "fake device",
                "fake module",
                id="URL encoding for ' ' character required for ids",
            ),
            pytest.param(
                "devices/fake%2Fdevice/modules/fake%2Fmodule/inputs/fake%20input/%24.mid=6b822696-f75a-46f5-8b02-0680db65abf5&%24.to=%2Fdevices%2Ffake%2Fdevice%2Fmodules%2Ffake%2Fmodule%2Finputs%2Ffake%2Finput",
                "fake/device",
                "fake/module",
                id="URL encoding for '/' character required for ids",
            ),
        ],
    )
    def test_url_encodes(self, topic, device_id, module_id):
        assert mqtt_topic_iothub.is_input_topic(topic, device_id, module_id)

    @pytest.mark.it("Converts the device_id and module_id to string when matching to the topic")
    def test_str_conversion(self):
        topic = "devices/2000/modules/4000/inputs/fake_input/%24.mid=6b822696-f75a-46f5-8b02-0680db65abf5&%24.to=%2Fdevices%2F2000%2Fmodules%2F4000%2Finputs%2Ffake_input"
        device_id = 2000
        module_id = 4000
        assert mqtt_topic_iothub.is_input_topic(topic, device_id, module_id)

    @pytest.mark.it("Returns False if the provided topic is not an input topic")
    @pytest.mark.parametrize(
        "topic, device_id, module_id",
        [
            pytest.param("not a topic", "fake_device", "fake_module", id="Not a topic"),
            pytest.param(
                "devices/fake_device/messages/devicebound/%24.mid=6b822696-f75a-46f5-8b02-0680db65abf5&%24.to=%2Fdevices%2Ffake_device%2Fmessages%2Fdevicebound",
                "fake_device",
                "fake_module",
                id="Topic of wrong type",
            ),
            pytest.param(
                "deivces/fake_device/modules/fake_module/inputs/fake_input/%24.mid=6b822696-f75a-46f5-8b02-0680db65abf5&%24.to=%2Fdevices%2Ffake_device%2Fmodules%2Ffake_module%2Finputs%2Ffake_input",
                "fake_device",
                "fake_module",
                id="Malformed topic",
            ),
        ],
    )
    def test_is_not_input_topic(self, topic, device_id, module_id):
        assert not mqtt_topic_iothub.is_input_topic(topic, device_id, module_id)

    @pytest.mark.it(
        "Returns False if the provided topic is an input topic, but does match the provided device id and/or module_id"
    )
    @pytest.mark.parametrize(
        "device_id, module_id",
        [
            pytest.param("VERY_fake_device", "fake_module", id="Non-matching device_id"),
            pytest.param("fake_device", "VERY_fake_module", id="Non-matching module_id"),
            pytest.param(
                "VERY_fake_device", "VERY_fake_module", id="Non-matching device_id AND module_id"
            ),
            pytest.param(None, "fake_module", id="No device_id"),
            pytest.param("fake_device", None, id="No module_id"),
        ],
    )
    def test_is_input_topic_but_wrong_id(self, device_id, module_id):
        topic = "devices/fake_device/modules/fake_module/inputs/fake_input/%24.mid=6b822696-f75a-46f5-8b02-0680db65abf5&%24.to=%2Fdevices%2Ffake_device%2Fmodules%2Ffake_module%2Finputs%2Ffake_input"
        assert not mqtt_topic_iothub.is_input_topic(topic, device_id, module_id)


@pytest.mark.describe(".is_method_topic()")
class TestIsMethodTopic(object):
    @pytest.mark.it("Returns True if the provided topic is a method topic")
    def test_is_method_topic(self):
        topic = "$iothub/methods/POST/fake_method/?$rid=1"
        assert mqtt_topic_iothub.is_method_topic(topic)

    @pytest.mark.it("Returns False if the provided topic is not a method topic")
    @pytest.mark.parametrize(
        "topic",
        [
            pytest.param("not a topic", id="Not a topic"),
            pytest.param(
                "devices/fake_device/messages/devicebound/%24.mid=6b822696-f75a-46f5-8b02-0680db65abf5&%24.to=%2Fdevices%2Ffake_device%2Fmessages%2Fdevicebound",
                id="Topic of wrong type",
            ),
            pytest.param("$iothub/mthds/POST/fake_method/?$rid=1", id="Malformed topic"),
        ],
    )
    def test_is_not_method_topic(self, topic):
        assert not mqtt_topic_iothub.is_method_topic(topic)


@pytest.mark.describe(".is_twin_response_topic()")
class TestIsTwinResponseTopic(object):
    @pytest.mark.it("Returns True if the provided topic is a twin response topic")
    def test_is_twin_response_topic(self):
        topic = "$iothub/twin/res/200/?$rid=d9d7ce4d-3be9-498b-abde-913b81b880e5"
        assert mqtt_topic_iothub.is_twin_response_topic(topic)

    @pytest.mark.it("Returns False if the provided topic is not a twin response topic")
    @pytest.mark.parametrize(
        "topic",
        [
            pytest.param("not a topic", id="Not a topic"),
            pytest.param("$iothub/methods/POST/fake_method/?$rid=1", id="Topic of wrong type"),
            pytest.param(
                "$iothub/twin/rs/200/?$rid=d9d7ce4d-3be9-498b-abde-913b81b880e5",
                id="Malformed topic",
            ),
        ],
    )
    def test_is_not_twin_response_topic(self, topic):
        assert not mqtt_topic_iothub.is_twin_response_topic(topic)


@pytest.mark.describe(".is_twin_desired_property_patch_topic()")
class TestIsTwinDesiredPropertyPatchTopic(object):
    @pytest.mark.it("Returns True if the provided topic is a desired property patch topic")
    def test_is_desired_property_patch_topic(self):
        topic = "$iothub/twin/PATCH/properties/desired/?$version=1"
        assert mqtt_topic_iothub.is_twin_desired_property_patch_topic(topic)

    @pytest.mark.it("Returns False if the provided topic is not a desired property patch topic")
    @pytest.mark.parametrize(
        "topic",
        [
            pytest.param("not a topic", id="Not a topic"),
            pytest.param("$iothub/methods/POST/fake_method/?$rid=1", id="Topic of wrong type"),
            pytest.param("$iothub/twin/PATCH/properties/dsiered/?$version=1", id="Malformed topic"),
        ],
    )
    def test_is_not_desired_property_patch_topic(self, topic):
        assert not mqtt_topic_iothub.is_twin_desired_property_patch_topic(topic)


@pytest.mark.describe(".get_input_name_from_topic()")
class TestGetInputNameFromTopic(object):
    @pytest.mark.it("Returns the input name from an input topic")
    def test_valid_input_topic(self):
        topic = "devices/fake_device/modules/fake_module/inputs/fake_input/%24.mid=6b822696-f75a-46f5-8b02-0680db65abf5&%24.to=%2Fdevices%2Ffake_device%2Fmodules%2Ffake_module%2Finputs%2Ffake_input"
        expected_input_name = "fake_input"

        assert mqtt_topic_iothub.get_input_name_from_topic(topic) == expected_input_name

    @pytest.mark.it("URL decodes the returned input name")
    @pytest.mark.parametrize(
        "topic, expected_input_name",
        [
            pytest.param(
                "devices/fake_device/modules/fake_module/inputs/fake%24input/%24.mid=6b822696-f75a-46f5-8b02-0680db65abf5&%24.to=%2Fdevices%2Ffake_device%2Fmodules%2Ffake_module%2Finputs%2Ffake%24input",
                "fake$input",
                id="Standard URL Decoding",
            ),
            pytest.param(
                "devices/fake_device/modules/fake_module/inputs/fake+input/%24.mid=6b822696-f75a-46f5-8b02-0680db65abf5&%24.to=%2Fdevices%2Ffake_device%2Fmodules%2Ffake_module%2Finputs%2Ffake+input",
                "fake+input",
                id="Does NOT decode '+' character",
            ),
        ],
    )
    def test_url_decodes_value(self, topic, expected_input_name):
        assert mqtt_topic_iothub.get_input_name_from_topic(topic) == expected_input_name

    @pytest.mark.it("Raises a ValueError if the provided topic is not an input name topic")
    @pytest.mark.parametrize(
        "topic",
        [
            pytest.param("not a topic", id="Not a topic"),
            pytest.param("$iothub/methods/POST/fake_method/?$rid=1", id="Topic of wrong type"),
            pytest.param(
                "devices/fake_device/inputs/fake_input/%24.mid=6b822696-f75a-46f5-8b02-0680db65abf5&%24.to=%2Fdevices%2Ffake_device%2Fmodules%2Ffake_module%2Finputs%2Ffake_input",
                id="Malformed topic",
            ),
        ],
    )
    def test_invalid_input_topic(self, topic):
        with pytest.raises(ValueError):
            mqtt_topic_iothub.get_input_name_from_topic(topic)


@pytest.mark.describe(".get_method_name_from_topic()")
class TestGetMethodNameFromTopic(object):
    @pytest.mark.it("Returns the method name from a method topic")
    def test_valid_method_topic(self):
        topic = "$iothub/methods/POST/fake_method/?$rid=1"
        expected_method_name = "fake_method"

        assert mqtt_topic_iothub.get_method_name_from_topic(topic) == expected_method_name

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
        assert mqtt_topic_iothub.get_method_name_from_topic(topic) == expected_method_name

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
            mqtt_topic_iothub.get_method_name_from_topic(topic)


@pytest.mark.describe(".get_method_request_id_from_topic()")
class TestGetMethodRequestIdFromTopic(object):
    @pytest.mark.it("Returns the request id from a method topic")
    def test_valid_method_topic(self):
        topic = "$iothub/methods/POST/fake_method/?$rid=1"
        expected_request_id = "1"

        assert mqtt_topic_iothub.get_method_request_id_from_topic(topic) == expected_request_id

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
        assert mqtt_topic_iothub.get_method_request_id_from_topic(topic) == expected_request_id

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
            mqtt_topic_iothub.get_method_request_id_from_topic(topic)


@pytest.mark.describe(".get_twin_request_id_from_topic()")
class TestGetTwinRequestIdFromTopic(object):
    @pytest.mark.it("Returns the request id from a twin response topic")
    def test_valid_twin_response_topic(self):
        topic = "$iothub/twin/res/200/?rid=1"
        expected_request_id = "1"

        assert mqtt_topic_iothub.get_twin_request_id_from_topic(topic) == expected_request_id

    @pytest.mark.it("URL decodes the returned value")
    @pytest.mark.parametrize(
        "topic, expected_request_id",
        [
            pytest.param(
                "$iothub/twin/res/200/?rid=fake%24request%2Fid",
                "fake$request/id",
                id="Standard URL Decoding",
            ),
            pytest.param(
                "$iothub/twin/res/200/?rid=fake+request+id",
                "fake+request+id",
                id="Does NOT decode '+' character",
            ),
        ],
    )
    def test_url_decodes_value(self, topic, expected_request_id):
        assert mqtt_topic_iothub.get_twin_request_id_from_topic(topic) == expected_request_id

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
            mqtt_topic_iothub.get_twin_request_id_from_topic(topic)


@pytest.mark.describe(".get_twin_status_code_from_topic()")
class TestGetTwinStatusCodeFromTopic(object):
    @pytest.mark.it("Returns the status from a twin response topic")
    def test_valid_twin_response_topic(self):
        topic = "$iothub/twin/res/200/?rid=1"
        expected_status = "200"

        assert mqtt_topic_iothub.get_twin_status_code_from_topic(topic) == expected_status

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
        assert mqtt_topic_iothub.get_twin_status_code_from_topic(topic) == expected_status

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
            mqtt_topic_iothub.get_twin_request_id_from_topic(topic)


@pytest.mark.describe(".extract_message_properties_from_topic()")
class TestExtractMessagePropertiesFromTopic(object):
    @pytest.mark.it("Adds properties from topic to Message object")
    @pytest.mark.parametrize(
        "topic, expected_system_properties, expected_custom_properties",
        [
            pytest.param(
                "devices/fake_device/messages/devicebound/%24.mid=6b822696-f75a-46f5-8b02-0680db65abf5&%24.to=%2Fdevices%2Ffake_device%2Fmessages%2Fdevicebound",
                {"mid": "6b822696-f75a-46f5-8b02-0680db65abf5"},
                {},
                id="C2D message topic, Mandatory system properties",
            ),
            pytest.param(
                "devices/fake_device/messages/devicebound/%24.exp=3237-07-19T23%3A06%3A40.0000000Z&%24.cid=fake_corid&%24.mid=6b822696-f75a-46f5-8b02-0680db65abf5&%24.to=%2Fdevices%2Ffake_device%2Fmessages%2Fdevicebound&%24.ct=fake_content_type&%24.ce=utf-8",
                {
                    "mid": "6b822696-f75a-46f5-8b02-0680db65abf5",
                    "exp": "3237-07-19T23:06:40.0000000Z",
                    "cid": "fake_corid",
                    "ct": "fake_content_type",
                    "ce": "utf-8",
                },
                {},
                id="C2D message topic, All system properties",
            ),
            pytest.param(
                "devices/fake_device/messages/devicebound/%24.mid=6b822696-f75a-46f5-8b02-0680db65abf5&%24.to=%2Fdevices%2Ffake_device%2Fmessages%2Fdevicebound&custom1=value1&custom2=value2&custom3=value3",
                {"mid": "6b822696-f75a-46f5-8b02-0680db65abf5"},
                {"custom1": "value1", "custom2": "value2", "custom3": "value3"},
                id="C2D message topic, Custom properties",
            ),
            pytest.param(
                "devices/fake_device/modules/fake_module/inputs/fake_input/%24.mid=6b822696-f75a-46f5-8b02-0680db65abf5&%24.to=%2Fdevices%2Ffake_device%2Fmodules%2Ffake_module%2Finputs%2Ffake_input",
                {"mid": "6b822696-f75a-46f5-8b02-0680db65abf5"},
                {},
                id="Input message topic, Mandatory system properties",
            ),
            pytest.param(
                "devices/fake_device/modules/fake_module/inputs/fake_input/%24.exp=3237-07-19T23%3A06%3A40.0000000Z&%24.cid=fake_corid&%24.mid=6b822696-f75a-46f5-8b02-0680db65abf5&%24.to=%2Fdevices%2Ffake_device%2Fmodules%2Ffake_module%2Finputs%2Ffake_input&%24.ct=fake_content_type&%24.ce=utf-8",
                {
                    "mid": "6b822696-f75a-46f5-8b02-0680db65abf5",
                    "exp": "3237-07-19T23:06:40.0000000Z",
                    "cid": "fake_corid",
                    "ct": "fake_content_type",
                    "ce": "utf-8",
                },
                {},
                id="Input message topic, All system properties",
            ),
            pytest.param(
                "devices/fake_device/modules/fake_module/inputs/fake_input/%24.mid=6b822696-f75a-46f5-8b02-0680db65abf5&%24.to=%2Fdevices%2Ffake_device%2Fmodules%2Ffake_module%2Finputs%2Ffake_input&custom1=value1&custom2=value2&custom3=value3",
                {"mid": "6b822696-f75a-46f5-8b02-0680db65abf5"},
                {"custom1": "value1", "custom2": "value2", "custom3": "value3"},
                id="Input message topic, Custom properties",
            ),
        ],
    )
    def test_extracts_properties(
        self, topic, expected_system_properties, expected_custom_properties
    ):
        msg = Message("fake message")
        mqtt_topic_iothub.extract_message_properties_from_topic(topic, msg)

        # Validate MANDATORY system properties
        assert msg.message_id == expected_system_properties["mid"]

        # Validate OPTIONAL system properties
        assert msg.correlation_id == expected_system_properties.get("cid", None)
        assert msg.user_id == expected_system_properties.get("uid", None)
        assert msg.content_type == expected_system_properties.get("ct", None)
        assert msg.content_encoding == expected_system_properties.get("ce", None)
        assert msg.expiry_time_utc == expected_system_properties.get("exp", None)

        # Validate custom properties
        assert msg.custom_properties == expected_custom_properties

    @pytest.mark.it("URL decodes properties from the topic when extracting")
    @pytest.mark.parametrize(
        "topic, expected_system_properties, expected_custom_properties",
        [
            pytest.param(
                "devices/fake%24device/messages/devicebound/%24.exp=3237-07-19T23%3A06%3A40.0000000Z&%24.cid=fake%23corid&%24.mid=message%24id&%24.to=%2Fdevices%2Ffake%24device%2Fmessages%2Fdevicebound&%24.ct=fake%23content%24type&%24.ce=utf-%24&custom%2A=value%23&custom%26=value%24&custom%25=value%40",
                {
                    "mid": "message$id",
                    "exp": "3237-07-19T23:06:40.0000000Z",
                    "cid": "fake#corid",
                    "ct": "fake#content$type",
                    "ce": "utf-$",
                },
                {"custom*": "value#", "custom&": "value$", "custom%": "value@"},
                id="C2D message topic, Standard URL decoding",
            ),
            pytest.param(
                "devices/fake+device/messages/devicebound/%24.exp=3237-07-19T23%3A06%3A40.0000000Z&%24.cid=fake+corid&%24.mid=message+id&%24.to=%2Fdevices%2Ffake+device%2Fmessages%2Fdevicebound&%24.ct=fake+content+type&%24.ce=utf-+&custom+1=value+1&custom+2=value+2&custom+3=value+3",
                {
                    "mid": "message+id",
                    "exp": "3237-07-19T23:06:40.0000000Z",
                    "cid": "fake+corid",
                    "ct": "fake+content+type",
                    "ce": "utf-+",
                },
                {"custom+1": "value+1", "custom+2": "value+2", "custom+3": "value+3"},
                id="C2D message topic, does NOT decode '+' character",
            ),
            pytest.param(
                "devices/fake%24device/modules/fake%23module/inputs/fake%25input/%24.exp=3237-07-19T23%3A06%3A40.0000000Z&%24.cid=fake%23corid&%24.mid=message%24id&%24.to=%2Fdevices%2Ffake%24device%2Fmodules%2Ffake%23module%2Finputs%2Ffake%25input&%24.ct=fake%23content%24type&%24.ce=utf-%24&custom%2A=value%23&custom%26=value%24&custom%25=value%40",
                {
                    "mid": "message$id",
                    "exp": "3237-07-19T23:06:40.0000000Z",
                    "cid": "fake#corid",
                    "ct": "fake#content$type",
                    "ce": "utf-$",
                },
                {"custom*": "value#", "custom&": "value$", "custom%": "value@"},
                id="Input message topic, Standard URL decoding",
            ),
            pytest.param(
                "devices/fake+device/modules/fake+module/inputs/fake+input/%24.exp=3237-07-19T23%3A06%3A40.0000000Z&%24.cid=fake+corid&%24.mid=message+id&%24.to=%2Fdevices%2Ffake+device%2Fmodules%2Ffake+module%2Finputs%2Ffake+input&%24.ct=fake+content+type&%24.ce=utf-+&custom+1=value+1&custom+2=value+2&custom+3=value+3",
                {
                    "mid": "message+id",
                    "exp": "3237-07-19T23:06:40.0000000Z",
                    "cid": "fake+corid",
                    "ct": "fake+content+type",
                    "ce": "utf-+",
                },
                {"custom+1": "value+1", "custom+2": "value+2", "custom+3": "value+3"},
                id="Input message topic, does NOT decode '+' character",
            ),
        ],
    )
    def test_url_decode(self, topic, expected_system_properties, expected_custom_properties):
        msg = Message("fake message")
        mqtt_topic_iothub.extract_message_properties_from_topic(topic, msg)

        # Validate MANDATORY system properties
        assert msg.message_id == expected_system_properties["mid"]

        # Validate OPTIONAL system properties
        assert msg.correlation_id == expected_system_properties.get("cid", None)
        assert msg.user_id == expected_system_properties.get("uid", None)
        assert msg.content_type == expected_system_properties.get("ct", None)
        assert msg.content_encoding == expected_system_properties.get("ce", None)
        assert msg.expiry_time_utc == expected_system_properties.get("exp", None)

        # Validate custom properties
        assert msg.custom_properties == expected_custom_properties

    @pytest.mark.it("Ignores certain properties in a C2D message topic, and does NOT extract them")
    @pytest.mark.parametrize(
        "topic",
        [
            pytest.param(
                "devices/fake_device/messages/devicebound/%24.mid=6b822696-f75a-46f5-8b02-0680db65abf5&%24.to=%2Fdevices%2Ffake_device%2Fmessages%2Fdevicebound",
                id="$.to",
            ),
            pytest.param(
                "devices/fake_device/messages/devicebound/%24.mid=6b822696-f75a-46f5-8b02-0680db65abf5&iothub-ack=full",
                id="iothub-ack",
            ),
        ],
    )
    def test_ignores_on_c2d(self, topic):
        msg = Message("fake message")
        mqtt_topic_iothub.extract_message_properties_from_topic(topic, msg)
        assert msg.custom_properties == {}

    @pytest.mark.it(
        "Ignores certain properties in an input message topic, and does NOT extract them"
    )
    @pytest.mark.parametrize(
        "topic",
        [
            pytest.param(
                "devices/fake_device/modules/fake_module/inputs/fake_input/%24.mid=6b822696-f75a-46f5-8b02-0680db65abf5&%24.to=%2Fdevices%2Ffake_device%2Fmodules%2Ffake_module%2Finputs%2Ffake_input",
                id="$.to",
            ),
            pytest.param(
                "devices/fake_device/modules/fake_module/inputs/fake_input/%24.mid=6b822696-f75a-46f5-8b02-0680db65abf5&iothub-ack=full",
                id="iothub-ack",
            ),
        ],
    )
    def test_ignores_on_input_message(self, topic):
        msg = Message("fake message")
        mqtt_topic_iothub.extract_message_properties_from_topic(topic, msg)
        assert msg.custom_properties == {}

    @pytest.mark.it(
        "Raises a ValueError if the provided topic is not a c2d topic or an input message topic"
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
        msg = Message("fake message")
        with pytest.raises(ValueError):
            mqtt_topic_iothub.extract_message_properties_from_topic(topic, msg)

    @pytest.mark.it("Extracts system and custom properties without values")
    @pytest.mark.parametrize(
        "topic, extracted_system_properties, extracted_custom_properties",
        [
            pytest.param(
                "devices/fakedevice/messages/devicebound/topic=%2Fsubscriptions%2FresourceGroups&subject=%2FgraphInstances&dataVersion=1.0&%24.cdid=fakecdid&%24.mid=e32c2285-668e-4161-a236-9f5f6b90362c&%24.cid&%24.uid",
                {"mid": "e32c2285-668e-4161-a236-9f5f6b90362c", "cid": None, "uid": None},
                {
                    "topic": "/subscriptions/resourceGroups",
                    "subject": "/graphInstances",
                    "dataVersion": "1.0",
                    "$.cdid": "fakecdid",
                },
                id="C2D topic with some system properties not having values",
            ),
            pytest.param(
                "devices/fakedevice/modules/fakemodule/inputs/fakeinput/topic=%2Fsubscriptions%2FresourceGroups&subject=%2FgraphInstances&dataVersion=1.0&%24.cdid=fakecdid&%24.mid=e32c2285-668e-4161-a236-9f5f6b90362c&%24.cid&%24.uid",
                {"mid": "e32c2285-668e-4161-a236-9f5f6b90362c", "cid": None, "uid": None},
                {
                    "topic": "/subscriptions/resourceGroups",
                    "subject": "/graphInstances",
                    "dataVersion": "1.0",
                    "$.cdid": "fakecdid",
                },
                id="Input message topic with some system properties not having values",
            ),
            pytest.param(
                "devices/fakedevice/messages/devicebound/topic=%2Fsubscriptions%2FresourceGroups&subject=%2FgraphInstances&dataVersion&%24.cdid=fakecdid&%24.mid=e32c2285-668e-4161-a236-9f5f6b90362c&%24.cid=fakecorrid&%24.uid=harrypotter&classname",
                {
                    "mid": "e32c2285-668e-4161-a236-9f5f6b90362c",
                    "cid": "fakecorrid",
                    "uid": "harrypotter",
                },
                {
                    "topic": "/subscriptions/resourceGroups",
                    "subject": "/graphInstances",
                    "$.cdid": "fakecdid",
                    "classname": None,
                    "dataVersion": None,
                },
                id="C2D topic with some custom properties not having values",
            ),
            pytest.param(
                "devices/fakedevice/modules/fakemodule/inputs/fakeinput/topic=%2Fsubscriptions%2FresourceGroups&subject=%2FgraphInstances&dataVersion&%24.cdid=fakecdid&%24.mid=e32c2285-668e-4161-a236-9f5f6b90362c&%24.cid=fakecorrid&%24.uid=harrypotter&classname",
                {
                    "mid": "e32c2285-668e-4161-a236-9f5f6b90362c",
                    "cid": "fakecorrid",
                    "uid": "harrypotter",
                },
                {
                    "topic": "/subscriptions/resourceGroups",
                    "subject": "/graphInstances",
                    "$.cdid": "fakecdid",
                    "classname": None,
                    "dataVersion": None,
                },
                id="Input message topic with some custom properties not having values",
            ),
            pytest.param(
                "devices/fakedevice/messages/devicebound/topic=%2Fsubscriptions%2FresourceGroups&subject=%2FgraphInstances&dataVersion&%24.cdid=fakecdid&%24.mid=e32c2285-668e-4161-a236-9f5f6b90362c&%24.cid&%24.uid&classname",
                {"mid": "e32c2285-668e-4161-a236-9f5f6b90362c", "cid": None, "uid": None},
                {
                    "topic": "/subscriptions/resourceGroups",
                    "subject": "/graphInstances",
                    "$.cdid": "fakecdid",
                    "classname": None,
                    "dataVersion": None,
                },
                id="C2D topic with some system properties and some custom not having values",
            ),
            pytest.param(
                "devices/fakedevice/modules/fakemodule/inputs/fakeinput/topic=%2Fsubscriptions%2FresourceGroups&subject=%2FgraphInstances&dataVersion&%24.cdid=fakecdid&%24.mid=e32c2285-668e-4161-a236-9f5f6b90362c&%24.cid&%24.uid&classname",
                {"mid": "e32c2285-668e-4161-a236-9f5f6b90362c", "cid": None, "uid": None},
                {
                    "topic": "/subscriptions/resourceGroups",
                    "subject": "/graphInstances",
                    "$.cdid": "fakecdid",
                    "classname": None,
                    "dataVersion": None,
                },
                id="Input message topic with some system properties and some custom not having values",
            ),
        ],
    )
    def test_receive_topic_without_values(
        self, topic, extracted_system_properties, extracted_custom_properties
    ):
        msg = Message("fake message")
        mqtt_topic_iothub.extract_message_properties_from_topic(topic, msg)

        # Validate system properties received
        assert msg.message_id == extracted_system_properties["mid"]
        assert msg.correlation_id == extracted_system_properties["cid"]
        assert msg.user_id == extracted_system_properties["uid"]

        # Validate system properties NOT received
        assert msg.content_type == extracted_system_properties.get("ct", None)
        assert msg.content_encoding == extracted_system_properties.get("ce", None)
        assert msg.expiry_time_utc == extracted_system_properties.get("exp", None)

        # Validate custom properties
        assert msg.custom_properties == extracted_custom_properties

    @pytest.mark.it("Extracts system and custom properties with empty string values")
    @pytest.mark.parametrize(
        "topic, extracted_system_properties, extracted_custom_properties",
        [
            pytest.param(
                "devices/fakedevice/messages/devicebound/topic=%2Fsubscriptions%2FresourceGroups&subject=%2FgraphInstances&dataVersion=1.0&%24.cdid=fakecdid&%24.mid=e32c2285-668e-4161-a236-9f5f6b90362c&%24.cid=&%24.uid=",
                {"mid": "e32c2285-668e-4161-a236-9f5f6b90362c", "cid": "", "uid": ""},
                {
                    "topic": "/subscriptions/resourceGroups",
                    "subject": "/graphInstances",
                    "dataVersion": "1.0",
                    "$.cdid": "fakecdid",
                },
                id="C2D topic with some system properties not having values",
            ),
            pytest.param(
                "devices/fakedevice/modules/fakemodule/inputs/fakeinput/topic=%2Fsubscriptions%2FresourceGroups&subject=%2FgraphInstances&dataVersion=1.0&%24.cdid=fakecdid&%24.mid=e32c2285-668e-4161-a236-9f5f6b90362c&%24.cid=&%24.uid=",
                {"mid": "e32c2285-668e-4161-a236-9f5f6b90362c", "cid": "", "uid": ""},
                {
                    "topic": "/subscriptions/resourceGroups",
                    "subject": "/graphInstances",
                    "dataVersion": "1.0",
                    "$.cdid": "fakecdid",
                },
                id="Input message topic with some system properties not having values",
            ),
            pytest.param(
                "devices/fakedevice/messages/devicebound/topic=%2Fsubscriptions%2FresourceGroups&subject=%2FgraphInstances&dataVersion=&%24.cdid=fakecdid&%24.mid=e32c2285-668e-4161-a236-9f5f6b90362c&%24.cid=fakecorrid&%24.uid=harrypotter&classname=",
                {
                    "mid": "e32c2285-668e-4161-a236-9f5f6b90362c",
                    "cid": "fakecorrid",
                    "uid": "harrypotter",
                },
                {
                    "topic": "/subscriptions/resourceGroups",
                    "subject": "/graphInstances",
                    "$.cdid": "fakecdid",
                    "dataVersion": "",
                    "classname": "",
                },
                id="C2D topic with some custom properties not having values",
            ),
            pytest.param(
                "devices/fakedevice/modules/fakemodule/inputs/fakeinput/topic=%2Fsubscriptions%2FresourceGroups&subject=%2FgraphInstances&dataVersion=&%24.cdid=fakecdid&%24.mid=e32c2285-668e-4161-a236-9f5f6b90362c&%24.cid=fakecorrid&%24.uid=harrypotter&classname=",
                {
                    "mid": "e32c2285-668e-4161-a236-9f5f6b90362c",
                    "cid": "fakecorrid",
                    "uid": "harrypotter",
                },
                {
                    "topic": "/subscriptions/resourceGroups",
                    "subject": "/graphInstances",
                    "$.cdid": "fakecdid",
                    "dataVersion": "",
                    "classname": "",
                },
                id="Input message topic with some custom properties not having values",
            ),
            pytest.param(
                "devices/fakedevice/messages/devicebound/topic=%2Fsubscriptions%2FresourceGroups&subject=%2FgraphInstances&dataVersion=&%24.cdid=fakecdid&%24.mid=e32c2285-668e-4161-a236-9f5f6b90362c&%24.cid=&%24.uid=&classname=",
                {"mid": "e32c2285-668e-4161-a236-9f5f6b90362c", "cid": "", "uid": ""},
                {
                    "topic": "/subscriptions/resourceGroups",
                    "subject": "/graphInstances",
                    "$.cdid": "fakecdid",
                    "dataVersion": "",
                    "classname": "",
                },
                id="C2D topic with some system properties and some custom not having values",
            ),
            pytest.param(
                "devices/fakedevice/modules/fakemodule/inputs/fakeinput/topic=%2Fsubscriptions%2FresourceGroups&subject=%2FgraphInstances&dataVersion=&%24.cdid=fakecdid&%24.mid=e32c2285-668e-4161-a236-9f5f6b90362c&%24.cid=&%24.uid=&classname=",
                {"mid": "e32c2285-668e-4161-a236-9f5f6b90362c", "cid": "", "uid": ""},
                {
                    "topic": "/subscriptions/resourceGroups",
                    "subject": "/graphInstances",
                    "$.cdid": "fakecdid",
                    "dataVersion": "",
                    "classname": "",
                },
                id="Input message topic with some system properties and some custom not having values",
            ),
        ],
    )
    def test_receive_topic_with_empty_values(
        self, topic, extracted_system_properties, extracted_custom_properties
    ):
        msg = Message("fake message")
        mqtt_topic_iothub.extract_message_properties_from_topic(topic, msg)

        # Validate system properties received
        assert msg.message_id == extracted_system_properties["mid"]
        assert msg.correlation_id == extracted_system_properties["cid"]
        assert msg.user_id == extracted_system_properties["uid"]

        # Validate system properties NOT received
        assert msg.content_type == extracted_system_properties.get("ct", None)
        assert msg.content_encoding == extracted_system_properties.get("ce", None)
        assert msg.expiry_time_utc == extracted_system_properties.get("exp", None)

        # Validate custom properties
        assert msg.custom_properties == extracted_custom_properties


@pytest.mark.describe(".encode_message_properties_in_topic()")
class TestEncodeMessagePropertiesInTopic(object):
    def create_message(self, system_properties, custom_properties):
        m = Message("payload")
        m.message_id = system_properties.get("mid")
        m.correlation_id = system_properties.get("cid")
        m.user_id = system_properties.get("uid")
        m.output_name = system_properties.get("on")
        m.content_encoding = system_properties.get("ce")
        m.content_type = system_properties.get("ct")
        m.expiry_time_utc = system_properties.get("exp")
        if system_properties.get("ifid"):
            m.set_as_security_message()
        m.custom_properties = custom_properties
        return m

    @pytest.fixture(params=["C2D Message", "Input Message"])
    def message_topic(self, request):
        if request.param == "C2D Message":
            return "devices/fake_device/messages/events/"
        else:
            return "devices/fake_device/modules/fake_module/messages/events/"

    @pytest.mark.it(
        "Returns a new version of the given topic string that contains message properties from the given message"
    )
    @pytest.mark.parametrize(
        "message_system_properties, message_custom_properties, expected_encoding",
        [
            pytest.param({}, {}, "", id="No properties"),
            pytest.param(
                {"mid": "1234", "ce": "utf-8"},
                {},
                "%24.mid=1234&%24.ce=utf-8",
                id="Some System Properties",
            ),
            pytest.param(
                {
                    "mid": "1234",
                    "cid": "5678",
                    "uid": "userid",
                    "on": "output",
                    "ce": "utf-8",
                    "ct": "type",
                    "exp": datetime.datetime(2019, 2, 2),
                    "ifid": True,
                },
                {},
                "%24.on=output&%24.mid=1234&%24.cid=5678&%24.uid=userid&%24.ct=type&%24.ce=utf-8&%24.ifid=urn%3Aazureiot%3ASecurity%3ASecurityAgent%3A1&%24.exp=2019-02-02T00%3A00%3A00",
                id="All System Properties",
            ),
            pytest.param(
                {},
                {"custom1": "value1", "custom2": "value2", "custom3": "value3"},
                "custom1=value1&custom2=value2&custom3=value3",
                id="Custom Properties ONLY",
            ),
            pytest.param(
                {
                    "mid": "1234",
                    "cid": "5678",
                    "uid": "userid",
                    "on": "output",
                    "ce": "utf-8",
                    "ct": "type",
                    "exp": datetime.datetime(2019, 2, 2),
                    "ifid": True,
                },
                {"custom1": "value1", "custom2": "value2", "custom3": "value3"},
                "%24.on=output&%24.mid=1234&%24.cid=5678&%24.uid=userid&%24.ct=type&%24.ce=utf-8&%24.ifid=urn%3Aazureiot%3ASecurity%3ASecurityAgent%3A1&%24.exp=2019-02-02T00%3A00%3A00&custom1=value1&custom2=value2&custom3=value3",
                id="System Properties AND Custom Properties",
            ),
        ],
    )
    def test_encodes_properties(
        self, message_topic, message_system_properties, message_custom_properties, expected_encoding
    ):
        message = self.create_message(message_system_properties, message_custom_properties)
        encoded_topic = mqtt_topic_iothub.encode_message_properties_in_topic(message, message_topic)

        assert encoded_topic.startswith(message_topic)
        encoding = encoded_topic.split(message_topic)[1]
        assert encoding == expected_encoding

    @pytest.mark.it("URL encodes message properties when adding them to the topic")
    @pytest.mark.parametrize(
        "message_system_properties, message_custom_properties, expected_encoding",
        [
            pytest.param(
                {
                    "mid": "message#id",
                    "cid": "correlation#id",
                    "uid": "user#id",
                    "on": "some#output",
                    "ce": "utf-#",
                    "ct": "fake#type",
                    "exp": datetime.datetime(2019, 2, 2),
                    "ifid": True,
                },
                {"custom#1": "value#1", "custom#2": "value#2", "custom#3": "value#3"},
                "%24.on=some%23output&%24.mid=message%23id&%24.cid=correlation%23id&%24.uid=user%23id&%24.ct=fake%23type&%24.ce=utf-%23&%24.ifid=urn%3Aazureiot%3ASecurity%3ASecurityAgent%3A1&%24.exp=2019-02-02T00%3A00%3A00&custom%231=value%231&custom%232=value%232&custom%233=value%233",
                id="Standard URL Encoding",
            ),
            pytest.param(
                {
                    "mid": "message id",
                    "cid": "correlation id",
                    "uid": "user id",
                    "on": "some output",
                    "ce": "utf- ",
                    "ct": "fake type",
                    "exp": datetime.datetime(2019, 2, 2),
                    "ifid": True,
                },
                {"custom 1": "value 1", "custom 2": "value 2", "custom 3": "value 3"},
                "%24.on=some%20output&%24.mid=message%20id&%24.cid=correlation%20id&%24.uid=user%20id&%24.ct=fake%20type&%24.ce=utf-%20&%24.ifid=urn%3Aazureiot%3ASecurity%3ASecurityAgent%3A1&%24.exp=2019-02-02T00%3A00%3A00&custom%201=value%201&custom%202=value%202&custom%203=value%203",
                id="URL Encoding of ' ' character",
            ),
            pytest.param(
                {
                    "mid": "message/id",
                    "cid": "correlation/id",
                    "uid": "user/id",
                    "on": "some/output",
                    "ce": "utf-/",
                    "ct": "fake/type",
                    "exp": datetime.datetime(2019, 2, 2),
                    "ifid": True,
                },
                {"custom/1": "value/1", "custom/2": "value/2", "custom/3": "value/3"},
                "%24.on=some%2Foutput&%24.mid=message%2Fid&%24.cid=correlation%2Fid&%24.uid=user%2Fid&%24.ct=fake%2Ftype&%24.ce=utf-%2F&%24.ifid=urn%3Aazureiot%3ASecurity%3ASecurityAgent%3A1&%24.exp=2019-02-02T00%3A00%3A00&custom%2F1=value%2F1&custom%2F2=value%2F2&custom%2F3=value%2F3",
                id="URL Encoding of '/' character",
            ),
        ],
    )
    def test_url_encodes(
        self, message_topic, message_system_properties, message_custom_properties, expected_encoding
    ):
        message = self.create_message(message_system_properties, message_custom_properties)
        encoded_topic = mqtt_topic_iothub.encode_message_properties_in_topic(message, message_topic)

        assert encoded_topic.startswith(message_topic)
        encoding = encoded_topic.split(message_topic)[1]
        assert encoding == expected_encoding

    @pytest.mark.it("String converts message properties when adding them to the topic")
    def test_str_conversion(self, message_topic):
        system_properties = {"mid": 1234, "cid": 5678, "uid": 4000, "on": 2222, "ce": 8, "ct": 12}
        custom_properties = {1: 23, 47: 245, 3000: 9458}
        expected_encoding = "%24.on=2222&%24.mid=1234&%24.cid=5678&%24.uid=4000&%24.ct=12&%24.ce=8&1=23&3000=9458&47=245"
        message = self.create_message(system_properties, custom_properties)
        encoded_topic = mqtt_topic_iothub.encode_message_properties_in_topic(message, message_topic)

        assert encoded_topic.startswith(message_topic)
        encoding = encoded_topic.split(message_topic)[1]
        assert encoding == expected_encoding

    @pytest.mark.it(
        "Raises ValueError if duplicate keys exist in custom properties due to string conversion"
    )
    def test_duplicate_keys(self, message_topic):
        system_properties = {}
        custom_properties = {1: "val1", "1": "val2"}
        message = self.create_message(system_properties, custom_properties)

        with pytest.raises(ValueError):
            mqtt_topic_iothub.encode_message_properties_in_topic(message, message_topic)
