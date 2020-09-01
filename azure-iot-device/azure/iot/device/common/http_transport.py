# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging
import uuid
import threading
import json
import ssl
from . import transport_exceptions as exceptions
from .pipeline import pipeline_thread
from six.moves import http_client

logger = logging.getLogger(__name__)


class HTTPTransport(object):
    """
    A wrapper class that provides an implementation-agnostic HTTP interface.
    """

    def __init__(self, hostname, server_verification_cert=None, x509_cert=None, cipher=None):
        """
        Constructor to instantiate an HTTP protocol wrapper.

        :param str hostname: Hostname or IP address of the remote host.
        :param str server_verification_cert: Certificate which can be used to validate a server-side TLS connection (optional).
        :param str cipher: Cipher string in OpenSSL cipher list format (optional)
        :param x509_cert: Certificate which can be used to authenticate connection to a server in lieu of a password (optional).
        """
        self._hostname = hostname
        self._server_verification_cert = server_verification_cert
        self._x509_cert = x509_cert
        self._cipher = cipher
        self._ssl_context = self._create_ssl_context()

    def _create_ssl_context(self):
        """
        This method creates the SSLContext object used to authenticate the connection. The generated context is used by the http_client and is necessary when authenticating using a self-signed X509 cert or trusted X509 cert
        """
        logger.debug("creating a SSL context")
        ssl_context = ssl.SSLContext(protocol=ssl.PROTOCOL_TLSv1_2)

        if self._server_verification_cert:
            ssl_context.load_verify_locations(cadata=self._server_verification_cert)
        else:
            ssl_context.load_default_certs()

        if self._cipher:
            try:
                ssl_context.set_ciphers(self._cipher)
            except ssl.SSLError as e:
                # TODO: custom error with more detail?
                raise e

        if self._x509_cert is not None:
            logger.debug("configuring SSL context with client-side certificate and key")
            ssl_context.load_cert_chain(
                self._x509_cert.certificate_file,
                self._x509_cert.key_file,
                self._x509_cert.pass_phrase,
            )

        ssl_context.verify_mode = ssl.CERT_REQUIRED
        ssl_context.check_hostname = True

        return ssl_context

    @pipeline_thread.invoke_on_http_thread_nowait
    def request(self, method, path, callback, body="", headers={}, query_params=""):
        """
        This method creates a connection to a remote host, sends a request to that host, and then waits for and reads the response from that request.

        :param str method: The request method (e.g. "POST")
        :param str path: The path for the URL
        :param Function callback: The function that gets called when this operation is complete or has failed. The callback function must accept an error and a response dictionary, where the response dictionary contains a status code, a reason, and a response string.
        :param str body: The body of the HTTP request to be sent following the headers.
        :param dict headers: A dictionary that provides extra HTTP headers to be sent with the request.
        :param str query_params: The optional query parameters to be appended at the end of the URL.
        """
        # Sends a complete request to the server
        logger.info("sending https {} request to {} .".format(method, path))
        try:
            logger.debug("creating an https connection")
            connection = http_client.HTTPSConnection(self._hostname, context=self._ssl_context)
            logger.debug("connecting to host tcp socket")
            connection.connect()
            logger.debug("connection succeeded")
            # TODO: URL formation should be moved to pipeline_stages_iothub_http, I believe, as
            # depending on the operation this could have a different hostname, due to different
            # destinations. For now this isn't a problem yet, because no possible client can
            # support more than one HTTP operation
            # (Device can do File Upload but NOT Method Invoke, Module can do Method Inovke and NOT file upload)
            url = "https://{hostname}/{path}{query_params}".format(
                hostname=self._hostname,
                path=path,
                query_params="?" + query_params if query_params else "",
            )
            logger.debug("Sending Request to HTTP URL: {}".format(url))
            logger.debug("HTTP Headers: {}".format(headers))
            logger.debug("HTTP Body: {}".format(body))
            connection.request(method, url, body=body, headers=headers)
            response = connection.getresponse()
            status_code = response.status
            reason = response.reason
            response_string = response.read()

            logger.debug("response received")
            logger.debug("closing connection to https host")
            connection.close()
            logger.debug("connection closed")
            logger.info(
                "https {} request sent to {}, and {} response received.".format(
                    method, path, status_code
                )
            )
            response_obj = {"status_code": status_code, "reason": reason, "resp": response_string}
            callback(response=response_obj)
        except Exception as e:
            logger.info("Error in HTTP Transport: {}".format(e))
            callback(
                error=exceptions.ProtocolClientError(
                    message="Unexpected HTTPS failure during connect", cause=e
                )
            )
