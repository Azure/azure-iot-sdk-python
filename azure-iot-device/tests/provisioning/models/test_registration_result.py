# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
import datetime
from azure.iot.device.provisioning.models.registration_result import (
    RegistrationResult,
    RegistrationState,
)

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
        fake_registration_state = RegistrationState(
            fake_device_id,
            fake_assigned_hub,
            fake_sub_status,
            fake_created_dttm,
            fake_last_update_dttm,
            fake_etag,
        )

        registration_result = RegistrationResult(
            fake_request_id, fake_operation_id, fake_status, fake_registration_state
        )
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

    @pytest.mark.it("Has attributes that do not have setter")
    def test_some_properties_of_result_are_not_settable(self):
        registration_result = RegistrationResult("RequestId123", "Operation456", "emitted", None)
        with pytest.raises(AttributeError, match="can't set attribute"):
            registration_result.request_id = "MyNimbus2000"
            registration_result.operation_id = "WhompingWillow"
            registration_result.status = "Flying"
            registration_result.registration_state = "FakeRegistrationState"

    @pytest.mark.it("Has `RegistrationState` with properties that do not have setter")
    def test_some_properties_of_state_are_not_settable(self):
        registration_state = RegistrationState(
            fake_device_id,
            fake_assigned_hub,
            fake_sub_status,
            fake_created_dttm,
            fake_last_update_dttm,
            fake_etag,
        )
        with pytest.raises(AttributeError, match="can't set attribute"):
            registration_state.device_id = fake_device_id
            registration_state.assigned_hub = fake_assigned_hub
            registration_state.sub_status = fake_sub_status
            registration_state.created_date_time = fake_created_dttm
