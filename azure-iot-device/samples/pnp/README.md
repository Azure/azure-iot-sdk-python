---
page_type: sample
description: "A set of Python samples that show how a device that uses the IoT Plug and Play conventions interacts with either IoT Hub or IoT Central."
languages:
- python
products:
- azure-iot-hub
- azure-iot-central
- azure-iot-pnp
urlFragment: azure-iot-pnp-device-samples-for-python
---

# IoT Plug And Play device samples

[![Documentation](../../doc/images/docs-link-buttons/azure-documentation.svg)](https://docs.microsoft.com/azure/iot-develop/)

These samples demonstrate how a device that follows the [IoT Plug and Play conventions](https://docs.microsoft.com/azure/iot-pnp/concepts-convention) interacts with IoT Hub or IoT Central, to:

- Send telemetry.
- Update read-only and read-write properties.
- Respond to command invocation.

The samples demonstrate two scenarios:

- An IoT Plug and Play device that implements the [Thermostat](https://devicemodels.azure.com/dtmi/com/example/thermostat-1.json) model. This model has a single interface that defines telemetry, read-only and read-write properties, and commands.
- An IoT Plug and Play device that implements the [Temperature controller](https://devicemodels.azure.com/dtmi/com/example/temperaturecontroller-2.json) model. This model uses multiple components:
  - The top-level interface defines telemetry, read-only property and commands.
  - The model includes two [Thermostat](https://devicemodels.azure.com/dtmi/com/example/thermostat-1.json) components, and a [device information](https://devicemodels.azure.com/dtmi/azure/devicemanagement/deviceinformation-1.json) component.

## Quickstarts and tutorials

To learn more about how to configure and run the Thermostat device sample with IoT Hub, see [Quickstart: Connect a sample IoT Plug and Play device application running on Linux or Windows to IoT Hub](https://docs.microsoft.com/azure/iot-pnp/quickstart-connect-device?pivots=programming-language-python).

To learn more about how to configure and run the Temperature Controller device sample with:

- IoT Hub, see [Tutorial: Connect an IoT Plug and Play multiple component device application running on Linux or Windows to IoT Hub](https://docs.microsoft.com/azure/iot-pnp/tutorial-multiple-components?pivots=programming-language-python)
- IoT Central, see [Tutorial: Create and connect a client application to your Azure IoT Central application](https://docs.microsoft.com/azure/iot-central/core/tutorial-connect-device?pivots=programming-language-python)

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
