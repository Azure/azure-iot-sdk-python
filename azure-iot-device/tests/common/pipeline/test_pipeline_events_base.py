# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import pytest
from azure.iot.device.common.pipeline import pipeline_events_base


@pytest.mark.describe("PipelineEvent object")
class TestPipelineEvent(object):
    @pytest.mark.it("Sets name attribute on instantiation")
    def test_default_arguments(self):
        obj = pipeline_events_base.PipelineEvent()
        assert obj.name is obj.__class__.__name__
