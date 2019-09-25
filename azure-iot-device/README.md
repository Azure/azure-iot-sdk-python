# Azure IoT Device SDK
The Azure IoT Device SDK for Python provides functionality for communicating with the Azure IoT Hub for both Devices and Modules.

**Note that this SDK is currently in preview, and is subject to change.**

## Features
The SDK provides the following clients:

* ### Provisioning Device Client
    * Creates a device identity on the Azure IoT Hub

* ### IoT Hub Device Client
    * Send telemetry messages to Azure IoT Hub
    * Receive Cloud-to-Device (C2D) messages from the Azure IoT Hub
    * Receive and respond to direct method invocations from the Azure IoT Hub

* ### IoT Hub Module Client
    * Supports Azure IoT Edge Hub and Azure IoT Hub
    * Send telemetry messages to a Hub or to another Module
    * Receive Input messages from a Hub or other Modules
    * Receive and respond to direct method invocations from a Hub or other Modules

These clients are available with an asynchronous API, as well as a blocking synchronous API for compatibility scenarios. **We recommend you use Python 3.7+ and the asynchronous API.**

| Python Version | Asynchronous API | Synchronous API |
| -------------- | ---------------- | --------------- |
| Python 3.5.3+  | **YES**          | **YES**         |
| Python 3.4     | NO               | **YES**         |
| Python 2.7     | NO               | **YES**         |

## Installation
```
pip install azure-iot-device
```

## Set up an IoT Hub and create a Device Identity
1. Install the [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli?view=azure-cli-latest) (or use the [Azure Cloud Shell](https://shell.azure.com/)) and use it to [create an Azure IoT Hub](https://docs.microsoft.com/en-us/cli/azure/iot/hub?view=azure-cli-latest#az-iot-hub-create).

    ```bash
    az iot hub create --resource-group <your resource group> --name <your IoT Hub name>
    ```
    * Note that this operation make take a few minutes.

2. Add the IoT Extension to the Azure CLI, and then [register a device identity](https://docs.microsoft.com/en-us/cli/azure/ext/azure-cli-iot-ext/iot/hub/device-identity?view=azure-cli-latest#ext-azure-cli-iot-ext-az-iot-hub-device-identity-create)

    ```bash
    az extension add --name azure-cli-iot-ext
    az iot hub device-identity create --hub-name <your IoT Hub name> --device-id <your device id>
    ```

2. [Retrieve your Device Connection String](https://docs.microsoft.com/en-us/cli/azure/ext/azure-cli-iot-ext/iot/hub/device-identity?view=azure-cli-latest#ext-azure-cli-iot-ext-az-iot-hub-device-identity-show-connection-string) using the Azure CLI

    ```bash
    az iot hub device-identity show-connection-string --device-id <your device id> --hub-name <your IoT Hub name>
    ```

    It should be in the format:
    ```
    HostName=<your IoT Hub name>.azure-devices.net;DeviceId=<your device id>;SharedAccessKey=<some value>
    ```

## Send a simple telemetry message

1. [Begin monitoring for telemetry](https://docs.microsoft.com/en-us/cli/azure/ext/azure-cli-iot-ext/iot/hub?view=azure-cli-latest#ext-azure-cli-iot-ext-az-iot-hub-monitor-events) on your IoT Hub using the Azure CLI

    ```bash
    az iot hub monitor-events --hub-name <your IoT Hub name> --output table
    ```

2. On your device, set the Device Connection String as an enviornment variable called `IOTHUB_DEVICE_CONNECTION_STRING`.

    ### Windows
    ```cmd
    set IOTHUB_DEVICE_CONNECTION_STRING=<your connection string here>
    ```
    * Note that there are **NO** quotation marks around the connection string.

    ### Linux
    ```bash
    export IOTHUB_DEVICE_CONNECTION_STRING="<your connection string here>"
    ```

3. Copy the following code that sends a single message to the IoT Hub into a new python file on your device, and run it from the terminal or IDE (**requires Python 3.7+**):

    ```python
    import asyncio
    import os
    from azure.iot.device.aio import IoTHubDeviceClient


    async def main():
        # Fetch the connection string from an enviornment variable
        conn_str = os.getenv("IOTHUB_DEVICE_CONNECTION_STRING")

        # Create instance of the device client using the connection string
        device_client = IoTHubDeviceClient.create_from_connection_string(conn_str)

        # Send a single message
        print("Sending message...")
        await device_client.send_message("This is a message that is being sent")
        print("Message successfully sent!")

        # finally, disconnect
        await device_client.disconnect()


    if __name__ == "__main__":
        asyncio.run(main())
    ```

4. Check the Azure CLI output to verify that the message was received by the IoT Hub. You should see the following output:

    ```bash
    Starting event monitor, use ctrl-c to stop...
    event:
      origin: <your Device name>
      payload: This is a message that is being sent
    ```

5. Your device is now able to connect to Azure IoT Hub!

## Additional Samples
Check out the [samples repository](https://github.com/Azure/azure-iot-sdk-python-preview/tree/master/azure-iot-device/samples) for example code showing how the SDK can be used in a variety of scenarios, including:
* Sending multiple telemetry messages at once.
* Receiving Cloud-to-Device messages.
* Using Edge Modules with the Azure IoT Edge Hub.
* Send and receive updates to device twin
* Receive invocations to direct methods
* Register a device with the Device Provisioning Service
* Legacy scenarios for Python 2.7 and 3.4

## Getting help and finding API docs

Our SDK makes use of docstrings which means you cand find API documentation directly through Python with use of the [help](https://docs.python.org/3/library/functions.html#help) command:


```python
>>> from azure.iot.device import IoTHubDeviceClient
>>> help(IoTHubDeviceClient)
```
