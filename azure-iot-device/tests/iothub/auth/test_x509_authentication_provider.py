# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
from azure.iot.device.iothub.auth.x509_authentication_provider import X509AuthenticationProvider
from azure.iot.device.common.models.x509 import X509

hostname = "beauxbatons.academy-net"
device_id = "MyPensieve"
fake_x509_cert_value = "fantastic_beasts"
fake_x509_cert_key = "where_to_find_them"
fake_pass_phrase = "alohomora"


def x509():
    return X509(fake_x509_cert_value, fake_x509_cert_key, fake_pass_phrase)


@pytest.mark.describe("X509AuthenticationProvider")
class TestX509AuthenticationProvider(object):
    @pytest.mark.it("Instantiates correctly with hostname")
    def test_instantiates_correctly_with_hostname(self):
        x509_cert_object = x509()
        x509_auth_provider = X509AuthenticationProvider(
            hostname=hostname, device_id=device_id, x509=x509_cert_object
        )
        assert x509_auth_provider.hostname == hostname

    @pytest.mark.it("Instantiates correctly with device_id")
    def test_instantiates_correctly_with_device_id(self):
        x509_cert_object = x509()
        x509_auth_provider = X509AuthenticationProvider(
            hostname=hostname, device_id=device_id, x509=x509_cert_object
        )
        assert x509_auth_provider.device_id == device_id

    @pytest.mark.it("Getter correctly retrieves the x509 certificate object")
    def test_get_certificate(self):
        x509_cert_object = x509()
        x509_auth_provider = X509AuthenticationProvider(
            hostname=hostname, device_id=device_id, x509=x509_cert_object
        )
        assert x509_auth_provider.get_x509_certificate()
