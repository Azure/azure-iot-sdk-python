# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import pytest
from azure.iot.device.provisioning.security.sk_security_client import SymmetricKeySecurityClient
from azure.iot.device.provisioning.sk_provisioning_device_client import (
    SymmetricKeyProvisioningDeviceClient,
)
from azure.iot.device.provisioning.provisioning_device_client_factory import (
    create_from_security_client,
)
from azure.iot.device.provisioning.pipeline.provisioning_pipeline import ProvisioningPipeline

fake_symmetric_key = "Zm9vYmFy"
fake_registration_id = "MyPensieve"
fake_id_scope = "Enchanted0000Ceiling7898"
fake_provisioning_host = "hogwarts.com"

xfail_notimplemented = pytest.mark.xfail(raises=NotImplementedError, reason="Unimplemented")


@pytest.fixture
def security_client():
    return SymmetricKeySecurityClient(
        provisioning_host=fake_provisioning_host,
        registration_id=fake_registration_id,
        id_scope=fake_id_scope,
        symmetric_key=fake_symmetric_key,
    )


@pytest.mark.describe("ProvisioningDeviceClientFactory")
class TestProvisioningDeviceClientFactory:
    @pytest.mark.it("creates ProvisioningDeviceClient")
    @pytest.mark.parametrize(
        "protocol,expected_pipeline",
        [
            pytest.param("mqtt", ProvisioningPipeline, id="mqtt"),
            pytest.param("amqp", None, id="amqp", marks=xfail_notimplemented),
            pytest.param("http", None, id="http", marks=xfail_notimplemented),
        ],
    )
    def test_create_from_security_provider_instantiates_client(
        self, security_client, protocol, expected_pipeline
    ):
        client = create_from_security_client(security_client, protocol)
        assert isinstance(client, SymmetricKeyProvisioningDeviceClient)

    @pytest.mark.it("raises error on creation if it is not symmetric security client")
    def test_raises_when_client_created_from_security_provider_with_not_symmetric_security(self):
        with pytest.raises(
            ValueError, match="A symmetric key security provider must be provided for MQTT"
        ):
            not_symmetric_security_client = NonSymmetricSecurityClientTest()
            create_from_security_client(not_symmetric_security_client, "mqtt")


class NonSymmetricSecurityClientTest(object):
    def __init__(self):
        self.registration_id = fake_registration_id
        self.id_scope = fake_id_scope
