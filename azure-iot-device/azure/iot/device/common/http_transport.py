# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging
import uuid
import threading
import json
from . import transport_exceptions as exceptions
from .pipeline import pipeline_thread


from six.moves import http_client

http_client.HTTPSConnection.debuglevel = 1

logger = logging.getLogger(__name__)


class HTTPTransport(object):
    """
    BLAH BLAH BLAH
    """

    def __init__(self, hostname, sas, ca_cert, x509_cert):
        """
        Constructor to instantiate an HTTP protocol wrapper.
        """
        self._hostname = hostname
        self._sas = sas
        self._ca_cert = ca_cert
        self._x509_cert = x509_cert

    def _format_headers(self, headers):
        # TODO: Right now I'm only doing sas token because I'm lazy and limited
        headers["Authorization"] = self._sas
        return headers

    @pipeline_thread.invoke_on_http_thread_nowait
    def connect(self, password):
        # Connect to the server specified when the object was created.
        # In the http client level, this connects to a TCP socket
        logger.info("connecting to http host")
        try:
            connection = http_client.HTTPSConnection(self._hostname)
            connection.connect()
            logger.debug("connection succeeded")
        except Exception as e:
            raise exceptions.ProtocolClientError(
                message="Unexpected HTTP failure during connect", cause=e
            )

    @pipeline_thread.invoke_on_http_thread_nowait
    def close(self):
        logger.info("closing connection to http host")
        try:
            connection = http_client.HTTPSConnection(self._hostname)
            connection.close()
            logger.debug("connection closed")
        except Exception as e:
            raise exceptions.ProtocolClientError(
                message="Unexpected HTTP failure during close", cause=e
            )

    """
    Some backstory on this.

    1) During discussion the concept of multiple simultaneous requests being made was brought up.
    Let's say you are a person and you want to make a request a bunch of times for some reason.
    We could do two things down here. First option, we could have a single HTTPSConnection established
    during instantation of the transport, in which case the HTTPSConnection would be shared among all
    requests! Cool? Maybe. I don't know precisely, but I'm pretty sure that if the conneciton is making a
    request, and then another thread comes along and using the same connection makes a request... well I just
    don't really know what's going to happen. So the second (and currently implemented) option for this is to
    create a new HTTPSConnection object every time we make a request, so that each request has it's own "connection".
    What does this mean? Not sure, but it seem safer.

    2) Initially I atomized each http_client call. We would create the client in one call, we would connect in another,
    disconnect in yet another. Seemed fine... ish. But then Carter was like hey we should make all the http_client specific
    stuff down here and only expose a relevant surface. What's a relevant surface for HTTP? Probably just request. So that's
    what I'm exposing. Everything, the insantiation of the HTTPSConnection, the sending of the request, the getting of the response,
    all happens in this one call, and that's better. Probably.
    """

    @pipeline_thread.invoke_on_http_thread_nowait
    def request(self, method, url, body=None, headers={}, *, callback):
        # Sends a complete request to the server
        logger.info("sending https request")
        try:
            logger.debug("creating to https connection")
            connection = http_client.HTTPSConnection(self._hostname)
            logger.debug("connecting to host tcp socket")
            connection.connect()
            logger.debug("connection succeeded")
            formatted_headers = self._format_headers(headers)
            connection.request(
                method, url, body=json.dumps(body).encode("utf-8"), headers=formatted_headers
            )
            response = connection.getresponse()
            logger.debug("response received: {}".format(response))
            logger.debug("closing connection to https host")
            connection.close()
            logger.debug("connection closed")
            logger.info("https request sent")
            callback()
        except Exception as e:
            raise exceptions.ProtocolClientError(
                message="Unexpected HTTPS failure during connect", cause=e
            )
