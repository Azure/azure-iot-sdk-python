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
from azure.iot.device import constant, Message, MethodResponse
from datetime import date, timedelta, datetime


logging.basicConfig(level=logging.ERROR)

# The device "TemperatureController" that is getting implemented using the above interfaces.
# This id can change according to the company the user is from
# and the name user wants to call this pnp device
model_id = "dtmi:com:example:Thermostat;1"

#####################################################
# GLOBAL THERMOSTAT VARIABLES
maxTemp = None
minTemp = None
avgTempList = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
sizeOfMovingWindow = len(avgTempList)
targetTemperature = None


#####################################################
# COMMAND HANDLERS : User will define these handlers
# depending on what commands the DTMI defines


async def reboot_handler(values):
    global maxTemp
    global minTemp
    global avgTempList
    global targetTemperature
    if values and type(values) == int:
        print("Rebooting after delay of {delay} secs".format(delay=values))
        asyncio.sleep(values)
    maxTemp = None
    minTemp = None
    for idx in range(len(avgTempList)):
        avgTempList[idx] = 0
    targetTemperature = None
    print("maxTemp {}, minTemp {}".format(maxTemp, minTemp))
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
    response_dict = {
        "tempReport": {
            "maxTemp": maxTemp,
            "minTemp": minTemp,
            "avgTemp": sum(avgTempList) / sizeOfMovingWindow,
            "startTime": (datetime.now() - timedelta(0, sizeOfMovingWindow * 8)).strftime(
                "%d/%m/%Y %H:%M:%S"
            ),
            "endTime": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        }
    }
    # serialize response dictionary into a JSON formatted str
    # TODO: For python team, this seems optional? Because for reboot response, the response being a dictionary seems to work fine.
    response_payload = json.dumps(response_dict, default=lambda o: o.__dict__, sort_keys=True)
    print(response_payload)
    return response_payload


def create_reboot_response(values):
    response = {"result": True, "data": "reboot succeeded"}
    return response


# END CREATE RESPONSES TO COMMANDS
#####################################################

#####################################################
# TELEMETRY TASKS


async def send_telemetry_from_thermostat(device_client, telemetry_msg):
    msg = Message(json.dumps(telemetry_msg))
    msg.content_encoding = "utf-8"
    msg.content_type = "application/json"
    print("Sent message")
    await device_client.send_message(msg)


# END TELEMETRY TASKS
#####################################################

#####################################################
# CREATE COMMAND LISTENERS


def retrieve_values_dict_from_payload(command_request):
    """
    Helper method to retrieve the values portion of the response payload.
    :param command_request: The full dictionary of the command request which contains the payload.
    :return: The values dictionary from the payload.
    """
    pnp_key = "commandRequest"
    values = {}
    if not command_request.payload:
        print("Payload was empty.")
    elif pnp_key not in command_request.payload:
        print("There was no payload for {key}.".format(key=pnp_key))
    else:
        command_request_payload = command_request.payload
        values = command_request_payload[pnp_key]["value"]
    return values


async def execute_command_listener(
    device_client, method_name, user_command_handler, create_user_response_handler
):
    while True:
        if method_name:
            command_name = method_name
        else:
            command_name = None

        command_request = await device_client.receive_method_request(command_name)
        print("Command request received with payload")
        print(command_request.payload)

        # TODO: In the PnP Spec, the "values" seems vague. What is the purpose of it for Command Requests? What for example would it be for 'reboot'?
        pnp_key = "commandRequest"
        values = {}
        if not command_request.payload:
            print("Payload was empty.")
        elif pnp_key not in command_request.payload:
            print("There was no payload for {key}.".format(key=pnp_key))
        else:
            command_request_payload = command_request.payload
            values = command_request_payload[pnp_key]["value"]

        await user_command_handler(values)

        response_status = 200
        response_payload = create_user_response_handler(values)

        command_response = MethodResponse.create_from_method_request(
            command_request, response_status, response_payload
        )

        try:
            await device_client.send_method_response(command_response)
        except Exception:
            print("responding to the {command} command failed".format(command=method_name))


# async def execute_property_listener(device_client):
#     ignore_keys = ["__t", "$version"]
#     while True:
#         patch = await device_client.receive_twin_desired_properties_patch()  # blocking call
#         print("the data in the desired properties patch was: {}".format(patch))

#         component_prefix = list(patch.keys())[0]
#         values = patch[component_prefix]
#         print("previous values")
#         print(values)

#         version = patch["$version"]
#         inner_dict = {}

#         for prop_name, prop_value in values.items():
#             if prop_name in ignore_keys:
#                 continue
#             else:
#                 inner_dict["ac"] = 200
#                 inner_dict["ad"] = "Successfully executed patch"
#                 inner_dict["av"] = version
#                 inner_dict["value"] = prop_value
#                 values[prop_name] = inner_dict

#         iotin_dict = dict()
#         if component_prefix:
#             iotin_dict[component_prefix] = values
#             # print(iotin_dict)
#         else:
#             iotin_dict = values

#         await device_client.patch_twin_reported_properties(iotin_dict)


# END COMMAND LISTENERS
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
    # Set and read desired property (target temperature)

    asyncio.create_task(
        device_client.patch_twin_reported_properties(
            {
                "targetTemperature": {
                    "value": targetTemperature,
                    "ac": 200,
                    "ad": "demonstrating Valid P&P property with embedded value",
                    "av": 1,
                },
                "maxTempSinceLastReboot": maxTemp,
            }
        )
    )

    ################################################
    # Register callback and Handle command (reboot)
    print("Listening for command requests and property updates")

    async def execute_property_listener():
        ignore_keys = ["__t", "$version"]
        while True:
            patch = await device_client.receive_twin_desired_properties_patch()  # blocking call
            print("the data in the desired properties patch was: {}".format(patch))

            component_prefix = list(patch.keys())[0]
            values = patch[component_prefix]
            print("previous values")
            print(values)

            version = patch["$version"]
            inner_dict = {}

            for prop_name, prop_value in values.items():
                if prop_name in ignore_keys:
                    continue
                else:
                    inner_dict["ac"] = 200
                    inner_dict["ad"] = "Successfully executed patch"
                    inner_dict["av"] = version
                    inner_dict["value"] = prop_value
                    values[prop_name] = inner_dict

            iotin_dict = dict()
            if component_prefix:
                iotin_dict[component_prefix] = values
                # print(iotin_dict)
            else:
                iotin_dict = values

            await device_client.patch_twin_reported_properties(iotin_dict)

    listeners = asyncio.gather(
        execute_command_listener(
            device_client,
            method_name="reboot",
            user_command_handler=reboot_handler,
            create_user_response_handler=create_reboot_response,
        ),
        execute_command_listener(
            device_client,
            method_name="getMaxMinReport",
            user_command_handler=max_min_handler,
            create_user_response_handler=create_max_min_report_response,
        ),
        execute_property_listener(),
    )

    ################################################
    # Send telemetry (current temperature)

    # TODO: Concern for the python team. It looks like the call stack keeps growing indefinitely when running send telemetry?
    async def send_telemetry():
        print("Sending telemetry for temperature")
        global maxTemp
        global minTemp
        currentAvgIdx = 0

        while True:
            currentTemp = random.randrange(10, 50)  # Current temperature in Celsius
            if not maxTemp:
                maxTemp = currentTemp
            elif currentTemp > maxTemp:
                maxTemp = currentTemp

            if not minTemp:
                minTemp = currentTemp
            elif currentTemp < minTemp:
                minTemp = currentTemp

            avgTempList[currentAvgIdx] = currentTemp
            currentAvgIdx = (currentAvgIdx + 1) % sizeOfMovingWindow

            temperature_msg1 = {"temperature": currentTemp}
            await send_telemetry_from_thermostat(device_client, temperature_msg1)
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
