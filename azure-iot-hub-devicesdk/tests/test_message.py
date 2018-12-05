# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

from azure.iot.hub.devicesdk.message import Message
import pytest


def test_construct_message_with_string():
    s = "After all this time? Always"
    msg = Message(s)
    assert msg.data == s


def test_construct_message_with_ids():
    s = "After all this time? Always"
    message_id = "Postage12323"
    msg = Message(s, message_id)
    assert msg.message_id == message_id


def test_construct_message_with_contenttype_encoding():
    s = "After all this time? Always"
    type = "application/json"
    encoding = "utf-16"
    msg = Message(s, None, encoding, type)
    assert msg.content_encoding == encoding
    assert msg.content_type == type


def test_int():
    s = 987
    msg = Message(s)
    assert msg.data == s


def test_someobject():
    s = "After all this time? Always"
    inner_mes = Message(s)
    msg = Message(inner_mes)
    assert msg.data == inner_mes
