# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import pytest
import logging
from azure.iot.device.provisioning.internal.polling_machine import PollingMachine
from azure.iot.device.provisioning.aio.async_provisioning_device_client import (
    ProvisioningDeviceClient,
)
from azure.iot.device.provisioning.models import RegistrationResult
from azure.iot.device.common.models.x509 import X509
from azure.iot.device.provisioning.pipeline import pipeline_ops_provisioning

logging.basicConfig(level=logging.INFO)
pytestmark = pytest.mark.asyncio

fake_symmetric_key = "Zm9vYmFy"
fake_registration_id = "MyPensieve"
fake_id_scope = "Enchanted0000Ceiling7898"
fake_provisioning_host = "hogwarts.com"
fake_x509_cert_file_value = "fantastic_beasts"
fake_x509_cert_key_file = "where_to_find_them"
fake_pass_phrase = "alohomora"


def create_success_result():
    result = RegistrationResult("R1234", "Oper1234", "assigned")
    return result


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
    async def test_create_from_symmetric_key(self, mocker, protocol):
        patch_set_sym_client = mocker.patch.object(
            pipeline_ops_provisioning, "SetSymmetricKeySecurityClientOperation"
        )
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
    async def test_create_from_x509_cert(self, mocker, protocol):
        patch_set_x509_client = mocker.patch.object(
            pipeline_ops_provisioning, "SetX509SecurityClientOperation"
        )
        client = ProvisioningDeviceClient.create_from_x509_certificate(
            fake_provisioning_host, fake_registration_id, fake_id_scope, fake_x509()
        )
        assert isinstance(client, ProvisioningDeviceClient)
        assert patch_set_x509_client.call_count == 1
        assert client._provisioning_pipeline is not None


class FakePollingMachineSuccess(PollingMachine):
    def register(self, callback):
        callback(create_success_result(), error=None)

    def cancel(self, callback):
        callback()

    def disconnect(self, callback):
        callback()


@pytest.mark.describe("ProvisioningDeviceClient")
class TestClientCallsPollingMachine(object):
    @pytest.fixture
    def mock_polling_machine_success(self, mocker):
        return mocker.MagicMock(wraps=FakePollingMachineSuccess(mocker.MagicMock()))

    @pytest.mark.it("Register calls register on polling machine with passed in callback")
    async def test_client_register_success_calls_polling_machine_register_with_callback(
        self, mocker, mock_polling_machine_success
    ):
        mqtt_provisioning_pipeline = mocker.MagicMock()
        mock_polling_machine_init = mocker.patch(
            "azure.iot.device.provisioning.aio.async_provisioning_device_client.PollingMachine"
        )
        mock_polling_machine_init.return_value = mock_polling_machine_success

        client = ProvisioningDeviceClient(mqtt_provisioning_pipeline)
        await client.register()

        assert mock_polling_machine_success.register.call_count == 1
        assert callable(mock_polling_machine_success.register.call_args[1]["callback"])

    @pytest.mark.it("Cancel calls cancel on polling machine with passed in callback")
    async def test_client_cancel_calls_polling_machine_cancel_with_callback(
        self, mocker, mock_polling_machine_success
    ):
        mqtt_provisioning_pipeline = mocker.MagicMock()
        mock_polling_machine_init = mocker.patch(
            "azure.iot.device.provisioning.aio.async_provisioning_device_client.PollingMachine"
        )
        mock_polling_machine_init.return_value = mock_polling_machine_success

        client = ProvisioningDeviceClient(mqtt_provisioning_pipeline)
        await client.cancel()

        assert mock_polling_machine_success.cancel.call_count == 1
        assert callable(mock_polling_machine_success.cancel.call_args[1]["callback"])
