# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import logging
import time
import pytest
import sys
import six
import threading
import random
from six.moves import queue
from azure.iot.device.common import transport_exceptions, handle_exceptions
from azure.iot.device.common.pipeline import (
    pipeline_stages_base,
    pipeline_ops_base,
    pipeline_ops_mqtt,
    pipeline_events_base,
    pipeline_exceptions,
)
from .helpers import StageRunOpTestBase, StageHandlePipelineEventTestBase
from .fixtures import ArbitraryOperation
from tests.common.pipeline import pipeline_stage_test

this_module = sys.modules[__name__]
logging.basicConfig(level=logging.DEBUG)
pytestmark = pytest.mark.usefixtures("fake_pipeline_thread")


# # Workaround for flake8.  A class with this name is actually created inside
# # add_base_pipeline_stage_test, but flake8 doesn't know that
# class TestPipelineRootStagePipelineThreading:
#     pass

# @pytest.mark.it("Calls operation callback in callback thread")
# def _test_pipeline_root_runs_callback_in_callback_thread(self, stage, mocker):
#     # the stage fixture comes from the TestPipelineRootStagePipelineThreading object that
#     # this test method gets added to, so it's a PipelineRootStage object
#     stage.pipeline_root = stage
#     callback_called = threading.Event()

#     def callback(op, error):
#         assert threading.current_thread().name == "callback"
#         callback_called.set()

#     op = pipeline_ops_base.ConnectOperation(callback=callback)
#     stage.run_op(op)
#     callback_called.wait()


# # CT-TODO: how is this test even passing????
# @pytest.mark.it("Runs operation in pipeline thread")
# def _test_pipeline_root_runs_operation_in_pipeline_thread(
#     self, mocker, stage, arbitrary_op, fake_non_pipeline_thread
# ):
#     # the stage fixture comes from the TestPipelineRootStagePipelineThreading object that
#     # this test method gets added to, so it's a PipelineRootStage object
#     assert threading.current_thread().name != "pipeline"

#     def mock_run_op(self, op):
#         print("mock_run_op called")
#         assert threading.current_thread().name == "pipeline"
#         op.callback(op)

#     mock_run_op = mocker.MagicMock(mock_run_op)
#     stage._run_op = mock_run_op

#     stage.run_op(arbitrary_op)
#     assert mock_run_op.call_count == 1


# @pytest.mark.it("Calls on_connected_handler in callback thread")
# def _test_pipeline_root_runs_on_connected_in_callback_thread(self, stage, mocker):
#     stage.pipeline_root = stage
#     callback_called = threading.Event()

#     def callback(*arg, **argv):
#         assert threading.current_thread().name == "callback"
#         callback_called.set()

#     stage.on_connected_handler = callback

#     stage.on_connected()
#     callback_called.wait()


# @pytest.mark.it("Calls on_disconnected_handler in callback thread")
# def _test_pipeline_root_runs_on_disconnected_in_callback_thread(self, stage, mocker):
#     stage.pipeline_root = stage
#     callback_called = threading.Event()

#     def callback(*arg, **argv):
#         assert threading.current_thread().name == "callback"
#         callback_called.set()

#     stage.on_disconnected_handler = callback

#     stage.on_disconnected()
#     callback_called.wait()


# @pytest.mark.it("Calls on_event_received_handler in callback thread")
# def _test_pipeline_root_runs_on_event_received_in_callback_thread(
#     self, stage, mocker, arbitrary_event
# ):
#     stage.pipeline_root = stage
#     callback_called = threading.Event()

#     def callback(*arg, **argv):
#         assert threading.current_thread().name == "callback"
#         callback_called.set()

#     stage.on_pipeline_event_handler = callback

#     stage.handle_pipeline_event(arbitrary_event)
#     callback_called.wait()


# TestPipelineRootStagePipelineThreading.test_runs_callback_in_callback_thread = (
#     _test_pipeline_root_runs_callback_in_callback_thread
# )
# TestPipelineRootStagePipelineThreading.test_runs_operation_in_pipeline_thread = (
#     _test_pipeline_root_runs_operation_in_pipeline_thread
# )
# TestPipelineRootStagePipelineThreading.test_pipeline_root_runs_on_connected_in_callback_thread = (
#     _test_pipeline_root_runs_on_connected_in_callback_thread
# )
# TestPipelineRootStagePipelineThreading.test_pipeline_root_runs_on_disconnected_in_callback_thread = (
#     _test_pipeline_root_runs_on_disconnected_in_callback_thread
# )
# TestPipelineRootStagePipelineThreading.test_pipeline_root_runs_on_event_received_in_callback_thread = (
#     _test_pipeline_root_runs_on_event_received_in_callback_thread
# )


#######################
# PIPELINE ROOT STAGE #
#######################


class PipelineRootStageTestConfig(object):
    @pytest.fixture
    def cls_type(self):
        return pipeline_stages_base.PipelineRootStage

    @pytest.fixture
    def init_kwargs(self, mocker):
        return {"pipeline_configuration": mocker.MagicMock()}

    @pytest.fixture
    def stage(self, cls_type, init_kwargs):
        stage = cls_type(**init_kwargs)
        return stage


class PipelineRootStageInstantiationTests(PipelineRootStageTestConfig):
    @pytest.mark.it("Initializes 'on_pipeline_event_handler' as None")
    def test_on_pipeline_event_handler(self, init_kwargs):
        stage = pipeline_stages_base.PipelineRootStage(**init_kwargs)
        assert stage.on_pipeline_event_handler is None

    @pytest.mark.it("Initializes 'on_connected_handler' as None")
    def test_on_connected_handler(self, init_kwargs):
        stage = pipeline_stages_base.PipelineRootStage(**init_kwargs)
        assert stage.on_connected_handler is None

    @pytest.mark.it("Initializes 'on_disconnected_handler' as None")
    def test_on_disconnected_handler(self, init_kwargs):
        stage = pipeline_stages_base.PipelineRootStage(**init_kwargs)
        assert stage.on_disconnected_handler is None

    @pytest.mark.it("Initializes 'connected' as False")
    def test_connected(self, init_kwargs):
        stage = pipeline_stages_base.PipelineRootStage(**init_kwargs)
        assert stage.connected is False

    @pytest.mark.it(
        "Initializes 'pipeline_configuration' with the provided 'pipeline_configuration' parameter"
    )
    def test_pipeline_configuration(self, init_kwargs):
        stage = pipeline_stages_base.PipelineRootStage(**init_kwargs)
        assert stage.pipeline_configuration is init_kwargs["pipeline_configuration"]


pipeline_stage_test.add_base_pipeline_stage_tests(
    test_module=this_module,
    stage_class_under_test=pipeline_stages_base.PipelineRootStage,
    stage_test_config_class=PipelineRootStageTestConfig,
    extended_stage_instantiation_test_class=PipelineRootStageInstantiationTests,
)


@pytest.mark.describe("PipelineRootStage - .append_stage()")
class TestPipelineRootStageAppendStage(PipelineRootStageTestConfig):
    @pytest.mark.it("Appends the provided stage to the tail of the pipeline")
    @pytest.mark.parametrize(
        "pipeline_len",
        [
            pytest.param(1, id="Pipeline Length: 1"),
            pytest.param(2, id="Pipeline Length: 2"),
            pytest.param(3, id="Pipeline Length: 3"),
            pytest.param(10, id="Pipeline Length: 10"),
            pytest.param(random.randint(4, 99), id="Randomly chosen Pipeline Length"),
        ],
    )
    def test_appends_new_stage(self, stage, pipeline_len):
        class ArbitraryStage(pipeline_stages_base.PipelineStage):
            pass

        assert stage.next is None
        assert stage.previous is None
        prev_tail = stage
        root = stage
        for i in range(0, pipeline_len):
            new_stage = ArbitraryStage()
            stage.append_stage(new_stage)
            assert prev_tail.next is new_stage
            assert new_stage.previous is prev_tail
            assert new_stage.pipeline_root is root
            prev_tail = new_stage


# CT-TODO: Address the unique .run_op() implementation


@pytest.mark.describe("PipelineRootStage - .handle_pipeline_event() -- Called with ConnectedEvent")
class TestPipelineRootStageHandlePipelineEventWithConnectedEvent(
    PipelineRootStageTestConfig, StageHandlePipelineEventTestBase
):
    @pytest.fixture
    def event(self):
        return pipeline_events_base.ConnectedEvent()

    @pytest.mark.it("Sets the 'connected' attribute to True")
    def test_set_connected_true(self, stage, event):
        assert not stage.connected
        stage.handle_pipeline_event(event)
        assert stage.connected

    @pytest.mark.it("Invokes the 'on_connected_handler' handler function, if set")
    def test_invoke_handler(self, mocker, stage, event):
        mock_handler = mocker.MagicMock()
        stage.on_connected_handler = mock_handler
        stage.handle_pipeline_event(event)
        assert mock_handler.call_count == 1
        assert mock_handler.call_args == mocker.call()


@pytest.mark.describe(
    "PipelineRootStage - .handle_pipeline_event() -- Called with DisconnectedEvent"
)
class TestPipelineRootStageHandlePipelineEventWithDisconnectedEvent(
    PipelineRootStageTestConfig, StageHandlePipelineEventTestBase
):
    @pytest.fixture
    def event(self):
        return pipeline_events_base.DisconnectedEvent()

    @pytest.mark.it("Sets the 'connected' attribute to True")
    def test_set_connected_false(self, stage, event):
        stage.connected = True
        stage.handle_pipeline_event(event)
        assert not stage.connected

    @pytest.mark.it("Invokes the 'on_disconnected_handler' handler function, if set")
    def test_invoke_handler(self, mocker, stage, event):
        mock_handler = mocker.MagicMock()
        stage.on_disconnected_handler = mock_handler
        stage.handle_pipeline_event(event)
        time.sleep(0.1)  # CT-TODO: get rid of this
        assert mock_handler.call_count == 1
        assert mock_handler.call_args == mocker.call()


@pytest.mark.describe(
    "PipelineRootStage - .handle_pipeline_event() -- Called with an arbitrary other event"
)
class TestPipelineRootStageHandlePipelineEventWithArbitraryEvent(
    PipelineRootStageTestConfig, StageHandlePipelineEventTestBase
):
    @pytest.fixture
    def event(self, arbitrary_event):
        return arbitrary_event

    @pytest.mark.it("Invokes the 'on_pipeline_event_handler' handler function, if set")
    def test_invoke_handler(self, mocker, stage, event):
        mock_handler = mocker.MagicMock()
        stage.on_pipeline_event_handler = mock_handler
        stage.handle_pipeline_event(event)
        time.sleep(0.1)  # CT-TODO: get rid of this
        assert mock_handler.call_count == 1
        assert mock_handler.call_args == mocker.call(event)


######################
# AUTO CONNECT STAGE #
######################


class AutoConnectStageTestConfig(object):
    @pytest.fixture
    def cls_type(self):
        return pipeline_stages_base.AutoConnectStage

    @pytest.fixture
    def init_kwargs(self, mocker):
        return {}

    @pytest.fixture
    def stage(self, mocker, cls_type, init_kwargs):
        stage = cls_type(**init_kwargs)
        stage.pipeline_root = pipeline_stages_base.PipelineRootStage(
            pipeline_configuration=mocker.MagicMock()
        )
        # Mock flow methods
        stage.send_op_down = mocker.MagicMock()
        stage.send_event_up = mocker.MagicMock()
        return stage


pipeline_stage_test.add_base_pipeline_stage_tests(
    test_module=this_module,
    stage_class_under_test=pipeline_stages_base.AutoConnectStage,
    stage_test_config_class=AutoConnectStageTestConfig,
)


@pytest.mark.describe(
    "AutoConnectStage - .run_op() -- Called with an Operation that requires an active connection"
)
class TestAutoConnectStageRunOpWithOpThatRequiresConnection(
    AutoConnectStageTestConfig, StageRunOpTestBase
):

    fake_topic = "__fake_topic__"
    fake_payload = "__fake_payload__"

    ops_requiring_connection = [
        pipeline_ops_mqtt.MQTTPublishOperation,
        pipeline_ops_mqtt.MQTTSubscribeOperation,
        pipeline_ops_mqtt.MQTTUnsubscribeOperation,
    ]

    @pytest.fixture(params=ops_requiring_connection)
    def op(self, mocker, request):
        op_class = request.param
        if op_class is pipeline_ops_mqtt.MQTTPublishOperation:
            op = op_class(
                topic=self.fake_topic, payload=self.fake_payload, callback=mocker.MagicMock()
            )
        else:
            op = op_class(topic=self.fake_topic, callback=mocker.MagicMock())
        assert op.needs_connection
        return op

    @pytest.mark.it(
        "Sends the operation down the pipeline if the pipeline is already in a 'connected' state"
    )
    def test_already_connected(self, mocker, stage, op):
        stage.pipeline_root.connected = True

        stage.run_op(op)

        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(op)

    @pytest.mark.it(
        "Sends a new ConnectOperation down the pipeline if the pipeline is not yet in a 'connected' state"
    )
    def test_not_connected(self, mocker, stage, op):
        mock_connect_op = mocker.patch.object(pipeline_ops_base, "ConnectOperation").return_value
        assert not stage.pipeline_root.connected

        stage.run_op(op)

        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(mock_connect_op)

    @pytest.mark.it(
        "Sends the operation down the pipeline once the ConnectOperation completes successfully"
    )
    def test_connect_success(self, mocker, stage, op):
        assert not stage.pipeline_root.connected

        # Run the original operation
        stage.run_op(op)
        assert not op.completed

        # Complete the newly created ConnectOperation that was sent down the pipeline
        assert stage.send_op_down.call_count == 1
        connect_op = stage.send_op_down.call_args[0][0]
        assert not connect_op.completed
        connect_op.complete()  # no error

        # The original operation has now been sent down the pipeline
        assert stage.send_op_down.call_count == 2
        assert stage.send_op_down.call_args == mocker.call(op)

    @pytest.mark.it(
        "Completes the operation with the error from the ConnectOperation, if the ConnectOperation completes with an error"
    )
    def test_connect_failure(self, mocker, stage, op, arbitrary_exception):
        assert not stage.pipeline_root.connected

        # Run the original operation
        stage.run_op(op)
        assert not op.completed

        # Complete the newly created ConnectOperation that was sent down the pipeline
        assert stage.send_op_down.call_count == 1
        connect_op = stage.send_op_down.call_args[0][0]
        assert not connect_op.completed
        connect_op.complete(error=arbitrary_exception)  # completes with error

        # The original operation has been completed the exception from the ConnectOperation
        assert op.completed
        assert op.error is arbitrary_exception


@pytest.mark.describe(
    "AutoConnectStage - .run_op() -- Called with an Operation that does not require an active connection"
)
class TestAutoConnectStageRunOpWithOpThatDoesNotRequireConnection(
    AutoConnectStageTestConfig, StageRunOpTestBase
):
    @pytest.fixture
    def op(self, arbitrary_op):
        assert not arbitrary_op.needs_connection
        return arbitrary_op

    @pytest.mark.it(
        "Sends the operation down the pipeline if the pipeline is in a 'connected' state"
    )
    def test_connected(self, mocker, stage, op):
        stage.pipeline_root.connected = True

        stage.run_op(op)
        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(op)

    @pytest.mark.it(
        "Sends the operation down the pipeline if the pipeline is in a 'disconnected' state"
    )
    def test_disconnected(self, mocker, stage, op):
        assert not stage.pipeline_root.connected

        stage.run_op(op)
        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(op)


#########################
# CONNECTION LOCK STAGE #
#########################

# This is a list of operations which can trigger a block on the ConnectionLockStage
connection_ops = [
    pipeline_ops_base.ConnectOperation,
    pipeline_ops_base.DisconnectOperation,
    pipeline_ops_base.ReconnectOperation,
]


class ConnectionLockStageTestConfig(object):
    @pytest.fixture
    def cls_type(self):
        return pipeline_stages_base.ConnectionLockStage

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
        return stage


class ConnectionLockStageInstantiationTests(ConnectionLockStageTestConfig):
    @pytest.mark.it("Initializes 'queue' as an empty Queue object")
    def test_queue(self, init_kwargs):
        stage = pipeline_stages_base.ConnectionLockStage(**init_kwargs)
        assert isinstance(stage.queue, queue.Queue)
        assert stage.queue.empty()

    @pytest.mark.it("Initializes 'blocked' as False")
    def test_blocked(self, init_kwargs):
        stage = pipeline_stages_base.ConnectionLockStage(**init_kwargs)
        assert not stage.blocked


pipeline_stage_test.add_base_pipeline_stage_tests(
    test_module=this_module,
    stage_class_under_test=pipeline_stages_base.ConnectionLockStage,
    stage_test_config_class=ConnectionLockStageTestConfig,
    extended_stage_instantiation_test_class=ConnectionLockStageInstantiationTests,
)


@pytest.mark.describe(
    "ConnectionLockStage - .run_op() -- Called with a ConnectOperation while not in a blocking state"
)
class TestConnectionLockStageRunOpWithConnectOpWhileUnblocked(
    ConnectionLockStageTestConfig, StageRunOpTestBase
):
    @pytest.fixture
    def op(self, mocker):
        return pipeline_ops_base.ConnectOperation(callback=mocker.MagicMock())

    @pytest.mark.it("Completes the operation immediately if the pipeline is already connected")
    def test_already_connected(self, mocker, stage, op):
        stage.pipeline_root.connected = True

        # Run the operation
        stage.run_op(op)

        # Operation is completed
        assert op.completed
        assert op.error is None

        # Stage is still not blocked
        assert not stage.blocked

    @pytest.mark.it(
        "Puts the stage in a blocking state and sends the operation down the pipeline, if the pipeline is not currently connected"
    )
    def test_not_connected(self, mocker, stage, op):
        stage.pipeline_root.connected = False

        # Stage is not blocked
        assert not stage.blocked

        # Run the operation
        stage.run_op(op)

        # Stage is now blocked
        assert stage.blocked

        # Operation was passed down
        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(op)

        # Operation is not yet completed
        assert not op.completed


@pytest.mark.describe(
    "ConnectionLockStage - .run_op() -- Called with a DisconnectOperation while not in a blocking state"
)
class TestConnectionLockStageRunOpWithDisconnectOpWhileUnblocked(
    ConnectionLockStageTestConfig, StageRunOpTestBase
):
    @pytest.fixture
    def op(self, mocker):
        return pipeline_ops_base.DisconnectOperation(callback=mocker.MagicMock())

    @pytest.mark.it("Completes the operation immediately if the pipeline is already disconnected")
    def test_already_disconnected(self, mocker, stage, op):
        stage.pipeline_root.connected = False

        # Run the operation
        stage.run_op(op)

        # Operation is completed
        assert op.completed
        assert op.error is None

        # Stage is still not blocked
        assert not stage.blocked

    @pytest.mark.it(
        "Puts the stage in a blocking state and sends the operation down the pipeline, if the pipeline is currently connected"
    )
    def test_connected(self, mocker, stage, op):
        stage.pipeline_root.connected = True

        # Stage is not blocked
        assert not stage.blocked

        # Run the operation
        stage.run_op(op)

        # Stage is now blocked
        assert stage.blocked

        # Operation was passed down
        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(op)

        # Operation is not yet completed
        assert not op.completed


@pytest.mark.describe(
    "ConnectionLockStage - .run_op() -- Called with a ReconnectOperation while not in a blocking state"
)
class TestConnectionLockStageRunOpWithReconnectOpWhileUnblocked(
    ConnectionLockStageTestConfig, StageRunOpTestBase
):
    @pytest.fixture
    def op(self, mocker):
        return pipeline_ops_base.ReconnectOperation(callback=mocker.MagicMock())

    @pytest.mark.it("Puts the stage in a blocking state and sends the operation down the pipeline")
    @pytest.mark.parametrize(
        "connected",
        [
            pytest.param(True, id="Pipeline Connected"),
            pytest.param(False, id="Pipeline Disconnected"),
        ],
    )
    def test_not_connected(self, mocker, connected, stage, op):
        stage.pipeline_root.connected = connected

        # Stage is not blocked
        assert not stage.blocked

        # Run the operation
        stage.run_op(op)

        # Stage is now blocked
        assert stage.blocked

        # Operation was passed down
        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(op)

        # Operation is not yet completed
        assert not op.completed


@pytest.mark.describe("ConnectionLockStage - .run_op() -- Called with an arbitrary other operation")
class TestConnectionLockStageRunOpWithArbitraryStageWhileUnblocked(
    ConnectionLockStageTestConfig, StageRunOpTestBase
):
    @pytest.fixture
    def op(self, arbitrary_op):
        return arbitrary_op

    @pytest.mark.it("Sends the operation down the pipeline")
    @pytest.mark.parametrize(
        "connected",
        [
            pytest.param(True, id="Pipeline Connected"),
            pytest.param(False, id="Pipeline Disconnected"),
        ],
    )
    def test_sends_down(self, mocker, connected, stage, op):
        stage.pipeline_root.connected = connected

        stage.run_op(op)

        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(op)


@pytest.mark.describe("ConnectionLockStage - .run_op() -- Called while in a blocking state")
class TestConnectionLockStageRunOpWhileBlocked(ConnectionLockStageTestConfig, StageRunOpTestBase):
    @pytest.fixture
    def blocking_op(self, mocker):
        return pipeline_ops_base.ConnectOperation(callback=mocker.MagicMock())

    @pytest.fixture
    def stage(self, mocker, init_kwargs, blocking_op):
        stage = pipeline_stages_base.ConnectionLockStage(**init_kwargs)
        stage.pipeline_root = pipeline_stages_base.PipelineRootStage(
            pipeline_configuration=mocker.MagicMock()
        )
        stage.send_op_down = mocker.MagicMock()
        mocker.spy(stage, "run_op")
        assert not stage.blocked

        # Block the stage by running a blocking operation
        stage.run_op(blocking_op)
        assert stage.blocked

        # Reset the mock for ease of testing
        stage.send_op_down.reset_mock()
        stage.run_op.reset_mock()
        return stage

    @pytest.fixture(params=(connection_ops + [ArbitraryOperation]))
    def op(self, mocker, request):
        conn_op_class = request.param
        op = conn_op_class(callback=mocker.MagicMock())
        return op

    @pytest.mark.it(
        "Adds the operation to the queue, pending the completion of the operation on which the stage is blocked"
    )
    def test_adds_to_queue(self, mocker, stage, op):
        assert stage.queue.empty()
        stage.run_op(op)

        # Operation is in queue
        assert not stage.queue.empty()
        assert stage.queue.qsize() == 1
        assert stage.queue.get(block=False) is op

        # Operation was not passed down
        assert stage.send_op_down.call_count == 0

        # Operation has not been completed
        assert not op.completed

    @pytest.mark.it(
        "Can support multiple pending operations if called multiple times during the blocking state"
    )
    def test_multiple_ops_added_to_queue(self, mocker, stage):
        assert stage.queue.empty()

        op1 = pipeline_ops_base.DisconnectOperation(callback=mocker.MagicMock())
        op2 = pipeline_ops_base.ConnectOperation(callback=mocker.MagicMock())
        op3 = pipeline_ops_base.ReconnectOperation(callback=mocker.MagicMock())
        op4 = ArbitraryOperation(callback=mocker.MagicMock())

        stage.run_op(op1)
        stage.run_op(op2)
        stage.run_op(op3)
        stage.run_op(op4)

        # Operations have all been added to the queue
        assert not stage.queue.empty()
        assert stage.queue.qsize() == 4

        # No Operations were passed down
        assert stage.send_op_down.call_count == 0

        # No Operations have been completed
        assert not op1.completed
        assert not op2.completed
        assert not op3.completed
        assert not op4.completed


class ConnectionLockStageBlockingOpCompletedTestConfig(ConnectionLockStageTestConfig):
    @pytest.fixture(params=connection_ops)
    def blocking_op(self, mocker, request):
        op_cls = request.param
        return op_cls(callback=mocker.MagicMock())

    @pytest.fixture
    def pending_ops(self, mocker):
        op1 = ArbitraryOperation(callback=mocker.MagicMock)
        op2 = ArbitraryOperation(callback=mocker.MagicMock)
        op3 = ArbitraryOperation(callback=mocker.MagicMock)
        pending_ops = [op1, op2, op3]
        return pending_ops

    @pytest.fixture
    def stage(self, mocker, init_kwargs, blocking_op, pending_ops):
        stage = pipeline_stages_base.ConnectionLockStage(**init_kwargs)
        stage.pipeline_root = pipeline_stages_base.PipelineRootStage(
            pipeline_configuration=mocker.MagicMock()
        )
        stage.send_op_down = mocker.MagicMock()
        mocker.spy(stage, "run_op")
        assert not stage.blocked

        # Set the pipeline connection state to ensure op will block
        if isinstance(blocking_op, pipeline_ops_base.ConnectOperation):
            stage.pipeline_root.connected = False
        else:
            stage.pipeline_root.connected = True

        # Block the stage by running the blocking operation
        stage.run_op(blocking_op)
        assert stage.blocked

        # Add pending operations
        for op in pending_ops:
            stage.run_op(op)

        # All pending ops should be queued
        assert stage.queue.qsize() == len(pending_ops)

        # Reset the mock for ease of testing
        stage.send_op_down.reset_mock()
        stage.run_op.reset_mock()
        return stage


@pytest.mark.describe(
    "ConnectionLockStage - EVENT: Operation blocking ConnectionLockStage is completed successfully"
)
class TestConnectionLockStageBlockingOpCompletedNoError(
    ConnectionLockStageBlockingOpCompletedTestConfig
):
    @pytest.mark.it("Re-runs the pending operations in FIFO order")
    def test_blocking_op_completes_successfully(self, mocker, stage, pending_ops, blocking_op):
        # .run_op() has not yet been called
        assert stage.run_op.call_count == 0

        # Pending ops are queued in the stage
        assert stage.queue.qsize() == len(pending_ops)

        # Complete blocking op successfully
        blocking_op.complete()

        # .run_op() was called for every pending operation, in FIFO order
        assert stage.run_op.call_count == len(pending_ops)
        assert stage.run_op.call_args_list == [mocker.call(op) for op in pending_ops]

        # Note that this is only true because we are using arbitrary ops. Depending on what occurs during
        # the .run_op() calls, this could end up having items, but that case is covered by a different test
        assert stage.queue.qsize() == 0

    @pytest.mark.it("Unblocks the ConnectionLockStage prior to re-running any pending operations")
    def test_unblocks_before_rerun(self, mocker, stage, blocking_op, pending_ops):
        mocker.spy(handle_exceptions, "handle_background_exception")
        assert stage.blocked

        def run_op_override(op):
            # Because the .run_op() invocation is called during operation completion,
            # any exceptions, including AssertionErrors will go to the background exception handler

            # Verify that the stage is not blocked during the call to .run_op()
            assert not stage.blocked

        stage.run_op = mocker.MagicMock(side_effect=run_op_override)

        blocking_op.complete()

        # Stage is still unblocked by the end of the blocking op completion
        assert not stage.blocked

        # Verify that the mock .run_op() was indeed called
        assert stage.run_op.call_count == len(pending_ops)

        # Verify that no assertions from the mock .run_op() turned up False
        assert handle_exceptions.handle_background_exception.call_count == 0


@pytest.mark.describe(
    "ConnectionLockStage - EVENT: Operation blocking ConnectionLockStage is completed with error"
)
class TestConnectionLockStageBlockingOpCompletedWithError(
    ConnectionLockStageBlockingOpCompletedTestConfig
):
    # CT-TODO: Show that completion occurs in FIFO order
    @pytest.mark.it("Completes all pending operations with the error from the blocking operation")
    def test_blocking_op_completes_with_error(
        self, stage, pending_ops, blocking_op, arbitrary_exception
    ):
        # Pending ops are not yet completed
        for op in pending_ops:
            assert not op.completed

        # Pending ops are queued in the stage
        assert stage.queue.qsize() == len(pending_ops)

        # Complete blocking op with error
        blocking_op.complete(error=arbitrary_exception)

        # Pending ops are now completed with error from blocking op
        for op in pending_ops:
            assert op.completed
            assert op.error is arbitrary_exception

        # No more pending ops in stage queue
        assert stage.queue.empty()

    @pytest.mark.it("Unblocks the ConnectionLockStage prior to completing any pending operations")
    def test_unblocks_before_complete(
        self, mocker, stage, pending_ops, blocking_op, arbitrary_exception
    ):
        mocker.spy(handle_exceptions, "handle_background_exception")
        assert stage.blocked

        def complete_override(error=None):
            # Because this call to .complete() is called during another op's completion,
            # any exceptions, including AssertionErrors will go to the background exception handler

            # Verify that the stage is not blocked during the call to .complete()
            assert not stage.blocked

        for op in pending_ops:
            op.complete = mocker.MagicMock(side_effect=complete_override)

        # Complete the blocking op with error
        blocking_op.complete(error=arbitrary_exception)

        # Stage is still unblocked at the end of the blocking op completion
        assert not stage.blocked

        # Verify that the mock completion was called for the pending ops
        for op in pending_ops:
            assert op.complete.call_count == 1

        # Verify that no assertions from the mock .complete() calls turned up False
        assert handle_exceptions.handle_background_exception.call_count == 0


# class TestConnectionLockStageRunOpWithConnectionOp(ConnectionLockStageTestConfig, StageRunOpTestBase):

#     connection_ops = [
#         pipeline_ops_base.ConnectOperation,
#         pipeline_ops_base.DisconnectOperation,
#         pipeline_ops_base.ReconnectOperation
#     ]


# # pipeline_stage_test.add_base_pipeline_stage_tests(
# #     cls=pipeline_stages_base.ConnectionLockStage,
# #     module=this_module,
# #     all_ops=all_common_ops,
# #     handled_ops=[
# #         pipeline_ops_base.ConnectOperation,
# #         pipeline_ops_base.DisconnectOperation,
# #         pipeline_ops_base.ReconnectOperation,
# #     ],
# #     all_events=all_common_events,
# #     handled_events=[],
# #     extra_initializer_defaults={"blocked": False, "queue": queue.Queue},
# # )

# connection_ops = [
#     {"op_class": pipeline_ops_base.ConnectOperation, "connected_flag_required_to_run": False},
#     {"op_class": pipeline_ops_base.DisconnectOperation, "connected_flag_required_to_run": True},
#     {"op_class": pipeline_ops_base.ReconnectOperation, "connected_flag_required_to_run": True},
# ]


# class ArbitraryOperation(pipeline_ops_base.PipelineOperation):
#     pass


# @pytest.mark.describe(
#     "ConnectionLockStage - .run_op() -- called with an operation that connects, disconnects, or reconnects"
# )
# class TestSerializeConnectOpStageRunOp(StageTestBase):
#     @pytest.fixture
#     def stage(self):
#         return pipeline_stages_base.ConnectionLockStage()

#     @pytest.fixture
#     def connection_op(self, mocker, params):
#         return params["op_class"](callback=mocker.MagicMock())

#     @pytest.fixture
#     def fake_op(self, mocker):
#         op = ArbitraryOperation(callback=mocker.MagicMock())
#         mocker.spy(op, "complete")
#         return op

#     @pytest.fixture
#     def fake_ops(self, mocker):
#         return [
#             ArbitraryOperation(callback=mocker.MagicMock()),
#             ArbitraryOperation(callback=mocker.MagicMock()),
#             ArbitraryOperation(callback=mocker.MagicMock()),
#         ]

#     @pytest.mark.it(
#         "Does not immediately pass down operations in the queue if an operation in the queue causes the stage to re-block"
#     )
#     def test_re_blocks_ops_from_queue(self, stage, mocker):
#         first_connect = pipeline_ops_base.ConnectOperation(callback=mocker.MagicMock())
#         mocker.spy(first_connect, "complete")
#         first_fake_op = ArbitraryOperation(callback=mocker.MagicMock())
#         second_connect = pipeline_ops_base.ReconnectOperation(callback=mocker.MagicMock())
#         mocker.spy(second_connect, "complete")
#         second_fake_op = ArbitraryOperation(callback=mocker.MagicMock())

#         stage.run_op(first_connect)
#         stage.run_op(first_fake_op)
#         stage.run_op(second_connect)
#         stage.run_op(second_fake_op)

#         # at this point, ops are pended waiting for the first connect to complete.  Verify this and complete the connect.
#         assert stage.next.run_op.call_count == 1
#         assert stage.next.run_op.call_args[0][0] == first_connect
#         first_connect.complete()

#         # The connect is complete.  This passes down first_fake_op and second_connect and second_fake_op gets pended waiting i
#         # for second_connect to complete.
#         # Note: this isn't ideal.  In a perfect world, second_connect wouldn't start until first_fake_op is complete, but we
#         # dont have this logic in place yet.
#         assert stage.next.run_op.call_count == 3
#         assert stage.next.run_op.call_args_list[1][0][0] == first_fake_op
#         assert stage.next.run_op.call_args_list[2][0][0] == second_connect

#         # now, complete second_connect to give second_fake_op a chance to get passed down
#         second_connect.complete()
#         assert stage.next.run_op.call_count == 4
#         assert stage.next.run_op.call_args_list[3][0][0] == second_fake_op

#     @pytest.mark.parametrize(
#         "params",
#         [
#             pytest.param(
#                 {
#                     "pre_connected_flag": True,
#                     "first_connection_op": pipeline_ops_base.DisconnectOperation,
#                     "mid_connect_flag": False,
#                     "second_connection_op": pipeline_ops_base.DisconnectOperation,
#                 },
#                 id="Disconnect followed by Disconnect",
#             ),
#             pytest.param(
#                 {
#                     "pre_connected_flag": False,
#                     "first_connection_op": pipeline_ops_base.ConnectOperation,
#                     "mid_connect_flag": True,
#                     "second_connection_op": pipeline_ops_base.ConnectOperation,
#                 },
#                 id="Connect followed by Connect",
#             ),
#             pytest.param(
#                 {
#                     "pre_connected_flag": True,
#                     "first_connection_op": pipeline_ops_base.ReconnectOperation,
#                     "mid_connect_flag": True,
#                     "second_connection_op": pipeline_ops_base.ConnectOperation,
#                 },
#                 id="Reconnect followed by Connect",
#             ),
#         ],
#     )
#     @pytest.mark.it(
#         "Immediately completes a second op which was waiting for a first op that succeeded"
#     )
#     def test_immediately_completes_second_op(self, stage, params, mocker):
#         first_connection_op = params["first_connection_op"](mocker.MagicMock())
#         second_connection_op = params["second_connection_op"](mocker.MagicMock())
#         mocker.spy(second_connection_op, "complete")
#         stage.pipeline_root.connected = params["pre_connected_flag"]

#         stage.run_op(first_connection_op)
#         stage.run_op(second_connection_op)

#         # first_connection_op has been passed down.  second_connection_op is waiting for first disconnect to complete.
#         assert stage.next.run_op.call_count == 1
#         assert stage.next.run_op.call_args[0][0] == first_connection_op

#         # complete first_connection_op
#         stage.pipeline_root.connected = params["mid_connect_flag"]
#         first_connection_op.complete()

#         # second connect_op should be completed without having been passed down.
#         assert stage.next.run_op.call_count == 1
#         assert second_connection_op.complete.call_count == 1
#         assert second_connection_op.complete.call_args == mocker.call()


# # pipeline_stage_test.add_base_pipeline_stage_tests(
# #     cls=pipeline_stages_base.CoordinateRequestAndResponseStage,
# #     module=this_module,
# #     all_ops=all_common_ops,
# #     handled_ops=[pipeline_ops_base.RequestAndResponseOperation],
# #     all_events=all_common_events,
# #     handled_events=[pipeline_events_base.ResponseEvent],
# #     extra_initializer_defaults={"pending_responses": dict},
# # )


# fake_request_type = "__fake_request_type__"
# fake_method = "__fake_method__"
# fake_resource_location = "__fake_resource_location__"
# fake_request_body = "__fake_request_body__"
# fake_status_code = "__fake_status_code__"
# fake_response_body = "__fake_response_body__"
# fake_request_id = "__fake_request_id__"


# def make_fake_request_and_response(mocker):
#     return pipeline_ops_base.RequestAndResponseOperation(
#         request_type=fake_request_type,
#         method=fake_method,
#         resource_location=fake_resource_location,
#         request_body=fake_request_body,
#         callback=mocker.MagicMock(),
#     )


# @pytest.mark.describe(
#     "CoordinateRequestAndResponse - .run_op() -- called with RequestAndResponseOperation"
# )
# class TestCoordinateRequestAndResponseSendIotRequestRunOp(StageTestBase):
#     @pytest.fixture
#     def op(self, mocker):
#         op = make_fake_request_and_response(mocker)
#         mocker.spy(op, "complete")
#         return op

#     @pytest.fixture
#     def stage(self):
#         return pipeline_stages_base.CoordinateRequestAndResponseStage()

#     @pytest.mark.it(
#         "Sends an RequestOperation op to the next stage with the same parameters and a newly allocated request_id"
#     )
#     def test_sends_op_and_validates_new_op(self, stage, op):
#         stage.run_op(op)
#         assert stage.next.run_op.call_count == 1
#         new_op = stage.next.run_op.call_args[0][0]
#         assert isinstance(new_op, pipeline_ops_base.RequestOperation)
#         assert new_op.request_type == op.request_type
#         assert new_op.method == op.method
#         assert new_op.resource_location == op.resource_location
#         assert new_op.request_body == op.request_body
#         assert new_op.request_id

#     @pytest.mark.it("Does not complete the SendIotRequestAndwaitForResponse op")
#     def test_sends_op_and_verifies_no_response(self, stage, op):
#         stage.run_op(op)
#         assert op.complete.call_count == 0

#     @pytest.mark.it("Generates a new request_id for every operation")
#     def test_sends_two_ops_and_validates_request_id(self, stage, op, mocker):
#         op2 = make_fake_request_and_response(mocker)
#         stage.run_op(op)
#         stage.run_op(op2)
#         assert stage.next.run_op.call_count == 2
#         new_op = stage.next.run_op.call_args_list[0][0][0]
#         new_op2 = stage.next.run_op.call_args_list[1][0][0]
#         assert new_op.request_id != new_op2.request_id

#     @pytest.mark.it(
#         "Fails RequestAndResponseOperation if an Exception is raised in the RequestOperation op"
#     )
#     def test_new_op_raises_exception(self, stage, op, mocker, arbitrary_exception):
#         stage.next._run_op = mocker.Mock(side_effect=arbitrary_exception)
#         stage.run_op(op)
#         assert op.complete.call_count == 1
#         assert op.complete.call_args == mocker.call(error=arbitrary_exception)


# @pytest.mark.describe(
#     "CoordinateRequestAndResponseStage - .handle_pipeline_event() -- called with ResponseEvent"
# )
# class TestCoordinateRequestAndResponseSendIotRequestHandleEvent(StageTestBase):
#     @pytest.fixture
#     def op(self, mocker):
#         op = make_fake_request_and_response(mocker)
#         mocker.spy(op, "complete")
#         return op

#     @pytest.fixture
#     def stage(self):
#         return pipeline_stages_base.CoordinateRequestAndResponseStage()

#     @pytest.fixture
#     def iot_request(self, stage, op):
#         stage.run_op(op)
#         return stage.next.run_op.call_args[0][0]

#     @pytest.fixture
#     def iot_response(self, stage, iot_request):
#         return pipeline_events_base.ResponseEvent(
#             request_id=iot_request.request_id,
#             status_code=fake_status_code,
#             response_body=fake_response_body,
#         )

#     @pytest.mark.it(
#         "Completes the RequestAndResponseOperation op with the matching request_id including response_body and status_code"
#     )
#     def test_completes_op_with_matching_request_id(self, mocker, stage, op, iot_response):
#         stage.next.send_event_up(iot_response)
#         assert op.complete.call_count == 1
#         assert op.complete.call_args == mocker.call()
#         assert op.status_code == iot_response.status_code
#         assert op.response_body == iot_response.response_body

#     @pytest.mark.it(
#         "Calls the unhandled error handler if there is no previous stage when request_id matches"
#     )
#     def test_matching_request_id_with_no_previous_stage(
#         self, stage, op, iot_response, unhandled_error_handler
#     ):
#         stage.next.previous = None
#         stage.next.send_event_up(iot_response)
#         assert unhandled_error_handler.call_count == 1

#     @pytest.mark.it(
#         "Does nothing if an IotResponse with an identical request_id is received a second time"
#     )
#     def test_ignores_duplicate_request_id(
#         self, mocker, stage, op, iot_response, unhandled_error_handler
#     ):
#         stage.next.send_event_up(iot_response)
#         assert op.complete.call_count == 1
#         assert op.complete.call_args == mocker.call()
#         op.complete.reset_mock()

#         stage.next.send_event_up(iot_response)
#         assert op.complete.call_count == 0
#         assert unhandled_error_handler.call_count == 0

#     @pytest.mark.it(
#         "Does nothing if an IotResponse with a request_id is received for an operation that returned failure"
#     )
#     def test_ignores_request_id_from_failure(
#         self, stage, op, mocker, unhandled_error_handler, arbitrary_exception
#     ):
#         stage.next._run_op = mocker.MagicMock(side_effect=arbitrary_exception)
#         stage.run_op(op)

#         req = stage.next.run_op.call_args[0][0]
#         resp = pipeline_events_base.ResponseEvent(
#             request_id=req.request_id,
#             status_code=fake_status_code,
#             response_body=fake_response_body,
#         )

#         op.complete.reset_mock()
#         stage.next.send_event_up(resp)
#         assert op.complete.call_count == 0
#         assert unhandled_error_handler.call_count == 0

#     @pytest.mark.it("Does nothing if an IotResponse with an unknown request_id is received")
#     def test_ignores_unknown_request_id(self, stage, op, iot_response, unhandled_error_handler):
#         iot_response.request_id = fake_request_id
#         stage.next.send_event_up(iot_response)
#         assert op.complete.call_count == 0
#         assert unhandled_error_handler.call_count == 0


# """
# A note on terms in the OpTimeoutStage tests:
#     No-timeout ops are ops that don't need a timeout check
#     Yes-timeout ops are ops that do need a timeout check
# """
# timeout_intervals = {
#     pipeline_ops_mqtt.MQTTSubscribeOperation: 10,
#     pipeline_ops_mqtt.MQTTUnsubscribeOperation: 10,
# }
# yes_timeout_ops = list(timeout_intervals.keys())
# no_timeout_ops = all_except(all_common_ops, yes_timeout_ops)

# # pipeline_stage_test.add_base_pipeline_stage_tests(
# #     cls=pipeline_stages_base.OpTimeoutStage,
# #     module=this_module,
# #     all_ops=all_common_ops,
# #     handled_ops=yes_timeout_ops,
# #     all_events=all_common_events,
# #     handled_events=[],
# #     extra_initializer_defaults={"timeout_intervals": timeout_intervals},
# # )


# @pytest.fixture()
# def mock_timer(mocker):
#     return mocker.patch(
#         "azure.iot.device.common.pipeline.pipeline_stages_base.Timer", autospec=True
#     )


# @pytest.mark.describe("OpTimeoutStage - run_op()")
# class TestOpTimeoutStageRunOp(StageTestBase):
#     @pytest.fixture(params=yes_timeout_ops)
#     def yes_timeout_op(self, request, mocker):
#         op = make_mock_op_or_event(request.param)
#         mocker.spy(op, "complete")
#         return op

#     @pytest.fixture(params=no_timeout_ops)
#     def no_timeout_op(self, request, mocker):
#         op = make_mock_op_or_event(request.param)
#         return op

#     @pytest.fixture
#     def stage(self):
#         return pipeline_stages_base.OpTimeoutStage()

#     @pytest.mark.it("Sends ops that don't need a timer to the next stage")
#     def test_sends_no_timer_op_down(self, stage, mock_timer, no_timeout_op):
#         stage.run_op(no_timeout_op)
#         assert stage.next.run_op.call_count == 1
#         assert stage.next.run_op.call_args[0][0] == no_timeout_op

#     @pytest.mark.it("Sends ops that do need a timer to the next stage")
#     def test_sends_yes_timer_op_down(self, stage, mock_timer, yes_timeout_op):
#         stage.run_op(yes_timeout_op)
#         assert stage.next.run_op.call_count == 1
#         assert stage.next.run_op.call_args[0][0] == yes_timeout_op

#     @pytest.mark.it("Does not set a timer for ops that don't need a timer set")
#     def test_does_not_set_timer(self, stage, mock_timer, no_timeout_op):
#         stage.run_op(no_timeout_op)
#         assert mock_timer.call_count == 0

#     @pytest.mark.it("Set a timer for ops that need a timer set")
#     def test_sets_timer(self, stage, mock_timer, yes_timeout_op):
#         stage.run_op(yes_timeout_op)
#         assert mock_timer.call_count == 1

#     @pytest.mark.it("Starts the timer based on the timeout interval")
#     def test_uses_timeout_interval(self, stage, mock_timer, yes_timeout_op):
#         stage.run_op(yes_timeout_op)
#         assert mock_timer.call_args[0][0] == timeout_intervals[yes_timeout_op.__class__]
#         assert mock_timer.return_value.start.call_count == 1
#         assert yes_timeout_op.timeout_timer == mock_timer.return_value

#     @pytest.mark.it("Clears the timer when the op completes successfully")
#     def test_clears_timer_on_success(self, stage, mock_timer, yes_timeout_op):
#         stage.run_op(yes_timeout_op)
#         yes_timeout_op.complete()
#         assert mock_timer.return_value.cancel.call_count == 1
#         assert getattr(yes_timeout_op, "timeout_timer", None) is None

#     @pytest.mark.it("Clears the timer when the op fails with an arbitrary exception")
#     def test_clears_timer_on_arbitrary_exception(
#         self, stage, mock_timer, yes_timeout_op, arbitrary_exception
#     ):
#         stage.run_op(yes_timeout_op)
#         yes_timeout_op.complete(error=arbitrary_exception)
#         assert mock_timer.return_value.cancel.call_count == 1
#         assert getattr(yes_timeout_op, "timeout_timer", None) is None

#     @pytest.mark.it("Clears the timer when the op times out")
#     def test_clears_timer_on_timeout(self, stage, mock_timer, yes_timeout_op):
#         stage.run_op(yes_timeout_op)
#         assert yes_timeout_op.timeout_timer == mock_timer.return_value
#         timer_callback = mock_timer.call_args[0][1]
#         timer_callback()
#         assert getattr(yes_timeout_op, "timeout_timer", None) is None

#     @pytest.mark.it("Completes the operation with a PipelineTimeoutError when the op times out")
#     def test_calls_callback_on_timeout(self, mocker, stage, mock_timer, yes_timeout_op):
#         stage.run_op(yes_timeout_op)
#         timer_callback = mock_timer.call_args[0][1]
#         timer_callback()
#         assert yes_timeout_op.complete.call_count == 1
#         assert (
#             type(yes_timeout_op.complete.call_args[1]["error"])
#             is pipeline_exceptions.PipelineTimeoutError
#         )


# """
# A note on terms in the RetryStage tests:
#     No-retry ops are ops that will never be retried.
#     Yes-retry ops are ops that might be retired, depending on the error.
#     Retry errors are errors that cause a retry for yes-retry ops
#     Arbitrary errors will never cause a retry
# """

# retry_intervals = {
#     pipeline_ops_mqtt.MQTTSubscribeOperation: 20,
#     pipeline_ops_mqtt.MQTTUnsubscribeOperation: 20,
#     pipeline_ops_base.ConnectOperation: 20,
#     pipeline_ops_mqtt.MQTTPublishOperation: 20,
# }
# yes_retry_ops = list(retry_intervals.keys())
# no_retry_ops = all_except(all_common_ops, yes_retry_ops)
# retry_errors = [pipeline_exceptions.PipelineTimeoutError]

# # pipeline_stage_test.add_base_pipeline_stage_tests(
# #     cls=pipeline_stages_base.RetryStage,
# #     module=this_module,
# #     all_ops=all_common_ops,
# #     handled_ops=[],
# #     all_events=all_common_events,
# #     handled_events=[],
# #     extra_initializer_defaults={"retry_intervals": retry_intervals, "ops_waiting_to_retry": []},
# # )


# class RetryStageTestOpSend(object):
#     """
#     Tests for RetryStage to verify that ops get sent down
#     """

#     @pytest.fixture(params=no_retry_ops)
#     def no_retry_op(self, request, mocker):
#         op = make_mock_op_or_event(request.param)
#         mocker.spy(op, "complete")
#         return op

#     @pytest.fixture(params=yes_retry_ops)
#     def yes_retry_op(self, request, mocker):
#         op = make_mock_op_or_event(request.param)
#         mocker.spy(op, "complete")
#         return op

#     @pytest.mark.it("Sends ops that don't need retry to the next stage")
#     def test_sends_no_retry_op_down(self, stage, no_retry_op):
#         stage.run_op(no_retry_op)
#         assert stage.next.run_op.call_count == 1
#         assert stage.next.run_op.call_args[0][0] == no_retry_op

#     @pytest.mark.it("Sends ops that do need retry to the next stage")
#     def test_sends_yes_retry_op_down(self, stage, yes_retry_op):
#         stage.run_op(yes_retry_op)
#         assert stage.next.run_op.call_count == 1
#         assert stage.next.run_op.call_args[0][0] == yes_retry_op


# class RetryStageTestNoRetryOpSetTimer(object):
#     """
#     Tests for RetryStage for not setting a timer for no-retry ops
#     """

#     # CT-TODO: this needs to be in a general class, not the specific one
#     @pytest.fixture(params=retry_errors)
#     def retry_error(self, request):
#         return request.param()

#     @pytest.mark.it("Does not set a retry timer when an op that doesn't need retry succeeds")
#     def test_no_timer_on_no_retry_op_success(self, stage, no_retry_op, mock_timer):
#         stage.run_op(no_retry_op)
#         no_retry_op.complete()
#         assert mock_timer.call_count == 0

#     @pytest.mark.it(
#         "Does not set a retry timer when an op that doesn't need retry fail with an arbitrary error"
#     )
#     def test_no_timer_on_no_retry_op_arbitrary_exception(
#         self, stage, no_retry_op, arbitrary_exception, mock_timer
#     ):
#         stage.run_op(no_retry_op)
#         no_retry_op.complete(error=arbitrary_exception)
#         assert mock_timer.call_count == 0

#     @pytest.mark.it(
#         "Does not set a retry timer when an op that doesn't need retry fail with a retry error"
#     )
#     def test_no_timer_on_no_retry_op_retry_error(self, stage, no_retry_op, retry_error, mock_timer):
#         stage.run_op(no_retry_op)
#         no_retry_op.complete(error=retry_error)
#         assert mock_timer.call_count == 0


# class RetryStageTestYesRetryOpSetTimer(object):
#     """
#     Tests for RetryStage for setting or not setting timers for yes-retry ops
#     """

#     @pytest.mark.it("Does not set a retry timer when an op that need retry succeeds")
#     def test_no_timer_on_yes_retry_op_success(self, stage, yes_retry_op, mock_timer):
#         stage.run_op(yes_retry_op)
#         yes_retry_op.complete()
#         assert mock_timer.call_count == 0

#     @pytest.mark.it(
#         "Does not set a retry timer when an op that need retry fail with an arbitrary error"
#     )
#     def test_no_timer_on_yes_retry_op_arbitrary_exception(
#         self, stage, yes_retry_op, arbitrary_exception, mock_timer
#     ):
#         stage.run_op(yes_retry_op)
#         yes_retry_op.complete(error=arbitrary_exception)
#         assert mock_timer.call_count == 0

#     @pytest.mark.it("Sets a retry timer when an op that need retry fail with retry error")
#     def test_yes_timer_on_yes_retry_op_retry_error(
#         self, stage, yes_retry_op, retry_error, mock_timer
#     ):
#         stage.run_op(yes_retry_op)
#         yes_retry_op.complete(error=retry_error)
#         assert mock_timer.call_count == 1

#     @pytest.mark.it("Uses the correct timout when setting a retry timer")
#     def test_uses_correct_timer_interval(self, stage, yes_retry_op, retry_error, mock_timer):
#         stage.run_op(yes_retry_op)
#         yes_retry_op.complete(error=retry_error)
#         assert mock_timer.call_args[0][0] == retry_intervals[yes_retry_op.__class__]


# class RetryStageTestResubmitOp(object):
#     """
#     Tests for RetryStage for resubmiting ops for retry
#     """

#     @pytest.mark.it("Retries execution of an op that needs retry after the retry interval elapses")
#     def test_resubmits_after_retry_interval_elapses(
#         self, stage, yes_retry_op, retry_error, mock_timer
#     ):
#         stage.run_op(yes_retry_op)
#         assert stage.next.run_op.call_count == 1
#         stage.next.run_op.reset_mock()
#         yes_retry_op.complete(error=retry_error)
#         timer_callback = mock_timer.call_args[0][1]
#         timer_callback()
#         assert stage.next.run_op.call_count == 1
#         assert stage.next.run_op.call_args[0][0] == yes_retry_op

#     @pytest.mark.it("Resets the operation to an incomplete state if retry is required")
#     def test_clears_complete_attribute_before_resubmitting(
#         self, stage, yes_retry_op, retry_error, mock_timer
#     ):
#         stage.run_op(yes_retry_op)
#         yes_retry_op.complete(error=retry_error)
#         assert not yes_retry_op.completed

#     @pytest.mark.it("Clears the retry timer attribute on the op when retrying")
#     def test_clears_retry_timer_before_retrying(self, stage, yes_retry_op, retry_error, mock_timer):
#         stage.run_op(yes_retry_op)
#         yes_retry_op.complete(error=retry_error)
#         assert yes_retry_op.retry_timer
#         timer_callback = mock_timer.call_args[0][1]
#         timer_callback()
#         assert mock_timer.return_value.cancel.call_count == 1
#         assert getattr(yes_retry_op, "retry_timer", None) is None

#     # CT-TODO: reconsider if this test is necessary
#     @pytest.mark.it(
#         "Sets a new retry timer error when the retried op completes with an retry error"
#     )
#     def test_sets_timer_on_retried_op_retry_error(
#         self, stage, yes_retry_op, retry_error, mock_timer
#     ):
#         stage.run_op(yes_retry_op)
#         yes_retry_op.complete(error=retry_error)
#         assert mock_timer.call_count == 1
#         timer_callback = mock_timer.call_args[0][1]
#         timer_callback()
#         yes_retry_op.complete(error=retry_error)
#         assert mock_timer.call_count == 2


# @pytest.mark.describe("RetryStage - run_op()")
# class TestRetryStageRunOp(
#     StageTestBase,
#     RetryStageTestOpSend,
#     RetryStageTestNoRetryOpSetTimer,
#     RetryStageTestYesRetryOpSetTimer,
#     RetryStageTestResubmitOp,
# ):
#     @pytest.fixture
#     def stage(self):
#         return pipeline_stages_base.RetryStage()


# # pipeline_stage_test.add_base_pipeline_stage_tests(
# #     cls=pipeline_stages_base.ReconnectStage,
# #     module=this_module,
# #     all_ops=all_common_ops,
# #     handled_ops=[],
# #     all_events=all_common_events,
# #     handled_events=[],
# #     extra_initializer_defaults={
# #         "reconnect_timer": None,
# #         "virtually_connected": False,
# #         "reconnect_delay": 10,
# #     },
# # )


# @pytest.mark.describe("ReconnectStage - .run_op()")
# class TestReconnectStageRunOp(StageTestBase):
#     @pytest.fixture
#     def stage(self):
#         return pipeline_stages_base.ReconnectStage()

#     @pytest.mark.it(
#         "Sets the stage virtually_connected attribute to True when a ConnectOperation is sent down"
#     )
#     def test_connect_op_virtual_connection(self, mocker, stage):
#         op = pipeline_ops_base.ConnectOperation(mocker.MagicMock())
#         assert not stage.virtually_connected
#         stage.run_op(op)
#         assert stage.virtually_connected

#     @pytest.mark.it(
#         "Keeps the stage virtually_connected attribute set to True, even if the ConnectOperation fails"
#     )
#     def test_connect_op_virtual_connection_failure(self, mocker, stage, arbitrary_exception):
#         op = pipeline_ops_base.ConnectOperation(mocker.MagicMock())
#         mocker.spy(op, "complete")
#         stage.next._run_op = mocker.MagicMock(side_effect=arbitrary_exception)
#         stage.run_op(op)
#         assert op.complete.call_count == 1
#         assert op.complete.call_args == mocker.call(error=arbitrary_exception)
#         assert stage.virtually_connected

#     @pytest.mark.it(
#         "Sets the stage virtually_connected attribute to False when a DisconnectOperation is sent down"
#     )
#     def test_disconnect_op_virtual_connection(self, mocker, stage):
#         op = pipeline_ops_base.DisconnectOperation(mocker.MagicMock())
#         stage.virtually_connected = True
#         stage.run_op(op)
#         assert not stage.virtually_connected

#     @pytest.mark.it(
#         "Keeps the stage virtually_connected attribute set to False, even if the DisconnectOperation fails"
#     )
#     def test_disconnect_op_virtual_connection_failure(self, mocker, stage, arbitrary_exception):
#         op = pipeline_ops_base.DisconnectOperation(mocker.MagicMock())
#         mocker.spy(op, "complete")
#         stage.virtually_connected = True
#         stage.next._run_op = mocker.MagicMock(side_effect=arbitrary_exception)
#         stage.run_op(op)
#         assert op.complete.call_count == 1
#         assert op.complete.call_args == mocker.call(error=arbitrary_exception)
#         assert not stage.virtually_connected


# @pytest.mark.describe("ReconnectStage - .on_connected()")
# class TestReconnectStageOnConnected(StageTestBase):
#     @pytest.fixture
#     def stage(self):
#         return pipeline_stages_base.ReconnectStage()

#     @pytest.mark.it("Clears any reconnect timers that may be running")
#     def test_clears_reconnect_timer(self, stage, mock_timer):
#         timer = mock_timer.return_value
#         stage.reconnect_timer = timer
#         assert timer.cancel.call_count == 0
#         stage.on_connected()
#         assert stage.reconnect_timer is None
#         assert mock_timer.return_value.cancel.call_count == 1

#     @pytest.mark.it("Does not fail if there there are no pending reconnect timers")
#     def test_succeeds_if_no_reconnect_timer(self, stage, mock_timer):
#         stage.on_connected()
#         assert mock_timer.return_value.cancel.call_count == 0

#     @pytest.mark.it("Calls the previous stage on_connected handler if there was a pending timer")
#     def test_calls_previous_stage_on_connected(self, mocker, stage, mock_timer):
#         mocker.spy(stage.previous, "on_connected")
#         stage.reconnect_timer = mock_timer.return_value
#         assert stage.previous.on_connected.call_count == 0
#         stage.on_connected()
#         assert stage.previous.on_connected.call_count == 1

#     @pytest.mark.it(
#         "Calls the previous stage on_connected handler if there was not a pending_timer"
#     )
#     def test_calls_previous_stage_on_connected_without_timer(self, mocker, stage):
#         mocker.spy(stage.previous, "on_connected")
#         assert stage.previous.on_connected.call_count == 0
#         stage.on_connected()
#         assert stage.previous.on_connected.call_count == 1


# default_reconnect_time = 10


# @pytest.mark.describe("ReconnectStage - .on_disconnected()")
# class TestReconnectStageOnDisconnected(StageTestBase):
#     @pytest.fixture
#     def stage(self):
#         return pipeline_stages_base.ReconnectStage()

#     @pytest.mark.it(
#         "Clears a previous reconnect timer if the stage virtually_connected attribute is set to True"
#     )
#     def test_clears_previous_reconnect_timer_if_virtually_connected(self, stage, mock_timer):
#         timer = mock_timer.return_value
#         stage.reconnect_timer = timer
#         stage.virtually_connected = True
#         stage.on_disconnected()
#         stage.reconnect_timer is None
#         timer.cancel.call_count == 1

#     @pytest.mark.it(
#         "Sets a reconnect timer if the stage virtually_connected attribute is set to True"
#     )
#     def test_sets_new_reconnect_timer_if_virtually_connected(self, stage, mock_timer):
#         stage.virtually_connected = True
#         stage.pipeline_root.connected = True
#         stage.on_disconnected()
#         assert stage.reconnect_timer == mock_timer.return_value
#         assert mock_timer.call_count == 1
#         assert mock_timer.call_args[0][0] == default_reconnect_time

#     @pytest.mark.it(
#         "Does not set a reconnect timer if the stage virtually_connected attribute is set to False"
#     )
#     def test_does_not_set_reconnect_timer_if_not_virtually_connected(self, stage, mock_timer):
#         stage.on_disconnected()
#         assert stage.reconnect_timer is None
#         assert mock_timer.call_count == 0

#     @pytest.mark.it(
#         "Calls the previous stage on_disconnected handler if the stage virtually_connected attribute is set to True"
#     )
#     def test_calls_previous_stage_on_disconnected_virtually_connected(
#         self, mocker, stage, mock_timer
#     ):
#         mocker.spy(stage.previous, "on_disconnected")
#         stage.pipeline_root.connected = True
#         stage.virtually_connected = True
#         stage.on_disconnected()
#         assert stage.previous.on_disconnected.call_count == 1

#     @pytest.mark.it(
#         "Calls the previous stage on_disconnected handler if the stage virtually_connected attribute is set to False"
#     )
#     def test_calls_previous_stage_on_disconnected_not_virtually_connected(
#         self, mocker, stage, mock_timer
#     ):
#         mocker.spy(stage.previous, "on_disconnected")
#         stage.on_disconnected()
#         assert stage.previous.on_disconnected.call_count == 1


# class ArbitraryException(Exception):
#     pass


# @pytest.mark.describe("ReconnectStage - reconnect timer routine")
# class TestReconnectStageReconnectTimerRoutine(StageTestBase):
#     @pytest.fixture
#     def stage(self):
#         return pipeline_stages_base.ReconnectStage()

#     @pytest.fixture
#     def timer_routine(self, stage, mock_timer):
#         stage.virtually_connected = True
#         stage.pipeline_root.connected = True
#         stage.on_disconnected()
#         return mock_timer.call_args[0][1]

#     @pytest.mark.it("Runs in the pipeline thread with nowait")
#     def test_invokes_on_pipeline_thread(
#         self, mocker, stage, timer_routine, fake_non_pipeline_thread
#     ):
#         done = threading.Event()
#         stage.pipeline_root.connected = False
#         names = {"thread_name": None}

#         def save_thread_name(*args, **kwargs):
#             names["thread_name"] = threading.current_thread().name
#             done.set()

#         logger = mocker.patch.object(pipeline_stages_base, "logger")
#         logger.debug.side_effect = save_thread_name

#         assert threading.current_thread().name != "pipeline"
#         timer_routine()
#         done.wait()
#         assert names["thread_name"] == "pipeline"

#     @pytest.mark.it("Does not send a ConnectOperation down if the transport is already connected")
#     def test_when_connected_does_not_send_connect_operation_down(self, stage, timer_routine):
#         stage.pipeline_root.connected = True
#         timer_routine()
#         assert stage.next.run_op.call_count == 0

#     @pytest.mark.it("Sends a ConnectOperation down if the transport is not connected")
#     def test_when_disconnected_sends_connect_operation_down(self, stage, timer_routine):
#         stage.pipeline_root.connected = False
#         timer_routine()
#         assert stage.next.run_op.call_count == 1
#         assert type(stage.next.run_op.call_args[0][0]) == pipeline_ops_base.ConnectOperation

#     @pytest.mark.parametrize(
#         "error_class",
#         [
#             ArbitraryException,
#             transport_exceptions.UnauthorizedError,
#             transport_exceptions.ProtocolClientError,
#             pipeline_exceptions.PipelineError,
#         ],
#     )
#     @pytest.mark.it(
#         "Does not sets a new reconnect timer if the ConnectOperation fails with an error that probably isn't transient"
#     )
#     def test_does_not_set_new_timer_on_non_transient_connect_error(
#         self, stage, mock_timer, timer_routine, error_class
#     ):
#         stage.pipeline_root.connected = False
#         assert mock_timer.call_count == 1
#         timer_routine()
#         assert stage.next.run_op.call_count == 1
#         op = stage.next.run_op.call_args[0][0]
#         assert type(op) == pipeline_ops_base.ConnectOperation
#         op.complete(error=error_class())
#         assert mock_timer.call_count == 1

#     @pytest.mark.parametrize(
#         "error_class",
#         [
#             pipeline_exceptions.OperationCancelled,
#             pipeline_exceptions.PipelineTimeoutError,
#             transport_exceptions.ConnectionFailedError,
#             transport_exceptions.ConnectionDroppedError,
#         ],
#     )
#     @pytest.mark.it(
#         "Sets a new reconnect timer if the ConnectOperation fails with an error that might be transient"
#     )
#     def test_sets_new_timer_on_transient_connect_error(
#         self, stage, mock_timer, timer_routine, error_class
#     ):
#         stage.pipeline_root.connected = False
#         assert mock_timer.call_count == 1
#         timer_routine()
#         assert stage.next.run_op.call_count == 1
#         op = stage.next.run_op.call_args[0][0]
#         assert type(op) == pipeline_ops_base.ConnectOperation
#         op.complete(error=error_class())
#         assert mock_timer.call_count == 2
