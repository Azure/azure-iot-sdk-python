# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import logging
import pytest
import functools
from azure.iot.device.common.transport import pipeline_stages_base
from azure.iot.device.common.transport import pipeline_ops_base
from azure.iot.device.common.transport import pipeline_events_base

logging.basicConfig(level=logging.INFO)


def assert_default_attributes(obj):
    assert obj.name is obj.__class__.__name__
    assert obj.next is None
    assert obj.previous is None
    assert obj.pipeline_root is None


# because PipelineStage is abstract, we need something concrete
class PipelineStage(pipeline_stages_base.PipelineStage):
    def _run_op(self, op):
        pass


def Op():
    return pipeline_ops_base.PipelineOperation()


def get_fake_error():
    return BaseException()


@pytest.fixture
def stage(mocker):
    def stage_run_op(self, op):
        if getattr(op, "action", None) is None or op.action == "pass":
            self.complete_op(op)
        elif op.action == "fail":
            raise get_fake_error()
        elif op.action == "pend":
            pass
        else:
            assert False

    first_stage = PipelineStage()
    first_stage.unhandled_error_handler = mocker.Mock()
    first_stage._run_op = functools.partial(stage_run_op, first_stage)
    mocker.spy(first_stage, "_run_op")
    mocker.spy(first_stage, "run_op")

    next_stage = PipelineStage()
    next_stage._run_op = functools.partial(stage_run_op, next_stage)
    mocker.spy(next_stage, "_run_op")
    mocker.spy(next_stage, "run_op")

    first_stage.next = next_stage
    first_stage.pipeline_root = first_stage

    next_stage.previous = first_stage
    next_stage.pipeline_root = first_stage

    return first_stage


@pytest.fixture
def callback(mocker):
    return mocker.Mock()


@pytest.fixture
def op():
    op = Op()
    op.name = "op"
    return op


@pytest.fixture
def op2():
    op = Op()
    op.name = "op2"
    return op


@pytest.fixture
def op3():
    op = Op()
    op.name = "op3"
    return op


@pytest.fixture
def finally_op():
    op = Op()
    op.name = "finally_op"
    return op


@pytest.fixture
def fake_error():
    return get_fake_error()


@pytest.fixture
def event():
    ev = pipeline_events_base.PipelineEvent()
    ev.name = "test event"
    return ev


def assert_callback_succeeded(callback, op):
    callback.assert_called_once_with(op)
    assert op.error is None


def assert_callback_failed(callback, op, error=None):
    callback.assert_called_once_with(op)
    if error:
        assert op.error is error
    else:
        assert op.error is not None


@pytest.mark.describe("PipelineStage initializer")
class TestPipelineStageInitializer(object):
    @pytest.mark.it("Sets required and default arguments correctly")
    def test_initializer(self):
        obj = PipelineStage()
        assert_default_attributes(obj)


@pytest.mark.describe("PipelineStage RunOp function")
class TestPipelineStageRunOp(object):
    @pytest.mark.it("calls _run_op")
    def test_1(self, stage, op):
        stage.run_op(op)
        stage._run_op.assert_called_once_with(op)

    @pytest.mark.it("completes the op correctly if the op throws")
    def test_4(self, stage, callback, op):
        op.action = "fail"
        op.callback = callback
        stage.run_op(op)
        assert_callback_failed(callback, op)


@pytest.mark.describe("PipelineStage run_ops_serial function")
class TestPipelineStageRunOpsSerial(object):
    @pytest.mark.it("accepts default args")
    def test_1(self, stage, callback):
        stage.run_ops_serial(Op(), Op(), callback=callback)

    @pytest.mark.it("accepts known keyword args")
    def test_2(self, stage, callback):
        stage.run_ops_serial(Op(), Op(), callback=callback, finally_op=Op())

    @pytest.mark.it("does not accept unknown keyword args")
    def test_3(self, stage, callback):
        with pytest.raises(TypeError):
            stage.run_ops_serial(Op(), Op(), callback=callback, unknown_arg=Op())

    @pytest.mark.it("requires the callback arg")
    def test_4(self, stage):
        with pytest.raises(TypeError):
            stage.run_ops_serial(Op(), Op())


@pytest.mark.describe("PipelineStage run_ops_serial function with one op and without finally op")
class TestPipelineStageRunOpsSerialOneOpButNoFinallyOp(object):
    @pytest.mark.it("runs the op")
    def test_1(self, stage, callback, op):
        stage.run_ops_serial(op, callback=callback)
        stage.next._run_op.assert_called_once_with(op)

    @pytest.mark.it("calls the callback correctly if the op succeeds")
    def test_2(self, stage, callback, op):
        stage.run_ops_serial(op, callback=callback)
        assert_callback_succeeded(callback, op)

    @pytest.mark.it("calls the callback correctly if the op fails")
    def test_3(self, stage, callback, op):
        op.action = "fail"
        stage.run_ops_serial(op, callback=callback)
        assert_callback_failed(callback, op)

    @pytest.mark.it("protects the callback with a try/except block")
    def test_4(self, stage, mocker, fake_error, op):
        callback = mocker.Mock(side_effect=fake_error)
        stage.run_ops_serial(op, callback=callback)
        callback.assert_called_once_with(op)
        stage.unhandled_error_handler.assert_called_once_with(fake_error)


@pytest.mark.describe("PipelineStage run_ops_serial function with one op and finally op")
class TestPipelineStageRunOpsSerialOneOpAndFinallyOp(object):
    @pytest.mark.it("runs the first op")
    def test_1(self, stage, callback, op, finally_op):
        stage.run_ops_serial(op, finally_op=finally_op, callback=callback)
        stage.next._run_op.assert_any_call(op)

    @pytest.mark.it("runs finally_op if the op succeeds")
    def test_2(self, stage, callback, op, finally_op):
        stage.run_ops_serial(op, finally_op=finally_op, callback=callback)
        stage.next._run_op.assert_any_call(finally_op)

    @pytest.mark.it("runs finally_op if the op fails")
    def test_3(self, stage, callback, op, finally_op):
        op.action = "fail"
        stage.run_ops_serial(op, finally_op=finally_op, callback=callback)
        stage.next._run_op.assert_any_call(finally_op)

    @pytest.mark.it("calls the callback correctly if op succeeds and finally_op fails")
    def test_4(self, stage, callback, op, finally_op):
        finally_op.action = "fail"
        stage.run_ops_serial(op, finally_op=finally_op, callback=callback)
        assert_callback_failed(callback, finally_op, error=finally_op.error)

    @pytest.mark.it("calls the callback correctly if op succeeds and finally_op succeeds")
    def test_5(self, stage, callback, op, finally_op):
        stage.run_ops_serial(op, finally_op=finally_op, callback=callback)
        assert_callback_succeeded(callback, finally_op)

    @pytest.mark.it("calls the callback correctly if op fails and finally_op also fails")
    def test_6(self, stage, callback, op, finally_op):
        op.action = "fail"
        finally_op.action = "fail"
        stage.run_ops_serial(op, finally_op=finally_op, callback=callback)
        assert_callback_failed(callback, finally_op, error=op.error)

    @pytest.mark.it("calls the callback correctly if op fails and finally_op succeeds")
    def test_7(self, stage, callback, op, finally_op):
        op.action = "fail"
        stage.run_ops_serial(op, finally_op=finally_op, callback=callback)
        assert_callback_failed(callback, finally_op, error=op.error)

    @pytest.mark.it("protects the callback with a try/except block")
    def test_8(self, stage, op, finally_op, fake_error, mocker):
        callback = mocker.Mock(side_effect=fake_error)
        stage.run_ops_serial(op, finally_op=finally_op, callback=callback)
        callback.assert_called_once_with(finally_op)
        stage.unhandled_error_handler.assert_called_once_with(fake_error)


@pytest.mark.describe("PipelineStage run_ops_serial function with three ops and without finally op")
class TestPipelineStageRunOpsSerialThreeOpsButNoFinallyOp(object):
    @pytest.mark.it("runs the first op")
    def test_1(self, stage, op, op2, op3, callback):
        op.action = "pend"
        stage.run_ops_serial(op, op2, op3, callback=callback)
        stage.next._run_op.assert_called_once_with(op)

    @pytest.mark.it("does not call the second or third op if the first op fails")
    def test_2(self, stage, op, op2, op3, callback):
        op.action = "fail"
        stage.run_ops_serial(op, op2, op3, callback=callback)
        stage.next._run_op.assert_called_once_with(op)

    @pytest.mark.it("calls the callback correctly if the first op fails")
    def test_3(self, stage, op, op2, op3, callback):
        op.action = "fail"
        stage.run_ops_serial(op, op2, op3, callback=callback)
        assert_callback_failed(callback, op)

    @pytest.mark.it("protects the callback with a try/except block")
    def test_4(self, stage, op, op2, op3, fake_error, mocker):
        callback = mocker.Mock(side_effect=fake_error)
        stage.run_ops_serial(op, op2, op3, callback=callback)
        callback.assert_called_once_with(op3)
        stage.unhandled_error_handler.assert_called_once_with(fake_error)

    @pytest.mark.it("runs the second op only after the first op succeeds")
    def test_7(self, stage, op, op2, op3, callback):
        op.action = "pend"
        op2.action = "pend"
        stage.run_ops_serial(op, op2, op3, callback=callback)
        stage.next._run_op.assert_called_once_with(op)
        stage.next.complete_op(op)
        stage.next._run_op.assert_any_call(op2)

    @pytest.mark.it("does not run the third op after the second op fails")
    def test_8(self, stage, op, op2, op3, callback):
        op2.action = "fail"
        stage.run_ops_serial(op, op2, op3, callback=callback)
        assert stage.next._run_op.call_count == 2
        stage.next._run_op.assert_any_call(op)
        stage.next._run_op.assert_any_call(op2)

    @pytest.mark.it("calls the callback correctly if the second op fails")
    def test_9(self, stage, op, op2, op3, callback):
        op2.action = "fail"
        stage.run_ops_serial(op, op2, op3, callback=callback)
        assert_callback_failed(callback, op2)

    @pytest.mark.it("calls the third op only after the second op succeeds")
    def test_10(self, stage, op, op2, op3, callback):
        op2.action = "pend"
        stage.run_ops_serial(op, op2, op3, callback=callback)
        assert stage.next._run_op.call_count == 2
        stage.next._run_op.assert_any_call(op)
        stage.next._run_op.assert_any_call(op2)
        stage.next.complete_op(op2)
        assert stage.next._run_op.call_count == 3
        stage.next._run_op.assert_any_call(op3)

    @pytest.mark.it("calls the callback correctly if the third op succeeds")
    def test_11(self, stage, op, op2, op3, callback):
        stage.run_ops_serial(op, op2, op3, callback=callback)
        assert_callback_succeeded(callback, op3)

    @pytest.mark.it("calls the callback correctly if the third op fails")
    def test_12(self, stage, op, op2, op3, callback):
        op3.action = "fail"
        stage.run_ops_serial(op, op2, op3, callback=callback)
        assert_callback_failed(callback, op3)


@pytest.mark.describe("PipelineStage run_ops_serial function with three ops and finally op")
class TestPipelineStageRunOpsSerialThreeOpsAndFinallyOp(object):
    @pytest.mark.it("runs the first op")
    def test_1(self, stage, op, op2, op3, finally_op, callback):
        op.action = "pend"
        stage.run_ops_serial(op, op2, op3, finally_op=finally_op, callback=callback)
        stage.next._run_op.assert_called_once_with(op)

    @pytest.mark.it("does not call the second or third op if the first op fails")
    @pytest.mark.it("runs the finally op if the first op fails")
    def test_2(self, stage, op, op2, op3, finally_op, callback):
        op.action = "fail"
        stage.run_ops_serial(op, op2, op3, finally_op=finally_op, callback=callback)
        assert stage.next._run_op.call_count == 2
        stage.next._run_op.assert_any_call(op)
        stage.next._run_op.assert_any_call(finally_op)

    @pytest.mark.it("calls the callback correctly if the first op fails and finally_op succeeds")
    def test_4(self, stage, op, op2, op3, finally_op, callback):
        op.action = "fail"
        stage.run_ops_serial(op, op2, op3, finally_op=finally_op, callback=callback)
        assert_callback_failed(callback, finally_op, error=op.error)

    @pytest.mark.it("calls the callback correctly if the first op fails and finally_op also fails")
    def test_5(self, stage, op, op2, op3, finally_op, callback):
        op.action = "fail"
        finally_op.action = "fail"
        stage.run_ops_serial(op, op2, op3, finally_op=finally_op, callback=callback)
        assert_callback_failed(callback, finally_op, error=finally_op.error)

    @pytest.mark.it("protects the callback with a try/except block")
    def test_6(self, stage, op, op2, op3, finally_op, fake_error, mocker):
        callback = mocker.Mock(side_effect=fake_error)
        stage.run_ops_serial(op, op2, op3, callback=callback, finally_op=finally_op)
        stage.unhandled_error_handler.assert_called_once_with(fake_error)

    @pytest.mark.it("runs the second op only after the first op succeeds")
    def test_9(self, stage, op, op2, op3, finally_op, callback):
        op.action = "pend"
        op2.action = "pend"
        stage.run_ops_serial(op, op2, op3, callback=callback, finally_op=finally_op)
        stage.next._run_op.assert_called_once_with(op)
        stage.next.complete_op(op)
        stage.next._run_op.assert_any_call(op2)

    @pytest.mark.it("does not run the third op after the second op fails")
    @pytest.mark.it("runs finally_op if the second op fails")
    def test_10(self, stage, op, op2, op3, finally_op, callback):
        op2.action = "fail"
        stage.run_ops_serial(op, op2, op3, callback=callback, finally_op=finally_op)
        assert stage.next._run_op.call_count == 3
        stage.next._run_op.assert_any_call(op)
        stage.next._run_op.assert_any_call(op2)
        stage.next._run_op.assert_any_call(finally_op)

    @pytest.mark.it("calls the callback correctly if the second op fails and finally_op succeeds")
    def test_12(self, stage, op, op2, op3, finally_op, callback):
        op2.action = "fail"
        stage.run_ops_serial(op, op2, op3, finally_op=finally_op, callback=callback)
        assert_callback_failed(callback, finally_op, error=op.error)

    @pytest.mark.it("calls the callback correctly if the second op fails and finally_op also fails")
    def test_13(self, stage, op, op2, op3, finally_op, callback):
        op2.action = "fail"
        finally_op.action = "fail"
        stage.run_ops_serial(op, op2, op3, finally_op=finally_op, callback=callback)
        assert_callback_failed(callback, finally_op, error=finally_op.error)
        pass

    @pytest.mark.it("calls the third op only after the second op succeeds")
    def test_14(self, stage, op, op2, op3, finally_op, callback):
        op2.action = "pend"
        stage.run_ops_serial(op, op2, op3, callback=callback, finally_op=finally_op)
        assert stage.next._run_op.call_count == 2
        stage.next._run_op.assert_any_call(op)
        stage.next._run_op.assert_any_call(op2)
        stage.next.complete_op(op2)
        assert stage.next._run_op.call_count == 4
        stage.next._run_op.assert_any_call(op3)
        stage.next._run_op.assert_any_call(finally_op)

    @pytest.mark.it("runs finally_op if the third op fails")
    def test_15(self, stage, op, op2, op3, finally_op, callback):
        op3.action = "fail"
        stage.run_ops_serial(op, op2, op3, callback=callback, finally_op=finally_op)
        stage.next._run_op.assert_any_call(finally_op)

    @pytest.mark.it("runs finally_op if the third op succeeds")
    def test_16(self, stage, op, op2, op3, finally_op, callback):
        stage.run_ops_serial(op, op2, op3, callback=callback, finally_op=finally_op)
        stage.next._run_op.assert_any_call(finally_op)

    @pytest.mark.it(
        "calls the callback correctly if the third op succeeds and finally_op also succeeds"
    )
    def test_17(self, stage, op, op2, op3, finally_op, callback):
        stage.run_ops_serial(op, op2, op3, callback=callback, finally_op=finally_op)
        assert_callback_succeeded(callback, finally_op)

    @pytest.mark.it("calls the callback correctly if the third op succeeds and finally_op fails")
    def test_18(self, stage, op, op2, op3, finally_op, callback):
        finally_op.action = "fail"
        stage.run_ops_serial(op, op2, op3, callback=callback, finally_op=finally_op)
        assert_callback_failed(callback, finally_op, error=finally_op.error)

    @pytest.mark.it("calls the callback correctly if the third op fails and finally_op succeeds")
    def test_19(self, stage, op, op2, op3, finally_op, callback):
        op3.action = "fail"
        stage.run_ops_serial(op, op2, op3, callback=callback, finally_op=finally_op)
        assert_callback_failed(callback, finally_op, error=op3.error)

    @pytest.mark.it("calls the callback correctly if the third op fails and finally_op also fails")
    def test_20(self, stage, op, op2, op3, finally_op, callback):
        op3.action = "fail"
        finally_op.action = "fail"
        stage.run_ops_serial(op, op2, op3, callback=callback, finally_op=finally_op)
        assert_callback_failed(callback, finally_op, error=op3.error)


@pytest.mark.describe("PipelineStage handle_pipeline_event function")
class TestPipelineStageHandlePipelineEvent(object):
    @pytest.mark.it("calls _handle_pipeline_event")
    def test_1(self, stage, event, mocker):
        stage._handle_pipeline_event = mocker.Mock()
        stage.handle_pipeline_event(event)
        stage._handle_pipeline_event.assert_called_once_with(event)

    @pytest.mark.it("protects _handle_pipeline_event with a try/except block")
    def test_2(self, stage, event, fake_error, mocker):
        stage._handle_pipeline_event = mocker.Mock(side_effect=fake_error)
        stage.handle_pipeline_event(event)
        stage.unhandled_error_handler.assert_called_once_with(fake_error)


@pytest.mark.describe("PipelineStage _handle_pipeline_event function")
class TestPipelineStageHandlePrivatePipelineEvent(object):
    @pytest.mark.it("calls the handle_pipeline_event function in the previous stage")
    def test_1(self, stage, event, mocker):
        stage.handle_pipeline_event = mocker.Mock()
        stage.next._handle_pipeline_event(event)
        stage.handle_pipeline_event.assert_called_once_with(event)

    @pytest.mark.it("calls the unhandled error handler if there is no previous stage")
    def test_2(self, stage, event):
        stage.previous = None
        stage.unhandled_error_handler.assert_not_called()
        stage._handle_pipeline_event(event)
        assert stage.unhandled_error_handler.call_count == 1


@pytest.mark.describe("PipelineStage continue_op function")
class TestPipelineStageContinueOp(object):
    @pytest.mark.it("completes the op without continuing if the op has an error")
    def test_1(self, stage, op, fake_error, callback):
        op.error = fake_error
        op.callback = callback
        stage.continue_op(op)
        callback.assert_called_once_with(op)
        assert stage.next.run_op.call_count == 0

    @pytest.mark.it("fails the op if there is no next stage")
    def test_2(self, stage, op, callback):
        op.callback = callback
        stage.next = None
        stage.continue_op(op)
        assert_callback_failed(callback, op)
        pass

    @pytest.mark.it("passes the op to the next stage if no error")
    def test_3(self, stage, op, callback):
        stage.continue_op(op)
        stage.next.run_op.assert_called_once_with(op)


@pytest.mark.describe("PipelineStage complete_op function")
class TestPipelineStageCompleteOp(object):
    @pytest.mark.it("calls the op callback on success")
    def test_1(self, stage, op, callback):
        op.callback = callback
        stage.complete_op(op)
        assert_callback_succeeded(callback, op)

    @pytest.mark.it("calls the op callback on failure")
    def test_2(self, stage, op, callback, fake_error):
        op.error = fake_error
        op.callback = callback
        stage.complete_op(op)
        assert_callback_failed(callback, op, fake_error)

    @pytest.mark.it("protects the op callback with a try/except handler")
    def test_3(self, stage, op, fake_error, mocker):
        op.callback = mocker.Mock(side_effect=fake_error)
        stage.complete_op(op)
        op.callback.assert_called_once_with(op)
        stage.unhandled_error_handler.assert_called_once_with(fake_error)


@pytest.mark.describe("PipelineStage continue_with_different_op function")
class TestPipelineStageContineWithDifferntOp(object):
    @pytest.mark.it("does not continue running the original op")
    @pytest.mark.it("runs the new op")
    def test_1(self, stage, op):
        new_op = Op()
        stage.continue_with_different_op(original_op=op, new_op=new_op)
        stage.next.run_op.assert_called_once_with(new_op)

    @pytest.mark.it("completes the original op after the new op completes")
    def test_3(self, stage, op, callback):
        op.callback = callback
        new_op = Op()
        new_op.action = "pend"

        stage.continue_with_different_op(original_op=op, new_op=new_op)
        callback.assert_not_called()  # because new_op is pending

        stage.next.complete_op(new_op)
        assert_callback_succeeded(callback, op)

    @pytest.mark.it("returns the new op failure in the original op if new op fails")
    def test_4(self, stage, op, callback):
        op.callback = callback
        new_op = Op()
        new_op.action = "fail"
        stage.continue_with_different_op(original_op=op, new_op=new_op)
        assert_callback_failed(callback, op, new_op.error)
