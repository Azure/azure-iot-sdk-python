# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import os
import asyncio
import random
import logging

from azure.iot.device.aio import IoTHubDeviceClient
import pnp_methods

logging.basicConfig(level=logging.ERROR)
interface = "digital-twin-model-id=dtmi:contoso:com:EnvironmentalSensor;1"

# User defined variables
sample_device_interface = "sampleDeviceInfo"
device_name = "sensor"


#####################################################
# COMMAND HANDLERS : User will define these handlers
async def blink_handler(values):
    if values and "interval" in values:
        interval = values["interval"]
        print("Interval is: " + str(interval))
    print("Done blinking")


async def turn_on_handler(values):
    print("Switched On device")


async def turn_off_handler(values):
    print("Switched Off device")


async def check_handler(values):
    if values and "after" in values:
        after = values["after"]
        print("After is: " + str(after))
    print("Done checking")


# END COMMAND HANDLERS
#####################################################


#####################################################
# An # END KEYBOARD INPUT LISTENER to quit application
def stdin_listener():
    """
    Listener for quitting the sample
    """
    while True:
        selection = input("Press Q to quit\n")
        if selection == "Q" or selection == "q":
            print("Quitting...")
            break


# END KEYBOARD INPUT LISTENER
#####################################################


#####################################################
# MAIN STARTS


async def main():
    # The connection string for a device should never be stored in code. For the sake of simplicity we're using an environment variable here.
    conn_str = os.getenv("IOTHUB_DEVICE_CONNECTION_STRING")

    print("Connecting using Connection String " + conn_str)

    # The client object is used to interact with your Azure IoT hub.
    device_client = IoTHubDeviceClient.create_from_connection_string(
        conn_str, product_info=interface
    )

    # Connect the client.
    await device_client.connect()

    ################################################
    # Get all the listeners running
    print("Listening for command requests")
    listeners = asyncio.gather(
        pnp_methods.execute_listener(device_client, device_name, "blink", blink_handler),
        pnp_methods.execute_listener(device_client, device_name, "turnon", turn_on_handler),
        pnp_methods.execute_listener(device_client, device_name, "turnoff", turn_off_handler),
        pnp_methods.execute_listener(device_client, device_name, "check", check_handler),
        pnp_methods.execute_listener(device_client, device_name),
    )

    await pnp_methods.pnp_update_property(
        device_client,
        sample_device_interface,
        # swVersion="4.3",
        manufacturer="Contoso Device Corporation",
        model="Contoso 4762B-turbo",
        osName="Mac Os",
        processorArchitecture="x86-64",
        processorManufacturer="Intel",
        totalStorage="1024 GB",
        totalMemory="32 GB",
    )

    ################################################
    # Function to send telemetry every 8 seconds
    async def send_telemetry():
        print("Entering send_telemetry")
        while True:
            telemetry_msg = {"temp": random.randrange(10, 51), "humidity": random.randrange(10, 99)}
            await pnp_methods.pnp_send_telemetry(
                device_client, device_name, telemetry_msg
            )  # only sends telemetry values that have changed
            await asyncio.sleep(8)

    send_telemetry_task = asyncio.ensure_future(send_telemetry())

    # Run the stdin listener in the event loop
    loop = asyncio.get_running_loop()
    user_finished = loop.run_in_executor(None, stdin_listener)
    # # Wait for user to indicate they are done listening for method calls
    await user_finished

    if not listeners.done():
        listeners.set_result("DONE")

    listeners.cancel()

    send_telemetry_task.cancel()

    # finally, disconnect
    await device_client.disconnect()


#####################################################
# EXECUTE MAIN

if __name__ == "__main__":
    asyncio.run(main())

    # If using Python 3.6 or below, use the following code instead of asyncio.run(main()):
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(main())
    # loop.close()
