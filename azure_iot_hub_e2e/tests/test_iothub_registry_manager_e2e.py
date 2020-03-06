# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import os
import pytest
import logging
import uuid
from azure.iot.hub.iothub_registry_manager import IoTHubRegistryManager

logging.basicConfig(level=logging.DEBUG)

iothub_connection_str = os.getenv("IOTHUB_CONNECTION_STRING")


@pytest.mark.describe("Create and test IoTHubRegistryManager")
class TestRegistryManager(object):
    @pytest.mark.it(
        "Create IoTHubRegistryManager using SAS authentication and create, get and delete device"
    )
    def test_iot_hub_registry_manager_sas(self):
        device_id = "e2e-iot-hub-registry-manager-sas-" + str(uuid.uuid4())

        try:
            iothub_registry_manager = IoTHubRegistryManager(iothub_connection_str)

            # Create a device
            primary_key = "aaabbbcccdddeeefffggghhhiiijjjkkklllmmmnnnoo"
            secondary_key = "111222333444555666777888999000aaabbbcccdddee"
            device_state = "enabled"
            new_device = iothub_registry_manager.create_device_with_sas(
                device_id, primary_key, secondary_key, device_state
            )

            # Verify result
            assert new_device.device_id == device_id
            assert new_device.authentication.type == "sas"
            assert new_device.authentication.symmetric_key.primary_key == primary_key
            assert new_device.authentication.symmetric_key.secondary_key == secondary_key
            assert new_device.status == device_state

            # Delete device
            iothub_registry_manager.delete_device(device_id)

        except Exception as e:
            logging.exception(e)

    @pytest.mark.it("Create, get, update and delete device")
    @pytest.mark.describe("Create and test IoTHubRegistryManager device CRUD")
    def test_iot_hub_registry_manager_sas_crud(self):
        device_id = "e2e-iot-hub-registry-manager-sas-" + str(uuid.uuid4())

        try:
            iothub_registry_manager = IoTHubRegistryManager(iothub_connection_str)

            # Create a device
            primary_key = "aaabbbcccdddeeefffggghhhiiijjjkkklllmmmnnnoo"
            secondary_key = "111222333444555666777888999000aaabbbcccdddee"
            device_state = "enabled"
            new_device = iothub_registry_manager.create_device_with_sas(
                device_id, primary_key, secondary_key, device_state
            )

            # Verify result
            assert new_device.device_id == device_id
            assert new_device.authentication.type == "sas"
            assert new_device.authentication.symmetric_key.primary_key == primary_key
            assert new_device.authentication.symmetric_key.secondary_key == secondary_key
            assert new_device.status == device_state

            # Update device
            updated_status = "disabled"
            updated_device = iothub_registry_manager.update_device_with_sas(
                device_id, new_device.etag, primary_key, secondary_key, updated_status
            )

            # Verify result
            assert updated_device.status == updated_status

            # Delete device
            iothub_registry_manager.delete_device(device_id)

        except Exception as e:
            logging.exception(e)

    @pytest.mark.it("Create, get, update and delete module")
    @pytest.mark.describe("Create and test IoTHubRegistryManager module CRUD")
    def test_iot_hub_registry_manager_sas_module_crud(self):
        device_id = "e2e-iot-hub-registry-manager-sas-" + str(uuid.uuid4())
        module_id = "e2e-iot-hub-registry-manager-sas-module-" + str(uuid.uuid4())

        try:
            iothub_registry_manager = IoTHubRegistryManager(iothub_connection_str)

            # Create a device
            primary_key = "aaabbbcccdddeeefffggghhhiiijjjkkklllmmmnnnoo"
            secondary_key = "111222333444555666777888999000aaabbbcccdddee"
            device_state = "enabled"
            new_device = iothub_registry_manager.create_device_with_sas(
                device_id, primary_key, secondary_key, device_state
            )

            # Create module
            module_primary_key = "hhhiiijjjkkklllmmmnnnooaaabbbcccdddeeefffggg"
            module_secondary_key = "888999000aaabbbcccdddee111222333444555666777"
            managed_by = device_id
            new_module = iothub_registry_manager.create_module_with_sas(
                device_id, module_id, managed_by, module_primary_key, module_secondary_key
            )

            # Verify result
            assert new_device.device_id == device_id
            assert new_device.authentication.symmetric_key.primary_key == primary_key
            assert new_device.authentication.symmetric_key.secondary_key == secondary_key
            assert new_device.status == device_state

            assert new_module.module_id == module_id
            assert new_module.managed_by == device_id
            assert new_module.authentication.type == "sas"
            assert new_module.authentication.symmetric_key.primary_key == module_primary_key
            assert new_module.authentication.symmetric_key.secondary_key == module_secondary_key

            # Get modules
            one_module = iothub_registry_manager.get_modules(device_id)
            assert len(one_module) == 1

            # Update module
            update_module_primary_key = "jjjkkklllmmmnnnooaaahhhiiibbbcccdddeeefffggg"
            update_module_secondary_key = "000aaabbbcccdddee888999111222333444555666777"
            updated_module = iothub_registry_manager.update_module_with_sas(
                device_id,
                module_id,
                managed_by,
                new_module.etag,
                update_module_primary_key,
                update_module_secondary_key,
            )

            # Verify result
            assert (
                updated_module.authentication.symmetric_key.primary_key == update_module_primary_key
            )
            assert (
                updated_module.authentication.symmetric_key.secondary_key
                == update_module_secondary_key
            )

            # Delete module
            iothub_registry_manager.delete_module(device_id, module_id)

            # Verify result
            no_module = iothub_registry_manager.get_modules(device_id)
            assert len(no_module) == 0

            # Delete device
            iothub_registry_manager.delete_device(device_id)

        except Exception as e:
            logging.exception(e)
