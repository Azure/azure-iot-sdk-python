# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging
import abc
import six
import uuid
from six.moves import queue
from . import pipeline_events_base
from . import pipeline_ops_base
from . import operation_flow
from . import pipeline_thread
from azure.iot.device.common import unhandled_exceptions

logger = logging.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class PipelineStage(object):
    """
    Base class representing a stage in the processing pipeline.  Each stage is responsible for receiving
    PipelineOperation objects from the top, possibly processing them, and possibly passing them down.  It
    is also responsible for receiving PipelineEvent objects from the bottom, possibly processing them, and
    possibly passing them up.

    Each PipelineStage in the pipeline, is expected to act on some well-defined set of PipelineOperation
    types and/or some set of PipelineEvent types.  If any stage does not act on an operation or event, it
    should pass it to the next stage (for operations) or the previous stage (for events).  In this way, the
    pipeline implements the "chain of responsibility" design pattern (Gamma, et.al. "Design Patterns".
    Addison Wesley. 1995), with each stage being responsible for implementing some "rule" or "policy" of the
    pipeline, and each stage being ignorant of the stages that are before or after it in the pipeline.

    Each stage in the pipeline should act on the smallest set of rules possible, thus making stages small
    and easily testable.  Complex logic should be the exception and not the rule, and complex stages should
    operate on the most generic type of operation possible, thus allowing us to re-use complex logic for
    multiple cases.  The best way to do this is with "converter" stages that convert a specific operation to
    a more general one and with other converter stages that convert general operations to more specific ones.

    An example of a specific-to-generic stage is UseSkAuthProviderStage which takes a specific operation
    (use an auth provider) and converts it into something more generic (here is your device_id, etc, and use
    this SAS token when connecting).

    An example of a generic-to-specific stage is IoTHubMQTTConverterStage which converts IoTHub operations
    (such as SendD2CMessageOperation) to MQTT operations (such as Publish).

    Each stage should also work in the broadest domain possible.  For example a generic stage (say
    "EnsureConnectionStage") that initiates a connection if any arbitrary operation needs a connection is more useful
    than having some MQTT-specific code that re-connects to the MQTT broker if the user calls Publish and
    there's no connection.

    One way to think about stages is to look at every "block of functionality" in your code and ask yourself
    "is this the one and only time I will need this code"?  If the answer is no, it might be worthwhile to
    implement that code in it's own stage in a very generic way.


    :ivar name: The name of the stage.  This is used primarily for logging
    :type name: str
    :ivar next: The next stage in the pipeline.  Set to None if this is the last stage in the pipeline.
    :type next: PipelineStage
    :ivar previous: The previous stage in the pipeline.  Set to None if this is the first stage in the pipeline.
    :type previous: PipelineStage
    :ivar pipeline_root: The first stage (root) of the pipeline.  This is useful if a stage wants to
      submit an operation to the pipeline starting at the root.  This type of behavior is uncommon but not
      unexpected.
    :type pipeline_root: PipelineStage
    """

    def __init__(self):
        """
        Initializer for PipelineStage objects.
        """
        self.name = self.__class__.__name__
        self.next = None
        self.previous = None
        self.pipeline_root = None

    @pipeline_thread.runs_on_pipeline_thread
    def run_op(self, op):
        """
        Run the given operation.  This is the public function that outside callers would call to run an
        operation.  Derived classes should override the private _execute_op function to implement
        stage-specific behavior.  When run_op returns, that doesn't mean that the operation has executed
        to completion.  Rather, it means that the pipeline has done something that will cause the
        operation to eventually execute to completion.  That might mean that something was sent over
        the network and some stage is waiting for a reply, or it might mean that the operation is sitting
        in a queue until something happens, or it could mean something entirely different.  The only
        thing you can assume is that the operation will _eventually_ complete successfully or fail, and the
        operation's callback will be called when that happens.

        :param PipelineOperation op: The operation to run.
        """
        logger.debug("{}({}): running".format(self.name, op.name))
        try:
            self._execute_op(op)
        except Exception as e:
            # This path is ONLY for unexpected errors. Expected errors should cause a fail completion
            # within ._execute_op()
            logger.error(msg="Unexpected error in {}._execute_op() call".format(self), exc_info=e)
            op.error = e
            operation_flow.complete_op(self, op)

    @abc.abstractmethod
    def _execute_op(self, op):
        """
        Abstract method to run the actual operation.  This function is implemented in derived classes
        and performs the actual work that any operation expects.  The default behavior for this function
        should be to forward the event to the next stage using operation_flow.pass_op_to_next_stage for any
        operations that a particular stage might not operate on.

        See the description of the run_op method for more discussion on what it means to "run" an operation.

        :param PipelineOperation op: The operation to run.
        """
        pass

    @pipeline_thread.runs_on_pipeline_thread
    def handle_pipeline_event(self, event):
        """
        Handle a pipeline event that arrives from the stage below this stage.  Derived
        classes should not override this function.  Any stage-specific handling of
        PipelineEvent objects should be implemented by overriding the private
        _handle_pipeline_event function in the derived stage.

        :param PipelineEvent event: The event that is being passed back up the pipeline
        """
        try:
            self._handle_pipeline_event(event)
        except Exception as e:
            logger.error(
                msg="Unexpected error in {}._handle_pipeline_event() call".format(self), exc_info=e
            )
            unhandled_exceptions.exception_caught_in_background_thread(e)

    @pipeline_thread.runs_on_pipeline_thread
    def _handle_pipeline_event(self, event):
        """
        Handle a pipeline event that arrives from the stage below this stage.  This
        is a function that is intended to be overridden in any stages that want to implement
        stage-specific handling of any events

        :param PipelineEvent event: The event that is being passed back up the pipeline
        """
        operation_flow.pass_event_to_previous_stage(self, event)

    @pipeline_thread.runs_on_pipeline_thread
    def on_connected(self):
        """
        Called by lower layers when the protocol client connects
        """
        if self.previous:
            self.previous.on_connected()

    @pipeline_thread.runs_on_pipeline_thread
    def on_disconnected(self):
        """
        Called by lower layers when the protocol client disconnects
        """
        if self.previous:
            self.previous.on_disconnected()


class PipelineRootStage(PipelineStage):
    """
    Object representing the root of a pipeline.  This is where the functions to build
    the pipeline exist.  This is also where clients can add event handlers to receive
    events from the pipeline.

    :ivar on_pipeline_event_handler: Handler which can be set by users of the pipeline to
      receive PipelineEvent objects.  This is how users receive any "unsolicited"
      events from the pipeline (such as C2D messages).  This function is called with
      a PipelineEvent object every time any such event occurs.
    :type on_pipeline_event_handler: Function
    :ivar on_connected_handler: Handler which can be set by users of the pipeline to
      receive events every time the underlying transport connects
    :type on_connected_handler: Function
    :ivar on_disconnected_handler: Handler which can be set by users of the pipeline to
      receive events every time the underlying transport disconnects
    :type on_disconnected_handler: Function
    """

    def __init__(self):
        super(PipelineRootStage, self).__init__()
        self.on_pipeline_event_handler = None
        self.on_connected_handler = None
        self.on_disconnected_handler = None
        self.connected = False

    def run_op(self, op):
        op.callback = pipeline_thread.invoke_on_callback_thread_nowait(op.callback)
        pipeline_thread.invoke_on_pipeline_thread(super(PipelineRootStage, self).run_op)(op)

    @pipeline_thread.runs_on_pipeline_thread
    def _execute_op(self, op):
        """
        run the operation.  At the root, the only thing to do is to pass the operation
        to the next stage.

        :param PipelineOperation op: Operation to run.
        """
        operation_flow.pass_op_to_next_stage(self, op)

    def append_stage(self, new_next_stage):
        """
        Add the next stage to the end of the pipeline.  This is the function that callers
        use to build the pipeline by appending stages.  This function returns the root of
        the pipeline so that calls to this function can be chained together.

        :param PipelineStage new_next_stage: Stage to add to the end of the pipeline
        :returns: The root of the pipeline.
        """
        old_tail = self
        while old_tail.next:
            old_tail = old_tail.next
        old_tail.next = new_next_stage
        new_next_stage.previous = old_tail
        new_next_stage.pipeline_root = self
        return self

    @pipeline_thread.runs_on_pipeline_thread
    def _handle_pipeline_event(self, event):
        """
        Override of the PipelineEvent handler.  Because this is the root of the pipeline,
        this function calls the on_pipeline_event_handler to pass the event to the
        caller.

        :param PipelineEvent event: Event to be handled, i.e. returned to the caller
          through the handle_pipeline_event (if provided).
        """
        if self.on_pipeline_event_handler:
            pipeline_thread.invoke_on_callback_thread_nowait(self.on_pipeline_event_handler)(event)
        else:
            logger.warning("incoming pipeline event with no handler.  dropping.")

    @pipeline_thread.runs_on_pipeline_thread
    def on_connected(self):
        logger.info(
            "{}: on_connected.  on_connected_handler={}".format(
                self.name, self.on_connected_handler
            )
        )
        self.connected = True
        if self.on_connected_handler:
            pipeline_thread.invoke_on_callback_thread_nowait(self.on_connected_handler)()

    @pipeline_thread.runs_on_pipeline_thread
    def on_disconnected(self):
        logger.info(
            "{}: on_disconnected.  on_disconnected_handler={}".format(
                self.name, self.on_disconnected_handler
            )
        )
        self.connected = False
        if self.on_disconnected_handler:
            pipeline_thread.invoke_on_callback_thread_nowait(self.on_disconnected_handler)()


class EnsureConnectionStage(PipelineStage):
    """
    This stage is responsible for ensuring that the protocol is connected when
    it needs to be connected.
    """

    @pipeline_thread.runs_on_pipeline_thread
    def _execute_op(self, op):
        # Any operation that requires a connection can trigger a connection if
        # we're not connected.
        if op.needs_connection and not self.pipeline_root.connected:
            logger.info(
                "{}({}): Op needs connection.  Queueing this op and starting a ConnectionOperation".format(
                    self.name, op.name
                )
            )
            self._do_connect(op)

        # Finally, if this stage doesn't need to do anything else with this operation,
        # it just passes it down.
        else:
            operation_flow.pass_op_to_next_stage(self, op)

    @pipeline_thread.runs_on_pipeline_thread
    def _do_connect(self, op):
        """
        Start connecting the transport in response to some operation
        """
        # function that gets called after we're connected.
        @pipeline_thread.runs_on_pipeline_thread
        def on_connect_op_complete(op_connect):
            if op_connect.error:
                logger.info(
                    "{}({}): Connection failed.  Completing with failure because of connection failure: {}".format(
                        self.name, op.name, op_connect.error
                    )
                )
                op.error = op_connect.error
                operation_flow.complete_op(stage=self, op=op)
            else:
                logger.info(
                    "{}({}): connection is complete.  Continuing with op".format(self.name, op.name)
                )
                operation_flow.pass_op_to_next_stage(stage=self, op=op)

        # call down to the next stage to connect.
        logger.info("{}({}): calling down with Connect operation".format(self.name, op.name))
        operation_flow.pass_op_to_next_stage(
            self, pipeline_ops_base.ConnectOperation(callback=on_connect_op_complete)
        )


class SerializeConnectOpsStage(PipelineStage):
    """
    This stage is responsible for serializing connect, disconnect, and reconnect ops on
    the pipeline, such that only a single one of these ops can go past this stage at a
    time.  This way, we don't have to worry about cases like "what happens if we try to
    disconnect if we're in the middle of reconnecting."  This stage will wait for the
    reconnect to complete before letting the disconnect past.
    """

    def __init__(self):
        super(SerializeConnectOpsStage, self).__init__()
        self.queue = queue.Queue()
        self.blocked = False

    @pipeline_thread.runs_on_pipeline_thread
    def _execute_op(self, op):
        # If this stage is currently blocked (because we're waiting for a connection, etc,
        # to complete), we queue up all operations until after the connect completes.
        if self.blocked:
            logger.info(
                "{}({}): pipeline is blocked waiting for a prior connect/disconnect/reconnect to complete.  queueing.".format(
                    self.name, op.name
                )
            )
            self.queue.put_nowait(op)

        elif isinstance(op, pipeline_ops_base.ConnectOperation) and self.pipeline_root.connected:
            logger.info(
                "{}({}): Transport is already connected.  Completing early".format(
                    self.name, op.name
                )
            )
            operation_flow.complete_op(stage=self, op=op)

        elif (
            isinstance(op, pipeline_ops_base.DisconnectOperation)
            and not self.pipeline_root.connected
        ):
            logger.info(
                "{}({}): Transport is already disconnected.  Completing early".format(
                    self.name, op.name
                )
            )
            operation_flow.complete_op(stage=self, op=op)

        elif (
            isinstance(op, pipeline_ops_base.DisconnectOperation)
            or isinstance(op, pipeline_ops_base.ConnectOperation)
            or isinstance(op, pipeline_ops_base.ReconnectOperation)
        ):
            self._block(op)
            old_callback = op.callback

            @pipeline_thread.runs_on_pipeline_thread
            def on_operation_complete(op):
                logger.info(
                    "{}({}): complete.  Unblocking queue with error: {}".format(
                        self.name, op.name, op.error
                    )
                )
                op.callback = old_callback
                self._unblock(op, op.error)
                logger.info(
                    "{}({}): unblock is complete.  completing op that caused unblock".format(
                        self.name, op.name
                    )
                )
                operation_flow.complete_op(stage=self, op=op)

            op.callback = on_operation_complete
            operation_flow.pass_op_to_next_stage(stage=self, op=op)

        else:
            operation_flow.pass_op_to_next_stage(stage=self, op=op)

    @pipeline_thread.runs_on_pipeline_thread
    def _block(self, op):
        """
        block this stage while we're waiting for the connect/disconnect/reconnect operation to complete.
        """
        logger.info("{}({}): blocking".format(self.name, op.name))
        self.blocked = True

    @pipeline_thread.runs_on_pipeline_thread
    def _unblock(self, op, error):
        """
        Unblock this stage after the connect/disconnect/reconnect operation is complete.  This also means
        releasing all the operations that were queued up.
        """
        logger.info("{}({}): unblocking and releasing queued ops.".format(self.name, op.name))
        self.blocked = False
        logger.info(
            "{}({}): processing {} items in queue".format(self.name, op.name, self.queue.qsize())
        )
        # Loop through our queue and release all the blocked operations
        # Put a new Queue in self.queue because releasing ops might put them back in the
        # queue, especially if there's a ConnectOperation in the list of ops to release
        old_queue = self.queue
        self.queue = queue.Queue()
        while not old_queue.empty():
            op_to_release = old_queue.get_nowait()
            if error:
                # if we're unblocking the queue because something (like a connect operation) failed,
                # then we fail all of the blocked operations with the same error.
                logger.info(
                    "{}({}): failing {} op because of error".format(
                        self.name, op.name, op_to_release.name
                    )
                )
                op_to_release.error = error
                operation_flow.complete_op(self, op_to_release)
            else:
                logger.info(
                    "{}({}): releasing {} op.".format(self.name, op.name, op_to_release.name)
                )
                # call run_op directly here so operations go through this stage again (especiall connect/disconnect ops)
                self.run_op(op_to_release)


class CoordinateRequestAndResponseStage(PipelineStage):
    """
    Pipeline stage which is responsible for coordinating SendIotRequestAndWaitForResponseOperation operations.  For each
    SendIotRequestAndWaitForResponseOperation operation, this stage passes down a SendIotRequestOperation operation and waits for
    an IotResponseEvent event.  All other events are passed down unmodified.
    """

    def __init__(self):
        super(CoordinateRequestAndResponseStage, self).__init__()
        self.pending_responses = {}

    @pipeline_thread.runs_on_pipeline_thread
    def _execute_op(self, op):
        if isinstance(op, pipeline_ops_base.SendIotRequestAndWaitForResponseOperation):
            # Convert SendIotRequestAndWaitForResponseOperation operation into a SendIotRequestOperation operation
            # and send it down.  A lower level will convert the SendIotRequestOperation into an
            # actual protocol client operation.  The SendIotRequestAndWaitForResponseOperation operation will be
            # completed when the corresponding IotResponse event is received in this stage.

            request_id = str(uuid.uuid4())

            @pipeline_thread.runs_on_pipeline_thread
            def on_send_request_done(send_request_op):
                logger.info(
                    "{}({}): Finished sending {} request to {} resource {}".format(
                        self.name, op.name, op.request_type, op.method, op.resource_location
                    )
                )
                if send_request_op.error:
                    op.error = send_request_op.error
                    logger.info(
                        "{}({}): removing request {} from pending list".format(
                            self.name, op.name, request_id
                        )
                    )
                    del (self.pending_responses[request_id])
                    operation_flow.complete_op(self, op)
                else:
                    # request sent.  Nothing to do except wait for the response
                    pass

            logger.info(
                "{}({}): Sending {} request to {} resource {}".format(
                    self.name, op.name, op.request_type, op.method, op.resource_location
                )
            )

            logger.info(
                "{}({}): adding request {} to pending list".format(self.name, op.name, request_id)
            )
            self.pending_responses[request_id] = op

            new_op = pipeline_ops_base.SendIotRequestOperation(
                method=op.method,
                resource_location=op.resource_location,
                request_body=op.request_body,
                request_id=request_id,
                request_type=op.request_type,
                callback=on_send_request_done,
            )
            operation_flow.pass_op_to_next_stage(self, new_op)

        else:
            operation_flow.pass_op_to_next_stage(self, op)

    @pipeline_thread.runs_on_pipeline_thread
    def _handle_pipeline_event(self, event):
        if isinstance(event, pipeline_events_base.IotResponseEvent):
            # match IotResponseEvent events to the saved dictionary of SendIotRequestAndWaitForResponseOperation
            # operations which have not received responses yet.  If the operation is found,
            # complete it.

            logger.info(
                "{}({}): Handling event with request_id {}".format(
                    self.name, event.name, event.request_id
                )
            )
            if event.request_id in self.pending_responses:
                op = self.pending_responses[event.request_id]
                del (self.pending_responses[event.request_id])
                op.status_code = event.status_code
                op.response_body = event.response_body
                logger.info(
                    "{}({}): Completing {} request to {} resource {} with status {}".format(
                        self.name,
                        op.name,
                        op.request_type,
                        op.method,
                        op.resource_location,
                        op.status_code,
                    )
                )
                operation_flow.complete_op(self, op)
            else:
                logger.warning(
                    "{}({}): request_id {} not found in pending list.  Nothing to do.  Dropping".format(
                        self.name, event.name, event.request_id
                    )
                )
        else:
            operation_flow.pass_event_to_previous_stage(self, event)
