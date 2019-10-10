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
        self._send_op_down(op)


@pytest.fixture
def stage(mocker, arbitrary_exception, arbitrary_base_exception):
    return make_mock_stage(
        mocker=mocker,
        stage_to_make=MockPipelineStage,
        exc_to_raise=arbitrary_exception,
        base_exc_to_raise=arbitrary_base_exception,
    )


@pytest.mark.describe("_send_worker_op_down()")
class TestContineWithDifferntOp(object):
    @pytest.mark.it("Runs the new op and does not continue running the original op")
    def test_runs_new_op(self, mocker, stage, op, new_op):
        stage._send_worker_op_down(worker_op=new_op, op=op)
        assert stage.next.run_op.call_count == 1
        assert stage.next.run_op.call_args == mocker.call(new_op)

    @pytest.mark.it("Completes the original op after the new op completes")
    def test_completes_original_op_after_new_op_completes(self, stage, op, new_op, callback):
        op.callback = callback
        new_op.action = "pend"

        stage._send_worker_op_down(worker_op=new_op, op=op)
        assert callback.call_count == 0  # because new_op is pending

        stage.next._complete_op(new_op)
        assert_callback_succeeded(op=op)

    @pytest.mark.it("Returns the new op failure in the original op if new op fails")
    def test_returns_new_op_failure_in_original_op(self, stage, op, new_op, callback):
        op.callback = callback
        new_op.action = "fail"
        stage._send_worker_op_down(worker_op=new_op, op=op)
        assert_callback_failed(op)


@pytest.mark.describe("_send_op_down()")
class TestContinueOp(object):
    @pytest.mark.it("Fails the op if there is no next stage")
    def test_fails_op_when_no_next_stage(self, stage, op, callback):
        op.callback = callback
        stage.next = None
        stage._send_op_down(op)
        assert_callback_failed(op=op)

    @pytest.mark.it("Passes the op to the next stage")
    def test_passes_op_to_next_stage(self, mocker, stage, op, callback):
        stage._send_op_down(op)
        assert stage.next.run_op.call_count == 1
        assert stage.next.run_op.call_args == mocker.call(op)


@pytest.mark.describe("_complete_op()")
class TestCompleteOp(object):
    @pytest.mark.it("Calls the op callback on success")
    def test_calls_callback_on_success(self, stage, op, callback):
        op.callback = callback
        stage._complete_op(op)
        assert_callback_succeeded(op)

    @pytest.mark.it("Calls the op callback on failure")
    def test_calls_callback_on_error(self, stage, op, callback, arbitrary_exception):
        op.callback = callback
        stage._complete_op(op, error=arbitrary_exception)
        assert_callback_failed(op=op, error=arbitrary_exception)

    @pytest.mark.it(
        "Handles Exceptions raised in operation callback and passes them to the unhandled error handler"
    )
    def test_op_callback_raises_exception(
        self, stage, op, arbitrary_exception, mocker, unhandled_error_handler
    ):
        op.callback = mocker.Mock(side_effect=arbitrary_exception)
        stage._complete_op(op)
        assert op.callback.call_count == 1
        assert op.callback.call_args == mocker.call(op, error=None)
        assert unhandled_error_handler.call_count == 1
        assert unhandled_error_handler.call_args == mocker.call(arbitrary_exception)

    @pytest.mark.it("Allows any BaseExceptions raised in operation callback to propagate")
    def test_op_callback_raises_base_exception(self, stage, op, arbitrary_base_exception, mocker):
        op.callback = mocker.Mock(side_effect=arbitrary_base_exception)
        with pytest.raises(arbitrary_base_exception.__class__):
            stage._complete_op(op)
