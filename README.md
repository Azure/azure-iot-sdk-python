# Azure IoT Hub Python SDKs v2 - PREVIEW

![Build Status](https://azure-iot-sdks.visualstudio.com/azure-iot-sdks/_apis/build/status/Azure.azure-iot-sdk-python)

This repository contains code for the Azure IoT SDKs for Python.  This enables python developers to easily create IoT devices that work semealessly 

*If you're looking for the v1.x.x client library, it is now preserved in the [v1-deprecated](https://github.com/Azure/azure-iot-sdk-python/tree/v1-deprecated) branch.*

**Note that these SDKs are currently in preview, and are subject to change.**

## Python SDK

This repository contains the following:

* *Azure IoT Device SDK*

  * Send/receive telemetry between a device or module and the Azure IoT hub or Azure IoT Edge device
  * Handle direct methods invoked by the Azure IoT hub on a device
  * Handle twin events and report twin updates
  * *Still in development*
    * *Blob/File upload*
    * *Invoking method from a module client onto a leaf device*

* Azure IoT Hub SDK
  * Do service/management operations on the Azure IoT Hub
  * *Still in development*
    * C2D messaging
    * Direct Methods
    * Configurations
    * Query devices
    * IoTHub Job

* Azure IoT Hub Provisioning SDK
  * Provision a device using the Device Provisioning Service for use with the Azure IoT hub
  * Do service/management operations on the Azure IoT Device Provisioning Service

## How to install the SDKs

The SDK is contained in various Pip Packages that can be installed with the following commands:

For the Device SDK the following command:

```Shell
pip install azure-iot-device
```

For the IoTHub SDK the following command:

```Shell
pip install azure-iot-hub
```

## Python SDKs Feature

:heavy_check_mark: feature available  :heavy_multiplication_x: feature planned but not yet supported  :heavy_minus_sign: no support planned*

*Features that are not planned may be prioritized in a future release, but are not currently in our 6 short term plans

### Device client SDK

| Features                                                                                                         | mqtt                       | mqtt-ws                   | https                    | Description                                                                                                                                                                                                          |
|------------------------------------------------------------------------------------------------------------------|----------------------------|---------------------------|--------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [Authentication](https://docs.microsoft.com/en-us/azure/iot-hub/iot-hub-security-deployment)                     | :heavy_check_mark:         | :heavy_check_mark:        | :heavy_minus_sign:       | Connect your device to IoT Hub securely with supported authentication, including private key, SASToken, X-509 Self Signed and Certificate Authority (CA) Signed.                                                     |
| [Send device-to-cloud message](https://docs.microsoft.com/en-us/azure/iot-hub/iot-hub-devguide-messages-d2c)     | :heavy_check_mark:         | :heavy_check_mark:        | :heavy_minus_sign:       | Send device-to-cloud messages (max 256KB) to IoT Hub with the option to add custom properties.                                                                                                                       |
| [Receive cloud-to-device messages](https://docs.microsoft.com/en-us/azure/iot-hub/iot-hub-devguide-messages-c2d) | :heavy_check_mark:         | :heavy_check_mark:        | :heavy_minus_sign:       | Receive cloud-to-device messages and read associated custom and system properties from IoT Hub, with the option to complete/reject/abandon C2D messages.                                                             |
| [Device Twins](https://docs.microsoft.com/en-us/azure/iot-hub/iot-hub-devguide-device-twins)                     | :heavy_check_mark:         | :heavy_check_mark:        | :heavy_minus_sign:       | IoT Hub persists a device twin for each device that you connect to IoT Hub.  The device can perform operations like get twin tags, subscribe to desired properties.                                                  |
| [Direct Methods](https://docs.microsoft.com/en-us/azure/iot-hub/iot-hub-devguide-direct-methods)                 | :heavy_check_mark:         | :heavy_check_mark:        | :heavy_minus_sign:       | IoT Hub gives you the ability to invoke direct methods on devices from the cloud.  The SDK supports handler for method specific and generic operation.                                                               |
| [Upload file to Blob](https://docs.microsoft.com/en-us/azure/iot-hub/iot-hub-devguide-file-upload)               | :heavy_multiplication_x:   | :heavy_multiplication_x:  | :heavy_minus_sign:       | A device can initiate a file upload and notifies IoT Hub when the upload is complete.   File upload requires HTTPS connection, but can be initiated from client using any protocol for other operations.             |
| [Connection Status and Error reporting](https://docs.microsoft.com/en-us/rest/api/iothub/common-error-codes)     | :heavy_multiplication_x:   | :heavy_multiplication_x:  | :heavy_multiplication_x: | Error reporting for IoT Hub supported error code.  *This SDK supports error reporting on authentication and Device Not Found.                                                                                        |
| Retry policies                                                                                                   | :heavy_check_mark:         | :heavy_check_mark:        | :heavy_minus_sign:       | Retry policy for unsuccessful device-to-cloud messages.                                                                                                                                                              |

### IoTHub client SDK

| Features                                                                                                      | Python                   | Description                                                                                                                        |
|---------------------------------------------------------------------------------------------------------------|--------------------------|------------------------------------------------------------------------------------------------------------------------------------|
| [Identity registry (CRUD)](https://docs.microsoft.com/en-us/azure/iot-hub/iot-hub-devguide-identity-registry) | :heavy_check_mark:       | Use your backend app to perform CRUD operation for individual device or in bulk.                                                   |
| [Cloud-to-device messaging](https://docs.microsoft.com/en-us/azure/iot-hub/iot-hub-devguide-messages-c2d)     | :heavy_multiplication_x: | Use your backend app to send cloud-to-device messages, and set up cloud-to-device message receivers.                               |
| [Direct Methods operations](https://docs.microsoft.com/en-us/azure/iot-hub/iot-hub-devguide-direct-methods)   | :heavy_multiplication_x: | Use your backend app to invoke direct method on device.                                                                            |
| [Device Twins operations](https://docs.microsoft.com/en-us/azure/iot-hub/iot-hub-devguide-device-twins)       | :heavy_multiplication_x: | Use your backend app to perform device twin operations.  *Twin reported property update callback and replace twin are in progress. |
| [Query](https://docs.microsoft.com/en-us/azure/iot-hub/iot-hub-devguide-query-language)                       | :heavy_multiplication_x: | Use your backend app to perform query for information.                                                                             |
| [Jobs](https://docs.microsoft.com/en-us/azure/iot-hub/iot-hub-devguide-jobs)                                  | :heavy_multiplication_x: | Use your backend app to perform job operation.                                                                                     |

### Provisioning client SDK

This repository contains provisioning device client SDK for the [Device Provisioning Service](https://docs.microsoft.com/en-us/azure/iot-dps/).  Provisioning service SDK for Python is work in progress.

:heavy_check_mark: feature available  :heavy_multiplication_x: feature planned but not supported  :heavy_minus_sign: no support planned

| Features                    | mqtt               | mqtt-ws            | https              | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
|-----------------------------|--------------------|--------------------|--------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| TPM Individual Enrollment   | :heavy_minus_sign: | :heavy_minus_sign: | :heavy_minus_sign: | This SDK supports connecting your device to the Device Provisioning Service via [individual enrollment](https://docs.microsoft.com/en-us/azure/iot-dps/concepts-service#enrollment) using [Trusted Platform Module](https://docs.microsoft.com/en-us/azure/iot-dps/concepts-security#trusted-platform-module-tpm).  Please review the [samples](./azure-iot-device/samples/) folder and this [quickstart](https://docs.microsoft.com/en-us/azure/iot-dps/quick-create-simulated-device-tpm-python)on how to create a device client.    |
| X.509 Individual Enrollment | :heavy_check_mark: | :heavy_check_mark: | :heavy_minus_sign: | This SDK supports connecting your device to the Device Provisioning Service via [individual enrollment](https://docs.microsoft.com/en-us/azure/iot-dps/concepts-service#enrollment) using [X.509 root certificate](https://docs.microsoft.com/en-us/azure/iot-dps/concepts-security#root-certificate).  Please review the [samples](./azure-iot-device/samples/) folder and this [quickstart](https://docs.microsoft.com/en-us/azure/iot-dps/quick-create-simulated-device-x509-python) on how to create a device client.              |
| X.509 Enrollment Group      | :heavy_check_mark: | :heavy_check_mark: | :heavy_minus_sign: | This SDK supports connecting your device to the Device Provisioning Service via [group enrollment](https://docs.microsoft.com/en-us/azure/iot-dps/concepts-service#enrollment) using [X.509 leaf certificate](https://docs.microsoft.com/en-us/azure/iot-dps/concepts-security#leaf-certificate)).  Please review the [samples](./azure-iot-device/samples/) folder on how to create a device client.                                                                                                                                  |
| Symmetric Key Enrollment    | :heavy_check_mark: | :heavy_check_mark: | :heavy_minus_sign: | This SDK supports connecting your device to the Device Provisioning Service via [individual enrollment](https://docs.microsoft.com/en-us/azure/iot-dps/concepts-service#enrollment) using [Symmetric key attestation](https://docs.microsoft.com/en-us/azure/iot-dps/concepts-symmetric-key-attestation)).  Please review the [samples](./azure-iot-device/samples/) folder on how to create a device client.                                                                                                                          |

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
