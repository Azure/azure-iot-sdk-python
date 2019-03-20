# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
from azure.iot.hub.devicesdk.transport.abstract_transport import AbstractTransport
from azure.iot.hub.devicesdk.transport import constant

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


"""----Shared mock transport fixture----"""


class FakeTransport(AbstractTransport):
    def connect(self, callback):
        callback()

    def disconnect(self, callback):
        callback()

    def enable_feature(self, feature_name, callback=None, qos=1):
        callback()

    def disable_feature(self, feature_name, callback=None):
        callback()

    def send_event(self, event, callback):
        callback()

    def send_output_event(self, event, callback):
        callback()

    def send_method_response(self, method, payload, status, callback=None):
        callback()


@pytest.fixture
def transport(mocker):
    return mocker.MagicMock(wraps=FakeTransport(mocker.MagicMock()))
