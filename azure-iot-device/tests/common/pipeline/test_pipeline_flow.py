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
    pipeline_exceptions,
)
from azure.iot.device.common import handle_exceptions
from tests.common.pipeline.helpers import (
    make_mock_stage,
    assert_callback_failed,
    assert_callback_succeeded,
)
from .fixtures import FakeOperation

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


@pytest.mark.describe("PipelineFlow - ._send_worker_op_down()")
class TestSendWorkerOpDown(object):
    @pytest.fixture
    def arbitrary_worker_op(self, mocker):
        op = FakeOperation(callback=mocker.MagicMock())
        op.name = "arbitrary_worker_op"
        return op

    @pytest.mark.it("Runs the worker op and does not continue running the original op")
    def test_runs_worker_op(self, mocker, stage, arbitrary_op, arbitrary_worker_op):
        stage._send_worker_op_down(worker_op=arbitrary_worker_op, op=arbitrary_op)
        assert stage.next.run_op.call_count == 1
        assert stage.next.run_op.call_args == mocker.call(arbitrary_worker_op)

    @pytest.mark.it("Completes the original op after the worker op completes")
    def test_completes_original_op_after_worker_op_completes(
        self, stage, arbitrary_op, arbitrary_worker_op
    ):
        callback = arbitrary_op.callback
        arbitrary_worker_op.action = "pend"

        stage._send_worker_op_down(worker_op=arbitrary_worker_op, op=arbitrary_op)
        assert callback.call_count == 0  # because arbitrary_worker_op is pending

        stage.next._complete_op(arbitrary_worker_op)
        assert_callback_succeeded(op=arbitrary_op)

    @pytest.mark.it("Returns the worker op failure in the original op if worker op fails")
    def test_returns_worker_op_failure_in_original_op(
        self, stage, arbitrary_op, arbitrary_worker_op, arbitrary_exception
    ):
        arbitrary_worker_op.action = "fail"
        stage._send_worker_op_down(worker_op=arbitrary_worker_op, op=arbitrary_op)
        assert_callback_failed(arbitrary_op, error=arbitrary_exception)


@pytest.mark.describe("PipelineFlow - ._send_op_down()")
class TestSendOpDown(object):
    @pytest.mark.it("Fails the op if there is no next stage")
    def test_fails_op_when_no_next_stage(self, stage, arbitrary_op):
        stage.next = None
        stage._send_op_down(arbitrary_op)
        assert_callback_failed(op=arbitrary_op, error=pipeline_exceptions.PipelineError)

    @pytest.mark.it("Passes the op to the next stage")
    def test_passes_op_to_next_stage(self, mocker, stage, arbitrary_op):
        stage._send_op_down(arbitrary_op)
        assert stage.next.run_op.call_count == 1
        assert stage.next.run_op.call_args == mocker.call(arbitrary_op)


@pytest.mark.describe("PipelineFlow - ._complete_op()")
class TestCompleteOp(object):
    @pytest.mark.it("Calls the op callback on success")
    def test_calls_callback_on_success(self, stage, arbitrary_op):
        stage._complete_op(arbitrary_op)
        assert_callback_succeeded(arbitrary_op)

    @pytest.mark.it("Calls the op callback on failure")
    def test_calls_callback_on_error(self, stage, arbitrary_op, arbitrary_exception):
        stage._complete_op(arbitrary_op, error=arbitrary_exception)
        assert_callback_failed(op=arbitrary_op, error=arbitrary_exception)

    @pytest.mark.it(
        "Calls handle_background_exception with a PipelineError if the op has previously been completed"
    )
    def test_background_exception_if_called_twice(self, stage, arbitrary_op, mocker):
        mocker.spy(handle_exceptions, "handle_background_exception")
        stage._complete_op(arbitrary_op)
        stage._complete_op(arbitrary_op)
        assert handle_exceptions.handle_background_exception.call_count == 1
        assert (
            handle_exceptions.handle_background_exception.call_args[0][0].__class__
            == pipeline_exceptions.PipelineError
        )

    @pytest.mark.it("Does not call the callback if the op has previously been completed")
    def test_no_callback_if_called_twice(self, stage, arbitrary_op):
        stage._complete_op(arbitrary_op)
        arbitrary_op.callback.reset_mock()
        stage._complete_op(arbitrary_op)
        assert arbitrary_op.callback.call_count == 0

    @pytest.mark.it(
        "Handles Exceptions raised in operation callback and passes them to the unhandled error handler"
    )
    def test_op_callback_raises_exception(
        self, stage, arbitrary_op, arbitrary_exception, mocker, unhandled_error_handler
    ):
        arbitrary_op.callback = mocker.Mock(side_effect=arbitrary_exception)
        stage._complete_op(arbitrary_op)
        assert arbitrary_op.callback.call_count == 1
        assert arbitrary_op.callback.call_args == mocker.call(arbitrary_op, error=None)
        assert unhandled_error_handler.call_count == 1
        assert unhandled_error_handler.call_args == mocker.call(arbitrary_exception)

    @pytest.mark.it("Allows any BaseExceptions raised in operation callback to propagate")
    def test_op_callback_raises_base_exception(
        self, stage, arbitrary_op, arbitrary_base_exception, mocker
    ):
        arbitrary_op.callback = mocker.Mock(side_effect=arbitrary_base_exception)
        with pytest.raises(arbitrary_base_exception.__class__):
            stage._complete_op(arbitrary_op)


@pytest.mark.describe("PipelineFlow - ._send_completed_op_up()")
class TestSendCompletedOpUp(object):
    @pytest.mark.it("Calls the op callback on success")
    def test_calls_callback_on_success(self, stage, arbitrary_op):
        arbitrary_op.completed = True
        stage._send_completed_op_up(arbitrary_op)
        assert_callback_succeeded(arbitrary_op)

    @pytest.mark.it("Calls the op callback on failure")
    def test_calls_callback_on_error(self, stage, arbitrary_op, arbitrary_exception):
        arbitrary_op.completed = True
        stage._send_completed_op_up(arbitrary_op, error=arbitrary_exception)
        assert_callback_failed(op=arbitrary_op, error=arbitrary_exception)

    @pytest.mark.it(
        "Calls the callback with a PipelineError if the operation has not been completed"
    )
    def test_error_if_not_completed(self, stage, arbitrary_op):
        with pytest.raises(pipeline_exceptions.PipelineError):
            stage._send_completed_op_up(arbitrary_op)

    @pytest.mark.it(
        "Handles Exceptions raised in operation callback and passes them to the unhandled error handler"
    )
    def test_op_callback_raises_exception(
        self, stage, arbitrary_op, arbitrary_exception, mocker, unhandled_error_handler
    ):
        arbitrary_op.callback = mocker.Mock(side_effect=arbitrary_exception)
        arbitrary_op.completed = True
        stage._send_completed_op_up(arbitrary_op)
        assert arbitrary_op.callback.call_count == 1
        assert arbitrary_op.callback.call_args == mocker.call(arbitrary_op, error=None)
        assert unhandled_error_handler.call_count == 1
        assert unhandled_error_handler.call_args == mocker.call(arbitrary_exception)

    @pytest.mark.it("Allows any BaseExceptions raised in operation callback to propagate")
    def test_op_callback_raises_base_exception(
        self, stage, arbitrary_op, arbitrary_base_exception, mocker
    ):
        arbitrary_op.callback = mocker.Mock(side_effect=arbitrary_base_exception)
        arbitrary_op.completed = True
        with pytest.raises(arbitrary_base_exception.__class__):
            stage._send_completed_op_up(arbitrary_op)


@pytest.mark.describe("PipelineFlow - ._send_op_down_and_intercept_return()")
class TestSendOpDownAndInterceptReturn(object):
    @pytest.mark.it("Calls _send_op_down to send the op down")
    def test_sends_op_down(self, stage, arbitrary_op, mocker):
        intercepted_return = mocker.MagicMock()
        mocker.spy(stage, "_send_op_down")
        stage._send_op_down_and_intercept_return(arbitrary_op, intercepted_return)
        assert stage._send_op_down.call_count == 1
        assert stage._send_op_down.call_args == mocker.call(arbitrary_op)

    @pytest.mark.it("Calls the intercepted_return function when the op succeeds")
    def test_calls_intercepted_return_on_op_success(self, stage, arbitrary_op, mocker):
        intercepted_return = mocker.MagicMock()
        stage._send_op_down_and_intercept_return(arbitrary_op, intercepted_return)
        assert intercepted_return.call_args == mocker.call(op=arbitrary_op, error=None)

    @pytest.mark.it("Calls the intercepted_return function when the op fails")
    def test_calls_intercepted_return_on_op_failure(
        self, stage, arbitrary_op, mocker, arbitrary_exception
    ):
        arbitrary_op.action = "fail"
        intercepted_return = mocker.MagicMock()
        stage._send_op_down_and_intercept_return(arbitrary_op, intercepted_return)
        assert intercepted_return.call_args == mocker.call(
            op=arbitrary_op, error=arbitrary_exception
        )

    @pytest.mark.it(
        "Ensures that the op callback is set to its original value when the intercepted_return function is called"
    )
    def test_restores_callback_before_calling_intercepted_return(self, stage, arbitrary_op, mocker):
        saved_callback = arbitrary_op.callback
        intercepted_return = mocker.MagicMock()
        stage._send_op_down_and_intercept_return(arbitrary_op, intercepted_return)
        assert intercepted_return.call_args[1]["op"].callback == saved_callback


@pytest.mark.describe("PipelineFlow - ._send_event_up()")
class TestSendEventUp(object):
    @pytest.mark.it("Calls handle_pipeline_event on the previous stage")
    def test_calls_handle_pipeline_event(self, stage, arbitrary_event, mocker):
        mocker.spy(stage, "handle_pipeline_event")
        stage.next._send_event_up(arbitrary_event)
        assert stage.handle_pipeline_event.call_count == 1
        assert stage.handle_pipeline_event.call_args == mocker.call(arbitrary_event)

    @pytest.mark.it(
        "Calls handle_background_exception with a PipelineError if there is no previous stage"
    )
    def test_no_previous_stage(self, stage, arbitrary_event, mocker):
        mocker.spy(handle_exceptions, "handle_background_exception")
        stage._send_event_up(arbitrary_event)
        assert handle_exceptions.handle_background_exception.call_count == 1
        assert (
            handle_exceptions.handle_background_exception.call_args[0][0].__class__
            == pipeline_exceptions.PipelineError
        )
