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

http_client.HTTPSConnection.debuglevel = 1


# def translate_error(body, response):
#     """
#     Codes_SRS_NODE_IOTHUB_REST_API_CLIENT_16_012: [Any error object returned by `translateError` shall inherit from the generic `Error` Javascript object and have 3 properties:
#     - `response` shall contain the `IncomingMessage` object returned by the HTTP layer.
#     - `reponseBody` shall contain the content of the HTTP response.
#     - `message` shall contain a human-readable error message.]
#     """
#     # errorContent = HttpBase.parseErrorBody(body)
#     # if errorContent:
#     #     message = errorContent.message
#     # else:
#     #     message = "Error: {}".format(body)
#     message = "fakemessage"
#     sc = response["statusCode"]
#     if sc == 400:
#         # `translateError` shall return an `ArgumentError` if the HTTP response status code is `400`.
#         error = "ArgumentError({})".format(message)
#     elif sc == 401:
#         # `translateError` shall return an `UnauthorizedError` if the HTTP response status code is `401`.
#         error = "UnauthorizedError({})".format(message)
#     elif sc == 403:
#         # `translateError` shall return an `TooManyDevicesError` if the HTTP response status code is `403`.
#         error = "ooManyDevicesError({})".format(message)
#     elif sc == 404:
#         if errorContent and errorContent.code == "DeviceNotFound":
#             # `translateError` shall return an `DeviceNotFoundError` if the HTTP response status code is `404` and if the error code within the body of the error response is `DeviceNotFound`.
#             error = "DeviceNotFoundError({})".format(message)
#         elif errorContent and errorContent.code == "IotHubNotFound":
#             # `translateError` shall return an `IotHubNotFoundError` if the HTTP response status code is `404` and if the error code within the body of the error response is `IotHubNotFound`.
#             error = "IotHubNotFoundError({})".format(message)
#         else:
#             error = "Error('Not found')"

#     elif sc == 408:
#         # `translateError` shall return a `DeviceTimeoutError` if the HTTP response status code is `408`.
#         error = "DeviceTimeoutError({})".format(message)

#     elif sc == 409:
#         # `translateError` shall return an `DeviceAlreadyExistsError` if the HTTP response status code is `409`.
#         error = "DeviceAlreadyExistsError({})".format(message)

#     elif sc == 412:
#         # `translateError` shall return an `InvalidEtagError` if the HTTP response status code is `412`.
#         error = "InvalidEtagError({})".format(message)

#     elif sc == 429:
#         # `translateError` shall return an `ThrottlingError` if the HTTP response status code is `429`.]
#         error = "ThrottlingError({})".format(message)

#     elif sc == 500:
#         # `translateError` shall return an `InternalServerError` if the HTTP response status code is `500`.
#         error = "InternalServerError({})".format(message)

#     elif sc == 502:
#         # `translateError` shall return a `BadDeviceResponseError` if the HTTP response status code is `502`.
#         error = "BadDeviceResponseError({})".format(message)

#     elif sc == 503:
#         # `translateError` shall return an `ServiceUnavailableError` if the HTTP response status code is `503`.
#         error = "ServiceUnavailableError({})".format(message)

#     elif sc == 504:
#         # `translateError` shall return a `GatewayTimeoutError` if the HTTP response status code is `504`.
#         error = "GatewayTimeoutError({})".format(message)

#     else:
#         # If the HTTP error code is unknown, `translateError` should return a generic Javascript `Error` object.
#         error = "Error({})".format(message)

#     # errorresponse = response
#     # error.responseBody = body
#     return error


class HTTPTransport(object):
    """
    BLAH BLAH BLAH
    """

    def __init__(self, hostname, ca_cert=None, x509_cert=None):
        """
        Constructor to instantiate an HTTP protocol wrapper.
        """
        self._hostname = hostname
        self._ca_cert = ca_cert
        self._x509_cert = x509_cert

    def _create_ssl_context(self):
        """
        This method creates the SSLContext object used by Paho to authenticate the connection.
        """
        logger.debug("creating a SSL context")
        ssl_context = ssl.SSLContext(protocol=ssl.PROTOCOL_TLSv1_2)

        if self._ca_cert:
            ssl_context.load_verify_locations(cadata=self._ca_cert)
        else:
            ssl_context.load_default_certs()
        ssl_context.verify_mode = ssl.CERT_REQUIRED
        ssl_context.check_hostname = True

        if self._x509_cert is not None:
            logger.debug("configuring SSL context with client-side certificate and key")
            ssl_context.load_cert_chain(
                self._x509_cert.certificate_file,
                self._x509_cert.key_file,
                self._x509_cert.pass_phrase,
            )

        return ssl_context

    # def _format_headers(self, headers):
    #     # TODO: Right now I'm only doing sas token because I'm lazy and limited
    #     formatted_headers = {}
    #     formatted_headers["Authorization"] = headers["sas"]
    #     return formatted_headers

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
    # TODO: This star syntax is incompatible with Python 2, change it so that the callback is in front of the optional params.
    def request(self, method, hostname, path, callback, body=None, headers={}, query_params=None):
        # Sends a complete request to the server
        logger.info("sending https request")
        try:
            logger.debug("creating to https connection")
            connection = http_client.HTTPSConnection(
                self._hostname, context=self._create_ssl_context()
            )
            logger.debug("connecting to host tcp socket")
            connection.connect()
            logger.debug("connection succeeded")
            # formatted_headers = self._format_headers(headers)
            url = "https://{hostname}/{path}?{query_params}".format(
                hostname=hostname, path=path, query_params=query_params
            )
            connection.request(method, url, body=json.dumps(body).encode("utf-8"), headers=headers)
            response = connection.getresponse()
            status_code = response.status
            response_string = response.read()

            logger.debug("response received.")
            logger.debug("closing connection to https host")
            connection.close()
            logger.debug("connection closed")
            logger.info("https request sent")
            callback(status_code, response_string)
        except Exception as e:
            # TODO: This exception needs to be returned in the callback, I cannot raise here because it's in a different thread than the pipeline
            # and would therefore do nothing. Instead pass an exception to the callback as an error if this is excepted.
            raise exceptions.ProtocolClientError(
                message="Unexpected HTTPS failure during connect", cause=e
            )
