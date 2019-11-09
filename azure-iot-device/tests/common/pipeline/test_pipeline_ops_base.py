# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import sys
import pytest
import logging
from azure.iot.device.common.pipeline import pipeline_ops_base

# from tests.common.pipeline import pipeline_data_object_test
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

    @pytest.fixture
    def op(self, mocker):
        op = pipeline_ops_base.ConnectOperation(callback=mocker.MagicMock())
        mocker.spy(op, "complete")
        return op


pipeline_ops_test.add_operation_tests(
    test_module=this_module,
    op_class_under_test=pipeline_ops_base.ConnectOperation,
    op_test_config_class=ConnectOperationTestConfig,
)


# pipeline_data_object_test.add_operation_test(
#     cls=pipeline_ops_base.ConnectOperation, module=this_module
# )
# pipeline_data_object_test.add_operation_test(
#     cls=pipeline_ops_base.DisconnectOperation, module=this_module
# )
# pipeline_data_object_test.add_operation_test(
#     cls=pipeline_ops_base.ReconnectOperation, module=this_module
# )
# pipeline_data_object_test.add_operation_test(
#     cls=pipeline_ops_base.EnableFeatureOperation,
#     module=this_module,
#     positional_arguments=["feature_name", "callback"],
# )
# pipeline_data_object_test.add_operation_test(
#     cls=pipeline_ops_base.DisableFeatureOperation,
#     module=this_module,
#     positional_arguments=["feature_name", "callback"],
# )
# pipeline_data_object_test.add_operation_test(
#     cls=pipeline_ops_base.UpdateSasTokenOperation,
#     module=this_module,
#     positional_arguments=["sas_token", "callback"],
# )
# pipeline_data_object_test.add_operation_test(
#     cls=pipeline_ops_base.RequestAndResponseOperation,
#     module=this_module,
#     positional_arguments=[
#         "request_type",
#         "method",
#         "resource_location",
#         "request_body",
#         "callback",
#     ],
# )
# pipeline_data_object_test.add_operation_test(
#     cls=pipeline_ops_base.RequestOperation,
#     module=this_module,
#     positional_arguments=[
#         "request_type",
#         "method",
#         "resource_location",
#         "request_body",
#         "request_id",
#         "callback",
#     ],
# )
