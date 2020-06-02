# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import pytest
import logging
from azure.iot.device.provisioning.provisioning_device_client import ProvisioningDeviceClient
from azure.iot.device.provisioning.pipeline import exceptions as pipeline_exceptions
from azure.iot.device.provisioning import pipeline
import threading
from azure.iot.device import exceptions as client_exceptions
from .shared_client_tests import (
    SharedProvisioningClientInstantiationTests,
    SharedProvisioningClientCreateFromSymmetricKeyTests,
    SharedProvisioningClientCreateFromX509CertificateTests,
)


logging.basicConfig(level=logging.DEBUG)


class ProvisioningClientTestsConfig(object):
    """Defines fixtures for synchronous ProvisioningDeviceClient tests"""

    @pytest.fixture
    def client_class(self):
        return ProvisioningDeviceClient

    @pytest.fixture
    def client(self, provisioning_pipeline):
        return ProvisioningDeviceClient(provisioning_pipeline)


@pytest.mark.describe("ProvisioningDeviceClient (Sync) - Instantiation")
class TestProvisioningClientInstantiation(
    ProvisioningClientTestsConfig, SharedProvisioningClientInstantiationTests
):
    pass


@pytest.mark.describe("ProvisioningDeviceClient (Sync) - .create_from_symmetric_key()")
class TestProvisioningClientCreateFromSymmetricKey(
    ProvisioningClientTestsConfig, SharedProvisioningClientCreateFromSymmetricKeyTests
):
    pass


@pytest.mark.describe("ProvisioningDeviceClient (Sync) - .create_from_x509_certificate()")
class TestProvisioningClientCreateFromX509Certificate(
    ProvisioningClientTestsConfig, SharedProvisioningClientCreateFromX509CertificateTests
):
    pass


@pytest.mark.describe("ProvisioningDeviceClient (Sync) - .register()")
class TestClientRegister(object):
    @pytest.mark.it("Implicitly enables responses from provisioning service if not already enabled")
    def test_enables_provisioning_only_if_not_already_enabled(
        self, mocker, provisioning_pipeline, registration_result
    ):
        # Override callback to pass successful result
        def register_complete_success_callback(payload, callback):
            callback(result=registration_result)

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
    def test_register_calls_pipeline_register(
        self, provisioning_pipeline, mocker, registration_result
    ):
        def register_complete_success_callback(payload, callback):
            callback(result=registration_result)

        mocker.patch.object(
            provisioning_pipeline, "register", side_effect=register_complete_success_callback
        )
        client = ProvisioningDeviceClient(provisioning_pipeline)
        client.register()
        assert provisioning_pipeline.register.call_count == 1

    @pytest.mark.it(
        "Waits for the completion of the 'register' pipeline operation before returning"
    )
    def test_waits_for_pipeline_op_completion(self, mocker, registration_result):
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
            cb(result=registration_result)

            # Assert Event is now completed
            assert event_mock.set.call_count == 1

        event_mock.wait.side_effect = check_callback_completes_event

        client = ProvisioningDeviceClient(manual_provisioning_pipeline_with_callback)
        client._provisioning_payload = "payload"
        client.register()

    @pytest.mark.it("Returns the registration result that the pipeline returned")
    def test_verifies_registration_result_returned(
        self, mocker, provisioning_pipeline, registration_result
    ):
        result = registration_result

        def register_complete_success_callback(payload, callback):
            callback(result=result)

        mocker.patch.object(
            provisioning_pipeline, "register", side_effect=register_complete_success_callback
        )

        client = ProvisioningDeviceClient(provisioning_pipeline)
        result_returned = client.register()
        assert result_returned == result

    @pytest.mark.it(
        "Raises a client error if the `register` pipeline operation calls back with a pipeline error"
    )
    @pytest.mark.parametrize(
        "pipeline_error,client_error",
        [
            pytest.param(
                pipeline_exceptions.ConnectionDroppedError,
                client_exceptions.ConnectionDroppedError,
                id="ConnectionDroppedError->ConnectionDroppedError",
            ),
            pytest.param(
                pipeline_exceptions.ConnectionFailedError,
                client_exceptions.ConnectionFailedError,
                id="ConnectionFailedError->ConnectionFailedError",
            ),
            pytest.param(
                pipeline_exceptions.UnauthorizedError,
                client_exceptions.CredentialError,
                id="UnauthorizedError->CredentialError",
            ),
            pytest.param(
                pipeline_exceptions.ProtocolClientError,
                client_exceptions.ClientError,
                id="ProtocolClientError->ClientError",
            ),
            pytest.param(Exception, client_exceptions.ClientError, id="Exception->ClientError"),
        ],
    )
    def test_raises_error_on_pipeline_op_error(
        self, mocker, pipeline_error, client_error, provisioning_pipeline
    ):
        error = pipeline_error()

        def register_complete_failure_callback(payload, callback):
            callback(result=None, error=error)

        mocker.patch.object(
            provisioning_pipeline, "register", side_effect=register_complete_failure_callback
        )

        client = ProvisioningDeviceClient(provisioning_pipeline)
        with pytest.raises(client_error) as e_info:
            client.register()

        assert e_info.value.__cause__ is error
        assert provisioning_pipeline.register.call_count == 1


@pytest.mark.describe("ProvisioningDeviceClient (Sync) - .set_provisioning_payload()")
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
