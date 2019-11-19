# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import sys


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
          failed.  The callback function must accept A PipelineOperation object which indicates
          the specific operation which has completed or failed.
        """
        if self.__class__ == PipelineOperation:
            raise TypeError(
                "Cannot instantiate PipelineOperation object.  You need to use a derived class"
            )
        self.name = self.__class__.__name__
        self.callback = callback
        self.needs_connection = False
        self.completed = False


class ConnectOperation(PipelineOperation):
    """
    A PipelineOperation object which tells the pipeline to connect to whatever service it needs to connect to.

    This operation is in the group of base operations because connecting is a common operation that many clients might need to do.

    Even though this is an base operation, it will most likely be handled by a more specific stage (such as an IoTHub or MQTT stage).
    """

    def __init__(self, callback):
        self.retry_timer = None
        super(ConnectOperation, self).__init__(callback)


class ReconnectOperation(PipelineOperation):
    """
    A PipelineOperation object which tells the pipeline to reconnect to whatever service it is connected to.

    Clients will most-likely submit a Reconnect operation when some credential (such as a sas token) has changed and the protocol client
    needs to re-establish the connection to refresh the credentials

    This operation is in the group of base operations because reconnecting is a common operation that many clients might need to do.

    Even though this is an base operation, it will most likely be handled by a more specific stage (such as an IoTHub or MQTT stage).
    """

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
    :ivar registration_id: The registration ID is used to uniquely identify a device in the Device Provisioning Service.
    :type registration_id: str
    :ivar operation_id: The id of the operation as returned by the initial provisioning request.
    :type operation_id: str
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
        :param str registration_id: The registration ID is used to uniquely identify a device in the Device Provisioning Service.
        :param str operation_id: The id of the operation as returned by the initial provisioning request.
        """
        super(RequestOperation, self).__init__(callback=callback)
        self.method = method
        self.resource_location = resource_location
        self.request_type = request_type
        self.request_body = request_body
        self.request_id = request_id
        self.query_params = query_params
