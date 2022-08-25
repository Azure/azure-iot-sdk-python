# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module contains test fixtures shared between sync/async client tests"""
import pytest
from azure.iot.device.provisioning.models.registration_result import (
    RegistrationResult,
    RegistrationState,
)
from azure.iot.device.common.models.x509 import X509

"""Constants"""
fake_x509_cert_file_value = "fake_cert_file"
fake_x509_cert_key_file = "fake_cert_key_file"
fake_pass_phrase = "fake_pass_phrase"
fake_status = "200"
fake_sub_status = "OK"
fake_operation_id = "fake_operation_id"
fake_device_id = "MyDevice"
fake_assigned_hub = "MyIoTHub"


"""Pipeline fixtures"""


@pytest.fixture
def mock_pipeline_init(mocker):
    return mocker.patch("azure.iot.device.provisioning.pipeline.MQTTPipeline")


@pytest.fixture(autouse=True)
def provisioning_pipeline(mocker):
    return mocker.MagicMock(wraps=FakeProvisioningPipeline())


class FakeProvisioningPipeline:
    def __init__(self):
        self.responses_enabled = {}

    def shutdown(self, callback):
        callback()

    def connect(self, callback):
        callback()

    def disconnect(self, callback):
        callback()

    def enable_responses(self, callback):
        callback()

    def register(self, payload, callback):
        callback(result={})


"""Parameter fixtures"""


@pytest.fixture
def registration_result():
    registration_state = RegistrationState(fake_device_id, fake_assigned_hub, fake_sub_status)
    return RegistrationResult(fake_operation_id, fake_status, registration_state)


@pytest.fixture
def x509():
    return X509(fake_x509_cert_file_value, fake_x509_cert_key_file, fake_pass_phrase)
