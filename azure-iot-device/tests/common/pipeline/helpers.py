# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import inspect
import pytest
import functools
from threading import Event
from azure.iot.device.common import handle_exceptions
from azure.iot.device.common.pipeline import (
    pipeline_events_base,
    pipeline_ops_base,
    pipeline_stages_base,
    pipeline_events_mqtt,
    pipeline_ops_mqtt,
    config,
)

try:
    from inspect import getfullargspec as getargspec
except ImportError:
    from inspect import getargspec


class StageRunOpTestBase(object):
    """All PipelineStage .run_op() tests should inherit from this base class.
    It provides basic tests for dealing with exceptions.
    """

    @pytest.mark.it(
        "Completes the operation with failure if an unexpected Exception is raised while executing the operation"
    )
    def test_completes_operation_with_error(self, mocker, stage, op, arbitrary_exception):
        stage._run_op = mocker.MagicMock(side_effect=arbitrary_exception)

        stage.run_op(op)

        assert op.completed
        assert op.error is arbitrary_exception

    @pytest.mark.it(
        "Allows any BaseException that was raised during execution of the operation to propogate"
    )
    def test_base_exception_propogates(self, mocker, stage, op, arbitrary_base_exception):
        stage._run_op = mocker.MagicMock(side_effect=arbitrary_base_exception)

        with pytest.raises(arbitrary_base_exception.__class__) as e_info:
            stage.run_op(op)
        assert e_info.value is arbitrary_base_exception


class StageHandlePipelineEventTestBase(object):
    """All PipelineStage .handle_pipeline_event() tests should inherit from this base class.
    It provides basic tests for dealing with exceptions.
    """

    @pytest.mark.it(
        "Sends any unexpected Exceptions raised during handling of the event to the background exception handler"
    )
    def test_uses_background_exception_handler(self, mocker, stage, event, arbitrary_exception):
        stage._handle_pipeline_event = mocker.MagicMock(side_effect=arbitrary_exception)
        mocker.spy(handle_exceptions, "handle_background_exception")

        stage.handle_pipeline_event(event)

        assert handle_exceptions.handle_background_exception.call_count == 1
        assert handle_exceptions.handle_background_exception.call_args == mocker.call(
            arbitrary_exception
        )

    @pytest.mark.it("Allows any BaseException raised during handling of the event to propogate")
    def test_base_exception_propogates(self, mocker, stage, event, arbitrary_base_exception):
        stage._handle_pipeline_event = mocker.MagicMock(side_effect=arbitrary_base_exception)

        with pytest.raises(arbitrary_base_exception.__class__) as e_info:
            stage.handle_pipeline_event(event)
        assert e_info.value is arbitrary_base_exception
