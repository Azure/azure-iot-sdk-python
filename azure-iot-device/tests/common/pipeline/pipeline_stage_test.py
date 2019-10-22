# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import logging
import pytest
import inspect
import threading
import concurrent.futures
from tests.common.pipeline.helpers import (
    all_except,
    make_mock_op_or_event,
    assert_callback_failed,
    get_arg_count,
    add_mock_method_waiter,
    StageTestBase,
    StageRunOpTestBase,
)
from azure.iot.device.common.pipeline.pipeline_stages_base import PipelineStage, PipelineRootStage
from tests.common.pipeline.pipeline_data_object_test import add_instantiation_test
from azure.iot.device.common.pipeline import pipeline_thread, pipeline_exceptions
from azure.iot.device.common import handle_exceptions
from .fixtures import FakeOperation
from .helpers import assert_callback_succeeded

logging.basicConfig(level=logging.DEBUG)


def add_base_pipeline_stage_tests(
    cls,
    module,
    all_ops,
    handled_ops,
    all_events,
    handled_events,
    methods_that_enter_pipeline_thread=[],
    methods_that_can_run_in_any_thread=[],
    extra_initializer_defaults={},
    positional_arguments=[],
    keyword_arguments={},
):
    """
    Add all of the "basic" tests for validating a pipeline stage.  This includes tests for
    instantiation and tests for properly handling "unhandled" operations and events".
    """

    add_instantiation_test(
        cls=cls,
        module=module,
        defaults={"name": cls.__name__, "next": None, "previous": None, "pipeline_root": None},
        extra_defaults=extra_initializer_defaults,
        positional_arguments=positional_arguments,
        keyword_arguments=keyword_arguments,
    )
    _add_unknown_ops_tests(cls=cls, module=module, all_ops=all_ops, handled_ops=handled_ops)
    _add_unknown_events_tests(
        cls=cls, module=module, all_events=all_events, handled_events=handled_events
    )
    _add_pipeline_thread_tests(
        cls=cls,
        module=module,
        methods_that_enter_pipeline_thread=methods_that_enter_pipeline_thread,
        methods_that_can_run_in_any_thread=methods_that_can_run_in_any_thread,
    )
    _add_pipeline_flow_tests(cls=cls, module=module)


def _add_unknown_ops_tests(cls, module, all_ops, handled_ops):
    """
    Add tests for properly handling of "unknown operations," which are operations that aren't
    handled by a particular stage.  These operations should be passed down by any stage into
    the stages that follow.
    """
    unknown_ops = all_except(all_items=all_ops, items_to_exclude=handled_ops)

    @pytest.mark.describe("{} - .run_op() -- unknown and unhandled operations".format(cls.__name__))
    class LocalTestObject(StageRunOpTestBase):
        @pytest.fixture
        def op(self, op_cls, mocker):
            op = make_mock_op_or_event(op_cls)
            op.callback = mocker.MagicMock()
            add_mock_method_waiter(op, "callback")
            return op

        @pytest.fixture
        def stage(self):
            if cls == PipelineRootStage:
                return cls(None)
            else:
                return cls()

        @pytest.mark.it("Passes unknown operation down to the next stage")
        @pytest.mark.parametrize("op_cls", unknown_ops)
        def test_passes_op_to_next_stage(self, mocker, op_cls, op, stage):
            mocker.spy(stage, "send_op_down")
            stage.run_op(op)
            assert stage.send_op_down.call_count == 1
            assert stage.send_op_down.call_args == mocker.call(op)

        # @pytest.mark.it("Catches Exceptions raised when passing unknown operation to next stage")
        # @pytest.mark.parametrize("op_cls", unknown_ops)
        # def test_passes_op_to_next_stage_which_throws_exception(
        #     self, op_cls, op, stage, next_stage_raises_arbitrary_exception, arbitrary_exception
        # ):
        #     stage.run_op(op)
        #     op.wait_for_callback_to_be_called()
        #     assert_callback_failed(op=op, error=arbitrary_exception)

        # @pytest.mark.it(
        #     "Allows BaseExceptions raised when passing unknown operation to next start to propogate"
        # )
        # @pytest.mark.parametrize("op_cls", unknown_ops)
        # def test_passes_op_to_next_stage_which_throws_base_exception(
        #     self,
        #     op_cls,
        #     op,
        #     stage,
        #     next_stage_raises_arbitrary_base_exception,
        #     arbitrary_base_exception,
        # ):
        #     with pytest.raises(arbitrary_base_exception.__class__) as e_info:
        #         stage.run_op(op)
        #     assert e_info.value is arbitrary_base_exception

    setattr(module, "Test{}UnknownOps".format(cls.__name__), LocalTestObject)


def _add_unknown_events_tests(cls, module, all_events, handled_events):
    """
    Add tests for properly handling of "unknown events," which are events that aren't
    handled by a particular stage.  These operations should be passed up by any stage into
    the stages that proceed it..
    """

    unknown_events = all_except(all_items=all_events, items_to_exclude=handled_events)

    if not unknown_events:
        return

    @pytest.mark.describe(
        "{} - .handle_pipeline_event() -- unknown and unhandled events".format(cls.__name__)
    )
    @pytest.mark.parametrize("event_cls", unknown_events)
    class LocalTestObject(StageTestBase):
        @pytest.fixture
        def event(self, event_cls):
            return make_mock_op_or_event(event_cls)

        @pytest.fixture
        def stage(self):
            return cls()

        @pytest.fixture
        def previous(self, stage, stage_base_configuration):
            return stage.previous

        @pytest.mark.it("Passes unknown event to previous stage")
        def test_passes_event_to_previous_stage(self, event_cls, stage, event, previous, mocker):
            mocker.spy(previous, "handle_pipeline_event")
            stage.handle_pipeline_event(event)
            assert previous.handle_pipeline_event.call_count == 1
            assert previous.handle_pipeline_event.call_args[0][0] == event

        @pytest.mark.it("Calls unhandled exception handler if there is no previous stage")
        def test_passes_event_with_no_previous_stage(
            self, event_cls, stage, event, unhandled_error_handler
        ):
            stage.previous = None
            stage.handle_pipeline_event(event)
            assert unhandled_error_handler.call_count == 1

        @pytest.mark.it("Catches Exceptions raised when passing unknown event to previous stage")
        def test_passes_event_to_previous_stage_which_throws_exception(
            self,
            event_cls,
            stage,
            event,
            previous,
            unhandled_error_handler,
            arbitrary_exception,
            mocker,
        ):
            previous.handle_pipeline_event = mocker.MagicMock(side_effect=arbitrary_exception)
            stage.handle_pipeline_event(event)
            assert unhandled_error_handler.call_count == 1
            assert unhandled_error_handler.call_args[0][0] == arbitrary_exception

        @pytest.mark.it(
            "Allows BaseExceptions raised when passing unknown operation to next start to propogate"
        )
        def test_passes_event_to_previous_stage_which_throws_base_exception(
            self,
            event_cls,
            stage,
            event,
            previous,
            unhandled_error_handler,
            arbitrary_base_exception,
            mocker,
        ):
            previous.handle_pipeline_event = mocker.MagicMock(side_effect=arbitrary_base_exception)
            with pytest.raises(arbitrary_base_exception.__class__) as e_info:
                stage.handle_pipeline_event(event)
            assert unhandled_error_handler.call_count == 0
            assert e_info.value is arbitrary_base_exception

    setattr(module, "Test{}UnknownEvents".format(cls.__name__), LocalTestObject)


class ThreadLaunchedError(Exception):
    pass


def _add_pipeline_thread_tests(
    cls, module, methods_that_enter_pipeline_thread, methods_that_can_run_in_any_thread
):
    def does_method_assert_pipeline_thread(method_name):
        if method_name.startswith("__"):
            return False
        elif method_name in methods_that_enter_pipeline_thread:
            return False
        elif method_name in methods_that_can_run_in_any_thread:
            return False
        else:
            return True

    methods_that_assert_pipeline_thread = [
        x[0]
        for x in inspect.getmembers(cls, inspect.isfunction)
        if does_method_assert_pipeline_thread(x[0])
    ]

    @pytest.mark.describe("{} - Pipeline threading".format(cls.__name__))
    class LocalTestObject(object):
        @pytest.fixture
        def stage(self):
            # BKTODO: Make this more generic
            if cls == PipelineRootStage:
                return cls(None)
            else:
                return cls()

        @pytest.mark.parametrize("method_name", methods_that_assert_pipeline_thread)
        @pytest.mark.it("Enforces use of the pipeline thread when calling method")
        def test_asserts_in_pipeline(self, stage, method_name, fake_non_pipeline_thread):
            func = getattr(stage, method_name)
            args = [None for i in (range(get_arg_count(func) - 1))]
            with pytest.raises(AssertionError):
                func(*args)

        if methods_that_enter_pipeline_thread:

            @pytest.mark.parametrize("method_name", methods_that_enter_pipeline_thread)
            @pytest.mark.it("Automatically enters the pipeline thread when calling method")
            def test_enters_pipeline(self, mocker, stage, method_name, fake_non_pipeline_thread):
                func = getattr(stage, method_name)
                args = [None for i in (range(get_arg_count(func) - 1))]

                #
                # We take a bit of a roundabout way to verify that the functuion enters the
                # pipeline executor:
                #
                # 1. we verify that the method got the pipeline executor
                # 2. we verify that the method invoked _something_ on the pipeline executor
                #
                # It's not perfect, but it's good enough.
                #
                # We do this because:
                # 1. We don't have the exact right args to run the method and we don't want
                #    to add the complexity to get the right args in this test.
                # 2. We can't replace the wrapped method with a mock, AFAIK.
                #
                pipeline_executor = pipeline_thread._get_named_executor("pipeline")
                mocker.patch.object(pipeline_executor, "submit")
                pipeline_executor.submit.side_effect = ThreadLaunchedError
                mocker.spy(pipeline_thread, "_get_named_executor")

                # If the method calls submit on some executor, it will raise a ThreadLaunchedError
                with pytest.raises(ThreadLaunchedError):
                    func(*args)

                # now verify that the code got the pipeline executor and verify that it used that
                # executor to launch something.
                assert pipeline_thread._get_named_executor.call_count == 1
                assert pipeline_thread._get_named_executor.call_args[0][0] == "pipeline"
                assert pipeline_executor.submit.call_count == 1

    setattr(module, "Test{}PipelineThreading".format(cls.__name__), LocalTestObject)


def _add_pipeline_flow_tests(cls, module):
    class PipelineFlowTestBase(StageTestBase):
        @pytest.fixture
        def stage(self):
            class MockPipelineStage(PipelineStage):
                def _execute_op(self, op):
                    self.send_op_down(op)

            return MockPipelineStage()

    @pytest.mark.describe("{} - .send_worker_op_down()".format(cls.__name__))
    class SendWorkerOpDownTests(PipelineFlowTestBase):
        @pytest.fixture
        def arbitrary_worker_op(self, mocker):
            op = FakeOperation(callback=mocker.MagicMock())
            op.name = "arbitrary_worker_op"
            return op

        @pytest.mark.it("Runs the worker op and does not continue running the original op")
        def test_runs_worker_op(self, mocker, stage, arbitrary_op, arbitrary_worker_op):
            stage.send_worker_op_down(worker_op=arbitrary_worker_op, op=arbitrary_op)
            assert stage.next.run_op.call_count == 1
            assert stage.next.run_op.call_args == mocker.call(arbitrary_worker_op)

        @pytest.mark.it("Completes the original op after the worker op completes")
        def test_completes_original_op_after_worker_op_completes(
            self, stage, arbitrary_op, arbitrary_worker_op
        ):
            callback = arbitrary_op.callback

            stage.send_worker_op_down(worker_op=arbitrary_worker_op, op=arbitrary_op)
            assert callback.call_count == 0  # because arbitrary_worker_op is pending

            stage.next.complete_op(arbitrary_worker_op)
            assert_callback_succeeded(op=arbitrary_op)

        @pytest.mark.it("Returns the worker op failure in the original op if worker op fails")
        def test_returns_worker_op_failure_in_original_op(
            self,
            stage,
            arbitrary_op,
            arbitrary_worker_op,
            arbitrary_exception,
            next_stage_raises_arbitrary_exception,
        ):
            stage.send_worker_op_down(worker_op=arbitrary_worker_op, op=arbitrary_op)
            assert_callback_failed(arbitrary_op, error=arbitrary_exception)

    @pytest.mark.describe("{} - .send_op_down()".format(cls.__name__))
    class SendOpDownTests(PipelineFlowTestBase):
        @pytest.mark.it("Fails the op if there is no next stage")
        def test_fails_op_when_no_next_stage(self, stage, arbitrary_op):
            stage.next = None
            stage.send_op_down(arbitrary_op)
            assert_callback_failed(op=arbitrary_op, error=pipeline_exceptions.PipelineError)

        @pytest.mark.it("Passes the op to the next stage")
        def test_passes_op_to_next_stage(self, mocker, stage, arbitrary_op):
            stage.send_op_down(arbitrary_op)
            assert stage.next.run_op.call_count == 1
            assert stage.next.run_op.call_args == mocker.call(arbitrary_op)

    @pytest.mark.describe("{} - .complete_op()".format(cls.__name__))
    class CompleteOpTests(PipelineFlowTestBase):
        @pytest.mark.it("Calls the op callback on success")
        def test_calls_callback_on_success(self, stage, arbitrary_op):
            stage.complete_op(arbitrary_op)
            assert_callback_succeeded(arbitrary_op)

        @pytest.mark.it("Calls the op callback on failure")
        def test_calls_callback_on_error(self, stage, arbitrary_op, arbitrary_exception):
            stage.complete_op(arbitrary_op, error=arbitrary_exception)
            assert_callback_failed(op=arbitrary_op, error=arbitrary_exception)

        @pytest.mark.it(
            "Calls handle_background_exception with a PipelineError if the op has previously been completed"
        )
        def test_background_exception_if_called_twice(self, stage, arbitrary_op, mocker):
            mocker.spy(handle_exceptions, "handle_background_exception")
            stage.complete_op(arbitrary_op)
            stage.complete_op(arbitrary_op)
            assert handle_exceptions.handle_background_exception.call_count == 1
            assert (
                handle_exceptions.handle_background_exception.call_args[0][0].__class__
                == pipeline_exceptions.PipelineError
            )

    @pytest.mark.describe("{} - .send_completed_op_up()".format(cls.__name__))
    class SendCompletedOpUpTests(PipelineFlowTestBase):
        @pytest.mark.it("Calls the op callback on success")
        def test_calls_callback_on_success(self, stage, arbitrary_op):
            arbitrary_op.completed = True
            stage.send_completed_op_up(arbitrary_op)
            assert_callback_succeeded(arbitrary_op)

        @pytest.mark.it("Calls the op callback on failure")
        def test_calls_callback_on_error(self, stage, arbitrary_op, arbitrary_exception):
            arbitrary_op.completed = True
            stage.send_completed_op_up(arbitrary_op, error=arbitrary_exception)
            assert_callback_failed(op=arbitrary_op, error=arbitrary_exception)

        @pytest.mark.it(
            "Calls the callback with a PipelineError if the operation has not been completed"
        )
        def test_error_if_not_completed(self, stage, arbitrary_op):
            with pytest.raises(pipeline_exceptions.PipelineError):
                stage.send_completed_op_up(arbitrary_op)

        @pytest.mark.it(
            "Handles Exceptions raised in operation callback and passes them to the unhandled error handler"
        )
        def test_op_callback_raises_exception(
            self, stage, arbitrary_op, arbitrary_exception, mocker, unhandled_error_handler
        ):
            arbitrary_op.callback = mocker.Mock(side_effect=arbitrary_exception)
            arbitrary_op.completed = True
            stage.send_completed_op_up(arbitrary_op)
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
                stage.send_completed_op_up(arbitrary_op)

    @pytest.mark.describe("{} - .send_op_down_and_intercept_return()".format(cls.__name__))
    class SendOpDownAndInterceptReturnTests(PipelineFlowTestBase):
        @pytest.mark.it("Calls send_op_down to send the op down")
        def test_sends_op_down(self, stage, arbitrary_op, mocker):
            intercepted_return = mocker.MagicMock()
            mocker.spy(stage, "send_op_down")
            stage.send_op_down_and_intercept_return(arbitrary_op, intercepted_return)
            assert stage.send_op_down.call_count == 1
            assert stage.send_op_down.call_args == mocker.call(arbitrary_op)

        @pytest.mark.it("Calls the intercepted_return function when the op succeeds")
        def test_calls_intercepted_return_on_op_success(
            self, stage, arbitrary_op, mocker, next_stage_succeeds
        ):
            intercepted_return = mocker.MagicMock()
            stage.send_op_down_and_intercept_return(arbitrary_op, intercepted_return)
            assert intercepted_return.call_args == mocker.call(op=arbitrary_op, error=None)

        @pytest.mark.it("Calls the intercepted_return function when the op fails")
        def test_calls_intercepted_return_on_op_failure(
            self,
            stage,
            arbitrary_op,
            mocker,
            arbitrary_exception,
            next_stage_raises_arbitrary_exception,
        ):
            intercepted_return = mocker.MagicMock()
            stage.send_op_down_and_intercept_return(arbitrary_op, intercepted_return)
            assert intercepted_return.call_args == mocker.call(
                op=arbitrary_op, error=arbitrary_exception
            )

        @pytest.mark.it(
            "Ensures that the op callback is set to its original value when the intercepted_return function is called"
        )
        def test_restores_callback_before_calling_intercepted_return(
            self, stage, arbitrary_op, mocker, next_stage_succeeds
        ):
            saved_callback = arbitrary_op.callback
            intercepted_return = mocker.MagicMock()
            stage.send_op_down_and_intercept_return(arbitrary_op, intercepted_return)
            assert intercepted_return.call_args[1]["op"].callback == saved_callback

    @pytest.mark.describe("{} - .send_event_up()".format(cls.__name__))
    class SendEventUpTests(PipelineFlowTestBase):
        @pytest.mark.it("Calls handle_pipeline_event on the previous stage")
        def test_calls_handle_pipeline_event(self, stage, arbitrary_event, mocker):
            mocker.spy(stage, "handle_pipeline_event")
            stage.next.send_event_up(arbitrary_event)
            assert stage.handle_pipeline_event.call_count == 1
            assert stage.handle_pipeline_event.call_args == mocker.call(arbitrary_event)

        @pytest.mark.it(
            "Calls handle_background_exception with a PipelineError if there is no previous stage"
        )
        def test_no_previous_stage(self, stage, arbitrary_event, mocker):
            stage.previous = None
            mocker.spy(handle_exceptions, "handle_background_exception")
            stage.send_event_up(arbitrary_event)
            assert handle_exceptions.handle_background_exception.call_count == 1
            assert (
                handle_exceptions.handle_background_exception.call_args[0][0].__class__
                == pipeline_exceptions.PipelineError
            )

    setattr(module, "Test{}SendWorkerOpDown".format(cls.__name__), SendWorkerOpDownTests)
    setattr(module, "Test{}SendOpDown".format(cls.__name__), SendOpDownTests)
    setattr(module, "Test{}CompleteOp".format(cls.__name__), CompleteOpTests)
    setattr(module, "Test{}SendCompletedOpUp".format(cls.__name__), SendCompletedOpUpTests)
    setattr(
        module,
        "Test{}SendOpDwonAndInterceptReturn".format(cls.__name__),
        SendOpDownAndInterceptReturnTests,
    )
    setattr(module, "Test{}SendEventUp".format(cls.__name__), SendEventUpTests)
