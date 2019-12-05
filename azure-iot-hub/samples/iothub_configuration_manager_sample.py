# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import sys
import os
from azure.iot.hub import IoTHubConfigurationManager
from azure.iot.hub.protocol.models import Configuration, ConfigurationContent, ConfigurationMetrics


iothub_connection_str = os.getenv("IOTHUB_CONNECTION_STRING")


def print_configuration(title, config):
    print()
    print(title)
    print(  "Configuration:")
    print("    {}".format(config))
    print(  "Configuration - content:")
    print("    {}".format(config.content))
    print(  "Configuration - metrics:")
    print("    {}".format(config.metrics))


def create_configuration(config_id):
    config = Configuration()
    config.id = config_id

    content = ConfigurationContent(
        device_content={"properties.desired.chiller-water": {"temperature: 68, pressure:28"}},
    )
    config.content = content

    metrics = ConfigurationMetrics(
        queries={"waterSettingPending": "SELECT deviceId FROM devices WHERE properties.reported.chillerWaterSettings.status=\'pending\'"}
    )
    config.metrics = metrics

    return config


try:
    # Create IoTHubConfigurationManager
    iothub_configuration = IoTHubConfigurationManager(iothub_connection_str)

    # Create configuration
    config_id = "sample_config"
    sample_configuration = create_configuration(config_id)
    print_configuration("Sample configuration", sample_configuration)

    created_config = iothub_configuration.create_configuration(sample_configuration)
    print_configuration("Created configuration", created_config)

    get_config = iothub_configuration.get_configuration(config_id)
    print_configuration("Get configuration", get_config)

    iothub_configuration.delete_configuration(config_id)

    # Get all configurations
    configurations = iothub_configuration.get_configurations()
    if (configurations):
        print_configuration("Get all configurations", configurations[0])
    else:
        print("No configuration found")


except Exception as ex:
    print("Unexpected error {0}".format(ex))
except KeyboardInterrupt:
    print("iothub_registry_manager_sample stopped")
