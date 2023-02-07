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

    # NOTE: This test tests all system properties, even though they shouldn't all be present simultaneously
    @pytest.mark.it("Can return the system properties set on the Message as a dictionary via API")
    def test_system_properties_dict_all(self):
        msg = Message("some message")
        msg.message_id = "message id"
        msg.content_encoding = "application/json"
        msg.content_type = "utf-16"
        msg.output_name = "output name"
        msg._iothub_interface_id = "interface id"
        msg.input_name = "input name"
        msg.ack = "value"
        msg.expiry_time_utc = "time"
        msg.user_id = "user id"
        msg.correlation_id = "correlation id"
        sys_prop = msg.get_system_properties_dict()

        assert sys_prop["$.mid"] == msg.message_id
        assert sys_prop["$.ce"] == msg.content_encoding
        assert sys_prop["$.ct"] == msg.content_type
        assert sys_prop["$.on"] == msg.output_name
        assert sys_prop["$.ifid"] == msg._iothub_interface_id
        assert sys_prop["$.to"] == msg.input_name
        assert sys_prop["iothub-ack"] == msg.ack
        assert sys_prop["$.exp"] == msg.expiry_time_utc
        assert sys_prop["$.uid"] == msg.user_id
        assert sys_prop["$.cid"] == msg.correlation_id

    @pytest.mark.it(
        "Only contains the system properties present on the Message in the system properties dictionary"
    )
    def test_system_properties_dict_partial(self):
        msg = Message("some message")
        msg.message_id = "message id"
        sys_prop = msg.get_system_properties_dict()
        assert len(sys_prop) == 1
        assert sys_prop["$.mid"] == msg.message_id

    # NOTE: This test tests all system properties, even though they shouldn't all be present simultaneously
    @pytest.mark.it("Can be instantiated from a properties dictionary")
    @pytest.mark.parametrize(
        "custom_properties",
        [
            pytest.param({}, id="System Properties Only"),
            pytest.param(
                {"cust1": "v1", "cust2": "v2"}, id="System Properties and Custom Properties"
            ),
        ],
    )
    def test_create_from_dict(self, custom_properties):
        system_properties = {
            "$.mid": "message id",
            "$.ce": "application/json",
            "$.ct": "utf-16",
            "$.on": "output name",
            "$.ifid": "interface id",
            "$.to": "input name",
            "iothub-ack": "value",
            "$.exp": "time",
            "$.uid": "user id",
            "$.cid": "correlation id",
        }
        properties = dict(system_properties)
        properties.update(custom_properties)
        message = Message.create_from_properties_dict("some payload", properties)

        assert message.message_id == system_properties["$.mid"]
        assert message.content_encoding == system_properties["$.ce"]
        assert message.content_type == system_properties["$.ct"]
        assert message.output_name == system_properties["$.on"]
        assert message._iothub_interface_id == system_properties["$.ifid"]
        assert message.input_name == system_properties["$.to"]
        assert message.ack == system_properties["iothub-ack"]
        assert message.expiry_time_utc == system_properties["$.exp"]
        assert message.user_id == system_properties["$.uid"]
        assert message.correlation_id == system_properties["$.cid"]

        for key in custom_properties:
            assert message.custom_properties[key] == custom_properties[key]


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
