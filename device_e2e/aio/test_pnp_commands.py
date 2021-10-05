# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import pytest
import logging
import asyncio
from utils import get_random_dict
import azure.iot.device.iothub

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)

pytestmark = pytest.mark.asyncio
try:
    CommandResponse = azure.iot.device.iothub.CommandResponse
except AttributeError:
    # only run if PNP enabled
    pytestmark = pytest.mark.skip


@pytest.fixture(scope="class")
def client_kwargs(pnp_model_id):
    return {"model_id": pnp_model_id}


@pytest.mark.pnp
@pytest.mark.describe("Pnp Commands")
class TestPnpCommands(object):
    @pytest.mark.it("Can handle a simple command")
    @pytest.mark.parametrize(
        "include_request_payload",
        [
            pytest.param(True, id="with request payload"),
            pytest.param(False, id="without request payload"),
        ],
    )
    @pytest.mark.parametrize(
        "include_response_payload",
        [
            pytest.param(True, id="with response payload"),
            pytest.param(False, id="without response payload"),
        ],
    )
    @pytest.mark.parametrize(
        "include_component_name",
        [
            pytest.param(True, id="with component name"),
            pytest.param(False, id="without component name"),
        ],
    )
    async def test_handle_pnp_commmand(
        self,
        client,
        event_loop,
        pnp_command_name,
        pnp_component_name,
        pnp_command_response_status,
        include_component_name,
        include_request_payload,
        include_response_payload,
        service_helper,
        device_id,
        module_id,
    ):
        actual_request = None

        if include_request_payload:
            request_payload = get_random_dict()
        else:
            request_payload = ""

        if include_response_payload:
            response_payload = get_random_dict()
        else:
            response_payload = None

        async def handle_on_command_request_received(request):
            nonlocal actual_request
            logger.info(
                "command request for component {}, command {} received".format(
                    request.component_name, request.command_name
                )
            )
            actual_request = request
            logger.info("Sending response")
            await client.send_command_response(
                CommandResponse.create_from_command_request(
                    request, pnp_command_response_status, response_payload
                )
            )

        client.on_command_request_received = handle_on_command_request_received
        await asyncio.sleep(1)  # wait for subscribe, etc, to complete

        # invoke the command
        command_response = await service_helper.invoke_pnp_command(
            device_id, module_id, pnp_component_name, pnp_command_name, request_payload
        )

        # verify that the method request arrived correctly
        assert actual_request.command_name == pnp_command_name
        assert actual_request.component_name == pnp_component_name

        if request_payload:
            assert actual_request.payload == request_payload
        else:
            assert not actual_request.payload

        # and make sure the response came back successfully
        # Currently no way to check the command response status code because the DigitalTwinClient A
        # object in the service SDK does not return this to the caller.
        # assert command_response[Fields.COMMAND_RESPONSE_STATUS_CODE] == command_response_status
        assert command_response == response_payload
