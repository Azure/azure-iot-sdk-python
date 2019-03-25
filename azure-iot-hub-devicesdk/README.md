# Azure IoT Hub Device SDK
The Azure IoT Hub Device SDK for Python provides functionality for communicating with the Azure IoT Hub for both Devices and Modules.

**Note that this SDK is currently in preview, and is subject to change.**

## Features
The SDK provides the following clients:
### Device Client
* Send telemetry messages to Azure IoT Hub
* Receive Cloud-to-Device (C2D) messages from the Azure IoT Hub
### Module Client
* Supports Azure IoT Edge Hub and Azure IoT Hub
* Send telemetry messages to a Hub or to another Module
* Receive Input messages from a Hub or other Modules

These clients are synchronous and communicate using the MQTT protocol

## Installation
We currently do not provide a binary distribution of our package, which means you'll have to clone the [Azure IoT Python SDKs Repository](https://github.com/Azure/azure-iot-sdk-python-preview) and manually install by running the following commands:
```
git clone https://github.com/Azure/azure-iot-sdk-python-preview.git
cd azure-iot-sdk-python-preview

pip install azure-iot-common
pip install azure-iot-hub-devicesdk
```

## Getting Started
The Device SDK provides client that let devices connect to an Azure IoT Hub instance. These clients needs to authenticate with IoT Hub,
and the easiest way to do that is using a device connection string which can be obtained from your Azure IoT Hub page in the [Azure Portal](https://portal.azure.com).

For detailed documentation that explains how to set up an Azure IoT Hub, please refer to the [Azure IoT Hub Documentation](https://docs.microsoft.com/en-us/azure/iot-hub/).


## Samples
Check out the [samples repository](https://github.com/Azure/azure-iot-sdk-python-preview/tree/master/azure-iot-hub-devicesdk/samples) for simple example code.

## Getting help and finding API docs

Our SDK makes use of docstrings which means you cand find API documentation directly through Python with use of the [help](https://docs.python.org/3/library/functions.html#help) command:


```python
>>> from azure.iot.hub.devicesdk import DeviceClient
>>> help(DeviceClient)
```
