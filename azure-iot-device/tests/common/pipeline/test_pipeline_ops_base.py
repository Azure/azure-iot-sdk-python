# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import sys
import pytest
import logging
from azure.iot.device.common.pipeline import pipeline_ops_base
from tests.common.pipeline import pipeline_ops_test

this_module = sys.modules[__name__]
logging.basicConfig(level=logging.DEBUG)
pytestmark = pytest.mark.usefixtures("fake_pipeline_thread")

# @pytest.mark.describe("PipelineOperation")
# class TestPipelineOperation(object):
#     @pytest.mark.it("Can't be instantiated")
#     def test_instantiate(self, mocker):
#         with pytest.raises(TypeError):
#             pipeline_ops_base.PipelineOperation(mocker.MagicMock())


class ConnectOperationTestConfig(object):
    @pytest.fixture
    def cls_type(self):
        return pipeline_ops_base.ConnectOperation

    @pytest.fixture
    def init_kwargs(self, mocker):
        kwargs = {"callback": mocker.MagicMock()}
        return kwargs


pipeline_ops_test.add_operation_tests(
    test_module=this_module,
    op_class_under_test=pipeline_ops_base.ConnectOperation,
    op_test_config_class=ConnectOperationTestConfig,
)


class DisconnectOperationTestConfig(object):
    @pytest.fixture
    def cls_type(self):
        return pipeline_ops_base.DisconnectOperation

    @pytest.fixture
    def init_kwargs(self, mocker):
        kwargs = {"callback": mocker.MagicMock()}
        return kwargs


pipeline_ops_test.add_operation_tests(
    test_module=this_module,
    op_class_under_test=pipeline_ops_base.DisconnectOperation,
    op_test_config_class=DisconnectOperationTestConfig,
)


class ReconnectOperationTestConfig(object):
    @pytest.fixture
    def cls_type(self):
        return pipeline_ops_base.ReconnectOperation

    @pytest.fixture
    def init_kwargs(self, mocker):
        kwargs = {"callback": mocker.MagicMock()}
        return kwargs


pipeline_ops_test.add_operation_tests(
    test_module=this_module,
    op_class_under_test=pipeline_ops_base.ReconnectOperation,
    op_test_config_class=ReconnectOperationTestConfig,
)


class EnableFeatureOperationTestConfig(object):
    @pytest.fixture
    def cls_type(self):
        return pipeline_ops_base.EnableFeatureOperation

    @pytest.fixture
    def init_kwargs(self, mocker):
        kwargs = {"feature_name": "some_feature", "callback": mocker.MagicMock()}
        return kwargs


class EnableFeatureInstantiationTests(EnableFeatureOperationTestConfig):
    @pytest.mark.it(
        "Initializes 'feature_name' attribute with the provided 'feature_name' parameter"
    )
    def test_feature_name(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.feature_name == init_kwargs["feature_name"]


pipeline_ops_test.add_operation_tests(
    test_module=this_module,
    op_class_under_test=pipeline_ops_base.EnableFeatureOperation,
    op_test_config_class=EnableFeatureOperationTestConfig,
    extended_op_instantiation_test_class=EnableFeatureInstantiationTests,
)


class DisableFeatureOperationTestConfig(object):
    @pytest.fixture
    def cls_type(self):
        return pipeline_ops_base.DisableFeatureOperation

    @pytest.fixture
    def init_kwargs(self, mocker):
        kwargs = {"feature_name": "some_feature", "callback": mocker.MagicMock()}
        return kwargs


class DisableFeatureInstantiationTests(DisableFeatureOperationTestConfig):
    @pytest.mark.it(
        "Initializes 'feature_name' attribute with the provided 'feature_name' parameter"
    )
    def test_feature_name(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.feature_name == init_kwargs["feature_name"]


pipeline_ops_test.add_operation_tests(
    test_module=this_module,
    op_class_under_test=pipeline_ops_base.DisableFeatureOperation,
    op_test_config_class=DisableFeatureOperationTestConfig,
    extended_op_instantiation_test_class=DisableFeatureInstantiationTests,
)


class UpdateSasTokenOperationTestConfig(object):
    @pytest.fixture
    def cls_type(self):
        return pipeline_ops_base.UpdateSasTokenOperation

    @pytest.fixture
    def init_kwargs(self, mocker):
        kwargs = {"sas_token": "some_token", "callback": mocker.MagicMock()}
        return kwargs


class UpdateSasTokenOperationInstantiationTests(UpdateSasTokenOperationTestConfig):
    @pytest.mark.it("Initializes 'sas_token' attribute with the provided 'sas_token' parameter")
    def test_sas_token(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.sas_token == init_kwargs["sas_token"]


pipeline_ops_test.add_operation_tests(
    test_module=this_module,
    op_class_under_test=pipeline_ops_base.UpdateSasTokenOperation,
    op_test_config_class=UpdateSasTokenOperationTestConfig,
    extended_op_instantiation_test_class=UpdateSasTokenOperationInstantiationTests,
)


class RequestAndResponseOperationTestConfig(object):
    @pytest.fixture
    def cls_type(self):
        return pipeline_ops_base.RequestAndResponseOperation

    @pytest.fixture
    def init_kwargs(self, mocker):
        kwargs = {
            "request_type": "some_request_type",
            "method": "SOME_METHOD",
            "resource_location": "some/resource/location",
            "request_body": "some_request_body",
            "callback": mocker.MagicMock(),
        }
        return kwargs


class RequestAndResponseOperationInstantiationTests(RequestAndResponseOperationTestConfig):
    @pytest.mark.it(
        "Initializes 'request_type' attribute with the provided 'request_type' parameter"
    )
    def test_request_type(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.request_type == init_kwargs["request_type"]

    @pytest.mark.it("Initializes 'method' attribute with the provided 'method' parameter")
    def test_method_type(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.method == init_kwargs["method"]

    @pytest.mark.it(
        "Initializes 'resource_location' attribute with the provided 'resource_location' parameter"
    )
    def test_resource_location(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.resource_location == init_kwargs["resource_location"]

    @pytest.mark.it(
        "Initializes 'request_body' attribute with the provided 'request_body' parameter"
    )
    def test_request_body(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.request_body == init_kwargs["request_body"]

    @pytest.mark.it("Initializes 'status_code' attribute to None")
    def test_status_code(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.status_code is None

    @pytest.mark.it("Initializes 'response_body' attribute to None")
    def test_response_body(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.response_body is None


pipeline_ops_test.add_operation_tests(
    test_module=this_module,
    op_class_under_test=pipeline_ops_base.RequestAndResponseOperation,
    op_test_config_class=RequestAndResponseOperationTestConfig,
    extended_op_instantiation_test_class=RequestAndResponseOperationInstantiationTests,
)


class RequestOperationTestConfig(object):
    @pytest.fixture
    def cls_type(self):
        return pipeline_ops_base.RequestOperation

    @pytest.fixture
    def init_kwargs(self, mocker):
        kwargs = {
            "method": "SOME_METHOD",
            "resource_location": "some/resource/location",
            "request_type": "some_request_type",
            "request_body": "some_request_body",
            "request_id": "some_request_id",
            "callback": mocker.MagicMock(),
        }
        return kwargs


class RequestOperationInstantiationTests(RequestOperationTestConfig):
    @pytest.mark.it("Initializes the 'method' attribute with the provided 'method' parameter")
    def test_method(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.method == init_kwargs["method"]

    @pytest.mark.it(
        "Initializes the 'resource_location' attribute with the provided 'resource_location' parameter"
    )
    def test_resource_location(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.resource_location == init_kwargs["resource_location"]

    @pytest.mark.it(
        "Initializes the 'request_type' attribute with the provided 'request_type' parameter"
    )
    def test_request_type(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.request_type == init_kwargs["request_type"]

    @pytest.mark.it(
        "Initializes the 'request_body' attribute with the provided 'request_body' parameter"
    )
    def test_request_body(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.request_body == init_kwargs["request_body"]

    @pytest.mark.it(
        "Initializes the 'request_id' attribute with the provided 'request_id' parameter"
    )
    def test_request_id(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.request_id == init_kwargs["request_id"]


pipeline_ops_test.add_operation_tests(
    test_module=this_module,
    op_class_under_test=pipeline_ops_base.RequestOperation,
    op_test_config_class=RequestOperationTestConfig,
    extended_op_instantiation_test_class=RequestOperationInstantiationTests,
)
