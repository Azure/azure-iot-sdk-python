# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
from azure.iot.hub.devicesdk.message import Message


class TestMessage(object):

    data_str = "After all this time? Always"
    data_int = 987
    data_obj = Message(data_str)

    @pytest.mark.parametrize(
        "data", [data_str, data_int, data_obj], ids=["String", "Integer", "Message"]
    )
    def test_instantiates_from_data(self, data):
        msg = Message(data)
        assert msg.data == data

    def test_instantiates_with_optional_message_id(self):
        s = "After all this time? Always"
        message_id = "Postage12323"
        msg = Message(s, message_id)
        assert msg.message_id == message_id

    def test_instantiates_with_optional_contenttype_encoding(self):
        s = "After all this time? Always"
        type = "application/json"
        encoding = "utf-16"
        msg = Message(s, None, encoding, type)
        assert msg.content_encoding == encoding
        assert msg.content_type == type
