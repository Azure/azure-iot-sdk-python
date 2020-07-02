# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging
import abc
import six
import sys
import time
import traceback
import uuid
import weakref
import threading
from six.moves import queue
from . import pipeline_events_base
from . import pipeline_ops_base, pipeline_ops_mqtt
from . import pipeline_thread
from . import pipeline_exceptions
from azure.iot.device.common import handle_exceptions, transport_exceptions
from azure.iot.device.common.callable_weak_method import CallableWeakMethod

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

    An example of a generic-to-specific stage is IoTHubMQTTTranslationStage which converts IoTHub operations
    (such as SendD2CMessageOperation) to MQTT operations (such as Publish).

    Each stage should also work in the broadest domain possible.  For example a generic stage (say
    "AutoConnectStage") that initiates a connection if any arbitrary operation needs a connection is more useful
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
        operation.  Derived classes should override the private _run_op function to implement
        stage-specific behavior.  When run_op returns, that doesn't mean that the operation has executed
        to completion.  Rather, it means that the pipeline has done something that will cause the
        operation to eventually execute to completion.  That might mean that something was sent over
        the network and some stage is waiting for a reply, or it might mean that the operation is sitting
        in a queue until something happens, or it could mean something entirely different.  The only
        thing you can assume is that the operation will _eventually_ complete successfully or fail, and the
        operation's callback will be called when that happens.

        :param PipelineOperation op: The operation to run.
        """
        try:
            self._run_op(op)
        except Exception as e:
            # This path is ONLY for unexpected errors. Expected errors should cause a fail completion
            # within ._run_op()

            # Do not use exc_info parameter on logger.error.  This casuses pytest to save the traceback which saves stack frames which shows up as a leak
            logger.error(msg="Unexpected error in {}._run_op() call".format(self))
            logger.error(traceback.format_exc())
            op.complete(error=e)

    @pipeline_thread.runs_on_pipeline_thread
    def _run_op(self, op):
        """
        Implementation of the stage-specific function of .run_op(). Override this method instead of
        .run_op() in child classes in order to change how a stage behaves when running an operation.

        See the description of the .run_op() method for more discussion on what it means to "run"
        an operation.

        :param PipelineOperation op: The operation to run.
        """
        self.send_op_down(op)

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
            # Do not use exc_info parameter on logger.error.  This casuses pytest to save the traceback which saves stack frames which shows up as a leak
            logger.error(msg="Unexpected error in {}._handle_pipeline_event() call".format(self))
            logger.error(traceback.format_exc())
            handle_exceptions.handle_background_exception(e)

    @pipeline_thread.runs_on_pipeline_thread
    def _handle_pipeline_event(self, event):
        """
        Handle a pipeline event that arrives from the stage below this stage.  This
        is a function that is intended to be overridden in any stages that want to implement
        stage-specific handling of any events

        :param PipelineEvent event: The event that is being passed back up the pipeline
        """
        self.send_event_up(event)

    @pipeline_thread.runs_on_pipeline_thread
    def send_op_down(self, op):
        """
        Helper function to continue a given operation by passing it to the next stage
        in the pipeline.  If there is no next stage in the pipeline, this function
        will fail the operation and call complete_op to return the failure back up the
        pipeline.

        :param PipelineOperation op: Operation which is being passed on
        """
        if not self.next:
            logger.error("{}({}): no next stage.  completing with error".format(self.name, op.name))
            error = pipeline_exceptions.PipelineError(
                "{} not handled after {} stage with no next stage".format(op.name, self.name)
            )
            op.complete(error=error)
        else:
            self.next.run_op(op)

    @pipeline_thread.runs_on_pipeline_thread
    def send_event_up(self, event):
        """
        Helper function to pass an event to the previous stage of the pipeline.  This is the default
        behavior of events while traveling through the pipeline. They start somewhere (maybe the
        bottom) and move up the pipeline until they're handled or until they error out.
        """
        if self.previous:
            self.previous.handle_pipeline_event(event)
        else:
            logger.error("{}({}): Error: unhandled event".format(self.name, event.name))
            error = pipeline_exceptions.PipelineError(
                "{} unhandled at {} stage with no previous stage".format(event.name, self.name)
            )
            handle_exceptions.handle_background_exception(error)


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

    def __init__(self, pipeline_configuration):
        super(PipelineRootStage, self).__init__()
        self.on_pipeline_event_handler = None
        self.on_connected_handler = None
        self.on_disconnected_handler = None
        self.connected = False
        self.pipeline_configuration = pipeline_configuration

    def run_op(self, op):
        # CT-TODO: make this more elegant
        op.callback_stack[0] = pipeline_thread.invoke_on_callback_thread_nowait(
            op.callback_stack[0]
        )
        pipeline_thread.invoke_on_pipeline_thread(super(PipelineRootStage, self).run_op)(op)

    def append_stage(self, new_stage):
        """
        Add the next stage to the end of the pipeline.  This is the function that callers
        use to build the pipeline by appending stages.  This function returns the root of
        the pipeline so that calls to this function can be chained together.

        :param PipelineStage new_stage: Stage to add to the end of the pipeline
        :returns: The root of the pipeline.
        """
        old_tail = self
        while old_tail.next:
            old_tail = old_tail.next
        old_tail.next = new_stage
        new_stage.previous = old_tail
        new_stage.pipeline_root = self
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
        if isinstance(event, pipeline_events_base.ConnectedEvent):
            logger.debug(
                "{}: ConnectedEvent received. Calling on_connected_handler".format(self.name)
            )
            self.connected = True
            if self.on_connected_handler:
                pipeline_thread.invoke_on_callback_thread_nowait(self.on_connected_handler)()

        elif isinstance(event, pipeline_events_base.DisconnectedEvent):
            logger.debug(
                "{}: DisconnectedEvent received. Calling on_disconnected_handler".format(self.name)
            )
            self.connected = False
            if self.on_disconnected_handler:
                pipeline_thread.invoke_on_callback_thread_nowait(self.on_disconnected_handler)()

        else:
            if self.on_pipeline_event_handler:
                pipeline_thread.invoke_on_callback_thread_nowait(self.on_pipeline_event_handler)(
                    event
                )
            else:
                logger.warning("incoming pipeline event with no handler.  dropping.")


# NOTE: This stage could be a candidate for being refactored into some kind of other
# pipeline-related structure. What's odd about it as a stage is that it doesn't really respond
# to operations or events so much as it spawns them on a timer.
# Perhaps some kind of... Pipeline Daemon?
class SasTokenRenewalStage(PipelineStage):
    # Amount of time, in seconds, prior to token expiration, when the renewal process will begin
    DEFAULT_TOKEN_RENEWAL_MARGIN = 120

    def __init__(self):
        super(SasTokenRenewalStage, self).__init__()
        self._token_renewal_timer = None

    @pipeline_thread.runs_on_pipeline_thread
    def _run_op(self, op):
        if (
            isinstance(op, pipeline_ops_base.InitializePipelineOperation)
            and self.pipeline_root.pipeline_configuration.sastoken
        ):
            self._start_renewal_timer()
            self.send_op_down(op)
        else:
            self.send_op_down(op)

    @pipeline_thread.runs_on_pipeline_thread
    def _cancel_token_renewal_timer(self):
        """Cancel and delete any pending renewal timer"""
        timer = self._token_renewal_timer
        self._token_renewal_timer = None
        if timer:
            logger.debug("Cancelling SAS Token renewal timer")
            timer.cancel()

    @pipeline_thread.runs_on_pipeline_thread
    def _start_renewal_timer(self):
        """Begin a renewal timer.
        When the timer expires, and the token is renewed, a new timer will be set"""
        self._cancel_token_renewal_timer()
        # NOTE: The assumption here is that the SasToken has just been refreshed, so there is
        # approximately 'TTL' seconds until expiration. In practice this could probably be off
        # a few seconds given processing time. We could make this more accurate if SasToken
        # objects had a live TTL value rather than a static one (i.e. "there are n seconds
        # remaining in the lifespan of this token", rather than "this token was intended to live
        # for n seconds")
        seconds_until_renewal = (
            self.pipeline_root.pipeline_configuration.sastoken.ttl
            - self.DEFAULT_TOKEN_RENEWAL_MARGIN
        )
        if seconds_until_renewal < 0:
            # This shouldn't happen in correct flow, but it's possible I suppose, if something goes
            # horribly awry elsewhere in the stack, or if we start allowing for custom
            # SasToken TTLs or custom Renewal Margins in the future
            logger.error("ERROR: SasToken TTL less than Renewal Margin")
            handle_exceptions.handle_background_exception(
                pipeline_exceptions.PipelineError("SasToken TTL less than Renewal Margin!")
            )
        else:
            logger.debug(
                "Scheduling SAS Token renewal for {} seconds in the future".format(
                    seconds_until_renewal
                )
            )
            self_weakref = weakref.ref(self)

            @pipeline_thread.runs_on_pipeline_thread
            def on_reauthorize_complete(op, error):
                this = self_weakref()
                if error:
                    logger.error(
                        "{}({}): reauthorize connection operation failed.  Error={}".format(
                            this.name, op.name, error
                        )
                    )
                    handle_exceptions.handle_background_exception(error)
                else:
                    logger.debug(
                        "{}({}): reauthorize connection operation is complete".format(
                            this.name, op.name
                        )
                    )

            @pipeline_thread.invoke_on_pipeline_thread_nowait
            def renew_token():
                this = self_weakref()
                logger.debug("Renewing SAS Token")
                # Renew the token
                sastoken = this.pipeline_root.pipeline_configuration.sastoken
                sastoken.refresh()
                # If the pipeline is already connected, send order to reauthorize the connection
                # now that token has been renewed
                if this.pipeline_root.connected:
                    this.send_op_down(
                        pipeline_ops_base.ReauthorizeConnectionOperation(
                            callback=on_reauthorize_complete
                        )
                    )
                # Once again, start a renewal timer
                this._start_renewal_timer()

            self._token_renewal_timer = threading.Timer(seconds_until_renewal, renew_token)
            self._token_renewal_timer.daemon = True
            self._token_renewal_timer.start()


class AutoConnectStage(PipelineStage):
    """
    This stage is responsible for ensuring that the protocol is connected when
    it needs to be connected.
    """

    @pipeline_thread.runs_on_pipeline_thread
    def _run_op(self, op):
        # Any operation that requires a connection can trigger a connection if
        # we're not connected.
        if op.needs_connection:
            if self.pipeline_root.connected:

                # If we think we're connected, we pass the op down, but we also check the result.
                # If we fail the op and we're not connected when we're done, we run through this
                # stage again to connect.  This is more common than you might think because the
                # *nix network stack won't detect a dropped connection until the client tries to
                # send something, so it's very possible that we're disconnected but don't know
                # it yet.

                @pipeline_thread.runs_on_pipeline_thread
                def check_for_connection_failure(op, error):
                    if error and not self.pipeline_root.connected:
                        logger.info(
                            "{}({}): op failed with {} and we're not conencted.  Re-submitting.".format(
                                self.name, op.name, error
                            )
                        )
                        op.halt_completion()
                        self.run_op(op)

                op.add_callback(check_for_connection_failure)
                logger.info(
                    "{}({}): Connected.  Sending down and adding callback to check result".format(
                        self.name, op.name
                    )
                )
                self.send_op_down(op)
            else:
                # operation needs connection, but pipeline is not connected.
                logger.debug(
                    "{}({}): Op needs connection.  Queueing this op and starting a ConnectionOperation".format(
                        self.name, op.name
                    )
                )
                self._do_connect(op)

        # Finally, if this stage doesn't need to do anything else with this operation,
        # it just passes it down.
        else:
            self.send_op_down(op)

    @pipeline_thread.runs_on_pipeline_thread
    def _do_connect(self, op):
        """
        Start connecting the transport in response to some operation
        """
        # Alias to avoid overload within the callback below
        # CT-TODO: remove the need for this with better callback semantics
        op_needs_complete = op

        # function that gets called after we're connected.
        @pipeline_thread.runs_on_pipeline_thread
        def on_connect_op_complete(op, error):
            if error:
                logger.info(
                    "{}({}): Connection failed.  Completing with failure because of connection failure: {}".format(
                        self.name, op_needs_complete.name, error
                    )
                )
                op_needs_complete.complete(error=error)
            else:
                logger.debug(
                    "{}({}): connection is complete.  Running op that triggered connection.".format(
                        self.name, op_needs_complete.name
                    )
                )
                # use run_op instead of send_op_down because we want the check_for_connection_failure logic
                # above to run.  Just because we just connected, it doesn't mean the connection won't drop
                # before we're done sending.  (This does actually happen in stress scenarios)
                self.run_op(op_needs_complete)

        # call down to the next stage to connect.
        logger.debug("{}({}): calling down with Connect operation".format(self.name, op.name))
        self.send_op_down(pipeline_ops_base.ConnectOperation(callback=on_connect_op_complete))


class ConnectionLockStage(PipelineStage):
    """
    This stage is responsible for serializing connect, disconnect, and reauthorize ops on
    the pipeline, such that only a single one of these ops can go past this stage at a
    time.  This way, we don't have to worry about cases like "what happens if we try to
    disconnect if we're in the middle of reauthorizing."  This stage will wait for the
    reauthorize to complete before letting the disconnect past.
    """

    def __init__(self):
        super(ConnectionLockStage, self).__init__()
        self.queue = queue.Queue()
        self.blocked = False

    @pipeline_thread.runs_on_pipeline_thread
    def _run_op(self, op):

        # If this stage is currently blocked (because we're waiting for a connection, etc,
        # to complete), we queue up all operations until after the connect completes.
        if self.blocked:
            logger.info(
                "{}({}): pipeline is blocked waiting for a prior connect/disconnect/reauthorize to complete.  queueing.".format(
                    self.name, op.name
                )
            )
            self.queue.put_nowait(op)

        elif isinstance(op, pipeline_ops_base.ConnectOperation) and self.pipeline_root.connected:
            logger.info(
                "{}({}): Transport is already connected.  Completing.".format(self.name, op.name)
            )
            op.complete()

        elif (
            isinstance(op, pipeline_ops_base.DisconnectOperation)
            and not self.pipeline_root.connected
        ):
            logger.info(
                "{}({}): Transport is already disconnected.  Completing.".format(self.name, op.name)
            )
            op.complete()

        elif (
            isinstance(op, pipeline_ops_base.DisconnectOperation)
            or isinstance(op, pipeline_ops_base.ConnectOperation)
            or isinstance(op, pipeline_ops_base.ReauthorizeConnectionOperation)
        ):
            self._block(op)

            @pipeline_thread.runs_on_pipeline_thread
            def on_operation_complete(op, error):
                if error:
                    logger.error(
                        "{}({}): op failed.  Unblocking queue with error: {}".format(
                            self.name, op.name, error
                        )
                    )
                else:
                    logger.debug(
                        "{}({}): op succeeded.  Unblocking queue".format(self.name, op.name)
                    )

                self._unblock(op, error)

            op.add_callback(on_operation_complete)
            self.send_op_down(op)

        else:
            self.send_op_down(op)

    @pipeline_thread.runs_on_pipeline_thread
    def _block(self, op):
        """
        block this stage while we're waiting for the connect/disconnect/reauthorize operation to complete.
        """
        logger.debug("{}({}): blocking".format(self.name, op.name))
        self.blocked = True

    @pipeline_thread.runs_on_pipeline_thread
    def _unblock(self, op, error):
        """
        Unblock this stage after the connect/disconnect/reauthorize operation is complete.  This also means
        releasing all the operations that were queued up.
        """
        logger.debug("{}({}): unblocking and releasing queued ops.".format(self.name, op.name))
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
                logger.error(
                    "{}({}): failing {} op because of error".format(
                        self.name, op.name, op_to_release.name
                    )
                )
                op_to_release.complete(error=error)
            else:
                logger.debug(
                    "{}({}): releasing {} op.".format(self.name, op.name, op_to_release.name)
                )
                # call run_op directly here so operations go through this stage again (especially connect/disconnect ops)
                self.run_op(op_to_release)


class CoordinateRequestAndResponseStage(PipelineStage):
    """
    Pipeline stage which is responsible for coordinating RequestAndResponseOperation operations.  For each
    RequestAndResponseOperation operation, this stage passes down a RequestOperation operation and waits for
    an ResponseEvent event.  All other events are passed down unmodified.
    """

    def __init__(self):
        super(CoordinateRequestAndResponseStage, self).__init__()
        self.pending_responses = {}

    @pipeline_thread.runs_on_pipeline_thread
    def _run_op(self, op):
        if isinstance(op, pipeline_ops_base.RequestAndResponseOperation):
            # Convert RequestAndResponseOperation operation into a RequestOperation operation
            # and send it down.  A lower level will convert the RequestOperation into an
            # actual protocol client operation.  The RequestAndResponseOperation operation will be
            # completed when the corresponding IotResponse event is received in this stage.

            request_id = str(uuid.uuid4())

            logger.debug(
                "{}({}): adding request {} to pending list".format(self.name, op.name, request_id)
            )
            self.pending_responses[request_id] = op

            self._send_request_down(request_id, op)

        else:
            self.send_op_down(op)

    @pipeline_thread.runs_on_pipeline_thread
    def _send_request_down(self, request_id, op):
        # Alias to avoid overload within the callback below
        # CT-TODO: remove the need for this with better callback semantics
        op_waiting_for_response = op

        @pipeline_thread.runs_on_pipeline_thread
        def on_send_request_done(op, error):
            logger.debug(
                "{}({}): Finished sending {} request to {} resource {}".format(
                    self.name,
                    op_waiting_for_response.name,
                    op_waiting_for_response.request_type,
                    op_waiting_for_response.method,
                    op_waiting_for_response.resource_location,
                )
            )
            if error:
                logger.debug(
                    "{}({}): removing request {} from pending list".format(
                        self.name, op_waiting_for_response.name, request_id
                    )
                )
                del (self.pending_responses[request_id])
                op_waiting_for_response.complete(error=error)
            else:
                # request sent.  Nothing to do except wait for the response
                pass

        logger.debug(
            "{}({}): Sending {} request to {} resource {}".format(
                self.name, op.name, op.request_type, op.method, op.resource_location
            )
        )

        new_op = pipeline_ops_base.RequestOperation(
            method=op.method,
            resource_location=op.resource_location,
            request_body=op.request_body,
            request_id=request_id,
            request_type=op.request_type,
            callback=on_send_request_done,
            query_params=op.query_params,
        )
        self.send_op_down(new_op)

    @pipeline_thread.runs_on_pipeline_thread
    def _handle_pipeline_event(self, event):
        if isinstance(event, pipeline_events_base.ResponseEvent):
            # match ResponseEvent events to the saved dictionary of RequestAndResponseOperation
            # operations which have not received responses yet.  If the operation is found,
            # complete it.

            logger.debug(
                "{}({}): Handling event with request_id {}".format(
                    self.name, event.name, event.request_id
                )
            )
            if event.request_id in self.pending_responses:
                op = self.pending_responses[event.request_id]
                del (self.pending_responses[event.request_id])
                op.status_code = event.status_code
                op.response_body = event.response_body
                op.retry_after = event.retry_after
                logger.debug(
                    "{}({}): Completing {} request to {} resource {} with status {}".format(
                        self.name,
                        op.name,
                        op.request_type,
                        op.method,
                        op.resource_location,
                        op.status_code,
                    )
                )
                op.complete()
            else:
                logger.warning(
                    "{}({}): request_id {} not found in pending list.  Nothing to do.  Dropping".format(
                        self.name, event.name, event.request_id
                    )
                )

        elif isinstance(event, pipeline_events_base.ConnectedEvent):
            """
            If we're reconnecting, send all pending requests down again.  This is necessary
            because any response that might have been sent by the service was possibly lost
            when the connection dropped.  The fact that the operation is still pending means
            that we haven't received the response yet.  Sending the request more than once
            will result in a reasonable response for all known operations, aside from extra
            processing on the server in the case of a re-sent provisioing request, or the
            appearance of a jump in $version attributes in the case of a lost twin PATCH
            operation.  Since we're reusing the same $rid, the server, of course, _could_
            recognize that this is a duplicate request, but the behavior in this case is
            undefined.
            """

            self.send_event_up(event)

            for request_id in self.pending_responses:
                logger.info(
                    "{}: ConnectedEvent: re-publishing request {}".format(self.name, request_id)
                )
                self._send_request_down(request_id, self.pending_responses[request_id])

        else:
            self.send_event_up(event)


class OpTimeoutStage(PipelineStage):
    """
    The purpose of the timeout stage is to add timeout errors to select operations

    The timeout_intervals attribute contains a list of operations to track along with
    their timeout values.  Right now this list is hard-coded but the operations and
    intervals will eventually become a parameter.

    For each operation that needs a timeout check, this stage will add a timer to
    the operation.  If the timer elapses, this stage will fail the operation with
    a PipelineTimeoutError.  The intention is that a higher stage will know what to
    do with that error and act accordingly (either return the error to the user or
    retry).

    This stage currently assumes that all timed out operation are just "lost".
    It does not attempt to cancel the operation, as Paho doesn't have a way to
    cancel an operation, and with QOS=1, sending a pub or sub twice is not
    catastrophic.

    Also, as a long-term plan, the operations that need to be watched for timeout
    will become an initialization parameter for this stage so that differet
    instances of this stage can watch for timeouts on different operations.
    This will be done because we want a lower-level timeout stage which can watch
    for timeouts at the MQTT level, and we want a higher-level timeout stage which
    can watch for timeouts at the iothub level.  In this way, an MQTT operation that
    times out can be retried as an MQTT operation and a higher-level IoTHub operation
    which times out can be retried as an IoTHub operation (which might necessitate
    redoing multiple MQTT operations).
    """

    def __init__(self):
        super(OpTimeoutStage, self).__init__()
        # use a fixed list and fixed intervals for now.  Later, this info will come in
        # as an init param or a retry poicy
        self.timeout_intervals = {
            pipeline_ops_mqtt.MQTTSubscribeOperation: 10,
            pipeline_ops_mqtt.MQTTUnsubscribeOperation: 10,
        }

    @pipeline_thread.runs_on_pipeline_thread
    def _run_op(self, op):
        if type(op) in self.timeout_intervals:
            # Create a timer to watch for operation timeout on this op and attach it
            # to the op.
            self_weakref = weakref.ref(self)

            @pipeline_thread.invoke_on_pipeline_thread_nowait
            def on_timeout():
                this = self_weakref()
                logger.info("{}({}): returning timeout error".format(this.name, op.name))
                op.complete(
                    error=pipeline_exceptions.PipelineTimeoutError(
                        "operation timed out before protocol client could respond"
                    )
                )

            logger.debug("{}({}): Creating timer".format(self.name, op.name))
            op.timeout_timer = threading.Timer(self.timeout_intervals[type(op)], on_timeout)
            op.timeout_timer.start()

            # Send the op down, but intercept the return of the op so we can
            # remove the timer when the op is done
            op.add_callback(self._clear_timer)
            logger.debug("{}({}): Sending down".format(self.name, op.name))
            self.send_op_down(op)
        else:
            self.send_op_down(op)

    @pipeline_thread.runs_on_pipeline_thread
    def _clear_timer(self, op, error):
        # When an op comes back, delete the timer and pass it right up.
        if op.timeout_timer:
            logger.debug("{}({}): Cancelling timer".format(self.name, op.name))
            op.timeout_timer.cancel()
            op.timeout_timer = None


class RetryStage(PipelineStage):
    """
    The purpose of the retry stage is to watch specific operations for specific
    errors and retry the operations as appropriate.

    Unlike the OpTimeoutStage, this stage will never need to worry about cancelling
    failed operations.  When an operation is retried at this stage, it is already
    considered "failed", so no cancellation needs to be done.
    """

    def __init__(self):
        super(RetryStage, self).__init__()
        # Retry intervals are hardcoded for now. Later, they come in as an
        # init param, probably via retry policy.
        self.retry_intervals = {
            pipeline_ops_mqtt.MQTTSubscribeOperation: 20,
            pipeline_ops_mqtt.MQTTUnsubscribeOperation: 20,
            pipeline_ops_mqtt.MQTTPublishOperation: 20,
        }
        self.ops_waiting_to_retry = []

    @pipeline_thread.runs_on_pipeline_thread
    def _run_op(self, op):
        """
        Send all ops down and intercept their return to "watch for retry"
        """
        if self._should_watch_for_retry(op):
            op.add_callback(self._do_retry_if_necessary)
            self.send_op_down(op)
        else:
            self.send_op_down(op)

    @pipeline_thread.runs_on_pipeline_thread
    def _should_watch_for_retry(self, op):
        """
        Return True if this op needs to be watched for retry.  This can be
        called before the op runs.
        """
        return type(op) in self.retry_intervals

    @pipeline_thread.runs_on_pipeline_thread
    def _should_retry(self, op, error):
        """
        Return True if this op needs to be retried.  This must be called after
        the op completes.
        """
        if error:
            if self._should_watch_for_retry(op):
                if isinstance(error, pipeline_exceptions.PipelineTimeoutError):
                    return True
        return False

    @pipeline_thread.runs_on_pipeline_thread
    def _do_retry_if_necessary(self, op, error):
        """
        Handler which gets called when operations are complete.  This function
        is where we check to see if a retry is necessary and set a "retry timer"
        which can be used to send the op down again.
        """
        if self._should_retry(op, error):
            self_weakref = weakref.ref(self)

            @pipeline_thread.invoke_on_pipeline_thread_nowait
            def do_retry():
                this = self_weakref()
                logger.info("{}({}): retrying".format(this.name, op.name))
                op.retry_timer.cancel()
                op.retry_timer = None
                this.ops_waiting_to_retry.remove(op)
                # Don't just send it down directly.  Instead, go through run_op so we get
                # retry functionality this time too
                this.run_op(op)

            interval = self.retry_intervals[type(op)]
            logger.warning(
                "{}({}): Op needs retry with interval {} because of {}.  Setting timer.".format(
                    self.name, op.name, interval, error
                )
            )

            # if we don't keep track of this op, it might get collected.
            op.halt_completion()
            self.ops_waiting_to_retry.append(op)
            op.retry_timer = threading.Timer(self.retry_intervals[type(op)], do_retry)
            op.retry_timer.start()

        else:
            if op.retry_timer:
                op.retry_timer.cancel()
                op.retry_timer = None


transient_connect_errors = [
    pipeline_exceptions.OperationCancelled,
    pipeline_exceptions.PipelineTimeoutError,
    pipeline_exceptions.OperationError,
    transport_exceptions.ConnectionFailedError,
    transport_exceptions.ConnectionDroppedError,
]


class ReconnectState(object):
    """
    Class which holds reconenct states as class variables.  Created to make code that reads like an enum without using an enum.

    WAITING_TO_RECONNECT: This stage is in a waiting period before reconnecting.  This state implies
    that the user wants the pipeline to be connected.  ie. After a successful connection, the
    state will change to LOGICALLY_CONNECTED

    LOGICALLY_CONNECTED: The client wants the pipeline to be connected.  This state is independent
    of the actual connection state since the pipeline could be logically connected but
    physically disconnected (this is a temporary condition though.  If we're logically connected
    and physically disconnected, then we should be waiting to reconnect.

    LOGICALLY_DISCONNECTED: The client does not want the pipeline to be connected or the pipeline had
    a permanent errors error and was forced to disconnect.  If the state is LOGICALLY_DISCONNECTED, then the pipeline
    should be physically disconnected since there is no reason to leave the pipeline connected in this state.
    """

    WAITING_TO_RECONNECT = "WAITING_TO_RECONNECT"
    LOGICALLY_CONNECTED = "LOGICALLY_CONNECTED"
    LOGICALLY_DISCONNECTED = "LOGICALLY_DISCONNECTED"


class ReconnectStage(PipelineStage):
    def __init__(self):
        super(ReconnectStage, self).__init__()
        self.reconnect_timer = None
        self.state = ReconnectState.LOGICALLY_DISCONNECTED
        # never_connected is important because some errors are handled differently the frist time
        # that we're connecting versus later connections.
        #
        # For example, if we get a "host not found" the first time we connect, it might mean:
        # 1. The connection string is wrong, in which case we don't want to retry
        # or it might mean:
        # 2. The connection string is correct and the host is just not available (network glitch?)
        #
        # If never_connected=True, we don't know if it's a permanent error (#1) or if it's
        # temporary (#2), so we take the conservative approach and assume it's a permanent error.
        #
        # If never_connected=False, we know that we've connected before, so the credentials were
        # valid at some point in the recent past.  We still don't know with certainty if it's
        # a temporary error or if it's permanent (the hub may have been deallocated), but it has
        # worked in the past, so we assume it's a temporary error.
        self.never_connected = True
        # connect delay is hardcoded for now.  Later, this comes from a retry policy
        self.reconnect_delay = 10
        self.waiting_connect_ops = []

    @pipeline_thread.runs_on_pipeline_thread
    def _run_op(self, op):
        if isinstance(op, pipeline_ops_base.ConnectOperation):
            if self.state == ReconnectState.WAITING_TO_RECONNECT:
                logger.info(
                    "{}({}): State is {}.  Adding to wait list".format(
                        self.name, op.name, self.state
                    )
                )
                self.waiting_connect_ops.append(op)
            else:
                logger.info(
                    "{}({}): State changes {}->LOGICALLY_CONNECTED.  Adding to wait list and sending new connect op down".format(
                        self.name, op.name, self.state
                    )
                )
                self.state = ReconnectState.LOGICALLY_CONNECTED
                # We don't send this op down.  Instead, we send a new connect op down.  This way,
                # we can distinguish between connect ops that we're handling (they go into the
                # queue) and connect ops that we are sending down.
                #
                # Once we finally connect, we only have to complete the ops in the queue and we
                # never have to worry about completing the op that we sent down.  The code is much
                # cleaner this way, especially when you take retries into account, trust me.
                self.waiting_connect_ops.append(op)
                self._send_new_connect_op_down()

        elif isinstance(op, pipeline_ops_base.DisconnectOperation):
            if self.state == ReconnectState.WAITING_TO_RECONNECT:
                logger.info(
                    "{}({}): State changes {}->LOGICALLY_DISCONNECTED.  Canceling waiting ops and sending disconnect down.".format(
                        self.name, op.name, self.state
                    )
                )
                self.state = ReconnectState.LOGICALLY_DISCONNECTED
                self._clear_reconnect_timer()
                self._complete_waiting_connect_ops(
                    pipeline_exceptions.OperationCancelled("Explicit disconnect invoked")
                )
                op.complete()

            else:
                logger.info(
                    "{}({}): State changes {}->LOGICALLY_DISCONNECTED.  Sending op down.".format(
                        self.name, op.name, self.state
                    )
                )
                self.state = ReconnectState.LOGICALLY_DISCONNECTED
                self.send_op_down(op)

        else:
            self.send_op_down(op)

    @pipeline_thread.runs_on_pipeline_thread
    def _handle_pipeline_event(self, event):
        if isinstance(event, pipeline_events_base.DisconnectedEvent):
            logger.debug(
                "{}({}): State is {} Connected is {}.".format(
                    self.name, event.name, self.state, self.pipeline_root.connected
                )
            )

            if self.pipeline_root.connected and self.state == ReconnectState.LOGICALLY_CONNECTED:
                # When we get disconnected, we try to reconnect as soon as we can.  We don't want
                # to reconnect right here bcause we're in a callback in the middle of being
                # disconnected and we want things to "settle down" a bit before reconnecting.
                #
                # We also use a timer to reconnect here because the "reconnect timer expired"
                # code path is well tested.  If we tried to immediately reconnect here, there
                # would be an entire set of scenarios that would need to be tested for
                # this case, and these tests would be idential to the "reconnect timer expired"
                # tests. Likewise, if there were 2 reconnect code paths (one immediate and one
                # delayed), then both those paths would need to be maintained as separate
                # flows
                self.state = ReconnectState.WAITING_TO_RECONNECT
                self._start_reconnect_timer(0.01)

            else:
                # If user manually disconnected, ReconnectState will be LOGICALLY_DISCONNECTED, and
                # no reconnect timer will be created.
                pass

            self.send_event_up(event)

        else:
            self.send_event_up(event)

    @pipeline_thread.runs_on_pipeline_thread
    def _send_new_connect_op_down(self):
        self_weakref = weakref.ref(self)

        @pipeline_thread.runs_on_pipeline_thread
        def on_connect_complete(op, error):
            this = self_weakref()
            if this:
                logger.debug(
                    "{}({}): on_connect_complete error={} state={} never_connected={} connected={} ".format(
                        this.name,
                        op.name,
                        error,
                        this.state,
                        this.never_connected,
                        this.pipeline_root.connected,
                    )
                )
                if error:
                    if this.never_connected:
                        # any error on a first connection is assumed to e permanent error
                        this.state = ReconnectState.LOGICALLY_DISCONNECTED
                        this._clear_reconnect_timer()
                        this._complete_waiting_connect_ops(error)
                    elif type(error) in transient_connect_errors:
                        # transient errors cause a reconnect attempt
                        self.state = ReconnectState.WAITING_TO_RECONNECT
                        self._start_reconnect_timer(self.reconnect_delay)
                    else:
                        # all others are permanent errors
                        this.state = ReconnectState.LOGICALLY_DISCONNECTED
                        this._clear_reconnect_timer()
                        this._complete_waiting_connect_ops(error)
                else:
                    # successfully connected
                    this.never_connected = False
                    this.state = ReconnectState.LOGICALLY_CONNECTED
                    this._clear_reconnect_timer()
                    this._complete_waiting_connect_ops()

        logger.debug("{}: sending new connect op down".format(self.name))
        op = pipeline_ops_base.ConnectOperation(callback=on_connect_complete)
        self.send_op_down(op)

    @pipeline_thread.runs_on_pipeline_thread
    def _start_reconnect_timer(self, delay):
        """
        Set a timer to reconnect after some period of time
        """
        logger.debug(
            "{}: State is {}. Connected={} Starting reconnect timer".format(
                self.name, self.state, self.pipeline_root.connected
            )
        )

        self._clear_reconnect_timer()

        self_weakref = weakref.ref(self)

        @pipeline_thread.invoke_on_pipeline_thread_nowait
        def on_reconnect_timer_expired():
            this = self_weakref()
            logger.debug(
                "{}: Reconnect timer expired. State is {} Connected is {}.".format(
                    self.name, self.state, self.pipeline_root.connected
                )
            )

            this.reconnect_timer = None
            if (
                this.state == ReconnectState.WAITING_TO_RECONNECT
                and not self.pipeline_root.connected
            ):
                # if we're waiting to reconnect and not connected, we try again
                this.state = ReconnectState.LOGICALLY_CONNECTED
                this._send_new_connect_op_down()

        self.reconnect_timer = threading.Timer(delay, on_reconnect_timer_expired)
        self.reconnect_timer.start()

    @pipeline_thread.runs_on_pipeline_thread
    def _clear_reconnect_timer(self):
        """
        Clear any previous reconnect timer
        """
        if self.reconnect_timer:
            logger.info("{}: clearing reconnect timer".format(self.name))
            self.reconnect_timer.cancel()
            self.reconnect_timer = None

    @pipeline_thread.runs_on_pipeline_thread
    def _complete_waiting_connect_ops(self, error=None):
        """
        A note of explanation: when we are waiting to reconnect, we need to keep a list of
        all connect ops that come through here.  We do this for 2 reasons:

        1. We don't want to pass them down immediately because we want to honor the waiting
           period.  If we passed them down immediately, we'd try to reconnect immediately
           instead of waiting until reconnect_timer fires.

        2. When we're retrying, there are new ConnectOperation ops sent down regularly.
           Any of the ops could be the one that succeeds.  When that happens, we need a
           way to to complete all of the ops that are patiently waiting for the connection.

        Right now, we only need to do this with ConnectOperation ops because these are the
        only ops that need to wait because these are the only ops that cause a connection
        to be established.  Other ops pass through this stage, and might fail in later
        stages, but that's OK.  If they needed a connection, the AutoConnectStage before
        this stage should be taking care of that.
        """
        logger.info("{}: completing waiting ops with error={}".format(self.name, error))
        list_copy = self.waiting_connect_ops
        self.waiting_connect_ops = []
        for op in list_copy:
            op.complete(error)
