# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import sys
import logging
from azure.iot.device.provisioning.pipeline import pipeline_events_provisioning
from tests.common.pipeline import pipeline_data_object_test

logging.basicConfig(level=logging.INFO)
this_module = sys.modules[__name__]

pipeline_data_object_test.add_event_test(
    cls=pipeline_events_provisioning.RegistrationResponseEvent,
    module=this_module,
    positional_arguments=["request_id", "status_code", "key_values", "response_payload"],
    keyword_arguments={},
)
