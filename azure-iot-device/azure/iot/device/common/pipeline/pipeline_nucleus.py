# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

from enum import Enum


class PipelineNucleus(object):
    """Contains data and information shared across the pipeline"""

    def __init__(self, pipeline_configuration):
        self.pipeline_configuration = pipeline_configuration
        self.connection_state = ConnectionState.DISCONNECTED

    @property
    def connected(self):
        # Only return True if fully connected
        return self.connection_state is ConnectionState.CONNECTED


class ConnectionState(Enum):
    CONNECTED = "CONNECTED"  # Client is connected (as far as it knows)
    DISCONNECTED = "DISCONNECTED"  # Client is disconnected
    CONNECTING = "CONNECTING"  # Client is in the process of connecting
    DISCONNECTING = "DISCONNECTING"  # Client is in the process of disconnecting
    REAUTHORIZING = "REAUTHORIZING"  # Client is in the process of reauthorizing
    # NOTE: Reauthorizing is the process of doing a disconnect, then a connect at transport level
