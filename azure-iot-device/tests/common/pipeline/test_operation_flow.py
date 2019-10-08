# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import logging
import pytest
from azure.iot.device.common.pipeline import (
    pipeline_thread,
    pipeline_stages_base,
    pipeline_ops_base,
    pipeline_events_base,
)
from azure.iot.device.common.pipeline.operation_flow import (
    delegate_to_different_op,
    complete_op,
    pass_op_to_next_stage,
)
from tests.common.pipeline.helpers import (
    make_mock_stage,
    assert_callback_failed,
    assert_callback_succeeded,
)

logging.basicConfig(level=logging.DEBUG)


# This fixture makes it look like all test in this file  tests are running
# inside the pipeline thread.  Because this is an autouse fixture, we
# manually add it to the individual test.py files that need it.  If,
# instead, we had added it to some conftest.py, it would be applied to
# every tests in every file and we don't want that.
@pytest.fixture(autouse=True)
def apply_fake_pipeline_thread(fake_pipeline_thread):
    pass


class MockPipelineStage(pipeline_stages_base.PipelineStage):
    def _execute_op(self, op):
        pass_op_to_next_stage(self, op)


@pytest.fixture
def stage(mocker, arbitrary_exception, arbitrary_base_exception):
    return make_mock_stage(
        mocker=mocker,
        stage_to_make=MockPipelineStage,
        exc_to_raise=arbitrary_exception,
        base_exc_to_raise=arbitrary_base_exception,
    )


@pytest.mark.describe("delegate_to_different_op()")
class TestContineWithDifferntOp(object):
    @pytest.mark.it("Runs the new op and does not continue running the original op")
    def test_runs_new_op(self, mocker, stage, op, new_op):
        delegate_to_different_op(stage, original_op=op, new_op=new_op)
        assert stage.next.run_op.call_count == 1
        assert stage.next.run_op.call_args == mocker.call(new_op)

    @pytest.mark.it("Completes the original op after the new op completes")
    def test_completes_original_op_after_new_op_completes(self, stage, op, new_op, callback):
        op.callback = callback
        new_op.action = "pend"

        delegate_to_different_op(stage, original_op=op, new_op=new_op)
        assert callback.call_count == 0  # because new_op is pending

        complete_op(stage.next, new_op)
        assert_callback_succeeded(op=op)

    @pytest.mark.it("Returns the new op failure in the original op if new op fails")
    def test_returns_new_op_failure_in_original_op(self, stage, op, new_op, callback):
        op.callback = callback
        new_op.action = "fail"
        delegate_to_different_op(stage, original_op=op, new_op=new_op)
        assert_callback_failed(op=op, error=new_op.error)


@pytest.mark.describe("pass_op_to_next_stage()")
class TestContinueOp(object):
    @pytest.mark.it("Completes the op without continuing if the op has an error")
    def test_completes_op_with_error(self, mocker, stage, op, arbitrary_exception, callback):
        op.error = arbitrary_exception
        op.callback = callback
        pass_op_to_next_stage(stage, op)
        assert_callback_failed(op=op, error=arbitrary_exception)
        assert stage.next.run_op.call_count == 0

    @pytest.mark.it("Fails the op if there is no next stage")
    def test_fails_op_when_no_next_stage(self, stage, op, callback):
        op.callback = callback
        stage.next = None
        pass_op_to_next_stage(stage, op)
        assert_callback_failed(op=op)
        pass

    @pytest.mark.it("Passes the op to the next stage")
    def test_passes_op_to_next_stage(self, mocker, stage, op, callback):
        pass_op_to_next_stage(stage, op)
        assert stage.next.run_op.call_count == 1
        assert stage.next.run_op.call_args == mocker.call(op)


@pytest.mark.describe("complete_op()")
class TestCompleteOp(object):
    @pytest.mark.it("Calls the op callback on success")
    def test_calls_callback_on_success(self, stage, op, callback):
        op.callback = callback
        complete_op(stage, op)
        assert_callback_succeeded(op)

    @pytest.mark.it("Calls the op callback on failure")
    def test_calls_callback_on_error(self, stage, op, callback, arbitrary_exception):
        op.error = arbitrary_exception
        op.callback = callback
        complete_op(stage, op)
        assert_callback_failed(op=op, error=arbitrary_exception)

    @pytest.mark.it(
        "Handles Exceptions raised in operation callback and passes them to the unhandled error handler"
    )
    def test_op_callback_raises_exception(
        self, stage, op, arbitrary_exception, mocker, unhandled_error_handler
    ):
        op.callback = mocker.Mock(side_effect=arbitrary_exception)
        complete_op(stage, op)
        assert op.callback.call_count == 1
        assert op.callback.call_args == mocker.call(op)
        assert unhandled_error_handler.call_count == 1
        assert unhandled_error_handler.call_args == mocker.call(arbitrary_exception)

    @pytest.mark.it("Allows any BaseExceptions raised in operation callback to propagate")
    def test_op_callback_raises_base_exception(self, stage, op, arbitrary_base_exception, mocker):
        op.callback = mocker.Mock(side_effect=arbitrary_base_exception)
        with pytest.raises(arbitrary_base_exception.__class__):
            complete_op(stage, op)
