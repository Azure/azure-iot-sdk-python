# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import os
import pytest
import logging
import uuid
from azure.iot.hub.iothub_configuration_manager import IoTHubConfigurationManager
from azure.iot.hub.models import Configuration, ConfigurationContent, ConfigurationMetrics

logging.basicConfig(level=logging.DEBUG)

iothub_connection_str = os.getenv("IOTHUB_CONNECTION_STRING")


@pytest.mark.describe("Create and test IoTHubConfigurationManager")
class TestConfigurationManager(object):
    @pytest.mark.it("Create IoTHubConfigurationManager and create, get and delete configuration")
    def test_iot_hub_configuration_manager(self):
        try:
            iothub_configuration = IoTHubConfigurationManager(iothub_connection_str)

            # Create configuration
            config_id = "e2e_test_config-" + str(uuid.uuid4())

            config = Configuration()
            config.id = config_id

            content = ConfigurationContent(
                device_content={
                    "properties.desired.chiller-water": {"temperature: 68, pressure:28"}
                }
            )
            config.content = content

            metrics = ConfigurationMetrics(
                queries={
                    "waterSettingPending": "SELECT deviceId FROM devices WHERE properties.reported.chillerWaterSettings.status='pending'"
                }
            )
            config.metrics = metrics

            # Create configuration
            new_config = iothub_configuration.create_configuration(config)

            # Verify result
            assert new_config.id == config_id

            # Get configuration
            get_config = iothub_configuration.get_configuration(config_id)

            # Verify result
            assert get_config.id == config_id

            # Get all configurations
            all_configurations = iothub_configuration.get_configurations()

            # Verify result
            assert get_config in all_configurations

            # Delete configuration
            iothub_configuration.delete_configuration(config_id)

            # Get all configurations
            all_configurations = iothub_configuration.get_configurations()

            # # Verify result
            assert get_config not in all_configurations

        except Exception as e:
            logging.exception(e)
