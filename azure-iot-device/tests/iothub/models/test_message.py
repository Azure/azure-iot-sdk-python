# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
import logging
from azure.iot.device.iothub.models import Message
from azure.iot.device import constant

logging.basicConfig(level=logging.DEBUG)

data_str = "Some string of data"
data_int = 987
data_obj = Message(data_str)


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
