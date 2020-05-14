# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import os
import asyncio
import random
import logging
import json

from azure.iot.device.aio import IoTHubDeviceClient
import pnp_methods
from azure.iot.device import constant

logging.basicConfig(level=logging.ERROR)

# The interfaces that are pulled in to implement the device.
# User has to know these values as these may change and user can
# choose to implement different interfaces.
sensor_digital_twin_model_identifier = "dtmi:com:examples:EnvironmentalSensor;1"
device_information_digital_twin_model_identifier = "dtmi:azure:DeviceManagement:DeviceInformation;1"
sdk_information_digital_twin_model_identifier = "dtmi:azure:Client:SDKInformation;1"

# The device that is getting implemented using the above 3 interfaces.
# This id can change according to the company the user is from
# and the name user wants to call the pnp device
model_id = "dtmi:com:examples:SampleDevice;1"

# defined component names according to interfaces following pascal case.
device_information_component_name = "deviceInformation"
sdk_information_component_name = "sdkInformation"
sensor_component_name = "sensor"

#####################################################
# COMMAND HANDLERS : User will define these handlers
# depending on what commands the component defines


async def blink_handler(values):
    if values and "interval" in values:
        interval = values["interval"]
        print("Interval is: " + str(interval))
        print("Setting blinking interval to {interval}".format(interval=interval))
    print("Done blinking")


async def turn_on_handler(values):
    print("Switched On device")


async def turn_off_handler(values):
    print("Switched Off device")


# END COMMAND HANDLERS
#####################################################

#####################################################
# CREATE RESPONSES TO COMMANDS


def create_blink_response(values):
    """
    An example function that can create a response to the "blink" command request the way the user wants it.
    Most of the times response is created by a helper function which follows a generic pattern.
    This should be only used when the user wants to give a detailed response back to the Hub.
    :param values: The values that were received as part of the request.
    """
    print(values)
    response_dict = {}

    if values and "interval" in values:
        interval = values["interval"]
        result = True
        blink_response = {
            "description": "blinking interval was set to {interval}".format(interval=str(interval))
        }
    else:
        result = False
        blink_response = {"description": "blinking interval could not be set due to errors"}

    response_dict["result"] = result
    response_dict["blinkResponse"] = blink_response

    response_payload = json.dumps(response_dict)
    print(response_payload)
    return response_payload


# END CREATE RESPONSES TO COMMANDS
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
        conn_str, product_info=model_id
    )

    # Connect the client.
    await device_client.connect()

    ################################################
    # Update properties from various components
    update_device_info_task = asyncio.create_task(
        pnp_methods.pnp_update_property(
            device_client,
            device_information_component_name,
            swVersion="4.5",
            manufacturer="Contoso Device Corporation",
            model="Contoso 4762B-turbo",
            osName="Mac Os",
            processorArchitecture="x86-64",
            processorManufacturer="Intel",
            totalStorage="1024 GB",
            totalMemory="32 GB",
        )
    )

    update_sdk_info_task = asyncio.create_task(
        pnp_methods.pnp_update_property(
            device_client,
            sdk_information_component_name,
            language="python",
            version=constant.VERSION,
            vendor="Microsoft",
        )
    )

    update_sensor_props_task = asyncio.create_task(
        pnp_methods.pnp_update_property(
            device_client, sensor_component_name, name="Harry Potter", brightness=3, state=True
        )
    )

    await asyncio.gather(update_device_info_task, update_sdk_info_task, update_sensor_props_task)

    ################################################
    # Get all the listeners running
    print("Listening for command requests")
    listeners = asyncio.gather(
        pnp_methods.execute_listener(
            device_client, sensor_component_name, "blink", blink_handler, create_blink_response
        ),
        pnp_methods.execute_listener(
            device_client, sensor_component_name, "turnOn", turn_on_handler
        ),
        pnp_methods.execute_listener(
            device_client, sensor_component_name, "turnOff", turn_off_handler
        ),
        pnp_methods.execute_listener(device_client, sensor_component_name),
    )

    ################################################
    # Function to send telemetry every 8 seconds
    async def send_telemetry():
        print("Sending telemetry from {component}".format(component=sensor_component_name))
        while True:
            # Temperature are supposed to be in Fahrenheit, so choose range appropriately
            telemetry_msg = {"temp": random.randrange(50, 80), "humidity": random.randrange(30, 60)}
            await pnp_methods.pnp_send_telemetry(
                device_client, sensor_component_name, telemetry_msg
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
