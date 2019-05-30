# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------


class PipelineEvent(object):
    """
    A base class for data objects representing events that travels up the pipeline.

    PipelineEvent objects are used for anything that happens inside the pipeine that
    cannot be attributed to a specific operation, such as a spontaneous disconnect.

    PipelineEvents flow up the pipeline until they reach the client.  Every stage
    has the opportunity to handle a given event.  If they don't handle it, they
    should pass it up to the next stage (this is the default behavior).  Stages
    have the opportunity to tie a PipelineEvent to a PipelineOperation object
    if they are waiting for a response for that particular operation.

    :ivar name: The name of the event.  This is used primarily for logging
    :type name: str
    """

    def __init__(self):
        """
        Initializer for PipelineEvent objects.
        """
        self.name = self.__class__.__name__


class IotResponseEvent(PipelineEvent):
    """
    A PipelineEvent object which is the second part of an SendIotRequestAndWaitForResponse operation
    (the response).  The SendIotRequestAndWaitForResponse represents the common operation of sending
    a request to iothub with a request_id ($rid) value and waiting for a response with
    the same $rid value.  This convention is used by both Twin and Provisioning features.

    The response represented by this event has not yet been matched to the corresponding
    SendIotRequest operation.  That matching is done by the CoordinateRequestAndResponse
    stage which takes the contents of this event and puts it into the SendIotRequestAndWaitForResponse
    operation with the matching $rid value.

    :ivar status_code: The status code returned by the response.  Any value under 300 is
      considered success.
    :type status_code: int
    :ivar request_id: The request ID which will eventually be used to match a SendIotRequest
      operation to this event.
    :type request: str
    :ivar response_body: The body of the response.
    :type request_body: str

    :ivar status_code:
    :type status: int
    :ivar respons_body:
    """

    def __init__(self, request_id, status_code, response_body):
        super(IotResponseEvent, self).__init()
        self.request_id = request_id
        self.status_code = status_code
        self.response_body = response_body
