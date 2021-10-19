# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
import pytest
import logging
import asyncio
import pprint
import azure.iot.device.iothub
from utils import get_random_dict, make_pnp_desired_property_patch

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)

pytestmark = pytest.mark.asyncio
try:
    ClientPropertyCollection = azure.iot.device.iothub.ClientPropertyCollection
    generate_writable_property_response = (
        azure.iot.device.iothub.generate_writable_property_response
    )
except AttributeError:
    # only run if PNP enabled
    pytestmark = pytest.mark.skip


@pytest.fixture(scope="class")
def extra_client_kwargs(pnp_model_id):
    return {"model_id": pnp_model_id}


@pytest.mark.pnp
@pytest.mark.parametrize(
    "is_component_property",
    [pytest.param(True, id="component property"), pytest.param(False, id="root property")],
)
@pytest.mark.describe("Device Client PNP properties")
class TestPnpSetProperties(object):
    @pytest.mark.it(
        "Can set a reported property value and retrieve it via the service get_digital_twin function"
    )
    async def test_set_reported_property(
        self,
        client,
        pnp_read_only_property_name,
        pnp_component_name,
        is_component_property,
        service_helper,
        device_id,
        module_id,
    ):
        random_property_value = get_random_dict()
        assert client.connected

        patch = ClientPropertyCollection()
        if is_component_property:
            patch.set_component_property(
                pnp_component_name, pnp_read_only_property_name, random_property_value
            )
        else:
            patch.set_property(pnp_read_only_property_name, random_property_value)

        logger.info("Setting {} to {}".format(pnp_read_only_property_name, random_property_value))
        await client.update_client_properties(patch)

        while True:
            properties = await service_helper.get_pnp_properties(device_id, module_id)

            if is_component_property:
                actual_value = properties.get(pnp_component_name, {}).get(
                    pnp_read_only_property_name, None
                )
            else:
                actual_value = properties.get(pnp_read_only_property_name, None)

            if actual_value == random_property_value:
                return

            else:
                logger.warning(
                    "property not matched yet.  Expected = {}, actual = {}".format(
                        random_property_value, actual_value
                    )
                )

            logger.warning(
                "digital_twin_client.get_digital_twin returned {}".format(
                    pprint.pformat(properties)
                )
            )

            await asyncio.sleep(5)

    @pytest.mark.it("Can retrieve a reported property via the get_client_properties function")
    async def test_get_reported_property(
        self,
        client,
        pnp_read_only_property_name,
        pnp_component_name,
        is_component_property,
    ):
        random_property_value = get_random_dict()
        assert client.connected

        patch = ClientPropertyCollection()
        if is_component_property:
            patch.set_component_property(
                pnp_component_name, pnp_read_only_property_name, random_property_value
            )
        else:
            patch.set_property(pnp_read_only_property_name, random_property_value)

        logger.info("Setting {} to {}".format(pnp_read_only_property_name, random_property_value))
        await client.update_client_properties(patch)

        properties = await client.get_client_properties()

        if is_component_property:
            assert (
                properties.reported_from_device.get_component_property(
                    pnp_component_name, pnp_read_only_property_name
                )
                == random_property_value
            )

            assert properties.reported_from_device.backing_object[pnp_component_name]["__t"] == "c"
        else:
            assert (
                properties.reported_from_device.get_property(pnp_read_only_property_name)
                == random_property_value
            )

    @pytest.mark.it("Can retrieve a desired property via the get_client_properties function")
    async def test_desired_properties_via_get_client_properties(
        self,
        event_loop,
        client,
        pnp_component_name,
        pnp_writable_property_name,
        is_component_property,
        service_helper,
        device_id,
        module_id,
    ):
        random_property_value = get_random_dict()
        received = asyncio.Event()

        async def handle_on_patch_received(patch):
            nonlocal received
            logger.info("received {}".format(patch))
            event_loop.call_soon_threadsafe(received.set)

        client.on_writable_property_update_request_received = handle_on_patch_received
        await asyncio.sleep(1)

        props = make_pnp_desired_property_patch(
            pnp_component_name if is_component_property else None,
            pnp_writable_property_name,
            random_property_value,
        )
        await service_helper.update_pnp_properties(device_id, module_id, props)

        # wait for the desired property patch to arrive at the client
        # We don't actually check the contents of the patch, but the
        # fact that it arrived means the device registry should have
        # finished ingesting the patch
        await asyncio.wait_for(received.wait(), 10)
        logger.info("got it")

        properties = await client.get_client_properties()
        if is_component_property:
            assert (
                properties.writable_properties_requests.get_component_property(
                    pnp_component_name, pnp_writable_property_name
                )
                == random_property_value
            )
            assert (
                properties.writable_properties_requests.backing_object[pnp_component_name]["__t"]
                == "c"
            )
        else:
            assert (
                properties.writable_properties_requests.get_property(pnp_writable_property_name)
                == random_property_value
            )

    @pytest.mark.it(
        "can receive a desired property patch and corectly respond with a writable_property_response"
    )
    async def test_receive_desired_property_patch(
        self,
        event_loop,
        client,
        pnp_component_name,
        pnp_writable_property_name,
        is_component_property,
        pnp_ack_code,
        pnp_ack_description,
        service_helper,
        device_id,
        module_id,
    ):
        random_property_value = get_random_dict()
        received_patch = None
        received = asyncio.Event()

        async def handle_on_patch_received(patch):
            nonlocal received_patch, received
            logger.info("received {}".format(patch))
            received_patch = patch
            event_loop.call_soon_threadsafe(received.set)

        client.on_writable_property_update_request_received = handle_on_patch_received
        await asyncio.sleep(1)

        # patch desired properites
        props = make_pnp_desired_property_patch(
            pnp_component_name if is_component_property else None,
            pnp_writable_property_name,
            random_property_value,
        )
        await service_helper.update_pnp_properties(device_id, module_id, props)
        logger.info("patch sent. Waiting for desired proprety")

        # wait for the desired property patch to arrive at the client
        await asyncio.wait_for(received.wait(), 10)
        logger.info("got it")

        # validate the patch
        if is_component_property:
            assert (
                received_patch.get_component_property(
                    pnp_component_name, pnp_writable_property_name
                )
                == random_property_value
            )
            assert received_patch.backing_object[pnp_component_name]["__t"] == "c"
        else:
            assert received_patch.get_property(pnp_writable_property_name) == random_property_value

        # make a reported property patch to respond
        update_patch = ClientPropertyCollection()
        property_response = generate_writable_property_response(
            random_property_value, pnp_ack_code, pnp_ack_description, received_patch.version
        )

        if is_component_property:
            update_patch.set_component_property(
                pnp_component_name, pnp_writable_property_name, property_response
            )
        else:
            update_patch.set_property(pnp_writable_property_name, property_response)

        # send the reported property patch
        await client.update_client_properties(update_patch)

        # verify that the reported value via digital_twin_client.get_digital_twin()
        props = await service_helper.get_pnp_properties(device_id, module_id)
        if is_component_property:
            props = props[pnp_component_name]

        assert props[pnp_writable_property_name] == random_property_value
        metadata = props["$metadata"][pnp_writable_property_name]
        assert metadata["ackCode"] == pnp_ack_code
        assert metadata["ackDescription"] == pnp_ack_description
        assert metadata["ackVersion"] == received_patch.version
        assert metadata["desiredVersion"] == received_patch.version
        assert metadata["desiredValue"] == random_property_value


# TODO: etag tests, version tests
