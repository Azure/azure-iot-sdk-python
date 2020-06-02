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
fake_x509_cert_file_value = "fantastic_beasts"
fake_x509_cert_key_file = "where_to_find_them"
fake_pass_phrase = "alohomora"
fake_status = "flying"
fake_sub_status = "FlyingOnHippogriff"
fake_operation_id = "quidditch_world_cup"
fake_device_id = "MyNimbus2000"
fake_assigned_hub = "Dumbledore'sArmy"


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
