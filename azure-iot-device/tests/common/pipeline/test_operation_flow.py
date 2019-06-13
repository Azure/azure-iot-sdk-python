# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import logging
import pytest
from azure.iot.device.common.pipeline import (
    pipeline_stages_base,
    pipeline_ops_base,
    pipeline_events_base,
)
from azure.iot.device.common.pipeline.operation_flow import (
    run_ops_in_serial,
    delegate_to_different_op,
    complete_op,
    pass_op_to_next_stage,
)
from tests.common.pipeline.helpers import (
    make_mock_stage,
    assert_callback_failed,
    assert_callback_succeeded,
    UnhandledException,
)

logging.basicConfig(level=logging.INFO)


class MockPipelineStage(pipeline_stages_base.PipelineStage):
    def _run_op(self, op):
        pass_op_to_next_stage(self, op)


@pytest.fixture
def stage(mocker):
    return make_mock_stage(mocker, MockPipelineStage)


@pytest.mark.describe("run_ops_in_serial()")
class TestRunOpsSerial(object):
    @pytest.mark.it("Accepts a list of operators and a callback")
    def test_accepts_default_args(self, stage, op, op2, callback):
        run_ops_in_serial(stage, op, op2, callback=callback)

    @pytest.mark.it("Accepts finally_op as an optional keyword args")
    def test_accepts_finally_op(self, stage, op, op2, finally_op, callback):
        run_ops_in_serial(stage, op, op2, callback=callback, finally_op=finally_op)

    @pytest.mark.it("Throws TypeError for any keyword args besides finally_op and callback")
    def test_throws_for_unknown_keyword_args(self, stage, op, op2, op3, callback):
        with pytest.raises(TypeError):
            run_ops_in_serial(stage, op, op2, callback=callback, unknown_arg=op3)

    @pytest.mark.it("Requires the callback arg")
    def test_throws_on_missing_callback(self, stage, op, op2):
        with pytest.raises(TypeError):
            run_ops_in_serial(stage, op, op2)


@pytest.mark.describe("run_ops_in_serial() -- called with one op and no finally_op")
class TestRunOpsSerialOneOpButNoFinallyOp(object):
    @pytest.mark.it("Runs the op")
    def test_runs_operation(self, mocker, stage, callback, op):
        run_ops_in_serial(stage, op, callback=callback)
        assert stage.next._run_op.call_count == 1
        assert stage.next._run_op.call_args == mocker.call(op)

    @pytest.mark.it("Calls the callback with no error if the op succeeds")
    def test_successful_operation(self, stage, callback, op):
        run_ops_in_serial(stage, op, callback=callback)
        assert_callback_succeeded(op=op, callback=callback)

    @pytest.mark.it("Calls the callback with the op error if the op fails")
    def test_failed_operation(self, stage, callback, op):
        op.action = "fail"
        run_ops_in_serial(stage, op, callback=callback)
        assert_callback_failed(op=op, callback=callback)

    @pytest.mark.it(
        "Handles Exceptions raised in the callback and passes them to the unhandled error handler"
    )
    def test_callback_throws_exception(self, stage, mocker, fake_exception, op):
        callback = mocker.Mock(side_effect=fake_exception)
        run_ops_in_serial(stage, op, callback=callback)
        assert callback.call_count == 1
        assert callback.call_args == mocker.call(op)
        assert stage.unhandled_error_handler.call_count == 1
        assert stage.unhandled_error_handler.call_args == mocker.call(fake_exception)

    @pytest.mark.it("Allows any BaseExceptions raised in the callback to propagate")
    def test_callback_throws_base_exception(self, stage, mocker, fake_base_exception, op):
        callback = mocker.Mock(side_effect=fake_base_exception)
        with pytest.raises(UnhandledException):
            run_ops_in_serial(stage, op, callback=callback)


@pytest.mark.describe("run_ops_in_serial() -- called with one op and finally_op")
class TestRunOpsSerialOneOpAndFinallyOp(object):
    @pytest.mark.it("Runs the first op")
    def test_runs_first_op(self, mocker, stage, callback, op, finally_op):
        run_ops_in_serial(stage, op, finally_op=finally_op, callback=callback)
        assert stage.next._run_op.call_args_list[0] == mocker.call(op)

    @pytest.mark.it("Runs finally_op if the op succeeds")
    def test_runs_finally_op_on_success(self, mocker, stage, callback, op, finally_op):
        run_ops_in_serial(stage, op, finally_op=finally_op, callback=callback)
        assert stage.next._run_op.call_args_list[1] == mocker.call(finally_op)

    @pytest.mark.it("Runs finally_op if the op fails")
    def test_runs_finally_op_on_op_failure(self, mocker, stage, callback, op, finally_op):
        op.action = "fail"
        run_ops_in_serial(stage, op, finally_op=finally_op, callback=callback)
        assert stage.next._run_op.call_args_list[1] == mocker.call(finally_op)

    @pytest.mark.it(
        "Calls the callback with the finally_op error if op succeeds and finally_op fails"
    )
    def test_calls_callback_with_error_if_op_succeeds_and_finally_op_fails(
        self, stage, callback, op, finally_op
    ):
        finally_op.action = "fail"
        run_ops_in_serial(stage, op, finally_op=finally_op, callback=callback)
        assert_callback_failed(callback=callback, op=finally_op, error=finally_op.error)

    @pytest.mark.it("Calls the callback with no error if op succeeds and finally_op succeeds")
    def test_callback_with_success_if_op_and_finally_op_succeed(
        self, stage, callback, op, finally_op
    ):
        run_ops_in_serial(stage, op, finally_op=finally_op, callback=callback)
        assert_callback_succeeded(callback=callback, op=finally_op)

    @pytest.mark.it(
        "Calls the callback with the finally op and the op error if op fails and finally_op also fails"
    )
    def test_callback_with_error_if_op_and_finally_op_both_fail(
        self, stage, callback, op, finally_op
    ):
        op.action = "fail"
        finally_op.action = "fail"
        run_ops_in_serial(stage, op, finally_op=finally_op, callback=callback)
        assert_callback_failed(callback=callback, op=finally_op, error=op.error)

    @pytest.mark.it(
        "Calls the callback with the finally op and the op error if op fails and finally_op succeeds"
    )
    def test_callback_with_error_if_op_fails_and_finally_op_succeeds(
        self, stage, callback, op, finally_op
    ):
        op.action = "fail"
        run_ops_in_serial(stage, op, finally_op=finally_op, callback=callback)
        assert_callback_failed(callback=callback, op=finally_op, error=op.error)

    @pytest.mark.it(
        "Handles Exceptions raised in the callback and passes them to the unhandled error handler"
    )
    def test_callback_raises_exception(self, stage, op, finally_op, fake_exception, mocker):
        callback = mocker.Mock(side_effect=fake_exception)
        run_ops_in_serial(stage, op, finally_op=finally_op, callback=callback)
        assert callback.call_count == 1
        assert callback.call_args == mocker.call(finally_op)
        assert stage.unhandled_error_handler.call_count == 1
        assert stage.unhandled_error_handler.call_args == mocker.call(fake_exception)

    @pytest.mark.it("Allows any BaseExceptions raised in the callback to propagate")
    def test_callback_raises_base_exception(
        self, stage, op, finally_op, fake_base_exception, mocker
    ):
        callback = mocker.Mock(side_effect=fake_base_exception)
        with pytest.raises(UnhandledException):
            run_ops_in_serial(stage, op, finally_op=finally_op, callback=callback)


@pytest.mark.describe("run_ops_in_serial() -- called with multiple ops and no finally_op")
class TestRunOpsSerialThreeOpsButNoFinallyOp(object):
    @pytest.mark.it("Runs the first op")
    def test_runs_first_op(self, mocker, stage, op, op2, op3, callback):
        op.action = "pend"
        run_ops_in_serial(stage, op, op2, op3, callback=callback)
        assert stage.next._run_op.call_count == 1
        assert stage.next._run_op.call_args == mocker.call(op)

    @pytest.mark.it("Does not call the second or third op if the first op fails")
    def test_does_not_call_second_or_third_op_if_first_op_fails(
        self, mocker, stage, op, op2, op3, callback
    ):
        op.action = "fail"
        run_ops_in_serial(stage, op, op2, op3, callback=callback)
        assert stage.next._run_op.call_count == 1
        assert stage.next._run_op.call_args == mocker.call(op)

    @pytest.mark.it("Calls the callback with the first op error if the first op fails")
    def test_calls_callback_when_first_op_fails(self, stage, op, op2, op3, callback):
        op.action = "fail"
        run_ops_in_serial(stage, op, op2, op3, callback=callback)
        assert_callback_failed(callback=callback, op=op)

    @pytest.mark.it(
        "Handles Exceptions raised in the callback and passes them to the unhandled error handler"
    )
    def test_callback_raises_exception(self, stage, op, op2, op3, fake_exception, mocker):
        callback = mocker.Mock(side_effect=fake_exception)
        run_ops_in_serial(stage, op, op2, op3, callback=callback)
        assert callback.call_count == 1
        assert callback.call_args == mocker.call(op3)
        assert stage.unhandled_error_handler.call_count == 1
        assert stage.unhandled_error_handler.call_args == mocker.call(fake_exception)

    @pytest.mark.it("Allows any BaseExceptions raised in the callback to propagate")
    def test_callback_raises_base_exception(self, stage, op, op2, op3, fake_base_exception, mocker):
        callback = mocker.Mock(side_effect=fake_base_exception)
        with pytest.raises(UnhandledException):
            run_ops_in_serial(stage, op, op2, op3, callback=callback)

    @pytest.mark.it("Runs the second op only after the first op succeeds")
    def test_runs_second_op_after_first_op_succceeds(self, mocker, stage, op, op2, op3, callback):
        op.action = "pend"
        op2.action = "pend"
        run_ops_in_serial(stage, op, op2, op3, callback=callback)
        assert stage.next._run_op.call_count == 1
        assert stage.next._run_op.call_args == mocker.call(op)
        complete_op(stage.next, op)
        assert stage.next._run_op.call_count == 2
        assert stage.next._run_op.call_args_list[1] == mocker.call(op2)

    @pytest.mark.it("Does not run the third op after the second op fails")
    def test_does_not_run_third_op_if_second_op_fails(self, mocker, stage, op, op2, op3, callback):
        op2.action = "fail"
        run_ops_in_serial(stage, op, op2, op3, callback=callback)
        assert stage.next._run_op.call_count == 2
        assert stage.next._run_op.call_args_list[0] == mocker.call(op)
        assert stage.next._run_op.call_args_list[1] == mocker.call(op2)

    @pytest.mark.it("Calls the callback with the second op error if the second op fails")
    def test_calls_callback_when_second_op_fails(self, stage, op, op2, op3, callback):
        op2.action = "fail"
        run_ops_in_serial(stage, op, op2, op3, callback=callback)
        assert_callback_failed(callback=callback, op=op2)

    @pytest.mark.it("Calls the third op only after the second op succeeds")
    def test_calls_third_op_after_second_op_succeeds(self, mocker, stage, op, op2, op3, callback):
        op2.action = "pend"
        run_ops_in_serial(stage, op, op2, op3, callback=callback)
        assert stage.next._run_op.call_count == 2
        assert stage.next._run_op.call_args_list[0] == mocker.call(op)
        assert stage.next._run_op.call_args_list[1] == mocker.call(op2)
        complete_op(stage.next, op2)
        assert stage.next._run_op.call_count == 3
        assert stage.next._run_op.call_args_list[2] == mocker.call(op3)

    @pytest.mark.it("Calls the callback with success if the third op succeeds")
    def test_calls_callback_with_third_op_succeeds(self, stage, op, op2, op3, callback):
        run_ops_in_serial(stage, op, op2, op3, callback=callback)
        assert_callback_succeeded(callback=callback, op=op3)

    @pytest.mark.it("Calls the callback with the third op error if the third op fails")
    def test_calls_callback_when_third_op_fails(self, stage, op, op2, op3, callback):
        op3.action = "fail"
        run_ops_in_serial(stage, op, op2, op3, callback=callback)
        assert_callback_failed(callback=callback, op=op3)


@pytest.mark.describe("run_ops_in_serial() -- called with multiple ops and no finally_op")
class TestRunOpsSerialThreeOpsAndFinallyOp(object):
    @pytest.mark.it("Runs the first op")
    def test_runs_first_op(self, mocker, stage, op, op2, op3, finally_op, callback):
        op.action = "pend"
        run_ops_in_serial(stage, op, op2, op3, finally_op=finally_op, callback=callback)
        assert stage.next._run_op.call_count == 1
        assert stage.next._run_op.call_args == mocker.call(op)

    @pytest.mark.it(
        "Does not call the second or third op, bue does call the fanally_op if the first op fails"
    )
    def test_runs_finally_op_if_first_op_fails(
        self, mocker, stage, op, op2, op3, finally_op, callback
    ):
        op.action = "fail"
        run_ops_in_serial(stage, op, op2, op3, finally_op=finally_op, callback=callback)
        assert stage.next._run_op.call_count == 2
        assert stage.next._run_op.call_args_list[0] == mocker.call(op)
        assert stage.next._run_op.call_args_list[1] == mocker.call(finally_op)

    @pytest.mark.it(
        "Calls the callback with the finally_op and the first_op error if the first op fails and finally_op succeeds"
    )
    def test_calls_callback_with_error_when_first_op_fails_and_finally_op_succeeds(
        self, stage, op, op2, op3, finally_op, callback
    ):
        op.action = "fail"
        run_ops_in_serial(stage, op, op2, op3, finally_op=finally_op, callback=callback)
        assert_callback_failed(callback=callback, op=finally_op, error=op.error)

    @pytest.mark.it(
        "Calls the callback with the finally_op and the first_op error if the first op fails and finally_op also fails"
    )
    def test_calls_callbacK_with_error_when_first_op_and_finally_op_both_fail(
        self, stage, op, op2, op3, finally_op, callback
    ):
        op.action = "fail"
        finally_op.action = "fail"
        run_ops_in_serial(stage, op, op2, op3, finally_op=finally_op, callback=callback)
        assert_callback_failed(callback=callback, op=finally_op, error=finally_op.error)

    @pytest.mark.it(
        "Handles Exceptions raised in the callback and passes them to the unhandled error handler"
    )
    def test_callback_raises_exception(
        self, stage, op, op2, op3, finally_op, fake_exception, mocker
    ):
        callback = mocker.Mock(side_effect=fake_exception)
        run_ops_in_serial(stage, op, op2, op3, callback=callback, finally_op=finally_op)
        assert stage.unhandled_error_handler.call_count == 1
        assert stage.unhandled_error_handler.call_args == mocker.call(fake_exception)

    @pytest.mark.it("Allows any BaseExceptions raised in the callback to propagate")
    def test_callback_raises_base_exception(
        self, stage, op, op2, op3, finally_op, fake_base_exception, mocker
    ):
        callback = mocker.Mock(side_effect=fake_base_exception)
        with pytest.raises(UnhandledException):
            run_ops_in_serial(stage, op, op2, op3, callback=callback, finally_op=finally_op)

    @pytest.mark.it("Runs the second op only after the first op succeeds")
    def test_runs_second_op(self, mocker, stage, op, op2, op3, finally_op, callback):
        op.action = "pend"
        op2.action = "pend"
        run_ops_in_serial(stage, op, op2, op3, callback=callback, finally_op=finally_op)
        assert stage.next._run_op.call_count == 1
        assert stage.next._run_op.call_args == mocker.call(op)
        complete_op(stage.next, op)
        assert stage.next._run_op.call_args_list[1] == mocker.call(op2)

    @pytest.mark.it("Does not run the third op but does run finally_op if the second op fails")
    def test_runs_finally_op_when_second_op_fails(
        self, mocker, stage, op, op2, op3, finally_op, callback
    ):
        op2.action = "fail"
        run_ops_in_serial(stage, op, op2, op3, callback=callback, finally_op=finally_op)
        assert stage.next._run_op.call_count == 3
        assert stage.next._run_op.call_args_list[0] == mocker.call(op)
        assert stage.next._run_op.call_args_list[1] == mocker.call(op2)
        assert stage.next._run_op.call_args_list[2] == mocker.call(finally_op)

    @pytest.mark.it(
        "Calls the callback with the finally_op and the  second_op error if the second op fails and finally_op succeeds"
    )
    def test_calls_callback_with_error_when_second_op_fails_and_finally_op_succeeds(
        self, stage, op, op2, op3, finally_op, callback
    ):
        op2.action = "fail"
        run_ops_in_serial(stage, op, op2, op3, finally_op=finally_op, callback=callback)
        assert_callback_failed(callback=callback, op=finally_op, error=op.error)

    @pytest.mark.it(
        "Calls the callback with the finally_op and the second_op error if the second op fails and finally_op also fails"
    )
    def test_calls_callback_with_error_when_second_op_and_finally_op_both_fail(
        self, stage, op, op2, op3, finally_op, callback
    ):
        op2.action = "fail"
        finally_op.action = "fail"
        run_ops_in_serial(stage, op, op2, op3, finally_op=finally_op, callback=callback)
        assert_callback_failed(callback=callback, op=finally_op, error=finally_op.error)
        pass

    @pytest.mark.it("Runs the third op only after the second op succeeds")
    def test_runs_third_op_after_second_op_succeeds(
        self, mocker, stage, op, op2, op3, finally_op, callback
    ):
        op2.action = "pend"
        run_ops_in_serial(stage, op, op2, op3, callback=callback, finally_op=finally_op)
        assert stage.next._run_op.call_count == 2
        assert stage.next._run_op.call_args_list[0] == mocker.call(op)
        assert stage.next._run_op.call_args_list[1] == mocker.call(op2)
        complete_op(stage.next, op2)
        assert stage.next._run_op.call_count == 4
        assert stage.next._run_op.call_args_list[2] == mocker.call(op3)
        assert stage.next._run_op.call_args_list[3] == mocker.call(finally_op)

    @pytest.mark.it("Runs finally_op if the third op fails")
    def test_runs_finally_op_if_third_op_fails(
        self, mocker, stage, op, op2, op3, finally_op, callback
    ):
        op3.action = "fail"
        run_ops_in_serial(stage, op, op2, op3, callback=callback, finally_op=finally_op)
        assert stage.next._run_op.call_count == 4
        assert stage.next._run_op.call_args_list[3] == mocker.call(finally_op)

    @pytest.mark.it("Runs finally_op if the third op succeeds")
    def test_runs_finally_op_if_third_op_succeeds(
        self, mocker, stage, op, op2, op3, finally_op, callback
    ):
        run_ops_in_serial(stage, op, op2, op3, callback=callback, finally_op=finally_op)
        assert stage.next._run_op.call_count == 4
        assert stage.next._run_op.call_args_list[3] == mocker.call(finally_op)

    @pytest.mark.it(
        "Calls the callback with the finally_op if the third op succeeds and finally_op also succeeds"
    )
    def test_calls_callback_with_no_error_if_third_op_and_finally_op_both_succeed(
        self, stage, op, op2, op3, finally_op, callback
    ):
        run_ops_in_serial(stage, op, op2, op3, callback=callback, finally_op=finally_op)
        assert_callback_succeeded(callback=callback, op=finally_op)

    @pytest.mark.it(
        "Calls the callback with the finally_op if the third op succeeds and finally_op fails"
    )
    def test_calls_callback_with_error_if_third_op_succeeds_and_finally_op_fails(
        self, stage, op, op2, op3, finally_op, callback
    ):
        finally_op.action = "fail"
        run_ops_in_serial(stage, op, op2, op3, callback=callback, finally_op=finally_op)
        assert_callback_failed(callback=callback, op=finally_op, error=finally_op.error)

    @pytest.mark.it(
        "Calls the callback with the finally_op and the third_op error if the third op fails and finally_op succeeds"
    )
    def test_calls_callback_with_error_if_the_third_op_fails_and_finally_op_succeeds(
        self, stage, op, op2, op3, finally_op, callback
    ):
        op3.action = "fail"
        run_ops_in_serial(stage, op, op2, op3, callback=callback, finally_op=finally_op)
        assert_callback_failed(callback=callback, op=finally_op, error=op3.error)

    @pytest.mark.it(
        "Calls the callback with the finally_op and the  third op error if the third op fails and finally_op also fails"
    )
    def test_calls_callback_with_error_if_third_op_and_finally_op_both_fail(
        self, stage, op, op2, op3, finally_op, callback
    ):
        op3.action = "fail"
        finally_op.action = "fail"
        run_ops_in_serial(stage, op, op2, op3, callback=callback, finally_op=finally_op)
        assert_callback_failed(callback=callback, op=finally_op, error=op3.error)


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
    def test_completes_op_with_error(self, mocker, stage, op, fake_exception, callback):
        op.error = fake_exception
        op.callback = callback
        pass_op_to_next_stage(stage, op)
        assert_callback_failed(op=op, error=fake_exception)
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
    def test_calls_callback_on_error(self, stage, op, callback, fake_exception):
        op.error = fake_exception
        op.callback = callback
        complete_op(stage, op)
        assert_callback_failed(op=op, error=fake_exception)

    @pytest.mark.it(
        "Handles Exceptions raised in operation callback and passes them to the unhandled error handler"
    )
    def test_op_callback_raises_exception(self, stage, op, fake_exception, mocker):
        op.callback = mocker.Mock(side_effect=fake_exception)
        complete_op(stage, op)
        assert op.callback.call_count == 1
        assert op.callback.call_args == mocker.call(op)
        assert stage.unhandled_error_handler.call_count == 1
        assert stage.unhandled_error_handler.call_args == mocker.call(fake_exception)

    @pytest.mark.it("Allows any BaseExceptions raised in operation callback to propagate")
    def test_op_callback_raises_base_exception(self, stage, op, fake_base_exception, mocker):
        op.callback = mocker.Mock(side_effect=fake_base_exception)
        with pytest.raises(UnhandledException):
            complete_op(stage, op)
