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
    StageHandlePipelineEventTestBase,
)
from azure.iot.device.common.pipeline.pipeline_stages_base import PipelineStage, PipelineRootStage
from tests.common.pipeline.pipeline_event_test import add_instantiation_test
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
        @pytest.fixture(params=unknown_ops)
        def op(self, request, mocker):
            op = make_mock_op_or_event(request.param)
            op.callbacks.append(mocker.MagicMock())  # TODO: make this simpler
            # add_mock_method_waiter(op, "callback")
            return op

        @pytest.fixture
        def stage(self):
            if cls == PipelineRootStage:
                return cls(None)
            else:
                return cls()

        @pytest.mark.it("Passes unknown operation down to the next stage")
        def test_passes_op_to_next_stage(self, mocker, op, stage):
            mocker.spy(stage, "send_op_down")
            stage.run_op(op)
            assert stage.send_op_down.call_count == 1
            assert stage.send_op_down.call_args == mocker.call(op)

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
    class LocalTestObject(StageHandlePipelineEventTestBase):
        @pytest.fixture(params=unknown_events)
        def event(self, request):
            return make_mock_op_or_event(request.param)

        @pytest.fixture
        def stage(self):
            return cls()

        @pytest.mark.it("Passes unknown event to previous stage")
        def test_passes_event_to_previous_stage(self, stage, event, mocker):
            mocker.spy(stage, "send_event_up")
            stage.handle_pipeline_event(event)

            assert stage.send_event_up.call_count == 1
            assert stage.send_event_up.call_args == mocker.call(event)

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
    class PipelineFlowTestBase(object):
        @pytest.fixture
        def stage(self, mocker):
            if cls == PipelineRootStage:
                stage = cls(None)
            else:
                stage = cls()
            stage.next = mocker.MagicMock()
            stage.previous = mocker.MagicMock()
            return stage

    @pytest.mark.describe("{} - .send_op_down()".format(cls.__name__))
    class SendOpDownTests(PipelineFlowTestBase):
        @pytest.mark.it("Completes the op with failure (PipelineError) if there is no next stage")
        def test_fails_op_when_no_next_stage(self, mocker, stage, arbitrary_op):
            mocker.spy(arbitrary_op, "complete")
            stage.next = None

            stage.send_op_down(arbitrary_op)

            assert arbitrary_op.complete.call_count == 1
            assert (
                type(arbitrary_op.complete.call_args[1]["error"])
                == pipeline_exceptions.PipelineError
            )

        @pytest.mark.it("Passes the op to the next stage's .run_op() method")
        def test_passes_op_to_next_stage(self, mocker, stage, arbitrary_op):
            stage.send_op_down(arbitrary_op)
            assert stage.next.run_op.call_count == 1
            assert stage.next.run_op.call_args == mocker.call(arbitrary_op)

    @pytest.mark.describe("{} - .send_event_up()".format(cls.__name__))
    class SendEventUpTests(PipelineFlowTestBase):
        @pytest.mark.it(
            "Passes the event up to the previous stage's .handle_pipeline_event() method"
        )
        def test_calls_handle_pipeline_event(self, stage, arbitrary_event, mocker):
            stage.send_event_up(arbitrary_event)
            assert stage.previous.handle_pipeline_event.call_count == 1
            assert stage.previous.handle_pipeline_event.call_args == mocker.call(arbitrary_event)

        @pytest.mark.it(
            "Sends a PipelineError to the background exception handler instead of sending the event up the pipeline, if there is no previous pipeline stage"
        )
        def test_no_previous_stage(self, stage, arbitrary_event, mocker):
            stage.previous = None
            mocker.spy(handle_exceptions, "handle_background_exception")

            stage.send_event_up(arbitrary_event)

            assert handle_exceptions.handle_background_exception.call_count == 1
            assert (
                type(handle_exceptions.handle_background_exception.call_args[0][0])
                == pipeline_exceptions.PipelineError
            )

    setattr(module, "Test{}SendOpDown".format(cls.__name__), SendOpDownTests)
    setattr(module, "Test{}SendEventUp".format(cls.__name__), SendEventUpTests)
