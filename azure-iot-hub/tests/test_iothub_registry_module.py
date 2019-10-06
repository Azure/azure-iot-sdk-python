# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import pytest
from .module_create_tests import (
    CreateModuleWithSymmetricKeyTests,
    CreateModuleWithX509Tests,
    CreateModuleWithCATests,
)
from .module_update_tests import (
    UpdateModuleWithSymmetricKeyTests,
    UpdateModuleWithX509Tests,
    UpdateModuleWithCATests,
)

from .common_fixtures import fake_device_id, fake_module_id, fake_etag


class ModuleMock(object):
    @pytest.fixture(scope="function")
    def mock_module_constructor(self, mocker):
        return mocker.patch("azure.iot.hub.iothub_registry_manager.Module")


@pytest.mark.describe("IotHub Registry Manager Module Create Tests")
class TestIotHubRegistryManagerModuleCreate(
    ModuleMock,
    CreateModuleWithSymmetricKeyTests,
    CreateModuleWithX509Tests,
    CreateModuleWithCATests,
):
    pass


@pytest.mark.describe("IotHub Registry Manager Module Update Tests")
class TestIotHubRegistryManagerModuleUpdate(
    ModuleMock,
    UpdateModuleWithSymmetricKeyTests,
    UpdateModuleWithX509Tests,
    UpdateModuleWithCATests,
):
    pass


@pytest.mark.describe("IoTHubRegistryManager -- .get_module()")
class TestGetModule(object):
    @pytest.mark.it("gets module from service for provided device id and module id")
    def test_get_module(self, mocker, mock_service_operations, iothub_registry_manager):
        iothub_registry_manager.get_module(fake_device_id, fake_module_id)

        assert mock_service_operations.get_module.call_args == mocker.call(
            fake_device_id, fake_module_id
        )


@pytest.mark.describe("IoTHubRegistryManager -- .delete_module()")
class TestDeleteModule(object):
    @pytest.mark.it("deletes module for the provided device id")
    def test_delete_module(self, mocker, mock_service_operations, iothub_registry_manager):
        iothub_registry_manager.delete_module(fake_device_id)

        assert mock_service_operations.delete_module.call_args == mocker.call(fake_device_id, "*")

    @pytest.mark.it("deletes module with an etag for the provided device id and etag")
    def test_delete_module_with_etag(
        self, mocker, mock_service_operations, iothub_registry_manager
    ):
        iothub_registry_manager.delete_module(device_id=fake_device_id, etag=fake_etag)

        assert mock_service_operations.delete_module.call_args == mocker.call(
            fake_device_id, fake_etag
        )
