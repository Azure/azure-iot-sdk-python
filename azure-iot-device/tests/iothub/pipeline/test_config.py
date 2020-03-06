# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import pytest
import logging
from tests.common.pipeline.pipeline_config_test import PipelineConfigInstantiationTestBase
from azure.iot.device.iothub.pipeline.config import IoTHubPipelineConfig


@pytest.mark.describe("IoTHubPipelineConfig - Instantiation")
class TestIoTHubPipelineConfigInstantiation(PipelineConfigInstantiationTestBase):
    @pytest.fixture
    def config_cls(self):
        # This fixture is needed for the parent class
        return IoTHubPipelineConfig

    @pytest.mark.it(
        "Instantiates with the 'product_info' attribute set to the provided 'product_info' parameter"
    )
    def test_product_info_set(self):
        my_product_info = "some_info"
        config = IoTHubPipelineConfig(product_info=my_product_info)

        assert config.product_info == my_product_info

    @pytest.mark.it(
        "Instantiates with the 'product_info' attribute defaulting to empty string if there is no provided 'product_info'"
    )
    def test_product_info_default(self):
        config = IoTHubPipelineConfig()
        assert config.product_info == ""

    @pytest.mark.it("Instantiates with the 'blob_upload' attribute set to False")
    def test_blob_upload(self):
        config = IoTHubPipelineConfig()
        assert config.blob_upload is False

    @pytest.mark.it("Instantiates with the 'method_invoke' attribute set to False")
    def test_method_invoke(self):
        config = IoTHubPipelineConfig()
        assert config.method_invoke is False
