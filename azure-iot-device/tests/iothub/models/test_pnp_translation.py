# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

from azure.iot.device.iothub.models.digital_twin_translation import (
    command_response_to_method_response,
    method_request_to_command,
)
from azure.iot.device.iothub.models.methods import MethodRequest, MethodResponse
from azure.iot.device.iothub.models import Command, CommandResponse
import pytest
import logging

logging.basicConfig(level=logging.DEBUG)


@pytest.mark.describe("method_request_to_command()")
class TestMethodRequestToCommand(object):
    @pytest.mark.it("Returns a Command with values derived from the given MethodRequest")
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
        command = method_request_to_command(method_request)

        assert isinstance(command, Command)
        assert command.request_id == method_request.request_id
        assert command.payload == method_request.payload
        assert command.component_name == expected_component_name
        assert command.command_name == expected_command_name


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
