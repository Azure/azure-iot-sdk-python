# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

import pytest
from azure.iot.provisioning.servicesdk.auth import (
    ConnectionStringAuthentication,
    HOST_NAME,
    SHARED_ACCESS_KEY,
    SHARED_ACCESS_KEY_NAME,
)


@pytest.fixture(scope="module")
def hostname():
    return "my.host.name"


@pytest.fixture(scope="module")
def keyname():
    return "mykeyname"


@pytest.fixture(scope="module")
def key():
    return "Zm9vYmFy"


@pytest.fixture(scope="module")
def service_str(hostname, keyname, key):
    return "HostName={};SharedAccessKeyName={};SharedAccessKey={}".format(hostname, keyname, key)


@pytest.fixture(scope="module")
def valid_cs_auth(service_str):
    return ConnectionStringAuthentication(service_str)


def test___repr__(valid_cs_auth, service_str):
    """Test that a string representation of ConnectionStringAuthentication is the same as the
    connection string given to it
    """
    assert str(valid_cs_auth) == service_str


def test__getitem__(valid_cs_auth, hostname, keyname, key):
    """Test that __getitem__ syntax works
    """
    assert valid_cs_auth[HOST_NAME] == hostname
    assert valid_cs_auth[SHARED_ACCESS_KEY_NAME] == keyname
    assert valid_cs_auth[SHARED_ACCESS_KEY] == key
    with pytest.raises(KeyError):
        valid_cs_auth["invalid"]


def test_signed_session(mocker, valid_cs_auth, hostname, keyname, key):
    """Test that a SasToken is created and added to the Authorization header
    """
    mock_sas = mocker.patch("azure.iot.provisioning.servicesdk.auth.SasToken", autospec=True)
    dummy_token = "DUMMY_SASTOKEN"
    mock_sas.return_value.__str__.return_value = (
        dummy_token
    )  # use __str__ instead of __repr__ because __repr__ is NonCallableMock

    session = valid_cs_auth.signed_session()

    mock_sas.assert_called_once_with(hostname, key, keyname)
    assert session.headers["Authorization"] == dummy_token
