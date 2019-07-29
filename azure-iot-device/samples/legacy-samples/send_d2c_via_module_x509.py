# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import os
import time
import uuid
from azure.iot.device import IoTHubModuleClient, Message, X509

hostname = os.getenv("HOSTNAME")

# The device having a certain module that has been created on the portal
# using X509 CA signing or Self signing capabilities
# The <device_id>\<module_id> should be the common name of the certificate

device_id = os.getenv("DEVICE_ID")
module_id = os.getenv("MODULE_ID")

x509 = X509(
    cert_file=os.getenv("X509_CERT_FILE"),
    key_file=os.getenv("X509_KEY_FILE"),
    pass_phrase=os.getenv("PASS_PHRASE"),
)

module_client = IoTHubModuleClient.create_from_x509_certificate(
    hostname=hostname, x509=x509, device_id=device_id, module_id=module_id
)

module_client.connect()


# send 5 messages with a 1 second pause between each message
for i in range(1, 6):
    print("sending message #" + str(i))
    msg = Message("test wind speed " + str(i))
    msg.message_id = uuid.uuid4()
    msg.correlation_id = "correlation-1234"
    msg.custom_properties["tornado-warning"] = "yes"
    module_client.send_d2c_message(msg)
    time.sleep(1)

# send only string messages
for i in range(6, 11):
    print("sending message #" + str(i))
    module_client.send_d2c_message("test payload message " + str(i))
    time.sleep(1)


# finally, disconnect
module_client.disconnect()
