# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import pytest
import logging
from azure.iot.device.provisioning.provisioning_device_client import ProvisioningDeviceClient
from azure.iot.device.provisioning.pipeline import exceptions as pipeline_exceptions
from azure.iot.device import exceptions as client_exceptions
from .shared_client_tests import (
    SharedProvisioningClientInstantiationTests,
    SharedProvisioningClientCreateFromSymmetricKeyTests,
    SharedProvisioningClientCreateFromX509CertificateTests,
)


logging.basicConfig(level=logging.DEBUG)


# NOTE: Not all of these errors are possible in practice on all pipeline operations.
# However, we will test all of them on all pipeline operations for safety + maintainability
POSSIBLE_CLIENT_ERRORS = [
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
    pytest.param(
        pipeline_exceptions.TlsExchangeAuthError,
        client_exceptions.ClientError,
        id="TlsExchangeAuthError->ClientError",
    ),
    pytest.param(
        pipeline_exceptions.ProtocolProxyError,
        client_exceptions.ClientError,
        id="ProtocolProxyError->ClientError",
    ),
    pytest.param(
        pipeline_exceptions.OperationTimeout,
        client_exceptions.OperationTimeout,
        id="OperationTimeout->OperationTimeout",
    ),
    pytest.param(
        pipeline_exceptions.OperationCancelled,
        client_exceptions.OperationCancelled,
        id="OperationCancelled->OperationCancelled",
    ),
    pytest.param(
        pipeline_exceptions.PipelineNotRunning,
        client_exceptions.ClientError,
        id="PipelineNotRunning->ClientError",
    ),
    pytest.param(Exception, client_exceptions.ClientError, id="Exception->ClientError"),
]


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


@pytest.mark.describe("ProvisioningDeviceClient (Sync) - .shutdown()")
class TestClientShutdown(object):
    @pytest.mark.it("Begins a 'shutdown' pipeline operation")
    def test_calls_pipeline_shutdown(self, provisioning_pipeline):
        client = ProvisioningDeviceClient(provisioning_pipeline)
        client.shutdown()
        assert provisioning_pipeline.shutdown.call_count == 1

    @pytest.mark.it(
        "Waits for the completion of the 'shutdown' pipeline operation before returning"
    )
    def test_waits_for_pipeline_op_completion(self, mocker, provisioning_pipeline):
        cb_mock_shutdown = mocker.patch(
            "azure.iot.device.provisioning.provisioning_device_client.EventedCallback"
        ).return_value

        client = ProvisioningDeviceClient(provisioning_pipeline)
        client.shutdown()
        assert provisioning_pipeline.shutdown.call_count == 1
        assert provisioning_pipeline.shutdown.call_args == mocker.call(callback=cb_mock_shutdown)
        assert cb_mock_shutdown.wait_for_completion.call_count == 1

    @pytest.mark.it(
        "Raises a client error if the `shutdown` pipeline operation calls back with a pipeline error"
    )
    @pytest.mark.parametrize("pipeline_error,client_error", POSSIBLE_CLIENT_ERRORS)
    def test_raises_error_on_pipeline_op_error(
        self, mocker, provisioning_pipeline, pipeline_error, client_error
    ):
        error = pipeline_error()

        def shutdown_complete_failure_callback(callback):
            callback(error=error)

        mocker.patch.object(
            provisioning_pipeline, "shutdown", side_effect=shutdown_complete_failure_callback
        )

        client = ProvisioningDeviceClient(provisioning_pipeline)
        with pytest.raises(client_error) as e_info:
            client.shutdown()

        assert e_info.value.__cause__ is error
        assert provisioning_pipeline.shutdown.call_count == 1


@pytest.mark.describe("ProvisioningDeviceClient (Sync) - .register()")
class TestClientRegister(object):
    @pytest.fixture
    def client(self, provisioning_pipeline):
        return ProvisioningDeviceClient(provisioning_pipeline)

    @pytest.mark.it(
        "Runs `connect`, `enable`, `register` and `disconnect` pipeline operations in sequence, if the registration response feature is not yet enabled"
    )
    def test_pipeline_operations_responses_disabled(
        self, mocker, client, provisioning_pipeline, registration_result
    ):
        # Set the pipeline to have responses not yet enabled
        provisioning_pipeline.responses_enabled.__getitem__.return_value = False
        # Create a manager mock to track all pipeline calls
        manager_mock = mocker.MagicMock()
        manager_mock.attach_mock(provisioning_pipeline.connect, "connect")
        manager_mock.attach_mock(provisioning_pipeline.enable_responses, "enable_responses")
        manager_mock.attach_mock(provisioning_pipeline.register, "register")
        manager_mock.attach_mock(provisioning_pipeline.disconnect, "disconnect")

        # Pipeline operations have not yet been called
        assert provisioning_pipeline.connect.call_count == 0
        assert provisioning_pipeline.enable_responses.call_count == 0
        assert provisioning_pipeline.register.call_count == 0
        assert provisioning_pipeline.disconnect.call_count == 0

        client.register()

        # Pipeline operations were called in sequence
        assert provisioning_pipeline.connect.call_count == 1
        assert provisioning_pipeline.enable_responses.call_count == 1
        assert provisioning_pipeline.register.call_count == 1
        assert provisioning_pipeline.disconnect.call_count == 1
        assert manager_mock.mock_calls == [
            mocker.call.connect(callback=mocker.ANY),
            mocker.call.enable_responses(callback=mocker.ANY),
            mocker.call.register(payload=mocker.ANY, callback=mocker.ANY),
            mocker.call.disconnect(callback=mocker.ANY),
        ]

    @pytest.mark.it(
        "Runs `connect`, `register` and `disconnect` pipeline operations in sequence, if the registration response feature is already enabled"
    )
    def test_pipeline_operations_responses_enabled(
        self, mocker, client, provisioning_pipeline, registration_result
    ):
        # Set the pipeline to have responses already enabled
        provisioning_pipeline.responses_enabled.__getitem__.return_value = True
        # Create a manager mock to track all pipeline calls
        manager_mock = mocker.MagicMock()
        manager_mock.attach_mock(provisioning_pipeline.connect, "connect")
        manager_mock.attach_mock(provisioning_pipeline.enable_responses, "enable_responses")
        manager_mock.attach_mock(provisioning_pipeline.register, "register")
        manager_mock.attach_mock(provisioning_pipeline.disconnect, "disconnect")

        # Pipeline operations have not yet been called
        assert provisioning_pipeline.connect.call_count == 0
        assert provisioning_pipeline.enable_responses.call_count == 0
        assert provisioning_pipeline.register.call_count == 0
        assert provisioning_pipeline.disconnect.call_count == 0

        client.register()

        # Enabling responses was not called
        assert provisioning_pipeline.enable_responses.call_count == 0
        # Pipeline operations were called in sequence
        assert provisioning_pipeline.connect.call_count == 1
        assert provisioning_pipeline.register.call_count == 1
        assert provisioning_pipeline.disconnect.call_count == 1
        assert manager_mock.mock_calls == [
            mocker.call.connect(callback=mocker.ANY),
            mocker.call.register(payload=mocker.ANY, callback=mocker.ANY),
            mocker.call.disconnect(callback=mocker.ANY),
        ]

    @pytest.mark.it("Waits for the completion of all pipeline operations before returning")
    def test_pipeline_operations_completed(self, mocker, client, provisioning_pipeline):
        # Set the pipeline to have responses not yet enabled
        provisioning_pipeline.responses_enabled.__getitem__.return_value = False
        cb_mock_connect = mocker.MagicMock()
        cb_mock_enable = mocker.MagicMock()
        cb_mock_register = mocker.MagicMock()
        cb_mock_disconnect = mocker.MagicMock()

        mocker.patch(
            "azure.iot.device.provisioning.provisioning_device_client.EventedCallback"
        ).side_effect = [cb_mock_connect, cb_mock_enable, cb_mock_register, cb_mock_disconnect]

        client.register()

        # All pipeline op completions were waited upon
        assert provisioning_pipeline.connect.call_count == 1
        assert provisioning_pipeline.connect.call_args == mocker.call(callback=cb_mock_connect)
        assert cb_mock_connect.wait_for_completion.call_count == 1
        assert provisioning_pipeline.enable_responses.call_count == 1
        assert provisioning_pipeline.enable_responses.call_args == mocker.call(
            callback=cb_mock_enable
        )
        assert cb_mock_enable.wait_for_completion.call_count == 1
        assert provisioning_pipeline.register.call_count == 1
        assert provisioning_pipeline.register.call_args == mocker.call(
            payload=mocker.ANY, callback=cb_mock_register
        )
        assert cb_mock_register.wait_for_completion.call_count == 1
        assert provisioning_pipeline.disconnect.call_count == 1
        assert provisioning_pipeline.disconnect.call_args == mocker.call(
            callback=cb_mock_disconnect
        )
        assert cb_mock_disconnect.wait_for_completion.call_count == 1

    @pytest.mark.it("Provides the provisioning payload to the pipeline `register` operation")
    @pytest.mark.parametrize(
        "payload",
        [
            pytest.param(None, id="No payload set on client"),
            pytest.param("Some Payload", id="Custom payload set on client"),
        ],
    )
    def test_register_with_payload(self, mocker, client, provisioning_pipeline, payload):
        if payload:
            client.provisioning_payload = payload
        else:
            assert client.provisioning_payload is None

        client.register()

        assert provisioning_pipeline.register.call_count == 1
        assert provisioning_pipeline.register.call_args == mocker.call(
            payload=client.provisioning_payload, callback=mocker.ANY
        )

    @pytest.mark.it("Returns the registration result returned by the pipeline `register` operation")
    @pytest.mark.parametrize(
        "registration_success",
        [
            pytest.param(True, id="Registration succeeded (assigned)"),
            pytest.param(False, id="Registration failed (not assigned)"),
        ],
    )
    def test_returns_registration_result(
        self, client, provisioning_pipeline, registration_result, registration_success
    ):
        if registration_success:
            registration_result._status = "assigned"
        else:
            registration_result._status = "not assigned"

        def register_complete_callback(payload, callback):
            callback(result=registration_result)

        provisioning_pipeline.register.side_effect = register_complete_callback

        result = client.register()
        assert result is registration_result

    @pytest.mark.it(
        "Raises a client error if the `connect` pipeline operation calls back with a pipeline error"
    )
    @pytest.mark.parametrize("pipeline_error,client_error", POSSIBLE_CLIENT_ERRORS)
    def test_connect_raises_error(
        self, client, provisioning_pipeline, pipeline_error, client_error
    ):
        my_pipeline_error = pipeline_error()

        def connect_complete_callback(callback):
            callback(error=my_pipeline_error)

        provisioning_pipeline.connect.side_effect = connect_complete_callback

        with pytest.raises(client_error) as e_info:
            client.register()
        assert e_info.value.__cause__ is my_pipeline_error

    @pytest.mark.it(
        "Raises a client error if the `enable` pipeline operation calls back with a pipeline error"
    )
    @pytest.mark.parametrize("pipeline_error,client_error", POSSIBLE_CLIENT_ERRORS)
    def test_enable_raises_error(self, client, provisioning_pipeline, pipeline_error, client_error):
        # Set the pipeline to have responses not yet enabled
        provisioning_pipeline.responses_enabled.__getitem__.return_value = False

        my_pipeline_error = pipeline_error()

        def enable_complete_callback(callback):
            callback(error=my_pipeline_error)

        provisioning_pipeline.enable_responses.side_effect = enable_complete_callback

        with pytest.raises(client_error) as e_info:
            client.register()
        assert e_info.value.__cause__ is my_pipeline_error

    @pytest.mark.it(
        "Raises a client error if the `register` pipeline operation calls back with a pipeline error"
    )
    @pytest.mark.parametrize("pipeline_error,client_error", POSSIBLE_CLIENT_ERRORS)
    def test_register_raises_error(
        self, client, provisioning_pipeline, pipeline_error, client_error
    ):
        my_pipeline_error = pipeline_error()

        def register_complete_callback(payload, callback):
            callback(error=my_pipeline_error, result=None)

        provisioning_pipeline.register.side_effect = register_complete_callback

        with pytest.raises(client_error) as e_info:
            client.register()
        assert e_info.value.__cause__ is my_pipeline_error

    @pytest.mark.it(
        "Still returns the registration result even if the `disconnect` pipeline operation calls back with a pipeline error"
    )
    @pytest.mark.parametrize("pipeline_error,client_error", POSSIBLE_CLIENT_ERRORS)
    def test_disconnect_raises_error(
        self, client, provisioning_pipeline, registration_result, pipeline_error, client_error
    ):
        my_pipeline_error = pipeline_error()

        def register_complete_callback(payload, callback):
            callback(result=registration_result)

        provisioning_pipeline.register.side_effect = register_complete_callback

        def disconnect_complete_callback(callback):
            callback(error=my_pipeline_error)

        provisioning_pipeline.disconnect.side_effect = disconnect_complete_callback

        result = client.register()
        assert result is registration_result


@pytest.mark.describe("ProvisioningDeviceClient (Sync) - .set_provisioning_payload()")
class TestClientProvisioningPayload(object):
    @pytest.mark.it("Sets the payload on the provisioning payload attribute")
    @pytest.mark.parametrize(
        "payload_input",
        [
            pytest.param("Hello World", id="String input"),
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
            pytest.param("Hello World", id="String input"),
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
