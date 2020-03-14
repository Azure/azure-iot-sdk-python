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


@pytest.fixture(scope="function")
def mock_provisioning_pipeline(
    mocker, input_security_client, mock_mqtt_transport, pipeline_configuration
):
    provisioning_pipeline = ProvisioningPipeline(input_security_client, pipeline_configuration)
    provisioning_pipeline.on_connected = mocker.MagicMock()
    provisioning_pipeline.on_disconnected = mocker.MagicMock()
    provisioning_pipeline.on_message_received = mocker.MagicMock()
    helpers.add_mock_method_waiter(provisioning_pipeline, "on_connected")
    helpers.add_mock_method_waiter(provisioning_pipeline, "on_disconnected")
    helpers.add_mock_method_waiter(mock_mqtt_transport, "publish")

    yield provisioning_pipeline
    provisioning_pipeline.disconnect()


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
    @pytest.mark.it("Request calls publish on provider")
    def test_send_register_request_calls_publish_on_provider(
        self, mocker, mock_provisioning_pipeline, input_security_client, mock_mqtt_transport
    ):
        mock_init_uuid = mocker.patch(
            "azure.iot.device.common.pipeline.pipeline_stages_base.uuid.uuid4"
        )
        mock_init_uuid.return_value = fake_request_id

        mock_provisioning_pipeline.connect()
        mock_mqtt_transport.on_mqtt_connected_handler()
        mock_provisioning_pipeline.wait_for_on_connected_to_be_called()
        mock_provisioning_pipeline.register(payload=fake_mqtt_payload)

        assert mock_mqtt_transport.connect.call_count == 1

        if isinstance(input_security_client, X509SecurityClient):
            assert mock_mqtt_transport.connect.call_args[1]["password"] is None
        else:
            assert mock_mqtt_transport.connect.call_args[1]["password"] is not None
            assert_for_symmetric_key(mock_mqtt_transport.connect.call_args[1]["password"])

        fake_publish_topic = "$dps/registrations/PUT/iotdps-register/?$rid={}".format(
            fake_request_id
        )

        mock_mqtt_transport.wait_for_publish_to_be_called()
        assert mock_mqtt_transport.publish.call_count == 1
        assert mock_mqtt_transport.publish.call_args[1]["topic"] == fake_publish_topic
        assert mock_mqtt_transport.publish.call_args[1]["payload"] == fake_register_publish_payload

    @pytest.mark.it("Request queues and connects before calling publish on provider")
    def test_send_request_queues_and_connects_before_sending(
        self, mocker, mock_provisioning_pipeline, input_security_client, mock_mqtt_transport
    ):

        mock_init_uuid = mocker.patch(
            "azure.iot.device.common.pipeline.pipeline_stages_base.uuid.uuid4"
        )
        mock_init_uuid.return_value = fake_request_id
        # send an event
        mock_provisioning_pipeline.register(payload=fake_mqtt_payload)

        # verify that we called connect
        assert mock_mqtt_transport.connect.call_count == 1

        if isinstance(input_security_client, X509SecurityClient):
            assert mock_mqtt_transport.connect.call_args[1]["password"] is None
        else:
            assert mock_mqtt_transport.connect.call_args[1]["password"] is not None
            assert_for_symmetric_key(mock_mqtt_transport.connect.call_args[1]["password"])

        # verify that we're not connected yet and verify that we havent't published yet
        mock_provisioning_pipeline.wait_for_on_connected_to_not_be_called()
        mock_provisioning_pipeline.on_connected.assert_not_called()
        mock_mqtt_transport.wait_for_publish_to_not_be_called()
        mock_mqtt_transport.publish.assert_not_called()

        # finish the connection
        mock_mqtt_transport.on_mqtt_connected_handler()
        mock_provisioning_pipeline.wait_for_on_connected_to_be_called()

        # verify that our connected callback was called and verify that we published the event
        mock_provisioning_pipeline.on_connected.assert_called_once_with("connected")

        fake_publish_topic = "$dps/registrations/PUT/iotdps-register/?$rid={}".format(
            fake_request_id
        )

        mock_mqtt_transport.wait_for_publish_to_be_called()
        assert mock_mqtt_transport.publish.call_count == 1
        assert mock_mqtt_transport.publish.call_args[1]["topic"] == fake_publish_topic
        assert mock_mqtt_transport.publish.call_args[1]["payload"] == fake_register_publish_payload

    @pytest.mark.it("Request queues and waits for connect to be completed")
    def test_send_request_queues_if_waiting_for_connect_complete(
        self, mocker, mock_provisioning_pipeline, input_security_client, mock_mqtt_transport
    ):
        mock_init_uuid = mocker.patch(
            "azure.iot.device.common.pipeline.pipeline_stages_base.uuid.uuid4"
        )
        mock_init_uuid.return_value = fake_request_id

        # start connecting and verify that we've called into the transport
        mock_provisioning_pipeline.connect()
        assert mock_mqtt_transport.connect.call_count == 1

        if isinstance(input_security_client, X509SecurityClient):
            assert mock_mqtt_transport.connect.call_args[1]["password"] is None
        else:
            assert mock_mqtt_transport.connect.call_args[1]["password"] is not None
            assert_for_symmetric_key(mock_mqtt_transport.connect.call_args[1]["password"])

        # send an event
        mock_provisioning_pipeline.register(payload=fake_mqtt_payload)

        # verify that we're not connected yet and verify that we havent't published yet
        mock_provisioning_pipeline.wait_for_on_connected_to_not_be_called()
        mock_provisioning_pipeline.on_connected.assert_not_called()
        mock_mqtt_transport.wait_for_publish_to_not_be_called()
        mock_mqtt_transport.publish.assert_not_called()

        # finish the connection
        mock_mqtt_transport.on_mqtt_connected_handler()
        mock_provisioning_pipeline.wait_for_on_connected_to_be_called()

        # verify that our connected callback was called and verify that we published the event
        mock_provisioning_pipeline.on_connected.assert_called_once_with("connected")
        fake_publish_topic = "$dps/registrations/PUT/iotdps-register/?$rid={}".format(
            fake_request_id
        )
        mock_mqtt_transport.wait_for_publish_to_be_called()
        assert mock_mqtt_transport.publish.call_count == 1
        assert mock_mqtt_transport.publish.call_args[1]["topic"] == fake_publish_topic
        assert mock_mqtt_transport.publish.call_args[1]["payload"] == fake_register_publish_payload

    @pytest.mark.it("Request can be sent multiple times overlapping each other")
    def test_send_request_sends_overlapped_events(
        self, mock_provisioning_pipeline, mock_mqtt_transport, mocker
    ):
        mock_init_uuid = mocker.patch(
            "azure.iot.device.common.pipeline.pipeline_stages_base.uuid.uuid4"
        )
        mock_init_uuid.return_value = fake_request_id

        fake_request_id_1 = fake_request_id
        fake_msg_1 = fake_mqtt_payload
        fake_msg_2 = "Petrificus Totalus"

        # connect
        mock_provisioning_pipeline.connect()
        mock_mqtt_transport.on_mqtt_connected_handler()
        mock_provisioning_pipeline.wait_for_on_connected_to_be_called()

        # send an event
        callback_1 = mocker.MagicMock()
        mock_provisioning_pipeline.register(payload=fake_msg_1, callback=callback_1)

        fake_publish_topic = "$dps/registrations/PUT/iotdps-register/?$rid={}".format(
            fake_request_id_1
        )
        mock_mqtt_transport.wait_for_publish_to_be_called()
        assert mock_mqtt_transport.publish.call_count == 1
        assert mock_mqtt_transport.publish.call_args[1]["topic"] == fake_publish_topic
        assert mock_mqtt_transport.publish.call_args[1]["payload"] == fake_register_publish_payload

        # while we're waiting for that send to complete, send another event
        callback_2 = mocker.MagicMock()
        # provisioning_pipeline.send_message(fake_msg_2, callback_2)
        mock_provisioning_pipeline.register(payload=fake_msg_2, callback=callback_2)

        # verify that we've called publish twice and verify that neither send_message
        # has completed (because we didn't do anything here to complete it).
        mock_mqtt_transport.wait_for_publish_to_be_called()
        assert mock_mqtt_transport.publish.call_count == 2
        callback_1.assert_not_called()
        callback_2.assert_not_called()

    @pytest.mark.it("Connects , sends request queues and then disconnects")
    def test_connect_send_disconnect(self, mock_provisioning_pipeline, mock_mqtt_transport):
        # connect
        mock_provisioning_pipeline.connect()
        mock_mqtt_transport.on_mqtt_connected_handler()
        mock_provisioning_pipeline.wait_for_on_connected_to_be_called()

        # send an event
        mock_provisioning_pipeline.register(payload=fake_mqtt_payload)
        mock_mqtt_transport.on_mqtt_published(0)

        # disconnect
        mock_provisioning_pipeline.disconnect()
        mock_mqtt_transport.disconnect.assert_called_once_with()


@pytest.mark.describe("ProvisioningPipeline - .disconnect()")
class TestDisconnect(object):
    @pytest.mark.it("Calls disconnect on provider")
    def test_disconnect_calls_disconnect_on_provider(
        self, mock_provisioning_pipeline, mock_mqtt_transport
    ):
        mock_provisioning_pipeline.connect()
        mock_mqtt_transport.on_mqtt_connected_handler()
        mock_provisioning_pipeline.wait_for_on_connected_to_be_called()
        mock_provisioning_pipeline.disconnect()

        mock_mqtt_transport.disconnect.assert_called_once_with()

    @pytest.mark.it("Is ignored if already disconnected")
    def test_disconnect_ignored_if_already_disconnected(
        self, mock_provisioning_pipeline, mock_mqtt_transport
    ):
        mock_provisioning_pipeline.disconnect(None)

        mock_mqtt_transport.disconnect.assert_not_called()

    @pytest.mark.it("After complete calls handler with `disconnected` state")
    def test_disconnect_calls_client_disconnect_callback(
        self, mock_provisioning_pipeline, mock_mqtt_transport
    ):
        mock_provisioning_pipeline.connect()
        mock_mqtt_transport.on_mqtt_connected_handler()
        mock_provisioning_pipeline.wait_for_on_connected_to_be_called()

        mock_provisioning_pipeline.disconnect()
        mock_mqtt_transport.on_mqtt_disconnected_handler(None)

        mock_provisioning_pipeline.wait_for_on_disconnected_to_be_called()
        mock_provisioning_pipeline.on_disconnected.assert_called_once_with("disconnected")


@pytest.mark.describe("ProvisioningPipeline - .enable_responses()")
class TestEnable(object):
    @pytest.mark.it("Calls subscribe on provider")
    def test_subscribe_calls_subscribe_on_provider(
        self, mock_provisioning_pipeline, mock_mqtt_transport
    ):
        mock_provisioning_pipeline.connect()
        mock_mqtt_transport.on_mqtt_connected_handler()
        mock_provisioning_pipeline.wait_for_on_connected_to_be_called()
        mock_provisioning_pipeline.enable_responses()

        assert mock_mqtt_transport.subscribe.call_count == 1
        assert mock_mqtt_transport.subscribe.call_args[1]["topic"] == fake_sub_unsub_topic
