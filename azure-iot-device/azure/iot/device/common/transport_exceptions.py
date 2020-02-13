# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module defines errors that may be raised from a transport"""

from .chainable_exception import ChainableException


class ConnectionFailedError(ChainableException):
    """
    Connection failed to be established
    """

    pass


class ConnectionDroppedError(ChainableException):
    """
    Previously established connection was dropped
    """

    pass


class UnauthorizedError(ChainableException):
    """
    Authorization was rejected
    """

    pass


class ProtocolClientError(ChainableException):
    """
    Error returned from protocol client library
    """

    pass


class TlsExchangeAuthError(ChainableException):
    """
    Error returned when transport layer exchanges
    result in a SSLCertVerification error.
    """

    pass
