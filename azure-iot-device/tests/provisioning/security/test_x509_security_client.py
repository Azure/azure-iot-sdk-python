# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
import logging
from azure.iot.device.provisioning.security.x509_security_client import X509SecurityClient
from azure.iot.device.common.models.x509 import X509

logging.basicConfig(level=logging.DEBUG)

fake_provisioning_host = "beauxbatons.academy-net"
fake_registration_id = "MyPensieve"
module_id = "Divination"
fake_id_scope = "Enchanted0000Ceiling7898"
signature = "IsolemnlySwearThatIamuUptoNogood"
expiry = "1539043658"
fake_x509_cert_value = "fantastic_beasts"
fake_x509_cert_key = "where_to_find_them"
fake_pass_phrase = "alohomora"


def x509():
    return X509(fake_x509_cert_value, fake_x509_cert_key, fake_pass_phrase)


@pytest.mark.describe("X509SecurityClient")
class TestX509SecurityClient(object):
    @pytest.mark.it("Properties have getters")
    def test_properties_are_gettable_after_instantiation_security_client(self):
        x509_cert = x509()
        security_client = X509SecurityClient(
            fake_provisioning_host, fake_registration_id, fake_id_scope, x509_cert
        )
        assert security_client.provisioning_host == fake_provisioning_host
        assert security_client.id_scope == fake_id_scope
        assert security_client.registration_id == fake_registration_id
        assert security_client.get_x509_certificate() == x509_cert

    @pytest.mark.it("Properties do not have setter")
    def test_properties_are_not_settable_after_instantiation_security_client(self):
        security_client = X509SecurityClient(
            fake_provisioning_host, fake_registration_id, fake_id_scope, x509()
        )
        with pytest.raises(AttributeError, match="can't set attribute"):
            security_client.registration_id = "MyNimbus2000"
            security_client.id_scope = "WhompingWillow"
            security_client.provisioning_host = "hogwarts.com"
