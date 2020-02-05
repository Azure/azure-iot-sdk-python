# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import sys
import os
from azure.iot.hub import IoTHubRegistryManager

connection_str = os.getenv("IOTHUB_CONNECTION_STRING")

try:
    # Create IoTHubRegistryManager
    registry_manager = IoTHubRegistryManager(connection_str)

    print("Conn String: {0}".format(connection_str))

    # GetStatistics
    service_statistics = registry_manager.get_service_statistics()
    print("Service Statistics:")
    print("Total device count                       : {0}".format(service_statistics))
    print("")

    registry_statistics = registry_manager.get_device_registry_statistics()
    print("Device Registry Statistics:")
    print("Total device count                       : {0}".format(registry_statistics))
    print("")

except Exception as ex:
    print("Unexpected error {0}".format(ex))
except KeyboardInterrupt:
    print("iothub_statistics stopped")
