import pytest
from pytest_mock import mocker
import time
from sastoken import SasToken, SasTokenError

class TestCreateSasToken(object):

    def test_create_default_ttl(self):
        uri = "myhub.azure-devices.net"
        key_name = "iothubowner"
        key = "N3QWnl1hC56JttVsO4s2qpi0BckBjpuK3TIlOnORi0M="
        s = SasToken(uri, key_name, key)
        assert s._uri == uri
        assert s._key_name == key_name
        assert s._key == key
        assert s.ttl == 3600

    def test_create_custom_ttl(self):
        uri = "myhub.azure-devices.net"
        key_name = "iothubowner"
        key = "N3QWnl1hC56JttVsO4s2qpi0BckBjpuK3TIlOnORi0M="
        s = SasToken(uri, key_name, key, 9000)
        assert s._uri == uri
        assert s._key_name == key_name
        assert s._key == key
        assert s.ttl == 9000

    def test_uri_with_special_chars(self):
        uri = "my châteu.azure-devices.provisioning.net"
        key_name = "iothubowner"
        key = "N3QWnl1hC56JttVsO4s2qpi0BckBjpuK3TIlOnORi0M="
        s = SasToken(uri, key_name, key)

        expected_uri = "my+ch%C3%A2teu.azure-devices.provisioning.net"
        assert s._uri == expected_uri

    @pytest.mark.xfail(raises=SasTokenError)
    def test_key_not_base_64(self):
        uri = "myhub.azure-devices.net"
        key_name = "iothubowner"
        key = "this is not base64"
        s = SasToken(uri, key_name, key)


class TestsOnValidSasToken(object): 

    def test_refresh(self):
        #Move this setup block to fixtures when understood
        uri = "myhub.azure-devices.net"
        key_name = "iothubowner"
        key = "N3QWnl1hC56JttVsO4s2qpi0BckBjpuK3TIlOnORi0M="
        sastoken = SasToken(uri, key_name, key)

        #Actual test
        old_expiry = sastoken.expiry_time
        time.sleep(1)
        sastoken.refresh()
        new_expiry = sastoken.expiry_time
        assert new_expiry > old_expiry

    def test_refresh_time_mock(self):
        #To be implemented (need mock framework knowledge)
        pass

    def test___repr_(self):
        #To be implemented (need regex knowledge)
        pass

