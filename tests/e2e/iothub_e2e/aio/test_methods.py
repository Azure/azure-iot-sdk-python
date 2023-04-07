# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import asyncio
import pytest
import logging
import parametrize
from dev_utils import get_random_dict
from azure.iot.device import DirectMethodResponse

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)


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
        session_object,
        method_name,
        method_response_status,
        include_request_payload,
        include_response_payload,
        service_helper,
        leak_tracker,
    ):
        leak_tracker.set_initial_object_list()
        registered = asyncio.Event()

        actual_request = None

        if include_request_payload:
            request_payload = get_random_dict()
        else:
            request_payload = None

        if include_response_payload:
            response_payload = get_random_dict()
        else:
            response_payload = None

        async def method_listener(sess):
            try:
                nonlocal actual_request
                async with sess.direct_method_requests() as requests:
                    registered.set()
                    async for request in requests:
                        logger.info("Method request for {} received".format(request.name))
                        actual_request = request
                        logger.info("Sending response")
                        await sess.send_direct_method_response(
                            DirectMethodResponse.create_from_method_request(
                                request, method_response_status, response_payload
                            )
                        )
            except asyncio.CancelledError:
                # this happens during shutdown. no need to log this.
                raise
            except BaseException:
                # Without this line, exceptions get silently ignored until
                # we await the listener task.
                logger.error("Exception", exc_info=True)
                raise

        async with session_object:
            method_listener_task = asyncio.create_task(method_listener(session_object))

            await registered.wait()

            # invoke the method call
            logger.info("Invoking method")
            method_response = await service_helper.invoke_method(method_name, request_payload)
            logger.info("Done Invoking method")

        assert session_object.connected is False
        with pytest.raises(asyncio.CancelledError):
            await method_listener_task
        method_listener_task = None

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
        # TODO: fix leak
        # leak_tracker.check_for_leaks()
