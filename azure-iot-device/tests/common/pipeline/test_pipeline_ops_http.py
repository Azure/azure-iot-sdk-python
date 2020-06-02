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
    op_class_under_test=pipeline_ops_http.HTTPRequestAndResponseOperation,
    op_test_config_class=HTTPRequestAndResponseOperationTestConfig,
    extended_op_instantiation_test_class=HTTPRequestAndResponseOperationInstantiationTests,
)
