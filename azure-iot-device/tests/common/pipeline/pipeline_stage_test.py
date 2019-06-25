# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import logging
import pytest
from tests.common.pipeline.helpers import (
    all_except,
    make_mock_stage,
    make_mock_op_or_event,
    assert_callback_failed,
    UnhandledException,
)
from azure.iot.device.common.pipeline.pipeline_stages_base import PipelineStage
from tests.common.pipeline.pipeline_data_object_test import add_instantiation_test

logging.basicConfig(level=logging.INFO)


def add_base_pipeline_stage_tests(cls, module, all_ops, handled_ops, all_events, handled_events):
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


def add_unknown_ops_tests(cls, module, all_ops, handled_ops):
    """
    Add tests for properly handling of "unknown operations," which are operations that aren't
    handled by a particular stage.  These operations should be passed down by any stage into
    the stages that follow.
    """
    unknown_ops = all_except(all_items=all_ops, items_to_exclude=handled_ops)

    @pytest.mark.describe("{} - .run_op() -- unknown and unhandled operations".format(cls.__name__))
    @pytest.mark.parametrize("op_cls", unknown_ops)
    class LocalTestObject(object):
        @pytest.fixture
        def op(self, op_cls, callback):
            op = make_mock_op_or_event(op_cls)
            op.callback = callback
            op.action = "pend"
            return op

        @pytest.fixture
        def stage(self, mocker):
            return make_mock_stage(mocker=mocker, stage_to_make=cls)

        @pytest.mark.it("Passes unknown operation to next stage")
        def test_passes_op_to_next_stage(self, op_cls, op, stage):
            stage.run_op(op)
            assert stage.next.run_op.call_count == 1
            assert stage.next.run_op.call_args[0][0] == op

        @pytest.mark.it("Fails unknown operation if there is no next stage")
        def test_passes_op_with_no_next_stage(self, op_cls, op, stage):
            stage.next = None
            stage.run_op(op)
            assert_callback_failed(op=op)

        @pytest.mark.it("Catches Exceptions raised when passing unknown operation to next stage")
        def test_passes_op_to_next_stage_which_throws_exception(self, op_cls, op, stage):
            op.action = "exception"
            stage.run_op(op)
            assert_callback_failed(op=op)

        @pytest.mark.it(
            "Allows BaseExceptions raised when passing unknown operation to next start to propogate"
        )
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

                def _run_op(self, op):
                    pass

            previous = PreviousStage()
            stage.previous = previous
            return previous

        @pytest.fixture
        def unhandled_error_handler(self, stage, mocker):
            class MockPipelineRootStage(object):
                def __init__(self):
                    self.unhandled_error_handler = mocker.MagicMock()

            root = MockPipelineRootStage()
            stage.pipeline_root = root
            return root.unhandled_error_handler

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

            pass

    setattr(module, "Test{}UnknownEvents".format(cls.__name__), LocalTestObject)
