# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import sys
import pytest
import logging
from azure.iot.device.common.pipeline import pipeline_ops_base
from tests.common.pipeline import pipeline_data_object_test

this_module = sys.modules[__name__]
logging.basicConfig(level=logging.DEBUG)


@pytest.mark.describe("PipelineOperation")
class TestPipelineOperation(object):
    @pytest.mark.it("Can't be instantiated")
    def test_instantiate(self, mocker):
        with pytest.raises(TypeError):
            pipeline_ops_base.PipelineOperation(mocker.MagicMock())


pipeline_data_object_test.add_operation_test(
    cls=pipeline_ops_base.ConnectOperation, module=this_module
)
pipeline_data_object_test.add_operation_test(
    cls=pipeline_ops_base.DisconnectOperation, module=this_module
)
pipeline_data_object_test.add_operation_test(
    cls=pipeline_ops_base.ReconnectOperation, module=this_module
)
pipeline_data_object_test.add_operation_test(
    cls=pipeline_ops_base.EnableFeatureOperation,
    module=this_module,
    positional_arguments=["feature_name", "callback"],
)
pipeline_data_object_test.add_operation_test(
    cls=pipeline_ops_base.DisableFeatureOperation,
    module=this_module,
    positional_arguments=["feature_name", "callback"],
)
pipeline_data_object_test.add_operation_test(
    cls=pipeline_ops_base.UpdateSasTokenOperation,
    module=this_module,
    positional_arguments=["sas_token", "callback"],
)
pipeline_data_object_test.add_operation_test(
    cls=pipeline_ops_base.RequestAndResponseOperation,
    module=this_module,
    positional_arguments=[
        "request_type",
        "method",
        "resource_location",
        "request_body",
        "callback",
    ],
)
pipeline_data_object_test.add_operation_test(
    cls=pipeline_ops_base.RequestOperation,
    module=this_module,
    positional_arguments=[
        "request_type",
        "method",
        "resource_location",
        "request_body",
        "request_id",
        "callback",
    ],
)
