# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import sys
from azure.iot.device.common.pipeline import pipeline_ops_mqtt
from tests.common.pipeline import pipeline_data_object_test

this_module = sys.modules[__name__]

pipeline_data_object_test.add_operation_test(
    obj=pipeline_ops_mqtt.SetConnectionArgs,
    module=this_module,
    positional_arguments=["client_id", "hostname", "username"],
    keyword_arguments={"ca_cert": None, "callback": None},
)
pipeline_data_object_test.add_operation_test(
    obj=pipeline_ops_mqtt.Publish,
    module=this_module,
    positional_arguments=["topic", "payload"],
    keyword_arguments={"callback": None},
)
pipeline_data_object_test.add_operation_test(
    obj=pipeline_ops_mqtt.Subscribe,
    module=this_module,
    positional_arguments=["topic"],
    keyword_arguments={"callback": None},
)
pipeline_data_object_test.add_operation_test(
    obj=pipeline_ops_mqtt.Unsubscribe,
    module=this_module,
    positional_arguments=["topic"],
    keyword_arguments={"callback": None},
)
