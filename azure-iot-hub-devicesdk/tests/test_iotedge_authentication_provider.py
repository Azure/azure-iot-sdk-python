# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------
import os
import pytest
from azure.iot.hub.devicesdk.auth.iotedge_authentication_provider import IotEdgeAuthenticationProvider

from six import add_move, MovedModule

add_move(MovedModule("mock", "mock", "unittest.mock"))
from six.moves import mock
from mock import Mock
from mock import patch

fake_ca_cert = "__FAKE_CA_CERTIFICATE__"
fake_module_id = "__FAKE_MODULE_ID__"
fake_device_id = "__FAKE_DEVICE_ID__"
fake_hostname = "__FAKE_HOSTNAME__"
fake_gateway_hostname = "__FAKE_GATEWAY_HOSTNAME__"
fake_digest = "__FAKE_DIGEST__"

required_environment_variables = {
    "IOTEDGE_MODULEID": fake_module_id,
    "IOTEDGE_DEVICEID": fake_device_id,
    "IOTEDGE_IOTHUBHOSTNAME": fake_hostname,
    "IOTEDGE_GATEWAYHOSTNAME": fake_gateway_hostname
}

@patch.dict(os.environ, required_environment_variables)
@patch("azure.iot.hub.devicesdk.auth.iotedge_authentication_provider.IotEdgeHsm")
def test_initializer_gets_details_from_environment(mock_hsm):
    auth_provider = IotEdgeAuthenticationProvider()
    assert(auth_provider.gateway_hostname == fake_gateway_hostname)
    assert(auth_provider.device_id == fake_device_id)
    assert(auth_provider.module_id == fake_module_id)
    assert(auth_provider.hostname == fake_hostname)

@patch.dict(os.environ, required_environment_variables)
@patch("azure.iot.hub.devicesdk.auth.iotedge_authentication_provider.IotEdgeHsm")
def test_initializer_gets_ca_certificate_from_hsm(MockHsm):
    MockHsm.return_value.get_trust_bundle.return_value = fake_ca_cert
    auth_provider = IotEdgeAuthenticationProvider()
    assert(auth_provider.ca_cert == fake_ca_cert)
    

@patch.dict(os.environ, required_environment_variables)
@patch("azure.iot.hub.devicesdk.auth.iotedge_authentication_provider.IotEdgeHsm")
def test_get_shared_access_key_uses_hsm_to_sign(MockHsm):
    MockHsm.return_value.sign.return_value = fake_digest
    auth_provider = IotEdgeAuthenticationProvider()
    sas_token = auth_provider.get_current_sas_token()
    assert(MockHsm.return_value.sign.call_args[0][0].startswith("{}%2Fdevices%2F{}%2Fmodules%2F{}\n".format(fake_hostname, fake_device_id, fake_module_id)))
    assert(sas_token.startswith("SharedAccessSignature sr={}%2Fdevices%2F{}%2Fmodules%2F{}&sig={}&se=".format(fake_hostname, fake_device_id, fake_module_id, fake_digest)))



