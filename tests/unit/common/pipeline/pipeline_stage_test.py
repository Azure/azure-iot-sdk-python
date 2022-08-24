# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import logging
import pytest
from tests.unit.common.pipeline.helpers import StageRunOpTestBase, StageHandlePipelineEventTestBase
from azure.iot.device.common.pipeline.pipeline_stages_base import PipelineStage
from azure.iot.device.common.pipeline import pipeline_exceptions, pipeline_events_base

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
            mocker.spy(stage, "report_background_exception")
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

        @pytest.mark.it("Initializes 'nucleus' attribute as None")
        def test_pipeline_nucleus(self, cls_type, init_kwargs):
            stage = cls_type(**init_kwargs)
            assert stage.nucleus is None

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
        @pytest.mark.it("Passes the op to the next stage's .run_op() method")
        def test_passes_op_to_next_stage(self, mocker, stage, arbitrary_op):
            stage.send_op_down(arbitrary_op)
            assert stage.next.run_op.call_count == 1
            assert stage.next.run_op.call_args == mocker.call(arbitrary_op)

        @pytest.mark.it("Raises a PipelineRuntimeError if there is no next stage")
        def test_fails_op_when_no_next_stage(self, mocker, stage, arbitrary_op):
            stage.next = None

            with pytest.raises(pipeline_exceptions.PipelineRuntimeError):
                stage.send_op_down(arbitrary_op)

    @pytest.mark.describe("{} - .send_event_up()".format(stage_class_under_test.__name__))
    class StageSendEventUpTests(StageTestConfig):
        @pytest.mark.it(
            "Passes the event up to the previous stage's .handle_pipeline_event() method"
        )
        def test_calls_handle_pipeline_event(self, stage, arbitrary_event, mocker):
            stage.send_event_up(arbitrary_event)
            assert stage.previous.handle_pipeline_event.call_count == 1
            assert stage.previous.handle_pipeline_event.call_args == mocker.call(arbitrary_event)

        @pytest.mark.it("Raises a PipelineRuntimeError if there is no previous stage")
        def test_no_previous_stage(self, stage, arbitrary_event):
            stage.previous = None
            with pytest.raises(pipeline_exceptions.PipelineRuntimeError):
                stage.send_event_up(arbitrary_event)

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

    ###############
    # OTHER TESTS #
    ###############

    @pytest.mark.describe(
        "{} - .report_background_exception()".format(stage_class_under_test.__name__)
    )
    class StageRaiseBackgroundExceptionTests(StageTestConfig):
        @pytest.mark.it(
            "Sends a BackgroundExceptionEvent up the pipeline with the provided exception set on it"
        )
        def test_new_event_sent_up(self, mocker, stage, arbitrary_exception):
            stage.report_background_exception(arbitrary_exception)

            assert stage.send_event_up.call_count == 1
            event = stage.send_event_up.call_args[0][0]
            assert isinstance(event, pipeline_events_base.BackgroundExceptionEvent)
            assert event.e is arbitrary_exception

    setattr(
        test_module,
        "Test{}RaiseBackgroundException".format(stage_class_under_test.__name__),
        StageRaiseBackgroundExceptionTests,
    )
