# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import os
import time
import uuid
from azure.iot.device import IoTHubDeviceClient, Message, X509

# The connection string for a device should never be stored in code.
# For the sake of simplicity we are creating the X509 connection string
# containing Hostname and Device Id in the following format:
# "HostName=<iothub_host_name>;DeviceId=<device_id>;x509=true"

hostname = os.getenv("HOSTNAME")

# The device that has been created on the portal using X509 CA signing or Self signing capabilities
device_id = os.getenv("DEVICE_ID")

x509 = X509(
    cert_file=os.getenv("X509_CERT_FILE"),
    key_file=os.getenv("X509_KEY_FILE"),
    pass_phrase=os.getenv("PASS_PHRASE"),
)

# The client object is used to interact with your Azure IoT hub.
device_client = IoTHubDeviceClient.create_from_x509_certificate(
    hostname=hostname, device_id=device_id, x509=x509
)

# Connect the client.
device_client.connect()

# send 5 messages with a 1 second pause between each message
for i in range(1, 6):
    print("sending message #" + str(i))
    msg = Message("test wind speed " + str(i))
    msg.message_id = uuid.uuid4()
    msg.correlation_id = "correlation-1234"
    msg.custom_properties["tornado-warning"] = "yes"
    device_client.send_d2c_message(msg)
    time.sleep(1)

# send only string messages
for i in range(6, 11):
    print("sending message #" + str(i))
    device_client.send_d2c_message("test payload message " + str(i))
    time.sleep(1)


# finally, disconnect
device_client.disconnect()
