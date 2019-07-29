# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
import logging
import datetime
from azure.iot.device.provisioning.internal.registration_query_status_result import (
    RegistrationQueryStatusResult,
)

logging.basicConfig(level=logging.INFO)

fake_request_id = "Request1234"
fake_retry_after = 6
fake_operation_id = "Operation4567"
fake_status = "Flying"
fake_device_id = "MyNimbus2000"
fake_assigned_hub = "Dumbledore'sArmy"
fake_sub_status = "FlyingOnHippogriff"
fake_created_dttm = datetime.datetime(2020, 5, 17)
fake_last_update_dttm = datetime.datetime(2020, 10, 17)
fake_etag = "HighQualityFlyingBroom"


@pytest.mark.describe("RegistrationQueryStatusResult")
class TestRegistrationQueryStatusResult(object):
    @pytest.mark.it("Instantiates correctly")
    def test_registration_status_query_result_instantiated_correctly(self):
        intermediate_result = RegistrationQueryStatusResult(
            fake_request_id, fake_retry_after, fake_operation_id, fake_status
        )
        assert intermediate_result.request_id == fake_request_id
        assert intermediate_result.retry_after == fake_retry_after
        assert intermediate_result.operation_id == fake_operation_id
        assert intermediate_result.status == fake_status

    @pytest.mark.it("Has request id that does not have setter")
    def test_rid_is_not_settable(self):
        registration_result = RegistrationQueryStatusResult(
            "RequestId123", "Operation456", "emitted", None
        )
        with pytest.raises(AttributeError, match="can't set attribute"):
            registration_result.request_id = "MyNimbus2000"
