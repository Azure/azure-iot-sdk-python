# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------


class PipelineOperation(object):
    """
    A base class for data objects representing operations that travels down the pipeline.

    Each PipelineOperation object represents a single asyncroneous operation that is performed
    by the pipeline. The PipelineOperation objects travel through "stages" of the pipeline,
    and each stage has the opportunity to act on each specific operation that it
    receives.  If a stage does not handle a particular operation, it needs to pass it to the
    next stage.  If the operation gets to the end of the pipeline without being handled
    (completed), then it is treated as an error.

    :ivar name: The name of the operation.  This, rather than the `isinstance` function, is
      used by stages to decide if they want to handle on a particular operation object.
    :type name: str
    :ivar callback: The callback that is called when the operation is completed, either
      successfully or with a failure.
    :type callback: Function
    :ivar needs_connection: This is an attribute that indicates whether a particular operation
      requires a connection to operate.  This is currently used by the EnsureConnection
      stage, but this functionality will be revamped shortly.
    :type needs_connection: Boolean
    :ivar error: The presence of a value in the error attribute indicates that the operation failed,
      absense of this value indicates that the operation either succeeded or hasn't been handled yet.
    :type error: Error
    """

    def __init__(self, callback=None):
        """
        Initializer for PipelineOperation objects.

        :param Function callback: The function that gets called when this operation is complete or has
          failed.  The callback function must accept A PipelineOperation object which indicates
          the specific operation which has completed or failed.
        """
        self.name = self.__class__.__name__
        self.callback = callback
        self.needs_connection = False
        self.error = None


class Connect(PipelineOperation):
    """
    A PipelineOperation object which tells the pipeline to connect to whatever service it needs to connect to.

    This operation is in the group of base operations because connecting is a common operation that many clients might need to do.

    Even though this is an base operation, it will most likely be handled by a more specific stage (such as an IotHub or Mqtt stage).
    """

    pass


class Reconnect(PipelineOperation):
    """
    A PipelineOperation object which tells the pipeline to reconnect to whatever service it is connected to.

    Clients will most-likely submit a Reconnect operation when some credential (such as a sas token) has changed and the transport
    needs to re-establish the connection to refresh the credentials

    This operation is in the group of base operations because reconnecting is a common operation that many clients might need to do.

    Even though this is an base operation, it will most likely be handled by a more specific stage (such as an IotHub or Mqtt stage).
    """

    pass


class Disconnect(PipelineOperation):
    """
    A PipelineOperation object which tells the pipeline to disconnect from whatever service it might be connected to.

    This operation is in the group of base operations because disconnecting is a common operation that many clients might need to do.

    Even though this is an base operation, it will most likely be handled by a more specific stage (such as an IotHub or Mqtt stage).
    """

    pass


class EnableFeature(PipelineOperation):
    """
    A PipelineOperation object which tells the pipeline to "enable" a particular feature.

    A "feature" is just a string which represents some set of functionality that needs to be enabled, such as "C2D" or "Twin".

    This object has no notion of what it means to "enable" a feature.  That knowledge is handled by stages in the pipeline which might convert
    this operation to a more specific operation (such as an MQTT subscribe operation with a specific topic name).

    This operation is in the group of base operations because disconnecting is a common operation that many clients might need to do.

    Even though this is an base operation, it will most likely be handled by a more specific stage (such as an IotHub or Mqtt stage).
    """

    def __init__(self, feature_name, callback=None):
        """
        Initializer for EnableFeature objects.

        :param Function callback: The function that gets called when this operation is complete or has
          failed.  The callback function must accept A PipelineOperation object which indicates
          the specific operation which has completed or failed.
        """
        super(EnableFeature, self).__init__(callback=callback)
        self.feature_name = feature_name


class DisableFeature(PipelineOperation):
    """
    A PipelineOperation object which tells the pipeline to "disable" a particular feature.

    A "feature" is just a string which represents some set of functionality that needs to be disabled, such as "C2D" or "Twin".

    This object has no notion of what it means to "disable" a feature.  That knowledge is handled by stages in the pipeline which might convert
    this operation to a more specific operation (such as an MQTT unsubscribe operation with a specific topic name).

    This operation is in the group of base operations because disconnecting is a common operation that many clients might need to do.

    Even though this is an base operation, it will most likely be handled by a more specific stage (such as an IotHub or Mqtt stage).
    """

    def __init__(self, feature_name, callback=None):
        """
        Initializer for DisableFeature objects.

        :param Function callback: The function that gets called when this operation is complete or has
          failed.  The callback function must accept A PipelineOperation object which indicates
          the specific operation which has completed or failed.
        """
        super(DisableFeature, self).__init__(callback=callback)
        self.feature_name = feature_name


class SetSasToken(PipelineOperation):
    """
    A PipelineOperation object which contains a SAS token used for connecting.  This operation was likely initiated
    by a pipeline stage that knows how to generate SAS tokens based on some other operation (such as SetAuthProvider)

    This operation is in the group of base operations because many different clients use the concept of a SAS token.

    Even though this is an base operation, it will most likely be generated and also handled by more specifics stages
    (such as IotHub or Mqtt stages).
    """

    def __init__(self, sas_token, callback=None):
        """
        Initializer for SetSasToken objects.

        :param Function callback: The function that gets called when this operation is complete or has
          failed.  The callback function must accept A PipelineOperation object which indicates
          the specific operation which has completed or failed.
        """
        super(SetSasToken, self).__init__(callback=callback)
        self.sas_token = sas_token
