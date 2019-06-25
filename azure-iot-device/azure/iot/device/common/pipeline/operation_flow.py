# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging
import sys

from six.moves import queue

logger = logging.getLogger(__name__)


def run_ops_in_serial(stage, *args, **kwargs):
    """
    Run the operations passed in *args in a serial manner, such that each operation waits for the
    previous operation to be completed before running.

    In normal operation, the first operation will be passed down to the next stage to run.  That
    stage will process it, pass it down, or whatever needs to be done to handle that operation.
    After that operation travels all the way down the pipeline and the result of the operation is
    returned via the operation's callback, the next operation will be passed down and execute.
    When the second operation's callback is called, the third operation will begin, and so on.
    After all of the operations run, the callback passed into run_ops_serial will be called to
    return the "final result" back to the caller.

    The finally_op parameter is used to provide an operation that will always be run as the last
    operation, even if one of the earlier operation fails.

    If an operation fails, the operations in *args that follow will not be run. However, the
    operation passed using the finally_op will be run.

    After all operations and the finally_op (if provided) are run, then the function passed in
    the callback parameter will be called, passing the last operation executed (in the event of
    success) or the failing operation (in the event of failure).

    :param PipelineStage stage: stage to run these operations on
    :param PipelineOperation[] *args: Operations to run serially.  These operations will be run
      one-after-another which each operation only running after the previous operations have all
      run.  If one of these operations fail, all subsequent operations will not execute and the
      failed operation will be passed as a parameter to the callback with the error attribute
      set to the cause of the failure.
    :param PipelineOperation finally_op: Operation to run last.  This will be called regardless
      of success or failure of the operations passed in *args
    :param Function callback: Callback to execute when all operations have completed.  The last
      operation executed will be passed as the parameter to this function.
    """
    worklist = queue.Queue()
    for arg in args:
        worklist.put_nowait(arg)
    finally_op = kwargs.get("finally_op", None)
    callback = kwargs.get("callback", None)

    if len([x for x in kwargs.keys() if x not in ["finally_op", "callback"]]):
        raise TypeError("finally_op and callback are the only allowed keyword args")
    if not callback:
        raise TypeError("callback is required")

    def on_last_op_done(last_op):
        if finally_op:

            def on_finally_done(finally_op):
                logger.info(
                    "{}({}):run_ops_serial: finally_op done.".format(stage.name, finally_op.name)
                )
                if last_op.error:
                    logger.info(
                        "{}({}):run_ops_serial: copying error from {}.".format(
                            stage.name, finally_op.name, last_op.name
                        )
                    )
                    finally_op.error = last_op.error
                try:
                    logger.info(
                        "{}({}):run_ops_serial: calling back after finally_op.".format(
                            stage.name, finally_op.name
                        )
                    )
                    callback(finally_op)
                except Exception as e:
                    logger.error(
                        msg="{}({}):run_ops_serial: Unhandled error in callback".format(
                            stage.name, finally_op.name
                        ),
                        exc_info=e,
                    )
                    stage.pipeline_root.unhandled_error_handler(e)

            finally_op.callback = on_finally_done
            logger.info(
                "{}({}):run_ops_serial: running finally_op.".format(stage.name, last_op.name)
            )
            pass_op_to_next_stage(stage, finally_op)
        else:
            try:
                logger.info(
                    "{}({}):run_ops_serial: no finally_op.  calling back.".format(
                        stage.name, last_op.name
                    )
                )
                callback(last_op)
            except Exception as e:
                logger.error(
                    msg="{}({}):run_ops_serial: Unhandled error in callback".format(
                        stage.name, last_op.name
                    ),
                    exc_info=e,
                )
                stage.pipeline_root.unhandled_error_handler(e)

    def on_op_done(completed_op):
        logger.info(
            "{}({}):run_ops_serial: completed. {} items left".format(
                stage.name, completed_op.name, worklist.qsize()
            )
        )
        if completed_op.error:
            logger.info(
                "{}({}):run_ops_serial: completed with failure. skipping last {} ops".format(
                    stage.name, completed_op.name, worklist.qsize()
                )
            )
            on_last_op_done(completed_op)
        else:
            if worklist.empty():
                logger.info(
                    "{}({}):run_ops_serial: last op succeeded.".format(
                        stage.name, completed_op.name
                    )
                )
                on_last_op_done(completed_op)
            else:
                logger.info(
                    "{}({}):run_ops_serial: op succeeded. running next op in list.".format(
                        stage.name, completed_op.name
                    )
                )
                next_op = worklist.get_nowait()
                next_op.callback = on_op_done
                pass_op_to_next_stage(stage, next_op)

    first_op = worklist.get_nowait()
    first_op.callback = on_op_done
    logger.info("{}({}):run_ops_serial: starting first op.".format(stage.name, first_op.name))
    pass_op_to_next_stage(stage, first_op)


def delegate_to_different_op(stage, original_op, new_op):
    """
    Continue an operation using a new operation.  This means that the new operation
    will be passed down the pipeline (starting at the next stage). When that new
    operation completes, the original operation will also complete.  In this way,
    a stage can accept one type of operation and, effectively, change that operation
    into a different type of operation before passing it to the next stage.

    This is useful when a generic operation (such as "enable feature") needs to be
    converted into a more specific operation (such as "subscribe to mqtt topic").
    In that case, a stage's _run_op function would call this function passing in
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

    logger.info("{}({}): continuing with {} op".format(stage.name, original_op.name, new_op.name))

    def new_op_complete(op):
        logger.info(
            "{}({}): completing with result from {}".format(
                stage.name, original_op.name, new_op.name
            )
        )
        original_op.error = new_op.error
        complete_op(stage, original_op)

    new_op.callback = new_op_complete
    pass_op_to_next_stage(stage, new_op)


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
        logger.info("{}({}): passing to next stage.".format(stage.name, op.name))
        stage.next.run_op(op)


def complete_op(stage, op):
    """
    Helper function to complete an operation by calling its callback function thus
    returning the result of the operation back up the pipeline.  This is perferred to
    calling the operation's callback directly as it provides several layers of protection
    (such as a try/except wrapper) which are strongly advised.
    """
    logger.info(
        "{}({}): completing {} error".format(stage.name, op.name, "with" if op.error else "without")
    )
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
        stage.pipeline_root.unhandled_error_handler(e)


def pass_event_to_previous_stage(stage, event):
    """
    Helper function to pass an event to the previous stage of the pipeline.  This is the default
    behavior of events while traveling through the pipeline. They start somewhere (maybe the
    bottom) and move up the pipeline until they're handled or until they error out.
    """
    if stage.previous:
        logger.info(
            "{}({}): pushing event up to {}".format(stage.name, event.name, stage.previous.name)
        )
        stage.previous.handle_pipeline_event(event)
    else:
        logger.error("{}({}): Error: unhandled event".format(stage.name, event.name))
        error = NotImplementedError(
            "{} unhandled at {} stage with no previous stage".format(event.name, stage.name)
        )
        stage.pipeline_root.unhandled_error_handler(error)
