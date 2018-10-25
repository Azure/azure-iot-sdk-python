# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

from azure.iot.hub.devicesdk.iotedge_hsm import IotEdgeHsm
import pytest
import requests
import os
import json
import base64

from six import add_move, MovedModule

add_move(MovedModule("mock", "mock", "unittest.mock"))
from six.moves import mock
from mock import MagicMock
from mock import patch

fake_module_id = '__FAKE_MODULE__ID__'
fake_api_version = '__FAKE_API_VERSION__'
fake_module_generation_id = '__FAKE_MODULE_GENERATION_ID__'
fake_workload_uri = '__FAKE_WORKLOAD_URI__'
fake_certificate = '__FAKE_CERTIFICATE__'
fake_message = '__FAKE_MESSAGE__'
fake_digest = '__FAKE_DIGEST__'

required_environment_variables = {
    'IOTEDGE_MODULEID': fake_module_id, 
    'IOTEDGE_APIVERSION': fake_api_version,
    'IOTEDGE_MODULEGENERATIONID': fake_module_generation_id,
    'IOTEDGE_WORKLOADURI': fake_workload_uri
}

@patch.dict(os.environ, required_environment_variables)
def test_initializer_doesnt_throw_when_all_environment_variables_are_present():
    hsm = IotEdgeHsm();

def test_initializer_throws_with_missing_environment_variables():
    for key in required_environment_variables:
        env = required_environment_variables.copy()
        del env[key]
        with patch.dict(os.environ, env):
            with pytest.raises(KeyError, match=key):
                hsm = IotEdgeHsm()

@patch.object(requests, 'get')
@patch.dict(os.environ, required_environment_variables)
def test_get_trust_bundle_returns_certificate(mock_get):
    mock_response = mock.Mock(spec = requests.Response)
    mock_response.json.return_value = {'certificate': fake_certificate}
    mock_get.return_value = mock_response
    
    hsm = IotEdgeHsm()
    cert = hsm.get_trust_bundle()

    assert(cert == fake_certificate)
    mock_response.raise_for_status.assert_called_once()  # this verifies that a failed status code will throw
    mock_get.assert_called_once_with(fake_workload_uri + 'trust-bundle', params={'api-version': fake_api_version})

@patch.object(requests, 'post')
@patch.dict(os.environ, required_environment_variables)
def test_get_trust_bundle_returns_certificate(mock_post):
    mock_response = mock.Mock(spec = requests.Response)
    mock_response.json.return_value = {'digest': base64.b64encode(fake_digest.encode())}
    mock_post.return_value = mock_response

    hsm = IotEdgeHsm()
    digest = hsm.sign(fake_message)

    assert(digest == fake_digest)
    mock_response.raise_for_status.assert_called_once()  # this verifies that a failed status code will throw
    fake_url = fake_workload_uri + 'modules/' + fake_module_id + '/genid/' + fake_module_generation_id + '/sign'
    fake_data = json.dumps({
        'keyId': 'primary',
        'algo': 'HMACSHA256',
        'data': base64.b64encode(fake_message.encode()).decode()
    })
    mock_post.assert_called_once_with(fake_url, data=fake_data, params={'api-version': fake_api_version})
    







