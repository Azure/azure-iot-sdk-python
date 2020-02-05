# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import pytest
import logging
from tests.common.pipeline.pipeline_config_test import PipelineConfigInstantiationTestBase
from azure.iot.device.provisioning.pipeline.config import ProvisioningPipelineConfig


@pytest.mark.describe("ProvisioningPipelineConfig - Instantiation")
class TestProvisioningPipelineConfigInstantiation(PipelineConfigInstantiationTestBase):
    @pytest.fixture
    def config_cls(self):
        # This fixture is needed for the parent class
        return ProvisioningPipelineConfig
