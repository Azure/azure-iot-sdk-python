# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import os
from azure.iot.device import ProvisioningDeviceClient
from azure.iot.device import IoTHubDeviceClient, Message
import uuid
import time


class Wizard(object):
    def __init__(self, first_name, last_name, dict_of_stuff):
        self.first_name = first_name
        self.last_name = last_name
        self.props = dict_of_stuff


provisioning_host = os.getenv("PROVISIONING_HOST")
id_scope = os.getenv("PROVISIONING_IDSCOPE")
registration_id = os.getenv("PROVISIONING_REGISTRATION_ID")
symmetric_key = os.getenv("PROVISIONING_SYMMETRIC_KEY")

provisioning_device_client = ProvisioningDeviceClient.create_from_symmetric_key(
    provisioning_host=provisioning_host,
    registration_id=registration_id,
    id_scope=id_scope,
    symmetric_key=symmetric_key,
)

properties = {"House": "Gryffindor", "Muggle-Born": "False"}
wizard_a = Wizard("Harry", "Potter", properties)

provisioning_device_client.provisioning_payload = wizard_a
registration_result = provisioning_device_client.register()
# The result can be directly printed to view the important details.
print(registration_result)

# Individual attributes can be seen as well
print("The status was :-")
print(registration_result.status)
print("The etag is :-")
print(registration_result.registration_state.etag)


if registration_result.status == "assigned":
    print("Will send telemetry from the provisioned device")
    # Create device client from the above result
    device_client = IoTHubDeviceClient.create_from_symmetric_key(
        symmetric_key=symmetric_key,
        hostname=registration_result.registration_state.assigned_hub,
        device_id=registration_result.registration_state.device_id,
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
        device_client.send_message(msg)
        time.sleep(1)

        # finally, disconnect
        device_client.disconnect()
else:
    print("Can not send telemetry from the provisioned device")
