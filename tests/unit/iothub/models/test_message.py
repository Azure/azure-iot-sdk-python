# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import datetime
import logging

import pytest

from azure.iot.device.iothub.models import Message
from azure.iot.device import constant

logging.basicConfig(level=logging.DEBUG)

data_str = "Some string of data"
data_int = 987
data_obj = Message(data_str)


def _make_unicode_message(target_size):
    multibyte_character = "\N{SNAKE}"
    remaining_size = target_size - len(multibyte_character.encode("utf-8"))
    return Message(multibyte_character + ("a" * remaining_size))


def _make_custom_property_message(target_size):
    key = "custom"
    value = "property"
    property_size = len(key.encode("utf-8")) + len(value.encode("utf-8"))
    message = Message(b"a" * (target_size - property_size))
    message.custom_properties[key] = value
    return message


def _set_system_properties(message):
    message.output_name = "output"
    message.message_id = 1234
    message.correlation_id = 5678
    message.user_id = 4000
    message.content_type = "application/json"
    message.content_encoding = "utf-8"
    message.expiry_time_utc = datetime.datetime(2026, 8, 21, 15, 33, 42)
    message.set_as_security_message()
    return [
        "output",
        "1234",
        "5678",
        "4000",
        "application/json",
        "utf-8",
        constant.SECURITY_MESSAGE_INTERFACE_ID,
        "2026-08-21T15:33:42",
    ]


def _make_system_property_message(target_size):
    message = Message(b"")
    values = _set_system_properties(message)
    property_size = sum(len(value.encode("utf-8")) for value in values)
    message.data = b"a" * (target_size - property_size)
    return message


@pytest.mark.describe("Message")
class TestMessage(object):
    @pytest.mark.it("Instantiates from data type")
    @pytest.mark.parametrize(
        "data", [data_str, data_int, data_obj], ids=["String", "Integer", "Message"]
    )
    def test_instantiates_from_data(self, data):
        msg = Message(data)
        assert msg.data == data

    @pytest.mark.it("Instantiates with optional provided message id")
    def test_instantiates_with_optional_message_id(self):
        message_id = "Postage12323"
        msg = Message("some message", message_id)
        assert msg.message_id == message_id

    @pytest.mark.it("Instantiates with optional provided content type and content encoding")
    def test_instantiates_with_optional_contenttype_encoding(self):
        ctype = "application/json"
        encoding = "utf-16"
        msg = Message("some message", None, encoding, ctype)
        assert msg.content_encoding == encoding
        assert msg.content_type == ctype

    @pytest.mark.it("Instantiates with optional provided output name")
    def test_instantiates_with_optional_output_name(self):
        output_name = "some_output"
        msg = Message("some message", output_name=output_name)
        assert msg.output_name == output_name

    @pytest.mark.it("Instantiates with no custom properties set")
    def test_default_custom_properties(self):
        msg = Message("some message")
        assert msg.custom_properties == {}

    @pytest.mark.it("Instantiates with no set expiry time")
    def test_default_expiry_time(self):
        msg = Message("some message")
        assert msg.expiry_time_utc is None

    @pytest.mark.it("Instantiates with no set correlation id")
    def test_default_corr_id(self):
        msg = Message("some message")
        assert msg.correlation_id is None

    @pytest.mark.it("Instantiates with no set user id")
    def test_default_user_id(self):
        msg = Message("some message")
        assert msg.user_id is None

    @pytest.mark.it("Instantiates with no set input name")
    def test_default_input_name(self):
        msg = Message("some message")
        assert msg.input_name is None

    @pytest.mark.it("Instantiates with no set ack value")
    def test_default_ack(self):
        msg = Message("some message")
        assert msg.ack is None

    @pytest.mark.it("Instantiates with no set iothub_interface_id (i.e. not as a security message)")
    def test_default_security_msg_status(self):
        msg = Message("some message")
        assert msg.iothub_interface_id is None

    @pytest.mark.it("Maintains iothub_interface_id (security message) as a read-only property")
    def test_read_only_iothub_interface_id(self):
        msg = Message("some message")
        with pytest.raises(AttributeError):
            msg.iothub_interface_id = "value"

    @pytest.mark.it(
        "Uses string representation of data/payload attribute as string representation of Message"
    )
    @pytest.mark.parametrize(
        "data", [data_str, data_int, data_obj], ids=["String", "Integer", "Message"]
    )
    def test_str_rep(self, data):
        msg = Message(data)
        assert str(msg) == str(data)

    @pytest.mark.it("Can be set as a security message via API")
    def test_setting_message_as_security_message(self):
        ctype = "application/json"
        encoding = "utf-16"
        msg = Message("some message", None, encoding, ctype)
        assert msg.iothub_interface_id is None
        msg.set_as_security_message()
        assert msg.iothub_interface_id == constant.SECURITY_MESSAGE_INTERFACE_ID

    @pytest.mark.it("Measures payload using the MQTT transport encoding")
    @pytest.mark.parametrize(
        "data, expected_size",
        [
            pytest.param("message", 7, id="String"),
            pytest.param("\N{LATIN SMALL LETTER E WITH ACUTE}\N{SNAKE}", 6, id="Unicode string"),
            pytest.param(b"\x00\xff", 2, id="Bytes"),
            pytest.param(bytearray(b"\x00\xff"), 2, id="Bytearray"),
            pytest.param(1234, 4, id="Integer"),
            pytest.param(-1.25, 5, id="Float"),
            pytest.param(None, 0, id="None"),
        ],
    )
    def test_get_size_payload_types(self, data, expected_size):
        assert Message(data).get_size() == expected_size

    @pytest.mark.it("Raises TypeError for payload types not supported by the MQTT transport")
    @pytest.mark.parametrize(
        "data",
        [
            pytest.param({"a": 1}, id="Dictionary"),
            pytest.param([1, 2, 3], id="List"),
            pytest.param(object(), id="Object"),
        ],
    )
    def test_get_size_invalid_payload_type(self, data):
        with pytest.raises(TypeError):
            Message(data).get_size()

    @pytest.mark.it("Counts custom property names and values after string conversion")
    def test_get_size_custom_properties(self):
        message = Message(b"body")
        message.custom_properties = {1: 23, "custom": "property"}

        expected_property_size = len("1") + len("23") + len("custom") + len("property")
        assert message.get_size() == len(b"body") + expected_property_size

    @pytest.mark.it("Counts system property values but not their names")
    def test_get_size_system_properties(self):
        message = Message(b"body")
        values = _set_system_properties(message)

        expected_property_size = sum(len(value.encode("utf-8")) for value in values)
        assert message.get_size() == len(b"body") + expected_property_size

    @pytest.mark.it("Does not count receive-only properties")
    def test_get_size_receive_only_properties(self):
        message = Message("body")
        message.input_name = "input"
        message.ack = "full"

        assert message.get_size() == len("body")

    @pytest.mark.it("Does not count MQTT topic encoding or system property names")
    def test_get_size_excludes_protocol_overhead(self):
        message = Message(b"")
        message.message_id = "#"
        message.custom_properties["#"] = "#"

        assert message.get_size() == 3

    @pytest.mark.it("Is deterministic below, at, and above the 256 KB limit")
    @pytest.mark.parametrize(
        "message_factory",
        [
            pytest.param(lambda target_size: Message(b"a" * target_size), id="Bytes payload"),
            pytest.param(_make_unicode_message, id="Unicode payload"),
            pytest.param(_make_custom_property_message, id="Custom properties"),
            pytest.param(_make_system_property_message, id="System properties"),
        ],
    )
    @pytest.mark.parametrize(
        "size_delta",
        [
            pytest.param(-1, id="Below limit"),
            pytest.param(0, id="At limit"),
            pytest.param(1, id="Above limit"),
        ],
    )
    def test_get_size_boundary(self, message_factory, size_delta):
        expected_size = constant.TELEMETRY_MESSAGE_SIZE_LIMIT + size_delta
        message = message_factory(expected_size)

        assert message.get_size() == expected_size
