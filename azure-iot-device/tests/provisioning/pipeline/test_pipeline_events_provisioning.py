# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import pytest
from azure.iot.device.provisioning.pipeline import pipeline_events_provisioning

fake_request_id = "req1234"
fake_response = "HelloHogwarts"
fake_status_code = 900


@pytest.mark.describe("RegistrationResponseEvent")
class TestRegistrationResponseEvent(object):
    @pytest.mark.it("Sets certain attributes on instantiation")
    def test_default_arguments(self):
        fake_key_values = {}
        fake_key_values["rid"] = [fake_request_id, " "]
        fake_key_values["retry-after"] = ["300", " "]
        fake_key_values["key1"] = ["value1", " "]

        obj = pipeline_events_provisioning.RegistrationResponseEvent(
            request_id=fake_key_values["rid"][0],
            status_code=fake_status_code,
            key_values=fake_key_values,
            response_payload=fake_response,
        )
        assert obj.rid is fake_request_id
        assert obj.status_code == fake_status_code
        assert obj.key_values == fake_key_values
        assert obj.response_payload is fake_response
        assert obj.name is obj.__class__.__name__
