# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import azure.iot.device.common.http_transport as http_transport
from azure.iot.device.common.http_transport import HTTPTransport
from azure.iot.device.common.models.x509 import X509
from six.moves import http_client
from azure.iot.device.common import transport_exceptions as errors
import pytest
import logging
import ssl
import threading


logging.basicConfig(level=logging.DEBUG)

fake_hostname = "__fake_hostname__"
fake_method = "__fake_method__"
fake_path = "__fake_path__"


fake_ca_cert = "__fake_ca_cert__"
fake_x509_cert = "__fake_x509_certificate__"


@pytest.mark.describe("HTTPTransport - Instantiation")
class TestInstantiation(object):
    @pytest.mark.it("Calls the HTTPTransport constructor with the required parameters")
    def test_calls_constructor(self, mocker):

        http_transport_constructor = mocker.patch.object(http_transport, "HTTPTransport")
        mocker.patch.object(ssl, "SSLContext").return_value
        mocker.patch.object(HTTPTransport, "_create_ssl_context").return_value

        http_transport.HTTPTransport(
            hostname=fake_hostname, ca_cert=fake_ca_cert, x509_cert=fake_x509_cert
        )

        assert http_transport_constructor.call_count == 1

        actual_constructor_args = http_transport_constructor.call_args[1]
        expected_constructor_args = mocker.call(
            hostname=fake_hostname, ca_cert=fake_ca_cert, x509_cert=fake_x509_cert
        )[2]
        assert actual_constructor_args == expected_constructor_args

    @pytest.mark.it("Sets the proper required instance parameters")
    def test_sets_required_parameters(self, mocker):

        mocker.patch.object(ssl, "SSLContext").return_value
        mocker.patch.object(HTTPTransport, "_create_ssl_context").return_value

        http_transport_object = HTTPTransport(
            hostname=fake_hostname, ca_cert=fake_ca_cert, x509_cert=fake_x509_cert
        )

        assert http_transport_object._hostname == fake_hostname
        assert http_transport_object._ca_cert == fake_ca_cert
        assert http_transport_object._x509_cert == fake_x509_cert

    @pytest.mark.it(
        "Configures TLS/SSL context to use TLS 1.2, require certificates and check hostname"
    )
    def test_configures_tls_context(self, mocker):
        mock_ssl_context_constructor = mocker.patch.object(ssl, "SSLContext")
        mock_ssl_context = mock_ssl_context_constructor.return_value

        HTTPTransport(hostname=fake_hostname)
        # Verify correctness of TLS/SSL Context
        assert mock_ssl_context_constructor.call_count == 1
        assert mock_ssl_context_constructor.call_args == mocker.call(protocol=ssl.PROTOCOL_TLSv1_2)
        assert mock_ssl_context.check_hostname is True
        assert mock_ssl_context.verify_mode == ssl.CERT_REQUIRED

    @pytest.mark.it(
        "Configures TLS/SSL context using default certificates if protocol wrapper not instantiated with a CA certificate"
    )
    def test_configures_tls_context_with_default_certs(self, mocker):
        mock_ssl_context = mocker.patch.object(ssl, "SSLContext").return_value

        HTTPTransport(hostname=fake_hostname)

        assert mock_ssl_context.load_default_certs.call_count == 1
        assert mock_ssl_context.load_default_certs.call_args == mocker.call()

    @pytest.mark.it(
        "Configures TLS/SSL context with provided CA certificates if protocol wrapper instantiated with a CA certificate"
    )
    def test_configures_tls_context_with_ca_certs(self, mocker):
        mock_ssl_context = mocker.patch.object(ssl, "SSLContext").return_value

        HTTPTransport(hostname=fake_hostname, ca_cert=fake_ca_cert)

        assert mock_ssl_context.load_verify_locations.call_count == 1
        assert mock_ssl_context.load_verify_locations.call_args == mocker.call(cadata=fake_ca_cert)

    @pytest.mark.it("Configures TLS/SSL context with client-provided-certificate-chain like x509")
    def test_configures_tls_context_with_client_provided_certificate_chain(self, mocker):
        fake_client_cert = X509("fantastic_beasts", "where_to_find_them", "alohomora")
        mock_ssl_context_constructor = mocker.patch.object(ssl, "SSLContext")
        mock_ssl_context = mock_ssl_context_constructor.return_value

        HTTPTransport(hostname=fake_hostname, x509_cert=fake_client_cert)

        assert mock_ssl_context.load_default_certs.call_count == 1
        assert mock_ssl_context.load_cert_chain.call_count == 1
        assert mock_ssl_context.load_cert_chain.call_args == mocker.call(
            fake_client_cert.certificate_file,
            fake_client_cert.key_file,
            fake_client_cert.pass_phrase,
        )


class HTTPTransportTestConfig(object):
    @pytest.fixture
    def mock_http_client_constructor(self, mocker):
        mocker.patch.object(ssl, "SSLContext").return_value
        mocker.patch.object(HTTPTransport, "_create_ssl_context").return_value
        mock_client_constructor = mocker.patch.object(http_client, "HTTPSConnection", autospec=True)
        mock_client = mock_client_constructor.return_value
        response_value = mock_client.getresponse.return_value
        response_value.status = 1234
        response_value.reason = "__fake_reason__"
        response_value.read.return_value = "__fake_response_read_value__"
        return mock_client_constructor

    @pytest.fixture
    def transport(self, mock_http_client_constructor):
        return HTTPTransport(hostname=fake_hostname)


@pytest.mark.describe("HTTPTransport - .request()")
class TestRequest(HTTPTransportTestConfig):
    @pytest.mark.it("Generates a unique HTTP Client connection for each request")
    def test_creates_http_connection_object(self, mocker, transport, mock_http_client_constructor):
        # We call .result because we need to block for the Future to complete before moving on.
        transport.request(fake_method, fake_path, mocker.MagicMock()).result()
        assert mock_http_client_constructor.call_count == 1

        transport.request(fake_method, fake_path, mocker.MagicMock()).result()
        assert mock_http_client_constructor.call_count == 2

    @pytest.mark.it("Uses the HTTP Transport SSL Context.")
    def test_uses_ssl_context(self, mocker, transport, mock_http_client_constructor):
        ssl_context_mocker = transport._ssl_context
        done = transport.request(fake_method, fake_path, mocker.MagicMock())
        done.result()

        assert mock_http_client_constructor.call_count == 1
        assert mock_http_client_constructor.call_args[1]["context"] == ssl_context_mocker

    @pytest.mark.it("Formats the request URL correctly given a path and no query parameters.")
    def test_formats_http_client_request_with_only_method_and_path(
        self, mocker, transport, mock_http_client_constructor
    ):
        mock_http_client_request = mock_http_client_constructor.return_value.request
        fake_method = "__fake_method__"
        fake_path = "__fake_path__"
        expected_url = "https://{}/{}".format(fake_hostname, fake_path)
        done = transport.request(fake_method, fake_path, mocker.MagicMock())
        done.result()

        assert mock_http_client_constructor.call_count == 1
        assert mock_http_client_request.call_count == 1
        assert mock_http_client_request.call_args[0][0] == fake_method
        assert mock_http_client_request.call_args[0][1] == expected_url
        assert mock_http_client_request.call_args[1]["body"] == ""
        assert bool(mock_http_client_request.call_args[1]["headers"]) is False

    @pytest.mark.it("Formats the request URL correctly given a path and query parameters.")
    def test_formats_http_client_request_with_method_path_and_query_params(
        self, mocker, transport, mock_http_client_constructor
    ):
        mock_http_client_request = mock_http_client_constructor.return_value.request
        fake_method = "__fake_method__"
        fake_path = "__fake_path__"
        fake_query_params = "__fake_query_params__"
        expected_url = "https://{}/{}?{}".format(fake_hostname, fake_path, fake_query_params)
        # output = {"response": None, "error": None}

        # def request_callback(response=None, error=None):

        done = transport.request(
            fake_method, fake_path, mocker.MagicMock(), query_params=fake_query_params
        )
        done.result()
        assert mock_http_client_constructor.call_count == 1
        assert mock_http_client_request.call_count == 1
        assert mock_http_client_request.call_args[0][0] == fake_method
        assert mock_http_client_request.call_args[0][1] == expected_url
        assert mock_http_client_request.call_args[1]["body"] == ""
        assert bool(mock_http_client_request.call_args[1]["headers"]) is False

    @pytest.mark.it(
        "Calls HTTP Client Connection request method with correct method, url, body, and headers."
    )
    @pytest.mark.parametrize(
        "method, path, query_params, body, headers",
        [
            pytest.param("__fake_method__", "__fake_path__", None, None, None),
            pytest.param("__fake_method__", "__fake_path__", "", "", ""),
            pytest.param("__fake_method__", "__fake_path__", "__fake_query_params__", None, None),
            pytest.param(
                "__fake_method__", "__fake_path__", "__fake_query_params__", "__fake_body__", None
            ),
            pytest.param(
                "__fake_method__",
                "__fake_path__",
                "__fake_query_params__",
                "__fake_body__",
                "__fake_headers__",
            ),
        ],
    )
    def test_calls_http_client_request_with_given_parameters(
        self,
        mocker,
        transport,
        mock_http_client_constructor,
        method,
        path,
        query_params,
        body,
        headers,
    ):
        mock_http_client_request = mock_http_client_constructor.return_value.request
        if query_params:
            expected_url = "https://{}/{}?{}".format(fake_hostname, path, query_params)
        else:
            expected_url = "https://{}/{}".format(fake_hostname, path)

        cb = mocker.MagicMock()
        done = transport.request(
            method, path, cb, body=body, headers=headers, query_params=query_params
        )
        done.result()
        assert mock_http_client_constructor.call_count == 1
        assert mock_http_client_request.call_count == 1
        assert mock_http_client_request.call_args[0][0] == method
        assert mock_http_client_request.call_args[0][1] == expected_url

        actual_body = mock_http_client_request.call_args[1]["body"]
        actual_headers = mock_http_client_request.call_args[1]["headers"]
        if body:
            assert actual_body == body
        else:
            assert not bool(actual_body)
        if headers:
            assert actual_headers == headers
        else:
            assert not bool(actual_headers)

    @pytest.mark.it(
        "Creates a response object with a status code, reason, and unformatted HTTP response and returns it via the callback."
    )
    def test_returns_response_on_success(self, mocker, transport, mock_http_client_constructor):
        cb = mocker.MagicMock()
        done = transport.request(fake_method, fake_path, cb)
        done.result()

        assert mock_http_client_constructor.call_count == 1
        assert cb.call_count == 1
        assert cb.call_args[1]["response"]["status_code"] == 1234
        assert cb.call_args[1]["response"]["reason"] == "__fake_reason__"
        assert cb.call_args[1]["response"]["resp"] == "__fake_response_read_value__"

    @pytest.mark.it("Raises a ProtocolClientError if request raises an unexpected Exception")
    def test_client_raises_unexpected_error(
        self, mocker, transport, mock_http_client_constructor, arbitrary_exception
    ):
        mock_http_client_constructor.return_value.connect.side_effect = arbitrary_exception
        cb = mocker.MagicMock()
        done = transport.request(fake_method, fake_path, cb)
        done.result()
        assert cb.call_args[1]["error"].__cause__ is arbitrary_exception
