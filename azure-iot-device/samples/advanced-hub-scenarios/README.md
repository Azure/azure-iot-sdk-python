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
* [receive_c2d_message.py](receive_c2d_message.py) - Receive Cloud-to-Device (C2D) messages sent from the Azure IoT Hub to a device.
    * In order to send a C2D message, use the following Azure CLI command:
        ```
        az iot device c2d-message send --device-id <your device id> --hub-name <your IoT Hub name> --data <your message here>
        ```
* [receive_direct_method.py](receive_direct_method.py) - Receive direct method requests on a device from the Azure IoT Hub and send responses back
    * In order to invoke a direct method, use the following Azure CLI command:
        ```
        az iot hub invoke-device-method --device-id <your device id> --hub-name <your IoT Hub name> --method-name <desired method>
        ```
* [send_telemetry.py](send_telemetry.py) - Send multiple telmetry messages in parallel from a device to the Azure IoT Hub.
    * You can monitor the Azure IoT Hub for messages received by using the following Azure CLI command:
        ```bash
        az iot hub monitor-events --hub-name <your IoT Hub name> --output table
        ```
### DPS Samples     
In order to use these samples, you **must** have the following environment variables :-

* PROVISIONING_HOST
* PROVISIONING_IDSCOPE
* PROVISIONING_REGISTRATION_ID

There are 2 ways that your device can get registered to the provisioning service differing in authentication mechanisms and another additional environment variable is needed to for the samples:-

* [register_symmetric_key.py](register_symmetric_key.py) - Register to provisioning service using a symmetric key. For this you must have the environment variable PROVISIONING_SYMMETRIC_KEY.
* [register_x509.py](register_x509.py) - Register to provisioning service using a symmetric key. For this you must have the environment variable X509_CERT_FILE, X509_KEY_FILE, PASS_PHRASE.