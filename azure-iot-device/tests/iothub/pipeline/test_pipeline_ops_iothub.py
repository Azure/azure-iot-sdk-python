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
    cls=pipeline_ops_iothub.SetAuthProviderOperation,
    module=this_module,
    positional_arguments=["auth_provider"],
    keyword_arguments={"callback": None},
)
pipeline_data_object_test.add_operation_test(
    cls=pipeline_ops_iothub.SetX509AuthProviderOperation,
    module=this_module,
    positional_arguments=["auth_provider"],
    keyword_arguments={"callback": None},
)
pipeline_data_object_test.add_operation_test(
    cls=pipeline_ops_iothub.SetAuthProviderArgsOperation,
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
    cls=pipeline_ops_iothub.SendD2CMessageOperation,
    module=this_module,
    positional_arguments=["message"],
    keyword_arguments={"callback": None},
    extra_defaults={"needs_connection": True},
)
pipeline_data_object_test.add_operation_test(
    cls=pipeline_ops_iothub.SendOutputEventOperation,
    module=this_module,
    positional_arguments=["message"],
    keyword_arguments={"callback": None},
    extra_defaults={"needs_connection": True},
)
pipeline_data_object_test.add_operation_test(
    cls=pipeline_ops_iothub.SendMethodResponseOperation,
    module=this_module,
    positional_arguments=["method_response"],
    keyword_arguments={"callback": None},
    extra_defaults={"needs_connection": True},
)
pipeline_data_object_test.add_operation_test(
    cls=pipeline_ops_iothub.GetTwinOperation,
    module=this_module,
    positional_arguments=[],
    keyword_arguments={"callback": None},
    extra_defaults={"needs_connection": True},
)
pipeline_data_object_test.add_operation_test(
    cls=pipeline_ops_iothub.PatchTwinReportedPropertiesOperation,
    module=this_module,
    positional_arguments=["patch"],
    keyword_arguments={"callback": None},
    extra_defaults={"needs_connection": True},
)
