# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import asyncio
import os
import random

from azure.iot.pnp.aio import IoTHubPnpClient
from azure.iot.pnp.models import (
    Interface,
    Telemetry,
    Property,
    WriteableProperty,
    Command,
    CommandAcknowledge,
    CommandUpdate,
)

capability_model = "urn:azureiot:samplemodel:1"


"""
Big questions:

    1. Do we automatically reate Python-native objects from the DTDL?  If so, how do we deal with naming -- processorArchitecture
       the model should be processor_architecture if it's a python attribute

    2. Do we invest more time in getting rid of the big switch model or let it drop?

Inconsistencies:

    1. For updating properties, you use the Property object.  For receiving property updates, you use a switch on the interface

    2. For sending property data, you call update on the property object.  For sending telemetry, you send json on the inerface.

    3. Command and Telemetry objects seem to be completely useless.  The app developer uses names for everything.

"""


# Note: Node calls the BaseInterface
class EnvironmentalSensor(Interface):
    def __init__(self, interface_instance_name):
        # Note: instance_name or interface_instance_name?
        super(EnvironmentalSensor, self).__init__(
            interface_instance_name, "urn:contoso:com:EnvironmentalSensor:1"
        )
        self.temp = Telemetry()
        self.humid = Telemetry()
        self.state = Property()
        self.blink = Command()
        # Note: the command in the model is TurnOff, but pythonic naming has us calling the Command object turn_off.  Confusing!
        self.turn_off = Command()
        self.turn_on = Command()
        self.run_diagnostics = Command()
        # Note: Node has Property(True) for writeable
        self.name = WriteableProperty()
        self.brightness = WriteableProperty()


class DeviceInformation(Interface):
    def __init__(self, interface_instance_name):
        super(DeviceInformation, self).__init__(
            interface_instance_name, "urn:azureiot:DeviceInformation:1"
        )
        self.manufacturer = Property()
        self.model = Property()
        self.sw_version = Property()
        self.os_name = Property()
        self.processor_architecture = Property()
        self.processor_manufacturer = Property()
        self.total_storage = Property()
        self.total_memory = Property()


class SampleExit(Interface):
    def __init__(self, interface_instance_name):
        super(SampleExit, self).__init__(
            interface_instance_name, "urn:azureiotsdknode:SampleInterface:SampleExit:1"
        )
        self.exit = Command()


class ModelDefinition(Interface):
    def __init__(self, interface_instance_name):
        super(ModelDefinition, self).__init__(
            interface_instance_name, "urn:azureiot:ModelDiscovery:ModelDefinition:1"
        )
        self.get_model_definition = Command()


environmental_sensor = EnvironmentalSensor("environmentalSensor")
device_information = DeviceInformation("deviceInformation")
model_definition = ModelDefinition("urn_azureiot_ModelDiscovery_ModelDefinition")
exit_interface = SampleExit("urn_azureiotsdknode_SampleInterface_SampleExit")


# Note: this follows the method pattern from the pythonIoTHubDeviceClient object.
async def environmental_command_listener(interface):
    while True:
        command_request = await interface.receive_pnp_command()

        if command_request.command_name == "blink":
            print("Got the blink command")

            command_acknowledge = CommandAcknowledge.create_from_command_request(
                command_request, 200, "blink response"
            )
            try:
                await interface.send_command_acknowledge(command_acknowledge)
            except Exception:
                print("responding to the blink command failed")

        elif command_request.command_name == "turnOn":
            # copypasta
            pass
        elif command_request.command_name == "turnOff":
            # copypasta
            pass
        elif command_request.command_name == "runDiagnostics":
            print("Got the runDiagnostics command.")

            command_acknowledge = CommandAcknowledge.create_from_command_request(
                command_request, 200, "runDiagnostics response"
            )
            try:
                await interface.send_command_acknowledge(command_acknowledge)
            except Exception as e:
                print("responding to the runDiagnostics command failed: {}".format(e))
            else:
                command_update = CommandUpdate.create_from_command_request(
                    command_request, 200, "runDiagnostics update response"
                )
                try:
                    await interface.send_command_update(command_update)
                except Exception as e:
                    print("Got an error on the update: {}".format(e))


async def environmental_property_changed_listener(interface):
    while True:
        property_change = await interface.receive_property_change()
        property = getattr(interface, property_change.property_name, None)

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


async def model_definition_command_listener(interface):
    pass
    # copypasta


async def wait_for_exit_command_listener(interface):
    command_request = await interface.receive_pnp_command()
    print(
        "received command: "
        + command_request.command_name
        + " for interfaceInstance: "
        + command_request.interface_instance_name
    )
    command_acknowledge = CommandAcknowledge.create_from_command_request(command_request, 200, None)
    await interface.send_command_acknowledge(command_acknowledge)
    await asyncio.sleep(2)
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
            environmental_command_listener(environmental_sensor),
            environmental_property_changed_listener(environmental_sensor),
            model_definition_command_listener(model_definition),
        )
    )

    await environmental_sensor.state.report(True)
    await device_information.manufacturer.report("Contoso Device Corporation")
    await device_information.model.report("Contoso 4762B-turbo")
    await device_information.sw_version.report("3.1")
    await device_information.os_name.report("ContosoOS")
    await device_information.processor_architecture.report("4762")
    await device_information.processor_manufacturer.report("Contoso Foundries")
    await device_information.total_storage.report("64000")
    await device_information.total_memory.report("640")

    #  send telemetry every 5 seconds
    def send_telemetry():
        while True:
            await environmental_sensor.sendTelemetry(
                {"temp": 10 + random.random_int(0, 90), "humid": 1 + random.randint(0, 99)}
            )
            await asyncio.sleep(5)

    sender = asyncio.ensure_future(send_telemetry())

    await wait_for_exit_command_listener(exit_interface)

    await listeners.cancel()
    await sender.cancel()


if __name__ == "__main__":
    asyncio.run(main())

    # If using Python 3.6 or below, use the following code instead of asyncio.run(main()):
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(main())
    # loop.close()
