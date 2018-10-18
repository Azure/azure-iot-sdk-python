# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

from azure.iot.hub.devicesdk.symmetric_key_authentication_provider import (
    SymmetricKeyAuthenticationProvider,
)
import pytest


connection_string_device_sk_format = "HostName={};DeviceId={};SharedAccessKey={}"
connection_string_device_skn_format = (
    "HostName={};DeviceId={};SharedAccessKeyName={};SharedAccessKey={}"
)
connection_string_module_sk_format = (
    "HostName={};DeviceId={};ModuleId={};SharedAccessKey={};GatewayHostName={}"
)

shared_access_key = "Zm9vYmFy"
shared_access_key_name = "alohomora"
hostname = "beauxbatons.academy-net"
device_id = "MyPensieve"
module_id = "Divination"
gateway_name = "EnchantedCeiling"


def test_create_from_incomplete_connection_string():
    with pytest.raises(ValueError, match="Invalid Connection String - Incomplete"):
        connection_string = "HostName=beauxbatons.academy-net;SharedAccessKey=Zm9vYmFy"
        SymmetricKeyAuthenticationProvider.create_authentication_from_connection_string(
            connection_string
        )


def test_create_from_duplicatekeys_connection_string():
    with pytest.raises(ValueError, match="Invalid Connection String - Unable to parse"):
        connection_string = (
            "HostName=beauxbatons.academy-net;HostName=TheDeluminator;HostName=Zm9vYmFy"
        )
        SymmetricKeyAuthenticationProvider.create_authentication_from_connection_string(
            connection_string
        )


# Without the proper delimiter the dictionary function itself can't take place
def test_create_from_badparsing_connection_string():
    with pytest.raises(ValueError):
        connection_string = "HostName+beauxbatons.academy-net!DeviceId+TheDeluminator!"
        SymmetricKeyAuthenticationProvider.create_authentication_from_connection_string(
            connection_string
        )


def test_create_from_badkeys_connection_string():
    with pytest.raises(ValueError, match="Invalid Connection String - Invalid Key"):
        connection_string = "BadHostName=beauxbatons.academy-net;BadDeviceId=TheDeluminator;SharedAccessKey=Zm9vYmFy"
        SymmetricKeyAuthenticationProvider.create_authentication_from_connection_string(
            connection_string
        )


def test_create_from_connection_string():
    connection_string = connection_string_device_sk_format.format(
        hostname, device_id, shared_access_key
    )
    authentication_provider = SymmetricKeyAuthenticationProvider.create_authentication_from_connection_string(
        connection_string
    )
    assert authentication_provider.hostname == hostname
    assert authentication_provider.device_id == device_id


def test_create_from_module_gateway_connection_string():
    connection_string = connection_string_module_sk_format.format(
        hostname, device_id, module_id, shared_access_key, gateway_name
    )
    authentication_provider = SymmetricKeyAuthenticationProvider.create_authentication_from_connection_string(
        connection_string
    )
    assert authentication_provider.module_id == module_id
    assert authentication_provider.gateway_hostname == gateway_name


def test_sastoken_key(mocker):
    uri = hostname + "/devices/" + device_id
    mock_sastoken = mocker.patch(
        "azure.iot.hub.devicesdk.symmetric_key_authentication_provider.SasToken"
    )
    dummy_value = "SharedAccessSignature sr=beauxbatons.academy-net%2Fdevices%2FMyPensieve&sig=zh8pwNIG56yUd3Nna7lyKA2HQAns84U3XwxyFQJqh48%3D&se=1539036534"
    mock_sastoken.return_value.__str__.return_value = dummy_value

    connection_string = connection_string_device_sk_format.format(
        hostname, device_id, shared_access_key
    )
    SymmetricKeyAuthenticationProvider.create_authentication_from_connection_string(
        connection_string
    )

    mock_sastoken.assert_called_once_with(uri, shared_access_key)


def test_sastoken_keyname(mocker):
    uri = hostname + "/devices/" + device_id
    mock_sastoken = mocker.patch(
        "azure.iot.hub.devicesdk.symmetric_key_authentication_provider.SasToken"
    )
    dummy_value = "SharedAccessSignature sr=beauxbatons.academy-net%2Fdevices%2FMyPensieve&sig=fT/nO0NA/25IKl0Ei2upxDDj6KnY6RPVIjlV84/9aR8%3D&se=1539043658&skn=alohomora"
    mock_sastoken.return_value.__str__.return_value = dummy_value

    connection_string = connection_string_device_skn_format.format(
        hostname, device_id, shared_access_key_name, shared_access_key
    )
    SymmetricKeyAuthenticationProvider.create_authentication_from_connection_string(
        connection_string
    )

    mock_sastoken.assert_called_once_with(uri, shared_access_key, shared_access_key_name)
