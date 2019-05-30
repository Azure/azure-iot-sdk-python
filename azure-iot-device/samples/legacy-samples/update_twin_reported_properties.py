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

# logging.basicConfig(level=logging.DEBUG)

conn_str = os.getenv("IOTHUB_DEVICE_CONNECTION_STRING")
auth_provider = auth.from_connection_string(conn_str)
device_client = IoTHubDeviceClient.from_authentication_provider(auth_provider, "mqtt")

# connect the client.
device_client.connect()

# get the twin
reported_properties = {"temperature": random.randint(320, 800) / 10}
print("Setting reported temperature to {}".format(reported_properties["temperature"]))
device_client.patch_twin_reported_properties(reported_properties)

# Finally, disconnect
device_client.disconnect()
