# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module defines exceptions that may be raised from a pipeline"""

from azure.iot.device.common.chainable_exception import ChainableException


class PipelineException(ChainableException):
    """Generic pipeline exception"""

    pass


class OperationCancelled(PipelineException):
    """Operation was cancelled"""

    pass


class OperationError(PipelineException):
    """Error while executing an Operation"""

    pass


class PipelineTimeoutError(PipelineException):
    """
    Pipeline operation timed out
    """

    pass


class PipelineError(PipelineException):
    """Error in Pipeline"""

    pass
