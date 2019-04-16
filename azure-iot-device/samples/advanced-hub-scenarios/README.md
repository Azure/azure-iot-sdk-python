# Advanced IoT Hub Scenario Samples for the Azure IoT Hub Device SDK

This directory contains samples showing how to use the various features of Azure IoT Hub Device SDK with the Azure IoT Hub.

**These samples are written to run in Python 3.7+**, but can be made to work with Python 3.5 and 3.6 with a slight modification as noted in each sample:

```python
if __name__ == "__main__":
    asyncio.run(main())

    # If using Python 3.6 or below, use the following code instead of asyncio.run(main()):
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(main())
    # loop.close()
```

In order to use these samples, you **must** set your Device Connection String in the environment variable `IOTHUB_DEVICE_CONNECTION_STRING`.

## Included Samples
* [authentication_providers.py](authentication_providers.py) - Use different methods of authentication to connect a device to the Azure IoT Hub.
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