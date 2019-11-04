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
import threading

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
    return RegistrationResult(fake_operation_id, fake_status, fake_registration_state)


def create_error():
    return RuntimeError("Incoming Failure")


def fake_x509():
    return X509(fake_x509_cert_file_value, fake_x509_cert_key_file, fake_pass_phrase)


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

    def disable_responses(self, callback):
        callback()

    def register(self, payload, callback):
        callback(result={})


# automatically mock the transport for all tests in this file.
@pytest.fixture(autouse=True)
def mock_transport(mocker):
    mocker.patch(
        "azure.iot.device.common.pipeline.pipeline_stages_mqtt.MQTTTransport", autospec=True
    )


@pytest.mark.describe("ProvisioningDeviceClient - Init")
class TestClientCreate(object):
    xfail_notimplemented = pytest.mark.xfail(raises=NotImplementedError, reason="Unimplemented")

    @pytest.mark.it("Is created from a symmetric key")
    def test_create_from_symmetric_key(self, mocker):
        client = ProvisioningDeviceClient.create_from_symmetric_key(
            fake_provisioning_host, fake_symmetric_key, fake_registration_id, fake_id_scope
        )
        assert isinstance(client, ProvisioningDeviceClient)
        assert client._provisioning_pipeline is not None

    @pytest.mark.it("Is created from a x509 certificate key")
    def test_create_from_x509_cert(self, mocker):
        client = ProvisioningDeviceClient.create_from_x509_certificate(
            fake_provisioning_host, fake_registration_id, fake_id_scope, fake_x509()
        )
        assert isinstance(client, ProvisioningDeviceClient)
        assert client._provisioning_pipeline is not None


@pytest.mark.describe("ProvisioningDeviceClient - .register()")
class TestClientRegister(object):
    @pytest.mark.it("Implicitly enables responses from provisioning service if not already enabled")
    def test_enables_provisioning_only_if_not_already_enabled(self, mocker, provisioning_pipeline):
        # Override callback to pass successful result
        def register_complete_success_callback(payload, callback):
            callback(result=create_success_result())

        mocker.patch.object(
            provisioning_pipeline, "register", side_effect=register_complete_success_callback
        )

        provisioning_pipeline.responses_enabled.__getitem__.return_value = False

        # assert provisioning_pipeline.responses_enabled is False
        client = ProvisioningDeviceClient(provisioning_pipeline)
        client.register()

        assert provisioning_pipeline.enable_responses.call_count == 1

        provisioning_pipeline.enable_responses.reset_mock()

        provisioning_pipeline.responses_enabled.__getitem__.return_value = True
        client.register()
        assert provisioning_pipeline.enable_responses.call_count == 0

    @pytest.mark.it("Begins a 'register' pipeline operation")
    def test_register_calls_pipeline_register(self, provisioning_pipeline, mocker):
        def register_complete_success_callback(payload, callback):
            callback(result=create_success_result())

        mocker.patch.object(
            provisioning_pipeline, "register", side_effect=register_complete_success_callback
        )
        client = ProvisioningDeviceClient(provisioning_pipeline)
        client.register()
        assert provisioning_pipeline.register.call_count == 1

    @pytest.mark.it(
        "Waits for the completion of the 'register' pipeline operation before returning"
    )
    def test_waits_for_pipeline_op_completion(self, mocker):
        manual_provisioning_pipeline_with_callback = mocker.MagicMock()
        event_init_mock = mocker.patch.object(threading, "Event")
        event_mock = event_init_mock.return_value
        pipeline_function = manual_provisioning_pipeline_with_callback.register

        def check_callback_completes_event():
            # Assert exactly one Event was instantiated so we know the following asserts
            # are related to the code under test ONLY
            assert event_init_mock.call_count == 1

            # Assert waiting for Event to complete
            assert event_mock.wait.call_count == 1
            assert event_mock.set.call_count == 0

            # Manually trigger callback
            cb = pipeline_function.call_args[1]["callback"]
            cb(result=create_success_result())

            # Assert Event is now completed
            assert event_mock.set.call_count == 1

        event_mock.wait.side_effect = check_callback_completes_event

        client = ProvisioningDeviceClient(manual_provisioning_pipeline_with_callback)
        client._provisioning_payload = "payload"
        client.register()

    @pytest.mark.it("Returns the registration result that the pipeline returned")
    def test_verifies_registration_result_returned(self, mocker, provisioning_pipeline):
        result = create_success_result()

        def register_complete_success_callback(payload, callback):
            callback(result=result)

        mocker.patch.object(
            provisioning_pipeline, "register", side_effect=register_complete_success_callback
        )

        client = ProvisioningDeviceClient(provisioning_pipeline)
        result_returned = client.register()
        assert result_returned == result

    @pytest.mark.it("Returns the error that the pipeline returned")
    def test_verifies_error_returned(self, mocker, provisioning_pipeline):
        error = create_error()

        # Override callback to pass successful result
        def register_complete_failure_callback(payload, callback):
            callback(result=None, error=error)

        mocker.patch.object(
            provisioning_pipeline, "register", side_effect=register_complete_failure_callback
        )

        client = ProvisioningDeviceClient(provisioning_pipeline)
        with pytest.raises(RuntimeError):
            error_returned = client.register()
            assert error_returned == error


@pytest.mark.describe("ProvisioningDeviceClient - .cancel()")
class TestClientCancel(object):
    @pytest.mark.it("Begins a 'disconnect' pipeline operation")
    def test_client_cancel_calls_pipeline_disconnect(self, mocker, provisioning_pipeline):

        client = ProvisioningDeviceClient(provisioning_pipeline)
        client.cancel()

        assert provisioning_pipeline.disconnect.call_count == 1
        assert callable(provisioning_pipeline.disconnect.call_args[1]["callback"])


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
    def test_set_payload(self, mocker, payload_input):
        provisioning_pipeline = mocker.MagicMock()

        client = ProvisioningDeviceClient(provisioning_pipeline)
        client.provisioning_payload = payload_input
        assert client._provisioning_payload == payload_input

    @pytest.mark.it("Gets the payload from the provisioning payload property")
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
    def test_get_payload(self, mocker, payload_input):
        provisioning_pipeline = mocker.MagicMock()

        client = ProvisioningDeviceClient(provisioning_pipeline)
        client.provisioning_payload = payload_input
        assert client.provisioning_payload == payload_input
