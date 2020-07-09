# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import sys
import os
from azure.iot.hub import IoTHubDigitalTwinManager


iothub_connection_str = os.getenv("IOTHUB_CONNECTION_STRING")
device_id = os.getenv("IOTHUB_DEVICE_ID")

try:
    # Create IoTHubDigitalTwinManager
    iothub_digital_twin_manager = IoTHubDigitalTwinManager(iothub_connection_str)

    # Get components
    components = iothub_digital_twin_manager.get_components(device_id)
    if components:
        print(components)
    else:
        print("No components found")

except Exception as ex:
    print("Unexpected error {0}".format(ex))
except KeyboardInterrupt:
    print("Sample stopped")
