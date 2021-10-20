# Azure IoTHub Service  SDK

The Azure IoTHub Service SDK for Python provides functionality for communicating with the Azure IoT Hub.

## Features

The SDK provides the following clients:

* ### IoT Hub Registry Manager

  * Provides CRUD operations for device on IoTHub
  * Get statistics about the IoTHub service and devices

## Installation

```python
pip install azure-iot-hub
```

**DEPRECATION NOTICE: SUPPORT FOR PYTHON 2.7 WILL BE DROPPED AT THE BEGINNING OF 2022**

## IoTHub Samples

Check out the [samples repository](https://github.com/Azure/azure-iot-sdk-python/tree/master/azure-iot-hub/samples) for more detailed samples

## Getting help and finding API docs


API documentation for this package is available via [Microsoft Docs](https://docs.microsoft.com/python/api/azure-iot-hub/azure.iot.hub?view=azure-python)

Additionally, the SDK makes use of docstrings which means you can find API documentation directly through Python with use of the [help](https://docs.python.org/3/library/functions.html#help) command:

```python
>>> from azure.iot.hub import IoTHubRegistryManager
>>> help(IoTHubRegistryManager)
```
