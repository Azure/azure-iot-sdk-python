# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module defines exceptions that may be raised from a pipeline"""


class PipelineException(Exception):
    """Generic pipeline exception"""

    pass


class OperationCancelled(PipelineException):
    """Operation was cancelled"""

    pass


class OperationTimeout(PipelineException):
    """Pipeline operation timed out"""

    pass


class OperationError(PipelineException):
    """Error while executing an Operation"""

    pass


class PipelineNotRunning(PipelineException):
    """Pipeline is not currently running"""

    pass


class PipelineRuntimeError(PipelineException):
    """Error at runtime caused by incorrect pipeline configuration"""

    pass
