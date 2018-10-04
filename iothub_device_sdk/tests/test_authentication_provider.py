# Temporary path hack (replace once monorepo path solution implemented)
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..\..\python_shared_utils"))
# ---------------------------------------------------------------------

from connection_string import ConnectionString, HOST_NAME, SHARED_ACCESS_KEY_NAME, SHARED_ACCESS_KEY, SHARED_ACCESS_SIGNATURE, DEVICE_ID, MODULE_ID, GATEWAY_HOST_NAME
from sastoken import SasToken
from ..device.authentication_provider import AuthenticationProvider

connection_string_format = "HostName={};DeviceId={};SharedAccessKey={}"
connection_string_skn_format = "HostName={};SharedAccessKeyName={};SharedAccessKey={}"
shared_access_key = "Zm9vYmFy"
shared_access_key_name = "alohomora"
hostname = "beauxbatons.academy-net"
device_id = "MyPensieve"


def test_create_from_connection_string():
    connection_string = connection_string_format.format(hostname, device_id, shared_access_key)
    authentication_provider = AuthenticationProvider.create_authentication_from_connection_string(connection_string)
    assert authentication_provider.get_hostname() == hostname
    assert authentication_provider.get_device_id() == device_id


def test_sastoken_key():
    connection_string = connection_string_format.format(hostname, device_id, shared_access_key)
    authentication_provider = AuthenticationProvider.create_authentication_from_connection_string(connection_string)

    uri = hostname + "/devices/" + device_id
    sas_token = SasToken(uri, shared_access_key)

    assert str(authentication_provider.get_current_sas_token()) == str(sas_token)

def test_sastoken_keyname():
    connection_string = connection_string_skn_format.format(hostname, shared_access_key_name, shared_access_key)
    authentication_provider = AuthenticationProvider.create_authentication_from_connection_string(connection_string)

    uri = hostname
    sas_token = SasToken(uri, shared_access_key, shared_access_key_name)

    assert str(authentication_provider.get_current_sas_token()) == str(sas_token)