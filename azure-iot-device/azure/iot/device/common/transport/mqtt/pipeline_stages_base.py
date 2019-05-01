# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging
import abc
import six
import sys
from six.moves import queue
from . import pipeline_ops_base

logger = logging.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class PipelineStage(object):
    """
    Base class representing a stage in the processing pipeline.  Each stage is responsible for receiving
    PipelineOperation objects from the top, possibly processing them, and possibly passing them down.  It
    is also responsible for receiving PipelineEvent objects from the bottom, possibly processing them, and
    possibly passing them up.  In both cases (PipelineOperation and PipelineEvent), the default behavior
    should be to pass along an operation or event that you don't handle.
    """

    def __init__(self):
        self.name = self.__class__.__name__
        self.next = None
        self.previous = None
        self.pipeline_root = None

    def run_op(self, op):
        """
        Run the given operation.  This is the public function that outside callers would call to run an
        operation.  Derived classes should override the private _run_op function to implement
        stage-specific behavior.
        """
        logger.info("{}({}): running".format(self.name, op.name))
        try:
            self._run_op(op)
        except:  # noqa: E722 do not use bare 'except'
            _, e, _ = sys.exc_info()
            logger.error(msg="Error in {}._run_op() call".format(self), exc_info=e)
            op.error = e
            self.complete_op(op)

    def run_ops_serial(self, *args, **kwargs):
        """
        Run the operations passed in *args in a serial manner, such that each operation waits for the
        previous operation to be completed before running.

        In normal operation, the first operation will be passed down to the next stage to run.  That
        stage will process it, pass it down, or whatever needs to be done to handle that operation.
        After that operation travels all the way down the pipeline and the result is returned to the
        callback, the next operation will be passed down and execute to completion.  When the second
        operation's callback is called, the third operation will begin, and so on.  After all of the
        operations run, the callback passed into run_ops_serial will be called to return the "final
        result" back to the caller.

        The finally_op parameter is used to provide an operation that will always be run as the last
        operation, even if one of the earlier operation fails.

        If an operation fails, the operations that follow will not be run. However, the operation
        passed using the finally_op will be run.

        After all operations and the finally_op (if provided) are run, then the function passed in
        the callback parameter will be called, passing the last operation executed (in the event of
        success) or the failing operation (in the event of failure).
        """
        worklist = queue.Queue()
        for arg in args:
            worklist.put_nowait(arg)
        finally_op = kwargs.get("finally_op", None)
        callback = kwargs.get("callback", None)

        if len([x for x in kwargs.keys() if x not in ["finally_op", "callback"]]):
            raise TypeError("finally_op and callback are the only allowed keyword args")

        def on_last_op_done(last_op):
            if finally_op:

                def on_finally_done(finally_op):
                    if not finally_op.error:
                        finally_op.error = last_op.error
                    try:
                        callback(finally_op)
                    except:  # noqa: E722 do not use bare 'except'
                        _, e, _ = sys.exc_info()
                        logger.error(
                            msg="Unhandled error calling back inside {}.run_ops_serial() after {} complete".format(
                                self.name, finally_op.name
                            ),
                            exc_info=e,
                        )
                        self.pipeline_root.unhandled_error_handler(e)

                finally_op.callback = on_finally_done
                self.continue_op(finally_op)
            else:
                try:
                    callback(last_op)
                except:  # noqa: E722 do not use bare 'except'
                    _, e, _ = sys.exc_info()
                    logger.error(
                        msg="Unhandled error calling back inside {}.run_ops_serial() after {} complete".format(
                            self.name, last_op.name
                        ),
                        exc_info=e,
                    )
                    self.pipeline_root.unhandled_error_handler(e)

        def on_op_done(completed_op):
            logger.info(
                "{}({}): complete in run_ops_serial. {} items left".format(
                    self.name, completed_op.name, worklist.qsize()
                )
            )
            if completed_op.error:
                on_last_op_done(completed_op)
            else:
                if worklist.empty():
                    on_last_op_done(completed_op)
                else:
                    next_op = worklist.get_nowait()
                    next_op.callback = on_op_done
                    self.run_op(next_op)

        first_op = worklist.get_nowait()
        first_op.callback = on_op_done
        self.run_op(first_op)

    @abc.abstractmethod
    def _run_op(self, op):
        """
        Abstract method to run the actual operation.  Implemented in derived classes.
        """
        pass

    def handle_pipeline_event(self, event):
        """
        Handle a pipeline event that arrives from the stage below this stage.  This
        is the function that is called from outside this object.  Stages which are
        derived from this Class should implement specific event handling code in the
        private _handle_pipeline_event function.
        """
        try:
            self._handle_pipeline_event(event)
        except:  # noqa: E722 do not use bare 'except'
            _, e, _ = sys.exc_info()
            logger.error(
                msg="Error in %s._handle_pipeline_event call".format(self.name), exc_info=e
            )
            self.pipeline_root.unhandled_error_handler(e)

    def _handle_pipeline_event(self, event):
        """
        Function which actually handles an event.  If a stage wants to handle events,
        it should override this function.
        """
        if self.previous:
            self.previous.handle_pipeline_event(event)

    def continue_op(self, op):
        """
        Helper function to continue a given operation by passing it to the next stage
        in the pipeline.  If there is no next stage in the pipeline, this function
        will fail the operation and call complete_op to return the failure back up the
        pipeline.  If the operation is already in an error state, this function will
        complete the operation in order to return that error to the caller.
        """
        if op.error:
            logger.error("{}({}): op has error.  completing.".format(self.name, op.name))
            self.complete_op(op)
        elif not self.next:
            logger.error("{}({}): no next stage.  completing with error".format(self.name, op.name))
            op.error = NotImplementedError()
            self.complete_op(op)
        else:
            logger.error("{}({}): passing to next stage.".format(self.name, op.name))
            self.next.run_op(op)

    def complete_op(self, op):
        """
        Helper function to complete an operation by calling its callback function thus
        returning the result of the operation back up the pipeline.
        """
        logger.info(
            "{}({}): completing {} error".format(
                self.name, op.name, "with" if op.error else "without"
            )
        )
        try:
            op.callback(op)
        except:  # noqa: E722 do not use bare 'except'
            _, e, _ = sys.exc_info()
            logger.error(
                msg="Unhandled error calling back inside {}.complete_op() after {} complete".format(
                    self.name, op.name
                ),
                exc_info=e,
            )
            self.pipeline_root.unhandled_error_handler(e)

    def continue_with_different_op(self, original_op, new_op):
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

        logger.info(
            "{}({}): continuing with {} op".format(self.name, original_op.name, new_op.name)
        )

        def new_op_complete(op):
            logger.info(
                "{}({}): completing with result from {}".format(
                    self.name, original_op.name, new_op.name
                )
            )
            original_op.error = new_op.error
            self.complete_op(original_op)

        new_op.callback = new_op_complete
        self.continue_op(new_op)

    def on_connected(self):
        """
        Called by lower layers when the transport connects
        """
        if self.previous:
            self.previous.on_connected()

    def on_disconnected(self):
        """
        Called by lower layers when the transport disconnects
        """
        if self.previous:
            self.previous.on_disconnected()


class PipelineRoot(PipelineStage):
    """
    Object representing the root of a pipeline.  This is where the functions to build
    the pipeline exist.  This is also where clients can add event handlers to receive
    events from the pipeline.
    """

    def __init__(self):
        super(PipelineRoot, self).__init__()
        self.on_pipeline_event = None

    def _run_op(self, op):
        """
        run the operation.  At the root, the only thing to do is to pass the operation
        to the next stage.
        """
        self.continue_op(op)

    def append_stage(self, new_next_stage):
        """
        Add the next stage to the end of the pipeline.
        """
        old_tail = self
        while old_tail.next:
            old_tail = old_tail.next
        old_tail.next = new_next_stage
        new_next_stage.previous = old_tail
        new_next_stage.pipeline_root = self
        return self

    def unhandled_error_handler(self, error):
        """
        Handler for errors that happen which cannot be tied to a specific operation.
        This is still a tentative implimentation and masy be replaced by
        some other mechanism as details on behavior are finalized.
        """
        # TODO: decide how to pass this error to the app
        # TODO: if there's an error in the app handler, print it and exit
        pass

    def _handle_pipeline_event(self, event):
        if self.on_pipeline_event:
            # already protected by try/except in handle_pipeline_event()
            self.on_pipeline_event(event)
        else:
            logger.warning("incoming pipeline event with no handler.  dropping.")


class EnsureConnection(PipelineStage):
    """
    This stage is responsible for ensuring that the transport is connected when
    it needs to be connected, and it's responsible for queueing operations
    while we're waiting for the connect operation to complete.

    Operations Handled:
    * Connect
    * Disconnect
    * all operations with needs_connection set to True (connects if necessary)
    * all operations (queues while waiting for connection)

    Operations Produced:
    * Connect

    Note: this stage will likely be replaced by a more full-featured stage to handle
    other "block while we're setting something up" operations, such as subscribing to
    twin responses.  That is another example where we want to ensure some state and block
    requests until that state is achieved.
    """

    def __init__(self):
        super(EnsureConnection, self).__init__()
        self.connected = False
        self.queue = queue.Queue()
        self.blocked = False

    def _run_op(self, op):
        # If this stage is currently blocked (because we're waiting for a connection
        # to complete, we queue up all operations until after the connect completes.
        if self.blocked:
            logger.info(
                "{}({}): pipeline is blocked waiting for connect.  queueing.".format(
                    self.name, op.name
                )
            )
            self.queue.put_nowait(op)

        # If we get a request to connect, we either complete immediately (if we're already
        # connected) or we do the connect operation, which is pulled out into a helper
        # function because starting the connection also means blocking this stage until
        # the connect is complete.
        elif isinstance(op, pipeline_ops_base.Connect):
            if self.connected:
                logger.info(
                    "{}({}): transport is already conencted.  completing early.".format(
                        self.name, op.name
                    )
                )
                self.complete_op(op)
            else:
                self._do_connect(op)

        # If we get a request to disconnect, we either complete the request immediately
        # (if we're already disconencted) or we pass the disconnect request down.
        elif isinstance(op, pipeline_ops_base.Disconnect):
            if not self.connected:
                logger.info(
                    "{}({}): transport is already disconencted.  completing early.".format(
                        self.name, op.name
                    )
                )
                self.complete_op(op)
            else:
                self.continue_op(op)

        # Any other operation that requires a connection can trigger a connection if
        # we're not connected.
        elif op.needs_connection and not self.connected:
            self._do_connect(op)

        # Finally, if this stage doesn't need to do anything else with this operation,
        # it just passes it down.
        else:
            self.continue_op(op)

    def _block(self, op):
        """
        block this stage while we're waiting for the connection to complete.
        """
        logger.info("{}({}): enabling block".format(self.name, op.name))
        self.blocked = True

    def _unblock(self, op, error):
        """
        Unblock this stage after the connection is complete.  This also means
        releasing all the queued up operations that we were waiting for the
        connect operation to complete.
        """
        logger.info("{}({}): disabling block and releasing queued ops.".format(self.name, op.name))
        self.blocked = False
        logger.info(
            "{}({}): processing {} items in queue".format(self.name, op.name, self.queue.qsize())
        )
        # loop through our queue and release all the blocked operations
        while not self.queue.empty():
            op_to_release = self.queue.get_nowait()
            if error:
                # if we're unblocking the queue because something (like a connect operation) failed,
                # then we fail all of the blocked operations with the same error.
                logger.info(
                    "{}({}): failing {} op because of error".format(
                        self.name, op.name, op_to_release.name
                    )
                )
                op_to_release.error = error
                self.complete_op(op_to_release)
            else:
                # when we release, go back through this stage again to make sure requirements are _really_ satisfied.
                # this also pre-maturely completes ops that might now be satisfied.
                logger.info(
                    "{}({}): releasing {} op.".format(self.name, op.name, op_to_release.name)
                )
                self.run_op(op_to_release)

    def _do_connect(self, op):
        """
        Start connecting the transport in response to some operation (which may or may not be a Connect operation)
        """
        # first, we block all future operations queue while we're connecting
        self._block(op=op)

        # If we're connecting as a side-effect of some other operation (that is not Connect), then we queue
        # that operation to run after the connection is complete.
        if not isinstance(op, pipeline_ops_base.Connect):
            logger.info("{}({}): queueing until connection complete".format(self.name, op.name))
            self.queue.put_nowait(op)

        # function that gets called after we're connected.
        def on_connected(op_connect):
            logger.info("{}({}): connection is complete".format(self.name, op.name))
            # if we're connecting because some layer above us asked us to connect, we complete that operation
            # once the connection is established.
            if isinstance(op, pipeline_ops_base.Connect):
                op.error = op_connect.error
                self.complete_op(op)
            # and, no matter what, we always unblock the stage when we're done connecting.
            self._unblock(op=op, error=op_connect.error)

        # call down to the next stage to connect.  We don't use continue_with_different_op because we have
        # extra code that needs to run (unblocking the queue) when the connect is complete and
        # continue_with_different_op can't do that.
        logger.info("{}({}): calling down with Connect operation".format(self.name, op.name))
        self.continue_op(pipeline_ops_base.Connect(callback=on_connected))

    def on_connected(self):
        self.connected = True
        PipelineStage.on_connected(self)

    def on_disconnected(self):
        self.connected = False
        PipelineStage.on_disconnected(self)
