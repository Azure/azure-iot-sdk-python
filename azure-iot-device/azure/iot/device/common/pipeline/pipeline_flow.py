# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging
import sys
from . import pipeline_thread
from azure.iot.device.common import handle_exceptions
from .pipeline_exceptions import PipelineError

from six.moves import queue

logger = logging.getLogger(__name__)


class PipelineFlow(object):
    @pipeline_thread.runs_on_pipeline_thread
    def _send_worker_op_down(self, worker_op, op):
        """
        Continue an operation using a new worker operation.  This means that the new operation
        will be passed down the pipeline (starting at the next stage). When that new
        operation completes, the original operation will be completed.  In this way,
        a stage can accept one type of operation and, effectively, change that operation
        into a different type of operation before passing it to the next stage.

        This is useful when a generic operation (such as "enable feature") needs to be
        converted into a more specific operation (such as "subscribe to mqtt topic").
        In that case, a stage's _execute_op function would call this function passing in
        the original "enable feature" op and the new "subscribe to mqtt topic"
        op.  This function will pass the "subscribe" down. When the "subscribe" op
        is completed, this function will cause the original op to complete.

        This function is only really useful if there is no data returned in the
        worker_op that that needs to be copied back into the original_op before
        completing it.  If data needs to be copied this way, some other method needs
        to be used.  (or a "copy data back" function needs to be added to this function
        as an optional parameter.)

        :param PipelineOperation op: Operation that is being continued using a
          different op.  This is most likely the operation that is currently being handled
          by the stage.  This operation is not actually continued, in that it is not
          actually passed down the pipeline.  Instead, the original_op operation is
          effectively paused while we wait for the worker_op operation to complete.  When
          the worker_op operation completes, the original_op operation will also be completed.
        :param PipelineOperation worker_op: Operation that is being passed down the pipeline
          to effectively continue the work represented by the original op.  This is most likely
          a different type of operation that is able to accomplish the intention of the
          original op in a way that is more specific than the original op.
        """

        logger.debug("{}({}): continuing with {} op".format(self.name, op.name, worker_op.name))

        @pipeline_thread.runs_on_pipeline_thread
        def worker_op_complete(worker_op, error):
            logger.debug(
                "{}({}): completing with result from {}".format(self.name, op.name, worker_op.name)
            )
            self._complete_op(op, error=error)

        worker_op.callback = worker_op_complete
        self._send_op_down(worker_op)

    @pipeline_thread.runs_on_pipeline_thread
    def _send_op_down(self, op):
        """
        Helper function to continue a given operation by passing it to the next stage
        in the pipeline.  If there is no next stage in the pipeline, this function
        will fail the operation and call _complete_op to return the failure back up the
        pipeline.

        :param PipelineOperation op: Operation which is being passed on
        """
        if not self.next:
            logger.error("{}({}): no next stage.  completing with error".format(self.name, op.name))
            error = PipelineError(
                "{} not handled after {} stage with no next stage".format(op.name, self.name)
            )
            self._complete_op(op, error=error)
        else:
            logger.debug("{}({}): passing to next stage.".format(self.name, op.name))
            self.next.run_op(op)

    @pipeline_thread.runs_on_pipeline_thread
    def _complete_op(self, op, error=None):
        """
        Helper function to complete an operation by calling its callback function thus
        returning the result of the operation back up the pipeline.  This is perferred to
        calling the operation's callback directly as it provides several layers of protection
        (such as a try/except wrapper) which are strongly advised.
        """
        if error:
            logger.error("{}({}): completing with error {}".format(self.name, op.name, error))
        else:
            logger.debug("{}({}): completing without error".format(self.name, op.name))

        if op.completed:
            logger.error(
                "{}({}): completing op that has already been completed!".format(self.name, op.name)
            )
            e = PipelineError(
                "Internal pipeline error: attempting to complete an already-completed operation: {}({})".format(
                    self.name, op.name
                )
            )
            handle_exceptions.handle_background_exception(e)
        else:
            op.completed = True
            self._send_completed_op_up(op, error)

    @pipeline_thread.runs_on_pipeline_thread
    def _send_completed_op_up(self, op, error=None):
        """
        Sends a previously-completed operation back up the pipeline, usually to the callback.
        This is used by _complete_op and it's also called from code in the stage itself inside
        an intercepted return (via _send_op_down_and_intercept_return).
        """
        if not op.completed:
            raise PipelineError(
                "Internal pipeline error: attempting to send an incomplete {} op up".format(op.name)
            )

        try:
            op.callback(op, error=error)
        except Exception as e:
            _, e, _ = sys.exc_info()
            logger.error(
                msg="Unhandled error calling back inside {}._complete_op() after {} complete".format(
                    self.name, op.name
                ),
                exc_info=e,
            )
            handle_exceptions.handle_background_exception(e)

    @pipeline_thread.runs_on_pipeline_thread
    def _send_event_up(self, event):
        """
        Helper function to pass an event to the previous stage of the pipeline.  This is the default
        behavior of events while traveling through the pipeline. They start somewhere (maybe the
        bottom) and move up the pipeline until they're handled or until they error out.
        """
        if self.previous:
            logger.debug(
                "{}({}): pushing event up to {}".format(self.name, event.name, self.previous.name)
            )
            self.previous.handle_pipeline_event(event)
        else:
            logger.error("{}({}): Error: unhandled event".format(self.name, event.name))
            error = PipelineError(
                "{} unhandled at {} stage with no previous stage".format(event.name, self.name)
            )
            handle_exceptions.handle_background_exception(error)

    @pipeline_thread.runs_on_pipeline_thread
    def _send_op_down_and_intercept_return(self, op, intercepted_return):
        """
        Function which sends an op down to the next stage in the pipeline and inserts an
        "intercepted_return" function in the return path of the op.  This way, a stage can
        continue processing of any op and use the intercepted_return function to  see the
        result of the op before returning it all the way to its original callback.  This is
        useful for stages that want to monitor the progress of ops, such as a TimeoutStage
        that needs to keep track of how long ops are running and when they complete.
        When that intercepted_return function is done with the op, it can use
        _send_completed_op_up() to finish processing the op.
        """
        old_callback = op.callback

        def new_callback(op, error):
            op.callback = old_callback
            intercepted_return(op=op, error=error)

        op.callback = new_callback
        self._send_op_down(op)
