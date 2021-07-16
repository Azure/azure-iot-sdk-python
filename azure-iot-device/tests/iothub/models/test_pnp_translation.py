# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

from azure.iot.device.iothub.models.pnp_translation import (
    client_property_collection_to_twin_patch,
    command_response_to_method_response,
    method_request_to_command_request,
    twin_patch_to_client_property_collection,
    twin_to_client_properties,
)
from azure.iot.device.iothub.models.methods import MethodRequest, MethodResponse
from azure.iot.device.iothub.models import (
    CommandRequest,
    CommandResponse,
    ClientPropertyCollection,
    ClientProperties,
)
import pytest
import logging

logging.basicConfig(level=logging.DEBUG)


@pytest.mark.describe("method_request_to_command_request()")
class TestMethodRequestToCommand(object):
    @pytest.mark.it("Returns a CommandRequest with values derived from the given MethodRequest")
    @pytest.mark.parametrize(
        "request_name, expected_component_name, expected_command_name",
        [
            pytest.param(
                "some_component*some_command",
                "some_component",
                "some_command",
                id="Request name in Component format",
            ),
            pytest.param(
                "some_command", None, "some_command", id="Request name in Non-Component format"
            ),
        ],
    )
    def test_translation(self, request_name, expected_component_name, expected_command_name):
        method_request = MethodRequest(request_id="1", name=request_name, payload={"key": "value"})
        command_request = method_request_to_command_request(method_request)

        assert isinstance(command_request, CommandRequest)
        assert command_request.request_id == method_request.request_id
        assert command_request.payload == method_request.payload
        assert command_request.component_name == expected_component_name
        assert command_request.command_name == expected_command_name


@pytest.mark.describe("command_response_to_method_response()")
class TestCommandResponseToMethodResponse(object):
    @pytest.mark.it("Returns a MethodResponse with values derived from the given CommandResponse")
    def test_translation(self):
        command_response = CommandResponse(request_id="1", status=200, payload={"key:": "value"})
        method_response = command_response_to_method_response(command_response)

        assert isinstance(method_response, MethodResponse)
        assert method_response.request_id == command_response.request_id
        assert method_response.status == command_response.status
        assert method_response.payload == command_response.payload


@pytest.mark.describe("twin_patch_to_client_property_collection()")
class TestTwinPatchToClientPropertyCollection(object):
    @pytest.mark.it(
        "Returns a ClientPropertyCollection with values derived from the given twin patch"
    )
    def test_translation(self):
        twin_patch = {
            "component1": {
                "__t": "c",
                "component_property1": "foo",
                "component_property2": "bar",
            },
            "property1": "buz",
            "property2": "baz",
            "$version": 12,
        }
        cpc = twin_patch_to_client_property_collection(twin_patch)
        assert isinstance(cpc, ClientPropertyCollection)
        assert cpc.backing_object is twin_patch


@pytest.mark.describe("twin_to_client_properties()")
class TestTwinToClientProperties(object):
    @pytest.mark.it("Returns a ClientProperties with values derived from the given twin")
    def test_translation(self, fake_twin):
        client_properties = twin_to_client_properties(fake_twin)
        assert isinstance(client_properties, ClientProperties)
        assert isinstance(client_properties.reported_from_device, ClientPropertyCollection)
        assert client_properties.reported_from_device.backing_object is fake_twin["reported"]
        assert isinstance(client_properties.writable_properties_requests, ClientPropertyCollection)
        assert client_properties.writable_properties_requests.backing_object is fake_twin["desired"]


@pytest.mark.describe("client_property_collection_to_twin_patch()")
class TestClientPropertyCollectionToTwinPatch(object):
    @pytest.mark.it(
        "Returns a twin patch with values derived from the given ClientPropertyCollection"
    )
    def test_translation(self):
        source_twin_patch = {
            "component1": {
                "__t": "c",
                "component_property1": "foo",
                "component_property2": "bar",
            },
            "property1": "buz",
            "property2": "baz",
        }
        cpc = ClientPropertyCollection()
        cpc.backing_object = source_twin_patch

        twin_patch = client_property_collection_to_twin_patch(cpc)
        assert twin_patch is cpc.backing_object
