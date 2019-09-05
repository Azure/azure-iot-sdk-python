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

logging.basicConfig(level=logging.DEBUG)

fake_request_id = "Request1234"
fake_operation_id = "Operation4567"
fake_status = "Flying"
fake_device_id = "MyNimbus2000"
fake_assigned_hub = "Dumbledore'sArmy"
fake_sub_status = "FlyingOnHippogriff"
fake_created_dttm = datetime.datetime(2020, 5, 17)
fake_last_update_dttm = datetime.datetime(2020, 10, 17)
fake_etag = "HighQualityFlyingBroom"


@pytest.mark.describe("RegistrationResult")
class TestRegistrationResult(object):
    @pytest.mark.it("Instantiates correctly")
    def test_registration_result_instantiated_correctly(self):
        fake_registration_state = create_registraion_state()
        registration_result = create_registration_result(fake_registration_state)

        assert registration_result.request_id == fake_request_id
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
        fake_registration_state = create_registraion_state()
        registration_result = create_registration_result(fake_registration_state)

        string_repr = "\n".join([str(fake_registration_state), fake_status])
        assert str(registration_result) == string_repr

    @pytest.mark.parametrize(
        "input_setter_code",
        [
            pytest.param('registration_result.request_id = "RequestId123"', id="Request Id"),
            pytest.param('registration_result.operation_id = "WhompingWillow"', id="Operation Id"),
            pytest.param('registration_result.status = "Apparating"', id="Status"),
            pytest.param(
                'registration_result.registration_state = "FakeRegistrationState"',
                id="Registration State",
            ),
        ],
    )
    @pytest.mark.it("Has attributes that do not have setter")
    def test_some_properties_of_result_are_not_settable(self, input_setter_code):
        registration_result = create_registration_result()  # noqa: F841
        with pytest.raises(AttributeError, match="can't set attribute"):
            exec(input_setter_code)

    @pytest.mark.parametrize(
        "input_setter_code",
        [
            pytest.param('registration_state.device_id = "Thunderbolt"', id="Device Id"),
            pytest.param('registration_state.assigned_hub = "MinistryOfMagic"', id="Assigned Hub"),
            pytest.param('registration_state.sub_status = "Apparating"', id="Substatus"),
            pytest.param('registration_state.etag = "QuidditchWorldCupWinning"', id="Etag"),
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
        registration_state = create_registraion_state()  # noqa: F841

        with pytest.raises(AttributeError, match="can't set attribute"):
            exec(input_setter_code)

    @pytest.mark.it(
        "Has a to string representation composed of device id, assigned hub and sub status"
    )
    def test_registration_state_to_string(self):
        registration_state = create_registraion_state()

        string_repr = "\n".join([fake_device_id, fake_assigned_hub, fake_sub_status])
        assert str(registration_state) == string_repr


def create_registraion_state():
    return RegistrationState(
        fake_device_id,
        fake_assigned_hub,
        fake_sub_status,
        fake_created_dttm,
        fake_last_update_dttm,
        fake_etag,
    )


def create_registration_result(registration_state=None):
    return RegistrationResult(fake_request_id, fake_operation_id, fake_status, registration_state)
