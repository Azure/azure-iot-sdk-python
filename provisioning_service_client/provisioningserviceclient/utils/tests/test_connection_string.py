# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

import pytest
from provisioningserviceclient.utils.connection_string import ConnectionString


class TestConnectionStringInput(object):
    def test_empty_input(self):
        with pytest.raises(ValueError):
            ConnectionString("")

    def test_garbage_input(self):
        with pytest.raises(ValueError):
            ConnectionString("garbage")

    def test_incomplete_input(self):
        with pytest.raises(ValueError):
            ConnectionString("HostName=my.host.name")

    def test_invalid_key(self):
        with pytest.raises(ValueError):
            ConnectionString(
                "InvalidKey=my.host.name;SharedAccessKeyName=mykeyname;SharedAccessKey=Zm9vYmFy"
            )

    def test_duplicate_key(self):
        with pytest.raises(ValueError):
            ConnectionString(
                "HostName=my.host.name;HostName=my.host.name;SharedAccessKey=mykeyname;SharedAccessKey=Zm9vYmFy"
            )

    def test_service_string(self):
        ConnectionString(
            "HostName=my.host.name;SharedAccessKeyName=mykeyname;SharedAccessKey=Zm9vYmFy"
        )

    def test_device_string(self):
        ConnectionString("HostName=my.host.name;DeviceId=my-device;SharedAccessKey=Zm9vYmFy")

    def test_device_string_with_gateway_hostname(self):
        ConnectionString(
            "HostName=my.host.name;DeviceId=my-device;SharedAccessKey=Zm9vYmFy;GatewayHostName=mygateway"
        )

    def test_module_string(self):
        ConnectionString(
            "HostName=my.host.name;DeviceId=my-device;ModuleId=my-module;SharedAccessKey=Zm9vYmFy"
        )

    def test_module_string_with_gateway_hostname(self):
        ConnectionString(
            "HostName=my.host.name;DeviceId=my-device;ModuleId=my-module;SharedAccessKey=Zm9vYmFy;GatewayHostName=mygateway"
        )


def test___repr__():
    string = "HostName=my.host.name;SharedAccessKeyName=mykeyname;SharedAccessKey=Zm9vYmFy"
    cs = ConnectionString(string)
    assert str(cs) == string


def test___getitem__item_exists():
    cs = ConnectionString(
        "HostName=my.host.name;SharedAccessKeyName=mykeyname;SharedAccessKey=Zm9vYmFy"
    )
    assert cs["HostName"] == "my.host.name"
    assert cs["SharedAccessKeyName"] == "mykeyname"
    assert cs["SharedAccessKey"] == "Zm9vYmFy"


def test___getitem__item_does_not_exist():
    with pytest.raises(KeyError):
        cs = ConnectionString(
            "HostName=my.host.name;SharedAccessKeyName=mykeyname;SharedAccessKey=Zm9vYmFy"
        )
        cs["SharedAccessSignature"]


def test_get_item_exists():
    cs = ConnectionString(
        "HostName=my.host.name;SharedAccessKeyName=mykeyname;SharedAccessKey=Zm9vYmFy"
    )
    assert cs.get("HostName") == "my.host.name"


def test_get_item_does_not_exist_w_default():
    cs = ConnectionString(
        "HostName=my.host.name;SharedAccessKeyName=mykeyname;SharedAccessKey=Zm9vYmFy"
    )
    assert cs.get("invalidkey", "defaultval") == "defaultval"


def test_get_item_does_not_exist_no_given_default():
    cs = ConnectionString(
        "HostName=my.host.name;SharedAccessKeyName=mykeyname;SharedAccessKey=Zm9vYmFy"
    )
    assert cs.get("invalidkey") is None
