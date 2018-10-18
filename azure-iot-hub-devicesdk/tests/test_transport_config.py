# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

from azure.iot.hub.devicesdk.symmetric_key_authentication_provider import (
    SymmetricKeyAuthenticationProvider,
)
from azure.iot.hub.devicesdk.transport.mqtt.mqtt_transport import MQTTTransport
from azure.iot.hub.devicesdk.transport.transport_config import TransportConfig, TransportProtocol
import pytest

connection_string_format = "HostName={};DeviceId={};SharedAccessKey={}"
shared_access_key = "Zm9vYmFy"
hostname = "beauxbatons.academy-net"
device_id = "MyPensieve"


@pytest.fixture
def connection_string():
    connection_string = connection_string_format.format(hostname, device_id, shared_access_key)
    return connection_string


@pytest.fixture
def authentication_provider(connection_string):
    auth_provider = SymmetricKeyAuthenticationProvider.create_authentication_from_connection_string(
        connection_string
    )
    return auth_provider


def test_create():
    transport_config = TransportConfig(TransportProtocol.MQTT)
    assert transport_config.device_transport is None
    assert transport_config._transport_protocol == TransportProtocol.MQTT


def test_create_specific_transport(mocker, authentication_provider):
    mock_transport = mocker.patch(
        "azure.iot.hub.devicesdk.transport.transport_config.MQTTTransport"
    )

    transport_config = TransportConfig(TransportProtocol.MQTT)
    transport_config.get_specific_transport(authentication_provider)

    mock_transport.assert_called_once_with(authentication_provider)
