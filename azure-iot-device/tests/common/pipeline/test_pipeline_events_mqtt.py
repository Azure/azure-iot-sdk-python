# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import sys
import logging
from azure.iot.device.common.pipeline import pipeline_events_mqtt
from tests.common.pipeline import pipeline_data_object_test

logging.basicConfig(level=logging.INFO)

this_module = sys.modules[__name__]

pipeline_data_object_test.add_event_test(
    cls=pipeline_events_mqtt.IncomingMQTTMessageEvent,
    module=this_module,
    positional_arguments=["topic", "payload"],
    keyword_arguments={},
)
