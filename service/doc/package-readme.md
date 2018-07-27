# Azure IoT Hub Service Client SDK

## How to Install
```
pip install azure-iothub-service-client
```

Additionally, if running on Linux or OSX:

```
apt-get install libboost-python-dev
```

For best results, ensure that your version of boost is >= 1.58

## Feature List
Use this SDK to:

* Manage the Azure IoT Hub device identity registry (CRUD operations for devices)
* Send messages from the Azure IoT Hub to devices (C2D messages)
* Invoke Azure IoT Device Direct Methods
* Update Azure IoT Device Twins

## User Guides
* Read the [Azure IoT Fundamentals][iot-fundamentals] guide to get an overview of what Azure IoT can do.
* Read the [Azure IoT Hub][iothub-doc] guide to understand how to conduct service operations using this SDK.

## Examples
Please refer to our [sample repository][service-samples] for examples of how to use the Azure IoT Hub Service Client SDK.


[iot-fundamentals]: https://docs.microsoft.com/en-us/azure/iot-fundamentals/
[iothub-doc]: https://docs.microsoft.com/en-us/azure/iot-hub/
[service-samples]: https://github.com/Azure/azure-iot-sdk-python/tree/master/service/samples