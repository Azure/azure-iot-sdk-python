# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import sys
from azure.iot.device.iothub.pipeline import pipeline_events_iothub
from tests.common.pipeline import pipeline_data_object_test

this_module = sys.modules[__name__]

pipeline_data_object_test.add_event_test(
    cls=pipeline_events_iothub.C2DMessageEvent,
    module=this_module,
    positional_arguments=["message"],
    keyword_arguments={},
)
pipeline_data_object_test.add_event_test(
    cls=pipeline_events_iothub.InputMessageEvent,
    module=this_module,
    positional_arguments=["input_name", "message"],
    keyword_arguments={},
)
pipeline_data_object_test.add_event_test(
    cls=pipeline_events_iothub.MethodRequest,
    module=this_module,
    positional_arguments=["method_request"],
    keyword_arguments={},
)
pipeline_data_object_test.add_event_test(
    cls=pipeline_events_iothub.TwinDesiredPropertiesPatchEvent,
    module=this_module,
    positional_arguments=["patch"],
    keyword_arguments={},
)
