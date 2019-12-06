# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import logging
import pytest
from tests.common.pipeline.helpers import (
    all_except,
    make_mock_op_or_event,
    StageRunOpTestBase,
    StageHandlePipelineEventTestBase,
)
from azure.iot.device.common.pipeline.pipeline_stages_base import PipelineStage, PipelineRootStage
from azure.iot.device.common.pipeline import pipeline_exceptions
from azure.iot.device.common import handle_exceptions

logging.basicConfig(level=logging.DEBUG)


def add_base_pipeline_stage_tests(
    test_module,
    stage_class_under_test,
    stage_test_config_class,
    extended_stage_instantiation_test_class=None,
):
    class StageTestConfig(stage_test_config_class):
        @pytest.fixture
        def stage(self, mocker, cls_type, init_kwargs):
            stage = cls_type(**init_kwargs)
            stage.next = mocker.MagicMock()
            stage.previous = mocker.MagicMock()
            mocker.spy(stage, "send_op_down")
            mocker.spy(stage, "send_event_up")
            return stage

    #######################
    # INSTANTIATION TESTS #
    #######################

    @pytest.mark.describe("{} -- Instantiation".format(stage_class_under_test.__name__))
    class StageBaseInstantiationTests(StageTestConfig):
        @pytest.mark.it("Initializes 'name' attribute as the classname")
        def test_name(self, cls_type, init_kwargs):
            stage = cls_type(**init_kwargs)
            assert stage.name == stage.__class__.__name__

        @pytest.mark.it("Initializes 'next' attribute as None")
        def test_next(self, cls_type, init_kwargs):
            stage = cls_type(**init_kwargs)
            assert stage.next is None

        @pytest.mark.it("Initializes 'previous' attribute as None")
        def test_previous(self, cls_type, init_kwargs):
            stage = cls_type(**init_kwargs)
            assert stage.previous is None

        @pytest.mark.it("Initializes 'pipeline_root' attribute as None")
        def test_pipeline_root(self, cls_type, init_kwargs):
            stage = cls_type(**init_kwargs)
            assert stage.pipeline_root is None

    if extended_stage_instantiation_test_class:

        class StageInstantiationTests(
            extended_stage_instantiation_test_class, StageBaseInstantiationTests
        ):
            pass

    else:

        class StageInstantiationTests(StageBaseInstantiationTests):
            pass

    setattr(
        test_module,
        "Test{}Instantiation".format(stage_class_under_test.__name__),
        StageInstantiationTests,
    )

    ##############
    # FLOW TESTS #
    ##############

    @pytest.mark.describe("{} - .send_op_down()".format(stage_class_under_test.__name__))
    class StageSendOpDownTests(StageTestConfig):
        @pytest.mark.it("Completes the op with failure (PipelineError) if there is no next stage")
        def test_fails_op_when_no_next_stage(self, mocker, stage, arbitrary_op):
            stage.next = None

            assert not arbitrary_op.completed

            stage.send_op_down(arbitrary_op)

            assert arbitrary_op.completed
            assert type(arbitrary_op.error) is pipeline_exceptions.PipelineError

        @pytest.mark.it("Passes the op to the next stage's .run_op() method")
        def test_passes_op_to_next_stage(self, mocker, stage, arbitrary_op):
            stage.send_op_down(arbitrary_op)
            assert stage.next.run_op.call_count == 1
            assert stage.next.run_op.call_args == mocker.call(arbitrary_op)

    @pytest.mark.describe("{} - .send_event_up()".format(stage_class_under_test.__name__))
    class StageSendEventUpTests(StageTestConfig):
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

    setattr(
        test_module,
        "Test{}SendOpDown".format(stage_class_under_test.__name__),
        StageSendOpDownTests,
    )
    setattr(
        test_module,
        "Test{}SendEventUp".format(stage_class_under_test.__name__),
        StageSendEventUpTests,
    )

    #############################################
    # RUN OP / HANDLE_PIPELINE_EVENT BASE TESTS #
    #############################################

    # These tests are only run if the Stage in question has NOT overridden the PipelineStage base
    # implementations of ._run_op() and/or ._handle_pipeline_event()

    if stage_class_under_test._run_op is PipelineStage._run_op:

        @pytest.mark.describe("{} - .run_op()".format(stage_class_under_test.__name__))
        class StageRunOpUnhandledOp(StageTestConfig, StageRunOpTestBase):
            @pytest.fixture
            def op(self, arbitrary_op):
                return arbitrary_op

            @pytest.mark.it("Sends the operation down the pipeline")
            def test_passes_down(self, mocker, stage, op):
                stage.run_op(op)
                assert stage.send_op_down.call_count == 1
                assert stage.send_op_down.call_args == mocker.call(op)

        setattr(
            test_module,
            "Test{}RunOpUnhandledOp".format(stage_class_under_test.__name__),
            StageRunOpUnhandledOp,
        )

    if stage_class_under_test._handle_pipeline_event is PipelineStage._handle_pipeline_event:

        @pytest.mark.describe(
            "{} - .handle_pipeline_event()".format(stage_class_under_test.__name__)
        )
        class StageHandlePipelineEventUnhandledEvent(
            StageTestConfig, StageHandlePipelineEventTestBase
        ):
            @pytest.fixture
            def event(self, arbitrary_event):
                return arbitrary_event

            @pytest.mark.it("Sends the event up the pipeline")
            def test_passes_up(self, mocker, stage, event):
                stage.handle_pipeline_event(event)
                assert stage.send_event_up.call_count == 1
                assert stage.send_event_up.call_args == mocker.call(event)

        setattr(
            test_module,
            "Test{}HandlePipelineEventUnhandledEvent".format(stage_class_under_test.__name__),
            StageHandlePipelineEventUnhandledEvent,
        )


#############################################################
# CODE BELOW THIS POINT IS DEPRECATED PENDING TEST OVERHAUL #
#############################################################

# CT-TODO: Remove this as soon as possible


def add_base_pipeline_stage_tests_old(
    cls,
    module,
    all_ops,
    handled_ops,
    all_events,
    handled_events,
    extra_initializer_defaults={},
    positional_arguments=[],
    keyword_arguments={},
):
    """
    Add all of the "basic" tests for validating a pipeline stage.  This includes tests for
    instantiation and tests for properly handling "unhandled" operations and events".
    """

    # NOTE: this infrastructure has been disabled, resulting in a reduction in test coverage.
    # Please port all stage tests to the new version of this function above to remedy
    # this problem.

    # add_instantiation_test(
    #     cls=cls,
    #     module=module,
    #     defaults={"name": cls.__name__, "next": None, "previous": None, "pipeline_root": None},
    #     extra_defaults=extra_initializer_defaults,
    #     positional_arguments=positional_arguments,
    #     keyword_arguments=keyword_arguments,
    # )
    _add_unknown_ops_tests(cls=cls, module=module, all_ops=all_ops, handled_ops=handled_ops)
    _add_unknown_events_tests(
        cls=cls, module=module, all_events=all_events, handled_events=handled_events
    )


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
            op.callback_stack.append(mocker.MagicMock())
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
