# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module defines an exception surface, exposed as part of the pipeline API"""

# For now, present relevant transport errors as part of the Pipeline API surface
# so that they do not have to be duplicated at this layer.
# OK TODO This mimics the IotHub Case. Both IotHub and Provisioning needs to change
from azure.iot.device.common.pipeline.pipeline_exceptions import *
from azure.iot.device.common.transport_exceptions import (
    ConnectionFailedError,
    ConnectionDroppedError,
    # CT TODO: UnauthorizedError (the one from transport) should probably not surface out of
    # the pipeline due to confusion with the higher level service UnauthorizedError. It
    # should probably get turned into some other error instead (e.g. ConnectionFailedError).
    # But for now, this is a stopgap.
    UnauthorizedError,
    ProtocolClientError,
)
