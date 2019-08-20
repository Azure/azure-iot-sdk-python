# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import sys
import pytest
from azure.iot.device.provisioning.models.registration_result import (
    RegistrationResult,
    RegistrationState,
)
from azure.iot.device.provisioning.internal.polling_machine import PollingMachine

collect_ignore = []


# Ignore Async tests if below Python 3.5
if sys.version_info < (3, 5):
    collect_ignore.append("aio")

fake_status = "flying"
fake_sub_status = "FlyingOnHippogriff"
fake_operation_id = "quidditch_world_cup"
fake_request_id = "request_1234"
fake_device_id = "MyNimbus2000"
fake_assigned_hub = "Dumbledore'sArmy"


class FakePollingMachineSuccess(PollingMachine):
    def register(self, callback):
        callback(result=None, error=None)

    def cancel(self, callback):
        callback()


@pytest.fixture
def mock_polling_machine(mocker):
    return mocker.MagicMock(wraps=FakePollingMachineSuccess(mocker.MagicMock()))
