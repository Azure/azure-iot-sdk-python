# Azure IoT Hub Provisioning Device Client SDK

## How to Install
```
pip install azure-iot-provisioning-device-client
```

Additionally, if running on Linux or OSX:

```
apt-get install libboost-python-dev
```

For best results, ensure that your version of boost is >= 1.58

## Feature List
Use this SDK to:

* Provision a connected device using an HSM security module (TPM or X509)

## User Guides
* Read the [Azure IoT Fundamentals][iot-fundamentals] guide to get an overview of what Azure IoT can do.
* Read the [Azure IoT Hub Device Provisioning Service][dps-doc] guide to understand how to enable zero-touch provisioning to IoT Hubs using this SDK.

## Examples
Please refer to our [sample repository][dps-device-samples] for examples of how to use the Azure IoT Hub Provisioning Device Client SDK.


[iot-fundamentals]: https://docs.microsoft.com/en-us/azure/iot-fundamentals/
[dps-doc]: https://docs.microsoft.com/en-us/azure/iot-dps/
[dps-device-samples]:https://github.com/Azure/azure-iot-sdk-python/tree/master/provisioning_device_client/samples
