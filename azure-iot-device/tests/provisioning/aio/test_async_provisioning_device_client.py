# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
from azure.iot.device.provisioning.internal.polling_machine import PollingMachine
from azure.iot.device.provisioning.aio.async_sk_provisioning_device_client import (
    SymmetricKeyProvisioningDeviceClient,
)
from azure.iot.device.provisioning.aio.async_x509_provisioning_device_client import (
    X509ProvisioningDeviceClient,
)
from azure.iot.device.provisioning.models import RegistrationResult
import pytest
from azure.iot.device.provisioning.security.sk_security_client import SymmetricKeySecurityClient
from azure.iot.device.provisioning.security.x509_security_client import X509SecurityClient
from azure.iot.device.provisioning.pipeline.provisioning_pipeline import ProvisioningPipeline

pytestmark = pytest.mark.asyncio

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
fake_provisioning_host = "hogwarts.com"
fake_x509_cert_value = "fantastic_beasts"
fake_x509_cert_key = "where_to_find_them"
fake_pass_phrase = "alohomora"


def create_success_result():
    result = RegistrationResult("R1234", "Oper1234", "assigned")
    return result


def create_error():
    return RuntimeError("Incoming Failure")


def symmetric_key_security_client():
    return SymmetricKeySecurityClient(
        provisioning_host=fake_provisioning_host,
        registration_id=fake_registration_id,
        id_scope=fake_id_scope,
        symmetric_key=fake_symmetric_key,
    )


def x509_security_client():
    mock_x509 = FakeX509(fake_x509_cert_value, fake_x509_cert_key, fake_pass_phrase)
    return X509SecurityClient(
        provisioning_host=fake_provisioning_host,
        registration_id=fake_registration_id,
        id_scope=fake_id_scope,
        x509=mock_x509,
    )


class FakeX509(object):
    def __init__(self, cert, key, pass_phrase):
        self.certificate = cert
        self.key = key
        self.pass_phrase = pass_phrase


different_security_clients = [
    {
        "name": "symmetric key security",
        "class": SymmetricKeySecurityClient,
        "client_class": SymmetricKeyProvisioningDeviceClient,
        "security_client": symmetric_key_security_client(),
    },
    {
        "name": "x509 security",
        "class": X509SecurityClient,
        "client_class": X509ProvisioningDeviceClient,
        "security_client": x509_security_client(),
    },
]


@pytest.mark.parametrize(
    "params_security_clients",
    different_security_clients,
    ids=[x["name"] for x in different_security_clients],
)
@pytest.mark.describe("ProvisioningDeviceClient")
class TestClientCreate:
    xfail_notimplemented = pytest.mark.xfail(raises=NotImplementedError, reason="Unimplemented")

    @pytest.fixture
    def security_client(self, params_security_clients):
        return params_security_clients["security_client"]

    @pytest.mark.it("is created from a security client and protocol")
    @pytest.mark.parametrize(
        "protocol,expected_pipeline",
        [
            pytest.param("mqtt", ProvisioningPipeline, id="mqtt"),
            pytest.param("amqp", None, id="amqp", marks=xfail_notimplemented),
            pytest.param("http", None, id="http", marks=xfail_notimplemented),
        ],
    )
    async def test_create_from_security_client_instantiates_client(
        self, security_client, protocol, expected_pipeline, params_security_clients
    ):
        client = params_security_clients["client_class"].create_from_security_client(
            security_client, protocol
        )
        assert isinstance(client, params_security_clients["client_class"])

    @pytest.mark.it("raises error on creation if it is not symmetric security client")
    async def test_raises_when_client_created_from_incorrect_security_client(
        self, params_security_clients
    ):
        with pytest.raises(
            ValueError,
            match="A symmetric key security client or a X509 security client must be provided for MQTT",
        ):
            incorrect_security_client = IncorrectSecurityClient()
            params_security_clients["client_class"].create_from_security_client(
                incorrect_security_client, "mqtt"
            )


class IncorrectSecurityClient(object):
    def __init__(self):
        self.registration_id = fake_registration_id
        self.id_scope = fake_id_scope


different_clients = [
    {
        "client_class": SymmetricKeyProvisioningDeviceClient,
        "patch_string": "azure.iot.device.provisioning.aio.async_sk_provisioning_device_client.PollingMachine",
    },
    {
        "client_class": X509ProvisioningDeviceClient,
        "patch_string": "azure.iot.device.provisioning.aio.async_x509_provisioning_device_client.PollingMachine",
    },
]


class FakePollingMachineSuccess(PollingMachine):
    def register(self, callback):
        callback(create_success_result(), error=None)

    def cancel(self, callback):
        callback()

    def disconnect(self, callback):
        callback()


@pytest.mark.parametrize(
    "params_clients", different_clients, ids=[x["client_class"].__name__ for x in different_clients]
)
class TestClientCallsPollingMachine:
    @pytest.fixture
    def mock_polling_machine_success(self, mocker):
        return mocker.MagicMock(wraps=FakePollingMachineSuccess(mocker.MagicMock()))

    @pytest.mark.it("register calls register on polling machine with passed in callback")
    async def test_client_register_success_calls_polling_machine_register_with_callback(
        self, mocker, mock_polling_machine_success, params_clients
    ):
        state_based_mqtt = mocker.MagicMock()
        mock_polling_machine_init = mocker.patch(params_clients["patch_string"])
        # TODO After deciding on one client, no need for params and patch will become
        # mock_polling_machine_init = mocker.patch(
        #     "azure.iot.device.provisioning.provisioning_device_client.PollingMachine"
        # )
        mock_polling_machine_init.return_value = mock_polling_machine_success

        client = params_clients["client_class"](state_based_mqtt)
        await client.register()
        assert mock_polling_machine_success.register.call_count == 1

    @pytest.mark.it("cancel calls cancel on polling machine with passed in callback")
    async def test_client_cancel_calls_polling_machine_cancel_with_callback(
        self, mocker, mock_polling_machine_success, params_clients
    ):
        state_based_mqtt = mocker.MagicMock()
        mock_polling_machine_init = mocker.patch(params_clients["patch_string"])
        # TODO After deciding on one client, no need for params and patch will become
        # mock_polling_machine_init = mocker.patch(
        #     "azure.iot.device.provisioning.provisioning_device_client.PollingMachine"
        # )
        mock_polling_machine_init.return_value = mock_polling_machine_success

        client = params_clients["client_class"](state_based_mqtt)
        await client.cancel()
        assert mock_polling_machine_success.cancel.call_count == 1
        assert "callback" in mock_polling_machine_success.cancel.call_args[1]
