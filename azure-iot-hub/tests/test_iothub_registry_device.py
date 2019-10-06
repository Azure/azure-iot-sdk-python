# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import pytest
from .device_create_tests import (
    CreateDeviceWithSymmetricKeyTests,
    CreateDeviceWithX509Tests,
    CreateDeviceWithCATests,
)
from .device_update_tests import (
    UpdateDeviceWithSymmetricKeyTests,
    UpdateDeviceWithX509Tests,
    UpdateDeviceWithCATests,
)

from .common_fixtures import fake_device_id, fake_etag


class DeviceMock(object):
    @pytest.fixture(scope="function")
    def mock_device_constructor(self, mocker):
        return mocker.patch("azure.iot.hub.iothub_registry_manager.Device")


@pytest.mark.describe("IotHub Registry Manager Device Create Tests")
class TestIotHubRegistryManagerDeviceCreate(
    DeviceMock,
    CreateDeviceWithSymmetricKeyTests,
    CreateDeviceWithX509Tests,
    CreateDeviceWithCATests,
):
    pass


@pytest.mark.describe("IotHub Registry Manager Device Update Tests")
class TestIotHubRegistryManagerDeviceUpdate(
    DeviceMock,
    UpdateDeviceWithSymmetricKeyTests,
    UpdateDeviceWithX509Tests,
    UpdateDeviceWithCATests,
):
    pass


@pytest.mark.describe("IoTHubRegistryManager -- .get_device()")
class TestGetDevice(object):
    @pytest.mark.it("gets device from service for provided device id")
    def test_get_device(self, mocker, mock_service_operations, iothub_registry_manager):
        iothub_registry_manager.get_device(fake_device_id)

        assert mock_service_operations.get_device.call_args == mocker.call(fake_device_id)


@pytest.mark.describe("IoTHubRegistryManager -- .get_device()")
class TestGetConfigOfDevice(object):
    @pytest.mark.it("gets configuration of device from service for provided device id")
    def test_get_config_of_device(self, mocker, mock_service_operations, iothub_registry_manager):
        iothub_registry_manager.get_configuration(fake_device_id)

        assert mock_service_operations.get_configuration.call_args == mocker.call(fake_device_id)


@pytest.mark.describe("IoTHubRegistryManager -- .delete_device()")
class TestDeleteDevice(object):
    @pytest.mark.it("deletes device for the provided device id")
    def test_delete_device(self, mocker, mock_service_operations, iothub_registry_manager):
        iothub_registry_manager.delete_device(fake_device_id)

        assert mock_service_operations.delete_device.call_args == mocker.call(fake_device_id, "*")

    @pytest.mark.it("deletes device with an etag for the provided device id and etag")
    def test_delete_device_with_etag(
        self, mocker, mock_service_operations, iothub_registry_manager
    ):
        iothub_registry_manager.delete_device(device_id=fake_device_id, etag=fake_etag)

        assert mock_service_operations.delete_device.call_args == mocker.call(
            fake_device_id, fake_etag
        )
