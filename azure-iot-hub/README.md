# Azure IoTHub Service  SDK

The Azure IoTHub Service SDK for Python provides functionality for communicating with the Azure IoT Hub.

**Note that this SDK is currently in preview, and is subject to change.**

## Features

The SDK provides the following clients:

* ### IoT Hub Registry Manager

  * Provides CRUD operations for device on IoTHub
  * Get statistics about the IoTHub service and devices

These clients are available with an asynchronous API, as well as a blocking synchronous API for compatibility scenarios. **We recommend you use Python 3.7+ and the asynchronous API.**

| Python Version | Synchronous API |
| -------------- | --------------- |
| Python 3.5.3+  | **YES**         |
| Python 3.4     | **YES**         |
| Python 2.7     | **YES**         |

## Installation

```python
pip install azure-iot-hub
```

## Set up an IoT Hub

1. Install the [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli?view=azure-cli-latest) (or use the [Azure Cloud Shell](https://shell.azure.com/)) and use it to [create an Azure IoT Hub](https://docs.microsoft.com/en-us/cli/azure/iot/hub?view=azure-cli-latest#az-iot-hub-create).

```bash
az iot hub create --resource-group <your resource group> --name <your IoT Hub name>
```

* Note that this operation make take a few minutes.

## How to use the IoTHub Registry Manager

* ### Create an IoTHubRegistryManager

```python
registry_manager = IoTHubRegistryManager(iothub_connection_str)
```

* ### Create a device

```python
new_device = registry_manager.create_device_with_sas(device_id, primary_key, secondary_key, device_state)
```

* ### Read device information

```python
device = registry_manager.get_device(device_id)
```

* ### Update device information

```python
device_updated = registry_manager.update_device_with_sas(
    device_id, etag, primary_key, secondary_key, device_state)
```

* ### Delete device

```python
registry_manager.delete_device(device_id)
```

* ### Get service statistics

```python
registry_statistics = registry_manager.get_service_statistics()
```

* ### Get device registry statistics

```python
registry_statistics = registry_manager.get_device_registry_statistics()
```

## IoTHub Samples

Check out the [samples repository](https://github.com/Azure/azure-iot-sdk-python/tree/master/azure-iot-hub/samples) for more detailed samples

## Getting help and finding API docs

Our SDK makes use of docstrings which means you can find API documentation directly through Python with use of the [help](https://docs.python.org/3/library/functions.html#help) command:

```python
>>> from azure.iot.hub import IoTHubRegistryManager
>>> help(IoTHubRegistryManager)
```
