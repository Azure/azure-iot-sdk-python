# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import pytest
import logging
from azure.iot.device.common.pipeline.pipeline_nucleus import PipelineNucleus


@pytest.mark.describe("PipelineNucleus - Instantiation")
class TestPipelineNucleusInstantiation(object):
    @pytest.fixture
    def pipeline_config(mocker):
        return mocker.MagicMock()

    @pytest.mark.it(
        "Instantiates with the 'pipeline_configuration' attribute set the the value of the provided 'pipeline_configuration' parameter"
    )
    def test_pipeline_config(self, pipeline_config):
        nucleus = PipelineNucleus(pipeline_configuration=pipeline_config)
        assert nucleus.pipeline_configuration is pipeline_config

    @pytest.mark.it("Instantiates with the 'connected' attribute set to False")
    def test_connected(self, pipeline_config):
        nucleus = PipelineNucleus(pipeline_config)
        assert nucleus.connected is False
