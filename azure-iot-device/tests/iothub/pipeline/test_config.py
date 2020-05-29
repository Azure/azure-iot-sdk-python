# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import pytest
import logging
from tests.common.pipeline.config_test import PipelineConfigInstantiationTestBase
from azure.iot.device.iothub.pipeline.config import IoTHubPipelineConfig

device_id = "my_device"
module_id = "my_module"
hostname = "hostname.some-domain.net"
product_info = "some_info"


@pytest.mark.describe("IoTHubPipelineConfig - Instantiation")
class TestIoTHubPipelineConfigInstantiation(PipelineConfigInstantiationTestBase):

    # This fixture is needed for tests inherited from the parent class
    @pytest.fixture
    def config_cls(self):
        return IoTHubPipelineConfig

    # This fixture is needed for tests inherited from the parent class
    @pytest.fixture
    def required_kwargs(self):
        return {"device_id": device_id, "hostname": hostname}

    # The parent class defines the auth mechanism fixtures (sastoken, x509).
    # For the sake of ease of testing, we will assume sastoken is being used unless
    # there is a strict need to do something else.
    # It does not matter which is used for the purposes of these tests.

    @pytest.mark.it(
        "Instantiates with the 'device_id' attribute set to the provided 'device_id' paramater"
    )
    def test_device_id_set(self, sastoken):
        config = IoTHubPipelineConfig(device_id=device_id, hostname=hostname, sastoken=sastoken)
        assert config.device_id == device_id

    @pytest.mark.it(
        "Instantiates with the 'module_id' attribute set to the provided 'module_id' paramater"
    )
    def test_module_id_set(self, sastoken):
        config = IoTHubPipelineConfig(
            device_id=device_id, module_id=module_id, hostname=hostname, sastoken=sastoken
        )
        assert config.module_id == module_id

    @pytest.mark.it(
        "Instantiates with the 'module_id' attribute set to 'None' if no 'module_id' paramater is provided"
    )
    def test_module_id_default(self, sastoken):
        config = IoTHubPipelineConfig(device_id=device_id, hostname=hostname, sastoken=sastoken)
        assert config.module_id is None

    @pytest.mark.it(
        "Instantiates with the 'product_info' attribute set to the provided 'product_info' parameter"
    )
    def test_product_info_set(self, sastoken):
        config = IoTHubPipelineConfig(
            device_id=device_id, hostname=hostname, product_info=product_info, sastoken=sastoken
        )
        assert config.product_info == product_info

    @pytest.mark.it(
        "Instantiates with the 'product_info' attribute defaulting to empty string if no 'product_info' paramater is provided"
    )
    def test_product_info_default(self, sastoken):
        config = IoTHubPipelineConfig(device_id=device_id, hostname=hostname, sastoken=sastoken)
        assert config.product_info == ""

    @pytest.mark.it("Instantiates with the 'blob_upload' attribute set to False")
    def test_blob_upload(self, sastoken):
        config = IoTHubPipelineConfig(device_id=device_id, hostname=hostname, sastoken=sastoken)
        assert config.blob_upload is False

    @pytest.mark.it("Instantiates with the 'method_invoke' attribute set to False")
    def test_method_invoke(self, sastoken):
        config = IoTHubPipelineConfig(device_id=device_id, hostname=hostname, sastoken=sastoken)
        assert config.method_invoke is False
