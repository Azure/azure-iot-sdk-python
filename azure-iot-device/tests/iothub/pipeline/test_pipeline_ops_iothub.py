# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import sys
from azure.iot.device.iothub.pipeline import pipeline_ops_iothub
from tests.common.pipeline import pipeline_data_object_test

this_module = sys.modules[__name__]

pipeline_data_object_test.add_operation_test(
    obj=pipeline_ops_iothub.SetAuthProvider,
    module=this_module,
    positional_arguments=["auth_provider"],
    keyword_arguments={"callback": None},
)
pipeline_data_object_test.add_operation_test(
    obj=pipeline_ops_iothub.SetAuthProviderArgs,
    module=this_module,
    positional_arguments=["device_id", "hostname"],
    keyword_arguments={
        "module_id": None,
        "gateway_hostname": None,
        "ca_cert": None,
        "callback": None,
    },
)
pipeline_data_object_test.add_operation_test(
    obj=pipeline_ops_iothub.SendTelemetry,
    module=this_module,
    positional_arguments=["message"],
    keyword_arguments={"callback": None},
    extra_defaults={"needs_connection": True},
)
pipeline_data_object_test.add_operation_test(
    obj=pipeline_ops_iothub.SendOutputEvent,
    module=this_module,
    positional_arguments=["message"],
    keyword_arguments={"callback": None},
    extra_defaults={"needs_connection": True},
)
pipeline_data_object_test.add_operation_test(
    obj=pipeline_ops_iothub.SendMethodResponse,
    module=this_module,
    positional_arguments=["method_response"],
    keyword_arguments={"callback": None},
    extra_defaults={"needs_connection": True},
)
pipeline_data_object_test.add_operation_test(
    obj=pipeline_ops_iothub.GetTwin,
    module=this_module,
    positional_arguments=[],
    keyword_arguments={"callback": None},
    extra_defaults={"needs_connection": True},
)
pipeline_data_object_test.add_operation_test(
    obj=pipeline_ops_iothub.PatchTwinReportedProperties,
    module=this_module,
    positional_arguments=["patch"],
    keyword_arguments={"callback": None},
    extra_defaults={"needs_connection": True},
)
