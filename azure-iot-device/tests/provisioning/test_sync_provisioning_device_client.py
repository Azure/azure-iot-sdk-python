# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import pytest
import logging
from azure.iot.device.common.models.x509 import X509
from azure.iot.device.provisioning.provisioning_device_client import ProvisioningDeviceClient
from azure.iot.device.provisioning.models.registration_result import (
    RegistrationResult,
    RegistrationState,
)
from azure.iot.device.provisioning.pipeline import pipeline_ops_provisioning

logging.basicConfig(level=logging.DEBUG)

fake_symmetric_key = "Zm9vYmFy"
fake_registration_id = "MyPensieve"
fake_id_scope = "Enchanted0000Ceiling7898"
fake_provisioning_host = "hogwarts.com"
fake_x509_cert_file_value = "fantastic_beasts"
fake_x509_cert_key_file = "where_to_find_them"
fake_pass_phrase = "alohomora"
fake_status = "flying"
fake_sub_status = "FlyingOnHippogriff"
fake_operation_id = "quidditch_world_cup"
fake_request_id = "request_1234"
fake_device_id = "MyNimbus2000"
fake_assigned_hub = "Dumbledore'sArmy"

fake_registration_state = RegistrationState(fake_device_id, fake_assigned_hub, fake_sub_status)


def create_success_result():
    return RegistrationResult(
        fake_request_id, fake_operation_id, fake_status, fake_registration_state
    )


def create_error():
    return RuntimeError("Incoming Failure")


def fake_x509():
    return X509(fake_x509_cert_file_value, fake_x509_cert_key_file, fake_pass_phrase)


@pytest.mark.describe("ProvisioningDeviceClient - Init")
class TestClientCreate(object):
    xfail_notimplemented = pytest.mark.xfail(raises=NotImplementedError, reason="Unimplemented")

    @pytest.mark.it("Is created from a symmetric key and protocol")
    @pytest.mark.parametrize(
        "protocol",
        [
            pytest.param("mqtt", id="mqtt"),
            pytest.param(None, id="optional protocol"),
            pytest.param("amqp", id="amqp", marks=xfail_notimplemented),
            pytest.param("http", id="http", marks=xfail_notimplemented),
        ],
    )
    def test_create_from_symmetric_key(self, mocker, protocol):
        patch_set_sym_client = mocker.patch.object(
            pipeline_ops_provisioning, "SetSymmetricKeySecurityClientOperation"
        )
        patch_set_sym_client.callback = mocker.MagicMock()
        client = ProvisioningDeviceClient.create_from_symmetric_key(
            fake_provisioning_host, fake_symmetric_key, fake_registration_id, fake_id_scope
        )
        assert isinstance(client, ProvisioningDeviceClient)
        assert patch_set_sym_client.call_count == 1
        assert client._provisioning_pipeline is not None

    @pytest.mark.it("Is created from a x509 certificate key and protocol")
    @pytest.mark.parametrize(
        "protocol",
        [
            pytest.param("mqtt", id="mqtt"),
            pytest.param(None, id="optional protocol"),
            pytest.param("amqp", id="amqp", marks=xfail_notimplemented),
            pytest.param("http", id="http", marks=xfail_notimplemented),
        ],
    )
    def test_create_from_x509_cert(self, mocker, protocol):
        patch_set_x509_client = mocker.patch.object(
            pipeline_ops_provisioning, "SetX509SecurityClientOperation"
        )
        client = ProvisioningDeviceClient.create_from_x509_certificate(
            fake_provisioning_host, fake_registration_id, fake_id_scope, fake_x509()
        )
        assert isinstance(client, ProvisioningDeviceClient)
        assert patch_set_x509_client.call_count == 1
        assert client._provisioning_pipeline is not None


@pytest.mark.describe("ProvisioningDeviceClient")
class TestClientRegister(object):
    @pytest.mark.it(
        "Register calls register on polling machine with passed in callback and returns the registration result"
    )
    def test_client_register_success_calls_polling_machine_register_with_callback(
        self, mocker, mock_polling_machine
    ):
        # Override callback to pass successful result
        def register_complete_success_callback(callback):
            callback(create_success_result())

        mocker.patch.object(
            mock_polling_machine, "register", side_effect=register_complete_success_callback
        )

        mqtt_provisioning_pipeline = mocker.MagicMock()
        mock_polling_machine_init = mocker.patch(
            "azure.iot.device.provisioning.provisioning_device_client.PollingMachine"
        )
        mock_polling_machine_init.return_value = mock_polling_machine

        client = ProvisioningDeviceClient(mqtt_provisioning_pipeline)
        result = client.register()

        assert mock_polling_machine.register.call_count == 1
        assert callable(mock_polling_machine.register.call_args[1]["callback"])
        assert result is not None
        assert result.registration_state == fake_registration_state
        assert result.status == fake_status
        assert result.registration_state == fake_registration_state
        assert result.registration_state.device_id == fake_device_id
        assert result.registration_state.assigned_hub == fake_assigned_hub

    @pytest.mark.it(
        "Register calls register on polling machine with passed in callback and returns no result when an error has occured"
    )
    def test_client_register_failure_calls_polling_machine_register_with_callback(
        self, mocker, mock_polling_machine
    ):
        # Override callback to pass successful result
        def register_complete_failure_callback(callback):
            callback(result=None, error=create_error())

        mocker.patch.object(
            mock_polling_machine, "register", side_effect=register_complete_failure_callback
        )

        mqtt_provisioning_pipeline = mocker.MagicMock()
        mock_polling_machine_init = mocker.patch(
            "azure.iot.device.provisioning.provisioning_device_client.PollingMachine"
        )
        mock_polling_machine_init.return_value = mock_polling_machine

        client = ProvisioningDeviceClient(mqtt_provisioning_pipeline)
        result = client.register()

        assert mock_polling_machine.register.call_count == 1
        assert callable(mock_polling_machine.register.call_args[1]["callback"])
        assert result is None

    @pytest.mark.it("Cancel calls cancel on polling machine with passed in callback")
    def test_client_cancel_calls_polling_machine_cancel_with_callback(
        self, mocker, mock_polling_machine
    ):
        mqtt_provisioning_pipeline = mocker.MagicMock()
        mock_polling_machine_init = mocker.patch(
            "azure.iot.device.provisioning.provisioning_device_client.PollingMachine"
        )
        mock_polling_machine_init.return_value = mock_polling_machine

        client = ProvisioningDeviceClient(mqtt_provisioning_pipeline)
        client.cancel()

        assert mock_polling_machine.cancel.call_count == 1
        assert callable(mock_polling_machine.cancel.call_args[1]["callback"])
