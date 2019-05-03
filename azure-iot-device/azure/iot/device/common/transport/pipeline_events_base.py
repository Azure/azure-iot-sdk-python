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
    """

    def __init__(self):
        self.name = self.__class__.__name__
        self.error = None
