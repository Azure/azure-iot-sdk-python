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
    cls=pipeline_ops_mqtt.SetMQTTConnectionArgsOperation,
    module=this_module,
    positional_arguments=["client_id", "hostname", "username"],
    keyword_arguments={"ca_cert": None, "client_cert": None, "sas_token": None, "callback": None},
)
pipeline_data_object_test.add_operation_test(
    cls=pipeline_ops_mqtt.MQTTPublishOperation,
    module=this_module,
    positional_arguments=["topic", "payload"],
    keyword_arguments={"callback": None},
)
pipeline_data_object_test.add_operation_test(
    cls=pipeline_ops_mqtt.MQTTSubscribeOperation,
    module=this_module,
    positional_arguments=["topic"],
    keyword_arguments={"callback": None},
)
pipeline_data_object_test.add_operation_test(
    cls=pipeline_ops_mqtt.MQTTUnsubscribeOperation,
    module=this_module,
    positional_arguments=["topic"],
    keyword_arguments={"callback": None},
)
