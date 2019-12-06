# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import os
from azure.iot.device import ProvisioningDeviceClient, X509
import time
from azure.iot.device import IoTHubDeviceClient, Message
import uuid


provisioning_host = os.getenv("PROVISIONING_HOST")
id_scope = os.getenv("PROVISIONING_IDSCOPE")
registration_id = os.getenv("DPS_X509_REGISTRATION_ID")

x509 = X509(
    cert_file=os.getenv("X509_CERT_FILE"),
    key_file=os.getenv("X509_KEY_FILE"),
    pass_phrase=os.getenv("PASS_PHRASE"),
)

provisioning_device_client = ProvisioningDeviceClient.create_from_x509_certificate(
    provisioning_host=provisioning_host,
    registration_id=registration_id,
    id_scope=id_scope,
    x509=x509,
)

registration_result = provisioning_device_client.register()

# The result can be directly printed to view the important details.
print(registration_result)

if registration_result.status == "assigned":
    print("Will send telemetry from the provisioned device")
    # Create device client from the above result
    device_client = IoTHubDeviceClient.create_from_registration_result_and_x509(
        registration_result, x509=x509
    )

    # Connect the client.
    device_client.connect()

    for i in range(1, 6):
        print("sending message #" + str(i))
        device_client.send_message("test payload message " + str(i))
        time.sleep(1)

    for i in range(6, 11):
        print("sending message #" + str(i))
        msg = Message("test wind speed " + str(i))
        msg.message_id = uuid.uuid4()
        msg.custom_properties["tornado-warning"] = "yes"
        device_client.send_message(msg)
        time.sleep(1)

    # finally, disconnect

else:
    print("Can not send telemetry from the provisioned device")
