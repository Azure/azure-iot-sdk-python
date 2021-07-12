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
from azure.iot.device.aio import ProvisioningDeviceClient
from azure.iot.device import CommandResponse, ClientPropertyCollection, WritablePropertyResponse
from datetime import timedelta, datetime

logging.basicConfig(level=logging.ERROR)

# The device "TemperatureController" that is getting implemented using the above interfaces.
# This id can change according to the company the user is from
# and the name user wants to call this Plug and Play device
model_id = "dtmi:com:example:TemperatureController;2"

# the components inside this Plug and Play device.
# there can be multiple components from 1 interface
# component names according to interfaces following pascal case.
device_information_component_name = "deviceInformation"
thermostat_1_component_name = "thermostat1"
thermostat_2_component_name = "thermostat2"
serial_number = "alohomora"


class Thermostat(object):
    def __init__(self, name, moving_win=10):

        self.moving_window = moving_win
        self.records = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        self.index = 0

        self.cur = 0
        self.max = 0
        self.min = 0
        self.avg = 0

        self.name = name

    def record(self, current_temp):
        self.cur = current_temp
        self.records[self.index] = current_temp
        self.max = self.calculate_max(current_temp)
        self.min = self.calculate_min(current_temp)
        self.avg = self.calculate_average()

        self.index = (self.index + 1) % self.moving_window

    def calculate_max(self, current_temp):
        if not self.max:
            return current_temp
        elif current_temp > self.max:
            return self.max

    def calculate_min(self, current_temp):
        if not self.min:
            return current_temp
        elif current_temp < self.min:
            return self.min

    def calculate_average(self):
        return sum(self.records) / self.moving_window

    def create_report(self):
        response_dict = {}
        response_dict["maxTemp"] = self.max
        response_dict["minTemp"] = self.min
        response_dict["avgTemp"] = self.avg
        response_dict["startTime"] = (
            datetime.now() - timedelta(0, self.moving_window * 8)
        ).isoformat()
        response_dict["endTime"] = datetime.now().isoformat()
        return response_dict


class ThermostatApp(object):
    def __init__(self):
        self.device_client = None
        self.thermostat_1 = None
        self.thermostat_2 = None

    #####################################################
    # CREATE RESPONSES TO COMMANDS

    def handle_max_min_report_command_request(self, thermostat_name):
        """
        An example function that can create a response to the "getMaxMinReport" command_request the way the user wants it.
        Most of the times response is created by a helper function which follows a generic pattern.
        This should be only used when the user wants to give a detailed response back to the Hub.
        :param values: The values that were received as part of the request.
        """
        if thermostat_name == thermostat_1_component_name and self.thermostat_1:
            response_dict = self.thermostat_1.create_report()
        elif thermostat_name == thermostat_2_component_name and self.thermostat_2:
            response_dict = self.thermostat_2.create_report()
        else:  # This is done to pass certification.
            response_dict = {}
            response_dict["maxTemp"] = 0
            response_dict["minTemp"] = 0
            response_dict["avgTemp"] = 0
            response_dict["startTime"] = datetime.now().isoformat()
            response_dict["endTime"] = datetime.now().isoformat()

        return 200, response_dict

    async def handle_reboot_command_request(self, values):
        if values:
            print("Rebooting after delay of {delay} secs".format(delay=values))
        print("Done rebooting")
        return 200, None

    # END CREATE RESPONSES TO COMMANDS
    #####################################################

    #####################################################
    # COMMAND TASKS

    async def handle_command_received(self, command_request):
        if command_request.command_name == "reboot":
            handle = self.handle_reboot_command_request
        elif command_request.command_name == "getMaxMinReport":
            handler = self.handle_max_min_report_command_request
        else:
            handler = None

        print("Command request received with payload")
        print(command_request.payload)

        if handle:
            response_status, response_payload = await handler(command_request.component_name)
        else:
            response_status = 404
            response_payload = None

        command_response = CommandResponse.create_from_command_request(
            command_request, response_status, response_payload
        )

        try:
            await self.device_client.send_command_response(command_response)
        except Exception:
            print(
                "responding to the {command_name} command failed".format(
                    command_name=command_request.command_name
                )
            )

    #####################################################
    # PROPERTY TASKS

    async def handle_writable_property_update_request_received(self, writable_props):
        while True:
            print(writable_props.backing_object)

            properties = ClientPropertyCollection()

            for component_name in [thermostat_1_component_name, thermostat_2_component_name]:
                component_props = writable_props.get(component_name, {})
                for property_name in component_props:
                    properties.set_component_property(
                        component_name,
                        property_name,
                        WritablePropertyResponse(
                            ack_code=200,
                            ck_description="Successfully executed patch",
                            ack_version=writable_props.version,
                            value=component_props[property_name],
                        ),
                    )

            await self.device_client.update_client_properties(properties)

    #####################################################
    # An # END KEYBOARD INPUT LISTENER to quit application

    def stdin_listener(self):
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
    async def provision_device(
        self, provisioning_host, id_scope, registration_id, symmetric_key, model_id
    ):
        provisioning_device_client = ProvisioningDeviceClient.create_from_symmetric_key(
            provisioning_host=provisioning_host,
            registration_id=registration_id,
            id_scope=id_scope,
            symmetric_key=symmetric_key,
        )

        provisioning_device_client.provisioning_payload = {"modelId": model_id}
        return await provisioning_device_client.register()

    async def main(self):
        switch = os.getenv("IOTHUB_DEVICE_SECURITY_TYPE")
        if switch == "DPS":
            provisioning_host = (
                os.getenv("IOTHUB_DEVICE_DPS_ENDPOINT")
                if os.getenv("IOTHUB_DEVICE_DPS_ENDPOINT")
                else "global.azure-devices-provisioning.net"
            )
            id_scope = os.getenv("IOTHUB_DEVICE_DPS_ID_SCOPE")
            registration_id = os.getenv("IOTHUB_DEVICE_DPS_DEVICE_ID")
            symmetric_key = os.getenv("IOTHUB_DEVICE_DPS_DEVICE_KEY")

            registration_result = await self.provision_device(
                provisioning_host, id_scope, registration_id, symmetric_key, model_id
            )

            if registration_result.status == "assigned":
                print("Device was assigned")
                print(registration_result.registration_state.assigned_hub)
                print(registration_result.registration_state.device_id)
                self.device_client = IoTHubDeviceClient.create_from_symmetric_key(
                    symmetric_key=symmetric_key,
                    hostname=registration_result.registration_state.assigned_hub,
                    device_id=registration_result.registration_state.device_id,
                    model_id=model_id,
                )
            else:
                raise RuntimeError(
                    "Could not provision device. Aborting Plug and Play device connection."
                )

        elif switch == "connectionString":
            conn_str = os.getenv("IOTHUB_DEVICE_CONNECTION_STRING")
            print("Connecting using Connection String " + conn_str)
            self.device_client = IoTHubDeviceClient.create_from_connection_string(
                conn_str, model_id=model_id
            )
        else:
            raise RuntimeError(
                "At least one choice needs to be made for complete functioning of this sample."
            )

        # Connect the client.
        await self.device_client.connect()

        ################################################
        # Update readable properties from various components

        properties = ClientPropertyCollection()
        properties.set_property("serialNumber", serial_number)
        properties.set_compoent_property(
            thermostat_1_component_name, "maxTempSinceLastReboot", 98.34
        )
        properties.set_compoent_property(
            thermostat_2_component_name, "maxTempSinceLastReboot", 48.92
        )
        properties.set_component_property(device_information_component_name, "swVersion", "5.5")
        properties.set_component_property(
            device_information_component_name, "manufacturer", "Contoso Device Corporation"
        )
        properties.set_component_property(
            device_information_component_name, "model", "Contoso 4762B-turbo"
        )
        properties.set_component_property(device_information_component_name, "osName", "Mac Os")
        properties.set_component_property(
            device_information_component_name, "processorArchitecture", "x86-64"
        )
        properties.set_component_property(
            device_information_component_name, "processorManufacturer", "Intel"
        )
        properties.set_component_property(device_information_component_name, "totalStorage", 1024)
        properties.set_component_property(device_information_component_name, "totalMemory", 32)
        await self.device_client.update_client_propertieupdate_client_properties(properties)

        ################################################
        # Get all the listeners running
        print("Listening for command requests and property updates")

        self.thermostat_1 = Thermostat(thermostat_1_component_name, 10)
        self.thermostat_2 = Thermostat(thermostat_2_component_name, 10)

        self.device_client.on_writable_property_update_request_received = (
            self.handle_writable_property_update_request_received
        )
        self.device_client.on_command_request_received = self.handle_command_received

        ################################################
        # Function to send telemetry every 8 seconds

        async def send_telemetry():
            print("Sending telemetry from various components")

            while True:
                curr_temp_ext = random.randrange(10, 50)
                self.thermostat_1.record(curr_temp_ext)

                temperature_msg1 = {"temperature": curr_temp_ext}
                await self.device_client.send_telemetry(
                    temperature_msg1, thermostat_1_component_name
                )
                await asyncio.sleep(5)

                curr_temp_int = random.randrange(10, 50)  # Current temperature in Celsius
                self.thermostat_2.record(curr_temp_int)

                temperature_msg2 = {"temperature": curr_temp_int}

                await self.device_client.send_telemetry(
                    temperature_msg2, thermostat_2_component_name
                )
                await asyncio.sleep(5)

                workingset_msg3 = {"workingSet": random.randrange(1, 100)}
                await self.device_client.send_telemetry(workingset_msg3)
                await asyncio.sleep(5)

        send_telemetry_task = asyncio.ensure_future(send_telemetry())

        # Run the stdin listener in the event loop
        loop = asyncio.get_running_loop()
        user_finished = loop.run_in_executor(None, self.stdin_listener)
        # # Wait for user to indicate they are done listening for method calls
        await user_finished

        send_telemetry_task.cancel()

        # Finally, shut down the client
        await self.device_client.shutdown()


#####################################################
# EXECUTE MAIN

if __name__ == "__main__":
    asyncio.run(ThermostatApp.main())

    # If using Python 3.6 or below, use the following code instead of asyncio.run(main()):
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(main())
    # loop.close()
