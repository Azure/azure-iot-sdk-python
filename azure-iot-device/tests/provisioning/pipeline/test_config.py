# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import pytest
import logging
from tests.common.pipeline.config_test import PipelineConfigInstantiationTestBase
from azure.iot.device.provisioning.pipeline.config import ProvisioningPipelineConfig

hostname = "hostname.some-domain.net"
registration_id = "registration_id"
id_scope = "id_scope"


@pytest.mark.describe("ProvisioningPipelineConfig - Instantiation")
class TestProvisioningPipelineConfigInstantiation(PipelineConfigInstantiationTestBase):
    @pytest.fixture
    def config_cls(self):
        # This fixture is needed for the parent class
        return ProvisioningPipelineConfig

    @pytest.fixture
    def required_kwargs(self):
        # This fixture is needed for the parent class
        return {"hostname": hostname, "registration_id": registration_id, "id_scope": id_scope}

    # The parent class defines the auth mechanism fixtures (sastoken, x509).
    # For the sake of ease of testing, we will assume sastoken is being used unless
    # there is a strict need to do something else.
    # It does not matter which is used for the purposes of these tests.

    @pytest.mark.it(
        "Instantiates with the 'registration_id' attribute set to the provided 'registration_id' paramameter"
    )
    def test_registration_id_set(self, sastoken):
        config = ProvisioningPipelineConfig(
            hostname=hostname, registration_id=registration_id, id_scope=id_scope, sastoken=sastoken
        )
        assert config.registration_id == registration_id

    @pytest.mark.it(
        "Instantiates with the 'id_scope' attribute set to the provided 'id_scope' parameter"
    )
    def test_id_scope_set(self, sastoken):
        config = ProvisioningPipelineConfig(
            hostname=hostname, registration_id=registration_id, id_scope=id_scope, sastoken=sastoken
        )
        assert config.id_scope == id_scope
