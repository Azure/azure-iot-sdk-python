# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

import pytest
from azure.iot.common.connection_string import ConnectionString


class TestConnectionString(object):
    @pytest.mark.parametrize(
        "input_string",
        [
            pytest.param(
                "HostName=my.host.name;SharedAccessKeyName=mykeyname;SharedAccessKey=Zm9vYmFy",
                id="service string",
            ),
            pytest.param(
                "HostName=my.host.name;DeviceId=my-device;SharedAccessKey=Zm9vYmFy",
                id="device string",
            ),
            pytest.param(
                "HostName=my.host.name;DeviceId=my-device;SharedAccessKey=Zm9vYmFy;GatewayHostName=mygateway",
                id="device string with gatewayhostname",
            ),
            pytest.param(
                "HostName=my.host.name;DeviceId=my-device;ModuleId=my-module;SharedAccessKey=Zm9vYmFy",
                id="module string",
            ),
            pytest.param(
                "HostName=my.host.name;DeviceId=my-device;ModuleId=my-module;SharedAccessKey=Zm9vYmFy;GatewayHostName=mygateway",
                id="module string with gatewayhostname",
            ),
        ],
    )
    def test_instantiates_correctly_from_string(self, input_string):
        cs = ConnectionString(input_string)
        assert isinstance(cs, ConnectionString)

    @pytest.mark.parametrize(
        "input_string",
        [
            pytest.param("", id="empty string"),
            pytest.param("garbage", id="garbage"),
            pytest.param("HostName=my.host.name", id="incomplete connection string"),
            pytest.param(
                "InvalidKey=my.host.name;SharedAccessKeyName=mykeyname;SharedAccessKey=Zm9vYmFy",
                id="invalid key",
            ),
            pytest.param(
                "HostName=my.host.name;HostName=my.host.name;SharedAccessKey=mykeyname;SharedAccessKey=Zm9vYmFy",
                id="duplicate key",
            ),
        ],
    )
    def test_raises_value_error_on_bad_input(self, input_string):
        with pytest.raises(ValueError):
            ConnectionString(input_string)

    def test_string_representation_of_object_is_the_input_string(self):
        string = "HostName=my.host.name;SharedAccessKeyName=mykeyname;SharedAccessKey=Zm9vYmFy"
        cs = ConnectionString(string)
        assert str(cs) == string

    def test_indexing_key_returns_corresponding_value(self):
        cs = ConnectionString(
            "HostName=my.host.name;SharedAccessKeyName=mykeyname;SharedAccessKey=Zm9vYmFy"
        )
        assert cs["HostName"] == "my.host.name"
        assert cs["SharedAccessKeyName"] == "mykeyname"
        assert cs["SharedAccessKey"] == "Zm9vYmFy"

    def test_indexing_key_raises_key_error_if_key_not_in_string(self):
        with pytest.raises(KeyError):
            cs = ConnectionString(
                "HostName=my.host.name;SharedAccessKeyName=mykeyname;SharedAccessKey=Zm9vYmFy"
            )
            cs["SharedAccessSignature"]

    def test_calling_get_with_key_returns_corresponding_value(self):
        cs = ConnectionString(
            "HostName=my.host.name;SharedAccessKeyName=mykeyname;SharedAccessKey=Zm9vYmFy"
        )
        assert cs.get("HostName") == "my.host.name"

    def test_calling_get_with_invalid_key_and_a_default_value_returns_default_value(self):
        cs = ConnectionString(
            "HostName=my.host.name;SharedAccessKeyName=mykeyname;SharedAccessKey=Zm9vYmFy"
        )
        assert cs.get("invalidkey", "defaultval") == "defaultval"

    def test_calling_get_with_invalid_key_and_no_default_value_returns_none(self):
        cs = ConnectionString(
            "HostName=my.host.name;SharedAccessKeyName=mykeyname;SharedAccessKey=Zm9vYmFy"
        )
        assert cs.get("invalidkey") is None
