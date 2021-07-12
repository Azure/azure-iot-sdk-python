# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

from azure.iot.device.iothub.models.commands import Command, CommandResponse
import pytest
import logging

logging.basicConfig(level=logging.DEBUG)

dummy_rid = 1
dummy_component_name = "some_component_name"
dummy_command_name = "some_command_name"
dummy_payload = {"key": "value"}
dummy_status = 200


@pytest.mark.describe("Command - Instantiation")
class TestCommandInstantiation(object):
    @pytest.mark.it(
        "Instantiates with a read-only 'request_id' attribute set to the value of the provided 'request_id' parameter"
    )
    def test_request_id(self):
        command = Command(
            request_id=dummy_rid,
            component_name=dummy_component_name,
            command_name=dummy_command_name,
            payload=dummy_payload,
        )

        assert command.request_id == dummy_rid

        new_rid = 2
        with pytest.raises(AttributeError):
            command.request_id = new_rid

    @pytest.mark.it(
        "Instantiates with a read-only 'component_name' attribute set to the value of the provided 'component_name' parameter"
    )
    def test_component_name(self):
        command = Command(
            request_id=dummy_rid,
            component_name=dummy_component_name,
            command_name=dummy_command_name,
            payload=dummy_payload,
        )

        assert command.component_name == dummy_component_name

        new_name = "new_name"
        with pytest.raises(AttributeError):
            command.component_name = new_name

    @pytest.mark.it(
        "Instantiates with a read-only 'command_name' attribute set to the value of the provided 'command_name' parameter"
    )
    def test_command_name(self):
        command = Command(
            request_id=dummy_rid,
            component_name=dummy_component_name,
            command_name=dummy_command_name,
            payload=dummy_payload,
        )

        assert command.command_name == dummy_command_name

        new_name = "new_name"
        with pytest.raises(AttributeError):
            command.command_name = new_name

    @pytest.mark.it(
        "Instantiates with a read-only 'payload' attribute set to the value of the provided 'payload' parameter"
    )
    def test_payload(self):
        command = Command(
            request_id=dummy_rid,
            component_name=dummy_component_name,
            command_name=dummy_command_name,
            payload=dummy_payload,
        )

        assert command.payload == dummy_payload

        new_payload = {"another_key": "another_value"}
        with pytest.raises(AttributeError):
            command.payload = new_payload


@pytest.mark.describe("CommandResponse - Instantiation")
class TestCommandResponseInstantiation(object):
    @pytest.mark.it(
        "Instantiates with the 'request_id' attribute set to the value of the provided 'request_id' parameter"
    )
    def test_request_id(self):
        command_response = CommandResponse(request_id=dummy_rid, status=dummy_status)

        assert command_response.request_id == dummy_rid

    @pytest.mark.it(
        "Instantiates with the 'status' attribute set to the value of the provided 'status' parameter"
    )
    def test_status(self):
        command_response = CommandResponse(request_id=dummy_rid, status=dummy_status)

        assert command_response.status == dummy_status

    @pytest.mark.it(
        "Instantiates with the 'payload' attribute set to the value of the 'payload' parameter, if provided"
    )
    def test_payload(self):
        command_response = CommandResponse(
            request_id=dummy_rid, status=dummy_status, payload=dummy_payload
        )

        assert command_response.payload == dummy_payload

    @pytest.mark.it(
        "Instantiates with the 'payload' attribute set to None if no value of the 'payload' parameter is provided"
    )
    def test_payload_default(self):
        command_response = CommandResponse(request_id=dummy_rid, status=dummy_status)

        assert command_response.payload is None


@pytest.mark.describe("CommandResponse - .create_from_command()")
class TestCommandResponseCreateFromCommand(object):
    @pytest.fixture
    def command(self):
        return Command(
            request_id=dummy_rid,
            component_name=dummy_component_name,
            command_name=dummy_command_name,
            payload=dummy_payload,
        )

    @pytest.mark.it(
        "Creates and returns a CommandResponse object containing the provided status and payload, using the request_id of the provided Command"
    )
    def test_instantiation(self, command):
        payload = {"another_key": "another_value"}
        status = 400
        command_response = CommandResponse.create_from_command(
            command=command, status=status, payload=payload
        )

        assert command_response.request_id == command.request_id
        assert command_response.status == status
        assert command_response.payload == payload

    @pytest.mark.it(
        "Defaults the value of 'payload' to None if no value for the 'payload' parameter is provided"
    )
    def test_default_payload(self, command):
        status = 400
        command_response = CommandResponse.create_from_command(command=command, status=status)

        assert command_response.payload is None
