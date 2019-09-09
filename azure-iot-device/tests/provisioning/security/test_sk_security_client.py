# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
import logging
from azure.iot.device.provisioning.security.sk_security_client import SymmetricKeySecurityClient

logging.basicConfig(level=logging.DEBUG)

fake_symmetric_key = "Zm9vYmFy"
key_name = "registration"
fake_provisioning_host = "beauxbatons.academy-net"
fake_registration_id = "MyPensieve"
module_id = "Divination"
fake_id_scope = "Enchanted0000Ceiling7898"
signature = "IsolemnlySwearThatIamuUptoNogood"
expiry = "1539043658"


@pytest.mark.describe("SymmetricKeySecurityClient")
class TestSymmetricKeySecurityClient(object):
    @pytest.mark.it("Properties have getters")
    def test_properties_are_gettable_after_instantiation_security_client(self):
        security_client = SymmetricKeySecurityClient(
            fake_provisioning_host, fake_registration_id, fake_id_scope, fake_symmetric_key
        )
        assert security_client.provisioning_host == fake_provisioning_host
        assert security_client.id_scope == fake_id_scope
        assert security_client.registration_id == fake_registration_id

    @pytest.mark.it("Properties do not have setter")
    def test_properties_are_not_settable_after_instantiation_security_client(self):
        security_client = SymmetricKeySecurityClient(
            fake_provisioning_host, fake_registration_id, fake_id_scope, fake_symmetric_key
        )
        with pytest.raises(AttributeError, match="can't set attribute"):
            security_client.registration_id = "MyNimbus2000"
            security_client.id_scope = "WhompingWillow"
            security_client.provisioning_host = "hogwarts.com"

    @pytest.mark.it("Can create sas token")
    def test_create_sas(self):
        security_client = SymmetricKeySecurityClient(
            fake_provisioning_host, fake_registration_id, fake_id_scope, fake_symmetric_key
        )
        sas_value = security_client.get_current_sas_token()
        assert key_name in sas_value
        assert fake_registration_id in sas_value
        assert fake_id_scope in sas_value
