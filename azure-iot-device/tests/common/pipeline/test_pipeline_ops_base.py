# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import sys
from azure.iot.device.common.pipeline import pipeline_ops_base
from tests.common.pipeline import pipeline_data_object_test

this_module = sys.modules[__name__]

pipeline_data_object_test.add_operation_test(
    cls=pipeline_ops_base.ConnectOperation,
    module=this_module,
    positional_arguments=[],
    keyword_arguments={"callback": None},
)
pipeline_data_object_test.add_operation_test(
    cls=pipeline_ops_base.DisconnectOperation,
    module=this_module,
    positional_arguments=[],
    keyword_arguments={"callback": None},
)
pipeline_data_object_test.add_operation_test(
    cls=pipeline_ops_base.ReconnectOperation,
    module=this_module,
    positional_arguments=[],
    keyword_arguments={"callback": None},
)
pipeline_data_object_test.add_operation_test(
    cls=pipeline_ops_base.EnableFeatureOperation,
    module=this_module,
    positional_arguments=["feature_name"],
    keyword_arguments={"callback": None},
    extra_defaults={"needs_connection": True},
)
pipeline_data_object_test.add_operation_test(
    cls=pipeline_ops_base.DisableFeatureOperation,
    module=this_module,
    positional_arguments=["feature_name"],
    keyword_arguments={"callback": None},
    extra_defaults={"needs_connection": True},
)
