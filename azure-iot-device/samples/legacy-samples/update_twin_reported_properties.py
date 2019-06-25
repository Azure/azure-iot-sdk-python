# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import os
import logging
import random
from azure.iot.device import IoTHubDeviceClient
from azure.iot.device import auth

logging.basicConfig(level=logging.ERROR)

conn_str = os.getenv("IOTHUB_DEVICE_CONNECTION_STRING")
device_client = IoTHubDeviceClient.create_from_connection_string(conn_str)

# connect the client.
device_client.connect()

# send new reported properties
reported_properties = {"temperature": random.randint(320, 800) / 10}
print("Setting reported temperature to {}".format(reported_properties["temperature"]))
device_client.patch_twin_reported_properties(reported_properties)

# Finally, disconnect
device_client.disconnect()
