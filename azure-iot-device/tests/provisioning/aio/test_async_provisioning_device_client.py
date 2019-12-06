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
from azure.iot.device.provisioning.models.registration_result import (
    RegistrationResult,
    RegistrationState,
)
from azure.iot.device.common.models.x509 import X509
from azure.iot.device.provisioning.pipeline import pipeline_ops_provisioning

logging.basicConfig(level=logging.DEBUG)
pytestmark = pytest.mark.asyncio

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


# automatically mock the transport for all tests in this file.
@pytest.fixture(autouse=True)
def mock_transport(mocker):
    mocker.patch(
        "azure.iot.device.common.pipeline.pipeline_stages_mqtt.MQTTTransport", autospec=True
    )


@pytest.mark.describe("ProvisioningDeviceClient - ..__init__()")
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
        client = ProvisioningDeviceClient.create_from_symmetric_key(
            fake_provisioning_host, fake_symmetric_key, fake_registration_id, fake_id_scope
        )
        assert isinstance(client, ProvisioningDeviceClient)
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
        client = ProvisioningDeviceClient.create_from_x509_certificate(
            fake_provisioning_host, fake_registration_id, fake_id_scope, fake_x509()
        )
        assert isinstance(client, ProvisioningDeviceClient)
        assert client._provisioning_pipeline is not None


@pytest.mark.describe("ProvisioningDeviceClient - .register()")
class TestClientRegister(object):
    @pytest.mark.it(
        "Calls register on polling machine with passed in callback and returns the registration result"
    )
    async def test_client_register_success_calls_polling_machine_register_with_callback(
        self, mocker, mock_polling_machine
    ):
        # Override callback to pass successful result
        def register_complete_success_callback(payload, callback):
            callback(result=create_success_result())

        mocker.patch.object(
            mock_polling_machine, "register", side_effect=register_complete_success_callback
        )

        mqtt_provisioning_pipeline = mocker.MagicMock()
        mock_polling_machine_init = mocker.patch(
            "azure.iot.device.provisioning.aio.async_provisioning_device_client.PollingMachine"
        )
        mock_polling_machine_init.return_value = mock_polling_machine

        client = ProvisioningDeviceClient(mqtt_provisioning_pipeline)
        result = await client.register()

        assert mock_polling_machine.register.call_count == 1
        assert mock_polling_machine.register.call_args[1]["payload"] is None
        assert callable(mock_polling_machine.register.call_args[1]["callback"])
        assert result is not None
        assert result.registration_state == fake_registration_state
        assert result.status == fake_status
        assert result.registration_state == fake_registration_state
        assert result.registration_state.device_id == fake_device_id
        assert result.registration_state.assigned_hub == fake_assigned_hub

    @pytest.mark.it(
        "Calls register on polling machine with passed in callback and raises the error when an error has occurred"
    )
    async def test_client_register_failure_calls_polling_machine_register_with_callback(
        self, mocker, mock_polling_machine
    ):
        # Override callback to pass successful result
        def register_complete_failure_callback(payload, callback):
            callback(result=None, error=create_error())

        mocker.patch.object(
            mock_polling_machine, "register", side_effect=register_complete_failure_callback
        )

        mqtt_provisioning_pipeline = mocker.MagicMock()
        mock_polling_machine_init = mocker.patch(
            "azure.iot.device.provisioning.aio.async_provisioning_device_client.PollingMachine"
        )
        mock_polling_machine_init.return_value = mock_polling_machine

        client = ProvisioningDeviceClient(mqtt_provisioning_pipeline)
        with pytest.raises(RuntimeError):
            await client.register()

        assert mock_polling_machine.register.call_count == 1
        assert mock_polling_machine.register.call_args[1]["payload"] is None
        assert callable(mock_polling_machine.register.call_args[1]["callback"])

    @pytest.mark.it(
        "Calls register on polling machine with user given payload and passed in callback and returns result"
    )
    async def test_client_register_calls_polling_machine_register_with_payload_and_callback(
        self, mocker, mock_polling_machine
    ):
        # Override callback to pass successful result
        def register_complete_success_callback(payload, callback):
            callback(result=create_success_result())

        mocker.patch.object(
            mock_polling_machine, "register", side_effect=register_complete_success_callback
        )

        mqtt_provisioning_pipeline = mocker.MagicMock()
        mock_polling_machine_init = mocker.patch(
            "azure.iot.device.provisioning.aio.async_provisioning_device_client.PollingMachine"
        )
        mock_polling_machine_init.return_value = mock_polling_machine

        user_payload = "petrificus totalus"
        client = ProvisioningDeviceClient(mqtt_provisioning_pipeline)
        client.provisioning_payload = user_payload
        result = await client.register()

        assert mock_polling_machine.register.call_count == 1
        assert mock_polling_machine.register.call_args[1]["payload"] == user_payload
        assert callable(mock_polling_machine.register.call_args[1]["callback"])
        assert result is not None
        assert result.registration_state == fake_registration_state
        assert result.status == fake_status
        assert result.registration_state == fake_registration_state
        assert result.registration_state.device_id == fake_device_id
        assert result.registration_state.assigned_hub == fake_assigned_hub


@pytest.mark.describe("ProvisioningDeviceClient - .set_provisioning_payload()")
class TestClientProvisioningPayload(object):
    @pytest.mark.it("Sets the payload on the provisioning payload attribute")
    @pytest.mark.parametrize(
        "payload_input",
        [
            pytest.param("Hello Hogwarts", id="String input"),
            pytest.param(222, id="Integer input"),
            pytest.param(object(), id="Object input"),
            pytest.param(None, id="None input"),
            pytest.param([1, "str"], id="List input"),
            pytest.param({"a": 2}, id="Dictionary input"),
        ],
    )
    async def test_set_payload(self, mocker, mock_polling_machine, payload_input):
        mqtt_provisioning_pipeline = mocker.MagicMock()
        mock_polling_machine_init = mocker.patch(
            "azure.iot.device.provisioning.provisioning_device_client.PollingMachine"
        )
        mock_polling_machine_init.return_value = mock_polling_machine

        client = ProvisioningDeviceClient(mqtt_provisioning_pipeline)
        client.provisioning_payload = payload_input
        assert client._provisioning_payload == payload_input

    @pytest.mark.it("Gets the payload from provisioning payload property")
    @pytest.mark.parametrize(
        "payload_input",
        [
            pytest.param("Hello Hogwarts", id="String input"),
            pytest.param(222, id="Integer input"),
            pytest.param(object(), id="Object input"),
            pytest.param(None, id="None input"),
            pytest.param([1, "str"], id="List input"),
            pytest.param({"a": 2}, id="Dictionary input"),
        ],
    )
    async def test_get_payload(self, mocker, mock_polling_machine, payload_input):
        mqtt_provisioning_pipeline = mocker.MagicMock()
        mock_polling_machine_init = mocker.patch(
            "azure.iot.device.provisioning.provisioning_device_client.PollingMachine"
        )
        mock_polling_machine_init.return_value = mock_polling_machine

        client = ProvisioningDeviceClient(mqtt_provisioning_pipeline)
        client.provisioning_payload = payload_input
        assert client.provisioning_payload == payload_input
