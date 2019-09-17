# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module defines an exception surface, exposed as part of the pipeline API"""

# For now, present relevant transport errors as part of the Pipeline API surface
from azure.iot.device.common.pipeline import PipelineError
from azure.iot.device.common.transport_exceptions import (
    ConnectionFailedError,
    ConnectionDroppedError,
    UnauthorizedError,
    ProtocolClientError,
)
