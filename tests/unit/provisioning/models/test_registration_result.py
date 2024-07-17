# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
import logging
import datetime
from azure.iot.device.provisioning.models.registration_result import (
    RegistrationResult,
    RegistrationState,
)
import json

logging.basicConfig(level=logging.DEBUG)

fake_request_id = "Request1234"
fake_operation_id = "Operation4567"
fake_status = "FakeStatus"
fake_device_id = "MyDevice"
fake_assigned_hub = "MyIoTHub"
fake_sub_status = "FakeSubStatus"
fake_created_dttm = datetime.datetime(2020, 5, 17)
fake_last_update_dttm = datetime.datetime(2020, 10, 17)
fake_etag = "SomeEtag"
fake_payload = "this is a fake payload"


@pytest.mark.describe("RegistrationResult")
class TestRegistrationResult(object):
    @pytest.mark.it("Instantiates correctly")
    def test_registration_result_instantiated_correctly(self):
        fake_registration_state = create_registration_state()
        registration_result = create_registration_result(fake_registration_state)

        assert registration_result.operation_id == fake_operation_id
        assert registration_result.status == fake_status
        assert registration_result.registration_state == fake_registration_state

        assert registration_result.registration_state.device_id == fake_device_id
        assert registration_result.registration_state.assigned_hub == fake_assigned_hub
        assert registration_result.registration_state.sub_status == fake_sub_status
        assert registration_result.registration_state.created_date_time == fake_created_dttm
        assert registration_result.registration_state.last_update_date_time == fake_last_update_dttm
        assert registration_result.registration_state.etag == fake_etag

    @pytest.mark.it("Has a to string representation composed of registration state and status")
    def test_registration_result_to_string(self):
        fake_registration_state = create_registration_state()
        registration_result = create_registration_result(fake_registration_state)

        string_repr = "\n".join([str(fake_registration_state), fake_status])
        assert str(registration_result) == string_repr

    @pytest.mark.parametrize(
        "input_setter_code",
        [
            pytest.param('registration_result.operation_id = "NewOperationId"', id="Operation Id"),
            pytest.param('registration_result.status = "NewStatus"', id="Status"),
            pytest.param(
                'registration_result.registration_state = "NewRegistrationState"',
                id="Registration State",
            ),
        ],
    )
    @pytest.mark.it("Has attributes that do not have setter")
    def test_some_properties_of_result_are_not_settable(self, input_setter_code):
        registration_result = create_registration_result()  # noqa: F841
        with pytest.raises(AttributeError):
            exec(input_setter_code)

    @pytest.mark.parametrize(
        "input_setter_code",
        [
            pytest.param('registration_state.device_id = "NewDeviceId"', id="Device Id"),
            pytest.param('registration_state.assigned_hub = "NewHub"', id="Assigned Hub"),
            pytest.param('registration_state.sub_status = "NewSubStatus"', id="Substatus"),
            pytest.param('registration_state.etag = "NewEtag"', id="Etag"),
            pytest.param(
                "registration_state.created_date_time = datetime.datetime(3000, 10, 17)",
                id="Create Date Time",
            ),
            pytest.param(
                "registration_state.last_update_date_time = datetime.datetime(3000, 10, 17)",
                id="Last Update Date Time",
            ),
        ],
    )
    @pytest.mark.it("Has `RegistrationState` with properties that do not have setter")
    def test_some_properties_of_state_are_not_settable(self, input_setter_code):
        registration_state = create_registration_state()  # noqa: F841

        with pytest.raises(AttributeError):
            exec(input_setter_code)

    @pytest.mark.it(
        "Has a to string representation composed of device id, assigned hub and sub status"
    )
    def test_registration_state_to_string_without_payload(self):
        registration_state = create_registration_state()
        # Serializes the __dict__ of every object instead of the object itself.
        # Helpful for all sorts of complex objects.
        json_payload = json.dumps(None, default=lambda o: o.__dict__, sort_keys=True)

        string_repr = "\n".join([fake_device_id, fake_assigned_hub, fake_sub_status, json_payload])
        assert str(registration_state) == string_repr

    @pytest.mark.it(
        "Has a to string representation composed of device id, assigned hub, sub status and response payload"
    )
    def test_registration_state_to_string_with_payload(self):
        registration_state = create_registration_state(fake_payload)
        json_payload = json.dumps(fake_payload, default=lambda o: o.__dict__, sort_keys=True)

        string_repr = "\n".join([fake_device_id, fake_assigned_hub, fake_sub_status, json_payload])
        assert str(registration_state) == string_repr


def create_registration_state(payload=None):
    return RegistrationState(
        fake_device_id,
        fake_assigned_hub,
        fake_sub_status,
        fake_created_dttm,
        fake_last_update_dttm,
        fake_etag,
        payload,
    )


def create_registration_result(registration_state=None):
    return RegistrationResult(fake_operation_id, fake_status, registration_state)
