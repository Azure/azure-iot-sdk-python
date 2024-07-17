# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import logging
import ssl
import requests  # type: ignore
from . import transport_exceptions as exceptions
from .pipeline import pipeline_thread

logger = logging.getLogger(__name__)


# NOTE: There should probably be a more global timeout configuration, but for now this will do.
HTTP_TIMEOUT = 10


class HTTPTransport(object):
    """
    A wrapper class that provides an implementation-agnostic HTTP interface.
    """

    def __init__(
        self,
        hostname,
        server_verification_cert=None,
        x509_cert=None,
        cipher=None,
        proxy_options=None,
    ):
        """
        Constructor to instantiate an HTTP protocol wrapper.

        :param str hostname: Hostname or IP address of the remote host.
        :param str server_verification_cert: Certificate which can be used to validate a server-side TLS connection (optional).
        :param str cipher: Cipher string in OpenSSL cipher list format (optional)
        :param x509_cert: Certificate which can be used to authenticate connection to a server in lieu of a password (optional).
        :param proxy_options: Options for sending traffic through proxy servers.
        """
        self._hostname = hostname
        self._server_verification_cert = server_verification_cert
        self._x509_cert = x509_cert
        self._cipher = cipher
        self._proxies = format_proxies(proxy_options)
        self._http_adapter = self._create_http_adapter()

    def _create_http_adapter(self):
        """
        This method creates a custom HTTPAdapter for use with a requests library session.
        It will allow for use of a custom configured SSL context.
        """
        ssl_context = self._create_ssl_context()

        class CustomSSLContextHTTPAdapter(requests.adapters.HTTPAdapter):
            def init_poolmanager(self, *args, **kwargs):
                kwargs["ssl_context"] = ssl_context
                return super().init_poolmanager(*args, **kwargs)

            def proxy_manager_for(self, *args, **kwargs):
                kwargs["ssl_context"] = ssl_context
                return super().proxy_manager_for(*args, **kwargs)

        return CustomSSLContextHTTPAdapter()

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

        # Mount the transport adapter to a requests session
        session = requests.Session()
        session.mount("https://", self._http_adapter)

        # Format request URL
        # TODO: URL formation should be moved to pipeline_stages_iothub_http, I believe, as
        # depending on the operation this could have a different hostname, due to different
        # destinations. For now this isn't a problem yet, because no possible client can
        # support more than one HTTP operation
        # (Device can do File Upload but NOT Method Invoke, Module can do Method Invoke and NOT file upload)
        url = "https://{hostname}/{path}{query_params}".format(
            hostname=self._hostname,
            path=path,
            query_params="?" + query_params if query_params else "",
        )

        try:
            # Note that various configuration options are not set here due to them being set
            # via the HTTPAdapter that was mounted at session level.
            if method == "GET":
                response = session.get(
                    url, data=body, headers=headers, proxies=self._proxies, timeout=HTTP_TIMEOUT
                )
            elif method == "POST":
                response = session.post(
                    url, data=body, headers=headers, proxies=self._proxies, timeout=HTTP_TIMEOUT
                )
            elif method == "PUT":
                response = session.put(
                    url, data=body, headers=headers, proxies=self._proxies, timeout=HTTP_TIMEOUT
                )
            elif method == "PATCH":
                response = session.patch(
                    url, data=body, headers=headers, proxies=self._proxies, timeout=HTTP_TIMEOUT
                )
            elif method == "DELETE":
                response = session.delete(
                    url, data=body, headers=headers, proxies=self._proxies, timeout=HTTP_TIMEOUT
                )
            else:
                raise ValueError("Invalid method type: {}".format(method))
        except ValueError as e:
            # Allow ValueError to propagate
            callback(error=e)
        except requests.exceptions.Timeout as e:
            # Allow Timeout to propagate
            # NOTE: This breaks the convention in transports where we don't expose anything
            # but builtin exceptions and the exceptions defined in transport_exceptions.py.
            # However, we don't exactly have infrastructure to support timeout at Transport level.
            # For now, just expose it, and if/when we more broadly support timeout, this can change
            callback(error=e)
        except Exception as e:
            # Raise error via the callback
            new_err = exceptions.ProtocolClientError("Unexpected HTTPS failure during connect")
            new_err.__cause__ = e
            callback(error=new_err)
        else:
            # Return the data from the response via the callback
            response_obj = {
                "status_code": response.status_code,
                "reason": response.reason,
                "resp": response.text,
            }
            callback(response=response_obj)


def format_proxies(proxy_options):
    """
    Format the data from the proxy_options object into a format for use with the requests library
    """
    proxies = {}
    if proxy_options:
        # Basic address/port formatting
        proxy = "{address}:{port}".format(
            address=proxy_options.proxy_address, port=proxy_options.proxy_port
        )
        # Add credentials if necessary
        if proxy_options.proxy_username and proxy_options.proxy_password:
            auth = "{username}:{password}".format(
                username=proxy_options.proxy_username, password=proxy_options.proxy_password
            )
            proxy = auth + "@" + proxy
        # Set proxy for use on HTTP or HTTPS connections
        if proxy_options.proxy_type == "HTTP":
            proxies["http"] = "http://" + proxy
            proxies["https"] = "http://" + proxy
        elif proxy_options.proxy_type == "SOCKS4":
            proxies["http"] = "socks4://" + proxy
            proxies["https"] = "socks4://" + proxy
        elif proxy_options.proxy_type == "SOCKS5":
            proxies["http"] = "socks5://" + proxy
            proxies["https"] = "socks5://" + proxy
        else:
            # This should be unreachable due to validation on the ProxyOptions object
            raise ValueError("Invalid proxy type: {}".format(proxy_options.proxy_type))

    return proxies
