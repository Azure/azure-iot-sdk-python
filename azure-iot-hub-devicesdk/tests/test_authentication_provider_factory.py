# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

from azure.iot.hub.devicesdk.auth.authentication_provider_factory import (
    from_connection_string,
    from_shared_access_signature,
)
from azure.iot.hub.devicesdk.auth.sk_authentication_provider import (
    SymmetricKeyAuthenticationProvider,
)
from azure.iot.hub.devicesdk.auth.sas_authentication_provider import (
    SharedAccessSignatureAuthenticationProvider,
)


connection_string_device_sk_format = "HostName={};DeviceId={};SharedAccessKey={}"
connection_string_device_skn_format = (
    "HostName={};DeviceId={};SharedAccessKeyName={};SharedAccessKey={}"
)
connection_string_module_sk_format = "HostName={};DeviceId={};ModuleId={};SharedAccessKey={}"
connection_string_module_gateway_sk_format = (
    "HostName={};DeviceId={};ModuleId={};SharedAccessKey={};GatewayHostName={}"
)

sas_device_token_format = "SharedAccessSignature sr={}&sig={}&se={}"

shared_access_key = "Zm9vYmFy"
shared_access_key_name = "alohomora"
hostname = "beauxbatons.academy-net"
device_id = "MyPensieve"
module_id = "Divination"
gateway_name = "EnchantedCeiling"
signature = "IsolemnlySwearThatIamuUptoNogood"
expiry = "1539043658"


sas_device_token_format = "SharedAccessSignature sr={}&sig={}&se={}"
sas_device_skn_token_format = "SharedAccessSignature sr={}&sig={}&se={}&skn={}"


def test_sk_auth_provider_created_correctly_from_device_connection_string():
    connection_string = connection_string_device_sk_format.format(
        hostname, device_id, shared_access_key
    )
    auth_provider = from_connection_string(connection_string)
    assert isinstance(auth_provider, SymmetricKeyAuthenticationProvider)
    assert auth_provider.device_id == device_id
    assert auth_provider.hostname == hostname


def test_sk_auth_provider_created_correctly_from_module_connection_string():
    connection_string = connection_string_module_sk_format.format(
        hostname, device_id, module_id, shared_access_key
    )
    auth_provider = from_connection_string(connection_string)
    assert isinstance(auth_provider, SymmetricKeyAuthenticationProvider)
    assert auth_provider.device_id == device_id
    assert auth_provider.hostname == hostname
    assert auth_provider.module_id == module_id


def test_sas_auth_provider_created_correctly_from_device_shared_access_signature_string():
    sas_string = create_sas_token_string()
    auth_provider = from_shared_access_signature(sas_string)

    assert isinstance(auth_provider, SharedAccessSignatureAuthenticationProvider)
    assert auth_provider.device_id == device_id
    assert auth_provider.hostname == hostname


def test_sas_auth_provider_created_correctly_from_module_shared_access_signature_string():
    sas_string = create_sas_token_string(True)
    auth_provider = from_shared_access_signature(sas_string)

    assert isinstance(auth_provider, SharedAccessSignatureAuthenticationProvider)
    assert auth_provider.device_id == device_id
    assert auth_provider.hostname == hostname
    assert auth_provider.module_id == module_id


def test_sas_auth_provider_created_correctly_from_module_shared_access_signature_string_keyname():
    sas_string = create_sas_token_string(True, True)
    auth_provider = from_shared_access_signature(sas_string)

    assert isinstance(auth_provider, SharedAccessSignatureAuthenticationProvider)
    assert auth_provider.device_id == device_id
    assert auth_provider.hostname == hostname
    assert auth_provider.module_id == module_id
    assert shared_access_key_name in auth_provider.get_current_sas_token()


def create_sas_token_string(is_module=False, is_key_name=False):
    uri = hostname + "/devices/" + device_id
    if is_module:
        uri = uri + "/modules/" + module_id
    if is_key_name:
        return sas_device_skn_token_format.format(uri, signature, expiry, shared_access_key_name)
    else:
        return sas_device_token_format.format(uri, signature, expiry)
