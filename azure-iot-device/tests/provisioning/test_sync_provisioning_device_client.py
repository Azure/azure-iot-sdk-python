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
from azure.iot.device.provisioning.pipeline import exceptions as pipeline_exceptions
from azure.iot.device.provisioning import security, pipeline
import threading
from azure.iot.device import exceptions as client_exceptions

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


@pytest.fixture
def registration_result():
    registration_state = RegistrationState(fake_device_id, fake_assigned_hub, fake_sub_status)
    return RegistrationResult(fake_operation_id, fake_status, registration_state)


@pytest.fixture
def x509():
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

    def register(self, payload, callback):
        callback(result={})


@pytest.fixture
def mock_pipeline_init(mocker):
    return mocker.patch("azure.iot.device.provisioning.pipeline.ProvisioningPipeline")


# automatically mock the transport for all tests in this file.
@pytest.fixture(autouse=True)
def mock_transport(mocker):
    mocker.patch(
        "azure.iot.device.common.pipeline.pipeline_stages_mqtt.MQTTTransport", autospec=True
    )


class SharedClientCreateMethodUserOptionTests(object):
    @pytest.mark.it(
        "Sets the 'websockets' user option parameter on the PipelineConfig, if provided"
    )
    def test_websockets_option(
        self, mocker, client_create_method, create_method_args, mock_pipeline_init
    ):
        client_create_method(*create_method_args, websockets=True)

        # Get configuration object
        assert mock_pipeline_init.call_count == 1
        config = mock_pipeline_init.call_args[0][1]

        assert config.websockets

    # TODO: Show that input in the wrong format is formatted to the correct one. This test exists
    # in the ProvisioningPipelineConfig object already, but we do not currently show that this is felt
    # from the API level.
    @pytest.mark.it("Sets the 'cipher' user option parameter on the PipelineConfig, if provided")
    def test_cipher_option(
        self, mocker, client_create_method, create_method_args, mock_pipeline_init
    ):

        cipher = "DHE-RSA-AES128-SHA:DHE-RSA-AES256-SHA:ECDHE-ECDSA-AES128-GCM-SHA256"
        client_create_method(*create_method_args, cipher=cipher)

        # Get configuration object
        assert mock_pipeline_init.call_count == 1
        config = mock_pipeline_init.call_args[0][1]

        assert config.cipher == cipher

    @pytest.mark.it("Raises a TypeError if an invalid user option parameter is provided")
    def test_invalid_option(
        self, mocker, client_create_method, create_method_args, mock_pipeline_init
    ):
        with pytest.raises(TypeError):
            client_create_method(*create_method_args, invalid_option="some_value")

    @pytest.mark.it("Sets default user options if none are provided")
    def test_default_options(
        self, mocker, client_create_method, create_method_args, mock_pipeline_init
    ):
        client_create_method(*create_method_args)

        # Get configuration object
        assert mock_pipeline_init.call_count == 1
        config = mock_pipeline_init.call_args[0][1]

        assert not config.websockets
        assert not config.cipher


@pytest.mark.describe("ProvisioningDeviceClient - Instantiation")
class TestClientInstantiation(object):
    @pytest.mark.it(
        "Stores the ProvisioningPipeline from the 'provisioning_pipeline' parameter in the '_provisioning_pipeline' attribute"
    )
    def test_sets_provisioning_pipeline(self, provisioning_pipeline):
        client = ProvisioningDeviceClient(provisioning_pipeline)

        assert client._provisioning_pipeline is provisioning_pipeline

    @pytest.mark.it(
        "Instantiates with the initial value of the '_provisioning_payload' attribute set to None"
    )
    def test_payload(self, provisioning_pipeline):
        client = ProvisioningDeviceClient(provisioning_pipeline)

        assert client._provisioning_payload is None


@pytest.mark.describe("ProvisioningDeviceClient - .create_from_symmetric_key()")
class TestClientCreateFromSymmetricKey(SharedClientCreateMethodUserOptionTests):
    @pytest.fixture
    def client_create_method(self):
        return ProvisioningDeviceClient.create_from_symmetric_key

    @pytest.fixture
    def create_method_args(self):
        return [fake_provisioning_host, fake_registration_id, fake_id_scope, fake_symmetric_key]

    @pytest.mark.it("Creates a SymmetricKeySecurityClient using the given parameters")
    def test_security_client(self, mocker):
        spy_sec_client = mocker.spy(security, "SymmetricKeySecurityClient")

        ProvisioningDeviceClient.create_from_symmetric_key(
            provisioning_host=fake_provisioning_host,
            registration_id=fake_registration_id,
            id_scope=fake_id_scope,
            symmetric_key=fake_symmetric_key,
        )

        assert spy_sec_client.call_count == 1
        assert spy_sec_client.call_args == mocker.call(
            provisioning_host=fake_provisioning_host,
            registration_id=fake_registration_id,
            id_scope=fake_id_scope,
            symmetric_key=fake_symmetric_key,
        )

    @pytest.mark.it(
        "Uses the SymmetricKeySecurityClient object and the ProvisioningPipelineConfig object to create a ProvisioningPipeline"
    )
    def test_pipeline(self, mocker, mock_pipeline_init):
        # Note that the details of how the pipeline config is set up are covered in the
        # SharedClientCreateMethodUserOptionTests
        mock_pipeline_config = mocker.patch.object(
            pipeline, "ProvisioningPipelineConfig"
        ).return_value
        mock_sec_client = mocker.patch.object(security, "SymmetricKeySecurityClient").return_value

        ProvisioningDeviceClient.create_from_symmetric_key(
            provisioning_host=fake_provisioning_host,
            registration_id=fake_registration_id,
            id_scope=fake_id_scope,
            symmetric_key=fake_symmetric_key,
        )

        assert mock_pipeline_init.call_count == 1
        assert mock_pipeline_init.call_args == mocker.call(mock_sec_client, mock_pipeline_config)

    @pytest.mark.it("Uses the ProvisioningPipeline to instantiate the client")
    def test_client_creation(self, mocker, mock_pipeline_init):
        spy_client_init = mocker.spy(ProvisioningDeviceClient, "__init__")

        ProvisioningDeviceClient.create_from_symmetric_key(
            provisioning_host=fake_provisioning_host,
            registration_id=fake_registration_id,
            id_scope=fake_id_scope,
            symmetric_key=fake_symmetric_key,
        )

        assert spy_client_init.call_count == 1
        assert spy_client_init.call_args == mocker.call(mocker.ANY, mock_pipeline_init.return_value)

    @pytest.mark.it("Returns the instantiated client")
    def test_returns_client(self, mocker):
        client = ProvisioningDeviceClient.create_from_symmetric_key(
            provisioning_host=fake_provisioning_host,
            registration_id=fake_registration_id,
            id_scope=fake_id_scope,
            symmetric_key=fake_symmetric_key,
        )
        assert isinstance(client, ProvisioningDeviceClient)


@pytest.mark.describe("ProvisioningDeviceClient - .create_from_x509_certificate()")
class TestClientCreateFromX509Certificate(SharedClientCreateMethodUserOptionTests):
    @pytest.fixture
    def client_create_method(self):
        return ProvisioningDeviceClient.create_from_x509_certificate

    @pytest.fixture
    def create_method_args(self, x509):
        return [fake_provisioning_host, fake_registration_id, fake_id_scope, x509]

    @pytest.mark.it("Creates an X509SecurityClient using the given parameters")
    def test_security_client(self, mocker, x509):
        spy_sec_client = mocker.spy(security, "X509SecurityClient")

        ProvisioningDeviceClient.create_from_x509_certificate(
            provisioning_host=fake_provisioning_host,
            registration_id=fake_registration_id,
            id_scope=fake_id_scope,
            x509=x509,
        )

        assert spy_sec_client.call_count == 1
        assert spy_sec_client.call_args == mocker.call(
            provisioning_host=fake_provisioning_host,
            registration_id=fake_registration_id,
            id_scope=fake_id_scope,
            x509=x509,
        )

    @pytest.mark.it(
        "Uses the X509SecurityClient object and the ProvisioningPipelineConfig object to create a ProvisioningPipeline"
    )
    def test_pipeline(self, mocker, mock_pipeline_init, x509):
        # Note that the details of how the pipeline config is set up are covered in the
        # SharedClientCreateMethodUserOptionTests
        mock_pipeline_config = mocker.patch.object(
            pipeline, "ProvisioningPipelineConfig"
        ).return_value
        mock_sec_client = mocker.patch.object(security, "X509SecurityClient").return_value

        ProvisioningDeviceClient.create_from_x509_certificate(
            provisioning_host=fake_provisioning_host,
            registration_id=fake_registration_id,
            id_scope=fake_id_scope,
            x509=x509,
        )

        assert mock_pipeline_init.call_count == 1
        assert mock_pipeline_init.call_args == mocker.call(mock_sec_client, mock_pipeline_config)

    @pytest.mark.it("Uses the ProvisioningPipeline to instantiate the client")
    def test_client_creation(self, mocker, mock_pipeline_init, x509):
        spy_client_init = mocker.spy(ProvisioningDeviceClient, "__init__")

        ProvisioningDeviceClient.create_from_x509_certificate(
            provisioning_host=fake_provisioning_host,
            registration_id=fake_registration_id,
            id_scope=fake_id_scope,
            x509=x509,
        )

        assert spy_client_init.call_count == 1
        assert spy_client_init.call_args == mocker.call(mocker.ANY, mock_pipeline_init.return_value)

    @pytest.mark.it("Returns the instantiated client")
    def test_returns_client(self, mocker, x509):
        client = ProvisioningDeviceClient.create_from_x509_certificate(
            provisioning_host=fake_provisioning_host,
            registration_id=fake_registration_id,
            id_scope=fake_id_scope,
            x509=x509,
        )
        assert isinstance(client, ProvisioningDeviceClient)


@pytest.mark.describe("ProvisioningDeviceClient - .register()")
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
