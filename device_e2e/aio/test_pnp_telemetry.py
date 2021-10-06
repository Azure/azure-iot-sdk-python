# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import pytest
import logging
import pprint
import const
from utils import get_random_dict
import azure.iot.device.iothub

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)

pytestmark = pytest.mark.asyncio
if not getattr(azure.iot.device.iothub, "CommandRequest", None):
    # only run if PNP enabled
    pytestmark = pytest.mark.skip


@pytest.fixture(scope="class")
def extra_client_kwargs(pnp_model_id):
    return {"model_id": pnp_model_id}


@pytest.mark.pnp
@pytest.mark.describe("Pnp Telemetry")
class TestPnpTelemetry(object):
    @pytest.mark.it("Can send a telemetry message")
    async def test_send_pnp_telemetry(self, client, pnp_model_id, get_next_eventhub_arrival):
        telemetry = get_random_dict()

        await client.send_telemetry(telemetry)
        event = await get_next_eventhub_arrival()

        logger.info(pprint.pformat(event))

        assert event.message_body == telemetry

        system_props = event.system_properties
        assert system_props[const.EVENTHUB_SYSPROP_DT_DATASCHEMA] == pnp_model_id
        assert system_props[const.EVENTHUB_SYSPROP_CONTENT_TYPE] == const.JSON_CONTENT_TYPE
        assert system_props[const.EVENTHUB_SYSPROP_CONTENT_ENCODING] == const.JSON_CONTENT_ENCODING
