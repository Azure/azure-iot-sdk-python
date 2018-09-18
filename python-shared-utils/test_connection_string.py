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
        cs = ConnectionString("HostName=myhub.azure-devices.net")

    @pytest.mark.xfail(raises=ValueError)
    def test_invalid_key(self):
        cs = ConnectionString("InvalidKey=myhub.azure-devices.net;SharedAccessKeyName=iothubowner;SharedAccessKey=N3QWnl1hC56JttVsO4s2qpi0BckBjpuK3TIlOnORi0M=")

    @pytest.mark.xfail(raises=ValueError)
    def test_duplicate_key(self):
        cs = ConnectionString("HostName=myhub.azure-devices.net;HostName=myhub.azure-devices.net;SharedAccessKey=iothubowner;SharedAccessKey=N3QWnl1hC56JttVsO4s2qpi0BckBjpuK3TIlOnORi0M=")

    def test_service_string(self):
        cs = ConnectionString("HostName=myhub.azure-devices.net;SharedAccessKeyName=iothubowner;SharedAccessKey=N3QWnl1hC56JttVsO4s2qpi0BckBjpuK3TIlOnORi0M=")

    def test_device_string(self):
        cs = ConnectionString("HostName=myhub.azure-devices.net;DeviceId=my-device;SharedAccessKey=N3QWnl1hC56JttVsO4s2qpi0BckBjpuK3TIlOnORi0M=")

    def test_device_string_with_gateway_hostname(self):
        cs = ConnectionString("HostName=myhub.azure-devices.net;DeviceId=my-device;SharedAccessKey=N3QWnl1hC56JttVsO4s2qpi0BckBjpuK3TIlOnORi0M=;GatewayHostName=mygateway")

    def test_module_string(self):
        cs = ConnectionString("HostName=myhub.azure-devices.net;DeviceId=my-device;ModuleId=my-module;SharedAccessKey=N3QWnl1hC56JttVsO4s2qpi0BckBjpuK3TIlOnORi0M=")

    def test_module_string_with_gateway_hostname(self):
        cs = ConnectionString("HostName=myhub.azure-devices.net;DeviceId=my-device;ModuleId=my-module;SharedAccessKey=N3QWnl1hC56JttVsO4s2qpi0BckBjpuK3TIlOnORi0M=;GatewayHostName=mygateway")

def test___repr__():
    string = "HostName=myhub.azure-devices.net;SharedAccessKeyName=iothubowner;SharedAccessKey=N3QWnl1hC56JttVsO4s2qpi0BckBjpuK3TIlOnORi0M="
    cs = ConnectionString(string)
    assert str(cs) == string

def test___getitem__item_exists():
    cs = ConnectionString("HostName=myhub.azure-devices.net;SharedAccessKeyName=iothubowner;SharedAccessKey=N3QWnl1hC56JttVsO4s2qpi0BckBjpuK3TIlOnORi0M=")
    assert cs["HostName"] == "myhub.azure-devices.net"
    assert cs["SharedAccessKeyName"] == "iothubowner"
    assert cs["SharedAccessKey"] == "N3QWnl1hC56JttVsO4s2qpi0BckBjpuK3TIlOnORi0M="

@pytest.mark.xfail(raises=KeyError)
def test___getitem__item_does_not_exist():
    cs = ConnectionString("HostName=myhub.azure-devices.net;SharedAccessKeyName=iothubowner;SharedAccessKey=N3QWnl1hC56JttVsO4s2qpi0BckBjpuK3TIlOnORi0M=")
    cs["SharedAccessSignature"]