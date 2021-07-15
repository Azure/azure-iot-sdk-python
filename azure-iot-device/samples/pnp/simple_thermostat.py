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
from azure.iot.device import (
    constant,
    ClientPropertyCollection,
    generate_writable_property_response,
    CommandResponse,
)
from datetime import date, timedelta, datetime

logging.basicConfig(level=logging.ERROR)

# The device "Thermostat" that is getting implemented using the above interfaces.
# This id can change according to the company the user is from
# and the name user wants to call this Plug and Play device
model_id = "dtmi:com:example:Thermostat;1"


class ThermostatApp(object):
    def __init__(self):
        self.device_client = None
        self.max_temp = None
        self.min_temp = None
        self.avg_temp_list = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        self.moving_window_size = len(self.avg_temp_list)
        self.target_temperature = None

    #####################################################
    # COMMAND HANDLERS : User will define these handlers
    # depending on what commands the DTMI defines

    async def reboot_handler(self, values):
        if values and type(values) == int:
            print("Rebooting after delay of {delay} secs".format(delay=values))
            asyncio.sleep(values)
        self.max_temp = None
        self.min_temp = None
        for idx in range(len(self.avg_temp_list)):
            self.avg_temp_list[idx] = 0
        self.target_temperature = None
        print("maxTemp {}, minTemp {}".format(self.max_temp, self.min_temp))
        print("Done rebooting")

    async def max_min_handler(self, values):
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

    def create_max_min_report_response(self, values):
        """
        An example function that can create a response to the "getMaxMinReport" command_request the way the user wants it.
        Most of the times response is created by a helper function which follows a generic pattern.
        This should be only used when the user wants to give a detailed response back to the Hub.
        :param values: The values that were received as part of the request.
        """
        response = {
            "maxTemp": self.max_temp,
            "minTemp": self.min_temp,
            "avgTemp": sum(self.avg_temp_list) / self.moving_window_size,
            "startTime": (datetime.now() - timedelta(0, self.moving_window_size * 8)).isoformat(),
            "endTime": datetime.now().isoformat(),
        }
        return response

    def create_reboot_response(self, values):
        response = {"result": True, "data": "reboot succeeded"}
        return response

    # END CREATE RESPONSES TO COMMANDS
    #####################################################

    #####################################################
    # CREATE COMMAND AND PROPERTY LISTENERS

    async def handle_command_request_received(self, command_request):
        if command_request.command_name == "reboot":
            handler = self.reboot_handler
            responder = self.create_reboot_response
        elif command_request.command_name == "getMaxMinReport":
            handler = self.max_min_handler
            responder = self.create_max_min_report_response
        else:
            handler = None
            responder = None

        print("Command request received with payload")
        print(command_request.payload)

        if handler:
            await handler(command_request.payload)
            response_status = 200
            response_payload = responder(command_request.payload)
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

    async def handle_writable_property_update_request_received(self, writable_props):
        # only handles root properties

        print(
            "the data in the desired properties patch was: {}".format(
                writable_props.backing_object()
            )
        )

        properties = ClientPropertyCollection()

        for prop_name in writable_props.backing_object:
            properties.set_property(
                prop_name,
                generate_writable_property_response(
                    ack_code=200,
                    ack_description="Successfully executed patch",
                    ack_version=writable_props.version,
                    value=writable_props.property_values[prop_name],
                ),
            )

        await self.device_client.update_client_properties(properties)

    # END COMMAND AND PROPERTY LISTENERS
    #####################################################

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
    # PROVISION DEVICE
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

    #####################################################
    # MAIN STARTS
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
        # Set and read desired property (target temperature)

        max_temp = 10.96  # Initial Max Temp otherwise will not pass certification
        properties = ClientPropertyCollection()
        properties.set_property_value("maxTempSinceLastReboot", max_temp)
        await self.device_client.update_client_propertieupdate_client_properties(properties)

        ################################################
        # Register callback and Handle command (reboot)
        print("Listening for command requests and property updates")
        self.device_client.on_writable_property_update_request_received = (
            self.handle_writable_property_update_request_received
        )
        self.device_client.on_command_request_received = self.handle_command_request_received

        ################################################
        # Send telemetry (current temperature)

        async def send_telemetry():
            print("Sending telemetry for temperature")
            current_avg_idx = 0

            while True:
                current_temp = random.randrange(10, 50)  # Current temperature in Celsius
                if not self.max_temp:
                    self.max_temp = current_temp
                elif current_temp > max_temp:
                    self.max_temp = current_temp

                if not self.min_temp:
                    self.min_temp = current_temp
                elif current_temp < self.min_temp:
                    self.min_temp = current_temp

                self.avg_temp_list[current_avg_idx] = current_temp
                current_avg_idx = (current_avg_idx + 1) % self.moving_window_size

                temperature_msg1 = {"temperature": current_temp}
                await self.device_client.send_telemetry(temperature_msg1)
                await asyncio.sleep(8)

        send_telemetry_task = asyncio.create_task(send_telemetry())

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
    asyncio.run(ThermostatApp().main())

    # If using Python 3.6 or below, use the following code instead of asyncio.run(main()):
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(main())
    # loop.close()
