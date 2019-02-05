import sys
import pytest

collect_ignore = []

# Ignore Async tests if below Python 3.5
if sys.version_info < (3, 5):
    collect_ignore.append("transport/mqtt/test_mqtt_async_adapter.py")
    collect_ignore.append("aio/test_async_clients.py")


"""----Shared auth_provider fixture----"""
connection_string_format = "HostName={};DeviceId={};SharedAccessKey={}"
sastoken_format = "SharedAccessSignature sr={}&sig={}&se={}"
shared_access_key = "Zm9vYmFy"
hostname = "beauxbatons.academy-net"
device_id = "MyPensieve"
signature = "IsolemnlySwearThatIamuUptoNogood"
expiry = "1539043658"


@pytest.fixture(params=["SymmetricKey", "SharedAccessSignature"])
def auth_provider(request):
    from azure.iot.hub.devicesdk.auth.authentication_provider_factory import (
        from_connection_string,
        from_shared_access_signature,
    )

    auth_type = request.param
    if auth_type == "SymmetricKey":
        return from_connection_string(
            connection_string_format.format(hostname, device_id, shared_access_key)
        )
    elif auth_type == "SharedAccessSignature":
        uri = hostname + "/devices/" + device_id
        return from_shared_access_signature(sastoken_format.format(uri, signature, expiry))
