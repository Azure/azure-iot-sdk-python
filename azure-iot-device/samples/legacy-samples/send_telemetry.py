# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import os
import time
import uuid
from azure.iot.device import IoTHubDeviceClient, Message
from azure.iot.device import auth

# The connection string for a device should never be stored in code. For the sake of simplicity we're using an environment variable here.
conn_str = os.getenv("IOTHUB_DEVICE_CONNECTION_STRING")
# The client object is used to interact with your Azure IoT hub.
device_client = IoTHubDeviceClient.create_from_connection_string(conn_str)

# Connect the client.
device_client.connect()

# send 5 messages with a 1 second pause between each message
for i in range(1, 6):
    print("sending message #" + str(i))
    msg = Message("test wind speed " + str(i))
    msg.message_id = uuid.uuid4()
    msg.correlation_id = "correlation-1234"
    msg.custom_properties["tornado-warning"] = "yes"
    device_client.send_event(msg)
    time.sleep(1)

# send only string messages
for i in range(6, 11):
    print("sending message #" + str(i))
    device_client.send_event("test payload message " + str(i))
    time.sleep(1)


# finally, disconnect
device_client.disconnect()
