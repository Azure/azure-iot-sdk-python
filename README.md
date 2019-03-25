![Build Status](https://azure-iot-sdks.visualstudio.com/azure-iot-sdks/_apis/build/status/python/python-preview)

# Azure IoT Hub Python SDKs v2 - PREVIEW

This repository contains the code for the future v2.0.0 of the Azure IoT SDKs for Python. The goal of v2.0.0 is to be a complete rewrite of the existing SDK that maximizes the use of the Python language and its standard features rather than wrap over the C SDK, like v1.x.x of the SDK did.

# How to install the SDKs

There are currently no preview packages released on pip. The only way to install the SDKs is to clone the repository and install manually with pip.

1. Clone the repository
    ```
    git clone https://github.com/Azure/azure-iot-sdk-python-preview.git
    cd azure-iot-sdk-python-preview
    ```

2. Install manually
    ```
    pip install azure-iot-common
    pip install azure-iot-hub-devicesdk
    ```
    Alternatively, to install all SDKs you can use the convenience script in the directory root.
    ```
    python env_setup.py --no_dev
    ```

# How to use the SDKs

For details on how to use sepcific SDKs please consult the SDK specific documentation:

* [Azure IoT Hub Device SDK](azure-iot-hub-devicesdk/README.md)

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
