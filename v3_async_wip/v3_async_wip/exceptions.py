# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module defines exceptions used by other modules"""


# Recoverable
class RecoverableException(Exception):
    """An exception that may be recoverable"""

    pass


class ConnectionFailedError(RecoverableException):
    pass


# Non-recoverable
class NonRecoverableException(Exception):
    """A exception that is not recoverable"""

    pass


class AuthorizationError(NonRecoverableException):
    pass
