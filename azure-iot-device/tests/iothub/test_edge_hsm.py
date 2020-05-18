# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
import logging
import requests
import json
import base64
from six.moves import urllib
from azure.iot.device.iothub.edge_hsm import IoTEdgeHsm, IoTEdgeError
from azure.iot.device import product_info


logging.basicConfig(level=logging.DEBUG)


@pytest.fixture
def edge_hsm():
    return IoTEdgeHsm(
        module_id="my_module_id",
        generation_id="module_generation_id",
        workload_uri="unix:///var/run/iotedge/workload.sock",
        api_version="my_api_version",
    )


@pytest.mark.describe("IoTEdgeHsm - Instantiation")
class TestIoTEdgeHsmInstantiation(object):
    @pytest.mark.it("URL encodes the provided module_id parameter and sets it as an attribute")
    def test_encode_and_set_module_id(self):
        module_id = "my_module_id"
        generation_id = "my_generation_id"
        api_version = "my_api_version"
        workload_uri = "unix:///var/run/iotedge/workload.sock"

        edge_hsm = IoTEdgeHsm(
            module_id=module_id,
            generation_id=generation_id,
            workload_uri=workload_uri,
            api_version=api_version,
        )

        assert edge_hsm.module_id == urllib.parse.quote(module_id, safe="")

    @pytest.mark.it(
        "Formats the provided workload_uri parameter for use with the requests library and sets it as an attribute"
    )
    @pytest.mark.parametrize(
        "workload_uri, expected_formatted_uri",
        [
            pytest.param(
                "unix:///var/run/iotedge/workload.sock",
                "http+unix://%2Fvar%2Frun%2Fiotedge%2Fworkload.sock/",
                id="Domain Socket URI",
            ),
            pytest.param("http://127.0.0.1:15580", "http://127.0.0.1:15580/", id="IP Address URI"),
        ],
    )
    def test_workload_uri_formatting(self, workload_uri, expected_formatted_uri):
        module_id = "my_module_id"
        generation_id = "my_generation_id"
        api_version = "my_api_version"

        edge_hsm = IoTEdgeHsm(
            module_id=module_id,
            generation_id=generation_id,
            workload_uri=workload_uri,
            api_version=api_version,
        )

        assert edge_hsm.workload_uri == expected_formatted_uri

    @pytest.mark.it("Sets the provided generation_id parameter as an attribute")
    def test_set_generation_id(self):
        module_id = "my_module_id"
        generation_id = "my_generation_id"
        api_version = "my_api_version"
        workload_uri = "unix:///var/run/iotedge/workload.sock"

        edge_hsm = IoTEdgeHsm(
            module_id=module_id,
            generation_id=generation_id,
            workload_uri=workload_uri,
            api_version=api_version,
        )

        assert edge_hsm.generation_id == generation_id

    @pytest.mark.it("Sets the provided api_version parameter as an attribute")
    def test_set_api_verison(self):
        module_id = "my_module_id"
        generation_id = "my_generation_id"
        api_version = "my_api_version"
        workload_uri = "unix:///var/run/iotedge/workload.sock"

        edge_hsm = IoTEdgeHsm(
            module_id=module_id,
            generation_id=generation_id,
            workload_uri=workload_uri,
            api_version=api_version,
        )

        assert edge_hsm.api_version == api_version


@pytest.mark.describe("IoTEdgeHsm - .get_certificate()")
class TestIoTEdgeHsmGetCertificate(object):
    @pytest.mark.it("Sends an HTTP GET request to retrieve the trust bundle from Edge")
    def test_requests_trust_bundle(self, mocker, edge_hsm):
        mock_request_get = mocker.patch.object(requests, "get")
        expected_url = edge_hsm.workload_uri + "trust-bundle"
        expected_params = {"api-version": edge_hsm.api_version}
        expected_headers = {
            "User-Agent": urllib.parse.quote_plus(product_info.get_iothub_user_agent())
        }

        edge_hsm.get_certificate()

        assert mock_request_get.call_count == 1
        assert mock_request_get.call_args == mocker.call(
            expected_url, params=expected_params, headers=expected_headers
        )

    @pytest.mark.it("Returns the certificate from the trust bundle received from Edge")
    def test_returns_certificate(self, mocker, edge_hsm):
        mock_request_get = mocker.patch.object(requests, "get")
        mock_response = mock_request_get.return_value
        certificate = "my certificate"
        mock_response.json.return_value = {"certificate": certificate}

        returned_cert = edge_hsm.get_certificate()

        assert returned_cert is certificate

    @pytest.mark.it("Raises IoTEdgeError if a bad request is made to Edge")
    def test_bad_request(self, mocker, edge_hsm):
        mock_request_get = mocker.patch.object(requests, "get")
        mock_response = mock_request_get.return_value
        error = requests.exceptions.HTTPError()
        mock_response.raise_for_status.side_effect = error

        with pytest.raises(IoTEdgeError) as e_info:
            edge_hsm.get_certificate()
        assert e_info.value.__cause__ is error

    @pytest.mark.it("Raises IoTEdgeError if there is an error in json decoding the trust bundle")
    def test_bad_json(self, mocker, edge_hsm):
        mock_request_get = mocker.patch.object(requests, "get")
        mock_response = mock_request_get.return_value
        error = ValueError()
        mock_response.json.side_effect = error

        with pytest.raises(IoTEdgeError) as e_info:
            edge_hsm.get_certificate()
        assert e_info.value.__cause__ is error

    @pytest.mark.it("Raises IoTEdgeError if the certificate is missing from the trust bundle")
    def test_bad_trust_bundle(self, mocker, edge_hsm):
        mock_request_get = mocker.patch.object(requests, "get")
        mock_response = mock_request_get.return_value
        # Return an empty json dict with no 'certificate' key
        mock_response.json.return_value = {}

        with pytest.raises(IoTEdgeError):
            edge_hsm.get_certificate()


@pytest.mark.describe("IoTEdgeHsm - .sign()")
class TestIoTEdgeHsmSign(object):
    @pytest.mark.it(
        "Makes an HTTP request to Edge to sign a piece of string data using the HMAC-SHA256 algorithm"
    )
    def test_requests_data_signing(self, mocker, edge_hsm):
        data_str = "somedata"
        data_str_b64 = "c29tZWRhdGE="
        mock_request_post = mocker.patch.object(requests, "post")
        mock_request_post.return_value.json.return_value = {"digest": "somedigest"}
        expected_url = "{workload_uri}modules/{module_id}/genid/{generation_id}/sign".format(
            workload_uri=edge_hsm.workload_uri,
            module_id=edge_hsm.module_id,
            generation_id=edge_hsm.generation_id,
        )
        expected_params = {"api-version": edge_hsm.api_version}
        expected_headers = {
            "User-Agent": urllib.parse.quote(product_info.get_iothub_user_agent(), safe="")
        }
        expected_json = json.dumps({"keyId": "primary", "algo": "HMACSHA256", "data": data_str_b64})

        edge_hsm.sign(data_str)

        assert mock_request_post.call_count == 1
        assert mock_request_post.call_args == mocker.call(
            url=expected_url, params=expected_params, headers=expected_headers, data=expected_json
        )

    @pytest.mark.it("Base64 encodes the string data in the request")
    def test_b64_encodes_data(self, mocker, edge_hsm):
        # This test is actually implicitly tested in the first test, but it's
        # important to have an explicit test for it since it's a requirement
        data_str = "somedata"
        data_str_b64 = base64.b64encode(data_str.encode("utf-8")).decode()
        mock_request_post = mocker.patch.object(requests, "post")
        mock_request_post.return_value.json.return_value = {"digest": "somedigest"}

        edge_hsm.sign(data_str)

        sent_data = json.loads(mock_request_post.call_args[1]["data"])["data"]

        assert data_str != data_str_b64
        assert sent_data == data_str_b64

    @pytest.mark.it("Returns the signed data received from Edge")
    def test_returns_signed_data(self, mocker, edge_hsm):
        expected_digest = "somedigest"
        mock_request_post = mocker.patch.object(requests, "post")
        mock_request_post.return_value.json.return_value = {"digest": expected_digest}

        signed_data = edge_hsm.sign("somedata")

        assert signed_data == expected_digest

    @pytest.mark.it("Raises IoTEdgeError if a bad request is made to EdgeHub")
    def test_bad_request(self, mocker, edge_hsm):
        mock_request_post = mocker.patch.object(requests, "post")
        mock_response = mock_request_post.return_value
        error = requests.exceptions.HTTPError()
        mock_response.raise_for_status.side_effect = error

        with pytest.raises(IoTEdgeError) as e_info:
            edge_hsm.sign("somedata")
        assert e_info.value.__cause__ is error

    @pytest.mark.it("Raises IoTEdgeError if there is an error in json decoding the signed response")
    def test_bad_json(self, mocker, edge_hsm):
        mock_request_post = mocker.patch.object(requests, "post")
        mock_response = mock_request_post.return_value
        error = ValueError()
        mock_response.json.side_effect = error
        with pytest.raises(IoTEdgeError) as e_info:
            edge_hsm.sign("somedata")
        assert e_info.value.__cause__ is error

    @pytest.mark.it("Raises IoTEdgeError if the signed data is missing from the response")
    def test_bad_response(self, mocker, edge_hsm):
        mock_request_post = mocker.patch.object(requests, "post")
        mock_response = mock_request_post.return_value
        mock_response.json.return_value = {}

        with pytest.raises(IoTEdgeError):
            edge_hsm.sign("somedata")
