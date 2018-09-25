import pytest
from connection_string import ConnectionString


class TestConnectionStringInput(object):
    
    @pytest.mark.xfail(raises=ValueError)
    def test_empty_input(self):
        cs = ConnectionString("")

    @pytest.mark.xfail(raises=ValueError)
    def test_garbage_input(self):
        cs = ConnectionString("garbage")

    @pytest.mark.xfail(raises=ValueError)
    def test_incomplete_input(self):
        cs = ConnectionString("HostName=my.host.name")

    @pytest.mark.xfail(raises=ValueError)
    def test_invalid_key(self):
        cs = ConnectionString("InvalidKey=my.host.name;SharedAccessKeyName=mykeyname;SharedAccessKey=Zm9vYmFy")

    @pytest.mark.xfail(raises=ValueError)
    def test_duplicate_key(self):
        cs = ConnectionString("HostName=my.host.name;HostName=my.host.name;SharedAccessKey=mykeyname;SharedAccessKey=Zm9vYmFy")

    def test_service_string(self):
        cs = ConnectionString("HostName=my.host.name;SharedAccessKeyName=mykeyname;SharedAccessKey=Zm9vYmFy")

    def test_device_string(self):
        cs = ConnectionString("HostName=my.host.name;DeviceId=my-device;SharedAccessKey=Zm9vYmFy")

    def test_device_string_with_gateway_hostname(self):
        cs = ConnectionString("HostName=my.host.name;DeviceId=my-device;SharedAccessKey=Zm9vYmFy;GatewayHostName=mygateway")

    def test_module_string(self):
        cs = ConnectionString("HostName=my.host.name;DeviceId=my-device;ModuleId=my-module;SharedAccessKey=Zm9vYmFy")

    def test_module_string_with_gateway_hostname(self):
        cs = ConnectionString("HostName=my.host.name;DeviceId=my-device;ModuleId=my-module;SharedAccessKey=Zm9vYmFy;GatewayHostName=mygateway")

def test___repr__():
    string = "HostName=my.host.name;SharedAccessKeyName=mykeyname;SharedAccessKey=Zm9vYmFy"
    cs = ConnectionString(string)
    assert str(cs) == string

def test___getitem__item_exists():
    cs = ConnectionString("HostName=my.host.name;SharedAccessKeyName=mykeyname;SharedAccessKey=Zm9vYmFy")
    assert cs["HostName"] == "my.host.name"
    assert cs["SharedAccessKeyName"] == "mykeyname"
    assert cs["SharedAccessKey"] == "Zm9vYmFy"

@pytest.mark.xfail(raises=KeyError)
def test___getitem__item_does_not_exist():
    cs = ConnectionString("HostName=my.host.name;SharedAccessKeyName=mykeyname;SharedAccessKey=Zm9vYmFy")
    cs["SharedAccessSignature"]