# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module defines exceptions that may be raised from a pipeline"""

from azure.iot.device.common.chainable_exception import ChainableException


class OperationCancelled(ChainableException):
    """
    Operation was cancelled.
    """

    pass
