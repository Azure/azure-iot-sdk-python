# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging
import sys
from . import pipeline_thread
from azure.iot.device.common import unhandled_exceptions

from six.moves import queue

logger = logging.getLogger(__name__)


@pipeline_thread.runs_on_pipeline_thread
def delegate_to_different_op(stage, original_op, new_op):
    """
    Continue an operation using a new operation.  This means that the new operation
    will be passed down the pipeline (starting at the next stage). When that new
    operation completes, the original operation will also complete.  In this way,
    a stage can accept one type of operation and, effectively, change that operation
    into a different type of operation before passing it to the next stage.

    This is useful when a generic operation (such as "enable feature") needs to be
    converted into a more specific operation (such as "subscribe to mqtt topic").
    In that case, a stage's _execute_op function would call this function passing in
    the original "enable feature" op and the new "subscribe to mqtt topic"
    op.  This function will pass the "subscribe" down. When the "subscribe" op
    is completed, this function will cause the original op to complete.

    This function is only really useful if there is no data returned in the
    new_op that that needs to be copied back into the original_op before
    completing it.  If data needs to be copied this way, some other method needs
    to be used.  (or a "copy data back" function needs to be added to this function
    as an optional parameter.)

    :param PipelineStage stage: stage to delegate the operation to
    :param PipelineOperation original_op: Operation that is being continued using a
      different op.  This is most likely the operation that is currently being handled
      by the stage.  This operation is not actually continued, in that it is not
      actually passed down the pipeline.  Instead, the original_op operation is
      effectively paused while we wait for the new_op operation to complete.  When
      the new_op operation completes, the original_op operation will also be completed.
    :param PipelineOperation new_op: Operation that is being passed down the pipeline
      to effectively continue the work represented by original_op.  This is most likely
      a different type of operation that is able to accomplish the intention of the
      original_op in a way that is more specific than the original_op.
    """

    logger.debug("{}({}): continuing with {} op".format(stage.name, original_op.name, new_op.name))

    @pipeline_thread.runs_on_pipeline_thread
    def new_op_complete(op):
        logger.debug(
            "{}({}): completing with result from {}".format(
                stage.name, original_op.name, new_op.name
            )
        )
        original_op.error = new_op.error
        complete_op(stage, original_op)

    new_op.callback = new_op_complete
    pass_op_to_next_stage(stage, new_op)


@pipeline_thread.runs_on_pipeline_thread
def pass_op_to_next_stage(stage, op):
    """
    Helper function to continue a given operation by passing it to the next stage
    in the pipeline.  If there is no next stage in the pipeline, this function
    will fail the operation and call complete_op to return the failure back up the
    pipeline.  If the operation is already in an error state, this function will
    complete the operation in order to return that error to the caller.

    :param PipelineStage stage: stage that the operation is being passed from
    :param PipelineOperation op: Operation which is being passed on
    """
    if op.error:
        logger.error("{}({}): op has error.  completing.".format(stage.name, op.name))
        complete_op(stage, op)
    elif not stage.next:
        logger.error("{}({}): no next stage.  completing with error".format(stage.name, op.name))
        op.error = NotImplementedError(
            "{} not handled after {} stage with no next stage".format(op.name, stage.name)
        )
        complete_op(stage, op)
    else:
        logger.debug("{}({}): passing to next stage.".format(stage.name, op.name))
        stage.next.run_op(op)


@pipeline_thread.runs_on_pipeline_thread
def complete_op(stage, op):
    """
    Helper function to complete an operation by calling its callback function thus
    returning the result of the operation back up the pipeline.  This is perferred to
    calling the operation's callback directly as it provides several layers of protection
    (such as a try/except wrapper) which are strongly advised.
    """
    if op.error:
        logger.error("{}({}): completing with error {}".format(stage.name, op.name, op.error))
    else:
        logger.debug("{}({}): completing without error".format(stage.name, op.name))

    try:
        op.callback(op)
    except Exception as e:
        _, e, _ = sys.exc_info()
        logger.error(
            msg="Unhandled error calling back inside {}.complete_op() after {} complete".format(
                stage.name, op.name
            ),
            exc_info=e,
        )
        unhandled_exceptions.exception_caught_in_background_thread(e)


@pipeline_thread.runs_on_pipeline_thread
def pass_event_to_previous_stage(stage, event):
    """
    Helper function to pass an event to the previous stage of the pipeline.  This is the default
    behavior of events while traveling through the pipeline. They start somewhere (maybe the
    bottom) and move up the pipeline until they're handled or until they error out.
    """
    if stage.previous:
        logger.debug(
            "{}({}): pushing event up to {}".format(stage.name, event.name, stage.previous.name)
        )
        stage.previous.handle_pipeline_event(event)
    else:
        logger.error("{}({}): Error: unhandled event".format(stage.name, event.name))
        error = NotImplementedError(
            "{} unhandled at {} stage with no previous stage".format(event.name, stage.name)
        )
        unhandled_exceptions.exception_caught_in_background_thread(error)
