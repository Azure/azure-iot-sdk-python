# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import pytest
import logging
import azure.iot.device.iothub

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)

pytestmark = pytest.mark.asyncio
if not getattr(azure.iot.device.iothub, "CommandRequest", None):
    # only run if PNP enabled
    pytestmark = pytest.mark.skip


@pytest.fixture(scope="class")
def pnp_model_id():
    return "dtmi:com:example:TemperatureController;2"


@pytest.fixture(scope="class")
def client_kwargs(pnp_model_id):
    return {"model_id": pnp_model_id}


@pytest.mark.pnp
@pytest.mark.describe("Device Client PNP Connection")
class TestPnpConnect(object):
    @pytest.mark.it("Can connect and disconnect with model_id set")
    async def test_connect(self, client, pnp_model_id):
        assert client._mqtt_pipeline.pipeline_configuration.model_id == pnp_model_id

        assert client
        await client.connect()
        assert client.connected

        await client.disconnect()
        assert not client.connected

        await client.connect()
        assert client.connected

    @pytest.mark.it("Shows up as a PNP device in the service client")
    async def test_model_id_in_service_helper(
        self, client, pnp_model_id, device_id, module_id, service_helper
    ):

        assert client._mqtt_pipeline.pipeline_configuration.model_id == pnp_model_id
        assert client.connected

        props = await service_helper.get_pnp_properties(device_id, module_id)

        assert props["$metadata"]["$model"] == pnp_model_id
