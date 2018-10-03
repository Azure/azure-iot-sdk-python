# -*- coding: utf-8 -*-

import pytest
import time
from sastoken import SasToken, SasTokenError


class TestCreateSasToken(object):
    def test_create_default_ttl(self):
        uri = "my.host.name"
        key_name = "mykeyname"
        key = "Zm9vYmFy"
        s = SasToken(uri, key, key_name)
        assert s._uri == uri
        assert s._key_name == key_name
        assert s._key == key
        assert s.ttl == 3600

    def test_create_custom_ttl(self):
        uri = "my.host.name"
        key_name = "mykeyname"
        key = "Zm9vYmFy"
        s = SasToken(uri, key, key_name, 9000)
        assert s._uri == uri
        assert s._key_name == key_name
        assert s._key == key
        assert s.ttl == 9000

    def test_uri_with_special_chars(self):
        uri = "my châteu.host.name"
        key_name = "mykeyname"
        key = "Zm9vYmFy"
        s = SasToken(uri, key, key_name)

        expected_uri = "my+ch%C3%A2teu.host.name"
        assert s._uri == expected_uri

    def test_key_not_base_64(self):
        with pytest.raises(SasTokenError):
            uri = "my.host.name"
            key_name = "mykeyname"
            key = "this is not base64"
            SasToken(uri, key, key_name)


class TestsOnValidSasToken(object):
    def test_refresh(self):
        # Move this setup block to fixtures when understood
        uri = "my.host.name"
        key_name = "mykeyname"
        key = "Zm9vYmFy"
        sastoken = SasToken(uri, key, key_name)

        # Actual test
        old_expiry = sastoken.expiry_time
        time.sleep(1)
        sastoken.refresh()
        new_expiry = sastoken.expiry_time
        assert new_expiry > old_expiry

    def test_refresh_time_mock(self):
        # To be implemented (need mock framework knowledge)
        pass

    def test___repr_(self):
        # To be implemented (need regex knowledge)
        pass
