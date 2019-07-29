# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
import logging
from azure.iot.device.iothub.models import Message

logging.basicConfig(level=logging.INFO)


@pytest.mark.describe("Message")
class TestMessage(object):

    data_str = "After all this time? Always"
    data_int = 987
    data_obj = Message(data_str)

    @pytest.mark.it("Instantiates from data type")
    @pytest.mark.parametrize(
        "data", [data_str, data_int, data_obj], ids=["String", "Integer", "Message"]
    )
    def test_instantiates_from_data(self, data):
        msg = Message(data)
        assert msg.data == data

    @pytest.mark.it("Instantiates with optional message id")
    def test_instantiates_with_optional_message_id(self):
        s = "After all this time? Always"
        message_id = "Postage12323"
        msg = Message(s, message_id)
        assert msg.message_id == message_id

    @pytest.mark.it("Instantiates with optional content type encoding")
    def test_instantiates_with_optional_contenttype_encoding(self):
        s = "After all this time? Always"
        ctype = "application/json"
        encoding = "utf-16"
        msg = Message(s, None, encoding, ctype)
        assert msg.content_encoding == encoding
        assert msg.content_type == ctype

    @pytest.mark.it(
        "Uses string representation of data/payload attribute as string representation of Message"
    )
    @pytest.mark.parametrize(
        "data", [data_str, data_int, data_obj], ids=["String", "Integer", "Message"]
    )
    def test_str_rep(self, data):
        msg = Message(data)
        assert str(msg) == str(data)
