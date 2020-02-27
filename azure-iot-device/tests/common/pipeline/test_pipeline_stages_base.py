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
    def stage(self, mocker, cls_type, init_kwargs):
        stage = cls_type(**init_kwargs)
        stage.send_op_down = mocker.MagicMock()
        stage.send_event_up = mocker.MagicMock()
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


# NOTE 1: Because the Root stage overrides the parent implementation, we must test it here
# (even though it's the same test).
# NOTE 2: Currently this implementation does some other things with threads, but we do not
# currently have a thread testing strategy, so it is untested for now.
@pytest.mark.describe("PipelineRootStage - .run_op()")
class TestPipelineRootStageRunOp(PipelineRootStageTestConfig):
    @pytest.fixture
    def op(self, arbitrary_op):
        return arbitrary_op

    @pytest.mark.it("Sends the operation down")
    def test_sends_op_down(self, mocker, stage, op):
        stage.run_op(op)
        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(op)


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
        time.sleep(0.1)  # CT-TODO / BK-TODO: get rid of this
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
        time.sleep(0.1)  # CT-TODO / BK-TODO: get rid of this
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
        time.sleep(0.1)  # CT-TODO/BK-TODO: get rid of this
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
        assert isinstance(connect_op, pipeline_ops_base.ConnectOperation)
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
        assert isinstance(connect_op, pipeline_ops_base.ConnectOperation)
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
    pipeline_ops_base.ReauthorizeConnectionOperation,
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
    "ConnectionLockStage - .run_op() -- Called with a ReauthorizeConnectionOperation while not in a blocking state"
)
class TestConnectionLockStageRunOpWithReconnectOpWhileUnblocked(
    ConnectionLockStageTestConfig, StageRunOpTestBase
):
    @pytest.fixture
    def op(self, mocker):
        return pipeline_ops_base.ReauthorizeConnectionOperation(callback=mocker.MagicMock())

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
        "Adds the operation to the queue, even if the operation's desired pipeline connection state already has been reached"
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
        op3 = pipeline_ops_base.ReauthorizeConnectionOperation(callback=mocker.MagicMock())
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
    "ConnectionLockStage - OCCURANCE: Operation blocking ConnectionLockStage is completed successfully"
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
        op3 = pipeline_ops_base.ReauthorizeConnectionOperation(callback=mocker.MagicMock())
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
    "ConnectionLockStage - OCCURANCE: Operation blocking ConnectionLockStage is completed with error"
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
class TestCoordinateRequestAndResponseStageRunOpWithArbitraryOperation(
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
    "CoordinateRequestAndResponseStage - OCCURANCE: RequestOperation tied to a stored RequestAndResponseOperation is completed"
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
    "OpTimeoutStage - OCCURANCE: Operation with a timeout timer times out before completion"
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
    "OpTimeoutStage - OCCURANCE: Operation with a timeout timer completes before timeout"
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
]

retryable_exceptions = [pipeline_exceptions.PipelineTimeoutError]


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
        "Sets default retry intervals to 20 seconds for MQTTSubscribeOperation, MQTTUnsubscribeOperation, and MQTTPublishOperation"
    )
    def test_retry_intervals(self, init_kwargs):
        stage = pipeline_stages_base.RetryStage(**init_kwargs)
        assert stage.retry_intervals[pipeline_ops_mqtt.MQTTSubscribeOperation] == 20
        assert stage.retry_intervals[pipeline_ops_mqtt.MQTTUnsubscribeOperation] == 20
        assert stage.retry_intervals[pipeline_ops_mqtt.MQTTPublishOperation] == 20

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
    "RetryStage - OCCURANCE: Retryable operation completes unsuccessfully with a retryable error after call to .run_op()"
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

    @pytest.mark.it(
        "Adds a new retry timer to the re-run operation, if it completes unsuccessfully again"
    )
    def test_rerun_op_unsuccessful_again(self, mocker, stage, op, error, mock_timer):
        stage.run_op(op)
        assert stage.run_op.call_count == 1

        # Complete with failure the first time
        op.complete(error=error)

        assert mock_timer.call_count == 1
        assert op.retry_timer is mock_timer.return_value
        timer_callback1 = mock_timer.call_args[0][1]

        # Trigger retry
        timer_callback1()

        assert stage.run_op.call_count == 2
        assert stage.run_op.call_args == mocker.call(op)
        assert op.retry_timer is None

        # Complete with failure the second time
        op.complete(error=error)

        assert mock_timer.call_count == 2
        assert op.retry_timer is mock_timer.return_value
        timer_callback2 = mock_timer.call_args[0][1]

        # Trigger retry again
        timer_callback2()

        assert stage.run_op.call_count == 3
        assert stage.run_op.call_args == mocker.call(op)
        assert op.retry_timer is None

    @pytest.mark.it("Supports multiple simultaneous operations retrying")
    def test_multiple_retries(self, mocker, stage, mock_timer):
        op1 = pipeline_ops_mqtt.MQTTSubscribeOperation(
            topic="fake_topic", callback=mocker.MagicMock()
        )
        op2 = pipeline_ops_mqtt.MQTTPublishOperation(
            topic="fake_topic", payload="fake_payload", callback=mocker.MagicMock()
        )
        op3 = pipeline_ops_mqtt.MQTTUnsubscribeOperation(
            topic="fake_topic", callback=mocker.MagicMock()
        )

        stage.run_op(op1)
        stage.run_op(op2)
        stage.run_op(op3)
        assert stage.run_op.call_count == 3

        assert not op1.completed
        assert not op2.completed
        assert not op3.completed

        op1.complete(error=pipeline_exceptions.PipelineTimeoutError())
        op2.complete(error=pipeline_exceptions.PipelineTimeoutError())
        op3.complete(error=pipeline_exceptions.PipelineTimeoutError())

        # Ops halted
        assert not op1.completed
        assert not op2.completed
        assert not op3.completed

        # Timers set
        assert mock_timer.call_count == 3
        assert op1.retry_timer is mock_timer.return_value
        assert op2.retry_timer is mock_timer.return_value
        assert op3.retry_timer is mock_timer.return_value
        assert mock_timer.return_value.start.call_count == 3

        # Operations awaiting retry
        assert op1 in stage.ops_waiting_to_retry
        assert op2 in stage.ops_waiting_to_retry
        assert op3 in stage.ops_waiting_to_retry

        timer1_complete = mock_timer.call_args_list[0][0][1]
        timer2_complete = mock_timer.call_args_list[1][0][1]
        timer3_complete = mock_timer.call_args_list[2][0][1]

        # Trigger op1's timer to complete
        timer1_complete()

        # Only op1 was re-run, and had it's timer removed
        assert mock_timer.return_value.cancel.call_count == 1
        assert op1.retry_timer is None
        assert op1 not in stage.ops_waiting_to_retry
        assert op2.retry_timer is mock_timer.return_value
        assert op2 in stage.ops_waiting_to_retry
        assert op3.retry_timer is mock_timer.return_value
        assert op3 in stage.ops_waiting_to_retry
        assert stage.run_op.call_count == 4
        assert stage.run_op.call_args == mocker.call(op1)

        # Trigger op2's timer to complete
        timer2_complete()

        # Only op2 was re-run and had it's timer removed
        assert mock_timer.return_value.cancel.call_count == 2
        assert op2.retry_timer is None
        assert op2 not in stage.ops_waiting_to_retry
        assert op3.retry_timer is mock_timer.return_value
        assert op3 in stage.ops_waiting_to_retry
        assert stage.run_op.call_count == 5
        assert stage.run_op.call_args == mocker.call(op2)

        # Trigger op3's timer to complete
        timer3_complete()

        # op3 has now also been re-run and had it's timer removed
        assert op3.retry_timer is None
        assert op3 not in stage.ops_waiting_to_retry
        assert stage.run_op.call_count == 6
        assert stage.run_op.call_args == mocker.call(op3)


@pytest.mark.describe(
    "RetryStage - OCCURANCE: Retryable operation completes unsucessfully with a non-retryable error after call to .run_op()"
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
    "RetryStage - OCCURANCE: Retryable operation completes successfully after call to .run_op()"
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
    "RetryStage - OCCURANCE: Non-retryable operation completes after call to .run_op()"
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


###################
# RECONNECT STAGE #
###################


class ReconnectStageTestConfig(object):
    @pytest.fixture
    def cls_type(self):
        return pipeline_stages_base.ReconnectStage

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


class ReconnectStageInstantiationTests(ReconnectStageTestConfig):
    @pytest.mark.it("Initializes the 'reconnect_timer' attribute as None")
    def test_reconnect_timer(self, cls_type, init_kwargs):
        stage = cls_type(**init_kwargs)
        assert stage.reconnect_timer is None

    @pytest.mark.it("Initializes the 'state' attribute as 'NEVER_CONNECTED'")
    def test_state(self, cls_type, init_kwargs):
        stage = cls_type(**init_kwargs)
        assert stage.state == pipeline_stages_base.ReconnectState.NEVER_CONNECTED

    @pytest.mark.it("Initializes the 'waiting_connect_ops' attribute as []")
    def test_waiting_connect_ops(self, cls_type, init_kwargs):
        stage = cls_type(**init_kwargs)
        assert stage.waiting_connect_ops == []

    # TODO: this will not be necessary once retry policy is implemented more fully
    @pytest.mark.it("Initializes the 'reconnect_delay' attribute/setting to 10 seconds")
    def test_reconnect_delay(self, cls_type, init_kwargs):
        stage = cls_type(**init_kwargs)
        assert stage.reconnect_delay == 10


pipeline_stage_test.add_base_pipeline_stage_tests(
    test_module=this_module,
    stage_class_under_test=pipeline_stages_base.ReconnectStage,
    stage_test_config_class=ReconnectStageTestConfig,
    extended_stage_instantiation_test_class=ReconnectStageInstantiationTests,
)


@pytest.mark.describe("ReconnectStage - .run_op() -- Called with ConnectOperation")
class TestReconnectStageRunOpWithConnectOperation(ReconnectStageTestConfig, StageRunOpTestBase):
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

    @pytest.fixture
    def fake_waiting_connect_ops(self, mocker):
        op1 = ArbitraryOperation(callback=mocker.MagicMock())
        op1.original_callback = op1.callback_stack[0]
        op2 = ArbitraryOperation(callback=mocker.MagicMock())
        op2.original_callback = op2.callback_stack[0]
        return list([op1, op2])

    @pytest.fixture
    def op(self, mocker):
        return pipeline_ops_base.ConnectOperation(callback=mocker.MagicMock())

    @pytest.mark.parametrize(
        "state",
        [
            pipeline_stages_base.ReconnectState.NEVER_CONNECTED,
            pipeline_stages_base.ReconnectState.WAITING_TO_RECONNECT,
            pipeline_stages_base.ReconnectState.CONNECTED_OR_DISCONNECTED,
        ],
    )
    @pytest.mark.it("Does not complete the operation")
    def test_does_not_immediately_complete(self, stage, op, state):
        stage.state = state
        callback = op.callback_stack[0]
        stage.run_op(op)
        assert callback.call_count == 0

    @pytest.mark.parametrize(
        "state",
        [
            pipeline_stages_base.ReconnectState.NEVER_CONNECTED,
            pipeline_stages_base.ReconnectState.WAITING_TO_RECONNECT,
            pipeline_stages_base.ReconnectState.CONNECTED_OR_DISCONNECTED,
        ],
    )
    @pytest.mark.it("adds the op to the waiting_connect_ops list")
    def test_adds_to_waiting_connect_ops(self, stage, op, state, fake_waiting_connect_ops):
        stage.state = state
        stage.waiting_connect_ops = fake_waiting_connect_ops
        waiting_connect_ops_copy = list(fake_waiting_connect_ops)
        stage.run_op(op)
        waiting_connect_ops_copy.append(op)
        assert stage.waiting_connect_ops == waiting_connect_ops_copy

    @pytest.mark.parametrize(
        "state",
        [
            pipeline_stages_base.ReconnectState.NEVER_CONNECTED,
            pipeline_stages_base.ReconnectState.WAITING_TO_RECONNECT,
            pipeline_stages_base.ReconnectState.CONNECTED_OR_DISCONNECTED,
        ],
    )
    @pytest.mark.it("does not complete any waiting ops")
    def test_does_not_complete_waiting_connect_ops(
        self, stage, op, state, fake_waiting_connect_ops
    ):
        stage.state = state
        stage.waiting_connect_ops = fake_waiting_connect_ops
        waiting_connect_ops_copy = list(fake_waiting_connect_ops)
        stage.run_op(op)
        for op in waiting_connect_ops_copy:
            assert op.original_callback.call_count == 0

    @pytest.mark.parametrize(
        "state",
        [
            pipeline_stages_base.ReconnectState.NEVER_CONNECTED,
            pipeline_stages_base.ReconnectState.CONNECTED_OR_DISCONNECTED,
        ],
    )
    @pytest.mark.it("Sends a new connect op down")
    def test_sends_new_op_down(self, stage, op, state):
        stage.state = state
        stage.run_op(op)
        assert stage.send_op_down.call_count == 1
        new_op = stage.send_op_down.call_args[0][0]
        assert isinstance(new_op, pipeline_ops_base.ConnectOperation)
        assert new_op != op

    @pytest.mark.parametrize("state", [pipeline_stages_base.ReconnectState.WAITING_TO_RECONNECT])
    @pytest.mark.it("Does not send a new connect op down")
    def test_does_not_send_new_op_down(self, stage, op, state):
        stage.state = state
        stage.run_op(op)
        assert stage.send_op_down.call_count == 0

    @pytest.mark.parametrize(
        "state",
        [
            pipeline_stages_base.ReconnectState.CONNECTED_OR_DISCONNECTED,
            pipeline_stages_base.ReconnectState.WAITING_TO_RECONNECT,
            pipeline_stages_base.ReconnectState.NEVER_CONNECTED,
        ],
    )
    @pytest.mark.it("Does not change the state")
    def test_does_not_change_state(self, stage, op, state):
        stage.state = state
        stage.run_op(op)
        assert stage.state == state

    @pytest.mark.parametrize(
        "state",
        [
            pipeline_stages_base.ReconnectState.NEVER_CONNECTED,
            pipeline_stages_base.ReconnectState.WAITING_TO_RECONNECT,
            pipeline_stages_base.ReconnectState.CONNECTED_OR_DISCONNECTED,
        ],
    )
    @pytest.mark.it("Does not cancel, clear or set a reconnect timer")
    def test_timer_untouched(self, mocker, stage, op, mock_timer, state):
        stage.state = state
        original_timer = stage.reconnect_timer
        stage.run_op(op)

        assert stage.reconnect_timer is original_timer
        if stage.reconnect_timer:
            assert stage.reconnect_timer.cancel.call_count == 0
        assert mock_timer.call_count == 0


@pytest.mark.describe("ReconnectStage - .run_op() -- Called with DisconnectOperation")
class TestReconnectStageRunOpWithDisconnectOperation(ReconnectStageTestConfig, StageRunOpTestBase):
    @pytest.fixture
    def op(self, mocker):
        return pipeline_ops_base.DisconnectOperation(callback=mocker.MagicMock())

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

    @pytest.fixture
    def fake_waiting_connect_ops(self, mocker):
        op1 = ArbitraryOperation(callback=mocker.MagicMock())
        op1.original_callback = op1.callback_stack[0]
        op2 = ArbitraryOperation(callback=mocker.MagicMock())
        op2.original_callback = op2.callback_stack[0]
        return list([op1, op2])

    @pytest.mark.parametrize("state", [pipeline_stages_base.ReconnectState.WAITING_TO_RECONNECT])
    @pytest.mark.it("Immediately completes the op")
    def test_completes_op(self, stage, op, state, mocker):
        stage.state = state
        callback = op.callback_stack[0]
        stage.run_op(op)
        assert callback.call_count == 1
        assert callback.call_args == mocker.call(op=op, error=None)

    @pytest.mark.parametrize(
        "state",
        [
            pipeline_stages_base.ReconnectState.CONNECTED_OR_DISCONNECTED,
            pipeline_stages_base.ReconnectState.NEVER_CONNECTED,
        ],
    )
    @pytest.mark.it("Does not immediately complete the op")
    def test_does_not_complete_op(self, stage, op, state):
        stage.state = state
        callback = op.callback_stack[0]
        stage.run_op(op)
        assert callback.call_count == 0

    @pytest.mark.parametrize(
        "state",
        [
            pipeline_stages_base.ReconnectState.CONNECTED_OR_DISCONNECTED,
            pipeline_stages_base.ReconnectState.NEVER_CONNECTED,
        ],
    )
    @pytest.mark.it("Sends the op down")
    def test_sends_op_down(self, stage, op, state, mocker):
        stage.state = state
        stage.run_op(op)
        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(op)

    @pytest.mark.parametrize("state", [pipeline_stages_base.ReconnectState.WAITING_TO_RECONNECT])
    @pytest.mark.it("Does not send the op down")
    def test_does_not_send_op_down(self, stage, op, state):
        stage.state = state
        stage.run_op(op)
        assert stage.send_op_down.call_count == 0

    @pytest.mark.parametrize("state", [pipeline_stages_base.ReconnectState.WAITING_TO_RECONNECT])
    @pytest.mark.it("Clears the reconnect timer")
    def test_clears_reconnect_timer(self, stage, op, state, mocker):
        stage.state = state
        reconnect_timer = mocker.MagicMock()
        stage.reconnect_timer = reconnect_timer
        stage.run_op(op)
        assert stage.reconnect_timer is None
        assert reconnect_timer.cancel.call_count == 1
        assert reconnect_timer.cancel.call_args == mocker.call()

    @pytest.mark.parametrize(
        "state",
        [
            pipeline_stages_base.ReconnectState.NEVER_CONNECTED,
            pipeline_stages_base.ReconnectState.CONNECTED_OR_DISCONNECTED,
        ],
    )
    @pytest.mark.it("Does not cancel, clear or set a reconnect timer")
    def test_timer_untouched(self, mocker, stage, op, mock_timer, state):
        stage.state = state
        original_timer = stage.reconnect_timer
        stage.run_op(op)

        assert stage.reconnect_timer is original_timer
        if stage.reconnect_timer:
            assert stage.reconnect_timer.cancel.call_count == 0
        assert mock_timer.call_count == 0

    @pytest.mark.parametrize("state", [pipeline_stages_base.ReconnectState.WAITING_TO_RECONNECT])
    @pytest.mark.it("Changes the state to CONNECTED_OR_DISCONNECTED")
    def test_changes_state(self, stage, op, state):
        stage.state = state
        stage.run_op(op)
        assert stage.state == pipeline_stages_base.ReconnectState.CONNECTED_OR_DISCONNECTED

    @pytest.mark.parametrize(
        "state",
        [
            pipeline_stages_base.ReconnectState.NEVER_CONNECTED,
            pipeline_stages_base.ReconnectState.CONNECTED_OR_DISCONNECTED,
        ],
    )
    @pytest.mark.it("Does not change the state")
    def test_does_not_change_state(self, stage, op, state):
        stage.state = state
        stage.run_op(op)
        assert stage.state == state

    @pytest.mark.parametrize("state", [pipeline_stages_base.ReconnectState.WAITING_TO_RECONNECT])
    @pytest.mark.it("Cancels all ops in the waiting list")
    def test_cancels_waiting_connect_ops(self, stage, op, state, fake_waiting_connect_ops):
        stage.state = state
        stage.waiting_connect_ops = fake_waiting_connect_ops
        waiting_connect_ops_copy = list(fake_waiting_connect_ops)
        stage.run_op(op)
        assert stage.waiting_connect_ops == []
        for op in waiting_connect_ops_copy:
            assert op.original_callback.call_count == 1
            error = op.original_callback.call_args[1]["error"]
            assert isinstance(error, pipeline_exceptions.OperationCancelled)

    @pytest.mark.parametrize(
        "state",
        [
            pipeline_stages_base.ReconnectState.NEVER_CONNECTED,
            pipeline_stages_base.ReconnectState.CONNECTED_OR_DISCONNECTED,
        ],
    )
    @pytest.mark.it("Does not add, remove, or complete any ops in the waiting ops list")
    def test_waiting_connect_ops_list_untouched(self, stage, op, state, fake_waiting_connect_ops):
        stage.state = state
        stage.waiting_connect_ops = fake_waiting_connect_ops
        waiting_connect_ops_copy = list(fake_waiting_connect_ops)
        stage.run_op(op)
        assert stage.waiting_connect_ops == waiting_connect_ops_copy
        for op in stage.waiting_connect_ops:
            assert op.original_callback.call_count == 0


@pytest.mark.describe("ReconnectStage - .run_op() -- Called with arbitrary other operation")
class TestReconnectStageRunOpWithArbitraryOperation(ReconnectStageTestConfig, StageRunOpTestBase):
    @pytest.fixture
    def op(self, arbitrary_op):
        return arbitrary_op

    @pytest.fixture(
        params=[
            pipeline_stages_base.ReconnectState.NEVER_CONNECTED,
            pipeline_stages_base.ReconnectState.WAITING_TO_RECONNECT,
            pipeline_stages_base.ReconnectState.CONNECTED_OR_DISCONNECTED,
        ]
    )
    def state(self, request):
        return request.param

    @pytest.fixture
    def stage(self, mocker, cls_type, init_kwargs, state):
        stage = cls_type(**init_kwargs)
        stage.pipeline_root = pipeline_stages_base.PipelineRootStage(
            pipeline_configuration=mocker.MagicMock()
        )
        mocker.spy(stage, "run_op")
        stage.send_op_down = mocker.MagicMock()
        stage.send_event_up = mocker.MagicMock()
        stage.state = state
        return stage

    @pytest.fixture
    def fake_waiting_connect_ops(self, mocker):
        op1 = ArbitraryOperation(callback=mocker.MagicMock())
        op1.original_callback = op1.callback_stack[0]
        op2 = ArbitraryOperation(callback=mocker.MagicMock())
        op2.original_callback = op2.callback_stack[0]
        return list([op1, op2])

    @pytest.mark.it("Does not change the state")
    def test_state_unchanged(self, stage, op):
        original_state = stage.state
        stage.run_op(op)
        assert stage.state is original_state

    @pytest.mark.it("Sends the operation down the pipeline")
    def test_sends_op_down(self, mocker, stage, op):
        stage.run_op(op)
        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(op)

    @pytest.mark.it("Does not cancel, clear or set a reconnect timer")
    def test_timer_untouched(self, mocker, stage, op, mock_timer):
        original_timer = stage.reconnect_timer
        stage.run_op(op)

        assert stage.reconnect_timer is original_timer
        if stage.reconnect_timer:
            assert stage.reconnect_timer.cancel.call_count == 0
        assert mock_timer.call_count == 0

    @pytest.mark.it("Does not add, remove, or complete any ops in the waiting ops list")
    def test_waiting_connect_ops_list_untouched(self, stage, op, state, fake_waiting_connect_ops):
        stage.state = state
        stage.waiting_connect_ops = fake_waiting_connect_ops
        waiting_connect_ops_copy = list(fake_waiting_connect_ops)
        stage.run_op(op)
        assert stage.waiting_connect_ops == waiting_connect_ops_copy
        for op in stage.waiting_connect_ops:
            assert op.original_callback.call_count == 0


@pytest.mark.describe("ReconnectStage - .handle_pipeline_event() -- Called with a ConnectedEvent")
class TestReconnectStageHandlePipelineEventWithConnectedEvent(
    ReconnectStageTestConfig, StageHandlePipelineEventTestBase
):
    @pytest.fixture(
        params=[
            pipeline_stages_base.ReconnectState.NEVER_CONNECTED,
            pipeline_stages_base.ReconnectState.WAITING_TO_RECONNECT,
            pipeline_stages_base.ReconnectState.CONNECTED_OR_DISCONNECTED,
        ]
    )
    def state(self, request):
        return request.param

    @pytest.fixture(params=[True, False], ids=["Connected", "Disconnected"])
    def connected(self, request):
        return request.param

    @pytest.fixture
    def fake_waiting_connect_ops(self, mocker):
        op1 = ArbitraryOperation(callback=mocker.MagicMock())
        op1.original_callback = op1.callback_stack[0]
        op2 = ArbitraryOperation(callback=mocker.MagicMock())
        op2.original_callback = op2.callback_stack[0]
        return list([op1, op2])

    @pytest.fixture(
        params=[True, False], ids=["Existing Reconnect Timer", "No Existing Reconnect Timer"]
    )
    def reconnect_timer(self, request, mocker):
        if request.param:
            return mocker.MagicMock()
        else:
            return None

    @pytest.fixture()
    def stage(self, mocker, cls_type, init_kwargs, connected, reconnect_timer):
        stage = cls_type(**init_kwargs)
        stage.pipeline_root = pipeline_stages_base.PipelineRootStage(
            pipeline_configuration=mocker.MagicMock()
        )
        mocker.spy(stage, "run_op")
        stage.send_op_down = mocker.MagicMock()
        stage.send_event_up = mocker.MagicMock()
        stage.pipeline_root.connected = connected
        stage.reconnect_timer = reconnect_timer
        return stage

    @pytest.fixture
    def event(self):
        return pipeline_events_base.ConnectedEvent()

    @pytest.mark.it("Sends the event up the pipeline")
    def test_sends_event_up(self, mocker, stage, event, state):
        stage.state = state
        stage.handle_pipeline_event(event)
        assert stage.send_event_up.call_count == 1
        assert stage.send_event_up.call_args == mocker.call(event)

    @pytest.mark.it("Does not add, remove, or complete any ops in the waiting ops list")
    def test_waiting_connect_ops_list_untouched(
        self, stage, event, state, fake_waiting_connect_ops
    ):
        stage.state = state
        stage.waiting_connect_ops = fake_waiting_connect_ops
        waiting_connect_ops_copy = list(fake_waiting_connect_ops)
        stage.handle_pipeline_event(event)
        assert stage.waiting_connect_ops == waiting_connect_ops_copy
        for op in stage.waiting_connect_ops:
            assert op.original_callback.call_count == 0

    @pytest.mark.it("Does not cancel, clear or set a reconnect timer")
    def test_timer_untouched(self, mocker, stage, event, mock_timer):
        original_timer = stage.reconnect_timer
        stage.handle_pipeline_event(event)

        assert stage.reconnect_timer is original_timer
        if stage.reconnect_timer:
            assert stage.reconnect_timer.cancel.call_count == 0
        assert mock_timer.call_count == 0


@pytest.mark.describe(
    "ReconnectStage - .handle_pipeline_event() -- Called with a DisconnectedEvent"
)
class TestReconnectStageHandlePipelineEventWithDisconnectedEvent(
    ReconnectStageTestConfig, StageHandlePipelineEventTestBase
):
    @pytest.fixture(
        params=[True, False], ids=["Existing Reconnect Timer", "No Existing Reconnect Timer"]
    )
    def reconnect_timer(self, request, mocker):
        if request.param:
            return mocker.MagicMock()
        else:
            return None

    @pytest.fixture(
        params=[
            pipeline_stages_base.ReconnectState.NEVER_CONNECTED,
            pipeline_stages_base.ReconnectState.WAITING_TO_RECONNECT,
            pipeline_stages_base.ReconnectState.CONNECTED_OR_DISCONNECTED,
        ]
    )
    def state(self, request):
        return request.param

    @pytest.fixture()
    def stage(self, mocker, cls_type, init_kwargs, state, reconnect_timer, mock_timer):
        # mock_timer fixture is used here so none of these tests create an actual timer.
        stage = cls_type(**init_kwargs)
        stage.pipeline_root = pipeline_stages_base.PipelineRootStage(
            pipeline_configuration=mocker.MagicMock()
        )
        stage.state = state
        stage.reconnect_timer = reconnect_timer
        mocker.spy(stage, "run_op")
        stage.send_op_down = mocker.MagicMock()
        stage.send_event_up = mocker.MagicMock()
        return stage

    @pytest.fixture
    def event(self):
        return pipeline_events_base.DisconnectedEvent()

    @pytest.mark.it("If previously connected, changes the state to WAITING_TO_RECONNECT")
    def test_changes_state(self, stage, event):
        stage.pipeline_root.connected = True
        stage.handle_pipeline_event(event)
        assert stage.state == pipeline_stages_base.ReconnectState.WAITING_TO_RECONNECT

    @pytest.mark.it("If not previously connectred, does not change the state")
    def test_does_not_change_state(self, stage, event):
        stage.pipeline_root.connected = False
        original_state = stage.state
        stage.handle_pipeline_event(event)
        assert stage.state == original_state

    @pytest.mark.it("If previously connected, clears the previous reconnect timer if there was one")
    def test_clears_reconnect_timer(self, stage, event):
        old_timer = stage.reconnect_timer
        stage.pipeline_root.connected = True
        stage.handle_pipeline_event(event)
        if old_timer:
            assert old_timer.cancel.call_count == 1
        assert stage.reconnect_timer != old_timer

    @pytest.mark.it(
        "If not previously connected, does not clears the previous reconnect timer if there was one"
    )
    def test_does_not_clear_reconnect_timer(self, stage, event):
        old_timer = stage.reconnect_timer
        stage.pipeline_root.connected = False
        stage.handle_pipeline_event(event)
        if old_timer:
            assert old_timer.cancel.call_count == 0
        assert stage.reconnect_timer == old_timer

    @pytest.mark.it("If previously connected, sets a new reconnect timer")
    def test_sets_new_reconnect_timer(self, stage, event, mock_timer):
        stage.pipeline_root.connected = True
        stage.handle_pipeline_event(event)
        assert mock_timer.call_count == 1
        assert stage.reconnect_timer == mock_timer.return_value
        assert stage.reconnect_timer.start.call_count == 1

    @pytest.mark.it("If not previously connected, does not set a new reconnect timer")
    def test_does_not_set_new_reconnect_timer(self, stage, event, mock_timer):
        old_reconnect_timer = stage.reconnect_timer
        stage.pipeline_root.connected = False
        stage.handle_pipeline_event(event)
        assert mock_timer.call_count == 0
        assert stage.reconnect_timer == old_reconnect_timer
        if stage.reconnect_timer:
            assert stage.reconnect_timer.start.call_count == 0

    @pytest.mark.parametrize(
        "previously_connected",
        [
            pytest.param(True, id="Previously conencted"),
            pytest.param(False, id="Not previously connected"),
        ],
    )
    @pytest.mark.it("Sends the event up")
    def test_sends_event_up(self, stage, event, previously_connected, mocker):
        stage.pipeline_root.connected = previously_connected
        stage.handle_pipeline_event(event)
        assert stage.send_event_up.call_count == 1
        assert stage.send_event_up.call_args == mocker.call(event)


@pytest.mark.describe(
    "ReconnectStage - .handle_pipeline_event() -- Called with some other arbitrary event"
)
class TestReconnectStageHandlePipelineEventWithArbitraryEvent(
    ReconnectStageTestConfig, StageHandlePipelineEventTestBase
):
    @pytest.fixture(
        params=[
            pipeline_stages_base.ReconnectState.NEVER_CONNECTED,
            pipeline_stages_base.ReconnectState.WAITING_TO_RECONNECT,
            pipeline_stages_base.ReconnectState.CONNECTED_OR_DISCONNECTED,
        ]
    )
    def state(self, request):
        return request.param

    @pytest.fixture(
        params=[True, False], ids=["Existing Reconnect Timer", "No Existing Reconnect Timer"]
    )
    def reconnect_timer(self, request, mocker):
        if request.param:
            return mocker.MagicMock()
        else:
            return None

    @pytest.fixture()
    def stage(self, mocker, cls_type, init_kwargs, state, reconnect_timer):
        stage = cls_type(**init_kwargs)
        stage.pipeline_root = pipeline_stages_base.PipelineRootStage(
            pipeline_configuration=mocker.MagicMock()
        )
        mocker.spy(stage, "run_op")
        stage.send_op_down = mocker.MagicMock()
        stage.send_event_up = mocker.MagicMock()
        stage.state = state
        stage.reconnect_timer = reconnect_timer
        return stage

    @pytest.fixture
    def event(self, arbitrary_event):
        return arbitrary_event

    @pytest.mark.it("Sends the event up the pipeline")
    def test_sends_up(self, mocker, stage, event):
        stage.handle_pipeline_event(event)

        assert stage.send_event_up.call_count == 1
        assert stage.send_event_up.call_args == mocker.call(event)

    @pytest.mark.it("Does not change the state")
    def test_state_unchanged(self, stage, event):
        original_state = stage.state
        stage.handle_pipeline_event(event)
        assert stage.state is original_state

    @pytest.mark.it("Does not cancel, clear or set a reconnect timer")
    def test_timer_untouched(self, mocker, stage, event, mock_timer):
        original_timer = stage.reconnect_timer
        stage.handle_pipeline_event(event)

        assert stage.reconnect_timer is original_timer
        if stage.reconnect_timer:
            assert stage.reconnect_timer.cancel.call_count == 0
        assert mock_timer.call_count == 0


@pytest.mark.describe("ReconnectStage - OCCURANCE: Reconnect Timer expires")
class TestReconnectStageReconnectTimerExpires(ReconnectStageTestConfig):
    @pytest.fixture()
    def stage(self, mocker, cls_type, init_kwargs):
        stage = cls_type(**init_kwargs)
        stage.pipeline_root = pipeline_stages_base.PipelineRootStage(
            pipeline_configuration=mocker.MagicMock()
        )
        mocker.spy(stage, "run_op")
        stage.send_op_down = mocker.MagicMock()
        stage.send_event_up = mocker.MagicMock()

        return stage

    @pytest.fixture
    def trigger_stage_retry_timer_completion(self, stage, mock_timer):
        # The stage must be connected in order to set a reconnect timer
        stage.pipeline_root.connected = True

        # Send a DisconnectedEvent to the stage in order to set up the timer
        stage.handle_pipeline_event(pipeline_events_base.DisconnectedEvent())

        # Get timer completion callback
        assert mock_timer.call_count == 1
        timer_callback = mock_timer.call_args[0][1]
        return timer_callback

    @pytest.mark.parametrize("state", [pipeline_stages_base.ReconnectState.WAITING_TO_RECONNECT])
    @pytest.mark.it("Creates a new ConnectOperation and sends it down the pipeline")
    def test_pipeline_disconnected(
        self, mocker, stage, trigger_stage_retry_timer_completion, state
    ):
        stage.state = state
        mock_connect_op = mocker.patch.object(pipeline_ops_base, "ConnectOperation")

        trigger_stage_retry_timer_completion()

        assert mock_connect_op.call_count == 1
        assert stage.send_op_down.call_count == 1
        assert stage.send_op_down.call_args == mocker.call(mock_connect_op.return_value)

    @pytest.mark.parametrize(
        "state",
        [
            pipeline_stages_base.ReconnectState.NEVER_CONNECTED,
            pipeline_stages_base.ReconnectState.CONNECTED_OR_DISCONNECTED,
        ],
    )
    @pytest.mark.it("Does not create a new ConnectOperation and send it down the pipeline")
    def test_pipeline_connected(self, mocker, stage, trigger_stage_retry_timer_completion, state):
        stage.state = state
        mock_connect_op = mocker.patch.object(pipeline_ops_base, "ConnectOperation")

        trigger_stage_retry_timer_completion()

        assert mock_connect_op.call_count == 0
        assert stage.send_op_down.call_count == 0

    @pytest.mark.parametrize(
        "state",
        [
            pipeline_stages_base.ReconnectState.NEVER_CONNECTED,
            pipeline_stages_base.ReconnectState.CONNECTED_OR_DISCONNECTED,
            pipeline_stages_base.ReconnectState.WAITING_TO_RECONNECT,
        ],
    )
    @pytest.mark.it("Sets self.reconnect_timer to None")
    def test_sets_reconnect_timer_to_none(
        self, mocker, stage, trigger_stage_retry_timer_completion, state
    ):
        stage.state = state
        trigger_stage_retry_timer_completion()
        assert stage.reconnect_timer is None

    @pytest.mark.parametrize("state", [pipeline_stages_base.ReconnectState.WAITING_TO_RECONNECT])
    @pytest.mark.it("Changes the state to CONNECTED_OR_DISCONNECTED")
    def test_changes_state(self, mocker, stage, trigger_stage_retry_timer_completion, state):
        stage.state = state
        trigger_stage_retry_timer_completion()
        assert stage.state == pipeline_stages_base.ReconnectState.CONNECTED_OR_DISCONNECTED

    @pytest.mark.parametrize(
        "state",
        [
            pipeline_stages_base.ReconnectState.NEVER_CONNECTED,
            pipeline_stages_base.ReconnectState.CONNECTED_OR_DISCONNECTED,
        ],
    )
    @pytest.mark.it("Does not change the state")
    def test_does_not_change_state(
        self, mocker, stage, trigger_stage_retry_timer_completion, state
    ):
        stage.state = state
        trigger_stage_retry_timer_completion()
        assert stage.state == state


@pytest.mark.describe(
    "ReconnectStage - OCCURANCE: ConnectOperation that was created in order to reconnect is completed"
)
class TestReconnectStageConnectOperationForReconnectIsCompleted(ReconnectStageTestConfig):
    @pytest.fixture(
        params=[
            pipeline_exceptions.OperationCancelled,
            pipeline_exceptions.PipelineTimeoutError,
            pipeline_exceptions.OperationError,
            transport_exceptions.ConnectionFailedError,
            transport_exceptions.ConnectionDroppedError,
        ]
    )
    def transient_connect_exception(self, request):
        return request.param()

    @pytest.fixture()
    def stage(self, mocker, cls_type, init_kwargs):
        stage = cls_type(**init_kwargs)
        stage.pipeline_root = pipeline_stages_base.PipelineRootStage(
            pipeline_configuration=mocker.MagicMock()
        )
        mocker.spy(stage, "run_op")
        stage.send_op_down = mocker.MagicMock()
        stage.send_event_up = mocker.MagicMock()

        return stage

    @pytest.fixture(
        params=[
            pytest.param(True, id="First connect attempt"),
            pytest.param(False, id="Second connect attempt"),
        ]
    )
    def connect_op(self, stage, request, mocker, mock_timer):
        first_connect_attempt = request.param

        if first_connect_attempt:
            stage.run_op(pipeline_ops_base.ConnectOperation(callback=mocker.MagicMock()))
        else:
            # The stage must be connected and virtually connected in order to set a reconnect timer
            stage.pipeline_root.connected = True

            # Send a DisconnectedEvent to the stage in order to set up the timer
            stage.handle_pipeline_event(pipeline_events_base.DisconnectedEvent())

            # Get timer completion callback
            assert mock_timer.call_count == 1
            timer_callback = mock_timer.call_args[0][1]
            mock_timer.reset_mock()

            # Force trigger the reconnect timer completion in order to trigger a reconnect
            timer_callback()

        # Get the connect operation sent down as part of the reconnect
        assert stage.send_op_down.call_count == 1
        connect_op = stage.send_op_down.call_args[0][0]
        assert isinstance(connect_op, pipeline_ops_base.ConnectOperation)
        return connect_op

    @pytest.fixture(
        params=[
            pipeline_stages_base.ReconnectState.NEVER_CONNECTED,
            pipeline_stages_base.ReconnectState.WAITING_TO_RECONNECT,
            pipeline_stages_base.ReconnectState.CONNECTED_OR_DISCONNECTED,
        ]
    )
    def all_states(self, request):
        return request.param

    @pytest.fixture
    def fake_waiting_connect_ops(self, mocker):
        op1 = ArbitraryOperation(callback=mocker.MagicMock())
        op1.original_callback = op1.callback_stack[0]
        op2 = ArbitraryOperation(callback=mocker.MagicMock())
        op2.original_callback = op2.callback_stack[0]
        return list([op1, op2])

    @pytest.mark.it("Sets the state to CONNECTED_OR_DISCONNECTED if the connect succeeds")
    def test_sets_state_on_success(self, stage, connect_op, all_states):
        stage.state = all_states
        connect_op.complete()
        assert stage.state == pipeline_stages_base.ReconnectState.CONNECTED_OR_DISCONNECTED

    @pytest.mark.it("Clears and sets reconnect_timer to None if the connect succeeds")
    def test_clears_reconnect_timer_on_success(self, stage, connect_op, all_states, mocker):
        stage.state = all_states
        reconnect_timer = mocker.MagicMock()
        stage.reconnect_timer = reconnect_timer
        connect_op.complete()
        assert stage.reconnect_timer is None
        assert reconnect_timer.cancel.call_count == 1

    @pytest.mark.it("Does not create a new reconnect timer on success")
    def test_does_not_create_new_reconnect_timer_on_success(
        self, stage, connect_op, all_states, mock_timer
    ):
        stage.state = all_states
        connect_op.complete()
        assert stage.reconnect_timer is None

    @pytest.mark.it("Completes any waiting ops if the connect succeeds")
    def test_completes_waiting_connect_ops(
        self, stage, connect_op, all_states, fake_waiting_connect_ops, mocker
    ):
        stage.state = all_states
        stage.waiting_connect_ops = list(fake_waiting_connect_ops)
        connect_op.complete()
        assert stage.waiting_connect_ops == []
        for op in fake_waiting_connect_ops:
            assert op.callback_stack == []
            assert op.original_callback.call_count == 1
            assert op.original_callback.call_args == mocker.call(op=op, error=None)

    @pytest.mark.parametrize(
        "state",
        [
            pipeline_stages_base.ReconnectState.NEVER_CONNECTED,
            pipeline_stages_base.ReconnectState.CONNECTED_OR_DISCONNECTED,
        ],
    )
    @pytest.mark.it("Does not change state if the connection fails with an arbitrary error")
    def test_does_not_change_state_on_arbitrary_exception(
        self, stage, connect_op, state, arbitrary_exception
    ):
        stage.state = state
        connect_op.complete(error=arbitrary_exception)
        assert stage.state == state

    @pytest.mark.parametrize(
        "state",
        [
            pipeline_stages_base.ReconnectState.NEVER_CONNECTED,
            pipeline_stages_base.ReconnectState.CONNECTED_OR_DISCONNECTED,
        ],
    )
    @pytest.mark.it(
        "Does not create a new reconnect timer if the connection fails with an arbitrary error"
    )
    def test_does_not_create_new_reconnect_timer_on_arbitrary_exception(
        self, stage, connect_op, state, mock_timer, arbitrary_exception
    ):
        stage.state = state
        connect_op.complete(error=arbitrary_exception)
        assert stage.reconnect_timer is None
        assert mock_timer.call_count == 0

    @pytest.mark.parametrize("state", [pipeline_stages_base.ReconnectState.WAITING_TO_RECONNECT])
    @pytest.mark.it(
        "Clears and sets reconnect_timer to None if the connection fails with an arbitrary error"
    )
    def test_clears_reconnect_timer_on_arbitrary_exception(
        self, stage, connect_op, state, mocker, arbitrary_exception
    ):
        stage.state = state
        reconnect_timer = mocker.MagicMock()
        stage.reconnect_timer = reconnect_timer
        connect_op.complete(error=arbitrary_exception)
        assert stage.reconnect_timer is None
        assert reconnect_timer.cancel.call_count == 1

    @pytest.mark.parametrize("state", [pipeline_stages_base.ReconnectState.WAITING_TO_RECONNECT])
    @pytest.mark.it(
        "Changes the state to CONNECTED_OR_DISCONNECTED if the connection fails with an arbitrary error"
    )
    def test_changes_state_on_arbitrary_exception(
        self, stage, connect_op, state, arbitrary_exception
    ):
        stage.state = state
        connect_op.complete(error=arbitrary_exception)
        assert stage.state == pipeline_stages_base.ReconnectState.CONNECTED_OR_DISCONNECTED

    @pytest.mark.it(
        "Completes all waiting ops with the arbitrary failure if the connection fails with an arbitrary error"
    )
    def test_completes_waiting_connect_ops_on_arbitrary_exception(
        self, stage, connect_op, all_states, fake_waiting_connect_ops, arbitrary_exception, mocker
    ):
        stage.state = all_states
        stage.waiting_connect_ops = list(fake_waiting_connect_ops)
        connect_op.complete(error=arbitrary_exception)
        assert stage.waiting_connect_ops == []
        for op in fake_waiting_connect_ops:
            assert op.callback_stack == []
            assert op.original_callback.call_count == 1
            assert op.original_callback.call_args == mocker.call(op=op, error=arbitrary_exception)

    @pytest.mark.parametrize("state", [pipeline_stages_base.ReconnectState.NEVER_CONNECTED])
    @pytest.mark.it(
        "Completes all waiting ops with the transient failure if the connection fails with a transient error"
    )
    def test_completes_all_waiting_connect_ops_on_transient_connect_exception(
        self,
        stage,
        connect_op,
        state,
        fake_waiting_connect_ops,
        transient_connect_exception,
        mocker,
    ):
        stage.state = state
        stage.waiting_connect_ops = list(fake_waiting_connect_ops)
        connect_op.complete(error=transient_connect_exception)
        assert stage.waiting_connect_ops == []
        for op in fake_waiting_connect_ops:
            assert op.callback_stack == []
            assert op.original_callback.call_count == 1
            assert op.original_callback.call_args == mocker.call(
                op=op, error=transient_connect_exception
            )

    @pytest.mark.parametrize("state", [pipeline_stages_base.ReconnectState.NEVER_CONNECTED])
    @pytest.mark.it(
        "Does not create a reconnect timer if the connection fails with a transient error"
    )
    def test_does_not_create_reconnect_timer_on_transient_connect_exception(
        self, stage, connect_op, state, mock_timer, transient_connect_exception
    ):
        stage.state = state
        connect_op.complete(error=transient_connect_exception)
        assert mock_timer.call_count == 0

    @pytest.mark.parametrize(
        "state",
        [
            pipeline_stages_base.ReconnectState.NEVER_CONNECTED,
            pipeline_stages_base.ReconnectState.WAITING_TO_RECONNECT,
        ],
    )
    @pytest.mark.it("Does not change state if the connection fails with a transient error")
    def test_does_not_change_state_on_transient_connect_exception(
        self, stage, connect_op, state, transient_connect_exception
    ):
        stage.state = state
        connect_op.complete(error=transient_connect_exception)
        assert stage.state == state

    @pytest.mark.parametrize(
        "state", [pipeline_stages_base.ReconnectState.CONNECTED_OR_DISCONNECTED]
    )
    @pytest.mark.it(
        "Changes the state to WAITING_TO_RECONNECT if the connection fails with a transient error"
    )
    def test_changes_state_on_transient_connect_exception(
        self, stage, connect_op, state, transient_connect_exception
    ):
        stage.state = state
        connect_op.complete(error=transient_connect_exception)
        assert stage.state == pipeline_stages_base.ReconnectState.WAITING_TO_RECONNECT

    @pytest.mark.parametrize(
        "state",
        [
            pipeline_stages_base.ReconnectState.CONNECTED_OR_DISCONNECTED,
            pipeline_stages_base.ReconnectState.WAITING_TO_RECONNECT,
        ],
    )
    @pytest.mark.it("Starts a new reconnect timer if the connection fails with a transient error")
    def test_starts_reconnect_timer_on_transient_connect_exception(
        self, stage, connect_op, state, transient_connect_exception, mock_timer
    ):
        stage.state = state
        connect_op.complete(error=transient_connect_exception)
        assert mock_timer.call_count == 1
        assert mock_timer.return_value.start.call_count == 1
