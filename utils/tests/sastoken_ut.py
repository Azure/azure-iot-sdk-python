# -*- coding: utf-8 -*-
# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

import time
import unittest
import mock

from utils.sastoken import SasToken, SasTokenFactory, SasTokenError


class TestValidSasToken(unittest.TestCase):

    def setUp(self):
        uri = "test-uri.azure-devices-provisioning.net"
        key_name = "provisioningserviceowner"
        key = "dGVzdGluZyBhIHNhc3Rva2Vu"
        self.sastoken = SasToken(uri, key_name, key)

    def tearDown(self):
        self.sastoken.refresh()

    def test_str(self):
        str_rep = str(self.sastoken)
        b64_regex = "[^-A-Za-z0-9+/=]|=[^=]|={3,}$"
        sas_regex = "SharedAccessSignature sr={}&sig={}&se={}&skn={}".format(
            self.sastoken._uri, b64_regex, str(self.sastoken.expiry_time), 
            self.sastoken._key_name)
        self.assertRegexpMatches(str_rep, sas_regex)

    def test_refresh(self):
        old_expiry = self.sastoken.expiry_time
        time.sleep(1)
        self.sastoken.refresh()
        new_expiry = self.sastoken.expiry_time
        self.assertGreater(new_expiry, old_expiry)
    
    @mock.patch('serviceclient.sastoken.time')
    def test_refresh_accurately(self, mock_time):
        mock_time.time.return_value = 0
        self.sastoken.refresh(2423)
        new_expiry = self.sastoken.expiry_time
        self.assertEqual(2423, new_expiry)

    def test_set_expiry_fail(self):
        with self.assertRaises(AttributeError):
            self.sastoken.expiry_time = 12345


class TestAltInputSasToken(unittest.TestCase):

    def test_key_not_base64(self):
        uri = "test-uri.azure-devices-provisioning.net"
        key_name = "provisioningserviceowner"
        key = "this is not base64"

        with self.assertRaises(SasTokenError) as cm:
            self.sastoken = SasToken(uri, key_name, key)
        e = cm.exception
        self.assertIsInstance(e.cause, TypeError)

    def test_uri_with_special_chars(self):
        uri = "my châteu.azure-devices.provisioning.net"
        key_name = "provisioningserviceowner"
        key = "dGVzdGluZyBhIHNhc3Rva2Vu"
        self.sastoken = SasToken(uri, key_name, key)

        expected_uri = "my+ch%C3%A2teu.azure-devices.provisioning.net"
        self.assertEqual(self.sastoken._uri, expected_uri)


if __name__ == '__main__':
    unittest.main()
