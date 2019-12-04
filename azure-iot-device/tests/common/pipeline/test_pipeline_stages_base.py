# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import logging
import copy
import time
import pytest
import sys
import six
import threading
import random
import uuid
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


###################
# COMMON FIXTURES #
###################
@pytest.fixture
def mock_timer(mocker):
    return mocker.patch.object(threading, "Timer")


# Not a fixture, but useful for sharing
def fake_callback(*args, **kwargs):
    pass


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


@pytest.mark.describe(
    "ConnectionLockStage - .run_op() -- Called with an arbitrary other operation while not in a blocking state"
)
class TestConnectionLockStageRunOpWithArbitraryOpWhileUnblocked(
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
        "Adds the operation to the queue, even if the pipeline is in a connection state where the operation is ready for completion"
    )
    @pytest.mark.parametrize(
        "op",
        [pipeline_ops_base.ConnectOperation, pipeline_ops_base.DisconnectOperation],
        indirect=True,
    )
    def test_blocks_ops_ready_for_completion(self, mocker, stage, op):
        # Set the pipeline connection state to be the one desired by the operation.
        # If the stage were unblocked, this would lead to immediate completion of the op.
        if isinstance(op, pipeline_ops_base.ConnectOperation):
            stage.pipeline_root.connected = True
        else:
            stage.pipeline_root.connected = False

        assert stage.queue.empty()

        stage.run_op(op)

        assert not op.completed
        assert stage.queue.qsize() == 1
        assert stage.send_op_down.call_count == 0

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
    def blocked_stage(self, mocker, init_kwargs, blocking_op, pending_ops):
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
    def test_blocking_op_completes_successfully(
        self, mocker, blocked_stage, pending_ops, blocking_op
    ):
        stage = blocked_stage
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
    def test_unblocks_before_rerun(self, mocker, blocked_stage, blocking_op, pending_ops):
        stage = blocked_stage
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

    @pytest.mark.it(
        "Requeues subsequent operations, retaining their original order, if one of the re-run operations returns the ConnectionLockStage to a blocking state"
    )
    def test_unblocked_op_changes_block_state(self, mocker, stage):
        op1 = pipeline_ops_base.ConnectOperation(callback=mocker.MagicMock())
        op2 = ArbitraryOperation(callback=mocker.MagicMock())
        op3 = pipeline_ops_base.ReconnectOperation(callback=mocker.MagicMock())
        op4 = ArbitraryOperation(callback=mocker.MagicMock())
        op5 = ArbitraryOperation(callback=mocker.MagicMock())

        # Block the stage on op1
        assert not stage.pipeline_root.connected
        assert not stage.blocked
        stage.run_op(op1)
        assert stage.blocked
        assert stage.queue.qsize() == 0

        # Run the rest of the ops, which will be added to the queue
        stage.run_op(op2)
        stage.run_op(op3)
        stage.run_op(op4)
        stage.run_op(op5)

        # op1 is the only op that has been passed down so far
        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(op1)
        assert stage.queue.qsize() == 4

        # Complete op1
        op1.complete()

        # Manually set pipeline to be connected (this doesn't happen naturally due to the scope of this test)
        stage.pipeline_root.connected = True

        # op2 and op3 have now been passed down, but no others
        assert stage.send_op_down.call_count == 3
        assert stage.send_op_down.call_args_list[1] == mocker.call(op2)
        assert stage.send_op_down.call_args_list[2] == mocker.call(op3)
        assert stage.queue.qsize() == 2

        # Complete op3
        op3.complete()

        # op4 and op5 are now also passed down
        assert stage.send_op_down.call_count == 5
        assert stage.send_op_down.call_args_list[3] == mocker.call(op4)
        assert stage.send_op_down.call_args_list[4] == mocker.call(op5)
        assert stage.queue.qsize() == 0


@pytest.mark.describe(
    "ConnectionLockStage - EVENT: Operation blocking ConnectionLockStage is completed with error"
)
class TestConnectionLockStageBlockingOpCompletedWithError(
    ConnectionLockStageBlockingOpCompletedTestConfig
):
    # CT-TODO: Show that completion occurs in FIFO order
    @pytest.mark.it("Completes all pending operations with the error from the blocking operation")
    def test_blocking_op_completes_with_error(
        self, blocked_stage, pending_ops, blocking_op, arbitrary_exception
    ):
        stage = blocked_stage

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
        self, mocker, blocked_stage, pending_ops, blocking_op, arbitrary_exception
    ):
        stage = blocked_stage
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


#########################################
# COORDINATE REQUEST AND RESPONSE STAGE #
#########################################


@pytest.fixture
def fake_uuid(mocker):
    my_uuid = "0f4f876b-f445-432e-a8de-43bbd66e4668"
    uuid4_mock = mocker.patch.object(uuid, "uuid4")
    uuid4_mock.return_value.__str__.return_value = my_uuid
    return my_uuid


class CoordinateRequestAndResponseStageTestConfig(object):
    @pytest.fixture
    def cls_type(self):
        return pipeline_stages_base.CoordinateRequestAndResponseStage

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


class CoordinateRequestAndResponseStageInstantiationTests(
    CoordinateRequestAndResponseStageTestConfig
):
    @pytest.mark.it("Initializes 'pending_responses' as an empty dict")
    def test_pending_responses(self, init_kwargs):
        stage = pipeline_stages_base.CoordinateRequestAndResponseStage(**init_kwargs)
        assert stage.pending_responses == {}


pipeline_stage_test.add_base_pipeline_stage_tests(
    test_module=this_module,
    stage_class_under_test=pipeline_stages_base.CoordinateRequestAndResponseStage,
    stage_test_config_class=CoordinateRequestAndResponseStageTestConfig,
    extended_stage_instantiation_test_class=CoordinateRequestAndResponseStageInstantiationTests,
)


@pytest.mark.describe(
    "CoordinateRequestAndResponseStage - .run_op() -- Called with a RequestAndResponseOperation"
)
class TestCoordinateRequestAndResponseStageRunOpWithRequestAndResponseOperation(
    CoordinateRequestAndResponseStageTestConfig, StageRunOpTestBase
):
    @pytest.fixture
    def op(self, mocker):
        return pipeline_ops_base.RequestAndResponseOperation(
            request_type="some_request_type",
            method="SOME_METHOD",
            resource_location="some/resource/location",
            request_body="some_request_body",
            callback=mocker.MagicMock(),
        )

    @pytest.mark.it(
        "Stores the operation in the 'pending_responses' dictionary, mapped with a generated UUID"
    )
    def test_stores_op(self, mocker, stage, op, fake_uuid):
        stage.run_op(op)

        assert stage.pending_responses[fake_uuid] is op
        assert not op.completed

    @pytest.mark.it(
        "Creates and a new RequestOperation using the generated UUID and sends it down the pipeline"
    )
    def test_sends_down_new_request_op(self, mocker, stage, op, fake_uuid):
        stage.run_op(op)

        assert stage.send_op_down.call_count == 1
        request_op = stage.send_op_down.call_args[0][0]
        assert isinstance(request_op, pipeline_ops_base.RequestOperation)
        assert request_op.method == op.method
        assert request_op.resource_location == op.resource_location
        assert request_op.request_body == op.request_body
        assert request_op.request_type == op.request_type
        assert request_op.request_id == fake_uuid

    @pytest.mark.it(
        "Generates a unique UUID for each RequestAndResponseOperation/RequestOperation pair"
    )
    def test_unique_uuid(self, mocker, stage, op):
        op1 = op
        op2 = copy.deepcopy(op)
        op3 = copy.deepcopy(op)

        stage.run_op(op1)
        assert stage.send_op_down.call_count == 1
        uuid1 = stage.send_op_down.call_args[0][0].request_id
        stage.run_op(op2)
        assert stage.send_op_down.call_count == 2
        uuid2 = stage.send_op_down.call_args[0][0].request_id
        stage.run_op(op3)
        assert stage.send_op_down.call_count == 3
        uuid3 = stage.send_op_down.call_args[0][0].request_id

        assert uuid1 != uuid2 != uuid3
        assert stage.pending_responses[uuid1] is op1
        assert stage.pending_responses[uuid2] is op2
        assert stage.pending_responses[uuid3] is op3


@pytest.mark.describe(
    "CoordinateRequestAndResponseStage - .run_op() -- Called with an arbitrary other operation"
)
class TestCoordinateRequestAndResponseStageRunOpWithArbitraryOp(
    CoordinateRequestAndResponseStageTestConfig, StageRunOpTestBase
):
    @pytest.fixture
    def op(self, arbitrary_op):
        return arbitrary_op

    @pytest.mark.it("Sends the operation down the pipeline")
    def test_sends_down(self, stage, mocker, op):
        stage.run_op(op)

        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(op)


@pytest.mark.describe(
    "CoordinateRequestAndResponseStage - EVENT: RequestOperation tied to a stored RequestAndResponseOperation is completed"
)
class TestCoordinateRequestAndResponseStageRequestOperationCompleted(
    CoordinateRequestAndResponseStageTestConfig
):
    @pytest.fixture
    def op(self, mocker):
        return pipeline_ops_base.RequestAndResponseOperation(
            request_type="some_request_type",
            method="SOME_METHOD",
            resource_location="some/resource/location",
            request_body="some_request_body",
            callback=mocker.MagicMock(),
        )

    @pytest.mark.it(
        "Completes the associated RequestAndResponseOperation with the error from the RequestOperation and removes it from the 'pending_responses' dict, if the RequestOperation is completed unsuccessfully"
    )
    def test_request_completed_with_error(self, mocker, stage, op, arbitrary_exception):
        stage.run_op(op)
        request_op = stage.send_op_down.call_args[0][0]

        assert not op.completed
        assert not request_op.completed
        assert stage.pending_responses[request_op.request_id] is op

        request_op.complete(error=arbitrary_exception)

        # RequestAndResponseOperation has been completed with the error from the RequestOperation
        assert request_op.completed
        assert op.completed
        assert op.error is request_op.error is arbitrary_exception

        # RequestAndResponseOperation has been removed from the 'pending_responses' dict
        with pytest.raises(KeyError):
            stage.pending_responses[request_op.request_id]

    @pytest.mark.it(
        "Does not complete or remove the RequestAndResponseOperation from the 'pending_responses' dict if the RequestOperation is completed successfully"
    )
    def test_request_completed_successfully(self, mocker, stage, op, arbitrary_exception):
        stage.run_op(op)
        request_op = stage.send_op_down.call_args[0][0]

        request_op.complete()

        assert request_op.completed
        assert not op.completed
        assert stage.pending_responses[request_op.request_id] is op


@pytest.mark.describe(
    "CoordinateRequestAndResponseStage - .handle_pipeline_event() -- Called with ResponseEvent"
)
class TestCoordinateRequestAndResponseStageHandlePipelineEventWithResponseEvent(
    CoordinateRequestAndResponseStageTestConfig, StageHandlePipelineEventTestBase
):
    @pytest.fixture
    def event(self, fake_uuid):
        return pipeline_events_base.ResponseEvent(
            request_id=fake_uuid, status_code=200, response_body="response body"
        )

    @pytest.fixture
    def pending_op(self, mocker):
        return pipeline_ops_base.RequestAndResponseOperation(
            request_type="some_request_type",
            method="SOME_METHOD",
            resource_location="some/resource/location",
            request_body="some_request_body",
            callback=mocker.MagicMock(),
        )

    @pytest.fixture
    def stage(self, mocker, cls_type, init_kwargs, fake_uuid, pending_op):
        stage = cls_type(**init_kwargs)
        stage.pipeline_root = pipeline_stages_base.PipelineRootStage(
            pipeline_configuration=mocker.MagicMock()
        )
        stage.send_event_up = mocker.MagicMock()
        stage.send_op_down = mocker.MagicMock()

        # Run the pending op
        stage.run_op(pending_op)
        return stage

    @pytest.mark.it(
        "Successfully completes a pending RequestAndResponseOperation that matches the 'request_id' of the ResponseEvent, and removes it from the 'pending_responses' dictionary"
    )
    def test_completes_matching_request_and_response_operation(
        self, mocker, stage, pending_op, event, fake_uuid
    ):
        assert stage.pending_responses[fake_uuid] is pending_op
        assert not pending_op.completed

        # Handle the ResponseEvent
        assert event.request_id == fake_uuid
        stage.handle_pipeline_event(event)

        # The pending RequestAndResponseOperation is complete
        assert pending_op.completed

        # The RequestAndResponseOperation has been removed from the dictionary
        with pytest.raises(KeyError):
            stage.pending_responses[fake_uuid]

    @pytest.mark.it(
        "Sets the 'status_code' and 'response_body' attributes on the completed RequestAndResponseOperation with values from the ResponseEvent"
    )
    def test_returns_values_in_attributes(self, mocker, stage, pending_op, event):
        assert not pending_op.completed
        assert pending_op.status_code is None
        assert pending_op.response_body is None

        stage.handle_pipeline_event(event)

        assert pending_op.completed
        assert pending_op.status_code == event.status_code
        assert pending_op.response_body == event.response_body

    @pytest.mark.it(
        "Does nothing if there is no pending RequestAndResponseOperation that matches the 'request_id' of the ResponseEvent"
    )
    def test_no_matching_request_id(self, mocker, stage, pending_op, event, fake_uuid):
        assert stage.pending_responses[fake_uuid] is pending_op
        assert not pending_op.completed

        # Use a nonmatching UUID
        event.request_id = "non-matching-uuid"
        assert event.request_id != fake_uuid
        stage.handle_pipeline_event(event)

        # Nothing has changed
        assert stage.pending_responses[fake_uuid] is pending_op
        assert not pending_op.completed


@pytest.mark.describe(
    "CoordinateRequestAndResponseStage - .handle_pipeline_event() -- Called with arbitrary other event"
)
class TestCoordinateRequestAndResponseStageHandlePipelineEventWithArbitraryEvent(
    CoordinateRequestAndResponseStageTestConfig, StageHandlePipelineEventTestBase
):
    @pytest.fixture
    def event(self, arbitrary_event):
        return arbitrary_event

    @pytest.mark.it("Sends the event up the pipeline")
    def test_sends_up(self, mocker, stage, event):
        stage.handle_pipeline_event(event)

        assert stage.send_event_up.call_count == 1
        assert stage.send_event_up.call_args == mocker.call(event)


####################
# OP TIMEOUT STAGE #
####################

ops_that_time_out = [
    pipeline_ops_mqtt.MQTTSubscribeOperation,
    pipeline_ops_mqtt.MQTTUnsubscribeOperation,
]


class OpTimeoutStageTestConfig(object):
    @pytest.fixture
    def cls_type(self):
        return pipeline_stages_base.OpTimeoutStage

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


class OpTimeoutStageInstantiationTests(OpTimeoutStageTestConfig):
    # TODO: this will no longer be necessary once these are implemented as part of a more robust retry policy
    @pytest.mark.it(
        "Sets default timout intervals to 10 seconds for MQTTSubscribeOperation and MQTTUnsubscribeOperation"
    )
    def test_timeout_intervals(self, init_kwargs):
        stage = pipeline_stages_base.OpTimeoutStage(**init_kwargs)
        assert stage.timeout_intervals[pipeline_ops_mqtt.MQTTSubscribeOperation] == 10
        assert stage.timeout_intervals[pipeline_ops_mqtt.MQTTUnsubscribeOperation] == 10


pipeline_stage_test.add_base_pipeline_stage_tests(
    test_module=this_module,
    stage_class_under_test=pipeline_stages_base.OpTimeoutStage,
    stage_test_config_class=OpTimeoutStageTestConfig,
    extended_stage_instantiation_test_class=OpTimeoutStageInstantiationTests,
)


@pytest.mark.describe("OpTimeoutStage - .run_op() -- Called with operation eligible for timeout")
class TestOpTimeoutStageRunOpCalledWithOpThatCanTimeout(
    OpTimeoutStageTestConfig, StageRunOpTestBase
):
    @pytest.fixture(params=ops_that_time_out)
    def op(self, mocker, request):
        op_cls = request.param
        op = op_cls(topic="some/topic", callback=mocker.MagicMock())
        return op

    @pytest.mark.it(
        "Adds a timeout timer with the interval specified in the configuration to the operation, and starts it"
    )
    def test_adds_timer(self, mocker, stage, op, mock_timer):

        stage.run_op(op)

        assert mock_timer.call_count == 1
        assert mock_timer.call_args == mocker.call(stage.timeout_intervals[type(op)], mocker.ANY)
        assert op.timeout_timer is mock_timer.return_value
        assert op.timeout_timer.start.call_count == 1
        assert op.timeout_timer.start.call_args == mocker.call()

    @pytest.mark.it("Sends the operation down the pipeline")
    def test_sends_down(self, mocker, stage, op, mock_timer):
        stage.run_op(op)

        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(op)
        assert op.timeout_timer is mock_timer.return_value


@pytest.mark.describe(
    "OpTimeoutStage - .run_op() -- Called with arbitrary operation that is not eligible for timeout"
)
class TestOpTimeoutStageRunOpCalledWithOpThatDoesNotTimeout(
    OpTimeoutStageTestConfig, StageRunOpTestBase
):
    @pytest.fixture
    def op(self, arbitrary_op):
        return arbitrary_op

    @pytest.mark.it("Sends the operation down the pipeline without attaching a timeout timer")
    def test_sends_down(self, mocker, stage, op, mock_timer):
        stage.run_op(op)

        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(op)
        assert mock_timer.call_count == 0
        assert not hasattr(op, "timeout_timer")


@pytest.mark.describe(
    "OpTimeoutStage - EVENT: Operation with a timeout timer times out before completion"
)
class TestOpTimeoutStageOpTimesOut(OpTimeoutStageTestConfig):
    @pytest.fixture(params=ops_that_time_out)
    def op(self, mocker, request):
        op_cls = request.param
        op = op_cls(topic="some/topic", callback=mocker.MagicMock())
        return op

    @pytest.mark.it("Completes the operation unsuccessfully, with a PiplineTimeoutError")
    def test_pipeline_timeout(self, mocker, stage, op, mock_timer):
        # Apply the timer
        stage.run_op(op)
        assert not op.completed
        assert mock_timer.call_count == 1
        on_timer_complete = mock_timer.call_args[0][1]

        # Call timer complete callback (indicating timer completion)
        on_timer_complete()

        # Op is now completed with error
        assert op.completed
        assert isinstance(op.error, pipeline_exceptions.PipelineTimeoutError)


@pytest.mark.describe(
    "OpTimeoutStage - EVENT: Operation with a timeout timer completes before timeout"
)
class TestOpTimeoutStageOpCompletesBeforeTimeout(OpTimeoutStageTestConfig):
    @pytest.fixture(params=ops_that_time_out)
    def op(self, mocker, request):
        op_cls = request.param
        op = op_cls(topic="some/topic", callback=mocker.MagicMock())
        return op

    @pytest.mark.it("Cancels and clears the operation's timeout timer")
    def test_complete_before_timeout(self, mocker, stage, op, mock_timer):
        # Apply the timer
        stage.run_op(op)
        assert not op.completed
        assert mock_timer.call_count == 1
        mock_timer_inst = op.timeout_timer
        assert mock_timer_inst is mock_timer.return_value
        assert mock_timer_inst.cancel.call_count == 0

        # Complete the operation
        op.complete()

        # Timer is now cancelled and cleared
        assert mock_timer_inst.cancel.call_count == 1
        assert mock_timer_inst.cancel.call_args == mocker.call()
        assert op.timeout_timer is None


###############
# RETRY STAGE #
###############

# Tuples of classname + args
retryable_ops = [
    (pipeline_ops_mqtt.MQTTSubscribeOperation, {"topic": "fake_topic", "callback": fake_callback}),
    (
        pipeline_ops_mqtt.MQTTUnsubscribeOperation,
        {"topic": "fake_topic", "callback": fake_callback},
    ),
    (
        pipeline_ops_mqtt.MQTTPublishOperation,
        {"topic": "fake_topic", "payload": "fake_payload", "callback": fake_callback},
    ),
    (pipeline_ops_base.ConnectOperation, {"callback": fake_callback}),
]

retryable_exceptions = [
    pipeline_exceptions.PipelineTimeoutError,
    transport_exceptions.ConnectionDroppedError,
    transport_exceptions.ConnectionFailedError,
]


class RetryStageTestConfig(object):
    @pytest.fixture
    def cls_type(self):
        return pipeline_stages_base.RetryStage

    @pytest.fixture
    def init_kwargs(self, mocker):
        return {}

    @pytest.fixture
    def stage(self, mocker, cls_type, init_kwargs):
        stage = cls_type(**init_kwargs)
        stage.pipeline_root = pipeline_stages_base.PipelineRootStage(
            pipeline_configuration=mocker.MagicMock()
        )
        mocker.spy(stage, "run_op")
        stage.send_op_down = mocker.MagicMock()
        stage.send_event_up = mocker.MagicMock()
        return stage


class RetryStageInstantiationTests(RetryStageTestConfig):
    # TODO: this will no longer be necessary once these are implemented as part of a more robust retry policy
    @pytest.mark.it(
        "Sets default retry intervals to 20 seconds for MQTTSubscribeOperation, MQTTUnsubscribeOperation, MQTTPublishOperation and ConnectOperation"
    )
    def test_retry_intervals(self, init_kwargs):
        stage = pipeline_stages_base.RetryStage(**init_kwargs)
        assert stage.retry_intervals[pipeline_ops_mqtt.MQTTSubscribeOperation] == 20
        assert stage.retry_intervals[pipeline_ops_mqtt.MQTTUnsubscribeOperation] == 20
        assert stage.retry_intervals[pipeline_ops_mqtt.MQTTPublishOperation] == 20
        assert stage.retry_intervals[pipeline_ops_base.ConnectOperation] == 20

    @pytest.mark.it("Initializes 'ops_waiting_to_retry' as an empty list")
    def test_ops_waiting_to_retry(self, init_kwargs):
        stage = pipeline_stages_base.RetryStage(**init_kwargs)
        assert stage.ops_waiting_to_retry == []


pipeline_stage_test.add_base_pipeline_stage_tests(
    test_module=this_module,
    stage_class_under_test=pipeline_stages_base.RetryStage,
    stage_test_config_class=RetryStageTestConfig,
    extended_stage_instantiation_test_class=RetryStageInstantiationTests,
)


# NOTE: Although there is a branch in the implementation that distinguishes between
# retryable operations, and non-retryable operations, with retryable operations having
# a callback added, this is not captured in this test, as callback resolution is tested
# in a different unit.
@pytest.mark.describe("RetryStage - .run_op()")
class TestRetryStageRunOp(RetryStageTestConfig, StageRunOpTestBase):
    ops = retryable_ops + [(ArbitraryOperation, {"callback": fake_callback})]

    @pytest.fixture(params=ops, ids=[x[0].__name__ for x in ops])
    def op(self, request, mocker):
        op_cls = request.param[0]
        init_kwargs = request.param[1]
        return op_cls(**init_kwargs)

    @pytest.mark.it("Sends the operation down the pipeline")
    def test_sends_op_down(self, mocker, stage, op):
        stage.run_op(op)

        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(op)


@pytest.mark.describe(
    "RetryStage - EVENT: Retryable operation completes unsuccessfully with a retryable error after call to .run_op()"
)
class TestRetryStageRetryableOperationCompletedWithRetryableError(RetryStageTestConfig):
    @pytest.fixture(params=retryable_ops, ids=[x[0].__name__ for x in retryable_ops])
    def op(self, request, mocker):
        op_cls = request.param[0]
        init_kwargs = request.param[1]
        return op_cls(**init_kwargs)

    @pytest.fixture(params=retryable_exceptions)
    def error(self, request):
        return request.param()

    @pytest.mark.it("Halts operation completion")
    def test_halt(self, mocker, stage, op, error, mock_timer):
        stage.run_op(op)
        op.complete(error=error)

        assert not op.completed

    @pytest.mark.it(
        "Adds a retry timer to the operation with the interval specified for the operation by the configuration, and starts it"
    )
    def test_timer(self, mocker, stage, op, error, mock_timer):
        stage.run_op(op)
        op.complete(error=error)

        assert mock_timer.call_count == 1
        assert mock_timer.call_args == mocker.call(stage.retry_intervals[type(op)], mocker.ANY)
        assert op.retry_timer is mock_timer.return_value
        assert op.retry_timer.start.call_count == 1
        assert op.retry_timer.start.call_args == mocker.call()

    @pytest.mark.it(
        "Adds the operation to the list of 'ops_waiting_to_retry' only for the duration of the timer"
    )
    def test_adds_to_waiting_list_during_timer(self, mocker, stage, op, error, mock_timer):
        stage.run_op(op)

        # The op is not listed as waiting for retry before completion
        assert op not in stage.ops_waiting_to_retry

        # Completing the op starts the timer
        op.complete(error=error)
        assert mock_timer.call_count == 1
        timer_callback = mock_timer.call_args[0][1]
        assert mock_timer.return_value.start.call_count == 1

        # Once completed and the timer has been started, the op IS listed as waiting for retry
        assert op in stage.ops_waiting_to_retry

        # Simulate timer completion
        timer_callback()

        # Once the timer is completed, the op is no longer listed as waiting for retry
        assert op not in stage.ops_waiting_to_retry

    @pytest.mark.it("Re-runs the operation after the retry timer expires")
    def test_reruns(self, mocker, stage, op, error, mock_timer):
        stage.run_op(op)
        op.complete(error=error)

        assert stage.run_op.call_count == 1
        assert mock_timer.call_count == 1
        timer_callback = mock_timer.call_args[0][1]

        # Simulate timer completion
        timer_callback()

        # run_op was called again
        assert stage.run_op.call_count == 2

    @pytest.mark.it("Cancels and clears the retry timer after the retry timer expires")
    def test_clears_retry_timer(self, mocker, stage, op, error, mock_timer):
        stage.run_op(op)
        op.complete(error=error)
        timer_callback = mock_timer.call_args[0][1]

        assert mock_timer.cancel.call_count == 0
        assert op.retry_timer is mock_timer.return_value

        # Simulate timer completion
        timer_callback()

        assert mock_timer.return_value.cancel.call_count == 1
        assert mock_timer.return_value.cancel.call_args == mocker.call()
        assert op.retry_timer is None


@pytest.mark.describe(
    "RetryStage - EVENT: Retryable operation completes unsucessfully with a non-retryable error after call to .run_op()"
)
class TestRetryStageRetryableOperationCompletedWithNonRetryableError(RetryStageTestConfig):
    @pytest.fixture(params=retryable_ops, ids=[x[0].__name__ for x in retryable_ops])
    def op(self, request, mocker):
        op_cls = request.param[0]
        init_kwargs = request.param[1]
        return op_cls(**init_kwargs)

    @pytest.fixture
    def error(self, arbitrary_exception):
        return arbitrary_exception

    @pytest.mark.it("Completes normally without retry")
    def test_no_retry(self, mocker, stage, op, error, mock_timer):
        stage.run_op(op)
        op.complete(error=error)

        assert op.completed
        assert op not in stage.ops_waiting_to_retry
        assert mock_timer.call_count == 0

    @pytest.mark.it("Cancels and clears the operation's retry timer, if one exists")
    def test_cancels_existing_timer(self, mocker, stage, op, error, mock_timer):
        # NOTE: This shouldn't happen naturally. We have to artificially create this circumstance
        stage.run_op(op)

        # Artificially add a timer. Note that this is already mocked due to the 'mock_timer' fixture
        op.retry_timer = threading.Timer(20, fake_callback)
        assert op.retry_timer is mock_timer.return_value

        op.complete(error=error)

        assert op.completed
        assert mock_timer.return_value.cancel.call_count == 1
        assert op.retry_timer is None


@pytest.mark.describe(
    "RetryStage - EVENT: Retryable operation completes successfully after call to .run_op()"
)
class TestRetryStageRetryableOperationCompletedSuccessfully(RetryStageTestConfig):
    @pytest.fixture(params=retryable_ops, ids=[x[0].__name__ for x in retryable_ops])
    def op(self, request, mocker):
        op_cls = request.param[0]
        init_kwargs = request.param[1]
        return op_cls(**init_kwargs)

    @pytest.mark.it("Completes normally without retry")
    def test_no_retry(self, mocker, stage, op, mock_timer):
        stage.run_op(op)
        op.complete()

        assert op.completed
        assert op not in stage.ops_waiting_to_retry
        assert mock_timer.call_count == 0

    # NOTE: this isn't doing anything because arb ops don't trigger callback
    @pytest.mark.it("Cancels and clears the operation's retry timer, if one exists")
    def test_cancels_existing_timer(self, mocker, stage, op, mock_timer):
        # NOTE: This shouldn't happen naturally. We have to artificially create this circumstance
        stage.run_op(op)

        # Artificially add a timer. Note that this is already mocked due to the 'mock_timer' fixture
        op.retry_timer = threading.Timer(20, fake_callback)
        assert op.retry_timer is mock_timer.return_value

        op.complete()

        assert op.completed
        assert mock_timer.return_value.cancel.call_count == 1
        assert op.retry_timer is None


@pytest.mark.describe(
    "RetryStage - EVENT: Non-retryable operation completes after call to .run_op()"
)
class TestRetryStageNonretryableOperationCompleted(RetryStageTestConfig):
    @pytest.fixture
    def op(self, arbitrary_op):
        return arbitrary_op

    @pytest.mark.it("Completes normally without retry, if completed successfully")
    def test_successful_completion(self, mocker, stage, op, mock_timer):
        stage.run_op(op)
        op.complete()

        assert op.completed
        assert op not in stage.ops_waiting_to_retry
        assert mock_timer.call_count == 0

    @pytest.mark.it(
        "Completes normally without retry, if completed unsucessfully with a non-retryable exception"
    )
    def test_unsucessful_non_retryable_err(
        self, mocker, stage, op, arbitrary_exception, mock_timer
    ):
        stage.run_op(op)
        op.complete(error=arbitrary_exception)

        assert op.completed
        assert op not in stage.ops_waiting_to_retry
        assert mock_timer.call_count == 0

    @pytest.mark.it(
        "Completes normally without retry, if completed unsucessfully with a retryable exception"
    )
    @pytest.mark.parametrize("exception", retryable_exceptions)
    def test_unsucessful_retryable_err(self, mocker, stage, op, exception, mock_timer):
        stage.run_op(op)
        op.complete(error=exception)

        assert op.completed
        assert op not in stage.ops_waiting_to_retry
        assert mock_timer.call_count == 0


# @pytest.mark.describe("RetryStage - EVENT: Non-retryable operation completed after call to .run_op()")

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
