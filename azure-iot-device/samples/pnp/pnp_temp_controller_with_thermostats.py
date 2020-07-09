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
from azure.iot.device import Message, MethodResponse
from datetime import date

import pnp_helper_summer_refresh


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
serial_number = "alohomora"
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
    pnp_msg = pnp_helper_summer_refresh.create_telemetry(telemetry_msg, component_name)
    await device_client.send_message(pnp_msg)
    print("Sent message")
    await asyncio.sleep(8)


#####################################################
# COMMAND TASKS


async def execute_command_listener(
    device_client,
    component_name=None,
    method_name=None,
    user_command_handler=None,
    create_user_response_handler=None,
):
    """
    Coroutine for executing listeners. These will listen for command requests.
    They will take in a user provided handler and call the user provided handler
    according to the command request received.
    :param device_client: The device client
    :param component_name: The name of the device like "sensor"
    :param method_name: (optional) The specific method name to listen for. Eg could be "blink", "turnon" etc.
    If not provided the listener will listen for all methods.
    :param user_command_handler: (optional) The user provided handler that needs to be executed after receiving "command requests".
    If not provided nothing will be executed on receiving command.
    :param create_user_response_handler: (optional) The user provided handler that will create a response.
    If not provided a generic response will be created.
    :return:
    """
    while True:
        if component_name and method_name:
            command_name = component_name + "*" + method_name
        elif method_name:
            command_name = method_name
        else:
            command_name = None

        command_request = await device_client.receive_method_request(command_name)
        print("Command request received with payload")
        values = command_request.payload
        print(values)

        if user_command_handler:
            await user_command_handler(values)
        else:
            print("No handler provided to execute")

        (
            response_status,
            response_payload,
        ) = pnp_helper_summer_refresh.create_response_payload_with_status(
            command_request, method_name, create_user_response=create_user_response_handler
        )

        pnp_command_response = MethodResponse.create_from_method_request(
            command_request, response_status, response_payload
        )

        try:
            await device_client.send_method_response(pnp_command_response)
        except Exception:
            print("responding to the {command} command failed".format(command=method_name))


#####################################################
# PROPERTY TASKS


async def execute_property_listener(device_client):
    while True:
        patch = await device_client.receive_twin_desired_properties_patch()  # blocking call
        pnp_properties_dict = pnp_helper_summer_refresh.create_reported_properties_from_desired(
            patch
        )

        await device_client.patch_twin_reported_properties(pnp_properties_dict)


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
    # Update readable properties from various components

    pnp_properties_root = pnp_helper_summer_refresh.create_reported_properties(
        serialNumber=serial_number
    )
    pnp_properties_thermostat1 = pnp_helper_summer_refresh.create_reported_properties(
        thermostat_1_component_name, maxTempSinceLastReboot=98.34
    )
    pnp_properties_thermostat2 = pnp_helper_summer_refresh.create_reported_properties(
        thermostat_2_component_name, maxTempSinceLastReboot=48.92
    )
    pnp_properties_device_info = pnp_helper_summer_refresh.create_reported_properties(
        device_information_component_name,
        swVersion="5.5",
        manufacturer="Contoso Device Corporation",
        model="Contoso 4762B-turbo",
        osName="Mac Os",
        processorArchitecture="x86-64",
        processorManufacturer="Intel",
        totalStorage=1024,
        totalMemory=32,
    )

    property_updates = asyncio.gather(
        device_client.patch_twin_reported_properties(pnp_properties_root),
        device_client.patch_twin_reported_properties(pnp_properties_thermostat1),
        device_client.patch_twin_reported_properties(pnp_properties_thermostat2),
        device_client.patch_twin_reported_properties(pnp_properties_device_info),
    )

    ################################################
    # Get all the listeners running
    print("Listening for command requests and property updates")

    listeners = asyncio.gather(
        execute_command_listener(
            device_client, method_name="reboot", user_command_handler=reboot_handler
        ),
        execute_command_listener(
            device_client,
            thermostat_1_component_name,
            method_name="getMaxMinReport",
            user_command_handler=max_min_handler,
            create_user_response_handler=create_max_min_report_response,
        ),
        execute_command_listener(
            device_client,
            thermostat_2_component_name,
            method_name="getMaxMinReport",
            user_command_handler=max_min_handler,
            create_user_response_handler=create_max_min_report_response,
        ),
        execute_property_listener(device_client),
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

    if not property_updates.done():
        property_updates.set_result("DONE")

    listeners.cancel()
    property_updates.cancel()

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
