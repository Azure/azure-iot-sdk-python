# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
import types
from azure.iot.device.provisioning.internal.polling_machine import PollingMachine
from azure.iot.device.provisioning.sk_provisioning_device_client import (
    SymmetricKeyProvisioningDeviceClient,
)
from azure.iot.device.provisioning.models import RegistrationResult
from azure.iot.device.provisioning.transport.state_based_mqtt_provider import StateBasedMQTTProvider

fake_request_id = "Request1234"
fake_retry_after = "3"
fake_operation_id = "Operation4567"
fake_status = "Flying"
fake_device_id = "MyNimbus2000"
fake_assigned_hub = "Dumbledore'sArmy"
fake_sub_status = "FlyingOnHippogriff"
fake_etag = "HighQualityFlyingBroom"
fake_symmetric_key = "Zm9vYmFy"
fake_registration_id = "MyPensieve"
fake_id_scope = "Enchanted0000Ceiling7898"
fake_success_response_topic = "$dps/registrations/res/200/?"
fake_failure_response_topic = "$dps/registrations/res/400/?"
fake_greater_429_response_topic = "$dps/registrations/res/430/?"
fake_assigning_status = "assigning"
fake_assigned_status = "assigned"


@pytest.fixture
def state_based_mqtt(mocker):
    return mocker.MagicMock(spec=StateBasedMQTTProvider)


@pytest.fixture
def client(transport):
    return SymmetricKeyProvisioningDeviceClient(transport)


def create_success_result():
    result = RegistrationResult("R1234", "Oper1234", "assigned")
    return result


def create_error():
    return RuntimeError("Incoming Failure")


class FakePollingMachineSuccess(PollingMachine):
    def register(self, callback):
        callback(create_success_result(), error=None)

    def cancel(self, callback):
        callback()

    def disconnect(self, callback):
        callback()


@pytest.fixture
def mock_polling_machine_success(mocker):
    return mocker.MagicMock(wraps=FakePollingMachineSuccess(mocker.MagicMock()))


@pytest.mark.it("register calls register on polling machine with passed in callback")
def test_client_register_success_calls_polling_machine_register_with_callback(
    mocker, state_based_mqtt, mock_polling_machine_success
):
    mock_polling_machine_init = mocker.patch(
        "azure.iot.device.provisioning.sk_provisioning_device_client.PollingMachine"
    )
    mock_polling_machine_init.return_value = mock_polling_machine_success

    client = SymmetricKeyProvisioningDeviceClient(state_based_mqtt)
    client.register()
    assert mock_polling_machine_success.register.call_count == 1


@pytest.mark.it("cancel calls cancel on polling machine with passed in callback")
def test_client_cancel_calls_polling_machine_cancel_with_callback(
    mocker, state_based_mqtt, mock_polling_machine_success
):
    mock_polling_machine_init = mocker.patch(
        "azure.iot.device.provisioning.sk_provisioning_device_client.PollingMachine"
    )
    mock_polling_machine_init.return_value = mock_polling_machine_success

    client = SymmetricKeyProvisioningDeviceClient(state_based_mqtt)
    client.cancel()
    assert mock_polling_machine_success.cancel.call_count == 1
    assert "callback" in mock_polling_machine_success.cancel.call_args[1]
    assert isinstance(
        mock_polling_machine_success.cancel.call_args[1]["callback"], types.FunctionType
    )
