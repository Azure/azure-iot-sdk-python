# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import pytest
from azure.iot.device.common.transport import pipeline_events_base


@pytest.mark.describe("PipelineEvent object")
class TestPipelineEvent(object):
    @pytest.mark.it("Sets arguments correctly")
    def test_default_arguments(self):
        obj = pipeline_events_base.PipelineEvent()
        assert obj.name is obj.__class__.__name__
