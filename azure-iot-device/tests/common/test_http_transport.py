# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
from azure.iot.device.common.http_transport import HTTPTransport, HTTP_TIMEOUT
from azure.iot.device.common.models import X509, ProxyOptions
from azure.iot.device.common import transport_exceptions as errors
import pytest
import logging
import ssl
import urllib3
import requests

logging.basicConfig(level=logging.DEBUG)

# Monkeypatch to bypass the decorator that runs on a separate thread
HTTPTransport.request = HTTPTransport.request.__wrapped__

fake_hostname = "fake.hostname"
fake_path = "path/to/resource"


fake_server_verification_cert = "__fake_server_verification_cert__"
fake_x509_cert = "__fake_x509_certificate__"
fake_cipher = "DHE-RSA-AES128-SHA"


@pytest.mark.describe("HTTPTransport - Instantiation")
class TestInstantiation(object):
    @pytest.fixture(
        params=["HTTP - No Auth", "HTTP - Auth", "SOCKS4", "SOCKS5 - No Auth", "SOCKS5 - Auth"]
    )
    def proxy_options(self, request):
        if "HTTP" in request.param:
            proxy_type = "HTTP"
        elif "SOCKS4" in request.param:
            proxy_type = "SOCKS4"
        else:
            proxy_type = "SOCKS5"

        if "No Auth" in request.param:
            proxy = ProxyOptions(proxy_type=proxy_type, proxy_addr="127.0.0.1", proxy_port=1080)
        else:
            proxy = ProxyOptions(
                proxy_type=proxy_type,
                proxy_addr="127.0.0.1",
                proxy_port=1080,
                proxy_username="fake_username",
                proxy_password="fake_password",
            )
        return proxy

    @pytest.mark.it("Stores the hostname for later use")
    def test_sets_required_parameters(self, mocker):

        mocker.patch.object(ssl, "SSLContext").return_value
        mocker.patch.object(HTTPTransport, "_create_ssl_context").return_value

        http_transport_object = HTTPTransport(
            hostname=fake_hostname,
            server_verification_cert=fake_server_verification_cert,
            x509_cert=fake_x509_cert,
            cipher=fake_cipher,
        )

        assert http_transport_object._hostname == fake_hostname

    @pytest.mark.it(
        "Creates a dictionary of proxies from the 'proxy_options' parameter, if the parameter is provided"
    )
    def test_proxy_format(self, proxy_options):
        http_transport_object = HTTPTransport(hostname=fake_hostname, proxy_options=proxy_options)

        if proxy_options.proxy_username and proxy_options.proxy_password:
            expected_proxy_string = "{username}:{password}@{address}:{port}".format(
                username=proxy_options.proxy_username,
                password=proxy_options.proxy_password,
                address=proxy_options.proxy_address,
                port=proxy_options.proxy_port,
            )
        else:
            expected_proxy_string = "{address}:{port}".format(
                address=proxy_options.proxy_address, port=proxy_options.proxy_port
            )

        if proxy_options.proxy_type == "HTTP":
            expected_proxy_string = "http://" + expected_proxy_string
        elif proxy_options.proxy_type == "SOCKS4":
            expected_proxy_string = "socks4://" + expected_proxy_string
        else:
            expected_proxy_string = "socks5://" + expected_proxy_string

        assert isinstance(http_transport_object._proxies, dict)
        assert http_transport_object._proxies["http"] == expected_proxy_string
        assert http_transport_object._proxies["https"] == expected_proxy_string

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
        "Configures TLS/SSL context using default certificates if protocol wrapper not instantiated with a server verification certificate"
    )
    def test_configures_tls_context_with_default_certs(self, mocker):
        mock_ssl_context = mocker.patch.object(ssl, "SSLContext").return_value

        HTTPTransport(hostname=fake_hostname)

        assert mock_ssl_context.load_default_certs.call_count == 1
        assert mock_ssl_context.load_default_certs.call_args == mocker.call()

    @pytest.mark.it(
        "Configures TLS/SSL context with provided server verification certificate if protocol wrapper instantiated with a server verification certificate"
    )
    def test_configures_tls_context_with_server_verification_certs(self, mocker):
        mock_ssl_context = mocker.patch.object(ssl, "SSLContext").return_value

        HTTPTransport(
            hostname=fake_hostname, server_verification_cert=fake_server_verification_cert
        )

        assert mock_ssl_context.load_verify_locations.call_count == 1
        assert mock_ssl_context.load_verify_locations.call_args == mocker.call(
            cadata=fake_server_verification_cert
        )

    @pytest.mark.it(
        "Configures TLS/SSL context with provided cipher if present during instantiation"
    )
    def test_configures_tls_context_with_cipher(self, mocker):
        mock_ssl_context = mocker.patch.object(ssl, "SSLContext").return_value

        HTTPTransport(hostname=fake_hostname, cipher=fake_cipher)

        assert mock_ssl_context.set_ciphers.call_count == 1
        assert mock_ssl_context.set_ciphers.call_args == mocker.call(fake_cipher)

    @pytest.mark.it("Configures TLS/SSL context with client-provided-certificate-chain like x509")
    def test_configures_tls_context_with_client_provided_certificate_chain(self, mocker):
        fake_client_cert = X509("fake_cert_file", "fake_key_file", "fake pass phrase")
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

    @pytest.mark.it(
        "Creates a custom requests HTTP Adapter that uses the configured SSL context when creating PoolManagers"
    )
    def test_http_adapter_pool_manager(self, mocker):
        # NOTE: This test involves mocking and testing deeper parts of the requests library stack
        # in order to show that the HTTPAdapter is functioning as intended. This naturally gets a
        # little messy from a unit testing perspective
        poolmanager_init_mock = mocker.patch.object(requests.adapters, "PoolManager")
        proxymanager_init_mock = mocker.patch.object(urllib3.poolmanager, "ProxyManager")
        socksproxymanager_init_mock = mocker.patch.object(requests.adapters, "SOCKSProxyManager")
        ssl_context_init_mock = mocker.patch.object(ssl, "SSLContext")
        mock_ssl_context = ssl_context_init_mock.return_value

        http_transport_object = HTTPTransport(hostname=fake_hostname)
        # SSL Context was only created once
        assert ssl_context_init_mock.call_count == 1
        # HTTP Adapter was set on the transport
        assert isinstance(http_transport_object._http_adapter, requests.adapters.HTTPAdapter)

        # Reset the poolmanager mock because it's already been called upon instantiation of the adapter
        # (We will manually test scenarios in which a PoolManager is instantiated)
        poolmanager_init_mock.reset_mock()

        # Basic PoolManager init scenario
        http_transport_object._http_adapter.init_poolmanager(
            connections=requests.adapters.DEFAULT_POOLSIZE,
            maxsize=requests.adapters.DEFAULT_POOLSIZE,
        )
        assert poolmanager_init_mock.call_count == 1
        assert poolmanager_init_mock.call_args[1]["ssl_context"] == mock_ssl_context

        # ProxyManager init scenario
        http_transport_object._http_adapter.proxy_manager_for(proxy="http://127.0.0.1")
        assert proxymanager_init_mock.call_count == 1
        assert proxymanager_init_mock.call_args[1]["ssl_context"] == mock_ssl_context

        # SOCKSProxyManager init scenario
        http_transport_object._http_adapter.proxy_manager_for(proxy="socks5://127.0.0.1")
        assert socksproxymanager_init_mock.call_count == 1
        assert socksproxymanager_init_mock.call_args[1]["ssl_context"] == mock_ssl_context

        # SSL Context was still only ever created once. This proves that the SSL context being
        # used above is the same one that was configured in a custom way
        assert ssl_context_init_mock.call_count == 1


@pytest.mark.describe("HTTPTransport - .request()")
class TestRequest(object):
    @pytest.fixture(autouse=True)
    def mock_requests_session(self, mocker):
        return mocker.patch.object(requests, "Session")

    @pytest.fixture
    def session(self, mock_requests_session):
        return mock_requests_session.return_value

    @pytest.fixture
    def transport(self):
        return HTTPTransport(hostname=fake_hostname)

    @pytest.fixture(params=["GET", "POST", "PUT", "PATCH", "DELETE"])
    def request_method(self, request):
        return request.param

    @pytest.mark.it(
        "Mounts the custom HTTP Adapter on a new requests Session before making a request"
    )
    def test_mount_adapter(self, mocker, transport, mock_requests_session, request_method):
        session = mock_requests_session.return_value
        session_method = getattr(session, request_method.lower())

        # Check that the request has not yet been made when mounted
        def check_request_not_made(*args):
            assert session_method.call_count == 0

        session.mount.side_effect = check_request_not_made

        # Session has not yet been created
        assert mock_requests_session.call_count == 0

        # Request
        transport.request(request_method, fake_path, mocker.MagicMock())

        # Session has been created
        assert mock_requests_session.call_count == 1
        assert mock_requests_session.call_args == mocker.call()
        assert session is mock_requests_session.return_value
        # Adapter has been mounted
        assert session.mount.call_count == 1
        assert session.mount.call_args == mocker.call("https://", transport._http_adapter)
        # Request was made after (see above side effect for proof that this happens after mount)
        assert session_method.call_count == 1

    @pytest.mark.it(
        "Makes a HTTP request with the new Session using the given parameters, stored hostname and stored proxy"
    )
    @pytest.mark.parametrize(
        "hostname, path, query_params, expected_url",
        [
            pytest.param(
                "fake.hostname",
                "path/to/resource",
                "",
                "https://fake.hostname/path/to/resource",
                id="No query parameters",
            ),
            pytest.param(
                "fake.hostname",
                "path/to/resource",
                "arg1=val1;arg2=val2",
                "https://fake.hostname/path/to/resource?arg1=val1;arg2=val2",
                id="With query parameters",
            ),
        ],
    )
    @pytest.mark.parametrize(
        "body", [pytest.param("", id="No body"), pytest.param("fake body", id="With body")]
    )
    @pytest.mark.parametrize(
        "headers",
        [pytest.param({}, id="No headers"), pytest.param({"Key": "Value"}, id="With headers")],
    )
    def test_request(
        self,
        mocker,
        transport,
        mock_requests_session,
        request_method,
        hostname,
        path,
        query_params,
        expected_url,
        body,
        headers,
    ):
        transport._hostname = hostname
        transport.request(
            method=request_method,
            path=path,
            callback=mocker.MagicMock(),
            body=body,
            headers=headers,
            query_params=query_params,
        )

        # New session was created
        assert mock_requests_session.call_count == 1
        assert mock_requests_session.call_args == mocker.call()
        session = mock_requests_session.return_value
        assert session.mount.call_count == 1
        assert session.mount.call_args == mocker.call("https://", transport._http_adapter)

        # The relevant method was called on the session
        session_method = getattr(session, request_method.lower())
        assert session_method.call_count == 1
        assert session_method.call_args == mocker.call(
            expected_url,
            data=body,
            headers=headers,
            proxies=transport._proxies,
            timeout=HTTP_TIMEOUT,
        )

    @pytest.mark.it(
        "Creates a response object containing the status code, reason and text from the HTTP response and returns it via the callback"
    )
    def test_returns_response(self, mocker, transport, session, request_method):
        session_method = getattr(session, request_method.lower())
        response = session_method.return_value
        cb_mock = mocker.MagicMock()

        transport.request(method=request_method, path=fake_path, callback=cb_mock)

        assert cb_mock.call_count == 1
        assert cb_mock.call_args == mocker.call(response=mocker.ANY)
        response_obj = cb_mock.call_args[1]["response"]
        assert response_obj["status_code"] == response.status_code
        assert response_obj["reason"] == response.reason
        assert response_obj["resp"] == response.text

    @pytest.mark.it(
        "Returns a ValueError via the callback if the request method provided is not valid"
    )
    def test_invalid_method(self, mocker, transport):
        cb_mock = mocker.MagicMock()
        transport.request(method="NOT A REAL METHOD", path=fake_path, callback=cb_mock)

        assert cb_mock.call_count == 1
        error = cb_mock.call_args[1]["error"]
        assert isinstance(error, ValueError)

    @pytest.mark.it(
        "Returns a requests.exceptions.Timeout via the callback if the HTTP request times out"
    )
    def test_request_timeout(self, mocker, transport, session, request_method):
        session_method = getattr(session, request_method.lower())
        session_method.side_effect = requests.exceptions.Timeout
        cb_mock = mocker.MagicMock()

        transport.request(method=request_method, path=fake_path, callback=cb_mock)

        assert cb_mock.call_count == 1
        error = cb_mock.call_args[1]["error"]
        assert isinstance(error, requests.exceptions.Timeout)

    @pytest.mark.it(
        "Returns a ProtocolClientError via the callback if making the HTTP request raises an unexpected Exception"
    )
    def test_client_raises_unexpected_error(
        self, mocker, transport, session, request_method, arbitrary_exception
    ):
        session_method = getattr(session, request_method.lower())
        session_method.side_effect = arbitrary_exception
        cb_mock = mocker.MagicMock()

        transport.request(method=request_method, path=fake_path, callback=cb_mock)

        assert cb_mock.call_count == 1
        error = cb_mock.call_args[1]["error"]
        assert isinstance(error, errors.ProtocolClientError)
        assert error.__cause__ is arbitrary_exception
