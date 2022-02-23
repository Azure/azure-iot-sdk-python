# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import pytest


class StageRunOpTestBase(object):
    """All PipelineStage .run_op() tests should inherit from this base class.
    It provides basic tests for dealing with exceptions.
    """

    @pytest.mark.it(
        "Completes the operation with failure if an unexpected Exception is raised while executing the operation and the operation has not yet completed"
    )
    def test_completes_operation_with_error(self, mocker, stage, op, arbitrary_exception):
        stage._run_op = mocker.MagicMock(side_effect=arbitrary_exception)

        stage.run_op(op)

        assert op.completed
        assert op.error is arbitrary_exception

    @pytest.mark.it(
        "Allows an unexpected Exception to propagate if it is raised after the operation has already been completed"
    )
    def test_exception_after_op_completed(self, mocker, stage, op, arbitrary_exception):
        stage._run_op = mocker.MagicMock(side_effect=arbitrary_exception)
        op.completed = True

        with pytest.raises(arbitrary_exception.__class__) as e_info:
            stage.run_op(op)
        assert e_info.value is arbitrary_exception

    @pytest.mark.it(
        "Allows any BaseException that was raised during execution of the operation to propagate"
    )
    def test_base_exception_propagates(self, mocker, stage, op, arbitrary_base_exception):
        stage._run_op = mocker.MagicMock(side_effect=arbitrary_base_exception)

        with pytest.raises(arbitrary_base_exception.__class__) as e_info:
            stage.run_op(op)
        assert e_info.value is arbitrary_base_exception


class StageHandlePipelineEventTestBase(object):
    """All PipelineStage .handle_pipeline_event() tests should inherit from this base class.
    It provides basic tests for dealing with exceptions.
    """

    @pytest.mark.it(
        "Raise any unexpected Exceptions raised during handling of the event as background exceptions, if a previous stage exists"
    )
    def test_uses_background_exception_handler(self, mocker, stage, event, arbitrary_exception):
        stage.previous = mocker.MagicMock()  # force previous stage
        stage._handle_pipeline_event = mocker.MagicMock(side_effect=arbitrary_exception)

        stage.handle_pipeline_event(event)

        assert stage.report_background_exception.call_count == 1
        assert stage.report_background_exception.call_args == mocker.call(arbitrary_exception)

    @pytest.mark.it(
        "Drops any unexpected Exceptions raised during handling of the event if no previous stage exists"
    )
    def test_exception_with_no_previous_stage(self, mocker, stage, event, arbitrary_exception):
        stage.previous = None
        stage._handle_pipeline_event = mocker.MagicMock(side_effect=arbitrary_exception)

        stage.handle_pipeline_event(event)

        assert stage.report_background_exception.call_count == 0
        # No background exception process. No errors were raised.
        # Logging did also occur here, but we don't test logs

    @pytest.mark.it("Allows any BaseException raised during handling of the event to propagate")
    def test_base_exception_propagates(self, mocker, stage, event, arbitrary_base_exception):
        stage._handle_pipeline_event = mocker.MagicMock(side_effect=arbitrary_base_exception)

        with pytest.raises(arbitrary_base_exception.__class__) as e_info:
            stage.handle_pipeline_event(event)
        assert e_info.value is arbitrary_base_exception
