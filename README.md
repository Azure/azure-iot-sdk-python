#
<div align=center>
    <img src="./doc/images/azure_iot_sdk_python_banner.png"></img>
    <h1> azure-iot-device </h1>
</div>

![Build Status](https://azure-iot-sdks.visualstudio.com/azure-iot-sdks/_apis/build/status/Azure.azure-iot-sdk-python)

The Azure IoT Device SDK for Python enables Python developers to easily create IoT device solutions that seamlessly connect to the Azure IoT Hub ecosystem.

* *If you're migrating v2.x.x code to use v3.x.x check the [IoT Hub Migration Guide](https://github.com/Azure/azure-iot-sdk-python/blob/main/migration_guide_iothub.md) and/or the [Provisioning Migration Guide](https://github.com/Azure/azure-iot-sdk-python/blob/main/migration_guide_provisioning.md)*

* *If you're looking for the v2.x.x client library, it is now preserved in the [v2](https://github.com/Azure/azure-iot-sdk-python/tree/v2) branch*

* *If you're looking for the v1.x.x client library, it is now preserved in the [v1-deprecated](https://github.com/Azure/azure-iot-sdk-python/tree/v1-deprecated) branch.*

* *If you're looking for the azure-iot-hub library, it is now located in the [azure-iot-hub-python](https://github.com/Azure/azure-iot-hub-python) repository*

**NOTE: 3.x.x is still in beta and APIs are subject to change until the release of 3.0.0**


## Installing the library

The Azure IoT Device library is available on PyPI:

```Shell
pip install azure-iot-device==3.0.0b2
```

Python 3.7 or higher is required in order to use the library


## Using the library
You can view the [**samples repository**](https://github.com/Azure/azure-iot-sdk-python/tree/main/samples) to see examples of SDK usage.

Full API documentation for this package is available via [**Microsoft Docs**](https://docs.microsoft.com/python/api/azure-iot-device/azure.iot.device?view=azure-python). Note that this documentation may currently be out of date as v3.x.x is still in preview at the time of this writing.

You can use the [**Connection Diagnostic Tool**](https://github.com/Azure/azure-iot-connection-diagnostic-tool) to help ascertain the cause of any connection issues you run into when using the SDK.

## Features

:heavy_check_mark: feature available  :heavy_multiplication_x: feature planned but not yet supported  :heavy_minus_sign: no support planned*

*Features that are not planned may be prioritized in a future release, but are not currently planned

This library primarily uses the **MQTT protocol**.

### IoTHubSession

| Features                                                                                                         | Status                     | Description                                                                                                                                                                                                          |
|------------------------------------------------------------------------------------------------------------------|----------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [Authentication](https://docs.microsoft.com/en-us/azure/iot-hub/iot-hub-security-deployment)                     | :heavy_check_mark:         | Connect your device to IoT Hub securely with supported authentication, including symmetric key, X-509 Self Signed, Certificate Authority (CA) Signed, and SASToken                                     |
| [Send device-to-cloud message](https://docs.microsoft.com/en-us/azure/iot-hub/iot-hub-devguide-messages-d2c)     | :heavy_check_mark:         | Send device-to-cloud messages (max 256KB) to IoT Hub with the option to add custom properties.                                                                                                                       |
| [Receive cloud-to-device messages](https://docs.microsoft.com/en-us/azure/iot-hub/iot-hub-devguide-messages-c2d) | :heavy_check_mark:         | Receive cloud-to-device messages and read associated custom and system properties from IoT Hub.                                                        |
| [Device Twins](https://docs.microsoft.com/en-us/azure/iot-hub/iot-hub-devguide-device-twins)                     | :heavy_check_mark:         | IoT Hub persists a device twin for each device that you connect to IoT Hub.  The device can perform operations like get twin tags, subscribe to desired properties.                                                |
| [Direct Methods](https://docs.microsoft.com/en-us/azure/iot-hub/iot-hub-devguide-direct-methods)                 | :heavy_check_mark:         | IoT Hub gives you the ability to invoke direct methods on devices from the cloud.  The SDK supports handler for method specific and generic operation.                                                            |
| [Connection Status and Error reporting](https://docs.microsoft.com/en-us/rest/api/iothub/common-error-codes)     | :heavy_check_mark:         | Error reporting for IoT Hub supported error code.                                                                                         |
| Connection Retry                                                                                                 | :heavy_check_mark:         | Dropped connections will be retried with a fixed 10 second interval by default. This functionality can be disabled if desired, and the interval can be configured   |
| [Upload file to Blob](https://docs.microsoft.com/en-us/azure/iot-hub/iot-hub-devguide-file-upload)               | :heavy_multiplication_x:   | A device can initiate a file upload and notifies IoT Hub when the upload is complete.  |
| Direct Invocation of Method on Modules                                                                           | :heavy_multiplication_x:   | Invoke method calls to another module using using the Edge Gateway.         


### ProvisioningSession

| Features                    | Status                   | Description                                                                                                                                                                                                                                                                                                                                        |
|-----------------------------|--------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| TPM Individual Enrollment   | :heavy_multiplication_x: | Provisioning via [Trusted Platform Module](https://docs.microsoft.com/en-us/azure/iot-dps/concepts-security#trusted-platform-module-tpm).                                                                                                                                                                                                          |
| X.509 Individual Enrollment | :heavy_check_mark:       | Provisioning via [X.509 root certificate](https://docs.microsoft.com/en-us/azure/iot-dps/concepts-security#root-certificate).  Please review the [samples](azure-iot-device/samples/async-hub-scenarios/provision_x509.py) folder and this [quickstart](https://docs.microsoft.com/en-us/azure/iot-dps/quick-create-simulated-device-x509-python) on how to create a device client.   |
| X.509 Enrollment Group      | :heavy_check_mark:       | Provisioning via [X.509 leaf certificate](https://docs.microsoft.com/en-us/azure/iot-dps/concepts-security#leaf-certificate)).  Please review the [samples](azure-iot-device/samples/async-hub-scenarios/provision_x509.py) folder on how to create a device client.                                                                                                                  |
| Symmetric Key Enrollment    | :heavy_check_mark:       | Provisioning via [Symmetric key attestation](https://docs.microsoft.com/en-us/azure/iot-dps/concepts-symmetric-key-attestation)).  Please review the [samples](azure-iot-device/samples/async-hub-scenarios/provision_symmetric_key.py) folder on how to create a device client.                                                                                                               |


## Contributing

This project welcomes contributions and suggestions.  Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit https://cla.microsoft.com.

When you submit a pull request, a CLA-bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., label, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.
