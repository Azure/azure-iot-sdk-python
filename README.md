![Build Status](https://azure-iot-sdks.visualstudio.com/azure-iot-sdks/_apis/build/status/python/python-preview)

# Azure IoT Hub Python SDKs v2 - PREVIEW

This repository contains the code for the future v2.0.0 of the Azure IoT SDKs for Python. The goal of v2.0.0 is to be a complete rewrite of the existing SDK that maximizes the use of the Python language and its standard features rather than wrap over the C SDK, like v1.x.x of the SDK did.

*If you're looking for the v1.x.x client library, it is now preserved in the [v1-deprecated](https://github.com/Azure/azure-iot-sdk-python/tree/v1-deprecated) branch.*

**Note that these SDKs are currently in preview, and are subject to change.**

# SDKs

This repository contains the following SDKs:

* [Azure IoT Device SDK](azure-iot-device) - /azure-iot-device
    * Provision a device using the Device Provisioning Service for use with the Azure IoT hub
    * Send/receive telemetry between a device or module and the Azure IoT hub or Azure IoT Edge device
    * Handle direct methods invoked by the Azure IoT hub on a device
    * Handle twin events and report twin updates
    * *Still in development*
        - *Blob/File upload*
        - *Invoking method from a module client onto a leaf device*

* Azure IoT Hub SDK **(COMING SOON)**
    * Do service/management operations on the Azure IoT Hub

* Azure IoT Hub Provisioning SDK **(COMING SOON)**
    * Do service/management operations on the Azure IoT Device Provisioning Service

# How to install the SDKs

```
pip install azure-iot-device
```

# Contributing

This project welcomes contributions and suggestions.  Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit https://cla.microsoft.com.

When you submit a pull request, a CLA-bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., label, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.
