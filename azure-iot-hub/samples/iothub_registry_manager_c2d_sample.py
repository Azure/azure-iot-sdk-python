# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import sys
import os
from azure.iot.hub import IoTHubRegistryManager

connection_str = os.getenv("IOTHUB_CONNECTION_STRING")
device_id = os.getenv("IOTHUB_DEVICE_ID")
send_message = "C2D message to be send to device"

try:
    # Create IoTHubRegistryManager
    registry_manager = IoTHubRegistryManager(connection_str)
    print("Conn String: {0}".format(connection_str))

    # Send Message To Device
    registry_manager.send_c2d_message(device_id, send_message)

except Exception as ex:
    print("Unexpected error {0}".format(ex))
except KeyboardInterrupt:
    print("iothub_statistics stopped")
