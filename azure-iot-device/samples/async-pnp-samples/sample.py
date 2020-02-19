# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import asyncio
import os
import random

from azure.iot.pnp.aio import IoTHubPnpClient

# These are objects that are modeled in the DTDL
from azure.iot.pnp.models import BaseInterface, Telemetry, Property, WriteableProperty, Command

# These are objects that represent communication with the service
from azure.iot.pnp.models import (
    CommandRequest,
    CommandAcknowledge,
    CommandUpdate,
    PropertyUpdateRequest,
)

capability_model = "urn:azureiot:samplemodel:1"


"""
Big questions:

    1. Do we automatically reate Python-native objects from the DTDL?  If so, how do we deal with naming -- processorArchitecture
       the model should be processorArchitecture if it's a python attribute

       Decision #1: generating object being covered in meeting with modeling team.
       Decision #2: keeping camelCase if that's what the DTDL uses.  Not converting to boxcar_case.

    2. Do we invest more time in getting rid of the big switch model or let it drop?

       Decision: big switch.

"""


class EnvironmentalSensor(BaseInterface):
    def __init__(self, interface_instance_name):
        # Note: instance_name or interface_instance_name?
        super(EnvironmentalSensor, self).__init__(
            interface_instance_name, "urn:contoso:com:EnvironmentalSensor:1"
        )
        self.telemetry.temp = Telemetry()
        self.telemetry.humid = Telemetry()
        self.properties.state = Property()
        self.commands.blink = Command()
        self.commands.turnOff = Command()
        self.commands.turnOn = Command()
        self.commands.runDiagnostics = Command()
        self.properties.name = WriteableProperty()
        self.properties.brightness = WriteableProperty()


class DeviceInformation(BaseInterface):
    def __init__(self, interface_instance_name):
        super(DeviceInformation, self).__init__(
            interface_instance_name, "urn:azureiot:DeviceInformation:1"
        )
        self.properties.manufacturer = Property()
        self.properties.model = Property()
        self.properties.swVersion = Property()
        self.properties.osName = Property()
        self.properties.processorArchitecture = Property()
        self.properties.processorManufacturer = Property()
        self.properties.totalStorage = Property()
        self.properties.totalMemory = Property()


class SampleExit(BaseInterface):
    def __init__(self, interface_instance_name):
        super(SampleExit, self).__init__(
            interface_instance_name, "urn:azureiotsdknode:SampleBaseInterface:SampleExit:1"
        )
        self.commands.exit = Command()


class ModelDefinition(BaseInterface):
    def __init__(self, interface_instance_name):
        super(ModelDefinition, self).__init__(
            interface_instance_name, "urn:azureiot:ModelDiscovery:ModelDefinition:1"
        )
        self.commands.getModelDefinition = Command()


environmental_sensor = EnvironmentalSensor("environmentalSensor")
device_information = DeviceInformation("deviceInformation")
model_definition = ModelDefinition("urn_azureiot_ModelDiscovery_ModelDefinition")
exit_interface = SampleExit("urn_azureiotsdknode_SampleBaseInterface_SampleExit")


# Note: this follows the method pattern from the pythonIoTHubDeviceClient object.
async def environmental_model_listener(interface):
    while True:
        incoming_message = await interface.receive_pnp_message()

        if incoming_message.target == interface.commands.blink:
            print("Got the blink command")

            command_acknowledge = CommandAcknowledge.create_from_command_request(
                incoming_message, 200, "blink response"
            )
            try:
                await interface.send_command_acknowledge(command_acknowledge)
            except Exception:
                print("responding to the blink command failed")

        elif incoming_message.target == interface.commands.turnOn:
            # copypasta
            pass
        elif incoming_message.target == interface.commands.turnOff:
            # copypasta
            pass
        elif incoming_message.target == interface.commands.runDiagnostics:
            print("Got the runDiagnostics command.")

            command_acknowledge = CommandAcknowledge.create_from_command_request(
                incoming_message, 200, "runDiagnostics response"
            )
            try:
                await interface.send_command_acknowledge(command_acknowledge)
            except Exception as e:
                print("responding to the runDiagnostics command failed: {}".format(e))
            else:
                command_update = CommandUpdate.create_from_command_request(
                    incoming_message, 200, "runDiagnostics update response"
                )
                try:
                    await interface.send_command_update(command_update)
                except Exception as e:
                    print("Got an error on the update: {}".format(e))
        elif isinstance(incoming_message, PropertyUpdateRequest):
            property = incoming_message.target
            property_change = incoming_message

            try:
                # question: is the JSON blob below standard?  Should there be a model object for this?
                property.report(
                    property_change.desired_value + "the boss",
                    {
                        "responseVersion": property_change.version,
                        "statusCode": 200,
                        "statusDescription": "a promotion",
                    },
                )
            except Exception:
                print("did not do the update")
            else:
                print("The update worked!!!!")


async def model_definition_listener(interface):
    pass
    # copypasta


async def exit_interface_listener(interface):
    while True:
        incoming_message = await interface.receive_pnp_message()
        if incoming_message.target == interface.commands.exit:
            print(
                "received command: "
                + incoming_message.target.command_name
                + " for interfaceInstance: "
                + incoming_message.interface_instance_name
            )
            command_acknowledge = CommandAcknowledge.create_from_command_request(
                incoming_message, 200, None
            )
            await interface.send_command_acknowledge(command_acknowledge)
            await asyncio.sleep(2)
            exit
            # coroutine returns, causing main() to exit


async def main():
    conn_str = os.getenv("IOTHUB_DEVICE_CONNECTION_STRING")
    pnp_client = IoTHubPnpClient.create_from_connection_string(conn_str, capability_model)

    pnp_client.add_interface_instance(environmental_sensor)
    pnp_client.add_interface_instance(device_information)
    pnp_client.add_interface_instance(model_definition)
    pnp_client.add_interface_instance(exit_interface)

    await pnp_client.register()

    listeners = asyncio.ensure_future(
        asyncio.gather(
            environmental_model_listener(environmental_sensor),
            model_definition_listener(model_definition),
        )
    )

    environmental_sensor.properties.state = True
    await environmental_sensor.report_properties()  # only reports changed properties

    device_information.properties.manufacturer = "Contoso Device Corporation"
    device_information.properties.model = "Contoso 4762B-turbo"
    device_information.properties.sw_version = "3.1"
    device_information.properties.os_name = "ContosoOS"
    device_information.properties.processor_architecture = "4762"
    device_information.properties.processor_manufacturer = "Contoso Foundries"
    device_information.properties.total_storage = "64000"
    device_information.properties.total_memory = "640"
    await device_information.report_properties()  # only repors changed properties

    #  send telemetry every 5 seconds
    def send_telemetry():
        while True:
            environmental_sensor.telemetry.temp = 10 + random.random_int(0, 90)
            environmental_sensor.telemetry.humid = 1 + random.randint(0, 99)
            await environmental_sensor.report_telemetry()  # only sends telemetry values that have changed
            await asyncio.sleep(5)

    sender = asyncio.ensure_future(send_telemetry())

    await exit_interface_listener(exit_interface)

    await listeners.cancel()
    await sender.cancel()


if __name__ == "__main__":
    asyncio.run(main())

    # If using Python 3.6 or below, use the following code instead of asyncio.run(main()):
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(main())
    # loop.close()
