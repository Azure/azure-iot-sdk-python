# Microsoft Azure IoT SDKs for Python

![Build Status](https://azure-iot-sdks.visualstudio.com/azure-iot-sdks/_apis/build/status/python/python-canary)

This repository contains the following:
* **Azure IoT Hub Device SDK for Python**: to connect client devices to Azure IoT Hub
* **Azure IoT Hub Service SDK for Python**: enables developing back-end applications for Azure IoT

To create and manage an instance of IoT Hub in your Azure subscription using Python, you can use the [Azure IoT Hub management library for Python][azure-iot-mgmt-lib]. Read more [here][azure-iot-mgmt-lib-doc].

To manage all your Azure resources using Python, you can leverate the [Azure CLI v2][azure-cli-v2].

To find SDKs in other languages for Azure IoT, please refer to the [azure-iot-sdks][azure-iot-sdks] repository.

## Developing applications for Azure IoT
Visit [Azure IoT Dev Center][iot-dev-center] to learn more about developing applications for Azure IoT.

## How to use the Azure IoT SDKs for Python
Devices and data sources in an IoT solution can range from a simple network-connected sensor to a powerful, standalone computing device. Devices may have limited processing capability, memory, communication bandwidth, and communication protocol support. The IoT device SDKs enable you to implement client applications for a wide variety of devices.
* **Using PyPI package on Windows, Linux (Ubuntu) or Raspberry Pi**: the simplest way to use the Azure IoT SDK for Python to develop device apps on Windows is to leverage the PyPI package which you can install following these [instructions][PyPI-install-instructions].
* **Clone the repository**: This repository uses [GitHub Submodules](https://git-scm.com/book/en/v2/Git-Tools-Submodules) for its dependencies. In order to automatically clone these submodules, you need to use the `--recursive` option as described here:
```
git clone --recursive https://github.com/Azure/azure-iot-sdk-python.git
```
If you have downloaded the zip instead of cloning the repository, you will need to run the following command to restore submodules:
```
git submodule update --init --recursive
```

* **Building the libraries and working with the SDK code**: follow [these instructions][devbox-setup].

## Key features and roadmap

### Device client SDK
:heavy_check_mark: feature available  :heavy_multiplication_x: feature planned but not supported  :heavy_minus_sign: no support planned


| Features                                                                                                         | mqtt                | mqtt-ws             | amqp                     | amqp-ws                  | https                    | Description                                                                                                                                                                                                                                                                                                       |
|------------------------------------------------------------------------------------------------------------------|---------------------|---------------------|--------------------------|--------------------------|--------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [Authentication](https://docs.microsoft.com/en-us/azure/iot-hub/iot-hub-security-deployment)                     | :heavy_check_mark:  | :heavy_check_mark:* | :heavy_check_mark:       | :heavy_check_mark:*      | :heavy_check_mark:*      | Connect your device to IoT Hub securely with supported authentication, including private key, SASToken, X-509 Self Signed and Certificate Authority (CA) Signed.  *IoT Hub only supports X-509 CA Signed over AMQP and MQTT at the moment.                                                                        |
| [Send device-to-cloud message](https://docs.microsoft.com/en-us/azure/iot-hub/iot-hub-devguide-messages-d2c)     | :heavy_check_mark:* | :heavy_check_mark:* | :heavy_check_mark:*      | :heavy_check_mark:*      | :heavy_check_mark:*      | Send device-to-cloud messages (max 256KB) to IoT Hub with the option to add custom properties.  IoT Hub only supports batch send over AMQP and HTTPS only at the moment.  This SDK supports batch send over HTTP.  * Batch send over AMQP and AMQP-WS, and add system properties on D2C messages are in progress. |
| [Receive cloud-to-device messages](https://docs.microsoft.com/en-us/azure/iot-hub/iot-hub-devguide-messages-c2d) | :heavy_check_mark:* | :heavy_check_mark:* | :heavy_check_mark:       | :heavy_check_mark:       | :heavy_check_mark:       | Receive cloud-to-device messages and read associated custom and system properties from IoT Hub, with the option to complete/reject/abandon C2D messages.  *IoT Hub supports the option to complete/reject/abandon C2D messages over HTTPS and AMQP only at the moment.                                            |
| [Device Twins](https://docs.microsoft.com/en-us/azure/iot-hub/iot-hub-devguide-device-twins)                     | :heavy_check_mark:* | :heavy_check_mark:* | :heavy_check_mark:*      | :heavy_check_mark:*      | :heavy_minus_sign:       | IoT Hub persists a device twin for each device that you connect to IoT Hub.  The device can perform operations like get twin tags, subscribe to desired properties.  *Send reported properties version and desired properties version are in progress.                                                            |
| [Direct Methods](https://docs.microsoft.com/en-us/azure/iot-hub/iot-hub-devguide-direct-methods)                 | :heavy_check_mark:  | :heavy_check_mark:  | :heavy_check_mark:       | :heavy_check_mark:       | :heavy_minus_sign:       | IoT Hub gives you the ability to invoke direct methods on devices from the cloud.  The SDK supports handler for method specific and generic operation.                                                                                                                                                            |
| [Upload file to Blob](https://docs.microsoft.com/en-us/azure/iot-hub/iot-hub-devguide-file-upload)               | :heavy_minus_sign:  | :heavy_minus_sign:  | :heavy_minus_sign:       | :heavy_minus_sign:       | :heavy_check_mark:       | A device can initiate a file upload and notifies IoT Hub when the upload is complete.   File upload requires HTTPS connection, but can be initiated from client using any protocol for other operations.                                                                                                          |
| [Connection Status and Error reporting](https://docs.microsoft.com/en-us/rest/api/iothub/common-error-codes)     | :heavy_check_mark:* | :heavy_check_mark:* | :heavy_check_mark:*      | :heavy_check_mark:*      | :heavy_multiplication_x: | Error reporting for IoT Hub supported error code.  *This SDK supports error reporting on authentication and Device Not Found.                                                                                                                                                                                 |
| Retry policies                                                                                                   | :heavy_check_mark:* | :heavy_check_mark:* | :heavy_check_mark:*      | :heavy_check_mark:*      | :heavy_multiplication_x: | Retry policy for unsuccessful device-to-cloud messages have two options: no try, exponential backoff with jitter (default).   *Custom retry policy is in progress.                                                                                                                                              |
| Devices multiplexing over single connection                                                                      | :heavy_minus_sign:  | :heavy_minus_sign:  | :heavy_check_mark:       | :heavy_check_mark:       | :heavy_check_mark:       |                                                                                                                                                                                                                                                                                                                   |
| Connection Pooling - Specifying number of connections                                                            | :heavy_minus_sign:  | :heavy_minus_sign:  | :heavy_multiplication_x: | :heavy_multiplication_x: | :heavy_multiplication_x: |                                                                                                                                                                                                                                                                                                                   |


### Service client SDK
:heavy_check_mark: feature available  :heavy_multiplication_x: feature planned but not supported  :heavy_minus_sign: no support planned

| Features                                                                                                      | Python             | Description                                                                                                                        |
|---------------------------------------------------------------------------------------------------------------|--------------------|------------------------------------------------------------------------------------------------------------------------------------|
| [Identity registry (CRUD)](https://docs.microsoft.com/en-us/azure/iot-hub/iot-hub-devguide-identity-registry) | :x:                | Use your backend app to perform CRUD operation for individual device or in bulk.                                                   |
| [Cloud-to-device messaging](https://docs.microsoft.com/en-us/azure/iot-hub/iot-hub-devguide-messages-c2d)     | :heavy_check_mark: | Use your backend app to send cloud-to-device messages in AMQP and AMQP-WS, and set up cloud-to-device message receivers.           |
| [Direct Methods operations](https://docs.microsoft.com/en-us/azure/iot-hub/iot-hub-devguide-direct-methods)   | :heavy_check_mark: | Use your backend app to invoke direct method on device.                                                                            |
| [Device Twins operations](https://docs.microsoft.com/en-us/azure/iot-hub/iot-hub-devguide-device-twins)       | :heavy_check_mark: | Use your backend app to perform device twin operations.  *Twin reported property update callback and replace twin are in progress. |
| [Query](https://docs.microsoft.com/en-us/azure/iot-hub/iot-hub-devguide-query-language)                       | :heavy_check_mark: | Use your backend app to perform query for information.                                                                             |
| [Jobs](https://docs.microsoft.com/en-us/azure/iot-hub/iot-hub-devguide-jobs)                                  | :x:                | Use your backend app to perform job operation.                                                                                     |
| [File Upload](https://docs.microsoft.com/en-us/azure/iot-hub/iot-hub-devguide-file-upload)                    | :x:                | Set up your backend app to send file upload notification receiver.                                                                 |

### Provisioning client SDK
This repository contains [provisioning device client SDK](./provisioning_device_client) for the [Device Provisioning Service](https://docs.microsoft.com/en-us/azure/iot-dps/).  Provisioning service SDK for Python is work in progress.  Please see provisoning service SDK in [Node.js](https://github.com/Azure/azure-iot-sdk-node), [Java](https://github.com/Azure/azure-iot-sdk-java) and [.NET](https://github.com/Azure/azure-iot-sdk-csharp) in the meantime.

:heavy_check_mark: feature available  :heavy_multiplication_x: feature planned but not supported  :heavy_minus_sign: no support planned

| Features                    | mqtt               | mqtt-ws            | amqp               | amqp-ws            | https              | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
|-----------------------------|--------------------|--------------------|--------------------|--------------------|--------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| TPM Individual Enrollment   | :heavy_minus_sign: | :heavy_minus_sign: | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: | This SDK supports connecting your device to the Device Provisioning Service via [individual enrollment](https://docs.microsoft.com/en-us/azure/iot-dps/concepts-service#enrollment) using [Trusted Platform Module](https://docs.microsoft.com/en-us/azure/iot-dps/concepts-security#trusted-platform-module-tpm).  Please review the [samples](./provisioning_device_client/samples/) folder and this [quickstart](https://docs.microsoft.com/en-us/azure/iot-dps/quick-create-simulated-device-tpm-python)on how to create a device client. TPM over MQTT is currently not supported by the Device Provisioning Service.                                                                                                                                                                                                       |
| X.509 Individual Enrollment | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: | This SDK supports connecting your device to the Device Provisioning Service via [individual enrollment](https://docs.microsoft.com/en-us/azure/iot-dps/concepts-service#enrollment) using [X.509 root certificate](https://docs.microsoft.com/en-us/azure/iot-dps/concepts-security#root-certificate).  Please review the [samples](./provisioning_device_client/samples/) folder and this [quickstart](https://docs.microsoft.com/en-us/azure/iot-dps/quick-create-simulated-device-x509-python) on how to create a device client.  |
| X.509 Enrollment Group      | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: | This SDK supports connecting your device to the Device Provisioning Service via [individual enrollment](https://docs.microsoft.com/en-us/azure/iot-dps/concepts-service#enrollment) using [X.509 leaf certificate](https://docs.microsoft.com/en-us/azure/iot-dps/concepts-security#leaf-certificate)).  Please review the [samples](./provisioning_device_client/samples/) folder on how to create a device client.                                                                                                                                                                                          |



## Samples
This repository contains various Python sample applications that illustrate how to use the Microsoft Azure IoT SDKs for Python.
* [Device SDK samples][device-samples]
* [Service SDK samples][service-samples]

## Contribution, feedback and issues
If you encounter any bugs, have suggestions for new features or if you would like to become an active contributor to this project please follow the instructions provided in the [contribution guidelines](.github/CONTRIBUTING.md).

## Support
* Have a feature request for SDKs? Please post it on [User Voice](https://feedback.azure.com/forums/321918-azure-iot) to help us prioritize.
* Have a technical question? Ask on [Stack Overflow](https://stackoverflow.com/questions/tagged/azure-iot-hub) with tag "azure-iot-hub".
* Need Support? Every customer with an active Azure subscription has access to [support](https://docs.microsoft.com/en-us/azure/azure-supportability/how-to-create-azure-support-request) with guaranteed response time.  Consider submitting a ticket and get assistance from Microsoft support team
* Found a bug? Please help us fix it by thoroughly documenting it and filing an issue on GitHub ([C](https://github.com/Azure/azure-iot-sdk-c), [Java](https://github.com/Azure/azure-iot-sdk-java), [.NET](https://github.com/Azure/azure-iot-sdk-csharp), [Node.js](https://github.com/Azure/azure-iot-sdk-node), [Python](https://github.com/Azure/azure-iot-sdk-python)).

## Read more
* [Azure IoT Hub documentation][iot-hub-documentation]
* [Prepare your development environment to use the Azure IoT device SDK for C][devbox-setup]
* [Setup IoT Hub][setup-iothub]

## SDK folder structure

### /build_all

This folder contains platform-specific build scripts for the client libraries and dependent components.

### /device

Contains Azure IoT Hub client components that provide the raw messaging capabilities of the library. Refer to the API documentation and samples for information on how to use it.

### /doc

This folder contains application development guides and device setup instructions.

### /jenkins
This folder contains scripts to build and run Python SDK provided proper environmental variables are set


### /service

Contains libraries that enable interactions with the IoT Hub service to perform operations such as sending messages to devices and managing the device identity registry.

# Long Term Support

The project offers a Long Term Support (LTS) version to allow users that do not need the latest features to be shielded from unwanted changes.

A new LTS version will be created every 6 months. The lifetime of an LTS branch is currently planned for one year. LTS branches receive all bug fixes that fall in one of these categories:

- security bugfixes
- critical bugfixes (crashes, memory leaks, etc.)

No new features or improvements will be picked up in an LTS branch.

LTS branches are named lts_*mm*_*yyyy*, where *mm* and *yyyy* are the month and year when the branch was created. An example of such a branch is *lts_07_2017*.

## Schedule<sup>1</sup>

Below is a table showing the mapping of the LTS branches to the packages released

| PIP Package   | Github Branch | LTS Status | LTS Start Date | Maintenance End Date | Removed Date |
| :-----------: | :-----------: | :--------: | :------------: | :------------------: | :----------: |
| azure-iothub-device-client: 1.2.3<br/> azure-iothub-service-client: 1.2.3<br/>  azure-iothub-provisioningserviceclient: 1.0.0         | lts_01_2018   | Active     | 2018-01-01     | 2018-06-30           | 2018-12-31   |
| 1.x.x         | lts_07_2017   | Deprecated | 2017-07-01     | 2017-12-31           | 2018-06-30   |

* <sup>1</sup> All scheduled dates are subject to change by the Azure IoT SDK team.

### Planned Release Schedule
![](./lts_branches.png)

---
This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/). For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

[iot-dev-center]: http://azure.com/iotdev
[iot-hub-documentation]: https://docs.microsoft.com/en-us/azure/iot-hub/
[azure-iot-sdks]: http://github.com/azure/azure-iot-sdks
[PyPI-install-instructions]: doc/python-devbox-setup.md#windows-wheels
[setup-iothub]: https://aka.ms/howtocreateazureiothub
[devbox-setup]: doc/python-devbox-setup.md
[device-samples]: device/samples/
[service-samples]: service/samples/
[azure-iot-mgmt-lib]: https://pypi.python.org/pypi/azure-mgmt-iothub
[azure-iot-mgmt-lib-doc]: http://azure-sdk-for-python.readthedocs.io/en/latest/sample_azure-mgmt-iothub.html
[azure-cli-v2]: https://github.com/Azure/azure-cli
