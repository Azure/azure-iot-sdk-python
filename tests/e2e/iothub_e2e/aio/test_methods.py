# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import pytest
import logging
import asyncio
import parametrize
from dev_utils import get_random_dict
from azure.iot.device.iothub import MethodResponse

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)

pytestmark = pytest.mark.asyncio


@pytest.fixture
def method_name():
    return "this_is_my_method_name"


@pytest.fixture
def method_response_status():
    return 299


@pytest.mark.describe("Client methods")
class TestMethods(object):
    @pytest.mark.it("Can handle a simple direct method call")
    @pytest.mark.parametrize(*parametrize.all_method_payload_options)
    async def test_handle_method_call(
        self,
        client,
        method_name,
        method_response_status,
        include_request_payload,
        include_response_payload,
        service_helper,
        leak_tracker,
    ):
        leak_tracker.set_initial_object_list()

        actual_request = None

        if include_request_payload:
            request_payload = get_random_dict()
        else:
            request_payload = None

        if include_response_payload:
            response_payload = get_random_dict()
        else:
            response_payload = None

        async def handle_on_method_request_received(request):
            nonlocal actual_request
            logger.info("Method request for {} received".format(request.name))
            actual_request = request
            logger.info("Sending response")
            await client.send_method_response(
                MethodResponse.create_from_method_request(
                    request, method_response_status, response_payload
                )
            )

        client.on_method_request_received = handle_on_method_request_received
        await asyncio.sleep(1)  # wait for subscribe, etc, to complete

        # invoke the method call
        method_response = await service_helper.invoke_method(method_name, request_payload)

        # verify that the method request arrived correctly
        assert actual_request.name == method_name
        if request_payload:
            assert actual_request.payload == request_payload
        else:
            assert not actual_request.payload

        # and make sure the response came back successfully
        assert method_response.status == method_response_status
        assert method_response.payload == response_payload

        actual_request = None  # so this isn't tagged as a leak
        leak_tracker.check_for_leaks()
