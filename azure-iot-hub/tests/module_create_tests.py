# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
from azure.iot.hub.protocol.models import AuthenticationMechanism
from .common_fixtures import (
    fake_device_id,
    fake_module_id,
    fake_managed_by,
    fake_status,
    fake_primary_key,
    fake_secondary_key,
    fake_primary_thumbprint,
    fake_secondary_thumbprint,
)


@pytest.mark.describe("IoTHubRegistryManager - .create_module_with_sas()")
class CreateModuleWithSymmetricKeyTests(object):

    testdata = [(fake_primary_key, None), (None, fake_secondary_key)]

    @pytest.mark.it("initializes module with device id, module id, managed_by status and sas auth")
    @pytest.mark.parametrize(
        "primary_key, secondary_key", testdata, ids=["Primary Key", "Secondary Key"]
    )
    def test_initializes_device_with_kwargs_for_sas(
        self,
        mock_service_operations,
        iothub_registry_manager,
        mock_module_constructor,
        primary_key,
        secondary_key,
    ):
        iothub_registry_manager.create_module_with_sas(
            device_id=fake_device_id,
            module_id=fake_module_id,
            managed_by=fake_managed_by,
            status=fake_status,
            primary_key=primary_key,
            secondary_key=secondary_key,
        )

        assert mock_module_constructor.call_count == 1

        assert mock_module_constructor.call_args[1]["module_id"] == fake_module_id
        assert mock_module_constructor.call_args[1]["managed_by"] == fake_managed_by
        assert mock_module_constructor.call_args[1]["device_id"] == fake_device_id
        assert mock_module_constructor.call_args[1]["status"] == fake_status
        assert isinstance(
            mock_module_constructor.call_args[1]["authentication"], AuthenticationMechanism
        )
        auth_mechanism = mock_module_constructor.call_args[1]["authentication"]
        assert auth_mechanism.type == "sas"
        assert auth_mechanism.x509_thumbprint is None
        sym_key = auth_mechanism.symmetric_key
        assert sym_key.primary_key == primary_key
        assert sym_key.secondary_key == secondary_key

    @pytest.mark.it(
        "calls method from service operations with device id, module id and previously constructed module"
    )
    @pytest.mark.parametrize(
        "primary_key, secondary_key", testdata, ids=["Primary Key", "Secondary Key"]
    )
    def test_calls_create_or_update_device_for_sas(
        self,
        mock_module_constructor,
        mock_service_operations,
        iothub_registry_manager,
        primary_key,
        secondary_key,
    ):
        iothub_registry_manager.create_module_with_sas(
            device_id=fake_device_id,
            status=fake_status,
            module_id=fake_module_id,
            managed_by=fake_managed_by,
            primary_key=primary_key,
            secondary_key=secondary_key,
        )

        assert mock_service_operations.create_or_update_module.call_count == 1
        assert mock_service_operations.create_or_update_module.call_args[0][0] == fake_device_id
        assert mock_service_operations.create_or_update_module.call_args[0][1] == fake_module_id
        assert (
            mock_service_operations.create_or_update_module.call_args[0][2]
            == mock_module_constructor.return_value
        )


@pytest.mark.describe("IoTHubRegistryManager - .create_module_with_x509()")
class CreateModuleWithX509Tests(object):

    testdata = [(fake_primary_thumbprint, None), (None, fake_secondary_thumbprint)]

    @pytest.mark.it(
        "initializes module with device id, module id, managed_by, status and X509 auth"
    )
    @pytest.mark.parametrize(
        "primary_thumbprint, secondary_thumbprint",
        testdata,
        ids=["Primary Thumbprint", "Secondary Thumbprint"],
    )
    def test_initializes_device_with_kwargs_for_x509(
        self,
        mock_service_operations,
        iothub_registry_manager,
        mock_module_constructor,
        primary_thumbprint,
        secondary_thumbprint,
    ):
        iothub_registry_manager.create_module_with_x509(
            device_id=fake_device_id,
            status=fake_status,
            module_id=fake_module_id,
            managed_by=fake_managed_by,
            primary_thumbprint=primary_thumbprint,
            secondary_thumbprint=secondary_thumbprint,
        )

        assert mock_module_constructor.call_count == 1
        assert mock_module_constructor.call_args[1]["module_id"] == fake_module_id
        assert mock_module_constructor.call_args[1]["managed_by"] == fake_managed_by
        assert mock_module_constructor.call_args[1]["device_id"] == fake_device_id
        assert mock_module_constructor.call_args[1]["status"] == fake_status
        assert isinstance(
            mock_module_constructor.call_args[1]["authentication"], AuthenticationMechanism
        )
        auth_mechanism = mock_module_constructor.call_args[1]["authentication"]
        assert auth_mechanism.type == "selfSigned"
        assert auth_mechanism.symmetric_key is None
        x509_thumbprint = auth_mechanism.x509_thumbprint
        assert x509_thumbprint.primary_thumbprint == primary_thumbprint
        assert x509_thumbprint.secondary_thumbprint == secondary_thumbprint

    @pytest.mark.it(
        "calls method from service operations with device id, module id and previously constructed module"
    )
    @pytest.mark.parametrize(
        "primary_thumbprint, secondary_thumbprint",
        testdata,
        ids=["Primary Thumbprint", "Secondary Thumbprint"],
    )
    def test_calls_create_or_update_device_for_x509(
        self,
        mock_module_constructor,
        mock_service_operations,
        iothub_registry_manager,
        primary_thumbprint,
        secondary_thumbprint,
    ):
        iothub_registry_manager.create_module_with_x509(
            device_id=fake_device_id,
            status=fake_status,
            module_id=fake_module_id,
            managed_by=fake_managed_by,
            primary_thumbprint=primary_thumbprint,
            secondary_thumbprint=secondary_thumbprint,
        )

        assert mock_service_operations.create_or_update_module.call_count == 1
        assert mock_service_operations.create_or_update_module.call_args[0][0] == fake_device_id
        assert mock_service_operations.create_or_update_module.call_args[0][1] == fake_module_id
        assert (
            mock_service_operations.create_or_update_module.call_args[0][2]
            == mock_module_constructor.return_value
        )


@pytest.mark.describe("IoTHubRegistryManager - .create_module_with_certificate_authority()")
class CreateModuleWithCATests(object):
    @pytest.mark.it("initializes module with device id, module id, managed_by, status and ca auth")
    def test_initializes_device_with_kwargs_for_certificate_authority(
        self, mock_module_constructor, mock_service_operations, iothub_registry_manager
    ):
        iothub_registry_manager.create_module_with_certificate_authority(
            device_id=fake_device_id,
            status=fake_status,
            module_id=fake_module_id,
            managed_by=fake_managed_by,
        )

        assert mock_module_constructor.call_count == 1
        assert mock_module_constructor.call_args[1]["module_id"] == fake_module_id
        assert mock_module_constructor.call_args[1]["managed_by"] == fake_managed_by
        assert mock_module_constructor.call_args[1]["device_id"] == fake_device_id
        assert mock_module_constructor.call_args[1]["status"] == fake_status
        assert isinstance(
            mock_module_constructor.call_args[1]["authentication"], AuthenticationMechanism
        )
        auth_mechanism = mock_module_constructor.call_args[1]["authentication"]
        assert auth_mechanism.type == "certificateAuthority"
        assert auth_mechanism.x509_thumbprint is None
        assert auth_mechanism.symmetric_key is None

    @pytest.mark.it(
        "calls method from service operations with device id, module id and previously constructed module"
    )
    def test_calls_create_or_update_device_for_certificate_authority(
        self, mock_module_constructor, mock_service_operations, iothub_registry_manager
    ):
        iothub_registry_manager.create_module_with_certificate_authority(
            device_id=fake_device_id,
            status=fake_status,
            module_id=fake_module_id,
            managed_by=fake_managed_by,
        )

        assert mock_service_operations.create_or_update_module.call_count == 1
        assert mock_service_operations.create_or_update_module.call_args[0][0] == fake_device_id
        assert mock_service_operations.create_or_update_module.call_args[0][1] == fake_module_id
        assert (
            mock_service_operations.create_or_update_module.call_args[0][2]
            == mock_module_constructor.return_value
        )
