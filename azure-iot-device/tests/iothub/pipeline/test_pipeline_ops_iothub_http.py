# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import pytest
import sys
import logging
from azure.iot.device.iothub.pipeline import pipeline_ops_iothub_http
from tests.common.pipeline import pipeline_ops_test

logging.basicConfig(level=logging.DEBUG)
this_module = sys.modules[__name__]
pytestmark = pytest.mark.usefixtures("fake_pipeline_thread")

fake_device_id = "__fake_device_id__"
fake_module_id = "__fake_module_id__"


class MethodInvokeOperationTestConfig(object):
    @pytest.fixture
    def cls_type(self):
        return pipeline_ops_iothub_http.MethodInvokeOperation

    @pytest.fixture
    def init_kwargs(self, mocker):
        kwargs = {
            "device_id": fake_module_id,
            "module_id": fake_module_id,
            "method_params": mocker.MagicMock(),
            "callback": mocker.MagicMock(),
        }
        return kwargs


class MethodInvokeOperationInstantiationTests(MethodInvokeOperationTestConfig):
    @pytest.mark.it("Initializes 'device_id' attribute with the provided 'device_id' parameter")
    def test_device_id(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.device_id is init_kwargs["device_id"]

    @pytest.mark.it("Initializes 'module_id' attribute with the provided 'module_id' parameter")
    def test_module_id(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.module_id is init_kwargs["module_id"]

    @pytest.mark.it(
        "Initializes 'method_params' attribute with the provided 'method_params' parameter"
    )
    def test_method_params(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.method_params is init_kwargs["method_params"]

    @pytest.mark.it("Initializes 'method_response' attribute as None")
    def test_method_response(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.method_response is None


pipeline_ops_test.add_operation_tests(
    test_module=this_module,
    op_class_under_test=pipeline_ops_iothub_http.MethodInvokeOperation,
    op_test_config_class=MethodInvokeOperationTestConfig,
    extended_op_instantiation_test_class=MethodInvokeOperationInstantiationTests,
)


class GetStorageInfoOperationTestConfig(object):
    @pytest.fixture
    def cls_type(self):
        return pipeline_ops_iothub_http.GetStorageInfoOperation

    @pytest.fixture
    def init_kwargs(self, mocker):
        kwargs = {"blob_name": "__fake_blob_name__", "callback": mocker.MagicMock()}
        return kwargs


class GetStorageInfoOperationInstantiationTests(GetStorageInfoOperationTestConfig):
    @pytest.mark.it("Initializes 'blob_name' attribute with the provided 'blob_name' parameter")
    def test_blob_name(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.blob_name is init_kwargs["blob_name"]

    @pytest.mark.it("Initializes 'storage_info' attribute as None")
    def test_storage_info(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.storage_info is None


pipeline_ops_test.add_operation_tests(
    test_module=this_module,
    op_class_under_test=pipeline_ops_iothub_http.GetStorageInfoOperation,
    op_test_config_class=GetStorageInfoOperationTestConfig,
    extended_op_instantiation_test_class=GetStorageInfoOperationInstantiationTests,
)


class NotifyBlobUploadStatusOperationTestConfig(object):
    @pytest.fixture
    def cls_type(self):
        return pipeline_ops_iothub_http.NotifyBlobUploadStatusOperation

    @pytest.fixture
    def init_kwargs(self, mocker):
        kwargs = {
            "correlation_id": "some_correlation_id",
            "upload_response": "some_upload_response",
            "status_code": "some_status_code",
            "status_description": "some_status_description",
            "callback": mocker.MagicMock(),
        }
        return kwargs


class NotifyBlobUploadStatusOperationInstantiationTests(NotifyBlobUploadStatusOperationTestConfig):
    @pytest.mark.it(
        "Initializes 'correlation_id' attribute with the provided 'correlation_id' parameter"
    )
    def test_correlation_id(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.correlation_id is init_kwargs["correlation_id"]

    @pytest.mark.it(
        "Initializes 'upload_response' attribute with the provided 'upload_response' parameter"
    )
    def test_upload_response(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.upload_response is init_kwargs["upload_response"]

    @pytest.mark.it(
        "Initializes 'request_status_code' attribute with the provided 'status_code' parameter"
    )
    def test_request_status_code(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.request_status_code is init_kwargs["status_code"]

    @pytest.mark.it(
        "Initializes 'status_description' attribute with the provided 'status_description' parameter"
    )
    def test_status_description(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.status_description is init_kwargs["status_description"]

    @pytest.mark.it("Initializes 'response_status_code' attribute as None")
    def test_ca_cert(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.response_status_code is None


pipeline_ops_test.add_operation_tests(
    test_module=this_module,
    op_class_under_test=pipeline_ops_iothub_http.NotifyBlobUploadStatusOperation,
    op_test_config_class=NotifyBlobUploadStatusOperationTestConfig,
    extended_op_instantiation_test_class=NotifyBlobUploadStatusOperationInstantiationTests,
)
