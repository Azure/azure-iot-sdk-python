# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest


class SharedAuthenticationProviderInstantiationTests(object):
    @pytest.mark.it("Sets the hostname parameter as an instance attribute")
    def test_hostname(self, auth_provider, hostname):
        assert auth_provider.hostname == hostname

    @pytest.mark.it("Sets the device_id parameter as an instance attribute")
    def test_device_id(self, auth_provider, device_id):
        assert auth_provider.device_id == device_id

    @pytest.mark.it("Sets the module_id parameter as an instance attribute")
    def test_module_id(self, auth_provider, module_id):
        assert auth_provider.module_id == module_id


class SharedBaseRenewableAuthenticationProviderInstantiationTests(
    SharedAuthenticationProviderInstantiationTests
):
    # TODO: Complete this testclass after refactoring the class under test
    pass
