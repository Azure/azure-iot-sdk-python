# Samples for the Azure IoT Hub Device SDK

This directory contains samples showing how to use the various features of the Microsoft Azure IoT Hub service from a device running the Azure IoT Hub Device SDK.

## Quick Start - Simple Telemetry Sample

**Note that this sample is configured for Python 3.7+**

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

4. [Begin monitoring for telemetry](https://docs.microsoft.com/en-us/cli/azure/ext/azure-cli-iot-ext/iot/hub?view=azure-cli-latest#ext-azure-cli-iot-ext-az-iot-hub-monitor-events) on your IoT Hub using the Azure CLI

    ```bash
    az iot hub monitor-events --hub-name <your IoT Hub name> --output table
    ```

5. On your device, set the Device Connection String as an enviornment variable called `IOTHUB_DEVICE_CONNECTION_STRING`.

    ### Windows (cmd)
    ```cmd
    set IOTHUB_DEVICE_CONNECTION_STRING=<your connection string here>
    ```
    * Note that there are **NO** quotation marks around the connection string.

    ### Linux (bash)
    ```bash
    export IOTHUB_DEVICE_CONNECTION_STRING="<your connection string here>"
    ```

6. Once the Device Connection String is set, run the following code from [simple_telemetry.py](simple_telemetry.py) on your device from the terminal or your IDE:

    ```python
    import os
    import asyncio
    from azure.iot.device.aio import IoTHubDeviceClient
    from azure.iot.device import auth


    async def main():
        # Fetch the connection string from an enviornment variable
        conn_str = os.getenv("IOTHUB_DEVICE_CONNECTION_STRING")

        # Create an authentication provider using the connection string
        auth_provider = auth.from_connection_string(conn_str)

        # Create instance of the device client using the authentication provider
        device_client = IoTHubDeviceClient.from_authentication_provider(auth_provider, "mqtt")

        # Connect the device client.
        await device_client.connect()

        # Send a single message
        print("Sending message...")
        await device_client.send_event("This is a message that is being sent")
        print("Message successfully sent!")

        # finally, disconnect
        await device_client.disconnect()


    if __name__ == "__main__":
        asyncio.run(main())
    ```

7. Check the Azure CLI output to verify that the message was received by the IoT Hub. You should see the following output:

    ```bash
    Starting event monitor, use ctrl-c to stop...
    event:
      origin: <your Device name>
      payload: This is a message that is being sent
    ```

8. Your device is now able to connect to Azure IoT Hub!

## Additional Samples
Further samples with more complex IoT Hub scenarios are contained in the [advanced-hub-scenarios](advanced-hub-scenarios) directory, including:

* Send multiple telemetry messages from a Device
* Receive Cloud-to-Device (C2D) messages on a Device

Further samples with more complex IoT Edge scnearios are contained in the [advanced-edge-scenarios](advanced-edge-scenarios) directory, including:

* Send multiple telemetry messages from a Module
* Receive input messages on a Module
* Send messages to a Module Output

Samples for the legacy clients, that use a synchronous API, intended for use with Python 2.7, Python 3.4, or compatibility scenarios for Python 3.5+ are contained in the [legacy-samples](legacy-samples) directory.