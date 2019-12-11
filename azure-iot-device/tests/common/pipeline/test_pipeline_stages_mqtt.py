# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import logging
import pytest
import sys
import six
from azure.iot.device.common import transport_exceptions, handle_exceptions
from azure.iot.device.common.pipeline import (
    pipeline_ops_base,
    pipeline_stages_base,
    pipeline_ops_mqtt,
    pipeline_events_base,
    pipeline_events_mqtt,
    pipeline_stages_mqtt,
    pipeline_exceptions,
    config,
)
from tests.common.pipeline.helpers import StageRunOpTestBase
from tests.common.pipeline import pipeline_stage_test

this_module = sys.modules[__name__]
logging.basicConfig(level=logging.DEBUG)
pytestmark = pytest.mark.usefixtures("fake_pipeline_thread")

###################
# COMMON FIXTURES #
###################


@pytest.fixture
def mock_transport(mocker):
    return mocker.patch(
        "azure.iot.device.common.pipeline.pipeline_stages_mqtt.MQTTTransport", autospec=True
    )


# Not a fixture, but used in parametrization
def fake_callback():
    pass


########################
# MQTT TRANSPORT STAGE #
########################


class MQTTTransportStageTestConfig(object):
    @pytest.fixture
    def cls_type(self):
        return pipeline_stages_mqtt.MQTTTransportStage

    @pytest.fixture
    def init_kwargs(self, mocker):
        return {}

    @pytest.fixture
    def stage(self, mocker, cls_type, init_kwargs):
        stage = cls_type(**init_kwargs)
        stage.pipeline_root = pipeline_stages_base.PipelineRootStage(
            pipeline_configuration=mocker.MagicMock()
        )
        stage.send_op_down = mocker.MagicMock()
        stage.send_event_up = mocker.MagicMock()
        return stage


class MQTTTransportInstantiationTests(MQTTTransportStageTestConfig):
    @pytest.mark.it("Initializes 'sas_token' attribute as None")
    def test_sas_token(self, cls_type, init_kwargs):
        stage = cls_type(**init_kwargs)
        assert stage.sas_token is None

    @pytest.mark.it("Initializes 'transport' attribute as None")
    def test_transport(self, cls_type, init_kwargs):
        stage = cls_type(**init_kwargs)
        assert stage.transport is None

    @pytest.mark.it("Initializes with no pending connection operation")
    def test_pending_op(self, cls_type, init_kwargs):
        stage = cls_type(**init_kwargs)
        assert stage._pending_connection_op is None


pipeline_stage_test.add_base_pipeline_stage_tests(
    test_module=this_module,
    stage_class_under_test=pipeline_stages_mqtt.MQTTTransportStage,
    stage_test_config_class=MQTTTransportStageTestConfig,
    extended_stage_instantiation_test_class=MQTTTransportInstantiationTests,
)


@pytest.mark.describe(
    "MQTTTransportStage - .run_op() -- Called with SetMQTTConnectionArgsOperation"
)
class TestMQTTTransportStageRunOpCalledWithSetMQTTConnectionArgsOperation(
    MQTTTransportStageTestConfig, StageRunOpTestBase
):
    @pytest.fixture
    def op(self, mocker):
        return pipeline_ops_mqtt.SetMQTTConnectionArgsOperation(
            client_id="fake_client_id",
            hostname="fake_hostname",
            username="fake_username",
            ca_cert="fake_ca_cert",
            client_cert="fake_client_cert",
            sas_token="fake_sas_token",
            callback=mocker.MagicMock(),
        )

    @pytest.mark.it("Stores the sas_token operation in the 'sas_token' attribute of the stage")
    def test_stores_data(self, stage, op, mocker, mock_transport):
        stage.run_op(op)
        assert stage.sas_token == op.sas_token

    # TODO: Should probably remove the requirement to set it on the root. This seems only needed by Horton
    @pytest.mark.it(
        "Creates an MQTTTransport object and sets it as the 'transport' attribute of the stage (and on the pipeline root)"
    )
    @pytest.mark.parametrize(
        "websockets",
        [
            pytest.param(True, id="Pipeline Configured for Websockets"),
            pytest.param(False, id="Pipeline NOT Configured for Websockets"),
        ],
    )
    def test_creates_transport(self, mocker, stage, op, websockets, mock_transport):
        # Configure websockets
        stage.pipeline_root.pipeline_configuration.websockets = websockets

        assert stage.transport is None

        stage.run_op(op)

        assert mock_transport.call_count == 1
        assert mock_transport.call_args == mocker.call(
            client_id=op.client_id,
            hostname=op.hostname,
            username=op.username,
            ca_cert=op.ca_cert,
            x509_cert=op.client_cert,
            websockets=websockets,
        )
        assert stage.transport is mock_transport.return_value

    @pytest.mark.it("Sets event handlers on the newly created MQTTTransport")
    def test_sets_transport_handlers(self, mocker, stage, op, mock_transport):
        stage.run_op(op)

        assert stage.transport.on_mqtt_disconnected_handler == stage._on_mqtt_disconnected
        assert stage.transport.on_mqtt_connected_handler == stage._on_mqtt_connected
        assert (
            stage.transport.on_mqtt_connection_failure_handler == stage._on_mqtt_connection_failure
        )
        assert stage.transport.on_mqtt_message_received_handler == stage._on_mqtt_message_received

    # CT-TODO: does this even need to be happening in this stage? Shouldn't this be part of init?
    @pytest.mark.it("Sets the stage's pending connection operation to None")
    def test_pending_conn_op(self, stage, op, mock_transport):
        stage.run_op(op)
        assert stage._pending_connection_op is None

    @pytest.mark.it("Completes the operation with success, upon successful execution")
    def test_succeeds(self, mocker, stage, op, mock_transport):
        assert not op.completed
        stage.run_op(op)
        assert op.completed


# NOTE: The MQTTTransport object is not instantiated upon instantiation of the MQTTTransportStage.
# It is only added once the SetMQTTConnectionArgsOperation runs.
# The lifecycle of the MQTTTransportStage is as follows:
#   1. Instantiate the stage
#   2. Configure the stage with a SetMQTTConnectionArgsOperation
#   3. Run any other desired operations.
#
# This is to say, no operation should be running before SetMQTTConnectionArgsOperation.
# Thus, for the following tests, we will assume that the MQTTTransport has already been created,
# and as such, the stage fixture used will have already have one.
class MQTTTransportStageTestConfigComplex(MQTTTransportStageTestConfig):
    @pytest.fixture
    def stage(self, mocker, cls_type, init_kwargs, mock_transport):
        stage = cls_type(**init_kwargs)
        stage.pipeline_root = pipeline_stages_base.PipelineRootStage(
            pipeline_configuration=mocker.MagicMock()
        )
        stage.send_op_down = mocker.MagicMock()
        stage.send_event_up = mocker.MagicMock()

        # Set up the Transport on the stage
        op = pipeline_ops_mqtt.SetMQTTConnectionArgsOperation(
            client_id="fake_client_id",
            hostname="fake_hostname",
            username="fake_username",
            ca_cert="fake_ca_cert",
            client_cert="fake_client_cert",
            sas_token="fake_sas_token",
            callback=mocker.MagicMock(),
        )
        stage.run_op(op)
        assert stage.transport is mock_transport.return_value

        return stage


@pytest.mark.describe("MQTTTransportStage - .run_op() -- Called with UpdateSasTokenOperation")
class TestMQTTTransportStageRunOpCalledWithUpdateSasTokenOperation(
    MQTTTransportStageTestConfigComplex, StageRunOpTestBase
):
    @pytest.fixture
    def op(self, mocker):
        return pipeline_ops_base.UpdateSasTokenOperation(
            sas_token="new_fake_sas_token", callback=mocker.MagicMock()
        )

    @pytest.mark.it(
        "Updates the 'sas_token' attribute to be the new value contained in the operation"
    )
    def test_updates_token(self, stage, op):
        assert stage.sas_token != op.sas_token
        stage.run_op(op)
        assert stage.sas_token == op.sas_token

    @pytest.mark.it("Completes the operation with success, upon successful execution")
    def test_complets_op(self, stage, op):
        assert not op.completed
        stage.run_op(op)
        assert op.completed


@pytest.mark.describe("MQTTTransportStage - .run_op() -- Called with ConnectOperation")
class TestMQTTTransportStageRunOpCalledWithConnectOperation(
    MQTTTransportStageTestConfigComplex, StageRunOpTestBase
):
    @pytest.fixture
    def op(self, mocker):
        return pipeline_ops_base.ConnectOperation(callback=mocker.MagicMock())

    @pytest.mark.it("Sets the operation as the stage's pending connection operation")
    def test_sets_pending_operation(self, stage, op):
        stage.run_op(op)
        assert stage._pending_connection_op is op

    @pytest.mark.it("Cancels any already pending connection operation")
    @pytest.mark.parametrize(
        "pending_connection_op",
        [
            pytest.param(
                pipeline_ops_base.ConnectOperation(callback=fake_callback),
                id="Pending ConnectOperation",
            ),
            pytest.param(
                pipeline_ops_base.ReauthorizeConnectionOperation(callback=fake_callback),
                id="Pending ReauthorizeConnectOperation",
            ),
            pytest.param(
                pipeline_ops_base.DisconnectOperation(callback=fake_callback),
                id="Pending DisconnectOperation",
            ),
        ],
    )
    def test_pending_operation_cancelled(self, mocker, stage, op, pending_connection_op):
        # Set up a pending op
        stage._pending_connection_op = pending_connection_op
        assert not pending_connection_op.completed

        # Run the connect op
        stage.run_op(op)

        # Operation has been completed, with an OperationCancelled exception set indicating early cancellation
        assert pending_connection_op.completed
        assert type(pending_connection_op.error) is pipeline_exceptions.OperationCancelled

        # New operation is now the pending operation
        assert stage._pending_connection_op is op

    @pytest.mark.it("Performs an MQTT connect via the MQTTTransport")
    def test_mqtt_connect(self, mocker, stage, op):
        stage.run_op(op)
        assert stage.transport.connect.call_count == 1
        assert stage.transport.connect.call_args == mocker.call(password=stage.sas_token)

    @pytest.mark.it(
        "Completes the operation unsucessfully if there is a failure connecting via the MQTTTransport, using the error raised by the MQTTTransport"
    )
    def test_fails_operation(self, mocker, stage, op, arbitrary_exception):
        stage.transport.connect.side_effect = arbitrary_exception
        stage.run_op(op)
        assert op.completed
        assert op.error is arbitrary_exception

    @pytest.mark.it(
        "Resets the stage's pending connection operation to None, if there is a failure connecting via the MQTTTransport"
    )
    def test_clears_pending_op_on_failure(self, mocker, stage, op, arbitrary_exception):
        stage.transport.connect.side_effect = arbitrary_exception
        stage.run_op(op)
        assert stage._pending_connection_op is None


@pytest.mark.describe(
    "MQTTTransportStage - .run_op() -- Called with ReauthorizeConnectionOperation"
)
class TestMQTTTransportStageRunOpCalledWithReauthorizeConnectionOperation(
    MQTTTransportStageTestConfigComplex, StageRunOpTestBase
):
    @pytest.fixture
    def op(self, mocker):
        return pipeline_ops_base.ReauthorizeConnectionOperation(callback=mocker.MagicMock())

    @pytest.mark.it("Sets the operation as the stage's pending connection operation")
    def test_sets_pending_operation(self, stage, op):
        stage.run_op(op)
        assert stage._pending_connection_op is op

    @pytest.mark.it("Cancels any already pending connection operation")
    @pytest.mark.parametrize(
        "pending_connection_op",
        [
            pytest.param(
                pipeline_ops_base.ConnectOperation(callback=fake_callback),
                id="Pending ConnectOperation",
            ),
            pytest.param(
                pipeline_ops_base.ReauthorizeConnectionOperation(callback=fake_callback),
                id="Pending ReauthorizeConnectionOperation",
            ),
            pytest.param(
                pipeline_ops_base.DisconnectOperation(callback=fake_callback),
                id="Pending DisconnectOperation",
            ),
        ],
    )
    def test_pending_operation_cancelled(self, mocker, stage, op, pending_connection_op):
        # Set up a pending op
        stage._pending_connection_op = pending_connection_op
        assert not pending_connection_op.completed

        # Run the connect op
        stage.run_op(op)

        # Operation has been completed, with an OperationCancelled exception set indicating early cancellation
        assert pending_connection_op.completed
        assert type(pending_connection_op.error) is pipeline_exceptions.OperationCancelled

        # New operation is now the pending operation
        assert stage._pending_connection_op is op

    @pytest.mark.it("Performs an MQTT reconnect via the MQTTTransport")
    def test_mqtt_connect(self, mocker, stage, op):
        stage.run_op(op)
        assert stage.transport.reauthorize_connection.call_count == 1
        assert stage.transport.reauthorize_connection.call_args == mocker.call(
            password=stage.sas_token
        )

    @pytest.mark.it(
        "Completes the operation unsucessfully if there is a failure reconnecting via the MQTTTransport, using the error raised by the MQTTTransport"
    )
    def test_fails_operation(self, mocker, stage, op, arbitrary_exception):
        stage.transport.reauthorize_connection.side_effect = arbitrary_exception
        stage.run_op(op)
        assert op.completed
        assert op.error is arbitrary_exception

    @pytest.mark.it(
        "Resets the stage's pending connection operation to None, if there is a failure reconnecting via the MQTTTransport"
    )
    def test_clears_pending_op_on_failure(self, mocker, stage, op, arbitrary_exception):
        stage.transport.reauthorize_connection.side_effect = arbitrary_exception
        stage.run_op(op)
        assert stage._pending_connection_op is None


@pytest.mark.describe("MQTTTransportStage - .run_op() -- Called with DisconnectOperation")
class TestMQTTTransportStageRunOpCalledWithDisconnectOperation(
    MQTTTransportStageTestConfigComplex, StageRunOpTestBase
):
    @pytest.fixture
    def op(self, mocker):
        return pipeline_ops_base.DisconnectOperation(callback=mocker.MagicMock())

    @pytest.mark.it("Sets the operation as the stage's pending connection operation")
    def test_sets_pending_operation(self, stage, op):
        stage.run_op(op)
        assert stage._pending_connection_op is op

    @pytest.mark.it("Cancels any already pending connection operation")
    @pytest.mark.parametrize(
        "pending_connection_op",
        [
            pytest.param(
                pipeline_ops_base.ConnectOperation(callback=fake_callback),
                id="Pending ConnectOperation",
            ),
            pytest.param(
                pipeline_ops_base.ReauthorizeConnectionOperation(callback=fake_callback),
                id="Pending ReauthorizeConnectionOperation",
            ),
            pytest.param(
                pipeline_ops_base.DisconnectOperation(callback=fake_callback),
                id="Pending DisconnectOperation",
            ),
        ],
    )
    def test_pending_operation_cancelled(self, mocker, stage, op, pending_connection_op):
        # Set up a pending op
        stage._pending_connection_op = pending_connection_op
        assert not pending_connection_op.completed

        # Run the connect op
        stage.run_op(op)

        # Operation has been completed, with an OperationCancelled exception set indicating early cancellation
        assert pending_connection_op.completed
        assert type(pending_connection_op.error) is pipeline_exceptions.OperationCancelled

        # New operation is now the pending operation
        assert stage._pending_connection_op is op

    @pytest.mark.it("Performs an MQTT disconnect via the MQTTTransport")
    def test_mqtt_connect(self, mocker, stage, op):
        stage.run_op(op)
        assert stage.transport.disconnect.call_count == 1
        assert stage.transport.disconnect.call_args == mocker.call()

    @pytest.mark.it(
        "Completes the operation unsucessfully if there is a failure disconnecting via the MQTTTransport, using the error raised by the MQTTTransport"
    )
    def test_fails_operation(self, mocker, stage, op, arbitrary_exception):
        stage.transport.disconnect.side_effect = arbitrary_exception
        stage.run_op(op)
        assert op.completed
        assert op.error is arbitrary_exception

    @pytest.mark.it(
        "Resets the stage's pending connection operation to None, if there is a failure disconnecting via the MQTTTransport"
    )
    def test_clears_pending_op_on_failure(self, mocker, stage, op, arbitrary_exception):
        stage.transport.disconnect.side_effect = arbitrary_exception
        stage.run_op(op)
        assert stage._pending_connection_op is None


@pytest.mark.describe("MQTTTransportStage - .run_op() -- called with MQTTPublishOperation")
class TestMQTTTransportStageRunOpCalledWithMQTTPublishOperation(
    MQTTTransportStageTestConfigComplex, StageRunOpTestBase
):
    @pytest.fixture
    def op(self, mocker):
        return pipeline_ops_mqtt.MQTTPublishOperation(
            topic="fake_topic", payload="fake_payload", callback=mocker.MagicMock()
        )

    @pytest.mark.it("Performs an MQTT publish via the MQTTTransport")
    def test_mqtt_publish(self, mocker, stage, op):
        stage.run_op(op)
        assert stage.transport.publish.call_count == 1
        assert stage.transport.publish.call_args == mocker.call(
            topic=op.topic, payload=op.payload, callback=mocker.ANY
        )

    @pytest.mark.it(
        "Sucessfully completes the operation, upon successful completion of the MQTT publish by the MQTTTransport"
    )
    def test_complete(self, mocker, stage, op):
        # Begin publish
        stage.run_op(op)

        assert not op.completed

        # Trigger publish completion
        stage.transport.publish.call_args[1]["callback"]()

        assert op.completed
        assert op.error is None


@pytest.mark.describe("MQTTTransportStage - .run_op() -- called with MQTTSubscribeOperation")
class TestMQTTTransportStageRunOpCalledWithMQTTSubscribeOperation(
    MQTTTransportStageTestConfigComplex, StageRunOpTestBase
):
    @pytest.fixture
    def op(self, mocker):
        return pipeline_ops_mqtt.MQTTSubscribeOperation(
            topic="fake_topic", callback=mocker.MagicMock()
        )

    @pytest.mark.it("Performs an MQTT subscribe via the MQTTTransport")
    def test_mqtt_publish(self, mocker, stage, op):
        stage.run_op(op)
        assert stage.transport.subscribe.call_count == 1
        assert stage.transport.subscribe.call_args == mocker.call(
            topic=op.topic, callback=mocker.ANY
        )

    @pytest.mark.it(
        "Sucessfully completes the operation, upon successful completion of the MQTT subscribe by the MQTTTransport"
    )
    def test_complete(self, mocker, stage, op):
        # Begin subscribe
        stage.run_op(op)

        assert not op.completed

        # Trigger subscribe completion
        stage.transport.subscribe.call_args[1]["callback"]()

        assert op.completed
        assert op.error is None


@pytest.mark.describe("MQTTTransportStage - .run_op() -- called with MQTTUnsubscribeOperation")
class TestMQTTTransportStageRunOpCalledWithMQTTUnsubscribeOperation(
    MQTTTransportStageTestConfigComplex, StageRunOpTestBase
):
    @pytest.fixture
    def op(self, mocker):
        return pipeline_ops_mqtt.MQTTUnsubscribeOperation(
            topic="fake_topic", callback=mocker.MagicMock()
        )

    @pytest.mark.it("Performs an MQTT unsubscribe via the MQTTTransport")
    def test_mqtt_publish(self, mocker, stage, op):
        stage.run_op(op)
        assert stage.transport.unsubscribe.call_count == 1
        assert stage.transport.unsubscribe.call_args == mocker.call(
            topic=op.topic, callback=mocker.ANY
        )

    @pytest.mark.it(
        "Successfully completes the operation upon successful completion of the MQTT unsubscribe by the MQTTTransport"
    )
    def test_complete(self, mocker, stage, op):
        # Begin unsubscribe
        stage.run_op(op)

        assert not op.completed

        # Trigger unsubscribe completion
        stage.transport.unsubscribe.call_args[1]["callback"]()

        assert op.completed
        assert op.error is None


# NOTE: This is not something that should ever happen in correct program flow
# There should be no operations that make it to the MQTTTransportStage that are not handled by it
@pytest.mark.describe("MQTTTransportStage - .run_op() -- called with arbitrary other operation")
class TestMQTTTransportStageRunOpCalledWithArbitraryOperation(
    MQTTTransportStageTestConfigComplex, StageRunOpTestBase
):
    @pytest.fixture
    def op(self, arbitrary_op):
        return arbitrary_op

    @pytest.mark.it("Sends the operation down")
    def test_sends_op_down(self, mocker, stage, op):
        stage.run_op(op)
        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(op)


@pytest.mark.describe("MQTTTransportStage - EVENT: MQTT message received")
class TestMQTTTransportStageProtocolClientEvents(MQTTTransportStageTestConfigComplex):
    @pytest.mark.it("Sends an IncomingMQTTMessageEvent event up the pipeline")
    def test_incoming_message_handler(self, stage, mocker):
        # Trigger MQTT message received
        stage.transport.on_mqtt_message_received_handler(topic="fake_topic", payload="fake_payload")

        assert stage.send_event_up.call_count == 1
        event = stage.send_event_up.call_args[0][0]
        assert isinstance(event, pipeline_events_mqtt.IncomingMQTTMessageEvent)

    @pytest.mark.it("Passes topic and payload as part of the IncomingMQTTMessageEvent")
    def test_verify_incoming_message_attributes(self, stage, mocker):
        fake_topic = "fake_topic"
        fake_payload = "fake_payload"

        # Trigger MQTT message received
        stage.transport.on_mqtt_message_received_handler(topic=fake_topic, payload=fake_payload)

        event = stage.send_event_up.call_args[0][0]
        assert event.payload == fake_payload
        assert event.topic == fake_topic


@pytest.mark.describe("MQTTTransportStage - EVENT: MQTT connected")
class TestMQTTTransportStageOnConnected(MQTTTransportStageTestConfigComplex):
    @pytest.mark.it("Sends a ConnectedEvent up the pipeline")
    @pytest.mark.parametrize(
        "pending_connection_op",
        [
            pytest.param(None, id="No pending operation"),
            pytest.param(pipeline_ops_base.ConnectOperation(1), id="Pending ConnectOperation"),
            pytest.param(
                pipeline_ops_base.ReauthorizeConnectionOperation(1),
                id="Pending ReauthorizeConnectionOperation",
            ),
            pytest.param(
                pipeline_ops_base.DisconnectOperation(1), id="Pending DisconnectOperation"
            ),
        ],
    )
    def test_sends_event_up(self, stage, pending_connection_op):
        stage._pending_connection_op = pending_connection_op
        # Trigger connect completion
        stage.transport.on_mqtt_connected_handler()

        assert stage.send_event_up.call_count == 1
        connect_event = stage.send_event_up.call_args[0][0]
        assert isinstance(connect_event, pipeline_events_base.ConnectedEvent)

    @pytest.mark.it("Completes a pending ConnectOperation successfully")
    def test_completes_pending_connect_op(self, mocker, stage):
        # Set a pending connect operation
        op = pipeline_ops_base.ConnectOperation(callback=mocker.MagicMock())
        stage.run_op(op)
        assert not op.completed
        assert stage._pending_connection_op is op

        # Trigger connect completion
        stage.transport.on_mqtt_connected_handler()

        # Connect operation completed successfully
        assert op.completed
        assert op.error is None
        assert stage._pending_connection_op is None

    @pytest.mark.it("Completes a pending ReauthorizeConnectionOperation successfully")
    def test_completes_pending_reconnect_op(self, mocker, stage):
        # Set a pending reconnect operation
        op = pipeline_ops_base.ReauthorizeConnectionOperation(callback=mocker.MagicMock())
        stage.run_op(op)
        assert not op.completed
        assert stage._pending_connection_op is op

        # Trigger connect completion
        stage.transport.on_mqtt_connected_handler()

        # Reconnect operation completed successfully
        assert op.completed
        assert op.error is None
        assert stage._pending_connection_op is None

    @pytest.mark.it(
        "Ignores a pending DisconnectOperation when the transport connected event fires"
    )
    def test_ignores_pending_disconnect_op(self, mocker, stage):
        # Set a pending disconnect operation
        op = pipeline_ops_base.DisconnectOperation(callback=mocker.MagicMock())
        stage.run_op(op)
        assert not op.completed
        assert stage._pending_connection_op is op

        # Trigger connect completion
        stage.transport.on_mqtt_connected_handler()

        # Disconnect operation was NOT completed
        assert not op.completed
        assert stage._pending_connection_op is op


@pytest.mark.describe("MQTTTransportStage - EVENT: MQTT connection failure")
class TestMQTTTransportStageOnConnectionFailure(MQTTTransportStageTestConfigComplex):
    @pytest.mark.it("Does not send any events up the pipeline")
    @pytest.mark.parametrize(
        "pending_connection_op",
        [
            pytest.param(None, id="No pending operation"),
            pytest.param(pipeline_ops_base.ConnectOperation(1), id="Pending ConnectOperation"),
            pytest.param(
                pipeline_ops_base.ReauthorizeConnectionOperation(1),
                id="Pending ReauthorizeConnectionOperation",
            ),
            pytest.param(
                pipeline_ops_base.DisconnectOperation(1), id="Pending DisconnectOperation"
            ),
        ],
    )
    def test_does_not_send_event(self, mocker, stage, pending_connection_op, arbitrary_exception):
        stage._pending_connection_op = pending_connection_op

        # Trigger connection failure with an arbitrary cause
        stage.transport.on_mqtt_connection_failure_handler(arbitrary_exception)

        assert stage.send_event_up.call_count == 0

    @pytest.mark.it(
        "Completes a pending ConnectOperation unsuccessfully with the cause of connection failure as the error"
    )
    def test_fails_pending_connect_op(self, mocker, stage, arbitrary_exception):
        # Create a pending ConnectOperation
        op = pipeline_ops_base.ConnectOperation(callback=mocker.MagicMock())
        stage.run_op(op)
        assert not op.completed
        assert stage._pending_connection_op is op

        # Trigger connection failure with an arbitrary cause
        stage.transport.on_mqtt_connection_failure_handler(arbitrary_exception)

        assert op.completed
        assert op.error is arbitrary_exception
        assert stage._pending_connection_op is None

    @pytest.mark.it(
        "Completes a pending ReauthorizeConnectionOperation unsuccessfully with the cause of connection failure as the error"
    )
    def test_fails_pending_reconnect_op(self, mocker, stage, arbitrary_exception):
        # Create a pending ReauthorizeConnectionOperation
        op = pipeline_ops_base.ReauthorizeConnectionOperation(callback=mocker.MagicMock())
        stage.run_op(op)
        assert not op.completed
        assert stage._pending_connection_op is op

        # Trigger connection failure with an arbitrary cause
        stage.transport.on_mqtt_connection_failure_handler(arbitrary_exception)

        assert op.completed
        assert op.error is arbitrary_exception
        assert stage._pending_connection_op is None

    @pytest.mark.it("Ignores a pending DisconnectOperation, and does not complete it")
    def test_ignores_pending_disconnect_op(self, mocker, stage, arbitrary_exception):
        # Create a pending DisconnectOperation
        op = pipeline_ops_base.DisconnectOperation(callback=mocker.MagicMock())
        stage.run_op(op)
        assert not op.completed
        assert stage._pending_connection_op is op

        # Trigger connection failure with an arbitrary cause
        stage.transport.on_mqtt_connection_failure_handler(arbitrary_exception)

        # Assert nothing changed about the operation
        assert not op.completed
        assert stage._pending_connection_op is op

    @pytest.mark.it(
        "Triggers the background exception handler (with error cause) when the connection failure is unexpected"
    )
    @pytest.mark.parametrize(
        "pending_connection_op",
        [
            pytest.param(None, id="No pending operation"),
            pytest.param(
                pipeline_ops_base.DisconnectOperation(callback=fake_callback),
                id="Pending DisconnectOperation",
            ),
        ],
    )
    def test_unexpected_connection_failure(
        self, mocker, stage, arbitrary_exception, pending_connection_op
    ):
        # A connection failure is unexpected if there is not a pending Connect/ReauthorizeConnection operation
        # i.e. "Why did we get a connection failure? We weren't even trying to connect!"
        mock_handler = mocker.patch.object(handle_exceptions, "handle_background_exception")
        stage._pending_connection_operation = pending_connection_op

        # Trigger connection failure with arbitrary cause
        stage.transport.on_mqtt_connection_failure_handler(arbitrary_exception)

        # Background exception handler has been called
        assert mock_handler.call_count == 1
        assert mock_handler.call_args == mocker.call(arbitrary_exception)


@pytest.mark.describe("MQTTTransportStage - EVENT: MQTT disconnected")
class TestMQTTTransportStageOnDisconnected(MQTTTransportStageTestConfigComplex):
    @pytest.fixture(params=[False, True], ids=["No error cause", "With error cause"])
    def cause(self, request, arbitrary_exception):
        if request.param:
            return arbitrary_exception
        else:
            return None

    @pytest.mark.it("Sends a DisconnectedEvent up the pipeline")
    @pytest.mark.parametrize(
        "pending_connection_op",
        [
            pytest.param(None, id="No pending operation"),
            pytest.param(
                pipeline_ops_base.ConnectOperation(callback=fake_callback),
                id="Pending ConnectOperation",
            ),
            pytest.param(
                pipeline_ops_base.ReauthorizeConnectionOperation(callback=fake_callback),
                id="Pending ReauthorizeConnectionOperation",
            ),
            pytest.param(
                pipeline_ops_base.DisconnectOperation(callback=fake_callback),
                id="Pending DisconnectOperation",
            ),
        ],
    )
    def test_disconnected_handler(self, stage, pending_connection_op, cause):
        stage._pending_connection_op = pending_connection_op
        assert stage.send_event_up.call_count == 0

        # Trigger disconnect
        stage.transport.on_mqtt_disconnected_handler(cause)

        assert stage.send_event_up.call_count == 1
        event = stage.send_event_up.call_args[0][0]
        assert isinstance(event, pipeline_events_base.DisconnectedEvent)

    @pytest.mark.it("Completes a pending DisconnectOperation successfully")
    def test_compltetes_pending_disconnect_op(self, mocker, stage, cause):
        # Create a pending DisconnectOperation
        op = pipeline_ops_base.DisconnectOperation(callback=mocker.MagicMock())
        stage.run_op(op)
        assert not op.completed
        assert stage._pending_connection_op is op

        # Trigger disconnect
        stage.transport.on_mqtt_disconnected_handler(cause)

        assert op.completed
        assert op.error is None

    @pytest.mark.it(
        "Swallows the exception that caused the disconnect, if there is a pending DisconnectOperation"
    )
    def test_completes_pending_disconnect_op_with_error(self, mocker, stage, arbitrary_exception):
        mock_swallow = mocker.patch.object(handle_exceptions, "swallow_unraised_exception")

        # Create a pending DisconnectOperation
        op = pipeline_ops_base.DisconnectOperation(callback=mocker.MagicMock())
        stage.run_op(op)
        assert not op.completed
        assert stage._pending_connection_op is op

        # Trigger disconnect with arbitrary cause
        stage.transport.on_mqtt_disconnected_handler(arbitrary_exception)

        # Exception swallower was called
        assert mock_swallow.call_count == 1
        assert mock_swallow.call_args == mocker.call(arbitrary_exception, log_msg=mocker.ANY)

    @pytest.mark.it(
        "Completes (unsuccessfully) a pending operation that is NOT a DisconnectOperation, with the cause of the disconnection set as the error, if there is a cause provided"
    )
    @pytest.mark.parametrize(
        "pending_connection_op",
        [
            pytest.param(
                pipeline_ops_base.ConnectOperation(callback=fake_callback),
                id="Pending ConnectOperation",
            ),
            pytest.param(
                pipeline_ops_base.ReauthorizeConnectionOperation(callback=fake_callback),
                id="Pending ReauthorizeConnectionOperation",
            ),
        ],
    )
    def test_comletes_with_cause_as_error_if_cause(
        self, mocker, stage, pending_connection_op, arbitrary_exception
    ):
        stage._pending_connection_op = pending_connection_op
        assert not pending_connection_op.completed

        # Trigger disconnect with arbitrary cause
        stage.transport.on_mqtt_disconnected_handler(arbitrary_exception)

        assert pending_connection_op.completed
        assert pending_connection_op.error is arbitrary_exception

    @pytest.mark.it(
        "Completes (unsuccessfully) a pending operation that is NOT a DisconnectOperation with a ConnectionDroppedError if no cause is provided for the disconnection"
    )
    @pytest.mark.parametrize(
        "pending_connection_op",
        [
            pytest.param(
                pipeline_ops_base.ConnectOperation(callback=fake_callback),
                id="Pending ConnectOperation",
            ),
            pytest.param(
                pipeline_ops_base.ReauthorizeConnectionOperation(callback=fake_callback),
                id="Pending ReauthorizeConnectionOperation",
            ),
        ],
    )
    def test_comletes_with_connection_dropped_error_as_error_if_no_cause(
        self, mocker, stage, pending_connection_op, arbitrary_exception
    ):
        stage._pending_connection_op = pending_connection_op
        assert not pending_connection_op.completed

        # Trigger disconnect with no cause
        stage.transport.on_mqtt_disconnected_handler()

        assert pending_connection_op.completed
        assert isinstance(pending_connection_op.error, transport_exceptions.ConnectionDroppedError)

    @pytest.mark.it(
        "Sends a ConnectionDroppedError to the background exception handler, if there is no pending operation when a disconnection occurs"
    )
    def test_no_pending_op(self, mocker, stage, cause):
        mock_handler = mocker.patch.object(handle_exceptions, "handle_background_exception")
        assert stage._pending_connection_op is None

        # Trigger disconnect
        stage.transport.on_mqtt_disconnected_handler(cause)

        assert mock_handler.call_count == 1
        exception = mock_handler.call_args[0][0]
        assert isinstance(exception, transport_exceptions.ConnectionDroppedError)
        assert exception.__cause__ is cause

    @pytest.mark.it("Clears any pending operation on the stage")
    @pytest.mark.parametrize(
        "pending_connection_op",
        [
            pytest.param(None, id="No pending operation"),
            pytest.param(
                pipeline_ops_base.ConnectOperation(callback=fake_callback),
                id="Pending ConnectOperation",
            ),
            pytest.param(
                pipeline_ops_base.ReauthorizeConnectionOperation(callback=fake_callback),
                id="Pending ReauthorizeConnectionOperation",
            ),
            pytest.param(
                pipeline_ops_base.DisconnectOperation(callback=fake_callback),
                id="Pending DisconnectOperation",
            ),
        ],
    )
    def test_clears_pending(self, mocker, stage, pending_connection_op, cause):
        stage._pending_connection_op = pending_connection_op

        # Trigger disconnect
        stage.transport.on_mqtt_disconnected_handler(cause)

        assert stage._pending_connection_op is None
