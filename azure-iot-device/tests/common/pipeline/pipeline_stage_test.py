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
    make_mock_stage,
    make_mock_op_or_event,
    assert_callback_failed,
    UnhandledException,
    get_arg_count,
    add_mock_method_waiter,
)
from azure.iot.device.common.pipeline.pipeline_stages_base import PipelineStage
from tests.common.pipeline.pipeline_data_object_test import add_instantiation_test
from azure.iot.device.common.pipeline import pipeline_thread

logging.basicConfig(level=logging.INFO)


def add_base_pipeline_stage_tests(
    cls,
    module,
    all_ops,
    handled_ops,
    all_events,
    handled_events,
    methods_that_enter_pipeline_thread=[],
    methods_that_can_run_in_any_thread=[],
):
    """
    Add all of the "basic" tests for validating a pipeline stage.  This includes tests for
    instantiation and tests for properly handling "unhandled" operations and events".
    """

    add_instantiation_test(
        cls=cls,
        module=module,
        defaults={"name": cls.__name__, "next": None, "previous": None, "pipeline_root": None},
    )
    add_unknown_ops_tests(cls=cls, module=module, all_ops=all_ops, handled_ops=handled_ops)
    add_unknown_events_tests(
        cls=cls, module=module, all_events=all_events, handled_events=handled_events
    )
    add_pipeline_thread_tests(
        cls=cls,
        module=module,
        methods_that_enter_pipeline_thread=methods_that_enter_pipeline_thread,
        methods_that_can_run_in_any_thread=methods_that_can_run_in_any_thread,
    )


def add_unknown_ops_tests(cls, module, all_ops, handled_ops):
    """
    Add tests for properly handling of "unknown operations," which are operations that aren't
    handled by a particular stage.  These operations should be passed down by any stage into
    the stages that follow.
    """
    unknown_ops = all_except(all_items=all_ops, items_to_exclude=handled_ops)

    @pytest.mark.describe("{} - .run_op() -- unknown and unhandled operations".format(cls.__name__))
    class LocalTestObject(object):
        @pytest.fixture
        def op(self, op_cls, callback):
            op = make_mock_op_or_event(op_cls)
            op.callback = callback
            op.action = "pend"
            add_mock_method_waiter(op, "callback")
            return op

        @pytest.fixture
        def stage(self, mocker):
            return make_mock_stage(mocker=mocker, stage_to_make=cls)

        @pytest.mark.it("Passes unknown operation to next stage")
        @pytest.mark.parametrize("op_cls", unknown_ops)
        def test_passes_op_to_next_stage(self, op_cls, op, stage):
            stage.run_op(op)
            assert stage.next.run_op.call_count == 1
            assert stage.next.run_op.call_args[0][0] == op

        @pytest.mark.it("Fails unknown operation if there is no next stage")
        @pytest.mark.parametrize("op_cls", unknown_ops)
        def test_passes_op_with_no_next_stage(self, op_cls, op, stage):
            stage.next = None
            stage.run_op(op)
            op.wait_for_callback_to_be_called()
            assert_callback_failed(op=op)

        @pytest.mark.it("Catches Exceptions raised when passing unknown operation to next stage")
        @pytest.mark.parametrize("op_cls", unknown_ops)
        def test_passes_op_to_next_stage_which_throws_exception(self, op_cls, op, stage):
            op.action = "exception"
            stage.run_op(op)
            op.wait_for_callback_to_be_called()
            assert_callback_failed(op=op)

        @pytest.mark.it(
            "Allows BaseExceptions raised when passing unknown operation to next start to propogate"
        )
        @pytest.mark.parametrize("op_cls", unknown_ops)
        def test_passes_op_to_next_stage_which_throws_base_exception(self, op_cls, op, stage):
            op.action = "base_exception"
            with pytest.raises(UnhandledException):
                stage.run_op(op)

    setattr(module, "Test{}UnknownOps".format(cls.__name__), LocalTestObject)


def add_unknown_events_tests(cls, module, all_events, handled_events):
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
    class LocalTestObject(object):
        @pytest.fixture
        def event(self, event_cls):
            return make_mock_op_or_event(event_cls)

        @pytest.fixture
        def stage(self, mocker):
            return make_mock_stage(mocker=mocker, stage_to_make=cls)

        @pytest.fixture
        def previous(self, stage, mocker):
            class PreviousStage(PipelineStage):
                def __init__(self):
                    super(PreviousStage, self).__init__()
                    self.handle_pipeline_event = mocker.MagicMock()

                def _execute_op(self, op):
                    pass

            previous = PreviousStage()
            stage.previous = previous
            return previous

        @pytest.mark.it("Passes unknown event to previous stage")
        def test_passes_event_to_previous_stage(self, event_cls, stage, event, previous):
            stage.handle_pipeline_event(event)
            assert previous.handle_pipeline_event.call_count == 1
            assert previous.handle_pipeline_event.call_args[0][0] == event

        @pytest.mark.it("Calls unhandled exception handler if there is no previous stage")
        def test_passes_event_with_no_previous_stage(
            self, event_cls, stage, event, unhandled_error_handler
        ):
            stage.handle_pipeline_event(event)
            assert unhandled_error_handler.call_count == 1

        @pytest.mark.it("Catches Exceptions raised when passing unknown event to previous stage")
        def test_passes_event_to_previous_stage_which_throws_exception(
            self, event_cls, stage, event, previous, unhandled_error_handler
        ):
            e = Exception()
            previous.handle_pipeline_event.side_effect = e
            stage.handle_pipeline_event(event)
            assert unhandled_error_handler.call_count == 1
            assert unhandled_error_handler.call_args[0][0] == e

        @pytest.mark.it(
            "Allows BaseExceptions raised when passing unknown operation to next start to propogate"
        )
        def test_passes_event_to_previous_stage_which_throws_base_exception(
            self, event_cls, stage, event, previous, unhandled_error_handler
        ):
            e = UnhandledException()
            previous.handle_pipeline_event.side_effect = e
            with pytest.raises(UnhandledException):
                stage.handle_pipeline_event(event)
            assert unhandled_error_handler.call_count == 0

    setattr(module, "Test{}UnknownEvents".format(cls.__name__), LocalTestObject)


class ThreadLaunchedError(Exception):
    pass


def add_pipeline_thread_tests(
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
