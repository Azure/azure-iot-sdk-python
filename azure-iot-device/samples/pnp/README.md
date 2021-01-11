# Samples to demonstrate Azure IoT Plug and Play

The samples in this directory demonstrate how to implement an Azure IoT Plug and Play device.  Azure IoT Plug and Play is documented [here](aka.ms/iotpnp).  The samples assume basic familiarity with Plug and Play concepts, though not in depth knowledge of the Plug and Play "convention".  The "convention" is a set of rules for serializing and de-serialing data that uses IoTHub primitives for transport which the samples themselves implement.

## Directory structure

The directory contains the following samples:

* [simple_thermostat](https://github.com/Azure/azure-iot-sdk-python/blob/master/azure-iot-device/samples/pnp/simple_thermostat.py) A simple thermostat that implements the model [dtmi:com:example:Thermostat;1](https://github.com/Azure/iot-plugandplay-models/blob/main/dtmi/com/example/thermostat-1.json).  This sample is considered simple because it only implements one component, the thermostat itself.  **You should begin with this sample.**

* [temperature_controller](https://github.com/Azure/azure-iot-sdk-python/blob/master/azure-iot-device/samples/pnp/temp_controller_with_thermostats.py) A temperature controller that implements the model [dtmi:com:example:TemperatureController;2](https://github.com/Azure/iot-plugandplay-models/blob/main/dtmi/com/example/temperaturecontroller-2.json).  This is considrably more complex than the [simple_thermostat](./simple_thermostat) and demonstrates the use of sub components.  **You should move onto this sample only after fully understanding simple_thermostat.**

## Configuring the samples

Both samples use environment variables to retrieve configuration.

* If you are using a connection string to authenticate:
  * set IOTHUB_DEVICE_SECURITY_TYPE="connectionString"
  * set IOTHUB_DEVICE_CONNECTION_STRING="\<connection string of your device\>"

* If you are using a DPS enrollment group to authenticate:
  * set IOTHUB_DEVICE_SECURITY_TYPE="DPS"
  * set IOTHUB_DEVICE_DPS_ID_SCOPE="\<ID Scope of DPS instance\>"
  * set IOTHUB_DEVICE_DPS_DEVICE_ID="\<Device's ID\>"
  * set IOTHUB_DEVICE_DPS_DEVICE_KEY="\<Device's security key \>"
  * set IOTHUB_DEVICE_DPS_ENDPOINT="\<DPS endpoint\>"

## Caveats

* Azure IoT Plug and Play is only supported for MQTT and MQTT over WebSockets for the Azure IoT Python Device SDK.  Modifying these samples to use AMQP, AMQP over WebSockets, or HTTP protocols **will not work**.

* When the thermostat receives a desired temperature, it has no actual affect on the current temperature.

* The command `getMaxMinReport` allows the application to specify statistics of the temperature since a given date.  To keep the sample simple, we ignore this field and instead return statistics from the some portion of the lifecycle of the executable.

* The temperature controller implements a command named `reboot` which takes a request payload indicating the delay in seconds.  The sample will ignore doing anything on this command.
