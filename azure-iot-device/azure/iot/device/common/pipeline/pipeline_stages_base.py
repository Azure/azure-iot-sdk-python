# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging
import abc
import time
import traceback
import uuid
import weakref
import threading
import queue
from . import pipeline_events_base
from . import pipeline_ops_base, pipeline_ops_mqtt
from . import pipeline_thread
from . import pipeline_exceptions
from azure.iot.device.common import transport_exceptions, alarm
from azure.iot.device.common.auth import sastoken as st

logger = logging.getLogger(__name__)


class PipelineStage(abc.ABC):
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
            # within ._run_op().
            #
            # We tag errors from here as logger.warning because, while we return them to the
            # caller and rely on the caller to handle them, they're somewhat unexpected and might be
            # worthy of investigation.

            # Do not use exc_info parameter on logger.* calls. This causes pytest to save the
            # traceback which saves stack frames which shows up as a leak
            logger.warning(msg="Unexpected error in {}._run_op() call".format(self))
            logger.warning(traceback.format_exc())

            # Only complete the operation if it is not already completed.
            # Attempting to complete a completed operation would raise an exception.
            if not op.completed:
                op.complete(error=e)
            else:
                # Note that this would be very unlikely to occur. It could only happen if a stage
                # was doing something after completing an operation, and an exception was raised,
                # which is unlikely because stages usually don't do anything after completing an
                # operation.
                raise e

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
            # Do not use exc_info parameter on logger.* calls. This causes pytest to save the
            # traceback which saves stack frames which shows up as a leak
            logger.error(
                msg="{}: Unexpected error in ._handle_pipeline_event() call: {}".format(self, e)
            )
            if self.previous:
                logger.error("{}: Raising background exception")
                self.report_background_exception(e)
            else:
                # Nothing else we can do but log this. There exists no stage we can send the
                # exception to, and raising would send the error back down the pipeline.
                logger.error(
                    "{}: Cannot report a background exception because there is no previous stage!"
                )

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
        if self.next:
            self.next.run_op(op)
        else:
            # This shouldn't happen if the pipeline was created correctly
            logger.error(
                "{}({}): no next stage.cannot send op down. completing with error".format(
                    self.name, op.name
                )
            )
            raise pipeline_exceptions.PipelineRuntimeError(
                "{} not handled after {} stage with no next stage".format(op.name, self.name)
            )

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
            # This shouldn't happen if the pipeline was created correctly
            logger.critical(
                "{}({}): no previous stage. cannot send event up".format(event.name, self.name)
            )
            # NOTE: We can't report a background exception here because that involves
            # sending an event up, which is what got us into this problem in the first place.
            # Instead, raise, and let the method invoking this method handle it
            raise pipeline_exceptions.PipelineRuntimeError(
                "{} not handled after {} stage with no previous stage".format(event.name, self.name)
            )

    @pipeline_thread.runs_on_pipeline_thread
    def report_background_exception(self, e):
        """
        Send an exception up the pipeline that ocurred in the background.
        These would typically be in response to unsolicited actions, such as receiving data or
        timer-based operations, which cannot be raised to the user because they ocurred on a
        non-application thread.

        Note that this function leverages pipeline event flow, which means that any background
        exceptions in the core event flow itself become problematic (it's a good thing it's well
        tested then!)

        :param Exception e: The exception that ocurred in the background
        """
        event = pipeline_events_base.BackgroundExceptionEvent(e)
        self.send_event_up(event)


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
        super().__init__()
        self.on_pipeline_event_handler = None
        self.on_connected_handler = None
        self.on_disconnected_handler = None
        self.on_new_sastoken_required_handler = None
        self.on_background_exception_handler = None
        self.connected = False
        self.pipeline_configuration = pipeline_configuration

    def run_op(self, op):
        # CT-TODO: make this more elegant
        op.callback_stack[0] = pipeline_thread.invoke_on_callback_thread_nowait(
            op.callback_stack[0]
        )
        pipeline_thread.invoke_on_pipeline_thread(super().run_op)(op)

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
        # Base events that are common to all pipelines are handled here
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

        elif isinstance(event, pipeline_events_base.NewSasTokenRequiredEvent):
            logger.debug(
                "{}: NewSasTokenRequiredEvent received. Calling on_new_sastoken_required_handler".format(
                    self.name
                )
            )
            if self.on_new_sastoken_required_handler:
                pipeline_thread.invoke_on_callback_thread_nowait(
                    self.on_new_sastoken_required_handler
                )()

        elif isinstance(event, pipeline_events_base.BackgroundExceptionEvent):
            logger.debug(
                "{}: BackgroundExceptionEvent received. Calling on_background_exception_handler".format(
                    self.name
                )
            )
            if self.on_background_exception_handler:
                pipeline_thread.invoke_on_callback_thread_nowait(
                    self.on_background_exception_handler
                )(event.e)

        # Events that are domain-specific and unique to each pipeline are handled by the provided
        # domain-specific .on_pipeline_event_handler
        else:
            if self.on_pipeline_event_handler:
                pipeline_thread.invoke_on_callback_thread_nowait(self.on_pipeline_event_handler)(
                    event
                )
            else:
                # unexpected condition: we should be handling all pipeline events
                logger.error("incoming {} event with no handler.  dropping.".format(event.name))


# NOTE: This stage could be a candidate for being refactored into some kind of other
# pipeline-related structure. What's odd about it as a stage is that it doesn't really respond
# to operations or events so much as it spawns them on a timer.
# Perhaps some kind of... Pipeline Daemon?
class SasTokenStage(PipelineStage):
    # Amount of time, in seconds, prior to token expiration to trigger alarm
    DEFAULT_TOKEN_UPDATE_MARGIN = 120

    def __init__(self):
        super().__init__()
        # Indicates when token needs to be updated
        self._token_update_alarm = None
        # Indicates when to retry a failed reauthorization attempt
        # (only used with renewable SAS auth)
        self._reauth_retry_timer = None

    @pipeline_thread.runs_on_pipeline_thread
    def _run_op(self, op):
        if (
            isinstance(op, pipeline_ops_base.InitializePipelineOperation)
            and self.pipeline_root.pipeline_configuration.sastoken is not None
        ):
            # Start an alarm (renewal or replacement depending on token type)
            self._start_token_update_alarm()
            self.send_op_down(op)
        elif (
            isinstance(op, pipeline_ops_base.ReauthorizeConnectionOperation)
            and self.pipeline_root.pipeline_configuration.sastoken is not None
        ):
            # NOTE 1: This case (currently) implies that we are using Non-Renewable SAS,
            # although it's not enforced here (it's a product of how the pipeline and client are
            # configured overall)

            # NOTE 2: There's a theoretically possible case where the new token has the same expiry
            # time as the old token, and thus a new update alarm wouldn't really be required, but
            # I don't want to include the complexity of checking. Just start a new alarm anyway.

            # NOTE 3: Yeah, this is the same logic as the above case for the InitializePipeline op,
            # but if it weren't separate, how would you get all these nice informative comments?
            # (Also, it leaves room for the logic to change in the future)
            self._start_token_update_alarm()
            self.send_op_down(op)
        elif isinstance(op, pipeline_ops_base.ShutdownPipelineOperation):
            self._cancel_token_update_alarm()
            self._cancel_reauth_retry_timer()
            self.send_op_down(op)
        else:
            self.send_op_down(op)

    @pipeline_thread.runs_on_pipeline_thread
    def _cancel_token_update_alarm(self):
        """Cancel and delete any pending update alarm"""
        old_alarm = self._token_update_alarm
        self._token_update_alarm = None
        if old_alarm:
            logger.debug("Cancelling SAS Token update alarm")
            old_alarm.cancel()
            old_alarm = None

    @pipeline_thread.runs_on_pipeline_thread
    def _cancel_reauth_retry_timer(self):
        """Cancel and delete any pending reauth retry timer"""
        old_reauth_retry_timer = self._reauth_retry_timer
        self._reauth_retry_timer = None
        if old_reauth_retry_timer:
            logger.debug("Cancelling reauthorization retry timer")
            old_reauth_retry_timer.cancel()
            old_reauth_retry_timer = None

    @pipeline_thread.runs_on_pipeline_thread
    def _start_token_update_alarm(self):
        """Begin an update alarm.
        If using a RenewableSasToken, when the alarm expires the token will be automatically
        renewed, and a new alarm will be set.

        If using a NonRenewableSasToken, when the alarm expires, it will trigger a
        NewSasTokenRequiredEvent to signal that a new SasToken must be manually provided.
        """
        self._cancel_token_update_alarm()

        update_time = (
            self.pipeline_root.pipeline_configuration.sastoken.expiry_time
            - self.DEFAULT_TOKEN_UPDATE_MARGIN
        )

        # On Windows platforms, the threading event TIMEOUT_MAX (approximately 49.7 days) could
        # conceivably be less than the SAS lifespan, which means we may need to update the token
        # before the lifespan ends.
        # If we really wanted to adjust this in the future to use the entire SAS lifespan, we could
        # implement Alarms that trigger other Alarms, but for now, just forcing a token update
        # is good enough.
        # Note that this doesn't apply to (most) Unix platforms, where TIMEOUT_MAX is 292.5 years.
        if (update_time - time.time()) > threading.TIMEOUT_MAX:
            update_time = time.time() + threading.TIMEOUT_MAX
            logger.warning(
                "SAS Token expiration ({expiry} seconds) exceeds max scheduled renewal time ({max} seconds). Will be renewing after {max} seconds instead".format(
                    expiry=self.pipeline_root.pipeline_configuration.sastoken.expiry_time,
                    max=threading.TIMEOUT_MAX,
                )
            )

        self_weakref = weakref.ref(self)

        # For renewable SasTokens, create an alarm that will automatically renew the token,
        # and then start another alarm.
        if isinstance(self.pipeline_root.pipeline_configuration.sastoken, st.RenewableSasToken):
            logger.debug(
                "{}: Scheduling automatic SAS Token renewal at epoch time: {}".format(
                    self.name, update_time
                )
            )

            @pipeline_thread.invoke_on_pipeline_thread_nowait
            def renew_token():
                this = self_weakref()
                # Cancel any token reauth retry timer in progress (from a previous renewal)
                this._cancel_reauth_retry_timer()
                logger.info("{}: Renewing SAS Token...".format(self.name))
                # Renew the token
                sastoken = this.pipeline_root.pipeline_configuration.sastoken
                try:
                    sastoken.refresh()
                except st.SasTokenError as e:
                    logger.error("{}: SAS Token renewal failed".format(self.name))
                    this.report_background_exception(e)
                    # TODO: then what? How do we respond to this? Retry?
                    # What if it never works and the token expires?
                else:
                    # If the pipeline is already connected, send order to reauthorize the connection
                    # now that token has been renewed. If the pipeline is not currently connected,
                    # there is no need to do this, as the next connection will be using the new
                    # credentials.
                    if this.pipeline_root.connected:
                        this._reauthorize()

                    # Once again, start a renewal alarm
                    this._start_token_update_alarm()

            self._token_update_alarm = alarm.Alarm(update_time, renew_token)

        # For nonrenewable SasTokens, create an alarm that will issue a NewSasTokenRequiredEvent
        else:
            logger.debug(
                "Scheduling manual SAS Token renewal at epoch time: {}".format(update_time)
            )

            @pipeline_thread.invoke_on_pipeline_thread_nowait
            def request_new_token():
                this = self_weakref()
                logger.info("Requesting new SAS Token....")
                # Send request
                this.send_event_up(pipeline_events_base.NewSasTokenRequiredEvent())

            self._token_update_alarm = alarm.Alarm(update_time, request_new_token)

        self._token_update_alarm.daemon = True
        self._token_update_alarm.start()

    @pipeline_thread.runs_on_pipeline_thread
    def _reauthorize(self):
        self_weakref = weakref.ref(self)

        @pipeline_thread.runs_on_pipeline_thread
        def on_reauthorize_complete(op, error):
            this = self_weakref()
            if error:
                logger.info(
                    "{}: Connection reauthorization failed.  Error={}".format(this.name, error)
                )
                self.report_background_exception(error)
                # If connection has not been somehow re-established, we need to keep trying
                # because for the reauthorization to originally have been issued, we were in
                # a connected state.
                # NOTE: we only do this if connection retry is enabled on the pipeline. If it is,
                # we have a contract to maintain a connection. If it has been disabled, we have
                # a contract to not do so.
                # NOTE: We can't rely on the ReconnectStage to do this because 1) the pipeline
                # stages should stand on their own, and 2) if the reauth failed, the ReconnectStage
                # wouldn't know to reconnect, because the expected state of a failed reauth is
                # to be disconnected.
                if (
                    not this.pipeline_root.connected
                    and this.pipeline_root.pipeline_configuration.connection_retry
                ):
                    logger.info("{}: Retrying connection reauthorization".format(this.name))
                    # No need to cancel the timer, because if this is running, it has already ended

                    @pipeline_thread.invoke_on_pipeline_thread_nowait
                    def retry_reauthorize():
                        # We need to check this when the timer expires as well as before creating
                        # the timer in case connection has been re-established while timer was
                        # running
                        if not this.pipeline_root.connected:
                            this._reauthorize()

                    this._reauth_retry_timer = threading.Timer(
                        this.pipeline_root.pipeline_configuration.connection_retry_interval,
                        retry_reauthorize,
                    )
                    this._reauth_retry_timer.daemon = True
                    this._reauth_retry_timer.start()

            else:
                logger.info("{}: Connection reauthorization successful".format(this.name))

        logger.info("{}: Starting reauthorization process for new SAS token".format(self.name))
        self.send_op_down(
            pipeline_ops_base.ReauthorizeConnectionOperation(callback=on_reauthorize_complete)
        )


class AutoConnectStage(PipelineStage):
    """
    This stage is responsible for ensuring that the protocol is connected when
    it needs to be connected.
    """

    @pipeline_thread.runs_on_pipeline_thread
    def _run_op(self, op):
        # Any operation that requires a connection can trigger a connection if
        # we're not connected and the auto-connect feature is enabled.
        if (
            op.needs_connection
            and not self.pipeline_root.connected
            and self.pipeline_root.pipeline_configuration.auto_connect
        ):
            logger.debug(
                "{}({}): Op needs connection.  Queueing this op and starting a ConnectionOperation".format(
                    self.name, op.name
                )
            )
            self._do_connect(op)

        else:
            self.send_op_down(op)

    @pipeline_thread.runs_on_pipeline_thread
    def _do_connect(self, op):
        """
        Start connecting the transport in response to some operation
        """
        # Alias to avoid overload within the callback below
        # CT-TODO: remove the need for this with better callback semantics
        op_needs_connect = op

        # function that gets called after we're connected.
        @pipeline_thread.runs_on_pipeline_thread
        def on_connect_op_complete(op, error):
            if error:
                logger.debug(
                    "{}({}): Connection failed.  Completing with failure because of connection failure: {}".format(
                        self.name, op_needs_connect.name, error
                    )
                )
                op_needs_connect.complete(error=error)
            else:
                logger.debug(
                    "{}({}): connection is complete.  Running op that triggered connection.".format(
                        self.name, op_needs_connect.name
                    )
                )
                self.run_op(op_needs_connect)

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
        super().__init__()
        self.queue = queue.Queue()
        self.blocked = False

    @pipeline_thread.runs_on_pipeline_thread
    def _run_op(self, op):

        # If this stage is currently blocked (because we're waiting for a connection, etc,
        # to complete), we queue up all operations until after the connect completes.
        if self.blocked:
            logger.debug(
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
                    logger.debug(
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
        logger.debug(
            "{}({}): processing {} items in queue for error={}".format(
                self.name, op.name, self.queue.qsize(), error
            )
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
                logger.debug(
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
        super().__init__()
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
                del self.pending_responses[request_id]
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
                del self.pending_responses[event.request_id]
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
                logger.info(
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
                    "{stage}: ConnectedEvent: re-publishing request {id} for {method} {type} ".format(
                        stage=self.name,
                        id=request_id,
                        method=self.pending_responses[request_id].method,
                        type=self.pending_responses[request_id].request_type,
                    )
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
    a OperationTimeout.  The intention is that a higher stage will know what to
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
        super().__init__()
        # use a fixed list and fixed intervals for now.  Later, this info will come in
        # as an init param or a retry poicy
        self.timeout_intervals = {
            pipeline_ops_mqtt.MQTTSubscribeOperation: 10,
            pipeline_ops_mqtt.MQTTUnsubscribeOperation: 10,
            # Only Sub and Unsub are here because MQTT auto retries pub
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
                    error=pipeline_exceptions.OperationTimeout(
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
        super().__init__()
        # Retry intervals are hardcoded for now. Later, they come in as an
        # init param, probably via retry policy.
        self.retry_intervals = {
            pipeline_ops_mqtt.MQTTSubscribeOperation: 20,
            pipeline_ops_mqtt.MQTTUnsubscribeOperation: 20,
            # Only Sub and Unsub are here because MQTT auto retries pub
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
                if isinstance(error, pipeline_exceptions.OperationTimeout):
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
                logger.debug("{}({}): retrying".format(this.name, op.name))
                op.retry_timer.cancel()
                op.retry_timer = None
                this.ops_waiting_to_retry.remove(op)
                # Don't just send it down directly.  Instead, go through run_op so we get
                # retry functionality this time too
                this.run_op(op)

            interval = self.retry_intervals[type(op)]
            logger.info(
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


class ReconnectState(object):
    """
    Class which holds reconnect states as class variables.  Created to make code that reads like an enum without using an enum.
    """

    CONNECTED = "CONNECTED"  # Client is connected (as far as it knows)
    DISCONNECTED = "DISCONNECTED"  # Client is disconnected
    CONNECTING = "CONNECTING"  # Client is in the process of connecting
    DISCONNECTING = "DISCONNECTING"  # Client is in the process of disconnecting
    REAUTHORIZING = "REAUTHORIZING"  # Client is in the process of reauthorizing
    # NOTE: Reauthorizing is the process of doing a disconnect, then a connect at transport level


class ReconnectStage(PipelineStage):

    intermediate_states = [
        ReconnectState.CONNECTING,
        ReconnectState.DISCONNECTING,
        ReconnectState.REAUTHORIZING,
    ]
    connection_ops = [
        pipeline_ops_base.ConnectOperation,
        pipeline_ops_base.DisconnectOperation,
        pipeline_ops_base.ReauthorizeConnectionOperation,
    ]
    transient_connect_errors = [
        pipeline_exceptions.OperationCancelled,
        pipeline_exceptions.OperationTimeout,
        pipeline_exceptions.OperationError,
        transport_exceptions.ConnectionFailedError,
        transport_exceptions.ConnectionDroppedError,
    ]

    def __init__(self):
        super().__init__()
        self.reconnect_timer = None
        self.state = ReconnectState.DISCONNECTED
        self.waiting_ops = queue.Queue()

        # NOTE: In this stage states are both checked, and changed, but there is no lock to protect
        # this state value, or the logic that surrounds it from multithreading. This is because due
        # to the threading model of the pipeline, there is a dedicated pipeline thread that handles
        # everything that runs here, and it can only be doing one thing at a time. Thus we don't
        # need to have a threading lock on our state, or be concerned with how atomic things are.

    @pipeline_thread.runs_on_pipeline_thread
    def _run_op(self, op):
        # NOTE: Connection Retry == Reconnect. These terms are used interchangably. 'reconnect' is a
        # more accurate term for the process happening internally here, but the feature is called
        # 'connection retry' when facing the end user.
        if self.pipeline_root.pipeline_configuration.connection_retry:

            # If receiving a connection op while one is already in progress, wait for the current
            # one to finish. This is kind of like a ConnectionLockStage, but inside this one.
            # It has to happen here because just relying on a ConnectionLockStage before or after
            # in the pipeline is insufficient, given that operations can spawn in this stage.
            # We need a way to wait ops without letting them pass through and affect the connection
            # state in order to address edge cases e.g. a user-initiated connect and a automatic
            # reconnect connect happen at approximately the same time.
            if self.state in self.intermediate_states and type(op) in self.connection_ops:
                logger.debug(
                    "{}({}): State is {} - waiting for in-progress operation to finish".format(
                        self.name, op.name, self.state
                    )
                )
                self.waiting_ops.put_nowait(op)

            else:
                if isinstance(op, pipeline_ops_base.ConnectOperation):
                    if self.state is ReconnectState.CONNECTED:
                        logger.debug(
                            "{}({}): State is already CONNECTED. Sending op down".format(
                                self.name, op.name
                            )
                        )
                        self._add_connection_op_callback(op)
                        # NOTE: This is the safest thing to do while the ConnectionLockStage is
                        # doing autocompletes based on connection status. When it is revisited,
                        # this logic may need to be updated.
                    elif self.state is ReconnectState.DISCONNECTED:
                        logger.debug(
                            "{}({}): State changes DISCONNECTED -> CONNECTING. Sending op down".format(
                                self.name, op.name
                            )
                        )
                        self.state = ReconnectState.CONNECTING
                        self._add_connection_op_callback(op)
                    else:
                        # This should be impossible to reach. If the state were intermediate, it
                        # would have been added to the waiting ops queue above.
                        logger.warning(
                            "{}({}): Invalid State - {}".format(self.name, op.name, self.state)
                        )

                elif isinstance(op, pipeline_ops_base.DisconnectOperation):
                    # First, always clear any reconnect timer. Because a manual disconnection is
                    # occurring, we won't want to be reconnecting any more.
                    self._clear_reconnect_timer()

                    if self.state is ReconnectState.CONNECTED:
                        logger.debug(
                            "{}({}): State changes CONNECTED -> DISCONNECTING. Sending op down.".format(
                                self.name, op.name
                            )
                        )
                        self.state = ReconnectState.DISCONNECTING
                        self._add_connection_op_callback(op)
                    elif self.state is ReconnectState.DISCONNECTED:
                        logger.debug(
                            "{}({}): State is already DISCONNECTED. Sending op down".format(
                                self.name, op.name
                            )
                        )
                        self._add_connection_op_callback(op)
                        # NOTE: This is the safest thing to do while the ConnectionLockStage is
                        # doing autocompletes based on connection status. When it is revisited,
                        # this logic may need to be updated.
                    else:
                        # This should be impossible to reach. If the state were intermediate, it
                        # would have been added to the waiting ops queue above.
                        logger.warning(
                            "{}({}): Invalid State - {}".format(self.name, op.name, self.state)
                        )

                elif isinstance(op, pipeline_ops_base.ReauthorizeConnectionOperation):
                    if self.state is ReconnectState.CONNECTED:
                        logger.debug(
                            "{}({}): State changes CONNECTED -> REAUTHORIZING. Sending op down.".format(
                                self.name, op.name
                            )
                        )
                        self.state = ReconnectState.REAUTHORIZING
                        self._add_connection_op_callback(op)
                    elif self.state is ReconnectState.DISCONNECTED:
                        logger.debug(
                            "{}({}): State changes DISCONNECTED -> REAUTHORIZING. Sending op down".format(
                                self.name, op.name
                            )
                        )
                        self.state = ReconnectState.REAUTHORIZING
                        self._add_connection_op_callback(op)
                    else:
                        # This should be impossible to reach. If the state were intermediate, it
                        # would have been added to the waiting ops queue above.
                        logger.warning(
                            "{}({}): Invalid State - {}".format(self.name, op.name, self.state)
                        )

                elif isinstance(op, pipeline_ops_base.ShutdownPipelineOperation):
                    self._clear_reconnect_timer()
                    # Cancel all pending ops so they don't hang
                    while not self.waiting_ops.empty():
                        waiting_op = self.waiting_ops.get_nowait()
                        cancel_error = pipeline_exceptions.OperationCancelled(
                            "Operation waiting in ReconnectStage cancelled by shutdown"
                        )
                        waiting_op.complete(error=cancel_error)

                # In all cases the op gets sent down
                self.send_op_down(op)

        # Connection retry disabled
        else:
            self.send_op_down(op)

    @pipeline_thread.runs_on_pipeline_thread
    def _handle_pipeline_event(self, event):
        # Connection Retry Enabled
        if self.pipeline_root.pipeline_configuration.connection_retry:
            if isinstance(event, pipeline_events_base.ConnectedEvent):
                # First, clear the reconnect timer no matter what.
                # We are now connected, so any ongoing reconnect is unnecessary
                self._clear_reconnect_timer()

                # EXPECTED CONNECTION (ConnectOperation was previously issued)
                if self.state is ReconnectState.CONNECTING:
                    logger.debug(
                        "{}({}): State changes CONNECTING -> CONNECTED. Connection established".format(
                            self.name, event.name
                        )
                    )
                    self.state = ReconnectState.CONNECTED

                # EXPECTED CONNECTION (ReauthorizeConnectionOperation was previously issued)
                elif self.state is ReconnectState.REAUTHORIZING:
                    logger.debug(
                        "{}({}): State changes REAUTHORIZING -> CONNECTED. Connection re-established after reauthentication".format(
                            self.name, event.name
                        )
                    )
                    self.state = ReconnectState.CONNECTED

                # BAD STATE (this block should not be reached)
                else:
                    logger.warning(
                        "{}: ConnectedEvent received while in unexpected state - {}, Connected: {}".format(
                            self.name, self.state, self.pipeline_root.connected
                        )
                    )
                    logger.debug(
                        "{}({}): State changes {} -> CONNECTED. Unexpected connection".format(
                            self.name, event.name, self.state
                        )
                    )
                    self.state = ReconnectState.CONNECTED

            elif isinstance(event, pipeline_events_base.DisconnectedEvent):
                # UNEXPECTED DISCONNECTION (i.e. Connection has been lost)
                if self.state is ReconnectState.CONNECTED:
                    # When we get disconnected, we try to reconnect as soon as we can. We set a
                    # timer here that will start the process in another thread because we don't
                    # want to hold up the event flow
                    logger.debug(
                        "{}({}): State changes CONNECTED -> DISCONNECTED. Attempting to reconnect".format(
                            self.name, event.name
                        )
                    )
                    # Set the state change before starting the timer in order to make sure
                    # there's no issues when the timer expires. The pipline threading model should
                    # already be preventing any weirdness with timing, but can't hurt to do this
                    # as well.
                    self.state = ReconnectState.DISCONNECTED
                    self._start_reconnect_timer(0.01)

                # EXPECTED DISCONNECTION (DisconnectOperation was previously issued)
                elif self.state is ReconnectState.DISCONNECTING:
                    # No reconnect timer will be created.
                    logger.debug(
                        "{}({}): State changes DISCONNECTING -> DISCONNECTED. Not attempting to reconnect (User-initiated disconnect)".format(
                            self.name, event.name
                        )
                    )
                    self.state = ReconnectState.DISCONNECTED

                # EXPECTED DISCONNECTION (Reauthorization process)
                elif self.state is ReconnectState.REAUTHORIZING:
                    # ReconnectState will remain REAUTHORIZING until completion of the process
                    # upon re-establishing the connection

                    # NOTE: There is a ~small~ chance of a false positive here if an unexpected
                    # disconnection occurs while a ReauthorizationOperation is in flight.
                    # However, it will sort itself out - the ensuing connect that occurs as part
                    # of the reauthorization will restore connection (no harm done) or it will
                    # fail, at which point the failure was a result of a manual operation and
                    # reconnection is not supposed to occur. So either way, we end up where we want
                    # to be despite the false positive - just be aware that this can happen.
                    logger.debug(
                        "{}({}): Not attempting to reconnect (Reauthorization in progress)".format(
                            self.name, event.name
                        )
                    )

                # BAD STATE (this block should not be reached)
                else:
                    logger.warning(
                        "{}: DisconnectEvent received while in unexpected state - {}, Connected: {}".format(
                            self.name, self.state, self.pipeline_root.connected
                        )
                    )
                    logger.debug(
                        "{}({}): State changes {} -> DISCONNECTED. Unexpected disconnect in unexpected state".format(
                            self.name, event.name, self.state
                        )
                    )
                    self.state = ReconnectState.DISCONNECTED

            # In all cases the event is sent up
            self.send_event_up(event)

        # Connection Retry disabled
        else:
            self.send_event_up(event)

    @pipeline_thread.runs_on_pipeline_thread
    def _add_connection_op_callback(self, op):
        """Adds callback to a connection op passing through to do necessary stage upkeep"""
        self_weakref = weakref.ref(self)

        # NOTE: we are currently protected from connect failing due to being already connected
        # by the ConnectionLockStage. If the ConnectionLockStage changes functionality,
        # we may need some logic changes to address an op that can fail while leaving us CONNECTED

        @pipeline_thread.runs_on_pipeline_thread
        def on_complete(op, error):
            this = self_weakref()
            # If error, set us back to a DISCONNECTED state. It doesn't matter what kind of
            # connection op this was, any failure should result in a disconnected state.

            # NOTE: Due to the stage waiting any ops if an ongoing connection op is in-progress
            # as well as the way that the reconnection process checks if there is an in-progress
            # connection op (and punts the reconnect if so), there is no risk here of setting
            # directly to DISCONNECTED - the intermediate state being overwritten is always going
            # to be due to this op that is now completing, we can be assured of that.
            if error:
                logger.debug(
                    "{}({}): failed, state change {} -> DISCONNECTED".format(
                        this.name, op.name, this.state
                    )
                )
                this.state = ReconnectState.DISCONNECTED

            # Allow the next waiting op to proceed (if any)
            this._run_all_waiting_ops()

        op.add_callback(on_complete)

    @pipeline_thread.runs_on_pipeline_thread
    def _run_all_waiting_ops(self):

        if not self.waiting_ops.empty():
            queuecopy = self.waiting_ops
            self.waiting_ops = queue.Queue()

            while not queuecopy.empty():
                next_op = queuecopy.get_nowait()
                if not next_op.completed:
                    logger.debug(
                        "{}: Resolving next waiting op: {}".format(self.name, next_op.name)
                    )
                    self.run_op(next_op)

    @pipeline_thread.runs_on_pipeline_thread
    def _reconnect(self):
        self_weakref = weakref.ref(self)

        @pipeline_thread.runs_on_pipeline_thread
        def on_reconnect_complete(op, error):
            this = self_weakref()
            if this:
                logger.debug(
                    "{}({}): on_connect_complete error={} state={} connected={} ".format(
                        this.name,
                        op.name,
                        error,
                        this.state,
                        this.pipeline_root.connected,
                    )
                )

                if error:
                    # Set state back to DISCONNECTED so as not to block anything else
                    logger.debug(
                        "{}: State change {} -> DISCONNECTED".format(this.name, this.state)
                    )
                    this.state = ReconnectState.DISCONNECTED

                    # report background exception to indicate this failure ocurred
                    this.report_background_exception(error)

                    # Determine if should try reconnect again
                    if this._should_reconnect(error):
                        # transient errors can cause a reconnect attempt
                        logger.debug(
                            "{}: Reconnect failed. Starting reconnection timer".format(this.name)
                        )
                        this._start_reconnect_timer(
                            this.pipeline_root.pipeline_configuration.connection_retry_interval
                        )
                    else:
                        # all others are permanent errors
                        logger.debug(
                            "{}: Cannot reconnect. Ending reconnection process".format(this.name)
                        )

                # Now see if there's anything that may have blocked waiting for us to finish
                this._run_all_waiting_ops()

        # NOTE: I had considered leveraging the run_op infrastructure instead of sending this
        # directly down. Ultimately however, I think it's best to keep reconnects completely
        # distinct from other operations that come through the pipeline - for instance, we don't
        # really want them to end up queued up behind other operations via the .waiting_ops queue.
        # Reconnects have a top priority.
        op = pipeline_ops_base.ConnectOperation(callback=on_reconnect_complete)
        self.send_op_down(op)

    @pipeline_thread.runs_on_pipeline_thread
    def _should_reconnect(self, error):
        """Returns True if a reconnect should occur in response to an error, False otherwise"""
        if self.pipeline_root.pipeline_configuration.connection_retry:
            if type(error) in self.transient_connect_errors:
                return True
        return False

    @pipeline_thread.runs_on_pipeline_thread
    def _start_reconnect_timer(self, delay):
        """
        Set a timer to reconnect after some period of time
        """
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
            # Clear the reconnect timer here first and foremost so it doesn't accidentally
            # get left around somehow. Don't use the _clear_reconnect_timer method, as the timer
            # has expired, and thus cannot be cancelled.
            this.reconnect_timer = None

            if this.state is ReconnectState.DISCONNECTED:
                # We are still disconnected, so reconnect

                # NOTE: Because any reconnect timer would have been cancelled upon a manual
                # disconnect, there is no way this block could be executing if we were happy
                # with our DISCONNECTED state.
                logger.debug("{}: Starting reconnection".format(this.name))
                logger.debug(
                    "{}: State changes {} -> CONNECTING. Sending new connect op down in reconnect attempt".format(
                        self.name, self.state
                    )
                )
                self.state = ReconnectState.CONNECTING
                this._reconnect()
            elif this.state in self.intermediate_states:
                # If another connection op is in progress, just wait and try again later to avoid
                # any extra confusion (i.e. punt the reconnection)
                logger.debug(
                    "{}: Other connection operation in-progress, setting a new reconnection timer".format(
                        this.name
                    )
                )
                this._start_reconnect_timer(
                    this.pipeline_root.pipeline_configuration.connection_retry_interval
                )
            else:
                logger.debug(
                    "{}: Unexpected state reached ({}) after reconnection timer expired".format(
                        this.name, this.state
                    )
                )

        self.reconnect_timer = threading.Timer(delay, on_reconnect_timer_expired)
        self.reconnect_timer.start()

    @pipeline_thread.runs_on_pipeline_thread
    def _clear_reconnect_timer(self):
        """
        Clear any previous reconnect timer
        """
        if self.reconnect_timer:
            logger.debug("{}: clearing reconnect timer".format(self.name))
            self.reconnect_timer.cancel()
            self.reconnect_timer = None
