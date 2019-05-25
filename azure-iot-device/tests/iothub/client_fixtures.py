# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
from azure.iot.device.iothub.pipeline import constant

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
    from azure.iot.device.iothub.auth.authentication_provider_factory import (
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


"""----Shared mock pipeline adapter fixture----"""


class FakePipelineAdapter:
    def __init__(self):
        self.feature_enabled = {
            constant.C2D_MSG: False,
            constant.INPUT_MSG: False,
            constant.METHODS: False,
        }

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

    def send_method_response(self, method_response, callback=None):
        callback()


@pytest.fixture
def pipeline(mocker):
    return mocker.MagicMock(wraps=FakePipelineAdapter())
