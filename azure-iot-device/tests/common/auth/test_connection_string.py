# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
import logging
import six
from azure.iot.device.common.auth.connection_string import ConnectionString

logging.basicConfig(level=logging.DEBUG)


@pytest.mark.describe("ConnectionString")
class TestConnectionString(object):
    @pytest.mark.it("Instantiates from a given connection string")
    @pytest.mark.parametrize(
        "input_string",
        [
            pytest.param(
                "HostName=my.host.name;SharedAccessKeyName=mykeyname;SharedAccessKey=Zm9vYmFy",
                id="Service connection string",
            ),
            pytest.param(
                "HostName=my.host.name;DeviceId=my-device;SharedAccessKey=Zm9vYmFy",
                id="Device connection string",
            ),
            pytest.param(
                "HostName=my.host.name;DeviceId=my-device;SharedAccessKey=Zm9vYmFy;GatewayHostName=mygateway",
                id="Device connection string w/ gatewayhostname",
            ),
            pytest.param(
                "HostName=my.host.name;DeviceId=my-device;ModuleId=my-module;SharedAccessKey=Zm9vYmFy",
                id="Module connection string",
            ),
            pytest.param(
                "HostName=my.host.name;DeviceId=my-device;ModuleId=my-module;SharedAccessKey=Zm9vYmFy;GatewayHostName=mygateway",
                id="Module connection string w/ gatewayhostname",
            ),
        ],
    )
    def test_instantiates_correctly_from_string(self, input_string):
        cs = ConnectionString(input_string)
        assert isinstance(cs, ConnectionString)

    @pytest.mark.it("Raises ValueError on invalid string input during instantiation")
    @pytest.mark.parametrize(
        "input_string",
        [
            pytest.param("", id="Empty string"),
            pytest.param("garbage", id="Not a connection string"),
            pytest.param("HostName=my.host.name", id="Incomplete connection string"),
            pytest.param(
                "InvalidKey=my.host.name;SharedAccessKeyName=mykeyname;SharedAccessKey=Zm9vYmFy",
                id="Invalid key",
            ),
            pytest.param(
                "HostName=my.host.name;HostName=my.host.name;SharedAccessKey=mykeyname;SharedAccessKey=Zm9vYmFy",
                id="Duplicate key",
            ),
        ],
    )
    def test_raises_value_error_on_invalid_input(self, input_string):
        with pytest.raises(ValueError):
            ConnectionString(input_string)

    @pytest.mark.it("Raises TypeError on non-string input during instantiation")
    @pytest.mark.parametrize(
        "input_val",
        [
            pytest.param(2123, id="Integer"),
            pytest.param(23.098, id="Float"),
            pytest.param(
                b"bytes",
                id="Bytes",
                marks=pytest.mark.xfail(six.PY2, reason="Bytes are valid in Python 2.7"),
            ),
            pytest.param(object(), id="Complex object"),
            pytest.param(["a", "b"], id="List"),
            pytest.param({"a": "b"}, id="Dictionary"),
        ],
    )
    def test_raises_type_error_on_non_string_input(self, input_val):
        with pytest.raises(TypeError):
            ConnectionString(input_val)

    @pytest.mark.it("Uses the input connection string as a string representation")
    def test_string_representation_of_object_is_the_input_string(self):
        string = "HostName=my.host.name;SharedAccessKeyName=mykeyname;SharedAccessKey=Zm9vYmFy"
        cs = ConnectionString(string)
        assert str(cs) == string

    @pytest.mark.it("Supports indexing syntax to return the stored value for a given key")
    def test_indexing_key_returns_corresponding_value(self):
        cs = ConnectionString(
            "HostName=my.host.name;SharedAccessKeyName=mykeyname;SharedAccessKey=Zm9vYmFy"
        )
        assert cs["HostName"] == "my.host.name"
        assert cs["SharedAccessKeyName"] == "mykeyname"
        assert cs["SharedAccessKey"] == "Zm9vYmFy"

    @pytest.mark.it("Raises KeyError if indexing on a key not contained in the ConnectionString")
    def test_indexing_key_raises_key_error_if_key_not_in_string(self):
        with pytest.raises(KeyError):
            cs = ConnectionString(
                "HostName=my.host.name;SharedAccessKeyName=mykeyname;SharedAccessKey=Zm9vYmFy"
            )
            cs["SharedAccessSignature"]


@pytest.mark.describe("ConnectionString - .get()")
class TestConnectionStringGet(object):
    @pytest.mark.it("Returns the stored value for a given key")
    def test_calling_get_with_key_returns_corresponding_value(self):
        cs = ConnectionString(
            "HostName=my.host.name;SharedAccessKeyName=mykeyname;SharedAccessKey=Zm9vYmFy"
        )
        assert cs.get("HostName") == "my.host.name"

    @pytest.mark.it("Returns None if the given key is invalid")
    def test_calling_get_with_invalid_key_and_no_default_value_returns_none(self):
        cs = ConnectionString(
            "HostName=my.host.name;SharedAccessKeyName=mykeyname;SharedAccessKey=Zm9vYmFy"
        )
        assert cs.get("invalidkey") is None

    @pytest.mark.it("Returns an optionally provided default value if the given key is invalid")
    def test_calling_get_with_invalid_key_and_a_default_value_returns_default_value(self):
        cs = ConnectionString(
            "HostName=my.host.name;SharedAccessKeyName=mykeyname;SharedAccessKey=Zm9vYmFy"
        )
        assert cs.get("invalidkey", "defaultval") == "defaultval"
