# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
import logging
from azure.iot.device.common.models import X509
from azure.iot.device.provisioning.security.sk_security_client import SymmetricKeySecurityClient
from azure.iot.device.provisioning.security.x509_security_client import X509SecurityClient
from azure.iot.device.provisioning.pipeline.provisioning_pipeline import ProvisioningPipeline
from tests.common.pipeline import helpers
import json
from azure.iot.device.provisioning.pipeline import constant as dps_constants
from azure.iot.device.provisioning.pipeline import (
    pipeline_stages_provisioning,
    pipeline_stages_provisioning_mqtt,
    pipeline_ops_provisioning,
)
from azure.iot.device.common.pipeline import (
    pipeline_stages_base,
    pipeline_stages_mqtt,
    pipeline_ops_base,
)

logging.basicConfig(level=logging.DEBUG)
pytestmark = pytest.mark.usefixtures("fake_pipeline_thread")


feature = dps_constants.REGISTER


fake_symmetric_key = "Zm9vYmFy"
fake_registration_id = "MyPensieve"
fake_id_scope = "Enchanted0000Ceiling7898"
fake_provisioning_host = "beauxbatons.academy-net"
fake_device_id = "elder_wand"
fake_registration_id = "registered_remembrall"
fake_provisioning_host = "hogwarts.com"
fake_id_scope = "weasley_wizard_wheezes"
fake_ca_cert = "fake_certificate"
fake_sas_token = "horcrux_token"
fake_security_client = "secure_via_muffliato"
fake_request_id = "fake_request_1234"
fake_mqtt_payload = "hello hogwarts"
fake_register_publish_payload = '{{"payload": {json_payload}, "registrationId": "{reg_id}"}}'.format(
    reg_id=fake_registration_id, json_payload=json.dumps(fake_mqtt_payload)
)
fake_operation_id = "fake_operation_9876"
fake_sub_unsub_topic = "$dps/registrations/res/#"
fake_x509_cert_file = "fantastic_beasts"
fake_x509_cert_key_file = "where_to_find_them"
fake_pass_phrase = "alohomora"
fake_registration_result = "fake_result"
fake_request_payload = "fake_request_payload"


def mock_x509():
    return X509(fake_x509_cert_file, fake_x509_cert_key_file, fake_pass_phrase)


different_security_clients = [
    (
        SymmetricKeySecurityClient,
        {
            "provisioning_host": fake_provisioning_host,
            "registration_id": fake_registration_id,
            "id_scope": fake_id_scope,
            "symmetric_key": fake_symmetric_key,
        },
    ),
    (
        X509SecurityClient,
        {
            "provisioning_host": fake_provisioning_host,
            "registration_id": fake_registration_id,
            "id_scope": fake_id_scope,
            "x509": mock_x509(),
        },
    ),
]


def assert_for_symmetric_key(password):
    assert password is not None
    assert "SharedAccessSignature" in password
    assert "skn=registration" in password
    assert fake_id_scope in password
    assert fake_registration_id in password


def assert_for_client_x509(x509):
    assert x509 is not None
    assert x509.certificate_file == fake_x509_cert_file
    assert x509.key_file == fake_x509_cert_key_file
    assert x509.pass_phrase == fake_pass_phrase


@pytest.fixture(
    scope="function",
    params=different_security_clients,
    ids=[x[0].__name__ for x in different_security_clients],
)
def input_security_client(request):
    sec_client_class = request.param[0]
    init_kwargs = request.param[1]
    return sec_client_class(**init_kwargs)


@pytest.fixture
def pipeline_configuration(mocker):
    return mocker.MagicMock()


@pytest.fixture
def pipeline(mocker, input_security_client, pipeline_configuration):
    pipeline = ProvisioningPipeline(input_security_client, pipeline_configuration)
    mocker.patch.object(pipeline._pipeline, "run_op")
    return pipeline


# automatically mock the transport for all tests in this file.
@pytest.fixture(autouse=True)
def mock_mqtt_transport(mocker):
    return mocker.patch(
        "azure.iot.device.provisioning.pipeline.provisioning_pipeline.pipeline_stages_mqtt.MQTTTransport"
    ).return_value


@pytest.mark.describe("ProvisioningPipeline - Instantiation")
class TestProvisioningPipelineInstantiation(object):
    @pytest.mark.it("Begins tracking the enabled/disabled status of responses")
    def test_features(self, input_security_client, pipeline_configuration):
        pipeline = ProvisioningPipeline(input_security_client, pipeline_configuration)
        pipeline.responses_enabled[feature]
        # No assertion required - if this doesn't raise a KeyError, it is a success

    @pytest.mark.it("Marks responses as disabled")
    def test_features_disabled(self, input_security_client, pipeline_configuration):
        pipeline = ProvisioningPipeline(input_security_client, pipeline_configuration)
        assert not pipeline.responses_enabled[feature]

    @pytest.mark.it("Sets all handlers to an initial value of None")
    def test_handlers_set_to_none(self, input_security_client, pipeline_configuration):
        pipeline = ProvisioningPipeline(input_security_client, pipeline_configuration)
        assert pipeline.on_connected is None
        assert pipeline.on_disconnected is None
        assert pipeline.on_message_received is None

    @pytest.mark.it("Configures the pipeline to trigger handlers in response to external events")
    def test_handlers_configured(self, input_security_client, pipeline_configuration):
        pipeline = ProvisioningPipeline(input_security_client, pipeline_configuration)
        assert pipeline._pipeline.on_pipeline_event_handler is not None
        assert pipeline._pipeline.on_connected_handler is not None
        assert pipeline._pipeline.on_disconnected_handler is not None

    @pytest.mark.it("Configures the pipeline with a series of PipelineStages")
    def test_pipeline_configuration(self, input_security_client, pipeline_configuration):
        pipeline = ProvisioningPipeline(input_security_client, pipeline_configuration)
        curr_stage = pipeline._pipeline

        expected_stage_order = [
            pipeline_stages_base.PipelineRootStage,
            pipeline_stages_provisioning.UseSecurityClientStage,
            pipeline_stages_provisioning.RegistrationStage,
            pipeline_stages_provisioning.PollingStatusStage,
            pipeline_stages_base.CoordinateRequestAndResponseStage,
            pipeline_stages_provisioning_mqtt.ProvisioningMQTTTranslationStage,
            pipeline_stages_base.AutoConnectStage,
            pipeline_stages_base.ReconnectStage,
            pipeline_stages_base.ConnectionLockStage,
            pipeline_stages_base.RetryStage,
            pipeline_stages_base.OpTimeoutStage,
            pipeline_stages_mqtt.MQTTTransportStage,
        ]

        # Assert that all PipelineStages are there, and they are in the right order
        for i in range(len(expected_stage_order)):
            expected_stage = expected_stage_order[i]
            assert isinstance(curr_stage, expected_stage)
            curr_stage = curr_stage.next

        # Assert there are no more additional stages
        assert curr_stage is None

    # TODO: revist these tests after auth revision
    # They are too tied to auth types (and there's too much variance in auths to effectively test)
    # Ideally ProvisioningPipeline is entirely insulated from any auth differential logic (and module/device distinctions)
    # In the meantime, we are using a device auth with connection string to stand in for generic SAS auth
    # and device auth with X509 certs to stand in for generic X509 auth
    @pytest.mark.it(
        "Runs a Set SecurityClient Operation with the provided SecurityClient on the pipeline"
    )
    def test_security_client_success(self, mocker, input_security_client, pipeline_configuration):
        mocker.spy(pipeline_stages_base.PipelineRootStage, "run_op")
        pipeline = ProvisioningPipeline(input_security_client, pipeline_configuration)

        op = pipeline._pipeline.run_op.call_args[0][1]
        assert pipeline._pipeline.run_op.call_count == 1
        if isinstance(input_security_client, X509SecurityClient):
            assert isinstance(op, pipeline_ops_provisioning.SetX509SecurityClientOperation)
        else:
            assert isinstance(op, pipeline_ops_provisioning.SetSymmetricKeySecurityClientOperation)
        assert op.security_client is input_security_client

    @pytest.mark.it(
        "Raises exceptions that occurred in execution upon unsuccessful completion of the Set SecurityClient Operation"
    )
    def test_security_client_failure(
        self, mocker, input_security_client, arbitrary_exception, pipeline_configuration
    ):
        old_run_op = pipeline_stages_base.PipelineRootStage._run_op

        def fail_set_security_client(self, op):
            if isinstance(input_security_client, X509SecurityClient) or isinstance(
                input_security_client, SymmetricKeySecurityClient
            ):
                op.complete(error=arbitrary_exception)
            else:
                old_run_op(self, op)

        mocker.patch.object(
            pipeline_stages_base.PipelineRootStage,
            "_run_op",
            side_effect=fail_set_security_client,
            autospec=True,
        )

        with pytest.raises(arbitrary_exception.__class__) as e_info:
            ProvisioningPipeline(input_security_client, pipeline_configuration)
        assert e_info.value is arbitrary_exception


@pytest.mark.describe("ProvisioningPipeline - .connect()")
class TestProvisioningPipelineConnect(object):
    @pytest.mark.it("Runs a ConnectOperation on the pipeline")
    def test_runs_op(self, pipeline, mocker):
        cb = mocker.MagicMock()
        pipeline.connect(callback=cb)
        assert pipeline._pipeline.run_op.call_count == 1
        assert isinstance(
            pipeline._pipeline.run_op.call_args[0][0], pipeline_ops_base.ConnectOperation
        )

    @pytest.mark.it("Triggers the callback upon successful completion of the ConnectOperation")
    def test_op_success_with_callback(self, mocker, pipeline):
        cb = mocker.MagicMock()

        # Begin operation
        pipeline.connect(callback=cb)
        assert cb.call_count == 0

        # Trigger op completion
        op = pipeline._pipeline.run_op.call_args[0][0]
        op.complete(error=None)

        assert cb.call_count == 1
        assert cb.call_args == mocker.call(error=None)

    @pytest.mark.it(
        "Calls the callback with the error upon unsuccessful completion of the ConnectOperation"
    )
    def test_op_fail(self, mocker, pipeline, arbitrary_exception):
        cb = mocker.MagicMock()

        pipeline.connect(callback=cb)
        op = pipeline._pipeline.run_op.call_args[0][0]

        op.complete(error=arbitrary_exception)
        assert cb.call_count == 1
        assert cb.call_args == mocker.call(error=arbitrary_exception)


@pytest.mark.describe("ProvisioningPipeline - .disconnect()")
class TestProvisioningPipelineDisconnect(object):
    @pytest.mark.it("Runs a DisconnectOperation on the pipeline")
    def test_runs_op(self, pipeline, mocker):
        pipeline.disconnect(callback=mocker.MagicMock())
        assert pipeline._pipeline.run_op.call_count == 1
        assert isinstance(
            pipeline._pipeline.run_op.call_args[0][0], pipeline_ops_base.DisconnectOperation
        )

    @pytest.mark.it("Triggers the callback upon successful completion of the DisconnectOperation")
    def test_op_success_with_callback(self, mocker, pipeline):
        cb = mocker.MagicMock()

        # Begin operation
        pipeline.disconnect(callback=cb)
        assert cb.call_count == 0

        # Trigger op completion callback
        op = pipeline._pipeline.run_op.call_args[0][0]
        op.complete(error=None)

        assert cb.call_count == 1
        assert cb.call_args == mocker.call(error=None)

    @pytest.mark.it(
        "Calls the callback with the error upon unsuccessful completion of the DisconnectOperation"
    )
    def test_op_fail(self, mocker, pipeline, arbitrary_exception):
        cb = mocker.MagicMock()
        pipeline.disconnect(callback=cb)

        op = pipeline._pipeline.run_op.call_args[0][0]
        op.complete(error=arbitrary_exception)

        assert cb.call_count == 1
        assert cb.call_args == mocker.call(error=arbitrary_exception)


@pytest.mark.describe("ProvisioningPipeline - .register()")
class TestSendRegister(object):
    @pytest.mark.it("Runs a RegisterOperation on the pipeline")
    def test_runs_op(self, pipeline, mocker):
        cb = mocker.MagicMock()
        pipeline.register(callback=cb)
        assert pipeline._pipeline.run_op.call_count == 1
        op = pipeline._pipeline.run_op.call_args[0][0]
        assert isinstance(op, pipeline_ops_provisioning.RegisterOperation)
        assert op.registration_id == fake_registration_id

    @pytest.mark.it("passes the payload parameter as request_payload on the RegistrationRequest")
    def test_sets_request_payload(self, pipeline, mocker):
        cb = mocker.MagicMock()
        pipeline.register(payload=fake_request_payload, callback=cb)
        op = pipeline._pipeline.run_op.call_args[0][0]
        assert op.request_payload is fake_request_payload

    @pytest.mark.it(
        "sets request_payload on the RegistrationRequest to None if no payload is provided"
    )
    def test_sets_empty_payload(self, pipeline, mocker):
        cb = mocker.MagicMock()
        pipeline.register(callback=cb)
        op = pipeline._pipeline.run_op.call_args[0][0]
        assert op.request_payload is None

    @pytest.mark.it(
        "Triggers the callback upon successful completion of the RegisterOperation, passing the registration result in the result parameter"
    )
    def test_op_success_with_callback(self, mocker, pipeline):
        cb = mocker.MagicMock()

        # Begin operation
        pipeline.register(callback=cb)
        assert cb.call_count == 0

        # Trigger op completion
        op = pipeline._pipeline.run_op.call_args[0][0]
        op.registration_result = fake_registration_result
        op.complete(error=None)

        assert cb.call_count == 1
        assert cb.call_args == mocker.call(result=fake_registration_result)

    @pytest.mark.it(
        "Calls the callback with the error upon unsuccessful completion of the RegisterOperation"
    )
    def test_op_fail(self, mocker, pipeline, arbitrary_exception):
        cb = mocker.MagicMock()

        pipeline.register(callback=cb)

        op = pipeline._pipeline.run_op.call_args[0][0]
        op.registration_result = fake_registration_result
        op.complete(error=arbitrary_exception)

        assert cb.call_count == 1
        assert cb.call_args == mocker.call(error=arbitrary_exception, result=None)


@pytest.mark.describe("ProvisioningPipeline - .enable_responses()")
class TestEnable(object):
    @pytest.mark.it("Marks the feature as enabled")
    def test_mark_feature_enabled(self, pipeline, mocker):
        assert not pipeline.responses_enabled[feature]
        pipeline.enable_responses(callback=mocker.MagicMock())
        assert pipeline.responses_enabled[feature]

    @pytest.mark.it(
        "Runs a EnableFeatureOperation on the pipeline, passing in the name of the feature"
    )
    def test_runs_op(self, pipeline, mocker):
        pipeline.enable_responses(callback=mocker.MagicMock())
        op = pipeline._pipeline.run_op.call_args[0][0]

        assert pipeline._pipeline.run_op.call_count == 1
        assert isinstance(op, pipeline_ops_base.EnableFeatureOperation)
        assert op.feature_name == dps_constants.REGISTER

    @pytest.mark.it(
        "Triggers the callback upon successful completion of the EnableFeatureOperation"
    )
    def test_op_success_with_callback(self, mocker, pipeline):
        cb = mocker.MagicMock()

        # Begin operation
        pipeline.enable_responses(callback=cb)
        assert cb.call_count == 0

        # Trigger op completion callback
        op = pipeline._pipeline.run_op.call_args[0][0]
        op.complete(error=None)

        assert cb.call_count == 1
        assert cb.call_args == mocker.call(error=None)

    @pytest.mark.it(
        "Calls the callback with the error upon unsuccessful completion of the EnableFeatureOperation"
    )
    def test_op_fail(self, mocker, pipeline, arbitrary_exception):
        cb = mocker.MagicMock()
        pipeline.enable_responses(callback=cb)

        op = pipeline._pipeline.run_op.call_args[0][0]
        op.complete(error=arbitrary_exception)

        assert cb.call_count == 1
        assert cb.call_args == mocker.call(error=arbitrary_exception)
