# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

from azure.iot.hub.devicesdk.sync_clients import ModuleClient, DeviceClient, GenericClientSync
from azure.iot.hub.devicesdk.auth.authentication_provider_factory import from_connection_string
from azure.iot.hub.devicesdk.transport.abstract_transport import AbstractTransport
import pytest
from mock import MagicMock

"""This file is being maintained for legacy tests on handlers until the functionality is replaced
in the API"""


connection_string_format = "HostName={};DeviceId={};SharedAccessKey={}"
shared_access_key = "Zm9vYmFy"
hostname = "beauxbatons.academy-net"
device_id = "MyPensieve"


@pytest.fixture(scope="module")
def connection_string():
    connection_string = connection_string_format.format(hostname, device_id, shared_access_key)
    return connection_string


@pytest.fixture(scope="function")
def authentication_provider(connection_string):
    auth_provider = from_connection_string(connection_string)
    return auth_provider


class FakeTransport(AbstractTransport):
    def __init__(self, auth_provider):
        pass

    def connect(self, callback):
        callback()

    def send_event(self, event, callback):
        callback()

    def send_output_event(self, event, callback):
        callback()

    def disconnect(self, callback):
        callback()


@pytest.fixture(scope="function")
def mock_transport(authentication_provider):
    return MagicMock(wraps=FakeTransport(authentication_provider))


def test_connected_state_handler_called_wth_new_state_once_transport_gets_connected(
    mocker, mock_transport
):
    client = GenericClientSync(mock_transport)
    stub_on_connection_state = mocker.stub(name="on_connection_state")
    client.on_connection_state = stub_on_connection_state

    client.connect()
    mock_transport.on_transport_connected("connected")

    stub_on_connection_state.assert_called_once_with("connected")


def test_connected_state_handler_called_wth_new_state_once_transport_gets_disconnected(
    mocker, mock_transport
):
    client = GenericClientSync(mock_transport)
    stub_on_connection_state = mocker.stub(name="on_connection_state")
    client.on_connection_state = stub_on_connection_state

    client.connect()

    stub_on_connection_state.reset_mock()

    client.disconnect()
    mock_transport.on_transport_disconnected("disconnected")

    stub_on_connection_state.assert_called_once_with("disconnected")
