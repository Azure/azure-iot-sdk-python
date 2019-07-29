# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import logging
import pytest
import sys
import threading
from azure.iot.device.common.pipeline import (
    pipeline_stages_base,
    pipeline_ops_base,
    pipeline_events_base,
    operation_flow,
)
from tests.common.pipeline.helpers import (
    make_mock_stage,
    assert_callback_failed,
    assert_callback_succeeded,
    UnhandledException,
    all_common_ops,
    all_common_events,
)
from tests.common.pipeline import pipeline_stage_test

this_module = sys.modules[__name__]
logging.basicConfig(level=logging.INFO)


# This fixture makes it look like all test in this file  tests are running
# inside the pipeline thread.  Because this is an autouse fixture, we
# manually add it to the individual test.py files that need it.  If,
# instead, we had added it to some conftest.py, it would be applied to
# every tests in every file and we don't want that.
@pytest.fixture(autouse=True)
def apply_fake_pipeline_thread(fake_pipeline_thread):
    pass


pipeline_stage_test.add_base_pipeline_stage_tests(
    cls=pipeline_stages_base.EnsureConnectionStage,
    module=this_module,
    all_ops=all_common_ops,
    handled_ops=[
        pipeline_ops_base.ConnectOperation,
        pipeline_ops_base.DisconnectOperation,
        pipeline_ops_base.EnableFeatureOperation,
        pipeline_ops_base.DisableFeatureOperation,
        pipeline_ops_base.SendIotRequestAndWaitForResponseOperation,
        pipeline_ops_base.SendIotRequestOperation,
    ],
    all_events=all_common_events,
    handled_events=[],
)


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
)


@pytest.mark.it("Calls operation callback in callback thread")
def _test_pipeline_root_runs_callback_in_callback_thread(self, stage, mocker):
    # the stage fixture comes from the TestPipelineRootStagePipelineThreading object that
    # this test method gets added to, so it's a PipelineRootStage object
    stage.pipeline_root = stage
    callback_called = threading.Event()

    def callback(op):
        assert threading.current_thread().name == "callback"
        callback_called.set()

    op = pipeline_ops_base.ConnectOperation(callback=callback)
    stage.run_op(op)
    callback_called.wait()


@pytest.mark.it("Runs operation in pipeline thread")
def _test_pipeline_root_runs_operation_in_pipeline_thread(
    self, mocker, stage, op, fake_non_pipeline_thread
):
    # the stage fixture comes from the TestPipelineRootStagePipelineThreading object that
    # this test method gets added to, so it's a PipelineRootStage object
    assert threading.current_thread().name != "pipeline"

    def mock_run_op(self, op):
        print("mock_run_op called")
        assert threading.current_thread().name == "pipeline"
        op.callback(op)

    mock_run_op = mocker.MagicMock(mock_run_op)
    stage._run_op = mock_run_op

    stage.run_op(op)
    assert mock_run_op.call_count == 1


TestPipelineRootStagePipelineThreading.test_runs_callback_in_callback_thread = (
    _test_pipeline_root_runs_callback_in_callback_thread
)
TestPipelineRootStagePipelineThreading.test_runs_operation_in_pipeline_thread = (
    _test_pipeline_root_runs_operation_in_pipeline_thread
)


pipeline_stage_test.add_base_pipeline_stage_tests(
    cls=pipeline_stages_base.CoordinateRequestAndResponseStage,
    module=this_module,
    all_ops=all_common_ops,
    handled_ops=[pipeline_ops_base.SendIotRequestAndWaitForResponseOperation],
    all_events=all_common_events,
    handled_events=[pipeline_events_base.IotResponseEvent],
)


fake_request_type = "__fake_request_type__"
fake_method = "__fake_method__"
fake_resource_location = "__fake_resource_location__"
fake_request_body = "__fake_request_body__"
fake_status_code = "__fake_status_code__"
fake_response_body = "__fake_response_body__"
fake_request_id = "__fake_request_id__"


def make_fake_request_and_response(mocker):
    return pipeline_ops_base.SendIotRequestAndWaitForResponseOperation(
        request_type=fake_request_type,
        method=fake_method,
        resource_location=fake_resource_location,
        request_body=fake_request_body,
        callback=mocker.MagicMock(),
    )


@pytest.mark.describe(
    "CoordinateRequestAndResponse - .run_op() -- called with SendIotRequestAndWaitForResponseOperation"
)
class TestCoordinateRequestAndResponseSendIotRequestRunOp(object):
    @pytest.fixture
    def op(self, mocker):
        return make_fake_request_and_response(mocker)

    @pytest.fixture
    def stage(self, mocker):
        return make_mock_stage(mocker, pipeline_stages_base.CoordinateRequestAndResponseStage)

    @pytest.mark.it(
        "Sends an SendIotRequestOperation op to the next stage with the same parameters and a newly allocated request_id"
    )
    def test_sends_op_and_validates_new_op(self, stage, op):
        stage.run_op(op)
        assert stage.next.run_op.call_count == 1
        new_op = stage.next.run_op.call_args[0][0]
        assert isinstance(new_op, pipeline_ops_base.SendIotRequestOperation)
        assert new_op.request_type == op.request_type
        assert new_op.method == op.method
        assert new_op.resource_location == op.resource_location
        assert new_op.request_body == op.request_body
        assert new_op.request_id

    @pytest.mark.it("Does not complete the SendIotRequestAndwaitForResponse op")
    def test_sends_op_and_verifies_no_response(self, stage, op):
        stage.run_op(op)
        assert op.callback.call_count == 0

    @pytest.mark.it("Fails SendIotRequestAndWaitForResponseOperation if there is no next stage")
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
        "Fails SendIotRequestAndWaitForResponseOperation if an Exception is raised in the SendIotRequestOperation op"
    )
    def test_new_op_raises_exception(self, stage, op, mocker):
        stage.next._run_op = mocker.Mock(side_effect=Exception)
        stage.run_op(op)
        assert_callback_failed(op=op)

    @pytest.mark.it("Allows BaseExceptions rised on the SendIotRequestOperation op to propogate")
    def test_new_op_raises_base_exception(self, stage, op, mocker):
        stage.next._run_op = mocker.Mock(side_effect=UnhandledException)
        with pytest.raises(UnhandledException):
            stage.run_op(op)
        assert op.callback.call_count == 0


@pytest.mark.describe(
    "CoordinateRequestAndResponseStage - .handle_pipeline_event() -- called with IotResponseEvent"
)
class TestCoordinateRequestAndResponseSendIotRequestHandleEvent(object):
    @pytest.fixture
    def op(self, mocker):
        return make_fake_request_and_response(mocker)

    @pytest.fixture
    def stage(self, mocker):
        return make_mock_stage(mocker, pipeline_stages_base.CoordinateRequestAndResponseStage)

    @pytest.fixture
    def iot_request(self, stage, op):
        stage.run_op(op)
        return stage.next.run_op.call_args[0][0]

    @pytest.fixture
    def iot_response(self, stage, iot_request):
        return pipeline_events_base.IotResponseEvent(
            request_id=iot_request.request_id,
            status_code=fake_status_code,
            response_body=fake_response_body,
        )

    @pytest.mark.it(
        "Completes the SendIotRequestAndWaitForResponseOperation op with the matching request_id including response_body and status_code"
    )
    def test_completes_op_with_matching_request_id(self, stage, op, iot_response):
        operation_flow.pass_event_to_previous_stage(stage.next, iot_response)
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
        operation_flow.pass_event_to_previous_stage(stage.next, iot_response)
        assert unhandled_error_handler.call_count == 1

    @pytest.mark.it(
        "Does nothing if an IotResponse with an identical request_id is received a second time"
    )
    def test_ignores_duplicate_request_id(self, stage, op, iot_response, unhandled_error_handler):
        operation_flow.pass_event_to_previous_stage(stage.next, iot_response)
        assert_callback_succeeded(op=op)
        op.callback.reset_mock()

        operation_flow.pass_event_to_previous_stage(stage.next, iot_response)
        assert op.callback.call_count == 0
        assert unhandled_error_handler.call_count == 0

    @pytest.mark.it(
        "Does nothing if an IotResponse with a request_id is received for an operation that returned failure"
    )
    def test_ignores_request_id_from_failure(self, stage, op, mocker, unhandled_error_handler):
        stage.next._run_op = mocker.MagicMock(side_effect=Exception)
        stage.run_op(op)

        req = stage.next.run_op.call_args[0][0]
        resp = pipeline_events_base.IotResponseEvent(
            request_id=req.request_id,
            status_code=fake_status_code,
            response_body=fake_response_body,
        )

        op.callback.reset_mock()
        operation_flow.pass_event_to_previous_stage(stage.next, resp)
        assert op.callback.call_count == 0
        assert unhandled_error_handler.call_count == 0

    @pytest.mark.it("Does nothing if an IotResponse with an unknown request_id is received")
    def test_ignores_unknown_request_id(self, stage, op, iot_response, unhandled_error_handler):
        iot_response.request_id = fake_request_id
        operation_flow.pass_event_to_previous_stage(stage.next, iot_response)
        assert op.callback.call_count == 0
        assert unhandled_error_handler.call_count == 0
