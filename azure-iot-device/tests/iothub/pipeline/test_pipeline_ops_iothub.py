# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import pytest
import sys
import logging
from azure.iot.device.iothub.pipeline import pipeline_ops_iothub
from tests.common.pipeline import pipeline_ops_test

logging.basicConfig(level=logging.DEBUG)
this_module = sys.modules[__name__]
pytestmark = pytest.mark.usefixtures("fake_pipeline_thread")


class SendD2CMessageOperationTestConfig(object):
    @pytest.fixture
    def cls_type(self):
        return pipeline_ops_iothub.SendD2CMessageOperation

    @pytest.fixture
    def init_kwargs(self, mocker):
        kwargs = {"message": mocker.MagicMock(), "callback": mocker.MagicMock()}
        return kwargs


class SendD2CMessageOperationInstantiationTests(SendD2CMessageOperationTestConfig):
    @pytest.mark.it("Initializes 'message' attribute with the provided 'message' parameter")
    def test_message(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.message is init_kwargs["message"]


pipeline_ops_test.add_operation_tests(
    test_module=this_module,
    op_class_under_test=pipeline_ops_iothub.SendD2CMessageOperation,
    op_test_config_class=SendD2CMessageOperationTestConfig,
    extended_op_instantiation_test_class=SendD2CMessageOperationInstantiationTests,
)


class SendOutputEventOperationTestConfig(object):
    @pytest.fixture
    def cls_type(self):
        return pipeline_ops_iothub.SendOutputEventOperation

    @pytest.fixture
    def init_kwargs(self, mocker):
        kwargs = {"message": mocker.MagicMock(), "callback": mocker.MagicMock()}
        return kwargs


class SendOutputEventOperationInstantiationTests(SendOutputEventOperationTestConfig):
    @pytest.mark.it("Initializes 'message' attribute with the provided 'message' parameter")
    def test_message(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.message is init_kwargs["message"]


pipeline_ops_test.add_operation_tests(
    test_module=this_module,
    op_class_under_test=pipeline_ops_iothub.SendOutputEventOperation,
    op_test_config_class=SendOutputEventOperationTestConfig,
    extended_op_instantiation_test_class=SendOutputEventOperationInstantiationTests,
)


class SendMethodResponseOperationTestConfig(object):
    @pytest.fixture
    def cls_type(self):
        return pipeline_ops_iothub.SendMethodResponseOperation

    @pytest.fixture
    def init_kwargs(self, mocker):
        kwargs = {"method_response": mocker.MagicMock(), "callback": mocker.MagicMock()}
        return kwargs


class SendMethodResponseOperationInstantiationTests(SendMethodResponseOperationTestConfig):
    @pytest.mark.it(
        "Initializes 'method_response' attribute with the provided 'method_response' parameter"
    )
    def test_method_response(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.method_response is init_kwargs["method_response"]


pipeline_ops_test.add_operation_tests(
    test_module=this_module,
    op_class_under_test=pipeline_ops_iothub.SendMethodResponseOperation,
    op_test_config_class=SendMethodResponseOperationTestConfig,
    extended_op_instantiation_test_class=SendMethodResponseOperationInstantiationTests,
)


class GetTwinOperationTestConfig(object):
    @pytest.fixture
    def cls_type(self):
        return pipeline_ops_iothub.GetTwinOperation

    @pytest.fixture
    def init_kwargs(self, mocker):
        kwargs = {"callback": mocker.MagicMock()}
        return kwargs


class GetTwinOperationInstantiationTests(GetTwinOperationTestConfig):
    @pytest.mark.it("Initializes 'twin' attribute as None")
    def test_twin(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.twin is None


pipeline_ops_test.add_operation_tests(
    test_module=this_module,
    op_class_under_test=pipeline_ops_iothub.GetTwinOperation,
    op_test_config_class=GetTwinOperationTestConfig,
    extended_op_instantiation_test_class=GetTwinOperationInstantiationTests,
)


class PatchTwinReportedPropertiesOperationTestConfig(object):
    @pytest.fixture
    def cls_type(self):
        return pipeline_ops_iothub.PatchTwinReportedPropertiesOperation

    @pytest.fixture
    def init_kwargs(self, mocker):
        kwargs = {"patch": {"some": "patch"}, "callback": mocker.MagicMock()}
        return kwargs


class PatchTwinReportedPropertiesOperationInstantiationTests(
    PatchTwinReportedPropertiesOperationTestConfig
):
    @pytest.mark.it("Initializes 'patch' attribute with the provided 'patch' parameter")
    def test_patch(self, cls_type, init_kwargs):
        op = cls_type(**init_kwargs)
        assert op.patch is init_kwargs["patch"]


pipeline_ops_test.add_operation_tests(
    test_module=this_module,
    op_class_under_test=pipeline_ops_iothub.PatchTwinReportedPropertiesOperation,
    op_test_config_class=PatchTwinReportedPropertiesOperationTestConfig,
    extended_op_instantiation_test_class=PatchTwinReportedPropertiesOperationInstantiationTests,
)
