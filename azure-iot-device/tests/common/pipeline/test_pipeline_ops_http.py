# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import pytest
import sys
import logging
from azure.iot.device.common.pipeline import pipeline_ops_http
from tests.common.pipeline import pipeline_ops_test

logging.basicConfig(level=logging.DEBUG)
this_module = sys.modules[__name__]
pytestmark = pytest.mark.usefixtures("fake_pipeline_thread")


class SetHTTPConnectionArgsOperationTestConfig(object):
    @pytest.fixture
    def cls_type(self):
        return pipeline_ops_http.SetHTTPConnectionArgsOperation

    @pytest.fixture
    def init_kwargs(self, mocker):
        kwargs = {
            "hostname": "some_hostname",
            "callback": mocker.MagicMock(),
            "server_verification_cert": "some_server_verification_cert",
            "client_cert": "some_client_cert",
            "sas_token": "some_sas_token",
        }
        return kwargs


class SetHTTPConnectionArgsOperationInstantiationTests(SetHTTPConnectionArgsOperationTestConfig):
    @pytest.mark.it("Initializes 'hostname' attribute with the provided 'hostname' parameter")
    def test_hostname(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.hostname == init_kwargs["hostname"]

    @pytest.mark.it(
        "Initializes 'server_verification_cert' attribute with the provided 'server_verification_cert' parameter"
    )
    def test_server_verification_cert(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.server_verification_cert == init_kwargs["server_verification_cert"]

    @pytest.mark.it(
        "Initializes 'server_verification_cert' attribute to None if no 'server_verification_cert' parameter is provided"
    )
    def test_server_verification_cert_default(self, cls_type, init_kwargs):
        del init_kwargs["server_verification_cert"]
        op = cls_type(**init_kwargs)
        assert op.server_verification_cert is None

    @pytest.mark.it("Initializes 'client_cert' attribute with the provided 'client_cert' parameter")
    def test_client_cert(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.client_cert == init_kwargs["client_cert"]

    @pytest.mark.it(
        "Initializes 'client_cert' attribute to None if no 'client_cert' parameter is provided"
    )
    def test_client_cert_default(self, cls_type, init_kwargs):
        del init_kwargs["client_cert"]
        op = cls_type(**init_kwargs)
        assert op.client_cert is None

    @pytest.mark.it("Initializes 'sas_token' attribute with the provided 'sas_token' parameter")
    def test_sas_token(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.sas_token == init_kwargs["sas_token"]

    @pytest.mark.it(
        "Initializes 'sas_token' attribute to None if no 'sas_token' parameter is provided"
    )
    def test_sas_token_default(self, cls_type, init_kwargs):
        del init_kwargs["sas_token"]
        op = cls_type(**init_kwargs)
        assert op.sas_token is None


pipeline_ops_test.add_operation_tests(
    test_module=this_module,
    op_class_under_test=pipeline_ops_http.SetHTTPConnectionArgsOperation,
    op_test_config_class=SetHTTPConnectionArgsOperationTestConfig,
    extended_op_instantiation_test_class=SetHTTPConnectionArgsOperationInstantiationTests,
)


class HTTPRequestAndResponseOperationTestConfig(object):
    @pytest.fixture
    def cls_type(self):
        return pipeline_ops_http.HTTPRequestAndResponseOperation

    @pytest.fixture
    def init_kwargs(self, mocker):
        kwargs = {
            "method": "some_topic",
            "path": "some_path",
            "headers": {"some_key": "some_value"},
            "body": "some_body",
            "query_params": "some_query_params",
            "callback": mocker.MagicMock(),
        }
        return kwargs


class HTTPRequestAndResponseOperationInstantiationTests(HTTPRequestAndResponseOperationTestConfig):
    @pytest.mark.it("Initializes 'method' attribute with the provided 'method' parameter")
    def test_method(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.method == init_kwargs["method"]

    @pytest.mark.it("Initializes 'path' attribute with the provided 'path' parameter")
    def test_path(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.path == init_kwargs["path"]

    @pytest.mark.it("Initializes 'headers' attribute with the provided 'headers' parameter")
    def test_headers(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.headers == init_kwargs["headers"]

    @pytest.mark.it("Initializes 'body' attribute with the provided 'body' parameter")
    def test_body(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.body == init_kwargs["body"]

    @pytest.mark.it(
        "Initializes 'query_params' attribute with the provided 'query_params' parameter"
    )
    def test_query_params(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.query_params == init_kwargs["query_params"]

    @pytest.mark.it("Initializes 'status_code' attribute as None")
    def test_status_code(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.status_code is None

    @pytest.mark.it("Initializes 'response_body' attribute as None")
    def test_response_body(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.response_body is None

    @pytest.mark.it("Initializes 'reason' attribute as None")
    def test_reason(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.reason is None


pipeline_ops_test.add_operation_tests(
    test_module=this_module,
    op_class_under_test=pipeline_ops_http.SetHTTPConnectionArgsOperation,
    op_test_config_class=HTTPRequestAndResponseOperationTestConfig,
    extended_op_instantiation_test_class=HTTPRequestAndResponseOperationInstantiationTests,
)
