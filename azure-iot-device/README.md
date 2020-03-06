# Azure IoT Device SDK

The Azure IoT Device SDK for Python provides functionality for communicating with the Azure IoT Hub for both Devices and Modules.

## Azure IoT Device Features

The SDK provides the following clients:

* ### Provisioning Device Client

  * Creates a device identity on the Azure IoT Hub

* ### IoT Hub Device Client

  * Send telemetry messages to Azure IoT Hub
  * Receive Cloud-to-Device (C2D) messages from the Azure IoT Hub
  * Receive and respond to direct method invocations from the Azure IoT Hub

* ### IoT Hub Module Client

  * Supports Azure IoT Edge Hub and Azure IoT Hub
  * Send telemetry messages to a Hub or to another Module
  * Receive Input messages from a Hub or other Modules
  * Receive and respond to direct method invocations from a Hub or other Modules

These clients are available with an asynchronous API, as well as a blocking synchronous API for compatibility scenarios. **We recommend you use Python 3.7+ and the asynchronous API.**

| Python Version | Asynchronous API | Synchronous API |
| -------------- | ---------------- | --------------- |
| Python 3.5.3+  | **YES**          | **YES**         |
| Python 2.7     | NO               | **YES**         |

## Installation

```Shell
pip install azure-iot-device
```

## Device Samples

Check out the [samples repository](./azure-iot-device/samples) for example code showing how the SDK can be used in a variety of scenarios, including:

* Sending multiple telemetry messages at once.
* Receiving Cloud-to-Device messages.
* Using Edge Modules with the Azure IoT Edge Hub.
* Send and receive updates to device twin
* Receive invocations to direct methods
* Register a device with the Device Provisioning Service

## Getting help and finding API docs

Our SDK makes use of docstrings which means you cand find API documentation directly through Python with use of the [help](https://docs.python.org/3/library/functions.html#help) command:

```python
>>> from azure.iot.device import IoTHubDeviceClient
>>> help(IoTHubDeviceClient)
```
