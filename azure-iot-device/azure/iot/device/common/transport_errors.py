# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module defines errors that may be raised from a transport"""


class OperationCancelledError(Exception):
    """
    Operation was cancelled.
    """

    pass


class ConnectionFailedError(Exception):
    """
    Connection failed to be established
    """

    pass


class ConnectionDroppedError(Exception):
    """
    Previously established connection was dropped
    """

    pass


class UnauthorizedError(Exception):
    """
    Service returned 401
    """

    pass


class ProtocolClientError(Exception):
    """
    Error returned from protocol client library
    """

    pass


# TODO: move this somewhere else
class PipelineError(Exception):
    """
    Error returned from transport pipeline
    """

    pass
