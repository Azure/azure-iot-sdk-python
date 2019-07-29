# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import os
from azure.iot.device import IoTHubDeviceClient


conn_str = os.getenv("IOTHUB_DEVICE_CONNECTION_STRING")
device_client = IoTHubDeviceClient.create_from_connection_string(conn_str)

# connect the client.
device_client.connect()

# get the twin
twin = device_client.get_twin()
print("Reported temperature is {}".format(twin["reported"]["temperature"]))

# Finally, disconnect
device_client.disconnect()
