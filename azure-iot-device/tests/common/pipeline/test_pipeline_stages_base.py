# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import logging
import pytest
import sys
import six
import threading
from six.moves import queue
from azure.iot.device.common.pipeline import (
    pipeline_stages_base,
    pipeline_ops_base,
    pipeline_ops_mqtt,
    pipeline_events_base,
    pipeline_exceptions,
)
from tests.common.pipeline.helpers import (
    assert_callback_failed,
    assert_callback_succeeded,
    all_common_ops,
    all_common_events,
    StageTestBase,
    StageRunOpTestBase,
    StageHandlePipelineEventTestBase,
    all_except,
    make_mock_op_or_event,
)
from tests.common.pipeline import pipeline_stage_test

this_module = sys.modules[__name__]
logging.basicConfig(level=logging.DEBUG)


# This fixture makes it look like all test in this file  tests are running
# inside the pipeline thread.  Because this is an autouse fixture, we
# manually add it to the individual test.py files that need it.  If,
# instead, we had added it to some conftest.py, it would be applied to
# every tests in every file and we don't want that.
@pytest.fixture(autouse=True)
def apply_fake_pipeline_thread(fake_pipeline_thread):
    pass


# Workaround for flake8.  A class with this name is actually created inside
# add_base_pipeline_stage_test, but flake8 doesn't know that
class TestPipelineRootStagePipelineThreading:
    pass


pipeline_stage_test.add_base_pipeline_stage_tests(
    cls=pipeline_stages_base.PipelineRootStage,
    module=this_module,
    all_ops=all_common_ops,
    handled_ops=[],
    all_events=all_common_events,
    handled_events=all_common_events,
    methods_that_can_run_in_any_thread=["append_stage", "run_op"],
    extra_initializer_defaults={
        "on_pipeline_event_handler": None,
        "on_connected_handler": None,
        "on_disconnected_handler": None,
        "connected": False,
    },
    positional_arguments=["pipeline_configuration"],
)


@pytest.mark.it("Calls operation callback in callback thread")
def _test_pipeline_root_runs_callback_in_callback_thread(self, stage, mocker):
    # the stage fixture comes from the TestPipelineRootStagePipelineThreading object that
    # this test method gets added to, so it's a PipelineRootStage object
    stage.pipeline_root = stage
    callback_called = threading.Event()

    def callback(op, error):
        assert threading.current_thread().name == "callback"
        callback_called.set()

    op = pipeline_ops_base.ConnectOperation(callback=callback)
    stage.run_op(op)
    callback_called.wait()


@pytest.mark.it("Runs operation in pipeline thread")
def _test_pipeline_root_runs_operation_in_pipeline_thread(
    self, mocker, stage, arbitrary_op, fake_non_pipeline_thread
):
    # the stage fixture comes from the TestPipelineRootStagePipelineThreading object that
    # this test method gets added to, so it's a PipelineRootStage object
    assert threading.current_thread().name != "pipeline"

    def mock_execute_op(self, op):
        print("mock_execute_op called")
        assert threading.current_thread().name == "pipeline"
        op.callback(op)

    mock_execute_op = mocker.MagicMock(mock_execute_op)
    stage._execute_op = mock_execute_op

    stage.run_op(arbitrary_op)
    assert mock_execute_op.call_count == 1


@pytest.mark.it("Calls on_connected_handler in callback thread")
def _test_pipeline_root_runs_on_connected_in_callback_thread(self, stage, mocker):
    stage.pipeline_root = stage
    callback_called = threading.Event()

    def callback(*arg, **argv):
        assert threading.current_thread().name == "callback"
        callback_called.set()

    stage.on_connected_handler = callback

    stage.on_connected()
    callback_called.wait()


@pytest.mark.it("Calls on_disconnected_handler in callback thread")
def _test_pipeline_root_runs_on_disconnected_in_callback_thread(self, stage, mocker):
    stage.pipeline_root = stage
    callback_called = threading.Event()

    def callback(*arg, **argv):
        assert threading.current_thread().name == "callback"
        callback_called.set()

    stage.on_disconnected_handler = callback

    stage.on_disconnected()
    callback_called.wait()


@pytest.mark.it("Calls on_event_received_handler in callback thread")
def _test_pipeline_root_runs_on_event_received_in_callback_thread(
    self, stage, mocker, arbitrary_event
):
    stage.pipeline_root = stage
    callback_called = threading.Event()

    def callback(*arg, **argv):
        assert threading.current_thread().name == "callback"
        callback_called.set()

    stage.on_pipeline_event_handler = callback

    stage.handle_pipeline_event(arbitrary_event)
    callback_called.wait()


TestPipelineRootStagePipelineThreading.test_runs_callback_in_callback_thread = (
    _test_pipeline_root_runs_callback_in_callback_thread
)
TestPipelineRootStagePipelineThreading.test_runs_operation_in_pipeline_thread = (
    _test_pipeline_root_runs_operation_in_pipeline_thread
)
TestPipelineRootStagePipelineThreading.test_pipeline_root_runs_on_connected_in_callback_thread = (
    _test_pipeline_root_runs_on_connected_in_callback_thread
)
TestPipelineRootStagePipelineThreading.test_pipeline_root_runs_on_disconnected_in_callback_thread = (
    _test_pipeline_root_runs_on_disconnected_in_callback_thread
)
TestPipelineRootStagePipelineThreading.test_pipeline_root_runs_on_event_received_in_callback_thread = (
    _test_pipeline_root_runs_on_event_received_in_callback_thread
)

pipeline_stage_test.add_base_pipeline_stage_tests(
    cls=pipeline_stages_base.AutoConnectStage,
    module=this_module,
    all_ops=all_common_ops,
    handled_ops=[
        pipeline_ops_mqtt.MQTTPublishOperation,
        pipeline_ops_mqtt.MQTTSubscribeOperation,
        pipeline_ops_mqtt.MQTTUnsubscribeOperation,
    ],
    all_events=all_common_events,
    handled_events=[],
)

fake_topic = "__fake_topic__"
fake_payload = "__fake_payload__"
ops_that_cause_connection = [
    {
        "op_class": pipeline_ops_mqtt.MQTTPublishOperation,
        "op_init_kwargs": {"topic": fake_topic, "payload": fake_payload, "callback": 1},
    },
    {
        "op_class": pipeline_ops_mqtt.MQTTSubscribeOperation,
        "op_init_kwargs": {"topic": fake_topic, "callback": 1},
    },
    {
        "op_class": pipeline_ops_mqtt.MQTTUnsubscribeOperation,
        "op_init_kwargs": {"topic": fake_topic, "callback": 1},
    },
]


@pytest.mark.parametrize(
    "params",
    ops_that_cause_connection,
    ids=[x["op_class"].__name__ for x in ops_that_cause_connection],
)
@pytest.mark.describe(
    "AutoConnectStage - .run_op() -- called with operation that causes a connection to be established"
)
class TestAutoConnectStageRunOp(StageTestBase):
    @pytest.fixture
    def op(self, mocker, params):
        op = params["op_class"](**params["op_init_kwargs"])
        op.callback = mocker.MagicMock()
        return op

    @pytest.fixture
    def stage(self):
        return pipeline_stages_base.AutoConnectStage()

    @pytest.mark.it("Passes the operation down the pipline when the transport is already connected")
    def test_operation_alrady_connected(self, params, op, stage):
        stage.pipeline_root.connected = True

        stage.run_op(op)

        assert stage.next.run_op.call_count == 1
        assert stage.next.run_op.call_args[0][0] == op

    @pytest.mark.it(
        "Sends a ConnectOperation instead of the op down the pipeline if the transport is not connected"
    )
    def test_sends_connect(self, params, op, stage):
        stage.pipeline_root.connected = False

        stage.run_op(op)

        assert stage.next.run_op.call_count == 1
        assert isinstance(stage.next.run_op.call_args[0][0], pipeline_ops_base.ConnectOperation)

    @pytest.mark.it(
        "Calls the op's callback with the error from the ConnectOperation if that operation fails"
    )
    def test_connect_failure(self, params, op, stage, arbitrary_exception):
        stage.pipeline_root.connected = False

        stage.run_op(op)
        connect_op = stage.next.run_op.call_args[0][0]
        stage.next.complete_op(connect_op, error=arbitrary_exception)

        assert_callback_failed(op=op, error=arbitrary_exception)

    @pytest.mark.it("Waits for the ConnectOperation to complete before pasing the operation down")
    def test_connect_success(self, params, op, stage):
        stage.pipeline_root.connected = False

        stage.run_op(op)
        assert stage.next.run_op.call_count == 1
        connect_op = stage.next.run_op.call_args[0][0]
        stage.next.complete_op(connect_op)

        assert stage.next.run_op.call_count == 2
        assert stage.next.run_op.call_args[0][0] == op

    @pytest.mark.it("calls the op's callback when the operation is complete after connecting")
    def test_operation_complete(self, params, op, stage):
        stage.pipeline_root.connected = False

        stage.run_op(op)
        connect_op = stage.next.run_op.call_args[0][0]
        stage.next.complete_op(connect_op)

        stage.next.complete_op(op)
        assert_callback_succeeded(op=op)

    @pytest.mark.it("calls the op's callback when the operation fails after connecting")
    def test_operation_fails(self, params, op, stage, arbitrary_exception):
        stage.pipeline_root.connected = False

        stage.run_op(op)
        connect_op = stage.next.run_op.call_args[0][0]
        stage.next.complete_op(connect_op)
        stage.next.complete_op(op, error=arbitrary_exception)

        assert_callback_failed(op=op, error=arbitrary_exception)


pipeline_stage_test.add_base_pipeline_stage_tests(
    cls=pipeline_stages_base.ConnectionLockStage,
    module=this_module,
    all_ops=all_common_ops,
    handled_ops=[
        pipeline_ops_base.ConnectOperation,
        pipeline_ops_base.DisconnectOperation,
        pipeline_ops_base.ReconnectOperation,
    ],
    all_events=all_common_events,
    handled_events=[],
    extra_initializer_defaults={"blocked": False, "queue": queue.Queue},
)

connection_ops = [
    {"op_class": pipeline_ops_base.ConnectOperation, "connected_flag_required_to_run": False},
    {"op_class": pipeline_ops_base.DisconnectOperation, "connected_flag_required_to_run": True},
    {"op_class": pipeline_ops_base.ReconnectOperation, "connected_flag_required_to_run": True},
]


class FakeOperation(pipeline_ops_base.PipelineOperation):
    pass


@pytest.mark.describe(
    "ConnectionLockStage - .run_op() -- called with an operation that connects, disconnects, or reconnects"
)
class TestSerializeConnectOpStageRunOp(StageTestBase):
    @pytest.fixture
    def stage(self):
        return pipeline_stages_base.ConnectionLockStage()

    @pytest.fixture
    def connection_op(self, mocker, params):
        return params["op_class"](callback=mocker.MagicMock())

    @pytest.fixture
    def fake_op(self, mocker):
        return FakeOperation(callback=mocker.MagicMock())

    @pytest.fixture
    def fake_ops(self, mocker):
        return [
            FakeOperation(callback=mocker.MagicMock()),
            FakeOperation(callback=mocker.MagicMock()),
            FakeOperation(callback=mocker.MagicMock()),
        ]

    @pytest.mark.it(
        "Immediately completes a ConnectOperation if the transport is already connected"
    )
    def test_connect_while_connected(self, stage, mocker):
        op = pipeline_ops_base.ConnectOperation(callback=mocker.MagicMock())
        stage.pipeline_root.connected = True
        stage.run_op(op)
        assert_callback_succeeded(op=op)

    @pytest.mark.it(
        "Immediately completes a DisconnectOperation if the transport is already disconnected"
    )
    def test_disconnect_while_disconnected(self, stage, mocker):
        op = pipeline_ops_base.DisconnectOperation(callback=mocker.MagicMock())
        stage.pipeline_root.connected = False
        stage.run_op(op)
        assert_callback_succeeded(op=op)

    @pytest.mark.it(
        "Immediately passes the operation down if an operation is not alrady being blocking the stage"
    )
    def test_passes_op_when_not_blocked(self, stage, mocker, fake_op):
        stage.run_op(fake_op)
        assert stage.next.run_op.call_count == 1
        assert stage.next.run_op.call_args[0][0] == fake_op

    @pytest.mark.parametrize(
        "params", connection_ops, ids=[x["op_class"].__name__ for x in connection_ops]
    )
    @pytest.mark.it(
        "Does not immediately pass the operation down if a different operation is currently blcking the stage"
    )
    def test_does_not_pass_op_if_blocked(self, params, stage, connection_op, fake_op):
        stage.pipeline_root.connected = params["connected_flag_required_to_run"]
        stage.run_op(connection_op)
        stage.run_op(fake_op)

        assert stage.next.run_op.call_count == 1
        assert stage.next.run_op.call_args[0][0] == connection_op

    @pytest.mark.parametrize(
        "params", connection_ops, ids=[x["op_class"].__name__ for x in connection_ops]
    )
    @pytest.mark.it(
        "Waits for the operation that is currently blocking the stage to complete before passing the op down"
    )
    def test_waits_for_serialized_op_to_complete_before_passing_blocked_op(
        self, params, stage, connection_op, fake_op
    ):
        stage.pipeline_root.connected = params["connected_flag_required_to_run"]
        stage.run_op(connection_op)
        stage.run_op(fake_op)
        stage.next.complete_op(connection_op)

        assert stage.next.run_op.call_count == 2
        assert stage.next.run_op.call_args[0][0] == fake_op

    @pytest.mark.parametrize(
        "params", connection_ops, ids=[x["op_class"].__name__ for x in connection_ops]
    )
    @pytest.mark.it("Fails the operation if the operation that previously blocked the stage fails")
    def test_fails_blocked_op_if_serialized_op_fails(
        self, params, stage, connection_op, fake_op, arbitrary_exception
    ):
        stage.pipeline_root.connected = params["connected_flag_required_to_run"]
        stage.run_op(connection_op)
        stage.run_op(fake_op)
        stage.next.complete_op(connection_op, error=arbitrary_exception)
        assert_callback_failed(op=fake_op, error=arbitrary_exception)

    @pytest.mark.parametrize(
        "params", connection_ops, ids=[x["op_class"].__name__ for x in connection_ops]
    )
    @pytest.mark.it(
        "Can pend multiple operations while waiting for an operation that is currently blocking the stage"
    )
    def test_blocks_multiple_ops(self, params, stage, connection_op, fake_ops):
        stage.pipeline_root.connected = params["connected_flag_required_to_run"]
        stage.run_op(connection_op)
        for op in fake_ops:
            stage.run_op(op)
        assert stage.next.run_op.call_count == 1

    @pytest.mark.parametrize(
        "params", connection_ops, ids=[x["op_class"].__name__ for x in connection_ops]
    )
    @pytest.mark.it(
        "Passes down all pending operations after the operation that previously blocked the stage completes successfully"
    )
    def test_unblocks_multiple_ops(self, params, stage, connection_op, fake_ops):
        stage.pipeline_root.connected = params["connected_flag_required_to_run"]
        stage.run_op(connection_op)
        for op in fake_ops:
            stage.run_op(op)

        stage.next.complete_op(connection_op)

        assert stage.next.run_op.call_count == 1 + len(fake_ops)

        # zip our ops and our calls together and make sure they match
        run_ops = zip(fake_ops, stage.next.run_op.call_args_list[1:])
        for run_op in run_ops:
            op = run_op[0]
            call_args = run_op[1]
            assert op == call_args[0][0]

    @pytest.mark.parametrize(
        "params", connection_ops, ids=[x["op_class"].__name__ for x in connection_ops]
    )
    @pytest.mark.it(
        "Fails all pending operations after the operation that previously blocked the stage fails"
    )
    def test_fails_multiple_ops(self, params, stage, connection_op, fake_ops, arbitrary_exception):
        stage.pipeline_root.connected = params["connected_flag_required_to_run"]
        stage.run_op(connection_op)
        for op in fake_ops:
            stage.run_op(op)

        stage.next.complete_op(connection_op, error=arbitrary_exception)

        for op in fake_ops:
            assert_callback_failed(op=op, error=arbitrary_exception)

    @pytest.mark.it(
        "Does not immediately pass down operations in the queue if an operation in the queue causes the stage to re-block"
    )
    def test_re_blocks_ops_from_queue(self, stage, mocker):
        first_connect = pipeline_ops_base.ConnectOperation(callback=mocker.MagicMock())
        first_fake_op = FakeOperation(callback=mocker.MagicMock())
        second_connect = pipeline_ops_base.ReconnectOperation(callback=mocker.MagicMock())
        second_fake_op = FakeOperation(callback=mocker.MagicMock())

        stage.run_op(first_connect)
        stage.run_op(first_fake_op)
        stage.run_op(second_connect)
        stage.run_op(second_fake_op)

        # at this point, ops are pended waiting for the first connect to complete.  Verify this and complete the connect.
        assert stage.next.run_op.call_count == 1
        assert stage.next.run_op.call_args[0][0] == first_connect
        stage.next.complete_op(first_connect)

        # The connect is complete.  This passes down first_fake_op and second_connect and second_fake_op gets pended waiting i
        # for second_connect to complete.
        # Note: this isn't ideal.  In a perfect world, second_connect wouldn't start until first_fake_op is complete, but we
        # dont have this logic in place yet.
        assert stage.next.run_op.call_count == 3
        assert stage.next.run_op.call_args_list[1][0][0] == first_fake_op
        assert stage.next.run_op.call_args_list[2][0][0] == second_connect

        # now, complete second_connect to give second_fake_op a chance to get passed down
        stage.next.complete_op(second_connect)
        assert stage.next.run_op.call_count == 4
        assert stage.next.run_op.call_args_list[3][0][0] == second_fake_op

    @pytest.mark.parametrize(
        "params",
        [
            pytest.param(
                {
                    "pre_connected_flag": True,
                    "first_connection_op": pipeline_ops_base.DisconnectOperation,
                    "mid_connect_flag": False,
                    "second_connection_op": pipeline_ops_base.DisconnectOperation,
                },
                id="Disconnect followed by Disconnect",
            ),
            pytest.param(
                {
                    "pre_connected_flag": False,
                    "first_connection_op": pipeline_ops_base.ConnectOperation,
                    "mid_connect_flag": True,
                    "second_connection_op": pipeline_ops_base.ConnectOperation,
                },
                id="Connect followed by Connect",
            ),
            pytest.param(
                {
                    "pre_connected_flag": True,
                    "first_connection_op": pipeline_ops_base.ReconnectOperation,
                    "mid_connect_flag": True,
                    "second_connection_op": pipeline_ops_base.ConnectOperation,
                },
                id="Reconnect followed by Connect",
            ),
        ],
    )
    @pytest.mark.it(
        "Immediately completes a second op which was waiting for a first op that succeeded"
    )
    def test_immediately_completes_second_op(self, stage, params, mocker):
        first_connection_op = params["first_connection_op"](mocker.MagicMock())
        second_connection_op = params["second_connection_op"](mocker.MagicMock())
        stage.pipeline_root.connected = params["pre_connected_flag"]

        stage.run_op(first_connection_op)
        stage.run_op(second_connection_op)

        # first_connection_op has been passed down.  second_connection_op is waiting for first disconnect to complete.
        assert stage.next.run_op.call_count == 1
        assert stage.next.run_op.call_args[0][0] == first_connection_op

        # complete first_connection_op
        stage.pipeline_root.connected = params["mid_connect_flag"]
        stage.next.complete_op(first_connection_op)

        # second connect_op should be completed without having been passed down.
        assert stage.next.run_op.call_count == 1
        assert_callback_succeeded(op=second_connection_op)


pipeline_stage_test.add_base_pipeline_stage_tests(
    cls=pipeline_stages_base.CoordinateRequestAndResponseStage,
    module=this_module,
    all_ops=all_common_ops,
    handled_ops=[pipeline_ops_base.RequestAndResponseOperation],
    all_events=all_common_events,
    handled_events=[pipeline_events_base.ResponseEvent],
    extra_initializer_defaults={"pending_responses": dict},
)


fake_request_type = "__fake_request_type__"
fake_method = "__fake_method__"
fake_resource_location = "__fake_resource_location__"
fake_request_body = "__fake_request_body__"
fake_status_code = "__fake_status_code__"
fake_response_body = "__fake_response_body__"
fake_request_id = "__fake_request_id__"


def make_fake_request_and_response(mocker):
    return pipeline_ops_base.RequestAndResponseOperation(
        request_type=fake_request_type,
        method=fake_method,
        resource_location=fake_resource_location,
        request_body=fake_request_body,
        callback=mocker.MagicMock(),
    )


@pytest.mark.describe(
    "CoordinateRequestAndResponse - .run_op() -- called with RequestAndResponseOperation"
)
class TestCoordinateRequestAndResponseSendIotRequestRunOp(StageTestBase):
    @pytest.fixture
    def op(self, mocker):
        return make_fake_request_and_response(mocker)

    @pytest.fixture
    def stage(self):
        return pipeline_stages_base.CoordinateRequestAndResponseStage()

    @pytest.mark.it(
        "Sends an RequestOperation op to the next stage with the same parameters and a newly allocated request_id"
    )
    def test_sends_op_and_validates_new_op(self, stage, op):
        stage.run_op(op)
        assert stage.next.run_op.call_count == 1
        new_op = stage.next.run_op.call_args[0][0]
        assert isinstance(new_op, pipeline_ops_base.RequestOperation)
        assert new_op.request_type == op.request_type
        assert new_op.method == op.method
        assert new_op.resource_location == op.resource_location
        assert new_op.request_body == op.request_body
        assert new_op.request_id

    @pytest.mark.it("Does not complete the SendIotRequestAndwaitForResponse op")
    def test_sends_op_and_verifies_no_response(self, stage, op):
        stage.run_op(op)
        assert op.callback.call_count == 0

    @pytest.mark.it("Fails RequestAndResponseOperation if there is no next stage")
    def test_no_next_stage(self, stage, op):
        stage.next = None
        stage.run_op(op)
        assert_callback_failed(op=op)

    @pytest.mark.it("Generates a new request_id for every operation")
    def test_sends_two_ops_and_validates_request_id(self, stage, op, mocker):
        op2 = make_fake_request_and_response(mocker)
        stage.run_op(op)
        stage.run_op(op2)
        assert stage.next.run_op.call_count == 2
        new_op = stage.next.run_op.call_args_list[0][0][0]
        new_op2 = stage.next.run_op.call_args_list[1][0][0]
        assert new_op.request_id != new_op2.request_id

    @pytest.mark.it(
        "Fails RequestAndResponseOperation if an Exception is raised in the RequestOperation op"
    )
    def test_new_op_raises_exception(self, stage, op, mocker, arbitrary_exception):
        stage.next._execute_op = mocker.Mock(side_effect=arbitrary_exception)
        stage.run_op(op)
        assert_callback_failed(op=op)

    @pytest.mark.it("Allows BaseExceptions rised on the RequestOperation op to propogate")
    def test_new_op_raises_base_exception(self, stage, op, mocker, arbitrary_base_exception):
        stage.next._execute_op = mocker.Mock(side_effect=arbitrary_base_exception)
        with pytest.raises(arbitrary_base_exception.__class__) as e_info:
            stage.run_op(op)
        assert op.callback.call_count == 0
        assert e_info.value is arbitrary_base_exception


@pytest.mark.describe(
    "CoordinateRequestAndResponseStage - .handle_pipeline_event() -- called with ResponseEvent"
)
class TestCoordinateRequestAndResponseSendIotRequestHandleEvent(StageTestBase):
    @pytest.fixture
    def op(self, mocker):
        return make_fake_request_and_response(mocker)

    @pytest.fixture
    def stage(self):
        return pipeline_stages_base.CoordinateRequestAndResponseStage()

    @pytest.fixture
    def iot_request(self, stage, op):
        stage.run_op(op)
        return stage.next.run_op.call_args[0][0]

    @pytest.fixture
    def iot_response(self, stage, iot_request):
        return pipeline_events_base.ResponseEvent(
            request_id=iot_request.request_id,
            status_code=fake_status_code,
            response_body=fake_response_body,
        )

    @pytest.mark.it(
        "Completes the RequestAndResponseOperation op with the matching request_id including response_body and status_code"
    )
    def test_completes_op_with_matching_request_id(self, stage, op, iot_response):
        stage.next.send_event_up(iot_response)
        assert_callback_succeeded(op=op)
        assert op.status_code == iot_response.status_code
        assert op.response_body == iot_response.response_body

    @pytest.mark.it(
        "Calls the unhandled error handler if there is no previous stage when request_id matches"
    )
    def test_matching_request_id_with_no_previous_stage(
        self, stage, op, iot_response, unhandled_error_handler
    ):
        stage.next.previous = None
        stage.next.send_event_up(iot_response)
        assert unhandled_error_handler.call_count == 1

    @pytest.mark.it(
        "Does nothing if an IotResponse with an identical request_id is received a second time"
    )
    def test_ignores_duplicate_request_id(self, stage, op, iot_response, unhandled_error_handler):
        stage.next.send_event_up(iot_response)
        assert_callback_succeeded(op=op)
        op.callback.reset_mock()

        stage.next.send_event_up(iot_response)
        assert op.callback.call_count == 0
        assert unhandled_error_handler.call_count == 0

    @pytest.mark.it(
        "Does nothing if an IotResponse with a request_id is received for an operation that returned failure"
    )
    def test_ignores_request_id_from_failure(
        self, stage, op, mocker, unhandled_error_handler, arbitrary_exception
    ):
        stage.next._execute_op = mocker.MagicMock(side_effect=arbitrary_exception)
        stage.run_op(op)

        req = stage.next.run_op.call_args[0][0]
        resp = pipeline_events_base.ResponseEvent(
            request_id=req.request_id,
            status_code=fake_status_code,
            response_body=fake_response_body,
        )

        op.callback.reset_mock()
        stage.next.send_event_up(resp)
        assert op.callback.call_count == 0
        assert unhandled_error_handler.call_count == 0

    @pytest.mark.it("Does nothing if an IotResponse with an unknown request_id is received")
    def test_ignores_unknown_request_id(self, stage, op, iot_response, unhandled_error_handler):
        iot_response.request_id = fake_request_id
        stage.next.send_event_up(iot_response)
        assert op.callback.call_count == 0
        assert unhandled_error_handler.call_count == 0


"""
A note on terms in the OpTimeoutStage tests:
    No-timeout ops are ops that don't need a timeout check
    Yes-timeout ops are ops that do need a timeout check
"""
timeout_intervals = {
    pipeline_ops_mqtt.MQTTSubscribeOperation: 10,
    pipeline_ops_mqtt.MQTTUnsubscribeOperation: 10,
}
yes_timeout_ops = list(timeout_intervals.keys())
no_timeout_ops = all_except(all_common_ops, yes_timeout_ops)

pipeline_stage_test.add_base_pipeline_stage_tests(
    cls=pipeline_stages_base.OpTimeoutStage,
    module=this_module,
    all_ops=all_common_ops,
    handled_ops=yes_timeout_ops,
    all_events=all_common_events,
    handled_events=[],
    extra_initializer_defaults={"timeout_intervals": timeout_intervals},
)


@pytest.fixture()
def mock_timer(mocker):
    return mocker.patch(
        "azure.iot.device.common.pipeline.pipeline_stages_base.Timer", autospec=True
    )


@pytest.mark.describe("OpTimeoutStage - run_op()")
class TestOpTimeoutStageRunOp(StageTestBase):
    @pytest.fixture(params=yes_timeout_ops)
    def yes_timeout_op(self, request, mocker):
        op = make_mock_op_or_event(request.param)
        op.callback = mocker.MagicMock()
        return op

    @pytest.fixture(params=no_timeout_ops)
    def no_timeout_op(self, request, mocker):
        op = make_mock_op_or_event(request.param)
        op.callback = mocker.MagicMock()
        return op

    @pytest.fixture
    def stage(self):
        return pipeline_stages_base.OpTimeoutStage()

    @pytest.mark.it("Sends ops that don't need a timer to the next stage")
    def test_sends_no_timer_op_down(self, stage, mock_timer, no_timeout_op):
        stage.run_op(no_timeout_op)
        assert stage.next.run_op.call_count == 1
        assert stage.next.run_op.call_args[0][0] == no_timeout_op

    @pytest.mark.it("Sends ops that do need a timer to the next stage")
    def test_sends_yes_timer_op_down(self, stage, mock_timer, yes_timeout_op):
        stage.run_op(yes_timeout_op)
        assert stage.next.run_op.call_count == 1
        assert stage.next.run_op.call_args[0][0] == yes_timeout_op

    @pytest.mark.it("Does not set a timer for ops that don't need a timer set")
    def test_does_not_set_timer(self, stage, mock_timer, no_timeout_op):
        stage.run_op(no_timeout_op)
        assert mock_timer.call_count == 0

    @pytest.mark.it("Set a timer for ops that need a timer set")
    def test_sets_timer(self, stage, mock_timer, yes_timeout_op):
        stage.run_op(yes_timeout_op)
        assert mock_timer.call_count == 1

    @pytest.mark.it("Starts the timer based on the timeout interval")
    def test_uses_timeout_interval(self, stage, mock_timer, yes_timeout_op):
        stage.run_op(yes_timeout_op)
        assert mock_timer.call_args[0][0] == timeout_intervals[yes_timeout_op.__class__]
        assert mock_timer.return_value.start.call_count == 1
        assert yes_timeout_op.timeout_timer == mock_timer.return_value

    @pytest.mark.it("Clears the timer when the op completes successfully")
    def test_clears_timer_on_success(self, stage, mock_timer, yes_timeout_op, next_stage_succeeds):
        stage.run_op(yes_timeout_op)
        assert mock_timer.return_value.cancel.call_count == 1
        assert getattr(yes_timeout_op, "timeout_timer", None) is None

    @pytest.mark.it("Clears the timer when the op fails with an arbitrary exception")
    def test_clears_timer_on_arbitrary_exception(
        self, stage, mock_timer, yes_timeout_op, next_stage_raises_arbitrary_exception
    ):
        stage.run_op(yes_timeout_op)
        assert mock_timer.return_value.cancel.call_count == 1
        assert getattr(yes_timeout_op, "timeout_timer", None) is None

    @pytest.mark.it("Does not clear the timer when the op fails with an arbitrary base exception")
    def test_doesnt_clear_timer_on_arbitrary_base_exception(
        self,
        stage,
        mock_timer,
        yes_timeout_op,
        next_stage_raises_arbitrary_base_exception,
        arbitrary_base_exception,
    ):
        with pytest.raises(arbitrary_base_exception.__class__):
            stage.run_op(yes_timeout_op)
        assert mock_timer.return_value.cancel.call_count == 0
        assert yes_timeout_op.timeout_timer == mock_timer.return_value

    @pytest.mark.it("Clears the timer when the op times out")
    def test_clears_timer_on_timeout(self, stage, mock_timer, yes_timeout_op):
        stage.run_op(yes_timeout_op)
        assert yes_timeout_op.timeout_timer == mock_timer.return_value
        timer_callback = mock_timer.call_args[0][1]
        timer_callback()
        assert getattr(yes_timeout_op, "timeout_timer", None) is None

    @pytest.mark.it("Calls the original callback with no error when the op completes with no error")
    def test_calls_callback_on_success(
        self, stage, mock_timer, yes_timeout_op, next_stage_succeeds
    ):
        stage.run_op(yes_timeout_op)
        assert_callback_succeeded(op=yes_timeout_op)

    @pytest.mark.it(
        "Calls the original callback with error when the op fails with an arbitrary exception"
    )
    def test_calls_callback_on_arbitrary_exception(
        self,
        stage,
        mock_timer,
        yes_timeout_op,
        next_stage_raises_arbitrary_exception,
        arbitrary_exception,
    ):
        stage.run_op(yes_timeout_op)
        assert_callback_failed(op=yes_timeout_op, error=arbitrary_exception)

    @pytest.mark.it(
        "Does not call the original callback when the op fails with an an arbitrary base exception"
    )
    def test_calls_callback_on_arbitrary_base_exception(
        self,
        stage,
        mock_timer,
        yes_timeout_op,
        next_stage_raises_arbitrary_base_exception,
        arbitrary_base_exception,
    ):
        callback = yes_timeout_op.callback  # capture before run_op because it changes inside run_op
        with pytest.raises(arbitrary_base_exception.__class__):
            stage.run_op(yes_timeout_op)
        assert callback.call_count == 0

    @pytest.mark.it("Calls the original callback with a PipelineTimeoutError when the op times out")
    def test_calls_callback_on_timeout(self, stage, mock_timer, yes_timeout_op):
        stage.run_op(yes_timeout_op)
        timer_callback = mock_timer.call_args[0][1]
        timer_callback()
        assert_callback_failed(op=yes_timeout_op, error=pipeline_exceptions.PipelineTimeoutError)


"""
A note on terms in the RetryStage tests:
    No-retry ops are ops that will never be retried.
    Yes-retry ops are ops that might be retired, depending on the error.
    Retry errors are errors that cause a retry for yes-retry ops
    Arbitrary errors will never cause a retry
"""

retry_intervals = {
    pipeline_ops_mqtt.MQTTSubscribeOperation: 20,
    pipeline_ops_mqtt.MQTTUnsubscribeOperation: 20,
}
yes_retry_ops = list(retry_intervals.keys())
no_retry_ops = all_except(all_common_ops, yes_retry_ops)
retry_errors = [pipeline_exceptions.PipelineTimeoutError]

pipeline_stage_test.add_base_pipeline_stage_tests(
    cls=pipeline_stages_base.RetryStage,
    module=this_module,
    all_ops=all_common_ops,
    handled_ops=[],
    all_events=all_common_events,
    handled_events=[],
    extra_initializer_defaults={"retry_intervals": retry_intervals, "ops_waiting_to_retry": []},
)


class RetryStageTestOpSend(object):
    """
    Tests for RetryStage to verify that ops get sent down
    """

    @pytest.fixture(params=no_retry_ops)
    def no_retry_op(self, request, mocker):
        op = make_mock_op_or_event(request.param)
        op.callback = mocker.MagicMock()
        return op

    @pytest.fixture(params=yes_retry_ops)
    def yes_retry_op(self, request, mocker):
        op = make_mock_op_or_event(request.param)
        op.callback = mocker.MagicMock()
        return op

    @pytest.mark.it("Sends ops that don't need retry to the next stage")
    def test_sends_no_retry_op_down(self, stage, no_retry_op):
        stage.run_op(no_retry_op)
        assert stage.next.run_op.call_count == 1
        assert stage.next.run_op.call_args[0][0] == no_retry_op

    @pytest.mark.it("Sends ops that do need retry to the next stage")
    def test_sends_yes_retry_op_down(self, stage, yes_retry_op):
        stage.run_op(yes_retry_op)
        assert stage.next.run_op.call_count == 1
        assert stage.next.run_op.call_args[0][0] == yes_retry_op


class RetryStageTestNoRetryOpCallback(object):
    """
    Tests for RetryStage for callbacks with no-retry ops.
    """

    @pytest.fixture(params=retry_errors)
    def retry_error(self, request):
        return request.param()

    @pytest.mark.it(
        "Calls the op callback with no error when an op that doesn't need retry succeeds"
    )
    def test_calls_callback_on_no_retry_op_success(self, stage, no_retry_op, next_stage_succeeds):
        stage.run_op(no_retry_op)
        assert_callback_succeeded(op=no_retry_op)

    @pytest.mark.it(
        "Calls the op callback with the correct error when an op that doesn't need retry fail with an arbitrary error"
    )
    def test_calls_callback_on_no_retry_op_arbitrary_exception(
        self, stage, no_retry_op, next_stage_raises_arbitrary_exception, arbitrary_exception
    ):
        stage.run_op(no_retry_op)
        assert_callback_failed(op=no_retry_op, error=arbitrary_exception)

    @pytest.mark.it(
        "Calls the op callback with the correct error when an op that doesn't need retry fail with a retry error"
    )
    def test_calls_callback_on_no_retry_op_retry_error(self, stage, no_retry_op, retry_error):
        stage.run_op(no_retry_op)
        stage.next.complete_op(op=no_retry_op, error=retry_error)
        assert_callback_failed(op=no_retry_op, error=retry_error)


class RetryStageTestNoRetryOpSetTimer(object):
    """
    Tests for RetryStage for not setting a timer for no-retry ops
    """

    @pytest.mark.it("Does not set a retry timer when an op that doesn't need retry succeeds")
    def test_no_timer_on_no_retry_op_success(
        self, stage, no_retry_op, next_stage_succeeds, mock_timer
    ):
        stage.run_op(no_retry_op)
        assert mock_timer.call_count == 0

    @pytest.mark.it(
        "Does not set a retry timer when an op that doesn't need retry fail with an arbitrary error"
    )
    def test_no_timer_on_no_retry_op_arbitrary_exception(
        self, stage, no_retry_op, next_stage_raises_arbitrary_exception, mock_timer
    ):
        stage.run_op(no_retry_op)
        assert mock_timer.call_count == 0

    @pytest.mark.it(
        "Does not set a retry timer when an op that doesn't need retry fail with a retry error"
    )
    def test_no_timer_on_no_retry_op_retry_error(self, stage, no_retry_op, retry_error, mock_timer):
        stage.run_op(no_retry_op)
        stage.next.complete_op(op=no_retry_op, error=retry_error)
        assert mock_timer.call_count == 0


class RetryStageTestYesRetryOpCallback(object):
    """
    Tests for RetryStage for callbacks with yes-retry ops
    """

    @pytest.mark.it("Calls the op callback with no error when an op that need retry succeeds")
    def test_callback_on_yes_retry_op_success(self, stage, yes_retry_op, next_stage_succeeds):
        stage.run_op(yes_retry_op)
        assert_callback_succeeded(op=yes_retry_op)

    @pytest.mark.it(
        "Calls the op callback with error when an op that need retry fails with an arbitrary error"
    )
    def test_callback_on_yes_retry_op_arbitrary_exception(
        self, stage, yes_retry_op, next_stage_raises_arbitrary_exception, arbitrary_exception
    ):
        stage.run_op(yes_retry_op)
        assert_callback_failed(op=yes_retry_op, error=arbitrary_exception)

    @pytest.mark.it(
        "Does not call the op callback when an op that need retry fail with a retry error"
    )
    def test_no_callback_on_yes_retry_op_retry_error(
        self, stage, yes_retry_op, retry_error, mock_timer
    ):
        stage.run_op(yes_retry_op)
        stage.next.complete_op(op=yes_retry_op, error=retry_error)
        assert yes_retry_op.callback.call_count == 0


class RetryStageTestYesRetryOpSetTimer(object):
    """
    Tests for RetryStage for setting or not setting timers for yes-retry ops
    """

    @pytest.mark.it("Does not set a retry timer when an op that need retry succeeds")
    def test_no_timer_on_yes_retry_op_success(
        self, stage, yes_retry_op, next_stage_succeeds, mock_timer
    ):
        stage.run_op(yes_retry_op)
        assert mock_timer.call_count == 0

    @pytest.mark.it(
        "Does not set a retry timer when an op that need retry fail with an arbitrary error"
    )
    def test_no_timer_on_yes_retry_op_arbitrary_exception(
        self, stage, yes_retry_op, next_stage_raises_arbitrary_exception, mock_timer
    ):
        stage.run_op(yes_retry_op)
        assert mock_timer.call_count == 0

    @pytest.mark.it("Sets a retry timer when an op that need retry fail with retry error")
    def test_yes_timer_on_yes_retry_op_retry_error(
        self, stage, yes_retry_op, retry_error, mock_timer
    ):
        stage.run_op(yes_retry_op)
        stage.next.complete_op(op=yes_retry_op, error=retry_error)
        assert mock_timer.call_count == 1

    @pytest.mark.it("Uses the correct timout when setting a retry timer")
    def test_uses_correct_timer_interval(self, stage, yes_retry_op, retry_error, mock_timer):
        stage.run_op(yes_retry_op)
        stage.next.complete_op(op=yes_retry_op, error=retry_error)
        assert mock_timer.call_args[0][0] == retry_intervals[yes_retry_op.__class__]


class RetryStageTestResubmitOp(object):
    """
    Tests for RetryStage for resubmiting ops for retry
    """

    @pytest.mark.it("Retries an op that needs retry after the retry interval elapses")
    def test_resubmits_after_retry_interval_elapses(
        self, stage, yes_retry_op, retry_error, mock_timer
    ):
        stage.run_op(yes_retry_op)
        assert stage.next.run_op.call_count == 1
        stage.next.run_op.reset_mock()
        stage.next.complete_op(op=yes_retry_op, error=retry_error)
        timer_callback = mock_timer.call_args[0][1]
        timer_callback()
        assert stage.next.run_op.call_count == 1
        assert stage.next.run_op.call_args[0][0] == yes_retry_op

    @pytest.mark.it("Clears the complete attribute on the op when retrying")
    def test_clears_complete_attribute_before_resubmitting(
        self, stage, yes_retry_op, retry_error, mock_timer
    ):
        stage.run_op(yes_retry_op)
        stage.next.complete_op(op=yes_retry_op, error=retry_error)
        assert yes_retry_op.completed
        timer_callback = mock_timer.call_args[0][1]
        timer_callback()
        assert not yes_retry_op.completed

    @pytest.mark.it("Clears the retry timer attribute on the op when retrying")
    def test_clears_retry_timer_before_retrying(self, stage, yes_retry_op, retry_error, mock_timer):
        stage.run_op(yes_retry_op)
        stage.next.complete_op(op=yes_retry_op, error=retry_error)
        assert yes_retry_op.retry_timer
        timer_callback = mock_timer.call_args[0][1]
        timer_callback()
        assert getattr(yes_retry_op, "retry_timer", None) is None


class RetryStageTestResubmitedOpCompletion(object):
    """
    Tests for RetryStage for resubmitted op completion
    """

    @pytest.mark.it("Calls the original callback with success when the retried op succeeds")
    def test_calls_callback_on_retried_op_success(
        self, stage, yes_retry_op, retry_error, mock_timer
    ):
        op_callback = yes_retry_op.callback
        stage.run_op(yes_retry_op)
        stage.next.complete_op(op=yes_retry_op, error=retry_error)
        timer_callback = mock_timer.call_args[0][1]
        timer_callback()
        assert op_callback.call_count == 0
        stage.next.complete_op(op=yes_retry_op)
        assert yes_retry_op.callback == op_callback
        assert_callback_succeeded(op=yes_retry_op)

    @pytest.mark.it(
        "Calls the original callback with error when the retried op compltes with an arbitrary error"
    )
    def test_calls_callback_on_retried_op_arbitrary_exception(
        self, stage, yes_retry_op, retry_error, mock_timer, arbitrary_exception, mocker
    ):

        stage.run_op(yes_retry_op)
        stage.next.complete_op(op=yes_retry_op, error=retry_error)
        timer_callback = mock_timer.call_args[0][1]
        timer_callback()
        stage.next.complete_op(op=yes_retry_op, error=arbitrary_exception)
        assert_callback_failed(op=yes_retry_op, error=arbitrary_exception)

    @pytest.mark.it(
        "Does not calls the original callback with error when the retried op compltes with an retry error"
    )
    def test_no_callback_on_retried_op_retry_error(
        self, stage, yes_retry_op, retry_error, mock_timer
    ):
        op_callback = yes_retry_op.callback
        stage.run_op(yes_retry_op)
        stage.next.complete_op(op=yes_retry_op, error=retry_error)
        timer_callback = mock_timer.call_args[0][1]
        timer_callback()
        stage.next.complete_op(op=yes_retry_op, error=retry_error)
        assert op_callback.call_count == 0

    @pytest.mark.it("Sets a new retry timer error when the retried op compltes with an retry error")
    def test_sets_timer_on_retried_op_retry_error(
        self, stage, yes_retry_op, retry_error, mock_timer
    ):
        stage.run_op(yes_retry_op)
        stage.next.complete_op(op=yes_retry_op, error=retry_error)
        assert mock_timer.call_count == 1
        timer_callback = mock_timer.call_args[0][1]
        timer_callback()
        stage.next.complete_op(op=yes_retry_op, error=retry_error)
        assert mock_timer.call_count == 2


@pytest.mark.describe("RetryStage - run_op()")
class TestRetryStageRunOp(
    StageTestBase,
    RetryStageTestOpSend,
    RetryStageTestNoRetryOpCallback,
    RetryStageTestNoRetryOpSetTimer,
    RetryStageTestYesRetryOpCallback,
    RetryStageTestYesRetryOpSetTimer,
    RetryStageTestResubmitOp,
    RetryStageTestResubmitedOpCompletion,
):
    @pytest.fixture
    def stage(self):
        return pipeline_stages_base.RetryStage()
