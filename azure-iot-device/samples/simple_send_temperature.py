# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import asyncio
from azure.iot.device.aio import ProvisioningDeviceClient
import os
from azure.iot.device.aio import IoTHubDeviceClient
from azure.iot.device import Message
import uuid
import json
import random

# ensure environment variables are set for your device and IoT Central application credentials
provisioning_host = os.getenv("PROVISIONING_HOST")
id_scope = os.getenv("ID_SCOPE")
registration_id = os.getenv("DEVICE_ID")
symmetric_key = os.getenv("DEVICE_KEY")

# allows the user to quit the program from the terminal
def stdin_listener():
    """
    Listener for quitting the sample
    """
    while True:
        selection = input("Press Q to quit\n")
        if selection == "Q" or selection == "q":
            print("Quitting...")
            break

async def main():

    # provisions the device to IoT Central-- this uses the Device Provisioning Service behind the scenes
    provisioning_device_client = ProvisioningDeviceClient.create_from_symmetric_key(
        provisioning_host=provisioning_host,
        registration_id=registration_id,
        id_scope=id_scope,
        symmetric_key=symmetric_key,
    )
    
    registration_result = await provisioning_device_client.register()

    print("The complete registration result is")
    print(registration_result.registration_state)

    if registration_result.status == "assigned":
        print("Your device has been provisioned. It will now begin sending telemetry.")
        device_client = IoTHubDeviceClient.create_from_symmetric_key(
            symmetric_key=symmetric_key,
            hostname=registration_result.registration_state.assigned_hub,
            device_id=registration_result.registration_state.device_id,
        )

        # Connect the client.
        await device_client.connect()

    # Send the current temperature as a telemetry message
    async def send_telemetry():
        print("Sending telemetry for temperature")

        while True:
            current_temp = random.randrange(10, 50)  # Current temperature in Celsius (randomly generated)
            # Send a single temperature report message
            temperature_msg = {"temperature": current_temp}

            msg = Message(json.dumps(temperature_msg))
            msg.content_encoding = "utf-8"
            msg.content_type = "application/json"
            print("Sent message")
            await device_client.send_message(msg)
            await asyncio.sleep(8)

    send_telemetry_task = asyncio.create_task(send_telemetry())

    # Run the stdin listener in the event loop
    loop = asyncio.get_running_loop()
    user_finished = loop.run_in_executor(None, stdin_listener)
    # Wait for user to indicate they are done listening for method calls
    await user_finished

    send_telemetry_task.cancel()
    # Finally, shut down the client
    await device_client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())

    # If using Python 3.6 or below, use the following code instead of asyncio.run(main()):
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(main())
    # loop.close()
