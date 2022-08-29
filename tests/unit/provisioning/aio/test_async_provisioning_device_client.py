# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import pytest
import logging
from azure.iot.device.provisioning.aio.async_provisioning_device_client import (
    ProvisioningDeviceClient,
)
from azure.iot.device.common import async_adapter
import asyncio
from azure.iot.device.iothub.pipeline import exceptions as pipeline_exceptions
from azure.iot.device import exceptions as client_exceptions
from ..shared_client_tests import (
    SharedProvisioningClientInstantiationTests,
    SharedProvisioningClientCreateFromSymmetricKeyTests,
    SharedProvisioningClientCreateFromX509CertificateTests,
)


logging.basicConfig(level=logging.DEBUG)
pytestmark = pytest.mark.asyncio


async def create_completed_future(result=None):
    f = asyncio.Future()
    f.set_result(result)
    return f


class ProvisioningClientTestsConfig(object):
    """Defines fixtures for asynchronous ProvisioningDeviceClient tests"""

    @pytest.fixture
    def client_class(self):
        return ProvisioningDeviceClient

    @pytest.fixture
    def client(self, provisioning_pipeline):
        return ProvisioningDeviceClient(provisioning_pipeline)


@pytest.mark.describe("ProvisioningDeviceClient (Async) - Instantiation")
class TestProvisioningClientInstantiation(
    ProvisioningClientTestsConfig, SharedProvisioningClientInstantiationTests
):
    pass


@pytest.mark.describe("ProvisioningDeviceClient (Async) - .create_from_symmetric_key()")
class TestProvisioningClientCreateFromSymmetricKey(
    ProvisioningClientTestsConfig, SharedProvisioningClientCreateFromSymmetricKeyTests
):
    pass


@pytest.mark.describe("ProvisioningDeviceClient (Async) - .create_from_x509_certificate()")
class TestProvisioningClientCreateFromX509Certificate(
    ProvisioningClientTestsConfig, SharedProvisioningClientCreateFromX509CertificateTests
):
    pass


@pytest.mark.describe("ProvisioningDeviceClient (Async) - .register()")
class TestClientRegister(object):
    @pytest.mark.it("Implicitly enables responses from provisioning service if not already enabled")
    async def test_enables_provisioning_only_if_not_already_enabled(
        self, mocker, provisioning_pipeline, registration_result
    ):
        # Override callback to pass successful result
        def register_complete_success_callback(payload, callback):
            callback(result=registration_result)

        mocker.patch.object(
            provisioning_pipeline, "register", side_effect=register_complete_success_callback
        )

        provisioning_pipeline.responses_enabled.__getitem__.return_value = False

        client = ProvisioningDeviceClient(provisioning_pipeline)
        await client.register()

        assert provisioning_pipeline.enable_responses.call_count == 1

        provisioning_pipeline.enable_responses.reset_mock()

        provisioning_pipeline.responses_enabled.__getitem__.return_value = True
        await client.register()
        assert provisioning_pipeline.enable_responses.call_count == 0

    @pytest.mark.it("Begins a 'register' pipeline operation")
    async def test_register_calls_pipeline_register(
        self, provisioning_pipeline, mocker, registration_result
    ):
        def register_complete_success_callback(payload, callback):
            callback(result=registration_result)

        mocker.patch.object(
            provisioning_pipeline, "register", side_effect=register_complete_success_callback
        )
        client = ProvisioningDeviceClient(provisioning_pipeline)
        await client.register()
        assert provisioning_pipeline.register.call_count == 1

    @pytest.mark.it(
        "Begins a 'shutdown' pipeline operation if the registration result is successful"
    )
    async def test_shutdown_upon_success(self, mocker, provisioning_pipeline, registration_result):
        # success result
        registration_result._status = "assigned"

        def register_complete_success_callback(payload, callback):
            callback(result=registration_result)

        mocker.patch.object(
            provisioning_pipeline, "register", side_effect=register_complete_success_callback
        )

        client = ProvisioningDeviceClient(provisioning_pipeline)
        await client.register()

        assert provisioning_pipeline.shutdown.call_count == 1

    @pytest.mark.it(
        "Does NOT begin a 'shutdown' pipeline operation if the registration result is NOT successful"
    )
    async def test_no_shutdown_upon_fail(self, mocker, provisioning_pipeline, registration_result):
        # fail result
        registration_result._status = "not assigned"

        def register_complete_fail_callback(payload, callback):
            callback(result=registration_result)

        mocker.patch.object(
            provisioning_pipeline, "register", side_effect=register_complete_fail_callback
        )

        client = ProvisioningDeviceClient(provisioning_pipeline)
        await client.register()

        assert provisioning_pipeline.shutdown.call_count == 0

    @pytest.mark.it(
        "Waits for the completion of both the 'register' and 'shutdown' pipeline operations before returning, if the registration result is successful"
    )
    async def test_waits_for_pipeline_op_completions_on_success(
        self, mocker, provisioning_pipeline, registration_result
    ):
        # success result
        registration_result._status = "assigned"

        # Set up mocks
        cb_mock_register = mocker.MagicMock()
        cb_mock_shutdown = mocker.MagicMock()
        cb_mock_register.completion.return_value = await create_completed_future(
            registration_result
        )
        cb_mock_shutdown.completion.return_value = await create_completed_future(None)
        mocker.patch.object(async_adapter, "AwaitableCallback").side_effect = [
            cb_mock_register,
            cb_mock_shutdown,
        ]

        # Run test
        client = ProvisioningDeviceClient(provisioning_pipeline)
        await client.register()

        # Calls made as expected
        assert provisioning_pipeline.register.call_count == 1
        assert provisioning_pipeline.shutdown.call_count == 1
        # Callbacks sent to pipeline as expected
        assert provisioning_pipeline.register.call_args == mocker.call(
            payload=mocker.ANY, callback=cb_mock_register
        )
        assert provisioning_pipeline.shutdown.call_args == mocker.call(callback=cb_mock_shutdown)
        # Callback completions were waited upon as expected
        assert cb_mock_register.completion.call_count == 1
        assert cb_mock_shutdown.completion.call_count == 1

    @pytest.mark.it(
        "Waits for the completion of just the 'register' pipeline operation before returning, if the registration result is NOT successful"
    )
    async def test_waits_for_pipeline_op_completion_on_failure(
        self, mocker, provisioning_pipeline, registration_result
    ):
        # fail result
        registration_result._status = "not assigned"

        # Set up mocks
        cb_mock_register = mocker.MagicMock()
        cb_mock_shutdown = mocker.MagicMock()
        cb_mock_register.completion.return_value = await create_completed_future(
            registration_result
        )
        cb_mock_shutdown.completion.return_value = await create_completed_future(None)
        mocker.patch.object(async_adapter, "AwaitableCallback").side_effect = [
            cb_mock_register,
            cb_mock_shutdown,
        ]

        # Run test
        client = ProvisioningDeviceClient(provisioning_pipeline)
        await client.register()

        # Calls made as expected
        assert provisioning_pipeline.register.call_count == 1
        assert provisioning_pipeline.shutdown.call_count == 0
        # Callbacks sent to pipeline as expected
        assert provisioning_pipeline.register.call_args == mocker.call(
            payload=mocker.ANY, callback=cb_mock_register
        )
        # Callback completions were waited upon as expected
        assert cb_mock_register.completion.call_count == 1
        assert cb_mock_shutdown.completion.call_count == 0

    @pytest.mark.it("Returns the registration result that the pipeline returned")
    async def test_verifies_registration_result_returned(
        self, mocker, provisioning_pipeline, registration_result
    ):
        result = registration_result

        def register_complete_success_callback(payload, callback):
            callback(result=result)

        mocker.patch.object(
            provisioning_pipeline, "register", side_effect=register_complete_success_callback
        )

        client = ProvisioningDeviceClient(provisioning_pipeline)
        result_returned = await client.register()
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
            pytest.param(
                pipeline_exceptions.OperationTimeout,
                client_exceptions.OperationTimeout,
                id="OperationTimeout->OperationTimeout",
            ),
            pytest.param(Exception, client_exceptions.ClientError, id="Exception->ClientError"),
        ],
    )
    async def test_raises_error_on_register_pipeline_op_error(
        self, mocker, client_error, pipeline_error, provisioning_pipeline
    ):
        error = pipeline_error()

        def register_complete_failure_callback(payload, callback):
            callback(result=None, error=error)

        mocker.patch.object(
            provisioning_pipeline, "register", side_effect=register_complete_failure_callback
        )

        client = ProvisioningDeviceClient(provisioning_pipeline)

        with pytest.raises(client_error) as e_info:
            await client.register()

        assert e_info.value.__cause__ is error
        assert provisioning_pipeline.register.call_count == 1

    @pytest.mark.it(
        "Raises a client error if the `shutdown` pipeline operation calls back with a pipeline error"
    )
    @pytest.mark.parametrize(
        "pipeline_error,client_error",
        [
            # The only expected errors are unexpected ones
            pytest.param(Exception, client_exceptions.ClientError, id="Exception->ClientError")
        ],
    )
    async def test_raises_error_on_shutdown_pipeline_op_error(
        self, mocker, pipeline_error, client_error, provisioning_pipeline, registration_result
    ):
        # success result is required to trigger shutdown
        registration_result._status = "assigned"

        error = pipeline_error()

        def register_complete_success_callback(payload, callback):
            callback(result=registration_result)

        def shutdown_failure_callback(callback):
            callback(result=None, error=error)

        mocker.patch.object(
            provisioning_pipeline, "register", side_effect=register_complete_success_callback
        )
        mocker.patch.object(
            provisioning_pipeline, "shutdown", side_effect=shutdown_failure_callback
        )

        client = ProvisioningDeviceClient(provisioning_pipeline)
        with pytest.raises(client_error) as e_info:
            await client.register()

        assert e_info.value.__cause__ is error
        assert provisioning_pipeline.register.call_count == 1


@pytest.mark.describe("ProvisioningDeviceClient (Async) - .set_provisioning_payload()")
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
    async def test_set_payload(self, mocker, payload_input):
        provisioning_pipeline = mocker.MagicMock()

        client = ProvisioningDeviceClient(provisioning_pipeline)
        client.provisioning_payload = payload_input
        assert client._provisioning_payload == payload_input

    @pytest.mark.it("Gets the payload from provisioning payload property")
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
    async def test_get_payload(self, mocker, payload_input):
        provisioning_pipeline = mocker.MagicMock()

        client = ProvisioningDeviceClient(provisioning_pipeline)
        client.provisioning_payload = payload_input
        assert client.provisioning_payload == payload_input
