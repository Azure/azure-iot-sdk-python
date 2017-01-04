---
platform: Debian, Linux, Raspbian, Ubuntu, Windows
device: any
language: Python
---

Run a simple Python sample on device
===
---

# Table of Contents

-   [Introduction](#Introduction)
-   [Step 1: Prerequisites](#Prerequisites)
-   [Step 2: Prepare your Device](#PrepareDevice)
-   [Step 3: Run the Sample](#Run)

<a name="Introduction"></a>
# Introduction

**About this document**

This document describes how to run the **iothub_client_sample.py** and **iothub_service_client_sample.py** Python sample application. This multi-step process includes:
-   Configuring Azure IoT Hub
-   Registering your IoT device
-   Build and deploy Azure IoT SDK on device

<a name="Prerequisites"></a>
# Step 1: Prerequisites

You should have the following items ready before beginning the process:
-   Computer with Git client installed and access to the
    [azure-iot-sdk-python](https://github.com/Azure/azure-iot-sdk-python) GitHub public repository.
-   [Prepare your development environment][lnk-python-devbox-setup]
-   [Setup your IoT hub][lnk-setup-iot-hub]
-   [Provision your device and get its credentials][lnk-manage-iot-hub]

<a name="PrepareDevice"></a>
# Step 2: Prepare your Device

-   Make sure desktop is ready as per instructions given on [Prepare your development environment][lnk-python-devbox-setup].

> Note: On Windows, you can install the **iothub-client** and **iothub-service-client** module package using Pip as described in [Prepare your development environment][lnk-python-devbox-setup].

<a name="Run Device Client"></a>
# Step 3: Run the Device Client sample

- Navigate to the folder **python/device/samples** in your local copy of the repository.

- Open the file **iothub_client_sample.py** in a text editor.

- Locate the following code in the file:

    ```
    connectionString = "[device connection string]"	
    ```

- Replace `[device connection string]` with the connection string for your device. Save the changes.

- Run the sample application using the following command:

    ```
	python iothub_client_sample.py
    ```

- The sample application will send messages to your IoT hub. The **iothub-explorer** utility will display the messages as your IoT hub receives them.

If you receive the error "ImportError: dynamic module does not define module export function (PyInit_iothub_client)" you may be running the samples with a different version of python than the iothub_client was build with. Following the [Prepare your development environment](#python-devbox-setup) to ensure the library is built with the desired python version

<a name="Run Service Client - Registry Manager"></a>
# Step 4: Run the Service Client - Registry Manager sample

- Navigate to the folder **python/service/samples** in your local copy of the repository.

- Open the file **iothub_registrymanager_sample.py** in a text editor.

- Locate the following code in the file:

    ```
    connectionString = "[IoTHub Connection String]"
    deviceId = "[Device Id]"	
    ```

- Replace `[IoTHub Connection String]` with the connection string for your IoTHub and the `[Device Id]` with the sample device name (device will be created and deleted by the sample). Save the changes.

- Run the sample application using the following command:

    ```
	python iothub_registrymanager_sample.py
    ```

- The sample application will do CRUD and Get/Update operations with the given device name. With the **iothub-explorer** you can follow the operations (debug).

<a name="Run Service Client - Messaging"></a>
# Step 5: Run the Service Client - Messaging sample

- Navigate to the folder **python/service/samples** in your local copy of the repository.

- Open the file **iothub_messaging_sample.py** in a text editor.

- Locate the following code in the file:

    ```
    connectionString = "[IoTHub Connection String]"
    deviceId = "[Device Id]"	
    ```

- Replace `[IoTHub Connection String]` with the connection string for your IoTHub and the `[Device Id]` with the sample device name (device will be created and deleted by the sample). Save the changes.

- Run the sample application using the following command:

    ```
	python iothub_messaging_sample.py
    ```

- The sample application will send messages to and receive feedbacks from the given device.

If you receive the error "ImportError: dynamic module does not define module export function (PyInit_iothub_service_client)" you may be running the samples with a different version of python than the iothub_service_client was build with. Following the [Prepare your development environment](#python-devbox-setup) to ensure the library is built with the desired python version

<a name="Run Service Client - Device Method"></a>
# Step 6: Run the Service Client - Device Method sample

- Navigate to the folder **python/service/samples** in your local copy of the repository.

- Open the file **iothub_devicemethod_sample.py** in a text editor.

- Locate the following code in the file:

    ```
    connectionString = "[IoTHub Connection String]"
    deviceId = "[Device Id]"	
    methodName = "MethodName"
    methodPayload = "MethodPayload"
    timeout = 60
    ```

- Replace `[IoTHub Connection String]` with the connection string for your IoTHub and the `[Device Id]` with the device name where you want to call the method on. Optionally, replace the `[methodName]`, `[methodPayload]` and `[timeout]`. Save the changes.

- Run the sample application using the following command:

    ```
   python iothub_devicemethod_sample.py
    ```

- The sample application will send messages to and receive feedbacks from the given device.

If you receive the error "ImportError: dynamic module does not define module export function (PyInit_iothub_service_client)" you may be running the samples with a different version of python than the iothub_service_client was build with. Following the [Prepare your development environment](#python-devbox-setup) to ensure the library is built with the desired python version

<a name="Run Service Client - Device Twin"></a>
# Step 7: Run the Service Client - Device Twin sample

- Navigate to the folder **python/service/samples** in your local copy of the repository.

- Open the file **iothub_devicetwin_sample.py** in a text editor.

- Locate the following code in the file:

    ```
    connectionString = "[IoTHub Connection String]"
    deviceId = "[Device Id]"	
    updateJson = "{\"properties\":{\"desired\":{\"telemetryInterval\":120}}}";
    ```

- Replace `[IoTHub Connection String]` with the connection string for your IoTHub and the `[Device Id]` with the device name what you want to use for twin operations. Optionally, replace the `[updateJson]`. Save the changes.

- Run the sample application using the following command:

    ```
   python iothub_devicetwin_sample.py
    ```

- The sample application will send messages to and receive feedbacks from the given device.

If you receive the error "ImportError: dynamic module does not define module export function (PyInit_iothub_service_client)" you may be running the samples with a different version of python than the iothub_service_client was build with. Following the [Prepare your development environment](#python-devbox-setup) to ensure the library is built with the desired python version

# Debugging the samples (and/or your code)
[Visual Studio Code](https://code.visualstudio.com/) provides an excellent environment to write and debug Python code:
- [Python Tools for Visual Studio](https://www.visualstudio.com/en-us/features/python-vs.aspx)

[lnk-setup-iot-hub]: ../setup_iothub.md
[lnk-manage-iot-hub]: ../manage_iot_hub.md
[lnk-python-devbox-setup]: python-devbox-setup.md
