# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""This module defines errors that may be raised from a transport"""


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


class NoConnectionError(Exception):
    """
    There is no connection
    """


class UnauthorizedError(Exception):
    """
    Authorization was rejected
    """

    pass


class ProtocolClientError(Exception):
    """
    Error returned from protocol client library
    """

    pass


class TlsExchangeAuthError(Exception):
    """
    Error returned when transport layer exchanges
    result in a SSLCertVerification error.
    """

    pass


class ProtocolProxyError(Exception):
    """
    All proxy-related errors.
    TODO : Not sure what to name it here. There is a class called Proxy Error already in Pysocks
    """

    pass
