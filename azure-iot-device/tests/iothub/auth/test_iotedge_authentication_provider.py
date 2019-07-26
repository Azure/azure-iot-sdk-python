# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
import requests
import json
import base64
import six.moves.urllib as urllib
from azure.iot.device.iothub.auth.iotedge_authentication_provider import (
    IoTEdgeAuthenticationProvider,
    IoTEdgeHsm,
    IoTEdgeError,
)
from .shared_auth_tests import SharedBaseRenewableAuthenticationProviderInstantiationTests
from azure.iot.device import constant


@pytest.fixture
def gateway_hostname():
    return "__FAKE_GATEWAY_HOSTNAME__"


@pytest.fixture
def module_generation_id():
    return "__FAKE_MODULE_GENERATION_ID__"


@pytest.fixture
def workload_uri():
    return "http://__FAKE_WORKLOAD_URI__/"


@pytest.fixture
def api_version():
    return "__FAKE_API_VERSION__"


@pytest.fixture
def certificate():
    return "__FAKE_CERTIFICATE__"


@pytest.fixture
def mock_hsm(mocker, certificate):
    mock_hsm = mocker.patch(
        "azure.iot.device.iothub.auth.iotedge_authentication_provider.IoTEdgeHsm"
    ).return_value
    mock_hsm.get_trust_bundle.return_value = certificate
    return mock_hsm


@pytest.fixture
def hsm(module_id, module_generation_id, workload_uri, api_version):
    return IoTEdgeHsm(
        module_id=module_id,
        module_generation_id=module_generation_id,
        workload_uri=workload_uri,
        api_version=api_version,
    )


@pytest.fixture
def auth_provider(
    mock_hsm,
    hostname,
    device_id,
    module_id,
    gateway_hostname,
    module_generation_id,
    workload_uri,
    api_version,
):
    return IoTEdgeAuthenticationProvider(
        hostname=hostname,
        device_id=device_id,
        module_id=module_id,
        gateway_hostname=gateway_hostname,
        module_generation_id=module_generation_id,
        workload_uri=workload_uri,
        api_version=api_version,
    )


#######################################
# IoTEdgeAuthenticationProvider Tests #
#######################################


@pytest.mark.describe("IoTEdgeAuthenticationProvider - Instantiation")
class TestIoTEdgeAuthenticationProviderInstantiation(
    SharedBaseRenewableAuthenticationProviderInstantiationTests
):

    # TODO: Increase coverage by completing parent class

    @pytest.mark.it("Sets the gateway_hostname parameter as an instance attribute")
    def test_gateway_hostname(self, auth_provider, gateway_hostname):
        assert auth_provider.gateway_hostname == gateway_hostname

    @pytest.mark.it("Creates an instance of the IoTEdgeHsm")
    def test_creates_edge_hsm(self, auth_provider, mock_hsm):
        assert auth_provider.hsm is mock_hsm

    @pytest.mark.it(
        "Sets a certificate acquired from the IoTEdgeHsm as the ca_cert instance attribute"
    )
    def test_ca_cert_from_edge_hsm(self, auth_provider, mock_hsm):
        assert auth_provider.ca_cert is mock_hsm.get_trust_bundle.return_value
        assert mock_hsm.get_trust_bundle.call_count == 1


# TODO: Potentially get rid of this test class depending on how the parent class is tested/refactored.
# After all, we really shouldn't be testing convention-private methods.
@pytest.mark.describe("IoTEdgeAuthenticationProvider - ._sign()")
class TestIoTEdgeAuthenticationProviderSign(object):
    @pytest.mark.it("Requests signing of a string in the format '<quoted_resource_uri>/n<expiry>'")
    def test_sign_request(self, mocker, auth_provider, mock_hsm):
        uri = "my/resource/uri"
        expiry = 1234567
        string_to_sign = uri + "\n" + str(expiry)

        auth_provider._sign(uri, expiry)

        assert mock_hsm.sign.call_count == 1
        assert mock_hsm.sign.call_args == mocker.call(string_to_sign)

    @pytest.mark.it("Returns the signed string provided by the IoTEdgeHsm")
    def test_returns_signed_response(self, auth_provider, mock_hsm):
        uri = "my/resource/uri"
        expiry = 1234567

        signed_string = auth_provider._sign(uri, expiry)

        assert signed_string is mock_hsm.sign.return_value


####################
# IoTEdgeHsm Tests #
####################


@pytest.mark.describe("IoTEdgeHsm - Instantiation")
class TestIoTEdgeHsmInstantiation(object):
    @pytest.mark.it("URL encodes the module_id parameter and sets it as an instance attribute")
    def test_module_id(self, module_generation_id, workload_uri, api_version):
        my_module_id = "not url //encoded"
        expected_module_id = urllib.parse.quote(my_module_id)
        hsm = IoTEdgeHsm(
            module_id=my_module_id,
            module_generation_id=module_generation_id,
            workload_uri=workload_uri,
            api_version=api_version,
        )

        assert my_module_id != expected_module_id
        assert hsm.module_id == expected_module_id

    @pytest.mark.it("Sets the module_generation_id paramater as an instance attribute")
    def test_module_generation_id(self, hsm, module_generation_id):
        assert hsm.module_generation_id == module_generation_id

    @pytest.mark.it(
        "Converts the workload_uri parameter into requests-unixsocket format and sets it as an instance attribute"
    )
    def test_workload_uri(self, module_id, module_generation_id, api_version):
        my_workload_uri = "unix:///var/run/iotedge/workload.sock"
        expected_workload_uri = "http+unix://%2Fvar%2Frun%2Fiotedge%2Fworkload.sock/"
        hsm = IoTEdgeHsm(
            module_id=module_id,
            module_generation_id=module_generation_id,
            workload_uri=my_workload_uri,
            api_version=api_version,
        )

        assert hsm.workload_uri == expected_workload_uri

    @pytest.mark.it("Sets the api_version paramater as an instance attribute")
    def test_api_version(self, hsm, api_version):
        assert hsm.api_version == api_version


@pytest.mark.describe("IoTEdgeHsm - .get_trust_bundle()")
class TestIoTEdgeHsmGetTrustBundle(object):
    @pytest.mark.it("Makes an HTTP request to EdgeHub for the trust bundle")
    def test_requests_trust_bundle(self, mocker, hsm):
        mock_request_get = mocker.patch.object(requests, "get")
        expected_url = hsm.workload_uri + "trust-bundle"
        expected_params = {"api-version": hsm.api_version}
        expected_headers = {"User-Agent": urllib.parse.quote_plus(constant.USER_AGENT)}

        hsm.get_trust_bundle()

        assert mock_request_get.call_count == 1
        assert mock_request_get.call_args == mocker.call(
            expected_url, params=expected_params, headers=expected_headers
        )

    @pytest.mark.it("Returns the certificate from the trust bundle received from EdgeHub")
    def test_returns_received_trust_bundle(self, mocker, hsm, certificate):
        mock_request_get = mocker.patch.object(requests, "get")
        mock_response = mock_request_get.return_value
        mock_response.json.return_value = {"certificate": certificate}

        cert = hsm.get_trust_bundle()

        assert cert is certificate

    @pytest.mark.it("Raises IoTEdgeError if a bad request is made to EdgeHub")
    def test_bad_request(self, mocker, hsm):
        mock_request_get = mocker.patch.object(requests, "get")
        mock_response = mock_request_get.return_value
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError

        with pytest.raises(IoTEdgeError):
            hsm.get_trust_bundle()

    @pytest.mark.it("Raises IoTEdgeError if there is an error in json decoding the trust bundle")
    def test_bad_json(self, mocker, hsm):
        mock_request_get = mocker.patch.object(requests, "get")
        mock_response = mock_request_get.return_value
        mock_response.json.side_effect = ValueError

        with pytest.raises(IoTEdgeError):
            hsm.get_trust_bundle()

    @pytest.mark.it("Raises IoTEdgeError if the certificate is missing from the trust bundle")
    def test_bad_trust_bundle(self, mocker, hsm):
        mock_request_get = mocker.patch.object(requests, "get")
        mock_response = mock_request_get.return_value
        # Return an empty json dict with no 'certificate' key
        mock_response.json.return_value = {}

        with pytest.raises(IoTEdgeError):
            hsm.get_trust_bundle()


@pytest.mark.describe("IoTEdgeHsm - .sign()")
class TestIoTEdgeHsmSign(object):
    @pytest.mark.it("Makes an HTTP request to EdgeHub to sign a piece of string data")
    def test_requests_data_signing(self, mocker, hsm):
        data_str = "somedata"
        data_str_b64 = "c29tZWRhdGE="
        mock_request_post = mocker.patch.object(requests, "post")
        mock_request_post.return_value.json.return_value = {"digest": "somedigest"}
        expected_url = "{workload_uri}modules/{module_id}/genid/{module_generation_id}/sign".format(
            workload_uri=hsm.workload_uri,
            module_id=hsm.module_id,
            module_generation_id=hsm.module_generation_id,
        )
        expected_params = {"api-version": hsm.api_version}
        expected_headers = {"User-Agent": urllib.parse.quote_plus(constant.USER_AGENT)}
        expected_json = json.dumps({"keyId": "primary", "algo": "HMACSHA256", "data": data_str_b64})

        hsm.sign(data_str)

        assert mock_request_post.call_count == 1
        assert mock_request_post.call_args == mocker.call(
            url=expected_url, params=expected_params, headers=expected_headers, data=expected_json
        )

    @pytest.mark.it("Base64 encodes the string data in the request")
    def test_b64_encodes_data(self, mocker, hsm):
        # This test is actually implicitly tested in the first test, but it's
        # important to have an explicit test for it since it's a requirement
        data_str = "somedata"
        data_str_b64 = base64.b64encode(data_str.encode("utf-8")).decode()
        mock_request_post = mocker.patch.object(requests, "post")
        mock_request_post.return_value.json.return_value = {"digest": "somedigest"}

        hsm.sign(data_str)

        sent_data = json.loads(mock_request_post.call_args[1]["data"])["data"]

        assert data_str != data_str_b64
        assert sent_data == data_str_b64

    @pytest.mark.it("Returns the signed data received from EdgeHub")
    def test_returns_signed_data(self, mocker, hsm):
        expected_digest = "somedigest"
        mock_request_post = mocker.patch.object(requests, "post")
        mock_request_post.return_value.json.return_value = {"digest": expected_digest}

        signed_data = hsm.sign("somedata")

        assert signed_data == expected_digest

    @pytest.mark.it("URL encodes the signed data before returning it")
    def test_url_encodes_signed_data(self, mocker, hsm):
        raw_signed_data = "this digest will be encoded"
        expected_signed_data = urllib.parse.quote(raw_signed_data)
        mock_request_post = mocker.patch.object(requests, "post")
        mock_request_post.return_value.json.return_value = {"digest": raw_signed_data}

        signed_data = hsm.sign("somedata")

        assert raw_signed_data != expected_signed_data
        assert signed_data == expected_signed_data

    @pytest.mark.it("Raises IoTEdgeError if a bad request is made to EdgeHub")
    def test_bad_request(self, mocker, hsm):
        mock_request_post = mocker.patch.object(requests, "post")
        mock_response = mock_request_post.return_value
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError

        with pytest.raises(IoTEdgeError):
            hsm.sign("somedata")

    @pytest.mark.it("Raises IoTEdgeError if there is an error in json decoding the signed response")
    def test_bad_json(self, mocker, hsm):
        mock_request_post = mocker.patch.object(requests, "post")
        mock_response = mock_request_post.return_value
        mock_response.json.side_effect = ValueError

        with pytest.raises(IoTEdgeError):
            hsm.sign("somedata")

    @pytest.mark.it("Raises IoTEdgeError if the signed data is missing from the response")
    def test_bad_response(self, mocker, hsm):
        mock_request_post = mocker.patch.object(requests, "post")
        mock_response = mock_request_post.return_value
        mock_response.json.return_value = {}

        with pytest.raises(IoTEdgeError):
            hsm.sign("somedata")
