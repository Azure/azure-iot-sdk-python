# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import sys
import logging
import traceback
from . import pipeline_exceptions
from . import pipeline_thread
from azure.iot.device.common import handle_exceptions

logger = logging.getLogger(__name__)


class PipelineOperation(object):
    """
    A base class for data objects representing operations that travels down the pipeline.

    Each PipelineOperation object represents a single asyncroneous operation that is performed
    by the pipeline. The PipelineOperation objects travel through "stages" of the pipeline,
    and each stage has the opportunity to act on each specific operation that it
    receives.  If a stage does not handle a particular operation, it needs to pass it to the
    next stage.  If the operation gets to the end of the pipeline without being handled
    (completed), then it is treated as an error.

    :ivar name: The name of the operation.  This is used primarily for logging
    :type name: str
    :ivar callback: The callback that is called when the operation is completed, either
        successfully or with a failure.
    :type callback: Function
    :ivar needs_connection: This is an attribute that indicates whether a particular operation
        requires a connection to operate.  This is currently used by the AutoConnectStage
        stage, but this functionality will be revamped shortly.
    :type needs_connection: Boolean
    :ivar error: The presence of a value in the error attribute indicates that the operation failed,
        absence of this value indicates that the operation either succeeded or hasn't been handled yet.
    :type error: Error
    """

    def __init__(self, callback):
        """
        Initializer for PipelineOperation objects.

        :param Function callback: The function that gets called when this operation is complete or has
            failed. The callback function must accept A PipelineOperation object which indicates
            the specific operation which has completed or failed.
        """
        if self.__class__ == PipelineOperation:
            raise TypeError(
                "Cannot instantiate PipelineOperation object.  You need to use a derived class"
            )
        self.name = self.__class__.__name__
        self.callback_stack = []
        self.needs_connection = False
        self.completed = False  # Operation has been fully completed
        self.completing = False  # Operation is in the process of completing
        self.error = None  # Error associated with Operation completion

        self.add_callback(callback)

    def add_callback(self, callback):
        """Adds a callback to the Operation that will be triggered upon Operation completion.

        When an Operation is completed, all callbacks will be resolved in LIFO order.

        Callbacks cannot be added to an already completed operation, or an operation that is
        currently undergoing a completion process.

        :param callback: The callback to add to the operation.

        :raises: OperationError if the operation is already completed, or is in the process of
            completing.
        """
        if self.completed:
            raise pipeline_exceptions.OperationError(
                "{}: Attempting to add a callback to an already-completed operation!".format(
                    self.name
                )
            )
        if self.completing:
            raise pipeline_exceptions.OperationError(
                "{}: Attempting to add a callback to a operation with completion in progress!".format(
                    self.name
                )
            )
        else:
            self.callback_stack.append(callback)

    @pipeline_thread.runs_on_pipeline_thread
    def complete(self, error=None):
        """ Complete the operation, and trigger all callbacks in LIFO order.

        The operation is completed successfully be default, or completed unsucessfully if an error
        is provided.

        An operation that is already fully completed, or in the process of completion cannot be
        completed again.

        This process can be halted if a callback for the operation invokes the .halt_completion()
        method on this Operation.

        :param error: Optionally provide an Exception object indicating the error that caused
            the completion. Providing an error indicates that the operation was unsucessful.
        """
        if error:
            logger.error("{}: completing with error {}".format(self.name, error))
        else:
            logger.debug("{}: completing without error".format(self.name))

        if self.completed or self.completing:
            logger.error("{}: has already been completed!".format(self.name))
            e = pipeline_exceptions.OperationError(
                "Attempting to complete an already-completed operation: {}".format(self.name)
            )
            # This could happen in a foreground or background thread, so err on the side of caution
            # and send it to the background handler.
            handle_exceptions.handle_background_exception(e)
        else:
            # Operation is now in the process of completing
            self.completing = True
            self.error = error

            while self.callback_stack:
                if not self.completing:
                    logger.debug("{}: Completion halted!".format(self.name))
                    break
                if self.completed:
                    # This block should never be reached - this is an invalid state.
                    # If this block is reached, there is a bug in the code.
                    logger.error(
                        "{}: Invalid State! Operation completed while resolving completion".format(
                            self.name
                        )
                    )
                    e = pipeline_exceptions.OperationError(
                        "Operation reached fully completed state while still resolving completion: {}".format(
                            self.name
                        )
                    )
                    handle_exceptions.handle_background_exception(e)
                    break

                callback = self.callback_stack.pop()
                try:
                    callback(op=self, error=error)
                except Exception as e:
                    logger.error(
                        "Unhandled error while triggering callback for {}".format(self.name)
                    )
                    logger.error(traceback.format_exc())
                    # This could happen in a foreground or background thread, so err on the side of caution
                    # and send it to the background handler.
                    handle_exceptions.handle_background_exception(e)

            if self.completing:
                # Operation is now completed, no longer in the process of completing
                self.completing = False
                self.completed = True

    @pipeline_thread.runs_on_pipeline_thread
    def halt_completion(self):
        """Halt the completion of an operation that is currently undergoing a completion process
        as a result of a call to .complete().

        Completion cannot be halted if there is no currently ongoing completion process. The only
        way to successfully invoke this method is from within a callback on the Operation in
        question.

        This method will leave any yet-untriggered callbacks on the Operation to be triggered upon
        a later completion.

        This method will clear any error associated with the currently ongoing completion process
        from the Operation.
        """
        if not self.completing:
            logger.error("{}: is not currently in the process of completion!".format(self.name))
            e = pipeline_exceptions.OperationError(
                "Attempting to halt completion of an operation not in the process of completion: {}".format(
                    self.name
                )
            )
            handle_exceptions.handle_background_exception(e)
        else:
            logger.debug("{}: Halting completion...".format(self.name))
            self.completing = False
            self.error = None

    @pipeline_thread.runs_on_pipeline_thread
    def spawn_worker_op(self, worker_op_type, **kwargs):
        """Create and return a new operation, which, when completed, will complete the operation
        it was spawned from.

        :param worker_op_type: The type (class) of the new worker operation.
        :param **kwargs: The arguments to instantiate the new worker operation with. Note that a
            callback is not required, but if provided, will be triggered prior to completing the
            operation that spawned the worker operation.

        :returns: A new worker operation of the type specified in the worker_op_type parameter.
        """
        logger.debug("{}: creating worker op of type {}".format(self.name, worker_op_type.__name__))

        @pipeline_thread.runs_on_pipeline_thread
        def on_worker_op_complete(op, error):
            logger.debug("{}: Worker op ({}) has been completed".format(self.name, op.name))
            self.complete(error=error)

        if "callback" in kwargs:
            provided_callback = kwargs["callback"]
            kwargs["callback"] = on_worker_op_complete
            worker_op = worker_op_type(**kwargs)
            worker_op.add_callback(provided_callback)
        else:
            kwargs["callback"] = on_worker_op_complete
            worker_op = worker_op_type(**kwargs)

        return worker_op


class ConnectOperation(PipelineOperation):
    """
    A PipelineOperation object which tells the pipeline to connect to whatever service it needs to connect to.

    This operation is in the group of base operations because connecting is a common operation that many clients might need to do.

    Even though this is an base operation, it will most likely be handled by a more specific stage (such as an IoTHub or MQTT stage).
    """

    def __init__(self, callback):
        self.watchdog_timer = None
        super(ConnectOperation, self).__init__(callback)


class ReauthorizeConnectionOperation(PipelineOperation):
    """
    A PipelineOperation object which tells the pipeline to reauthorize the connection to whatever service it is connected to.

    Clients will most-likely submit a ReauthorizeConnectionOperation when some credential (such as a sas token) has changed and the protocol client
    needs to re-establish the connection to refresh the credentials

    This operation is in the group of base operations because reauthorizinging is a common operation that many clients might need to do.

    Even though this is an base operation, it will most likely be handled by a more specific stage (such as an IoTHub or MQTT stage).
    """

    def __init__(self, callback):
        self.watchdog_timer = None
        super(ReauthorizeConnectionOperation, self).__init__(callback)

    pass


class DisconnectOperation(PipelineOperation):
    """
    A PipelineOperation object which tells the pipeline to disconnect from whatever service it might be connected to.

    This operation is in the group of base operations because disconnecting is a common operation that many clients might need to do.

    Even though this is an base operation, it will most likely be handled by a more specific stage (such as an IoTHub or MQTT stage).
    """

    pass


class EnableFeatureOperation(PipelineOperation):
    """
    A PipelineOperation object which tells the pipeline to "enable" a particular feature.

    A "feature" is just a string which represents some set of functionality that needs to be enabled, such as "C2D" or "Twin".

    This object has no notion of what it means to "enable" a feature.  That knowledge is handled by stages in the pipeline which might convert
    this operation to a more specific operation (such as an MQTT subscribe operation with a specific topic name).

    This operation is in the group of base operations because disconnecting is a common operation that many clients might need to do.

    Even though this is an base operation, it will most likely be handled by a more specific stage (such as an IoTHub or MQTT stage).
    """

    def __init__(self, feature_name, callback):
        """
        Initializer for EnableFeatureOperation objects.

        :param str feature_name: Name of the feature that is being enabled.  The meaning of this
            string is defined in the stage which handles this operation.
        :param Function callback: The function that gets called when this operation is complete or has
            failed.  The callback function must accept A PipelineOperation object which indicates
            the specific operation which has completed or failed.
        """
        super(EnableFeatureOperation, self).__init__(callback=callback)
        self.feature_name = feature_name


class DisableFeatureOperation(PipelineOperation):
    """
    A PipelineOperation object which tells the pipeline to "disable" a particular feature.

    A "feature" is just a string which represents some set of functionality that needs to be disabled, such as "C2D" or "Twin".

    This object has no notion of what it means to "disable" a feature.  That knowledge is handled by stages in the pipeline which might convert
    this operation to a more specific operation (such as an MQTT unsubscribe operation with a specific topic name).

    This operation is in the group of base operations because disconnecting is a common operation that many clients might need to do.

    Even though this is an base operation, it will most likely be handled by a more specific stage (such as an IoTHub or MQTT stage).
    """

    def __init__(self, feature_name, callback):
        """
        Initializer for DisableFeatureOperation objects.

        :param str feature_name: Name of the feature that is being disabled.  The meaning of this
            string is defined in the stage which handles this operation.
        :param Function callback: The function that gets called when this operation is complete or has
            failed.  The callback function must accept A PipelineOperation object which indicates
            the specific operation which has completed or failed.
        """
        super(DisableFeatureOperation, self).__init__(callback=callback)
        self.feature_name = feature_name


class UpdateSasTokenOperation(PipelineOperation):
    """
    A PipelineOperation object which contains a SAS token used for connecting.  This operation was likely initiated
    by a pipeline stage that knows how to generate SAS tokens.

    This operation is in the group of base operations because many different clients use the concept of a SAS token.

    Even though this is an base operation, it will most likely be generated and also handled by more specifics stages
    (such as IoTHub or MQTT stages).
    """

    def __init__(self, sas_token, callback):
        """
        Initializer for UpdateSasTokenOperation objects.

        :param str sas_token: The token string which will be used to authenticate with whatever
            service this pipeline connects with.
        :param Function callback: The function that gets called when this operation is complete or has
            failed.  The callback function must accept A PipelineOperation object which indicates
            the specific operation which has completed or failed.
        """
        super(UpdateSasTokenOperation, self).__init__(callback=callback)
        self.sas_token = sas_token


class RequestAndResponseOperation(PipelineOperation):
    """
    A PipelineOperation object which wraps the common operation of sending a request to iothub with a request_id ($rid)
    value and waiting for a response with the same $rid value.  This convention is used by both Twin and Provisioning
    features.

    Even though this is an base operation, it will most likely be generated and also handled by more specifics stages
    (such as IoTHub or MQTT stages).

    The type of the request payload and the response payload is undefined at this level.  The type of the payload is defined
    based on the type of request that is being executed.  If types need to be converted, that is the responsibility of
    the stage which creates this operation, and also the stage which executes on the operation.

    :ivar status_code: The status code returned by the response.  Any value under 300 is considered success.
    :type status_code: int
    :ivar response_body: The body of the response.
    :type response_body: Undefined
    :ivar query_params: Any query parameters that need to be sent with the request.
    Example is the id of the operation as returned by the initial provisioning request.
    """

    def __init__(
        self, request_type, method, resource_location, request_body, callback, query_params=None
    ):
        """
        Initializer for RequestAndResponseOperation objects

        :param str request_type: The type of request.  This is a string which is used by protocol-specific stages to
            generate the actual request.  For example, if request_type is "twin", then the iothub_mqtt stage will convert
            the request into an MQTT publish with topic that begins with $iothub/twin
        :param str method: The method for the request, in the REST sense of the word, such as "POST", "GET", etc.
        :param str resource_location: The resource that the method is acting on, in the REST sense of the word.
            For twin request with method "GET", this is most likely the string "/" which retrieves the entire twin
        :param request_body: The body of the request.  This is a required field, and a single space can be used to denote
            an empty body.
        :type request_body: Undefined
        :param Function callback: The function that gets called when this operation is complete or has
            failed.  The callback function must accept A PipelineOperation object which indicates
            the specific operation which has completed or failed.
        """
        super(RequestAndResponseOperation, self).__init__(callback=callback)
        self.request_type = request_type
        self.method = method
        self.resource_location = resource_location
        self.request_body = request_body
        self.status_code = None
        self.response_body = None
        self.query_params = query_params


class RequestOperation(PipelineOperation):
    """
    A PipelineOperation object which is the first part of an RequestAndResponseOperation operation (the request). The second
    part of the RequestAndResponseOperation operation (the response) is returned via an ResponseEvent event.

    Even though this is an base operation, it will most likely be generated and also handled by more specifics stages
    (such as IoTHub or MQTT stages).
    """

    def __init__(
        self,
        request_type,
        method,
        resource_location,
        request_body,
        request_id,
        callback,
        query_params=None,
    ):
        """
        Initializer for RequestOperation objects

        :param str request_type: The type of request.  This is a string which is used by protocol-specific stages to
            generate the actual request.  For example, if request_type is "twin", then the iothub_mqtt stage will convert
            the request into an MQTT publish with topic that begins with $iothub/twin
        :param str method: The method for the request, in the REST sense of the word, such as "POST", "GET", etc.
        :param str resource_location: The resource that the method is acting on, in the REST sense of the word.
            For twin request with method "GET", this is most likely the string "/" which retrieves the entire twin
        :param request_body: The body of the request.  This is a required field, and a single space can be used to denote
            an empty body.
        :type request_body: dict, str, int, float, bool, or None (JSON compatible values)
        :param Function callback: The function that gets called when this operation is complete or has
            failed.  The callback function must accept A PipelineOperation object which indicates
            the specific operation which has completed or failed.
        :type query_params: Any query parameters that need to be sent with the request.
        Example is the id of the operation as returned by the initial provisioning request.
        """
        super(RequestOperation, self).__init__(callback=callback)
        self.method = method
        self.resource_location = resource_location
        self.request_type = request_type
        self.request_body = request_body
        self.request_id = request_id
        self.query_params = query_params
