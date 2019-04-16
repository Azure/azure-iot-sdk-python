# Legacy Scenario Samples for the Azure IoT Hub Device SDK

This directory contains samples showing how to use the various features of Azure IoT Hub Device SDK with the Azure IoT Hub and Azure IoT Edge.

**These samples are legacy samples**, they use the sycnhronous API intended for use with Python 2.7 and 3.4, or in compatibility scenarios with later versions. We recommend you use the [asynchronous API instead](../advanced-hub-scenarios).


## Device Samples
In order to use these samples, you **must** set your Device Connection String in the environment variable `IOTHUB_DEVICE_CONNECTION_STRING`.

* [receive_c2d_message.py](receive_c2d_message.py) - Receive Cloud-to-Device (C2D) messages sent from the Azure IoT Hub to a device.
    * In order to send a C2D message, use the following Azure CLI command:
        ```
        az iot device c2d-message send --device-id <your device id> --hub-name <your IoT Hub name> --data <your message here>
        ```
* [receive_direct_method.py](receive_direct_method.py) - Receive a direct method invocation request on a device from the Azure IoT Hub
    * **THIS FEATURE IS NOT YET COMPLETED, THIS SAMPLE WILL NOT WORK**
* [send_telemetry.py](send_telemetry.py) - Send multiple telmetry messages in parallel from a device to the Azure IoT Hub.
    * You can monitor the Azure IoT Hub for messages received by using the following Azure CLI command:
        ```bash
        az iot hub monitor-events --hub-name <your IoT Hub name> --output table
        ```

## Module Samples
In order to use these samples, they **must** be run from inside an Edge container.

* [receive_input_message.py](receive_input_message.py) - Receive messages sent to an Edge module on a specific module input.
* [send_to_output.py](send_to_output.py) - Send multiple messages in parallel from an Edge module to a specific output