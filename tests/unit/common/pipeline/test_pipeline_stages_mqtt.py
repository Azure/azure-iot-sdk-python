# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import logging
import pytest
import sys
import threading
from azure.iot.device.common import transport_exceptions, handle_exceptions
from azure.iot.device.common.pipeline import (
    pipeline_ops_base,
    pipeline_ops_mqtt,
    pipeline_events_base,
    pipeline_events_mqtt,
    pipeline_stages_mqtt,
    pipeline_exceptions,
)
from tests.unit.common.pipeline.helpers import StageRunOpTestBase
from tests.unit.common.pipeline import pipeline_stage_test

this_module = sys.modules[__name__]
logging.basicConfig(level=logging.DEBUG)
pytestmark = pytest.mark.usefixtures("fake_pipeline_thread")

logging.getLogger("azure.iot.device.common").setLevel(level=logging.DEBUG)

###################
# COMMON FIXTURES #
###################


@pytest.fixture
def mock_transport(mocker):
    return mocker.patch(
        "azure.iot.device.common.pipeline.pipeline_stages_mqtt.MQTTTransport", autospec=True
    )


@pytest.fixture
def mock_timer(mocker):
    return mocker.patch.object(threading, "Timer")


# Not a fixture, but used in parametrization
def fake_callback(op, error):
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
    def stage(self, mocker, cls_type, init_kwargs, nucleus):
        stage = cls_type(**init_kwargs)
        stage.nucleus = nucleus
        stage.nucleus.pipeline_configuration.hostname = "some.fake-host.name.com"
        stage.send_op_down = mocker.MagicMock()
        stage.send_event_up = mocker.MagicMock()
        mocker.spy(stage, "report_background_exception")
        return stage


class MQTTTransportInstantiationTests(MQTTTransportStageTestConfig):
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


@pytest.mark.describe("MQTTTransportStage - .run_op() -- Called with InitializePipelineOperation")
class TestMQTTTransportStageRunOpCalledWithInitializePipelineOperation(
    MQTTTransportStageTestConfig, StageRunOpTestBase
):
    @pytest.fixture
    def op(self, mocker):
        op = pipeline_ops_base.InitializePipelineOperation(callback=mocker.MagicMock())
        # These values are patched onto the op in a previous stage
        op.client_id = "fake_client_id"
        op.username = "fake_username"
        return op

    @pytest.mark.it(
        "Creates an MQTTTransport object and sets it as the 'transport' attribute of the stage"
    )
    @pytest.mark.parametrize(
        "websockets",
        [
            pytest.param(True, id="Pipeline configured for websockets"),
            pytest.param(False, id="Pipeline NOT configured for websockets"),
        ],
    )
    @pytest.mark.parametrize(
        "cipher",
        [
            pytest.param("DHE-RSA-AES128-SHA", id="Pipeline configured for custom cipher"),
            pytest.param(
                "DHE-RSA-AES128-SHA:DHE-RSA-AES256-SHA:ECDHE-ECDSA-AES128-GCM-SHA256",
                id="Pipeline configured for multiple custom ciphers",
            ),
            pytest.param("", id="Pipeline NOT configured for custom cipher(s)"),
        ],
    )
    @pytest.mark.parametrize(
        "proxy_options",
        [
            pytest.param("FAKE-PROXY", id="Proxy present"),
            pytest.param(None, id="Proxy None"),
            pytest.param("", id="Proxy Absent"),
        ],
    )
    @pytest.mark.parametrize(
        "gateway_hostname",
        [
            pytest.param("fake.gateway.hostname.com", id="Using Gateway Hostname"),
            pytest.param(None, id="Not using Gateway Hostname"),
        ],
    )
    @pytest.mark.parametrize(
        "keep_alive",
        [
            pytest.param(900, id="Pipeline configured for custom keep alive"),
            pytest.param(None, id="Pipeline NOT configured for custom keep alive"),
        ],
    )
    def test_creates_transport(
        self,
        mocker,
        stage,
        op,
        mock_transport,
        websockets,
        cipher,
        proxy_options,
        gateway_hostname,
        keep_alive,
    ):
        # Configure websockets & cipher & keep alive
        stage.nucleus.pipeline_configuration.websockets = websockets
        stage.nucleus.pipeline_configuration.cipher = cipher
        stage.nucleus.pipeline_configuration.proxy_options = proxy_options
        stage.nucleus.pipeline_configuration.gateway_hostname = gateway_hostname
        stage.nucleus.pipeline_configuration.keep_alive = keep_alive

        # NOTE: if more of this type of logic crops up, consider splitting this test up
        if stage.nucleus.pipeline_configuration.gateway_hostname:
            expected_hostname = stage.nucleus.pipeline_configuration.gateway_hostname
        else:
            expected_hostname = stage.nucleus.pipeline_configuration.hostname

        assert stage.transport is None

        stage.run_op(op)

        assert mock_transport.call_count == 1
        assert mock_transport.call_args == mocker.call(
            client_id=op.client_id,
            hostname=expected_hostname,
            username=op.username,
            server_verification_cert=stage.nucleus.pipeline_configuration.server_verification_cert,
            x509_cert=stage.nucleus.pipeline_configuration.x509,
            websockets=websockets,
            cipher=cipher,
            proxy_options=proxy_options,
            keep_alive=keep_alive,
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

    @pytest.mark.it("Sets the stage's pending connection operation to None")
    def test_pending_conn_op(self, mocker, stage, op, mock_transport):
        # NOTE: The pending connection operation ALREADY should be None, but we set it to None
        # again for safety here just in case. So this test is for an edge case.
        stage._pending_connection_op = mocker.MagicMock()
        stage.run_op(op)
        assert stage._pending_connection_op is None

    @pytest.mark.it("Completes the operation with success, upon successful execution")
    def test_succeeds(self, mocker, stage, op, mock_transport):
        assert not op.completed
        stage.run_op(op)
        assert op.completed


# NOTE: The MQTTTransport object is not instantiated upon instantiation of the MQTTTransportStage.
# It is only added once the InitializePipelineOperation runs.
# The lifecycle of the MQTTTransportStage is as follows:
#   1. Instantiate the stage
#   2. Configure the stage with an InitializePipelineOperation
#   3. Run any other desired operations.
#
# This is to say, no operation should be running before InitializePipelineOperation.
# Thus, for the following tests, we will assume that the MQTTTransport has already been created,
# and as such, the stage fixture used will have already have one.
class MQTTTransportStageTestConfigComplex(MQTTTransportStageTestConfig):
    @pytest.fixture
    def stage(self, mocker, cls_type, init_kwargs, nucleus, mock_transport):
        stage = cls_type(**init_kwargs)
        stage.nucleus = nucleus
        stage.send_op_down = mocker.MagicMock()
        stage.send_event_up = mocker.MagicMock()
        mocker.spy(stage, "report_background_exception")

        # Set up the Transport on the stage
        op = pipeline_ops_base.InitializePipelineOperation(callback=mocker.MagicMock())
        op.client_id = "fake_client_id"
        op.username = "fake_username"
        stage.run_op(op)

        assert stage.transport is mock_transport.return_value

        return stage


@pytest.mark.describe("MQTTTransportStage - .run_op() -- Called with ShutdownPipelineOperation")
class TestMQTTTransportStageRunOpCalledWithShutdownPipelineOperation(
    MQTTTransportStageTestConfigComplex, StageRunOpTestBase
):
    @pytest.fixture
    def op(self, mocker):
        return pipeline_ops_base.ShutdownPipelineOperation(callback=mocker.MagicMock())

    @pytest.mark.it("Performs a shutdown of the MQTTTransport")
    def test_transport_shutdown(self, mocker, stage, op):
        stage.run_op(op)
        assert stage.transport.shutdown.call_count == 1
        assert stage.transport.shutdown.call_args == mocker.call()

    @pytest.mark.it(
        "Completes the operation successfully if there is no error in executing the MQTTTransport shutdown"
    )
    def test_no_error(self, stage, op):
        stage.run_op(op)
        assert op.completed
        assert op.error is None

    @pytest.mark.it(
        "Completes the operation unsuccessfully (with error) if there was an error in executing the MQTTTransport shutdown"
    )
    def test_error_occurs(self, mocker, stage, op, arbitrary_exception):
        stage.transport.shutdown.side_effect = arbitrary_exception
        stage.run_op(op)
        assert op.completed
        assert op.error is arbitrary_exception


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

    @pytest.mark.it("Starts the connection watchdog")
    def test_starts_watchdog(self, mocker, stage, op, mock_timer):
        stage.run_op(op)

        assert mock_timer.call_count == 1
        assert mock_timer.call_args == mocker.call(60, mocker.ANY)
        assert mock_timer.return_value.daemon is True
        assert mock_timer.return_value.start.call_count == 1

    @pytest.mark.it(
        "Performs an MQTT connect via the MQTTTransport, using the PipelineNucleus' SasToken as a password, if using SAS-based authentication"
    )
    def test_mqtt_connect_sastoken(self, mocker, stage, op):
        assert stage.nucleus.pipeline_configuration.sastoken is not None
        stage.run_op(op)
        assert stage.transport.connect.call_count == 1
        assert stage.transport.connect.call_args == mocker.call(
            password=str(stage.nucleus.pipeline_configuration.sastoken)
        )

    @pytest.mark.it(
        "Performs an MQTT connect via the MQTTTransport, with no password, if NOT using SAS-based authentication"
    )
    def test_mqtt_connect_no_sastoken(self, mocker, stage, op):
        # no token
        stage.nucleus.pipeline_configuration.sastoken = None
        stage.run_op(op)
        assert stage.transport.connect.call_count == 1
        assert stage.transport.connect.call_args == mocker.call(password=None)

    @pytest.mark.it(
        "Completes the operation unsuccessfully if there is a failure connecting via the MQTTTransport, using the error raised by the MQTTTransport"
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

    @pytest.mark.it(
        "Leaves the watchdog running while waiting for the connect operation to complete"
    )
    def test_leaves_watchdog_running(self, mocker, stage, op, arbitrary_exception, mock_timer):
        stage.run_op(op)
        assert mock_timer.return_value.cancel.call_count == 0
        assert op.watchdog_timer is mock_timer.return_value

    @pytest.mark.it(
        "Cancels the connection watchdog if the MQTTTransport connect operation raises an exception"
    )
    def test_cancels_watchdog(self, mocker, stage, op, arbitrary_exception, mock_timer):
        stage.transport.connect.side_effect = arbitrary_exception
        stage.run_op(op)
        assert mock_timer.return_value.cancel.call_count == 1
        assert op.watchdog_timer is None


@pytest.mark.describe(
    "MQTTTransportStage - .run_op() -- Called with ReauthorizeConnectionOperation"
)
class TestMQTTTransportStageRunOpCalledWithReauthorizeConnectionOperation(
    MQTTTransportStageTestConfigComplex, StageRunOpTestBase
):
    @pytest.fixture
    def op(self, mocker):
        return pipeline_ops_base.ReauthorizeConnectionOperation(callback=mocker.MagicMock())

    @pytest.mark.it(
        "Spawns a new DisconnectOperation (configured as a soft disconnect) and runs it on the stage"
    )
    def test_disconnect(self, mocker, stage, op):
        original_run_op = stage.run_op
        mock_run_op = mocker.MagicMock()
        stage.run_op = mock_run_op

        original_run_op(op)

        assert mock_run_op.call_count == 1
        disconnect_op = mock_run_op.call_args[0][0]
        assert isinstance(disconnect_op, pipeline_ops_base.DisconnectOperation)
        assert disconnect_op.hard is False

        assert not op.completed

    @pytest.mark.it(
        "Spawns a new ConnectOperation and runs it on the stage upon completion of the DisconnectOperation"
    )
    @pytest.mark.parametrize(
        "successful_disconnect",
        [
            pytest.param(True, id="Disconnect Completed Successfully"),
            pytest.param(False, id="Disconnect Completed with Error"),
        ],
    )
    def test_connect(self, mocker, stage, op, successful_disconnect, arbitrary_exception):
        original_run_op = stage.run_op
        mock_run_op = mocker.MagicMock()
        stage.run_op = mock_run_op

        original_run_op(op)

        assert mock_run_op.call_count == 1
        disconnect_op = mock_run_op.call_args[0][0]
        assert isinstance(disconnect_op, pipeline_ops_base.DisconnectOperation)

        if successful_disconnect:
            error = None
        else:
            error = arbitrary_exception

        disconnect_op.complete(error=error)

        assert not op.completed

        assert mock_run_op.call_count == 2
        connect_op = mock_run_op.call_args[0][0]
        assert isinstance(connect_op, pipeline_ops_base.ConnectOperation)

        assert not op.completed

    @pytest.mark.it(
        "Completes the original ReauthorizeConnectionOperation upon completion of the ConnectOperation"
    )
    @pytest.mark.parametrize(
        "successful_connect",
        [
            pytest.param(True, id="Connect Completed Successfully"),
            pytest.param(False, id="Connect Completed with Error"),
        ],
    )
    def test_completion(self, mocker, stage, op, successful_connect, arbitrary_exception):
        original_run_op = stage.run_op
        mock_run_op = mocker.MagicMock()
        stage.run_op = mock_run_op

        original_run_op(op)

        assert mock_run_op.call_count == 1
        disconnect_op = mock_run_op.call_args[0][0]
        assert isinstance(disconnect_op, pipeline_ops_base.DisconnectOperation)

        disconnect_op.complete()

        assert not op.completed

        assert mock_run_op.call_count == 2
        connect_op = mock_run_op.call_args[0][0]
        assert isinstance(connect_op, pipeline_ops_base.ConnectOperation)

        assert not op.completed

        if successful_connect:
            error = None
        else:
            error = arbitrary_exception

        connect_op.complete(error=error)

        assert op.completed
        assert op.error is error


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

    @pytest.mark.it(
        "Performs an MQTT disconnect via the MQTTTransport, using the 'clear_inflight' option only if the operation is configured for a hard disconnect"
    )
    def test_mqtt_connect(self, mocker, stage, op):
        # Hard disconnect
        assert op.hard is True
        stage.run_op(op)
        assert stage.transport.disconnect.call_count == 1
        assert stage.transport.disconnect.call_args == mocker.call(clear_inflight=True)

        stage.transport.disconnect.reset_mock()

        # Soft disconnect
        op.hard = False
        stage.run_op(op)
        assert stage.transport.disconnect.call_count == 1
        assert stage.transport.disconnect.call_args == mocker.call(clear_inflight=False)

    @pytest.mark.it(
        "Completes the operation unsuccessfully if there is a failure disconnecting via the MQTTTransport, using the error raised by the MQTTTransport"
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
        "Successfully completes the operation, upon successful completion of the MQTT publish by the MQTTTransport"
    )
    def test_complete(self, mocker, stage, op):
        # Begin publish
        stage.run_op(op)

        assert not op.completed

        # Trigger publish completion
        stage.transport.publish.call_args[1]["callback"]()

        assert op.completed
        assert op.error is None

    @pytest.mark.it(
        "Completes the operation with an OperationCancelled error upon cancellation of the MQTT unsubscribe by the MQTTTransport"
    )
    def test_complete_with_cancel(self, mocker, stage, op):
        # Begin publish
        stage.run_op(op)

        assert not op.completed

        # Trigger publish cancellation
        stage.transport.publish.call_args[1]["callback"](cancelled=True)

        assert op.completed
        assert isinstance(op.error, pipeline_exceptions.OperationCancelled)

    @pytest.mark.it(
        "Completes the operation using the exception that was raised, if an exception was raised from the MQTTTransport"
    )
    def test_publish_error(self, stage, op, arbitrary_exception):
        stage.transport.publish.side_effect = arbitrary_exception

        stage.run_op(op)

        assert op.completed
        assert op.error is arbitrary_exception


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
        "Successfully completes the operation, upon successful completion of the MQTT subscribe by the MQTTTransport"
    )
    def test_complete(self, mocker, stage, op):
        # Begin subscribe
        stage.run_op(op)

        assert not op.completed

        # Trigger subscribe completion
        stage.transport.subscribe.call_args[1]["callback"]()

        assert op.completed
        assert op.error is None

    @pytest.mark.it(
        "Completes the operation with an OperationCancelled error upon cancellation of the MQTT unsubscribe by the MQTTTransport"
    )
    def test_complete_with_cancel(self, mocker, stage, op):
        # Begin unsubscribe
        stage.run_op(op)

        assert not op.completed

        # Trigger subscribe cancellation
        stage.transport.subscribe.call_args[1]["callback"](cancelled=True)

        assert op.completed
        assert isinstance(op.error, pipeline_exceptions.OperationCancelled)

    @pytest.mark.it(
        "Completes the operation using the exception that was raised, if an exception was raised from the MQTTTransport"
    )
    def test_subscribe_error(self, stage, op, arbitrary_exception):
        stage.transport.subscribe.side_effect = arbitrary_exception

        stage.run_op(op)

        assert op.completed
        assert op.error is arbitrary_exception


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

    @pytest.mark.it(
        "Completes the operation with an OperationCancelled error upon cancellation of the MQTT unsubscribe by the MQTTTransport"
    )
    def test_complete_with_cancel(self, mocker, stage, op):
        # Begin unsubscribe
        stage.run_op(op)

        assert not op.completed

        # Trigger unsubscribe cancellation
        stage.transport.unsubscribe.call_args[1]["callback"](cancelled=True)

        assert op.completed
        assert isinstance(op.error, pipeline_exceptions.OperationCancelled)

    @pytest.mark.it(
        "Completes the operation using the exception that was raised, if an exception was raised from the MQTTTransport"
    )
    def test_publish_error(self, stage, op, arbitrary_exception):
        stage.transport.unsubscribe.side_effect = arbitrary_exception

        stage.run_op(op)

        assert op.completed
        assert op.error is arbitrary_exception


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


@pytest.mark.describe("MQTTTransportStage - OCCURRENCE: MQTT message received")
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


@pytest.mark.describe("MQTTTransportStage - OCCURRENCE: MQTT connected")
class TestMQTTTransportStageOnConnected(MQTTTransportStageTestConfigComplex):
    @pytest.mark.it("Sends a ConnectedEvent up the pipeline")
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

    @pytest.mark.it(
        "Does not complete  a pending DisconnectOperation when the transport connected event fires"
    )
    def test_does_not_complete_pending_disconnect_op(self, mocker, stage):
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

    @pytest.mark.it(
        "Cancels the connection watchdog if the pending operation is a ConnectOperation"
    )
    def test_cancels_watchdog_on_pending_connect(self, mocker, stage, mock_timer):
        # Set a pending connect operation
        op = pipeline_ops_base.ConnectOperation(callback=mocker.MagicMock())
        stage.run_op(op)

        # assert watchdog is running
        assert op.watchdog_timer is mock_timer.return_value
        assert op.watchdog_timer.start.call_count == 1

        # Trigger connect completion
        stage.transport.on_mqtt_connected_handler()

        # assert watchdog was cancelled
        assert op.watchdog_timer is None
        assert mock_timer.return_value.cancel.call_count == 1

    @pytest.mark.it(
        "Does not cancels the connection watchdog if the pending operation is DisconnectOperation because there is no connection watchdog"
    )
    def test_does_not_cancel_watchdog_on_pending_disconnect(self, mocker, stage, mock_timer):
        # Set a pending disconnect operation
        op = pipeline_ops_base.DisconnectOperation(callback=mocker.MagicMock())
        stage.run_op(op)

        # assert no timers are running
        assert mock_timer.return_value.start.call_count == 0

        # Trigger connect completion
        stage.transport.on_mqtt_connected_handler()

        # assert no timers are still running
        assert mock_timer.return_value.start.call_count == 0
        assert mock_timer.return_value.cancel.call_count == 0


@pytest.mark.describe("MQTTTransportStage - OCCURRENCE: MQTT connection failure")
class TestMQTTTransportStageOnConnectionFailure(MQTTTransportStageTestConfigComplex):
    @pytest.mark.it("Does not send any events up the pipeline")
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
        "Triggers the swallowed exception handler (with error cause) when the connection failure is unexpected"
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
        # A connection failure is unexpected if there is not a pending Connect operation
        # i.e. "Why did we get a connection failure? We weren't even trying to connect!"
        mock_handler = mocker.patch.object(handle_exceptions, "swallow_unraised_exception")
        stage._pending_connection_operation = pending_connection_op

        # Trigger connection failure with arbitrary cause
        stage.transport.on_mqtt_connection_failure_handler(arbitrary_exception)

        # swallow exception handler has been called
        assert mock_handler.call_count == 1
        assert mock_handler.call_args == mocker.call(
            arbitrary_exception, log_msg=mocker.ANY, log_lvl="info"
        )

    @pytest.mark.it(
        "Cancels the connection watchdog if the pending operation is a ConnectOperation"
    )
    def test_cancels_watchdog_on_pending_connect(
        self, mocker, stage, mock_timer, arbitrary_exception
    ):
        # Set a pending connect operation
        op = pipeline_ops_base.ConnectOperation(callback=mocker.MagicMock())
        stage.run_op(op)

        # assert watchdog is running
        assert op.watchdog_timer is mock_timer.return_value
        assert op.watchdog_timer.start.call_count == 1

        # Trigger connection failure with arbitrary cause
        stage.transport.on_mqtt_connection_failure_handler(arbitrary_exception)

        # assert watchdog was cancelled
        assert op.watchdog_timer is None
        assert mock_timer.return_value.cancel.call_count == 1

    @pytest.mark.it(
        "Does not cancels the connection watchdog if the pending operation is DisconnectOperation"
    )
    def test_does_not_cancel_watchdog_on_pending_disconnect(
        self, mocker, stage, mock_timer, arbitrary_exception
    ):
        # Set a pending disconnect operation
        op = pipeline_ops_base.DisconnectOperation(callback=mocker.MagicMock())
        stage.run_op(op)

        # assert no timers are running
        assert mock_timer.return_value.start.call_count == 0

        # Trigger connection failure with arbitrary cause
        stage.transport.on_mqtt_connection_failure_handler(arbitrary_exception)

        # assert no timers are still running
        assert mock_timer.return_value.start.call_count == 0
        assert mock_timer.return_value.cancel.call_count == 0


@pytest.mark.describe("MQTTTransportStage - OCCURRENCE: MQTT disconnected (Expected)")
class TestMQTTTransportStageOnDisconnectedExpected(MQTTTransportStageTestConfigComplex):
    @pytest.fixture(params=[False, True], ids=["No error cause", "With error cause"])
    def cause(self, request, arbitrary_exception):
        if request.param:
            return arbitrary_exception
        else:
            return None

    @pytest.fixture
    def pending_connection_op(self):
        return pipeline_ops_base.DisconnectOperation(callback=fake_callback)

    @pytest.mark.it("Sends a DisconnectedEvent up the pipeline")
    def test_disconnect_event_sent(self, stage, cause, pending_connection_op):
        stage._pending_connection_op = pending_connection_op
        assert stage.send_event_up.call_count == 0

        # Trigger disconnect
        stage.transport.on_mqtt_disconnected_handler(cause)

        assert stage.send_event_up.call_count == 1
        event = stage.send_event_up.call_args[0][0]
        assert isinstance(event, pipeline_events_base.DisconnectedEvent)

    @pytest.mark.it("Swallows the exception that caused the disconnect if the cause is specified")
    def test_error_swallowed(self, mocker, stage, arbitrary_exception, pending_connection_op):
        mock_swallow = mocker.patch.object(handle_exceptions, "swallow_unraised_exception")
        stage._pending_connection_op = pending_connection_op

        # Trigger disconnect with arbitrary cause
        stage.transport.on_mqtt_disconnected_handler(arbitrary_exception)

        # Exception swallower was called
        assert mock_swallow.call_count == 1
        assert mock_swallow.call_args == mocker.call(arbitrary_exception, log_msg=mocker.ANY)

    @pytest.mark.it(
        "Completes the pending DisconnectOperation successfully and removes its pending status"
    )
    def test_disconnect_op_completed(self, mocker, stage, cause, pending_connection_op):
        stage._pending_connection_op = pending_connection_op
        assert not pending_connection_op.completed
        assert pending_connection_op.error is None

        # Trigger disconnect
        stage.transport.on_mqtt_disconnected_handler(cause)

        assert stage._pending_connection_op is None
        assert pending_connection_op.completed
        assert pending_connection_op.error is None


@pytest.mark.describe(
    "MQTTTransportStage - OCCURRENCE: MQTT disconnected (Unexpected - pending ConnectionOperation)"
)
class TestMQTTTransportStageOnDisconnectedUnexpectedWithPendingConnectOp(
    MQTTTransportStageTestConfigComplex
):
    @pytest.fixture(params=[False, True], ids=["No error cause", "With error cause"])
    def cause(self, request, arbitrary_exception):
        if request.param:
            return arbitrary_exception
        else:
            return None

    @pytest.fixture
    def pending_connection_op(self):
        return pipeline_ops_base.ConnectOperation(callback=fake_callback)

    @pytest.mark.it("Sends a DisconnectedEvent up the pipeline")
    def test_disconnect_event_sent(self, stage, cause, pending_connection_op):
        stage._pending_connection_op = pending_connection_op
        assert stage.send_event_up.call_count == 0

        # Trigger disconnect
        stage.transport.on_mqtt_disconnected_handler(cause)

        assert stage.send_event_up.call_count == 1
        event = stage.send_event_up.call_args[0][0]
        assert isinstance(event, pipeline_events_base.DisconnectedEvent)

    @pytest.mark.it(
        "Completes the pending ConnectOperation unsuccessfully with the cause of the disconnection set as the error, and removes its pending status, if the cause is specified"
    )
    def test_op_completed_with_cause(self, stage, arbitrary_exception, pending_connection_op):
        stage._pending_connection_op = pending_connection_op
        assert not pending_connection_op.completed
        assert pending_connection_op.error is None

        # Trigger disconnect with arbitrary cause
        stage.transport.on_mqtt_disconnected_handler(arbitrary_exception)

        assert stage._pending_connection_op is None
        assert pending_connection_op.completed
        assert pending_connection_op.error is arbitrary_exception

    @pytest.mark.it(
        "Completes the pending ConnectOperation unsuccessfully with a ConnectionDroppedError, and removes its pending status, if no cause is provided for the disconnection"
    )
    def test_op_completed_no_cause(self, stage, pending_connection_op):
        stage._pending_connection_op = pending_connection_op
        assert not pending_connection_op.completed
        assert pending_connection_op.error is None

        # Trigger disconnect with no cause
        stage.transport.on_mqtt_disconnected_handler()

        assert stage._pending_connection_op is None
        assert pending_connection_op.completed
        assert isinstance(pending_connection_op.error, transport_exceptions.ConnectionDroppedError)

    @pytest.mark.it("Cancels the connection watchdog")
    def test_cancels_watchdog(self, mocker, stage, mock_timer, cause, pending_connection_op):
        # Set a pending connect operation
        stage.run_op(pending_connection_op)

        # assert watchdog is running
        assert pending_connection_op.watchdog_timer is mock_timer.return_value
        assert pending_connection_op.watchdog_timer.start.call_count == 1

        # Trigger disconnect
        stage.transport.on_mqtt_disconnected_handler(cause)

        # assert watchdog was cancelled
        assert pending_connection_op.watchdog_timer is None
        assert mock_timer.return_value.cancel.call_count == 1


@pytest.mark.describe(
    "MQTTTransportStage - OCCURRENCE: MQTT disconnected (Unexpected - no pending operation)"
)
class TestMQTTTransportStageOnDisconnectedUnexpectedNoPendingConnectionOp(
    MQTTTransportStageTestConfigComplex
):
    @pytest.fixture(params=[False, True], ids=["No error cause", "With error cause"])
    def cause(self, request, arbitrary_exception):
        if request.param:
            return arbitrary_exception
        else:
            return None

    @pytest.mark.it(
        "Cancels all in-flight operations in the transport, if connection retry has been disabled"
    )
    def test_inflight_no_retry(self, mocker, stage, cause):
        stage.transport._op_manager = mocker.MagicMock()
        mock_cancel = stage.transport._op_manager.cancel_all_operations
        stage.nucleus.pipeline_configuration.connection_retry = False
        assert stage._pending_connection_op is None
        assert mock_cancel.call_count == 0

        # Trigger disconnect
        stage.transport.on_mqtt_disconnected_handler(cause)

        assert mock_cancel.call_count == 1
        assert mock_cancel.call_args == mocker.call()

    @pytest.mark.it(
        "Does not cancel any in-flight operations in the transport if connection retry has been enabled"
    )
    def test_inflight_unexpected_with_retry(self, mocker, stage, cause):
        stage.transport._op_manager = mocker.MagicMock()
        mock_cancel = stage.transport._op_manager.cancel_all_operations
        stage.nucleus.pipeline_configuration.connection_retry = True
        assert stage._pending_connection_op is None
        assert mock_cancel.call_count == 0

        # Trigger disconnect
        stage.transport.on_mqtt_disconnected_handler(cause)

        assert mock_cancel.call_count == 0

    @pytest.mark.it("Raises a ConnectionDroppedError as a background exception")
    def test_background_exception_raised(self, stage, cause):
        assert stage._pending_connection_op is None
        assert stage.report_background_exception.call_count == 0

        # Trigger disconnect
        stage.transport.on_mqtt_disconnected_handler(cause)

        assert stage.report_background_exception.call_count == 1
        background_exception = stage.report_background_exception.call_args[0][0]
        assert isinstance(background_exception, transport_exceptions.ConnectionDroppedError)
        assert background_exception.__cause__ is cause


disconnect_can_raise = [
    "disconnect_raises",
    [
        pytest.param(True, id="mqtt_transport.disconnect raises an exception"),
        pytest.param(False, id="mqtt_transport.disconnect does not raises an exception"),
    ],
]


@pytest.mark.describe("MQTTTransportStage - OCCURRENCE: Connection watchdog expired")
class TestMQTTTransportStageWatchdogExpired(MQTTTransportStageTestConfigComplex):
    @pytest.fixture(params=[pipeline_ops_base.ConnectOperation], ids=["Pending ConnectOperation"])
    def pending_op(self, request, mocker):
        return request.param(callback=mocker.MagicMock())

    @pytest.mark.it(
        "Performs an MQTT disconnect via the MQTTTransport if the op that started the watchdog is still pending"
    )
    def test_calls_disconnect(self, mocker, stage, pending_op, mock_timer):
        stage.run_op(pending_op)

        watchdog_expiration = mock_timer.call_args[0][1]
        watchdog_expiration()

        assert stage.transport.disconnect.call_count == 1

    @pytest.mark.it(
        "Does not perform an MQTT disconnect via the MQTTTransport if the op that started the watchdog is no longer pending"
    )
    def test_does_not_call_disconnect_if_no_longer_pending(
        self, mocker, stage, pending_op, mock_timer
    ):
        stage.run_op(pending_op)
        stage._pending_connection_op = None

        watchdog_expiration = mock_timer.call_args[0][1]
        watchdog_expiration()

        assert stage.transport.disconnect.call_count == 0

    @pytest.mark.parametrize(*disconnect_can_raise)
    @pytest.mark.it(
        "Completes the op that started the watchdog with an OperationTimeout exception if that op is still pending"
    )
    def test_completes_with_operation_cancelled(
        self, mocker, stage, pending_op, mock_timer, disconnect_raises, arbitrary_exception
    ):
        if disconnect_raises:
            stage.transport.disconnect = mocker.MagicMock(side_effect=arbitrary_exception)

        callback = pending_op.callback_stack[0]

        stage.run_op(pending_op)

        watchdog_expiration = mock_timer.call_args[0][1]
        watchdog_expiration()

        assert callback.call_count == 1
        assert isinstance(callback.call_args[1]["error"], pipeline_exceptions.OperationTimeout)

    @pytest.mark.parametrize(*disconnect_can_raise)
    @pytest.mark.it(
        "Does not complete the op that started the watchdog with an OperationCancelled error if that op is no longer pending"
    )
    def test_does_not_complete_op_if_no_longer_pending(
        self, mocker, stage, pending_op, mock_timer, disconnect_raises, arbitrary_exception
    ):
        if disconnect_raises:
            stage.transport.disconnect = mocker.MagicMock(side_effect=arbitrary_exception)

        callback = pending_op.callback_stack[0]

        stage.run_op(pending_op)
        stage._pending_connection_op = None

        watchdog_expiration = mock_timer.call_args[0][1]
        watchdog_expiration()

        assert callback.call_count == 0

    @pytest.mark.parametrize(*disconnect_can_raise)
    @pytest.mark.it(
        "Sends a DisconnectedEvent if the op that started the watchdog is still pending and the pipeline is connected"
    )
    def test_sends_disconnected_event_if_still_pending_and_connected(
        self,
        mocker,
        stage,
        pending_op,
        mock_timer,
        disconnect_raises,
        arbitrary_exception,
        pipeline_connected_mock,
    ):
        if disconnect_raises:
            stage.transport.disconnect = mocker.MagicMock(side_effect=arbitrary_exception)

        pipeline_connected_mock.return_value = True
        assert stage.nucleus.connected
        stage.run_op(pending_op)

        watchdog_expiration = mock_timer.call_args[0][1]
        watchdog_expiration()

        assert stage.send_event_up.call_count == 1
        assert isinstance(
            stage.send_event_up.call_args[0][0], pipeline_events_base.DisconnectedEvent
        )

    @pytest.mark.parametrize(*disconnect_can_raise)
    @pytest.mark.it(
        "Does not send a DisconnectedEvent if the op that started the watchdog is still pending and the pipeline is not connected"
    )
    def test_does_not_send_disconnected_event_if_still_pending_and_not_connected(
        self,
        mocker,
        stage,
        pending_op,
        mock_timer,
        disconnect_raises,
        arbitrary_exception,
        pipeline_connected_mock,
    ):
        if disconnect_raises:
            stage.transport.disconnect = mocker.MagicMock(side_effect=arbitrary_exception)

        pipeline_connected_mock.return_value = False
        assert not stage.nucleus.connected
        stage.run_op(pending_op)

        watchdog_expiration = mock_timer.call_args[0][1]
        watchdog_expiration()

        assert stage.send_event_up.call_count == 0

    @pytest.mark.parametrize(*disconnect_can_raise)
    @pytest.mark.it(
        "Does not send a DisconnectedEvent if the op that started the watchdog is no longer pending and the pipeline is connected"
    )
    def test_does_not_send_disconnected_event_if_no_longer_pending_and_connected(
        self,
        mocker,
        stage,
        pending_op,
        mock_timer,
        disconnect_raises,
        arbitrary_exception,
        pipeline_connected_mock,
    ):
        if disconnect_raises:
            stage.transport.disconnect = mocker.MagicMock(side_effect=arbitrary_exception)

        pipeline_connected_mock.return_value = True
        assert stage.nucleus.connected
        stage.run_op(pending_op)
        stage._pending_connection_op = None

        watchdog_expiration = mock_timer.call_args[0][1]
        watchdog_expiration()

        assert stage.send_event_up.call_count == 0

    @pytest.mark.parametrize(*disconnect_can_raise)
    @pytest.mark.it(
        "Does not send a DisconnectedEvent if the op that started the watchdog is no longer pending and the pipeline connected flag is False"
    )
    def test_does_not_send_disconnected_event_if_no_longer_pending_and_not_connected(
        self,
        mocker,
        stage,
        pending_op,
        mock_timer,
        disconnect_raises,
        arbitrary_exception,
        pipeline_connected_mock,
    ):
        if disconnect_raises:
            stage.transport.disconnect = mocker.MagicMock(side_effect=arbitrary_exception)

        pipeline_connected_mock.return_value = True
        assert stage.nucleus.connected
        stage.run_op(pending_op)
        stage._pending_connection_op = None

        watchdog_expiration = mock_timer.call_args[0][1]
        watchdog_expiration()

        assert stage.send_event_up.call_count == 0
