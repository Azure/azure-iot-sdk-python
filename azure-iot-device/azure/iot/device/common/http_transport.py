# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import http.client
import logging
import ssl
import sys
import threading
import traceback
import weakref
from . import transport_exceptions as exceptions

logger = logging.getLogger(__name__)


# Default keepalive.  Paho sends a PINGREQ using this interval
# to make sure the connection is still open.
DEFAULT_KEEPALIVE = 60


class HTTPTransport(object):
    """
    BLAH BLAH BLAH
    """

    def __init__(
        self, client_id, hostname, username, ca_cert=None, x509_cert=None, websockets=False
    ):
        """
        Constructor to instantiate an HTTP Protocol Wrapper
        """
        self._authenticationProvider = client_id
        self._http = hostname
        self._username = username

    def _create_http_client(self):
        """
        Create the HTTP client object and assign all necessary event handler callbacks.
        """
        logger.info("creating http client")
