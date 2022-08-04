# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
import logging
from azure.iot.device.iothub.models import MethodRequest, MethodResponse

logging.basicConfig(level=logging.DEBUG)

dummy_rid = 1
dummy_name = "name"
dummy_payload = {"MethodPayload": "somepayload"}
dummy_status = 200


@pytest.mark.describe("MethodRequest - Instantiation")
class TestMethodRequest(object):
    @pytest.mark.it("Instantiates with a read-only 'request_id' attribute")
    def test_request_id_property_is_read_only(self):
        m_req = MethodRequest(request_id=dummy_rid, name=dummy_name, payload=dummy_payload)
        new_rid = 2

        with pytest.raises(AttributeError):
            m_req.request_id = new_rid
        assert m_req.request_id != new_rid
        assert m_req.request_id == dummy_rid

    @pytest.mark.it("Instantiates with a read-only 'name' attribute")
    def test_name_property_is_read_only(self):
        m_req = MethodRequest(request_id=dummy_rid, name=dummy_name, payload=dummy_payload)
        new_name = "new_name"

        with pytest.raises(AttributeError):
            m_req.name = new_name
        assert m_req.name != new_name
        assert m_req.name == dummy_name

    @pytest.mark.it("Instantiates with a read-only 'payload' attribute")
    def test_payload_property_is_read_only(self):
        m_req = MethodRequest(request_id=dummy_rid, name=dummy_name, payload=dummy_payload)
        new_payload = {"NewPayload": "somenewpayload"}

        with pytest.raises(AttributeError):
            m_req.payload = new_payload
        assert m_req.payload != new_payload
        assert m_req.payload == dummy_payload


@pytest.mark.describe("MethodResponse - Instantiation")
class TestMethodResponseInstantiation(object):
    @pytest.mark.it("Instantiates with an editable 'request_id' attribute")
    def test_instantiates_with_request_id(self):
        response = MethodResponse(request_id=dummy_rid, status=dummy_status, payload=dummy_payload)
        assert response.request_id == dummy_rid

        new_rid = "2"
        assert response.request_id != new_rid
        response.request_id = new_rid
        assert response.request_id == new_rid

    @pytest.mark.it("Instantiates with an editable 'status' attribute")
    def test_instantiates_with_status(self):
        response = MethodResponse(request_id=dummy_rid, status=dummy_status, payload=dummy_payload)
        assert response.status == dummy_status

        new_status = 400
        assert response.status != new_status
        response.status = new_status
        assert response.status == new_status

    @pytest.mark.it("Instantiates with an editable 'payload' attribute")
    def test_instantiates_with_payload(self):
        response = MethodResponse(request_id=dummy_rid, status=dummy_status, payload=dummy_payload)
        assert response.payload == dummy_payload

        new_payload = {"NewPayload": "yes_this_is_new"}
        assert response.payload != new_payload
        response.payload = new_payload
        assert response.payload == new_payload

    @pytest.mark.it("Instantiates with a default 'payload' of 'None' if not provided")
    def test_instantiates_without_payload(self):
        response = MethodResponse(request_id=dummy_rid, status=dummy_status)
        assert response.request_id == dummy_rid
        assert response.status == dummy_status
        assert response.payload is None


@pytest.mark.describe("MethodResponse - .create_from_method_request()")
class TestMethodResponseCreateFromMethodRequest(object):
    @pytest.mark.it("Instantiates using a MethodRequest to provide the 'request_id'")
    def test_instantiates_from_method_request(self):
        request = MethodRequest(request_id=dummy_rid, name=dummy_name, payload=dummy_payload)
        status = 200
        payload = {"ResponsePayload": "SomeResponse"}
        response = MethodResponse.create_from_method_request(
            method_request=request, status=status, payload=payload
        )

        assert isinstance(response, MethodResponse)
        assert response.request_id == request.request_id
        assert response.status == status
        assert response.payload == payload

    @pytest.mark.it("Instantiates with a default 'payload' of 'None' if not provided")
    def test_instantiates_without_payload(self):
        request = MethodRequest(request_id=dummy_rid, name=dummy_name, payload=dummy_payload)
        status = 200
        response = MethodResponse.create_from_method_request(request, status)

        assert isinstance(response, MethodResponse)
        assert response.request_id == request.request_id
        assert response.status == status
        assert response.payload is None
