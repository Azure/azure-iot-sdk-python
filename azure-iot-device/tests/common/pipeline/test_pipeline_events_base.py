# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import sys
import pytest
import logging
from azure.iot.device.common.pipeline import pipeline_events_base
from tests.common.pipeline import pipeline_data_object_test

logging.basicConfig(level=logging.DEBUG)
this_module = sys.modules[__name__]


@pytest.mark.describe("PipelineEvent")
class TestPipelineOperation(object):
    @pytest.mark.it("Can't be instantiated")
    def test_instantiate(self):
        with pytest.raises(TypeError):
            pipeline_events_base.PipelineEvent()


pipeline_data_object_test.add_event_test(
    cls=pipeline_events_base.ResponseEvent,
    module=this_module,
    positional_arguments=["request_id", "status_code", "response_body"],
    keyword_arguments={},
)
