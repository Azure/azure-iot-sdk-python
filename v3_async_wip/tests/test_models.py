# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
import logging
from v3_async_wip.models import Message, MethodRequest, MethodResponse
from v3_async_wip import constant

logging.basicConfig(level=logging.DEBUG)

FAKE_RID = "123"
FAKE_METHOD_NAME = "some_method"
FAKE_STATUS = 200


json_serializable_payload_params = [
    pytest.param("String payload", id="String Payload"),
    pytest.param(123, id="Integer Payload"),
    pytest.param(2.0, id="Float Payload"),
    pytest.param(True, id="Boolean Payload"),
    pytest.param({"dictionary": {"payload": "nested"}}, id="Dictionary Payload"),
    pytest.param([1, 2, 3], id="List Payload"),
    pytest.param((1, 2, 3), id="Tuple Payload"),
    pytest.param(None, id="No Payload"),
]


@pytest.mark.describe("Message")
class TestMessage:
    @pytest.mark.it("Instantiates with the provided payload set as an attribute")
    @pytest.mark.parametrize("payload", json_serializable_payload_params)
    def test_instantiates_from_data(self, payload):
        msg = Message(payload)
        assert msg.payload == payload

    @pytest.mark.it("Instantiates with optional provided message id set as an attribute")
    def test_instantiates_with_optional_message_id(self):
        message_id = "Postage12323"
        msg = Message("some message", message_id)
        assert msg.message_id == message_id

    @pytest.mark.it(
        "Instantiates with optional provided content type and content encoding set as attributes"
    )
    def test_instantiates_with_optional_contenttype_encoding(self):
        ctype = "application/json"
        encoding = "utf-16"
        msg = Message("some message", None, encoding, ctype)
        assert msg.content_encoding == encoding
        assert msg.content_type == ctype

    @pytest.mark.it("Instantiates with no custom properties set")
    def test_default_custom_properties(self):
        msg = Message("some message")
        assert msg.custom_properties == {}

    @pytest.mark.it("Instantiates with optional provided output name set as an attribute")
    def test_instantiates_with_optional_output_name(self):
        output_name = "some_output"
        msg = Message("some message", output_name=output_name)
        assert msg.output_name == output_name

    @pytest.mark.it("Instantiates with no set input name")
    def test_default_input_name(self):
        msg = Message("some message")
        assert msg.input_name is None

    @pytest.mark.it("Instantiates with no set ack value")
    def test_default_ack(self):
        msg = Message("some message")
        assert msg.ack is None

    @pytest.mark.it("Instantiates with no set expiry time")
    def test_default_expiry_time(self):
        msg = Message("some message")
        assert msg.expiry_time_utc is None

    @pytest.mark.it("Instantiates with no set user id")
    def test_default_user_id(self):
        msg = Message("some message")
        assert msg.user_id is None

    @pytest.mark.it("Instantiates with no set correlation id")
    def test_default_corr_id(self):
        msg = Message("some message")
        assert msg.correlation_id is None

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
    @pytest.mark.parametrize("payload", json_serializable_payload_params)
    def test_str_rep(self, payload):
        msg = Message(payload)
        assert str(msg) == str(payload)

    @pytest.mark.it("Can be set as a security message via API")
    def test_setting_message_as_security_message(self):
        ctype = "application/json"
        encoding = "utf-16"
        msg = Message("some message", None, encoding, ctype)
        assert msg.iothub_interface_id is None
        msg.set_as_security_message()
        assert msg.iothub_interface_id == constant.SECURITY_MESSAGE_INTERFACE_ID


@pytest.mark.describe("MethodRequest")
class TestMethodRequest:
    @pytest.mark.it("Instantiates with the provided 'request_id' set as an attribute")
    def test_request_id(self):
        m_req = MethodRequest(request_id=FAKE_RID, name=FAKE_METHOD_NAME, payload={})
        assert m_req.request_id == FAKE_RID

    @pytest.mark.it("Instantiates with the provided 'name' set as an attribute")
    def test_name(self):
        m_req = MethodRequest(request_id=FAKE_RID, name=FAKE_METHOD_NAME, payload={})
        assert m_req.name == FAKE_METHOD_NAME

    @pytest.mark.it("Instantiates with the provided 'payload' set as an attribute")
    @pytest.mark.parametrize("payload", json_serializable_payload_params)
    def test_payload(self, payload):
        m_req = MethodRequest(request_id=FAKE_RID, name=FAKE_METHOD_NAME, payload=payload)
        assert m_req.payload == payload


@pytest.mark.describe("MethodResponse")
class TestMethodResponse:
    @pytest.mark.it("Instantiates with the provided 'request_id' set as an attribute")
    def test_request_id(self):
        m_resp = MethodResponse(request_id=FAKE_RID, status=FAKE_STATUS, payload={})
        assert m_resp.request_id == FAKE_RID

    @pytest.mark.it("Instantiates with the provided 'status' set as an attribute")
    def test_status(self):
        m_resp = MethodResponse(request_id=FAKE_RID, status=FAKE_STATUS, payload={})
        assert m_resp.status == FAKE_STATUS

    @pytest.mark.it("Instantiates with the optional provided 'payload' set as an attribute")
    @pytest.mark.parametrize("payload", json_serializable_payload_params)
    def test_payload(self, payload):
        m_resp = MethodResponse(request_id=FAKE_RID, status=FAKE_STATUS, payload=payload)
        assert m_resp.payload == payload

    @pytest.mark.it("Can be instantiated from a MethodResponse via factory API")
    @pytest.mark.parametrize("payload", json_serializable_payload_params)
    def test_factory(self, payload):
        m_req = MethodRequest(request_id=FAKE_RID, name=FAKE_METHOD_NAME, payload={})
        m_resp = MethodResponse.create_from_method_request(
            method_request=m_req, status=FAKE_STATUS, payload=payload
        )
        assert isinstance(m_resp, MethodResponse)
        assert m_resp.request_id == m_req.request_id
        assert m_resp.status == FAKE_STATUS
        assert m_resp.payload == payload
