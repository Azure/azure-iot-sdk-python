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
from datetime import date


logging.basicConfig(level=logging.ERROR)

# the interfaces that are pulled in to implement the device.
# User has to know these values as these may change and user can
# choose to implement different interfaces.
thermostat_digital_twin_model_identifier = "dtmi:com:example:Thermostat;1"
device_info_digital_twin_model_identifier = "dtmi:azure:DeviceManagement:DeviceInformation;1"

# The device "TemperatureController" that is getting implemented using the above interfaces.
# This id can change according to the company the user is from
# and the name user wants to call this pnp device
model_id = "dtmi:com:example:TemperatureController;1"

# the components inside this pnp device.
# there can be multiple components from 1 interface
# component names according to interfaces following pascal case.
device_information_component_name = "deviceInformation"
thermostat_1_component_name = "thermostat1"
thermostat_2_component_name = "thermostat2"

#####################################################
# COMMAND HANDLERS : User will define these handlers
# depending on what commands the component defines


async def reboot_handler(values):
    if values:
        print("Rebooting after delay of {delay} secs".format(delay=values))
    print("Done rebooting")


async def max_min_handler(values):
    if values:
        print(
            "Will return the max, min and average temperature from the specified time {since} to the current time".format(
                since=values
            )
        )
    print("Done generating")


# END COMMAND HANDLERS
#####################################################

#####################################################
# CREATE RESPONSES TO COMMANDS


def create_max_min_report_response(values):
    """
    An example function that can create a response to the "getMaxMinReport" command request the way the user wants it.
    Most of the times response is created by a helper function which follows a generic pattern.
    This should be only used when the user wants to give a detailed response back to the Hub.
    :param values: The values that were received as part of the request.
    """
    response_dict = {}
    response_dict["maxTemp"] = 60.64
    response_dict["minTemp"] = 10.54
    response_dict["avgTemp"] = 34.78
    response_dict["startTime"] = date.fromisoformat("2020-05-04").__str__()
    response_dict["endTime"] = date.fromisoformat("2020-06-04").__str__()

    final_dict = {"tempReport": response_dict}

    response_payload = json.dumps(final_dict, default=lambda o: o.__dict__, sort_keys=True)
    # print(response_payload)
    return response_payload


# END CREATE RESPONSES TO COMMANDS
#####################################################

#####################################################
# TELEMETRY TASKS


async def send_telemetry_from_temp_controller(device_client, telemetry_msg, component_name=None):
    await pnp_methods.pnp_send_telemetry(
        device_client, telemetry_msg, component_name
    )  # only sends telemetry values that have changed
    await asyncio.sleep(8)


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

    asyncio.create_task(pnp_methods.pnp_update_property(device_client, serialNumber="alohomora"))

    asyncio.create_task(
        pnp_methods.pnp_update_property(
            device_client,
            thermostat_1_component_name,
            targetTemperature={"value": 56.78, "ac": 200, "ad": "wingardium leviosa", "av": 1},
            maxTempSinceLastReboot=67.89,
        )
    )

    asyncio.create_task(
        pnp_methods.pnp_update_property(
            device_client,
            thermostat_2_component_name,
            targetTemperature={"value": 35.67, "ac": 200, "ad": "expecto patronum", "av": 1},
            maxTempSinceLastReboot=78.90,
        )
    )

    asyncio.create_task(
        pnp_methods.pnp_update_property(
            device_client,
            device_information_component_name,
            swVersion="4.5",
            manufacturer="Contoso Device Corporation",
            model="Contoso 4762B-turbo",
            osName="Mac Os",
            processorArchitecture="x86-64",
            processorManufacturer="Intel",
            totalStorage=1024,
            totalMemory=32,
        )
    )

    ################################################
    # Get all the listeners running
    print("Listening for command requests and property updates")

    listeners = asyncio.gather(
        pnp_methods.execute_listener(
            device_client, method_name="reboot", user_command_handler=reboot_handler
        ),
        pnp_methods.execute_listener(
            device_client,
            thermostat_1_component_name,
            method_name="getMaxMinReport",
            user_command_handler=max_min_handler,
            create_user_response_handler=create_max_min_report_response,
        ),
        pnp_methods.execute_listener(
            device_client,
            thermostat_2_component_name,
            method_name="getMaxMinReport",
            user_command_handler=max_min_handler,
            create_user_response_handler=create_max_min_report_response,
        ),
        pnp_methods.execute_property_listener(device_client),
    )

    ################################################
    # Function to send telemetry every 8 seconds

    async def send_telemetry():
        print("Sending telemetry from various components")
        while True:
            temperature_msg1 = {"temperature": random.randrange(10, 50)}
            temperature_msg2 = {"temperature": random.randrange(10, 50)}
            workingset_msg3 = {"workingset": random.randrange(1, 100)}
            await send_telemetry_from_temp_controller(
                device_client, temperature_msg1, thermostat_1_component_name
            )
            await send_telemetry_from_temp_controller(
                device_client, temperature_msg2, thermostat_2_component_name
            )
            await send_telemetry_from_temp_controller(device_client, workingset_msg3)

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
