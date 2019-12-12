# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

# import azure.iot.device.common.http_transport as http_transport
from azure.iot.device.common.http_transport import HTTPTransport
from azure.iot.device.common.models.x509 import X509
from six.moves import http_client
from azure.iot.device.common import transport_exceptions as errors
import pytest
import logging
import ssl
import asyncio
import threading


logging.basicConfig(level=logging.DEBUG)

fake_hostname = "__fake_hostname__"


@pytest.mark.describe("HTTPTransport - Instantiation")
class TestInstantiation(object):
    @pytest.mark.it("Sets the proper required instance parameters")
    def test_sets_required_parameters(self, mocker):
        fake_ca_cert = "__fake_ca_cert__"
        fake_x509_cert = "__fake_x509_certificate__"

        mocker.spy(HTTPTransport, "__init__")
        mocker.patch.object(ssl, "SSLContext").return_value
        mocker.patch.object(HTTPTransport, "_create_ssl_context").return_value

        http_transport_object = HTTPTransport(
            hostname=fake_hostname, ca_cert=fake_ca_cert, x509_cert=fake_x509_cert
        )

        assert http_transport_object.__init__.call_args == mocker.call(
            mocker.ANY, hostname=fake_hostname, ca_cert=fake_ca_cert, x509_cert=fake_x509_cert
        )
        assert http_transport_object.__init__.call_count == 1
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
        fake_ca_cert = "__fake_ca_cert__"
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


# @pytest.fixture
# def mock_http_client(mocker):
#     mock_http_connection_constructor = mocker.patch.object(http_client, "HTTPSConnection")

#     return mock_http_connection_constructor

# @pytest.fixture
# def transport(mocker, mock_http_client):
#     mocker.patch("ssl.SSLContext").return_value
#     return


class HTTPTransportTestConfig(object):
    @pytest.fixture
    def mock_http_client_constructor(self, mocker):
        mock_client_constructor = mocker.patch.object(http_client, "HTTPSConnection", autospec=True)
        mock_client = mock_client_constructor.return_value
        response_value = mock_client.getresponse.return_value
        response_value.status = 1234
        response_value.reason = "__fake_reason__"
        response_value.read.return_value = "__fake_response_read_value__"
        # mock_client.getresponse.return_value = response_value
        # stage = cls_type(**init_kwargs)
        # stage.pipeline_root = pipeline_stages_base.PipelineRootStage(
        #     pipeline_configuration=mocker.MagicMock()
        # )
        # stage.send_op_down = mocker.MagicMock()

        # # Set up the Transport on the stage
        # op = pipeline_ops_http.SetHTTPConnectionArgsOperation(
        #     hostname="fake_hostname",
        #     ca_cert="fake_ca_cert",
        #     client_cert="fake_client_cert",
        #     sas_token="fake_sas_token",
        #     callback=mocker.MagicMock(),
        # )
        # stage.run_op(op)
        # assert stage.transport is mock_transport.return_value

        return mock_client_constructor


@pytest.mark.describe("HTTPTransport - .request()")
class TestRequest(HTTPTransportTestConfig):
    @pytest.mark.it("Generates a unique HTTP Client connection for each request")
    def test_creates_http_connection_object(self, mocker, mock_http_client_constructor):
        transport = HTTPTransport(hostname=fake_hostname)
        fake_method = "__fake_method__"
        fake_path = "__fake_path__"
        # def request_callback(response, error):
        # mocker.patch("concurrent.futures")
        # original_thread = threading.current_thread()

        # future.result()
        output = {"response": None, "error": None}

        def request_callback(response=None, error=None):
            # threading.main_thread()
            output["response"] = response
            output["error"] = error

        done = transport.request(fake_method, fake_path, request_callback)
        done.result()
        assert mock_http_client_constructor.call_count == 1
        assert output["error"] is None
        assert output["response"] is not None
        assert output["response"]["status_code"] == 1234
        assert output["response"]["reason"] == "__fake_reason__"
        assert output["response"]["resp"] == "__fake_response_read_value__"
